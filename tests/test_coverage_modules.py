#!/usr/bin/env python3
"""Tests de cobertura: NetworkTrafficAnalyzer, MonitorService y entrega de
alertas del agente (spool, heartbeat, push con retry stubbeado). Offline."""

import json

import pytest

scapy = pytest.importorskip("scapy")
from scapy.all import IP, TCP, UDP, Ether, wrpcap  # noqa: E402


def _mkpcap(tmp_path, n=6):
    pkts = []
    for i in range(n):
        pkts.append(
            Ether() / IP(src=f"10.0.0.{2 + i}", dst="93.184.216.34")
            / TCP(sport=40000 + i, dport=443)
        )
        pkts.append(
            Ether() / IP(src="10.0.0.9", dst=f"10.0.0.{2 + i}")
            / TCP(sport=443, dport=40000 + i)
        )
    p = tmp_path / "t.pcap"
    wrpcap(str(p), pkts)
    return p


# ── NetworkTrafficAnalyzer ────────────────────────────────────────────────

def test_analyzer_no_predictor_returns_error(tmp_path):
    from qzero.core.detector import NetworkTrafficAnalyzer

    pcap = _mkpcap(tmp_path)
    res = NetworkTrafficAnalyzer(predictor=None).analyze(str(pcap))
    # envelope OK; la detección degradada se reporta en results
    assert res["status"] == "success"
    assert res["results"]["status"] == "no_model"
    assert res["flows_extracted"] >= 1


def test_analyzer_bad_pcap(tmp_path):
    from qzero.core.detector import NetworkTrafficAnalyzer

    bad = tmp_path / "bad.pcap"
    bad.write_bytes(b"not a pcap at all")
    res = NetworkTrafficAnalyzer().analyze(str(bad))
    assert res["status"] == "error"
    assert "PCAP" in res["message"] or "pcap" in res["message"]


def test_analyzer_empty_pcap(tmp_path):
    from qzero.core.detector import NetworkTrafficAnalyzer

    p = tmp_path / "empty.pcap"
    wrpcap(str(p), [])
    res = NetworkTrafficAnalyzer().analyze(str(p))
    assert res["status"] == "error"


def test_analyzer_predict_stub_no_model():
    """_predict con predictor sin fitted -> diccionario 'no_model' completo."""
    from qzero.core.detector import NetworkTrafficAnalyzer
    import pandas as pd

    class Unfitted:
        model_fitted = False
        scaler = None

    res = NetworkTrafficAnalyzer(predictor=Unfitted())._predict(
        pd.DataFrame({"a": [1.0, 2.0]}))
    assert res["status"] == "no_model"
    assert res["n_anomalies_detected"] == 0


# ── MonitorService ────────────────────────────────────────────────────────

def test_monitor_severity_and_stats():
    from qzero.api.monitor import _severity, MonitorStats

    assert _severity(9.0) in {"CRITICAL", "HIGH"}
    assert _severity(0.1) == "LOW"
    s = MonitorStats()
    d = s.to_dict()
    assert "total_packets" in d


def test_monitor_configure_stop_without_start():
    from qzero.api.monitor import MonitorService

    ms = MonitorService()
    assert ms.is_running is False
    ms.stop()  # idempotente sin start
    assert ms.is_running is False


def test_monitor_analyze_and_update_unfitted():
    """Sin predictor fitted solo actualiza estadísticas de tasa."""
    from qzero.api.monitor import MonitorService

    ms = MonitorService()
    ms.configure(predictor=None, interface="lo", interval=1.0)
    pkts = [Ether() / IP(src="1.2.3.4", dst="5.6.7.8") / UDP()] * 10
    ms._analyze_and_update(pkts)
    assert ms.stats.total_packets >= 10
    assert ms.stats.packets_per_sec > 0


@pytest.mark.asyncio
async def test_monitor_broadcast_no_clients():
    from qzero.api.monitor import MonitorService

    ms = MonitorService()
    await ms._broadcast({"type": "ping"})  # sin sockets: no debe explotar
    await ms._send_to(None, {"type": "x"})  # ws muerto -> ignorado


# ── Agente: entrega de alertas ────────────────────────────────────────────

def test_agent_spool_local_jsonl(tmp_path):
    from qzero.agent.agent import AgentConfig, QZeroAgent

    cfg = AgentConfig(hub_url="", buffer_dir=str(tmp_path))
    agent = QZeroAgent(cfg)
    alert = {"severity": "HIGH", "src": "a", "dst": "b", "anomaly_score": 5.0}
    agent._emit_alerts([alert])
    files = list(tmp_path.glob("qzero-alerts-*.jsonl"))
    assert len(files) == 1
    line = json.loads(files[0].read_text().splitlines()[0])
    assert line["severity"] == "HIGH"
    assert agent.stats["alerts_sent"] == 1


def test_agent_push_failure_spools(tmp_path, monkeypatch):
    import urllib.request
    import urllib.error

    from qzero.agent.agent import AgentConfig, QZeroAgent

    cfg = AgentConfig(hub_url="http://127.0.0.1:9/api",
                      buffer_dir=str(tmp_path),
                      max_retries=1, retry_backoff=0.01)
    agent = QZeroAgent(cfg)

    def refuse(*a, **k):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    agent._emit_alerts([{"severity": "LOW", "src": "a", "dst": "b",
                         "anomaly_score": 1.0}])
    assert agent.stats["push_failures"] == 1
    assert list(tmp_path.glob("qzero-alerts-*.jsonl"))


def test_agent_push_success(monkeypatch):
    from qzero.agent.agent import AgentConfig, QZeroAgent

    cfg = AgentConfig(hub_url="http://hub.local", max_retries=1,
                      retry_backoff=0.01)
    agent = QZeroAgent(cfg)

    class FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("qzero.agent.agent.urllib.request.urlopen",
                        lambda *a, **k: FakeResp())
    assert agent._push_with_retry({"alerts": []}) is True


def test_agent_heartbeat_failure_swallowed(monkeypatch):
    import urllib.request
    import urllib.error

    from qzero.agent.agent import AgentConfig, QZeroAgent

    cfg = AgentConfig(hub_url="http://127.0.0.1:9/api")
    agent = QZeroAgent(cfg)

    def refuse(*a, **k):
        raise urllib.error.URLError("down")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)
    agent._heartbeat()  # no debe lanzar


def test_agent_get_status():
    from qzero.agent.agent import AgentConfig, QZeroAgent

    agent = QZeroAgent(AgentConfig(hub_url=""))
    st = agent.get_status()
    assert isinstance(st, dict)
    assert "alerts_sent" in st
