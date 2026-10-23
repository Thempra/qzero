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
              "QZERO_AGENT_TOKEN", "QZERO_AUTH_ENFORCE")


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



# ── Fase 0.1/0.2/0.3 — hardening (tests de regresión) ───────────────────────
# Estos tests fallaban con el código anterior (fail-open, password en claro,
# sin rate limit, ingest abierto con token configurado).


@pytest.fixture(autouse=True)
def _reset_login_limits():
    """El rate limiter es estado de módulo: limpiarlo entre tests."""
    auth_mod.reset_login_limits()
    yield
    auth_mod.reset_login_limits()


def test_fail_closed_production_mode_without_admin_password(monkeypatch):
    """B-1: en modo producción (QZERO_AUTH_ENFORCE=1) sin ADMIN_PASSWORD las
    rutas protegidas dan 503 SIEMPRE (antes: 200 fail-open)."""
    for k in _AUTH_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("QZERO_AUTH_ENFORCE", "1")
    c = TestClient(app)
    assert c.get("/api/v1/alerts").status_code == 503
    assert c.get("/api/v1/hub/summary").status_code == 503
    # exentas siguen exentas
    assert c.get("/health").status_code != 503
    assert c.get("/api/v1/auth/status").status_code == 200


def test_fail_closed_default_outside_pytest(monkeypatch):
    """B-1: sin QZERO_AUTH_ENFORCE el default es fail-closed, SIEMPRE.

    Antes este test fingía ``_test_mode() -> False`` porque el parche usaba
    ``sys.modules`` para adivinar si estaba bajo pytest. Ese backdoor se
    retiró: el default ya no depende del runner, así que aquí basta con no
    definir el flag. Ver también test_no_sys_modules_sniffing_in_production_code.
    """
    for k in _AUTH_KEYS:
        monkeypatch.delenv(k, raising=False)
    assert auth_mod.auth_enforce_mode() == "on"
    assert auth_mod.auth_enforced() is True


def test_login_rate_limit_429_after_five_failures(client_auth):
    """B-2: 6º intento fallido en 60s desde la misma IP -> 429 + Retry-After."""
    codes = []
    for _ in range(5):
        codes.append(client_auth.post("/api/v1/auth/login",
                                      json={"password": "bad"}).status_code)
    assert codes == [401] * 5
    r = client_auth.post("/api/v1/auth/login", json={"password": "bad"})
    assert r.status_code == 429
    assert int(r.headers.get("retry-after", "0")) > 0


def test_login_non_ascii_password_is_401_not_500(client_auth):
    """B-2: compare_digest sobre str no-ASCII lanzaba TypeError -> 500."""
    r = client_auth.post("/api/v1/auth/login", json={"password": "contraseña-ñ"})
    assert r.status_code == 401
    r = client_auth.post("/api/v1/auth/login", json={"password": "pässwörd"})
    assert r.status_code == 401


def test_hashed_password_accepted_and_wrong_rejected(monkeypatch):
    """B-2: ADMIN_PASSWORD admite pbkdf2_sha256$iter$salt$hash."""
    hashed = auth_mod.hash_password("s3cret-admin", iterations=1000)
    assert hashed.startswith("pbkdf2_sha256$")
    monkeypatch.setenv("ADMIN_PASSWORD", hashed)
    monkeypatch.setenv("QZERO_AUTH_SECRET", "test-signing-secret")
    auth_mod.reset_login_limits()
    c = TestClient(app)
    assert c.post("/api/v1/auth/login",
                  json={"password": "s3cret-admin"}).status_code == 200
    assert c.post("/api/v1/auth/login",
                  json={"password": "nope"}).status_code == 401


def test_plaintext_password_still_supported(monkeypatch):
    """B-2: compatibilidad — un ADMIN_PASSWORD sin formato hash es claro."""
    assert auth_mod.verify_password("plain-pw", "plain-pw") is True
    assert auth_mod.verify_password("wrong", "plain-pw") is False


def test_ingest_requires_agent_token_when_configured(client_auth, monkeypatch):
    """B-3: si QZERO_AGENT_TOKEN está definido se exige SIEMPRE, aunque
    QZERO_REQUIRE_AGENT_TOKEN esté a 0/ausente (antes: ingest abierto)."""
    monkeypatch.setenv("QZERO_AGENT_TOKEN", "tok-agente")
    monkeypatch.delenv("QZERO_REQUIRE_AGENT_TOKEN", raising=False)
    r = client_auth.post("/api/v1/agents/fase0-agent/alerts",
                         json={"alerts": []})
    assert r.status_code == 401
    r = client_auth.post("/api/v1/agents/fase0-agent/alerts",
                         json={"alerts": []},
                         headers={"X-Agent-Token": "tok-agente"})
    assert r.status_code == 200


def test_agent_token_flag_without_token_is_503(client_auth, monkeypatch):
    """B-3: flag activo sin QZERO_AGENT_TOKEN -> 503 (no fail-open)."""
    monkeypatch.setenv("QZERO_REQUIRE_AGENT_TOKEN", "1")
    monkeypatch.delenv("QZERO_AGENT_TOKEN", raising=False)
    r = client_auth.post("/api/v1/agents/fase0-agent/heartbeat", json={})
    assert r.status_code == 503
