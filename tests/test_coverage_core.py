#!/usr/bin/env python3
"""Tests dirigidos de cobertura: HubStore (SQLite), PostFilter, AgentConfig,
_metrics y config. Todo offline, sin red ni hardware._"""

import json

import numpy as np
import pytest

from qzero.api.hub import HubStore
from qzero.preprocessing.postfilter import PostFilter, PostFilterConfig


# ── HubStore ──────────────────────────────────────────────────────────────

@pytest.fixture()
def store(tmp_path):
    s = HubStore(db_path=tmp_path / "hub.db")
    yield s
    s.close()


ALERT = {
    "timestamp": "2026-09-25T10:00:00+00:00",
    "severity": "HIGH",
    "src": "10.0.0.5", "dst": "93.184.216.34",
    "protocol": 6, "src_port": 44444, "dst_port": 443,
    "size": 1200, "packets": 10, "anomaly_score": 4.7,
    "detail": {"duration_ms": 300, "fwd_packets": 6},
}


def _payload(n=2, severity="HIGH"):
    alerts = [dict(ALERT, severity=severity) for _ in range(n)]
    return {"agent_id": "a1", "agent_name": "srv", "interface": "eth0",
            "timestamp": ALERT["timestamp"], "alerts": alerts}


def test_hub_ingest_and_summary(store):
    r = store.ingest_alert_batch(_payload(3))
    assert r["received"] == 3
    s = store.summary()
    assert s["total_alerts"] == 3
    assert s["agents"] == 1
    assert s["by_severity"].get("HIGH") == 3


def test_hub_ingest_empty(store):
    r = store.ingest_alert_batch({"agent_id": "a1", "alerts": []})
    assert r["received"] == 0


def test_hub_list_alerts_filters(store):
    store.ingest_alert_batch(_payload(2, "HIGH"))
    store.ingest_alert_batch(_payload(1, "CRITICAL"))
    assert len(store.list_alerts()) == 3
    assert len(store.list_alerts(severity="CRITICAL")) == 1
    assert len(store.list_alerts(agent_id="a1", limit=1)) == 1
    assert store.list_alerts(since="2030-01-01T00:00:00") == []


def test_hub_detail_deserialized(store):
    store.ingest_alert_batch(_payload(1))
    a = store.list_alerts()[0]
    assert isinstance(a["detail"], dict)
    assert a["detail"]["fwd_packets"] == 6


def test_hub_heartbeat_and_agents(store):
    r = store.heartbeat("a2", "srv2", "eth0")
    assert r["heartbeat"] is True
    agents = {a["agent_id"]: a for a in store.list_agents()}
    assert "a2" in agents
    assert agents["a2"]["interface"] == "eth0"


def test_hub_summary_counters_incremental(store):
    store.ingest_alert_batch(_payload(5))
    store.ingest_alert_batch(_payload(2, "CRITICAL"))
    s = store.summary()
    assert s["total_alerts"] == 7
    assert s["by_severity"]["CRITICAL"] == 2


def test_hub_reopen_migrates(tmp_path):
    db = tmp_path / "hub.db"
    s1 = HubStore(db_path=db)
    s1.ingest_alert_batch(_payload(1))
    s1.close()
    s2 = HubStore(db_path=db)
    assert s2.summary()["total_alerts"] == 1
    s2.close()


# ── PostFilter ────────────────────────────────────────────────────────────

def test_postfilter_dns_suppressed():
    pf = PostFilter()
    flow = {"src_ip": "10.0.0.5", "dst_ip": "1.1.1.1", "proto": 17,
            "src_port": 51000, "dst_port": 53, "bytes": 80, "packets": 2}
    assert pf.should_suppress(flow, 4.5)[0] is True


def test_postfilter_private_not_suppressed_by_default():
    """Regresión: el tráfico LAN (escaneo interno) NUNCA se blanquea."""
    pf = PostFilter()
    flow = {"src_ip": "192.168.1.10", "dst_ip": "192.168.1.20", "proto": 6,
            "src_port": 4000, "dst_port": 22, "bytes": 5000, "packets": 50}
    assert pf.should_suppress(flow, 4.9)[0] is False


def test_postfilter_https_volume_cap():
    pf = PostFilter()
    flow = {"src_port": 40000, "dst_port": 443, "bytes": 9_000_000,
            "packets": 6000}
    # score alto por volumen → no CRITICAL
    assert pf.severity_for(flow, 9.0) != "CRITICAL"
    # sin cap → CRITICAL
    pf2 = PostFilter(PostFilterConfig(https_volume_cap_score=None))
    assert pf2.severity_for(flow, 9.0) == "CRITICAL"


def test_postfilter_severity_thresholds():
    pf = PostFilter(PostFilterConfig(https_volume_cap_score=None))
    assert pf.severity_for({}, 5.5) == "CRITICAL"
    assert pf.severity_for({}, 4.5) == "HIGH"
    assert pf.severity_for({}, 4.0) == "MEDIUM"
    assert pf.severity_for({}, 1.0) == "LOW"


def test_postfilter_local_multicast_small_suppressed():
    pf = PostFilter()
    flow = {"src_ip": "224.0.0.251", "dst_ip": "10.0.0.5", "proto": 17,
            "src_port": 5353, "dst_port": 5353, "bytes": 60, "packets": 1}
    assert pf.should_suppress(flow, 3.0)[0] is True


def test_postfilter_annotate_defaults():
    pf = PostFilter()
    flow = {"src_ip": "10.0.0.5", "dst_ip": "8.8.8.8", "proto": 6,
            "src_port": 1, "dst_port": 9999, "bytes": 900, "packets": 9}
    ann = pf.annotate(flow, 4.8)
    assert ann["suppressed"] is False
    assert ann["suppress_reason"] == ""


# ── AgentConfig ───────────────────────────────────────────────────────────

def test_agent_config_defaults():
    from qzero.agent.agent import AgentConfig

    cfg = AgentConfig()
    assert cfg.interface == "eth0"
    assert cfg.max_alerts_per_batch > 0


def test_agent_config_auto_interface_and_id():
    from qzero.agent.agent import AgentConfig

    cfg = AgentConfig(interface="auto", agent_id="")
    assert cfg.agent_id  # se autogenera host-interface
    assert isinstance(cfg.interface, str)


def test_agent_severity_pure():
    from qzero.agent.agent import QZeroAgent

    assert QZeroAgent._severity(6.0) in {"CRITICAL", "HIGH"}
    assert QZeroAgent._severity(0.5) == "LOW"


def test_agent_flow_alert_shape():
    from qzero.agent.agent import AgentConfig, QZeroAgent

    agent = QZeroAgent(AgentConfig(hub_url=""))
    flow = {"src_ip": "10.0.0.5", "dst_ip": "1.2.3.4", "proto": 6,
            "src_port": 1234, "dst_port": 443,
            "total_length_fwd_packets": 100, "total_length_bwd_packets": 50,
            "total_fwd_packets": 5, "total_bwd_packets": 2,
            "flow_duration": 12, "flow_bytes_per_sec": 12.5}
    alert = agent._flow_alert(flow, 4.2)
    assert alert["size"] == 150
    assert alert["packets"] == 7
    assert alert["detail"]["fwd_packets"] == 5
    assert alert["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


# ── evaluation.metrics ────────────────────────────────────────────────────

def test_evaluate_model_perfect():
    from qzero.evaluation.metrics import evaluate_model

    y = np.array([0, 1, 0, 1, 1, 0])
    res = evaluate_model(y, y.copy())
    d = res.to_dict() if hasattr(res, "to_dict") else res
    assert d["accuracy"] == pytest.approx(1.0)


def test_calculate_quantum_advantage_shape():
    from qzero.evaluation.metrics import calculate_quantum_advantage

    res = calculate_quantum_advantage(
        {"accuracy": 0.9, "f1_weighted": 0.85},
        {"accuracy": 0.95, "f1_weighted": 0.92},
    )
    assert isinstance(res, dict)


# ── config ────────────────────────────────────────────────────────────────

def test_config_get_set_save(tmp_path):
    from qzero.config import QZeroConfig

    f = tmp_path / "cfg.json"
    cfg = QZeroConfig(config_file=str(f))
    cfg.set("alpha", 7)
    cfg.save()
    cfg2 = QZeroConfig(config_file=str(f))
    assert cfg2.get("alpha") == 7
    assert cfg2.get("missing", "dflt") == "dflt"


def test_config_get_path(tmp_path):
    from qzero.config import QZeroConfig

    f = tmp_path / "cfg.json"
    cfg = QZeroConfig(config_file=str(f))
    cfg.set("paths.model_dir", str(tmp_path))
    p = cfg.get_path("paths.model_dir")
    assert p == tmp_path


def test_setup_logging_idempotent():
    from qzero.config import setup_logging

    setup_logging(verbose=True)
    setup_logging(verbose=False)
