"""Observabilidad: envío de errores a BugSink (protocolo Sentry).

BugSink expone DSN estilo Sentry, así que basta `sentry-sdk`. Este módulo:

- no hace nada si `BUGSINK_DSN` está vacío (dev/local sin tracker),
- filtra eventos ruidosos (desconexiones de cliente, timeouts de socket),
- etiqueta el entorno con `APP_ENV` para separar dev de prod en el mismo
  proyecto y poder filtrar por `environment`.

El DSN se inyecta por entorno; nunca se versiona (lleva la clave pública del
proyecto, que permite inyectar eventos falsos).

Uso:

    from qzero.api.observability import init_sentry

    init_sentry()                      # una sola vez, al arrancar
    sentry_capture(exc)                # en hilos/callbacks que se tragan errores
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("qzero.observability")

_initialized = False

# Errores que NO son fallos nuestros: clientes que cortan la conexión, sondas
# que piden hosts que no servimos. Sin este filtro el tracker se llena de ruido
# y los errores reales se pierden entre él.
_RUIDO = {
    "DisallowedHost",
    "ClientDisconnected",
    "ConnectionResetError",
    "BrokenPipeError",
    "asyncio.CancelledError",
    "CancelledError",
}


def _ignorar(event, hint):  # pragma: no cover - lo ejecuta el SDK
    """Descarta errores que no son fallos del producto."""
    exc = hint.get("exc_info")
    if exc:
        nombre = exc[0].__name__
        if nombre in _RUIDO:
            return None
    return event


def init_sentry(dsn: str | None = None, environment: str | None = None) -> bool:
    """Inicializa el SDK una sola vez. Devuelve si quedó activo."""
    global _initialized
    if _initialized:
        return True

    dsn = (dsn if dsn is not None else os.environ.get("BUGSINK_DSN", "")).strip()
    if not dsn:
        log.info("BugSink desactivado (BUGSINK_DSN vacío)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ImportError:  # pragma: no cover - dependencia opcional en local
        log.warning("sentry-sdk no instalado: BugSink desactivado")
        return False

    env = (environment or os.environ.get("APP_ENV") or "dev").strip()
    release = (os.environ.get("QZERO_RELEASE") or "").strip() or None

    # El agente corre fuera de FastAPI y no necesita esa integración; la API sí.
    # Se decide por la pinta del stack: si uvicorn está corriendo, hay app ASGI.
    integrations = []
    try:
        integrations.append(FastApiIntegration())
    except Exception:  # pragma: no cover - nunca debe tumbar el arranque
        pass

    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        release=release,
        # Solo errores: las trazas de rendimiento se facturan aparte y aquí no
        # se usan. Sin datos personales por defecto.
        traces_sample_rate=0.0,
        send_default_pii=False,
        before_send=_ignorar,
        integrations=integrations,
    )
    _initialized = True
    log.info("BugSink activo (environment=%s)", env)
    return True


def sentry_capture(exc: BaseException, **scope) -> None:
    """Reporta una excepción capturada.

    Necesario en los sitios que se tragan la excepción y solo la escriben al
    log: el loop de mantenimiento, los hilos del agente, los callbacks. Sin
    esto, un fallo ahí nunca llega al tracker.
    """
    if not _initialized:
        return
    try:
        import sentry_sdk

        # `isolation_scope` (SDK 2.x) en vez de `push_scope`, que está
        # deprecado: aísla los extras de esta captura sin contaminar el scope
        # global del proceso.
        with sentry_sdk.isolation_scope() as s:
            for k, v in scope.items():
                s.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
        sentry_sdk.flush(timeout=2.0)
    except Exception:  # pragma: no cover - el tracker nunca debe tumbar la app
        log.warning("No se pudo reportar la excepción a BugSink", exc_info=True)


def is_enabled() -> bool:
    """¿Está el tracker activo? Útil en /health y en los tests."""
    return _initialized
