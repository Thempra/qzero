"""Hito 3.7 — auth app-level: login fail-closed, token SPA, exenciones."""

import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ.setdefault("QZERO_HUB_DB", _tmp)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import qzero.api.auth as auth_mod  # noqa: E402
from qzero.api.app import app  # noqa: E402

_AUTH_KEYS = ("ADMIN_PASSWORD", "QZERO_AUTH_SECRET",
              "QZERO_AUTH_TOKEN_VERSION", "QZERO_REQUIRE_AGENT_TOKEN",
              "QZERO_AGENT_TOKEN")


@pytest.fixture()
def client_auth(monkeypatch):
    """Client con auth ACTIVA; el entorno se restaura tras cada test para no
    contaminar otros módulos (el objeto app se comparte entre tests)."""
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret-admin")
    monkeypatch.setenv("QZERO_AUTH_SECRET", "test-signing-secret")
    monkeypatch.setenv("QZERO_AUTH_TOKEN_VERSION", "1")
    return TestClient(app)


def _login(client):
    r = client.post("/api/v1/auth/login", json={"password": "s3cret-admin"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_wrong_password_401(client_auth):
    r = client_auth.post("/api/v1/auth/login", json={"password": "nope"})
    assert r.status_code == 401


def test_query_routes_require_token(client_auth):
    assert client_auth.get("/api/v1/hub/summary").status_code == 401
    assert client_auth.get("/api/v1/alerts").status_code == 401
    tok = _login(client_auth)
    assert client_auth.get("/api/v1/hub/summary").status_code == 401
    r = client_auth.get("/api/v1/hub/summary", headers=_auth(tok))
    assert r.status_code == 200 and "total_alerts" in r.json()


def test_health_and_ingest_exempt(client_auth):
    assert client_auth.get("/health").status_code == 200
    # ingest de agentes sin token SPA debe pasar (data-plane LAN)
    r = client_auth.post("/api/v1/agents/auth-test/heartbeat", json={})
    assert r.status_code == 200


def test_tampered_and_expired_tokens_rejected(client_auth):
    tok = _login(client_auth)
    h, p, s = tok.split(".")
    assert client_auth.get("/api/v1/alerts",
                           headers=_auth(f"{h}.{p}.XXX")).status_code == 401
    t_exp, _ = auth_mod.issue_token(ttl_seconds=-10)
    assert client_auth.get("/api/v1/alerts", headers=_auth(t_exp)).status_code == 401


def test_token_version_rotation_revokes(client_auth, monkeypatch):
    tok = _login(client_auth)
    assert client_auth.get("/api/v1/alerts", headers=_auth(tok)).status_code == 200
    monkeypatch.setenv("QZERO_AUTH_TOKEN_VERSION", "2")
    assert client_auth.get("/api/v1/alerts", headers=_auth(tok)).status_code == 401
    tok2 = _login(client_auth)
    assert client_auth.get("/api/v1/alerts", headers=_auth(tok2)).status_code == 200


def test_fail_closed_without_admin_password(monkeypatch):
    for k in _AUTH_KEYS:
        monkeypatch.delenv(k, raising=False)
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"password": "anything"})
    assert r.status_code == 503


def test_agent_token_required_on_ingest_when_enabled(client_auth, monkeypatch):
    monkeypatch.setenv("QZERO_REQUIRE_AGENT_TOKEN", "1")
    monkeypatch.setenv("QZERO_AGENT_TOKEN", "tok-agente")
    r = client_auth.post("/api/v1/agents/secure-agent/heartbeat", json={})
    assert r.status_code == 401
    r = client_auth.post("/api/v1/agents/secure-agent/heartbeat", json={},
                         headers={"X-Agent-Token": "tok-agente"})
    assert r.status_code == 200

