"""
QZero Hito 3.7 — auth a nivel de aplicación del hub.

Contrato (docs/backend-schema.md §2):
  * ``POST /api/v1/auth/login`` con ``ADMIN_PASSWORD`` (env, **fail-closed**:
    sin password configurada las rutas protegidas devuelven 503, nunca open).
    El modo se controla con ``QZERO_AUTH_ENFORCE`` (1/0); si no está definido
    el default es fail-closed (ver ``auth_enforced()``).
  * ``ADMIN_PASSWORD`` admite claro (compatibilidad) o hash
    ``pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>`` (``hash_password()``).
  * Rate limit del login en memoria por IP: máx. 5 fallos / 60 s -> 429.
  * ``QZERO_AGENT_TOKEN`` definido => el ingest exige ``X-Agent-Token``
    siempre (``QZERO_REQUIRE_AGENT_TOKEN`` solo añade el 503 si falta token).
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
import re
import secrets
import sys
import threading
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
    """ADMIN_PASSWORD env (claro o ``pbkdf2_sha256$...``), vacío = sin configurar."""
    return os.environ.get("ADMIN_PASSWORD", "")


def auth_enabled() -> bool:
    return bool(admin_password())


# ── Modo de enforcement (Fase 0.1) ──────────────────────────────────────────
# Criterio de seguridad: un despliegue sin ADMIN_PASSWORD devuelve 503.
#   QZERO_AUTH_ENFORCE=1 (o sin definir) -> fail-closed. Es el default DURO.
#   QZERO_AUTH_ENFORCE=0                 -> sin enforcement. SOLO para la
#                                           suite de tests, que declara este
#                                           opt-out en tests/conftest.py.
# El código de producción NO inspecciona sys.modules ni detecta runners: un
# backdoor que se abre solo porque algo importó pytest es un fallo de
# seguridad, no una comodidad. (Una versión anterior de este parche hacía
# exactamente eso; se retiró.)

def auth_enforced() -> bool:
    raw = os.environ.get("QZERO_AUTH_ENFORCE")
    if raw is not None and raw.strip() != "":
        return _truthy(raw)
    return True  # fail-closed por defecto, sin excepciones


def auth_enforce_mode() -> str:
    """"on" | "off" — modo efectivo, para /api/v1/auth/status y logs."""
    return "on" if auth_enforced() else "off"


# ── Contraseñas: soporte de hash PBKDF2 (Fase 0.2) ──────────────────────────
PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
_HASH_RE = re.compile(r"^pbkdf2_sha256\$(\d+)\$([A-Za-z0-9_\-=]+)\$([A-Za-z0-9_\-=]+)$")


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS,
                  salt: bytes | None = None) -> str:
    """Devuelve ``pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>`` (stdlib)."""
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 salt, int(iterations))
    return f"{PBKDF2_PREFIX}${int(iterations)}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, configured: str) -> bool:
    """Constant-time. Acepta hash pbkdf2 o, por compatibilidad, claro.

    Codifica a UTF-8 antes de compare_digest: comparar ``str`` no-ASCII
    lanzaba TypeError (500 en el login).
    """
    if not isinstance(password, str) or not isinstance(configured, str):
        return False
    match = _HASH_RE.match(configured)
    if match:
        iterations, salt_b64, hash_b64 = match.groups()
        try:
            expected = _b64d(hash_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                         _b64d(salt_b64), int(iterations))
        except (ValueError, TypeError):
            logger.warning("ADMIN_PASSWORD con formato de hash inválido.")
            return False
        return hmac.compare_digest(actual, expected)
    return hmac.compare_digest(password.encode("utf-8"),
                               configured.encode("utf-8"))


# ── Rate limit del login (Fase 0.2) ─────────────────────────────────────────
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60

_login_failures: dict[str, list[float]] = {}
_login_lock = threading.Lock()


def reset_login_limits() -> None:
    """Limpia el estado del rate limiter (tests / reinicio de credenciales)."""
    with _login_lock:
        _login_failures.clear()


def login_retry_after(client_ip: str) -> int:
    """Segundos de bloqueo restantes para esa IP (0 = permitido)."""
    now = time.time()
    with _login_lock:
        stamps = [t for t in _login_failures.get(client_ip, [])
                  if now - t < LOGIN_WINDOW_SECONDS]
        if stamps:
            _login_failures[client_ip] = stamps
        else:
            _login_failures.pop(client_ip, None)
        if len(stamps) < LOGIN_MAX_ATTEMPTS:
            return 0
        return max(1, int(LOGIN_WINDOW_SECONDS - (now - stamps[0])) + 1)


def register_login_failure(client_ip: str) -> None:
    """Anota un fallo de login para esa IP (ventana deslizante de 60 s)."""
    now = time.time()
    with _login_lock:
        stamps = [t for t in _login_failures.get(client_ip, [])
                  if now - t < LOGIN_WINDOW_SECONDS]
        stamps.append(now)
        _login_failures[client_ip] = stamps


def agent_token_required() -> bool:
    """True si el ingest debe autenticarse.

    Fase 0.3: basta con que ``QZERO_AGENT_TOKEN`` esté definido — el token se
    exige SIEMPRE y el flag ``QZERO_REQUIRE_AGENT_TOKEN=1`` solo añade el 503
    cuando falta el token (un flag a 0 no puede desactivar la exigencia).
    """
    if os.environ.get("QZERO_AGENT_TOKEN"):
        return True
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
    if not header_value:
        return False
    return hmac.compare_digest(header_value.encode("utf-8"),
                               required.encode("utf-8"))


def login(password: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> dict | None:
    """Comprueba ADMIN_PASSWORD (constant-time) y emite el token SPA.

    Devuelve None si credenciales inválidas o auth sin configurar
    (fail-closed: sin ADMIN_PASSWORD no se emiten tokens). El rate limit por
    IP se aplica en el endpoint (``login_retry_after``), que es donde se
    conoce la IP del cliente.
    """
    configured = admin_password()
    if not configured:
        logger.warning("Login intentado sin ADMIN_PASSWORD configurada (503).")
        return None
    if not verify_password(password, configured):
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
        "auth_enforced": auth_enforced(),
    }


if __name__ == "__main__":  # pragma: no cover - utilidad de operador
    # python -m qzero.api.auth "<password>"  -> ADMIN_PASSWORD=pbkdf2_sha256$...
    import getpass

    _pw = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("password: ")
    print(hash_password(_pw))
