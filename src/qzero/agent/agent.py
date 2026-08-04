"""
QZero Agent — real-time traffic monitor deployable on any server.

The agent continuously captures live network traffic, runs QZero's quantum
anomaly detection on each capture window, and pushes any detected alerts to
a central QZero hub via HTTP. This lets you deploy lightweight sensors across
many servers while keeping a single centralised view of all alerts.

The agent is intentionally dependency-light: transport uses the Python
standard library (urllib), so it can run anywhere the qzero package + scapy
are installed.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import socket
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_HUB_PATH = "/api/v1/agents/{agent_id}/alerts"


@dataclass
class AgentConfig:
    """Configuration for a QZero agent instance."""

    agent_id: str = ""
    agent_name: str = ""
    interface: str = "eth0"
    promiscuous: bool = False
    interval: float = 5.0          # capture window (seconds)
    hub_url: str = ""              # base URL of the central QZero hub, e.g. http://1.2.3.4:8000
    model_dir: Optional[str] = None
    n_qubits: int = 4
    train_samples: int = 2000
    use_qsvm: bool = True   # QSVM is very slow to train on CPU — disable for fast boot
    use_qivae: bool = True  # Quantum-inspired VAE (torch) — faster, good default
    alert_threshold: float = 0.5   # anomaly score above which an alert is raised
    max_alerts_per_batch: int = 20
    retry_backoff: float = 2.0     # seconds between hub push retries
    max_retries: int = 3
    buffer_dir: Optional[str] = None  # local spool for alerts when hub is down

    def __post_init__(self) -> None:
        if not self.agent_id:
            host = socket.gethostname() or platform.node() or "unknown"
            self.agent_id = f"{host}-{self.interface}"
        if not self.agent_name:
            self.agent_name = platform.node() or self.agent_id
        if self.interface == "auto":
            self.interface = self._detect_interface()

    @staticmethod
    def _detect_interface() -> str:
        """Pick the default outbound interface (best-effort)."""
        try:
            import subprocess
            out = subprocess.run(
                ["ip", "route", "get", "1.1.1.1"],
                capture_output=True, text=True, timeout=5,
            ).stdout
            toks = out.split()
            if "dev" in toks:
                idx = toks.index("dev")
                if idx + 1 < len(toks):
                    return toks[idx + 1]
        except Exception:
            pass
        return "eth0"


class QZeroAgent:
    """Run a real-time traffic-monitoring loop and push alerts to a hub."""

    def __init__(self, config: AgentConfig | dict | None = None, **overrides):
        if config is None:
            config = AgentConfig()
        elif isinstance(config, dict):
            config = AgentConfig(**{**config, **overrides})
        else:
            # AgentConfig instance + keyword overrides
            d = asdict(config)
            d.update(overrides)
            config = AgentConfig(**d)
        self.config = config

        self._predictor = None
        self._analyzer = None
        self._running = False
        self.stats = {
            "agent_id": config.agent_id,
            "agent_name": config.agent_name,
            "interface": config.interface,
            "started_at": None,
            "windows": 0,
            "packets_seen": 0,
            "alerts_sent": 0,
            "push_failures": 0,
        }

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_models(self) -> None:
        from qzero import QZero

        if self._predictor is not None:
            return
        logger.info("Loading / preparing QZero models …")
        qzero = QZero(
            n_qubits=self.config.n_qubits,
            use_qsvm=self.config.use_qsvm,
            use_qivae=self.config.use_qivae,
        )
        model_dir = Path(self.config.model_dir) if self.config.model_dir else None
        # A mounted-but-empty volume creates the dir but holds no models yet.
        has_models = bool(
            model_dir and model_dir.exists() and (model_dir / "scaler.pkl").exists()
        )
        if has_models:
            try:
                qzero.load(str(model_dir))
                logger.info("Loaded pre-trained models from %s", model_dir)
            except Exception as e:  # noqa: BLE001 — corrupt/incomplete volume
                logger.warning("Model load failed (%s) — retraining.", e)
                qzero = QZero(
                    n_qubits=self.config.n_qubits,
                    use_qsvm=self.config.use_qsvm,
                    use_qivae=self.config.use_qivae,
                )
                qzero.train(n_samples=self.config.train_samples)
                self._persist_models(qzero)
        else:
            logger.info(
                "No model dir — training on synthetic data (qsvm=%s, qivae=%s, "
                "samples=%s; may take a while) …",
                self.config.use_qsvm, self.config.use_qivae, self.config.train_samples,
            )
            qzero.train(n_samples=self.config.train_samples)
            # Persist trained models so the agent starts fast on next boot
            # instead of re-training the quantum stack every time.
            self._persist_models(qzero)
        self._predictor = qzero.predictor

        from qzero.core.detector import NetworkTrafficAnalyzer
        self._analyzer = NetworkTrafficAnalyzer(predictor=self._predictor)

    def _persist_models(self, qzero) -> None:
        """Save freshly trained models if a model_dir is configured."""
        if not self.config.model_dir:
            return
        try:
            qzero.save(self.config.model_dir)
            logger.info("Saved freshly trained models to %s", self.config.model_dir)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not save models: %s", e)

    # ------------------------------------------------------------------
    # Capture + analyze loop
    # ------------------------------------------------------------------

    def run(self, keep_running=True) -> None:
        """Run the monitoring loop forever (or until KeyboardInterrupt)."""
        self._ensure_models()

        if self.config.interface == "any":
            logger.warning(
                "'any' interface is not supported by scapy on all systems; "
                "falling back to default."
            )

        self._running = True
        self.stats["started_at"] = datetime.now().isoformat()
        logger.info(
            "QZero Agent %s monitoring %s (interval %ss) → hub %s",
            self.config.agent_id,
            self.config.interface,
            self.config.interval,
            self.config.hub_url or "LOCAL-ONLY (no hub)",
        )

        try:
            from scapy.all import sniff, wrpcap

            while self._running:
                window_start = time.time()
                packets = sniff(
                    iface=self.config.interface,
                    promisc=self.config.promiscuous,
                    timeout=self.config.interval,
                    store=True,
                )
                self.stats["windows"] += 1
                self.stats["packets_seen"] += len(packets)

                if not packets:
                    continue

                alerts = self._analyze_window(packets, wrpcap)
                if alerts:
                    self._emit_alerts(alerts)

                # Enforce interval pacing if capture returned early
                elapsed = time.time() - window_start
                if keep_running and elapsed < self.config.interval:
                    time.sleep(self.config.interval - elapsed)

        except KeyboardInterrupt:
            logger.info("Agent stopped by user.")
        except ImportError:
            logger.error("Scapy is not installed. Run: pip install scapy")
        finally:
            self._running = False

    def _analyze_window(self, packets, wrpcap) -> List[Dict]:
        """Run detection on a captured window and return per-packet alerts."""
        if self._analyzer is None:
            return []

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
                tmp_path = tmp.name
            wrpcap(tmp_path, packets)

            result = self._analyzer.analyze(tmp_path)
            res = result.get("results", {})
            scores = res.get("anomaly_scores", [])

            alerts = []
            for i, pkt in enumerate(packets):
                if i >= len(scores):
                    break
                score = float(scores[i])
                if score < self.config.alert_threshold:
                    continue
                alerts.append(self._packet_alert(pkt, score))
                if len(alerts) >= self.config.max_alerts_per_batch:
                    break

            return alerts
        except Exception as e:  # noqa: BLE001
            logger.error("Analysis error: %s", e)
            return []
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    def _packet_alert(self, pkt, score: float) -> Dict:
        from scapy.all import IP, TCP, UDP

        src = dst = "?"
        sport = dport = 0
        proto = 0
        if pkt.haslayer(IP):
            src = pkt[IP].src
            dst = pkt[IP].dst
            proto = pkt[IP].proto
        if pkt.haslayer(TCP):
            sport, dport = pkt[TCP].sport, pkt[TCP].dport
        elif pkt.haslayer(UDP):
            sport, dport = pkt[UDP].sport, pkt[UDP].dport

        return {
            "timestamp": datetime.now().isoformat(),
            "src": src,
            "dst": dst,
            "protocol": proto,
            "src_port": sport,
            "dst_port": dport,
            "size": len(bytes(pkt)),
            "anomaly_score": round(score, 4),
            "severity": self._severity(score),
        }

    @staticmethod
    def _severity(score: float) -> str:
        if score >= 0.85:
            return "CRITICAL"
        if score >= 0.70:
            return "HIGH"
        if score >= 0.55:
            return "MEDIUM"
        return "LOW"

    # ------------------------------------------------------------------
    # Alert delivery
    # ------------------------------------------------------------------

    def _emit_alerts(self, alerts: List[Dict]) -> None:
        """Push alerts to the hub (with retry + local spool), and log them."""
        for a in alerts:
            logger.warning(
                "⚠️  ALERT [%s] %s → %s proto=%s score=%s (%s)",
                a["severity"], a["src"], a["dst"], a.get("protocol"),
                a["anomaly_score"], a["src_port"],
            )

        if not self.config.hub_url:
            # No hub — reflect locally to a JSONL file
            self._spool_locally(alerts)
            self.stats["alerts_sent"] += len(alerts)
            return

        payload = {
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "interface": self.config.interface,
            "timestamp": datetime.now().isoformat(),
            "alerts": alerts,
        }

        sent = self._push_with_retry(payload)
        if sent:
            self.stats["alerts_sent"] += len(alerts)
        else:
            self.stats["push_failures"] += 1
            self._spool_locally(alerts)

    def _push_with_retry(self, payload: Dict) -> bool:
        url = self.config.hub_url.rstrip("/") + DEFAULT_HUB_PATH.format(
            agent_id=self.config.agent_id
        )
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(1, self.config.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if 200 <= resp.status < 300:
                        return True
                    logger.warning("Hub returned status %s", resp.status)
            except urllib.error.URLError as e:
                logger.warning(
                    "Hub push failed (attempt %s/%s): %s", attempt,
                    self.config.max_retries, e,
                )
            time.sleep(self.config.retry_backoff * attempt)
        return False

    def _spool_locally(self, alerts: List[Dict]) -> None:
        """Write alerts to a local JSONL file (used when hub is absent/down)."""
        buf = self.config.buffer_dir or "."
        path = Path(buf) / f"qzero-alerts-{self.config.agent_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            for a in alerts:
                f.write(json.dumps(a) + "\n")
        logger.info("Spooled %d alert(s) to %s", len(alerts), path)

    # ------------------------------------------------------------------

    def get_status(self) -> Dict:
        return dict(self.stats)


def main() -> None:
    """Simple CLI entry for running an agent standalone."""
    import argparse

    parser = argparse.ArgumentParser(
        description="QZero Agent — real-time quantum threat detection sensor"
    )
    parser.add_argument("--agent-id", default=os.environ.get("QZERO_AGENT_ID", ""))
    parser.add_argument("--interface", "-i", default=os.environ.get("QZERO_INTERFACE", "eth0"))
    parser.add_argument("--promiscuous", "-p", action="store_true",
                        default=os.environ.get("QZERO_PROMISCUOUS", "0") == "1")
    parser.add_argument("--interval", type=float,
                        default=float(os.environ.get("QZERO_INTERVAL", "5.0")))
    parser.add_argument("--hub-url", default=os.environ.get("QZERO_HUB_URL", ""),
                        help="Central hub base URL, e.g. http://10.0.0.5:8000")
    parser.add_argument("--model-dir", default=os.environ.get("QZERO_MODEL_DIR"))
    parser.add_argument("--n-qubits", type=int, default=int(os.environ.get("QZERO_N_QUBITS", "4")))
    parser.add_argument("--threshold", type=float,
                        default=float(os.environ.get("QZERO_ALERT_THRESHOLD", "0.5")))
    parser.add_argument("--buffer-dir", default=os.environ.get("QZERO_BUFFER_DIR"))
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = AgentConfig(
        agent_id=args.agent_id,
        interface=args.interface,
        promiscuous=args.promiscuous,
        interval=args.interval,
        hub_url=args.hub_url,
        model_dir=args.model_dir,
        n_qubits=args.n_qubits,
        alert_threshold=args.threshold,
        buffer_dir=args.buffer_dir,
    )
    QZeroAgent(config).run()


if __name__ == "__main__":
    main()
