"""Hito 3.8 — cache ip_intel server-side (sin red en segundas llamadas)."""

import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["QZERO_HUB_DB_PATH"] = _tmp

import pytest
from fastapi.testclient import TestClient

import qzero.api.intel as intel
from qzero.api.app import app

client = TestClient(app)


def test_private_ip_never_hits_network():
    calls = []
    intel.lookup_upstream = lambda ip: calls.append(ip) or {}
    r = client.get("/api/v1/intel/192.168.1.55")
    assert r.status_code == 200
    body = r.json()
    assert body["org"] == "LAN" and body["asn"] == "PRIVATE"
    assert calls == []


def test_public_ip_cached_after_first_lookup():
    calls = []

    def fake(ip):
        calls.append(ip)
        return {"org": "Test ISP S.L.", "asn": "AS64500",
                "country": "ES", "anycast": False}

    intel.lookup_upstream = fake
    r1 = client.get("/api/v1/intel/8.8.8.8").json()
    r2 = client.get("/api/v1/intel/8.8.8.8").json()
    assert calls == ["8.8.8.8"]           # red solo una vez
    assert r1["cached"] is False and r2["cached"] is True
    assert r2["org"] == "Test ISP S.L." and r2["asn"] == "AS64500"


def test_unparseable_ip_treated_as_lan():
    r = client.get("/api/v1/intel/not-an-ip")
    assert r.status_code == 200
    assert r.json()["org"] == "LAN"
