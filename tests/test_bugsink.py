"""Tests del enganche con BugSink (protocolo Sentry).

Lo que se comprueba, y por qué:

1. **Sin DSN no se activa nada.** En local y en los tests no debe salir ni un
   evento: si el SDK arrancara sin DSN, cada `pytest` intentaría hablar con
   un host externo.
2. **Con DSN se activa.** Es el caso real en producción.
3. **El envío de errores no rompe la app.** `sentry_capture` hace `flush()` y
   puede lanzar si el host no responde; el tracker jamás debe tumbar el
   proceso que intenta reportar.
4. **El 500 pasa por el handler y devuelve JSON**, no una traza HTML, y el
   evento llega al tracker con la ruta como extra.
"""
from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def obs():
    """Módulo de observabilidad limpio (sin estado de inicializaciones)."""
    import qzero.api.observability as m

    importlib.reload(m)
    yield m
    importlib.reload(m)


def test_disabled_when_dsn_empty(obs, monkeypatch):
    monkeypatch.delenv("BUGSINK_DSN", raising=False)
    assert obs.init_sentry() is False
    assert obs.is_enabled() is False


def test_dsn_whitespace_only_counts_as_empty(obs, monkeypatch):
    """Un DSN con solo espacios (env mal puesto) no debe activar el SDK."""
    monkeypatch.setenv("BUGSINK_DSN", "   ")
    assert obs.init_sentry() is False


def test_capture_is_noop_when_disabled(obs, monkeypatch):
    """Sin tracker activo, `sentry_capture` no debe ni importar el SDK."""
    monkeypatch.delenv("BUGSINK_DSN", raising=False)
    obs.init_sentry()
    # No debe lanzar aunque le pasemos una excepción cualquiera.
    obs.sentry_capture(ValueError("boom"), task="test")


def test_capture_swallows_sdk_errors(obs, monkeypatch):
    """Si el envío falla, `sentry_capture` no propaga la excepción."""
    monkeypatch.delenv("BUGSINK_DSN", raising=False)
    obs.init_sentry()
    obs._initialized = True  # forzamos "activo" sin DSN real

    def _explode(*a, **kw):
        raise RuntimeError("tracker caído")

    monkeypatch.setattr(obs, "sentry_capture", obs.sentry_capture)
    # El import dentro de la función es el que fallaría; lo simulamos
    # rompiendo `sentry_sdk.capture_exception`.
    sentry_sdk = pytest.importorskip("sentry_sdk")
    monkeypatch.setattr(sentry_sdk, "capture_exception", _explode)

    obs.sentry_capture(ValueError("boom"))  # no debe lanzar


def test_unhandled_exception_returns_json_500(monkeypatch):
    """El handler global devuelve 500 JSON y reporta el error."""
    # `qzero/api/__init__.py` re-exporta la instancia `app`, así que
    # `import qzero.api.app as m` devuelve el objeto FastAPI, no el módulo.
    import sys
    import qzero.api.app

    app_mod = sys.modules["qzero.api.app"]

    capturado = {}

    def _capture(exc, **scope):
        capturado["exc"] = exc
        capturado.update(scope)

    monkeypatch.setattr(app_mod, "sentry_capture", _capture)

    @app_mod.app.get("/__boom_test")
    async def _boom():
        raise RuntimeError("fallo simulado")

    try:
        with TestClient(app_mod.app, raise_server_exceptions=False) as c:
            r = c.get("/__boom_test")
        assert r.status_code == 500
        assert r.json() == {"detail": "internal server error"}
        assert isinstance(capturado.get("exc"), RuntimeError)
        assert capturado.get("path") == "/__boom_test"
        assert capturado.get("method") == "GET"
    finally:
        app_mod.app.router.routes = [
            rt for rt in app_mod.app.router.routes
            if getattr(rt, "path", None) != "/__boom_test"
        ]


def test_background_task_failure_is_reported(monkeypatch):
    """Si el mantenimiento muere, el callback lo reporta al tracker.

    Sin esto, la tarea termina con 'Task exception was never retrieved' y el
    hub se queda sin retención ni avisos, aparentemente sano.
    """
    import asyncio

    # `qzero/api/__init__.py` re-exporta la instancia `app`, así que
    # `import qzero.api.app as m` devuelve el objeto FastAPI, no el módulo.
    import sys
    import qzero.api.app

    app_mod = sys.modules["qzero.api.app"]

    reportado = {}
    monkeypatch.setattr(
        app_mod, "sentry_capture",
        lambda exc, **scope: reportado.update({"exc": exc, **scope}))

    async def _escenario():
        async def _muere():
            raise RuntimeError("mantenimiento roto")

        task = asyncio.create_task(_muere())
        app_mod._BACKGROUND_TASKS.add(task)
        task.add_done_callback(app_mod._on_background_done)
        with pytest.raises(RuntimeError):
            await task
        await asyncio.sleep(0)  # deja correr el callback

    asyncio.run(_escenario())
    assert isinstance(reportado.get("exc"), RuntimeError)
    assert reportado.get("task") == "maintenance_loop"


def test_background_task_cancel_is_not_reported(monkeypatch):
    """Cancelar al apagar NO es un error: no debe ensuciar el tracker."""
    import asyncio

    # `qzero/api/__init__.py` re-exporta la instancia `app`, así que
    # `import qzero.api.app as m` devuelve el objeto FastAPI, no el módulo.
    import sys
    import qzero.api.app

    app_mod = sys.modules["qzero.api.app"]

    reportado = []
    monkeypatch.setattr(
        app_mod, "sentry_capture",
        lambda exc, **scope: reportado.append(exc))

    async def _escenario():
        async def _duerme():
            await asyncio.sleep(3600)

        task = asyncio.create_task(_duerme())
        app_mod._BACKGROUND_TASKS.add(task)
        task.add_done_callback(app_mod._on_background_done)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)

    asyncio.run(_escenario())
    assert reportado == []
