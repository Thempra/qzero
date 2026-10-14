"""
QZero Hito 3.7 — auth a nivel de aplicación del hub.

Contrato (docs/backend-schema.md §2):
  * ``POST /api/v1/auth/login`` con ``ADMIN_PASSWORD`` (env, **fail-closed**:
    sin password configurada las rutas protegidas devuelven 503, nunca open).
  * Token SPA "JWT-lite": header+payload base64url firmados con HMAC-SHA256,
    con ``exp`` y ``token_version``. Cambiar ``QZERO_AUTH_TOKEN_VERSION``
    revoca TODOS los tokens emitidos (los clientes vuelven a loguearse).
  * Middleware: protege ``/api/v1/*`` (rutas de consulta del hub) y la API
    clásica de control/consulta. NO protege ``/health`` (healthcheck del
    contenedor) ni el ingest de agentes (POST alerts/heartbeat), que usa
    ``X-Agent-Token`` opcional vía ``QZERO_REQUIRE_AGENT_TOKEN``.
  * Nunca Basic Auth de nginx — la auth vive en la app.

Sin dependencias externas (stdlib: hmac/hashlib/base64/secrets), firma
equivalente a un JWS HS256 pero sin importar python-jose/PyJWT.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

logger = logging.getLogger(__name__)

# TTL por defecto del token SPA: 12 h (sesión de consola de un turno).
DEFAULT_TTL_SECONDS = 12 * 3600

# Secrearia de firma del proceso: env QZERO_AUTH_SECRET, o aleatoria por
# arranque (los tokens se invalidan al reiniciar — los operadores vuelven a
# loguearse; mejor que derivar la firma del password y exponerla al offline).
_PROCESS_SECRET: bytes | None = None

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in _TRUE_VALUES


def admin_password() -> str:
    """ADMIN_PASSWORD env, vacío = auth sin configurar (fail-closed)."""
    return os.environ.get("ADMIN_PASSWORD", "")


def auth_enabled() -> bool:
    return bool(admin_password())


def agent_token_required() -> bool:
    """QZERO_REQUIRE_AGENT_TOKEN=1 exige X-Agent-Token en el ingest."""
    return _truthy(os.environ.get("QZERO_REQUIRE_AGENT_TOKEN"))


def agent_token() -> str:
    return os.environ.get("QZERO_AGENT_TOKEN", "")


def token_version() -> str:
    return os.environ.get("QZERO_AUTH_TOKEN_VERSION", "1")


def _signing_key() -> bytes:
    global _PROCESS_SECRET
    secret = os.environ.get("QZERO_AUTH_SECRET", "")
    if secret:
        return secret.encode("utf-8")
    if _PROCESS_SECRET is None:
        _PROCESS_SECRET = secrets.token_bytes(32)
        logger.warning(
            "QZERO_AUTH_SECRET no configurada: usando firma aleatoria por "
            "proceso — los tokens SPA se invalidan al reiniciar la API."
        )
    return _PROCESS_SECRET


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _sign(signing_input: bytes) -> bytes:
    return hmac.new(_signing_key(), signing_input, hashlib.sha256).digest()


def issue_token(subject: str = "admin",
                ttl_seconds: int = DEFAULT_TTL_SECONDS) -> tuple[str, int]:
    """Emite el token SPA. Devuelve (token, caducidad_epoch)."""
    now = int(time.time())
    expires_at = now + int(ttl_seconds)
    header = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"},
                              separators=(",", ":")).encode())
    payload = _b64e(json.dumps(
        {"sub": subject, "iat": now, "exp": expires_at,
         "ver": token_version()},
        separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    token = f"{header}.{payload}.{_b64e(_sign(signing_input))}"
    return token, expires_at


def verify_token(token: str | None) -> bool:
    """Constant-time: firma válida, sin caducar, token_version actual."""
    if not token:
        return False
    parts = token.split(".")
    if len(parts) != 3:
        return False
    header_b64, payload_b64, sig_b64 = parts
    try:
        expected = _sign(f"{header_b64}.{payload_b64}".encode("ascii"))
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            return False
        payload = json.loads(_b64d(payload_b64))
    except Exception:  # noqa: BLE001 — token malformado = inválido
        return False
    if int(payload.get("exp", 0)) < int(time.time()):
        return False
    if str(payload.get("ver", "")) != token_version():
        return False
    return True


def check_agent_token(header_value: str | None) -> bool:
    """X-Agent-Token exige además QZERO_AGENT_TOKEN (fail-closed)."""
    required = agent_token()
    if not required:
        logger.warning(
            "QZERO_REQUIRE_AGENT_TOKEN activo sin QZERO_AGENT_TOKEN: "
            "ingest rechazado (fail-closed).")
        return False
    return bool(header_value) and hmac.compare_digest(header_value, required)


def login(password: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict | None:
    """Comprueba ADMIN_PASSWORD (constant-time) y emite el token SPA.

    Devuelve None si credenciales inválidas o auth sin configurar
    (fail-closed: sin ADMIN_PASSWORD no se emiten tokens).
    """
    configured = admin_password()
    if not configured:
        logger.warning("Login intentado sin ADMIN_PASSWORD configurada (503).")
        return None
    if not isinstance(password, str) or not hmac.compare_digest(
            password, configured):
        return None
    token, expires_at = issue_token(ttl_seconds=ttl_seconds)
    logger.info("Login OK (token_version=%s)", token_version())
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "expires_in": ttl_seconds,
        "token_version": token_version(),
    }


def auth_status() -> dict:
    """Estado público de la auth para clientes (login, dashboard)."""
    return {
        "auth_required": auth_enabled(),
        "agent_token_required": agent_token_required(),
    }
