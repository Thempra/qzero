"""
Real-time monitoring service for the QZero dashboard.

Captures live traffic, runs quantum detection, and broadcasts
events to all connected WebSocket clients.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MonitorStats:
    total_packets: int = 0
    total_anomalies: int = 0
    packets_per_sec: float = 0.0
    anomaly_rate: float = 0.0
    uptime_seconds: float = 0.0
    interface: str = ""
    promiscuous: bool = False
    running: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Alert:
    timestamp: str
    src: str
    dst: str
    protocol: int
    size: int
    anomaly_score: float
    severity: str  # LOW / MEDIUM / HIGH / CRITICAL

    def to_dict(self) -> dict:
        return asdict(self)


def _severity(score: float) -> str:
    if score >= 0.85:
        return "CRITICAL"
    if score >= 0.70:
        return "HIGH"
    if score >= 0.55:
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# MonitorService
# ---------------------------------------------------------------------------

class MonitorService:
    """
    Singleton-per-app service that:
    - Runs a background packet-capture loop (scapy in a thread pool)
    - Analyzes batches with the configured QZeroPredictor
    - Broadcasts JSON events to all connected WebSocket clients
    """

    MAX_ALERTS = 200   # keep last N alerts in memory
    HISTORY_LEN = 120  # data-points for the time-series charts

    def __init__(self):
        self._predictor = None
        self._interface: str = "eth0"
        self._promiscuous: bool = False
        self._interval: float = 5.0   # seconds per capture window

        self._connections: Set[WebSocket] = set()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._start_time: Optional[float] = None

        self.stats = MonitorStats()
        self.alerts: deque[Alert] = deque(maxlen=self.MAX_ALERTS)

        # Rolling history (kept as parallel lists for easy JSON serialisation)
        self.history_labels: deque[str] = deque(maxlen=self.HISTORY_LEN)
        self.history_anomaly_rate: deque[float] = deque(maxlen=self.HISTORY_LEN)
        self.history_pps: deque[float] = deque(maxlen=self.HISTORY_LEN)

    # ------------------------------------------------------------------
    # WebSocket connection management
    # ------------------------------------------------------------------

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        # Immediately send current state so the page renders without waiting
        await self._send_to(ws, self._state_snapshot())

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def _broadcast(self, payload: dict) -> None:
        dead: Set[WebSocket] = set()
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    async def _send_to(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            self._connections.discard(ws)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def configure(
        self,
        predictor,
        interface: str = "eth0",
        promiscuous: bool = False,
        interval: float = 5.0,
    ) -> None:
        self._predictor = predictor
        self._interface = interface
        self._promiscuous = promiscuous
        self._interval = interval
        self.stats.interface = interface
        self.stats.promiscuous = promiscuous

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self.stats.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"MonitorService started on {self._interface}")

    def stop(self) -> None:
        self._running = False
        self.stats.running = False
        if self._task:
            self._task.cancel()
        logger.info("MonitorService stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Monitoring loop
    # ------------------------------------------------------------------

    async def _monitor_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while self._running:
            t0 = time.time()
            try:
                packets = await loop.run_in_executor(
                    None, self._capture, self._interval
                )
                if packets:
                    await loop.run_in_executor(
                        None, self._analyze_and_update, packets
                    )
            except asyncio.CancelledError:
                # S7497: re-lanzar tras la limpieza para no romper la semántica
                # de cancelación de asyncio (stop() también pone _running=False).
                raise
            except Exception as e:
                logger.exception("Monitor loop error")
                await asyncio.sleep(1)

            # Update uptime and broadcast
            self.stats.uptime_seconds = time.time() - self._start_time
            snapshot = self._state_snapshot()
            await self._broadcast(snapshot)

    def _capture(self, timeout: float) -> list:
        """Blocking packet capture (runs in thread pool)."""
        try:
            from scapy.all import sniff
            return sniff(
                iface=self._interface,
                timeout=timeout,
                promisc=self._promiscuous,
                store=True,
            )
        except Exception as e:
            logger.exception("Capture error")
            return []

    def _analyze_and_update(self, packets: list) -> None:
        """Blocking analysis (runs in thread pool)."""
        import tempfile
        import numpy as np
        from pathlib import Path

        n_packets = len(packets)
        elapsed = self._interval or 1.0
        ts_label = datetime.now().strftime("%H:%M:%S")

        # Write to tmp pcap for the detector
        tmp_path = None
        n_anomalies = 0
        anomaly_scores: list[float] = []

        if self._predictor and self._predictor.model_fitted:
            try:
                from scapy.all import wrpcap
                from ..core.detector import NetworkTrafficAnalyzer

                with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
                    tmp_path = tmp.name
                wrpcap(tmp_path, packets)

                analyzer = NetworkTrafficAnalyzer(predictor=self._predictor)
                result = analyzer.analyze(tmp_path)
                res = result.get("results", {})
                n_anomalies = res.get("n_anomalies_detected", 0)
                anomaly_scores = res.get("anomaly_scores", [])

            except Exception as e:
                logger.exception("Analysis error")
            finally:
                if tmp_path:
                    Path(tmp_path).unlink(missing_ok=True)

        # Update rolling stats
        pps = n_packets / elapsed
        rate = (n_anomalies / n_packets * 100) if n_packets else 0.0

        self.stats.total_packets += n_packets
        self.stats.total_anomalies += n_anomalies
        self.stats.packets_per_sec = round(pps, 1)
        self.stats.anomaly_rate = round(rate, 2)

        self.history_labels.append(ts_label)
        self.history_anomaly_rate.append(round(rate, 2))
        self.history_pps.append(round(pps, 1))

        # Generate per-packet alerts for high-score anomalies
        if anomaly_scores:
            from scapy.all import IP, TCP, UDP
            for i, pkt in enumerate(packets):
                if i >= len(anomaly_scores):
                    break
                score = float(anomaly_scores[i])
                if score < 0.5:
                    continue
                src = dst = "?"
                proto = 0
                if pkt.haslayer(IP):
                    src = pkt[IP].src
                    dst = pkt[IP].dst
                    proto = pkt[IP].proto
                self.alerts.appendleft(
                    Alert(
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        src=src,
                        dst=dst,
                        protocol=proto,
                        size=len(bytes(pkt)),
                        anomaly_score=round(score, 4),
                        severity=_severity(score),
                    )
                )

    # ------------------------------------------------------------------
    # State snapshot (sent to clients)
    # ------------------------------------------------------------------

    def _state_snapshot(self) -> dict:
        return {
            "type": "snapshot",
            "stats": self.stats.to_dict(),
            "alerts": [a.to_dict() for a in list(self.alerts)[:50]],
            "history": {
                "labels": list(self.history_labels),
                "anomaly_rate": list(self.history_anomaly_rate),
                "pps": list(self.history_pps),
            },
            "model": {
                "fitted": bool(self._predictor and self._predictor.model_fitted),
                "qsvm": bool(self._predictor and self._predictor.use_qsvm),
                "qivae": bool(self._predictor and self._predictor.use_qivae),
                "n_qubits": getattr(self._predictor, "n_qubits", 0),
            },
        }


# Global singleton — shared across the FastAPI application
monitor_service = MonitorService()
