#!/usr/bin/env python3
"""Tests de la API FastAPI con TestClient (offline, sin captura real).

La variable QZERO_HUB_DB debe fijarse ANTES de importar qzero.api.app para
que el hub_store singleton no escriba en data/hub.db."""

import os
import tempfile

import pytest

_tmp_hub_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ.setdefault("QZERO_HUB_DB", _tmp_hub_db)

from fastapi.testclient import TestClient  # noqa: E402

from qzero.api.app import app, monitor_service  # noqa: E402

client = TestClient(app)


# ── Endpoints básicos ─────────────────────────────────────────────────────

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "QZero API"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_models():
    r = client.get("/models")
    assert r.status_code == 200
    assert "models" in r.json()


def test_stats():
    r = client.get("/stats")
    assert r.status_code == 200


def test_dashboard_serves_html():
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "<html" in r.text.lower()


# ── Hub ───────────────────────────────────────────────────────────────────

ALERT = {
    "timestamp": "2026-09-25T10:00:00+00:00",
    "severity": "HIGH", "src": "10.0.0.5", "dst": "1.2.3.4",
    "protocol": 6, "src_port": 1, "dst_port": 443,
    "size": 900, "packets": 9, "anomaly_score": 4.6, "detail": {},
}


def test_hub_ingest_and_query_flow():
    payload = {"agent_name": "t", "interface": "eth0",
               "timestamp": ALERT["timestamp"], "alerts": [ALERT]}
    r = client.post("/api/v1/agents/testapi/alerts", json=payload)
    assert r.status_code == 200
    assert r.json()["received"] == 1

    s = client.get("/api/v1/hub/summary").json()
    assert s["total_alerts"] >= 1

    agents = client.get("/api/v1/agents").json()
    assert any(a["agent_id"] == "testapi" for a in agents)

    alerts = client.get("/api/v1/alerts", params={"agent_id": "testapi"}).json()
    assert alerts and alerts[0]["severity"] == "HIGH"

    rec = client.get("/api/v1/alerts/recent", params={"minutes": 1}).json()
    assert isinstance(rec, list)


def test_hub_heartbeat_endpoint():
    r = client.post("/api/v1/agents/testhb/heartbeat",
                    json={"agent_name": "hb", "interface": "wlan0"})
    assert r.status_code == 200
    assert r.json()["heartbeat"] is True


def test_hub_dashboard_html():
    r = client.get("/api/v1/hub")
    assert r.status_code == 200
    assert "<html" in r.text.lower()


# ── Monitor control (sin interfaz real) ───────────────────────────────────

def test_monitor_stop_idempotent():
    r = client.post("/monitor/stop")
    assert r.status_code == 200
    assert r.json()["status"] == "stopped"
    assert monitor_service.is_running is False


# ── /analyze (analyzer stubbeado: sin scapy/torch real) ──────────────────

def test_analyze_endpoint_uses_analyzer(monkeypatch):
    fake = {"status": "ok", "filename": "x.pcap", "total_packets": 5,
            "method": "qivae", "results": {"anomalies": 1, "total_flows": 2}}
    import qzero.core.detector as det

    monkeypatch.setattr(
        det.NetworkTrafficAnalyzer, "analyze",
        lambda self, path, method="best": fake, raising=True)
    r = client.post("/analyze",
                    files={"file": ("x.pcap", b"\x00" * 16,
                                    "application/octet-stream")})
    assert r.status_code == 200
    assert r.json()["results"]["anomalies"] == 1


def test_analyze_error_returns_500(monkeypatch):
    import qzero.core.detector as det

    def boom(self, path, method="best"):
        raise RuntimeError("corrupt pcap")

    monkeypatch.setattr(det.NetworkTrafficAnalyzer, "analyze", boom)
    r = client.post("/analyze",
                    files={"file": ("bad.pcap", b"\x00", None)})
    assert r.status_code == 500
    assert "corrupt pcap" in r.json()["detail"]
