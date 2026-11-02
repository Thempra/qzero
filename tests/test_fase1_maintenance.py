"""Tests de maintenance.py: digest, Telegram y el bucle de mantenimiento.

Cubren lo que el gate de Sonar mide y lo que de verdad rompe en producción:
que un fallo de Telegram no tumbe el hub, que el digest no mienta y que el
bucle purgue/no purgue según la configuración.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from qzero.api import maintenance as m


# --------------------------------------------------------------- send_telegram


def test_send_telegram_sin_config_no_intenta_red(monkeypatch):
    monkeypatch.delenv("QZERO_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("QZERO_TELEGRAM_CHAT_ID", raising=False)

    def _boom(*a, **k):
        raise AssertionError("no debe tocar la red sin configurar")

    monkeypatch.setattr(m.urllib.request, "urlopen", _boom)
    assert m.send_telegram("hola") is False


def test_send_telegram_ok_sin_tocar_la_red_real(monkeypatch):
    monkeypatch.setenv("QZERO_TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("QZERO_TELEGRAM_CHAT_ID", "42")
    capturado = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _urlopen(req, timeout=10):
        capturado["url"] = req.full_url
        capturado["body"] = json.loads(req.data.decode())
        return _Resp()

    monkeypatch.setattr(m.urllib.request, "urlopen", _urlopen)
    assert m.send_telegram("aviso") is True
    assert capturado["url"].endswith("/bott/sendMessage")
    assert capturado["body"]["chat_id"] == "42"
    assert capturado["body"]["text"] == "aviso"


def test_send_telegram_traga_errores(monkeypatch):
    """Un Telegram caído no puede propagar: el hub seguiría sin digest."""
    monkeypatch.setenv("QZERO_TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("QZERO_TELEGRAM_CHAT_ID", "42")

    def _urlopen(*a, **k):
        raise OSError("caído")

    monkeypatch.setattr(m.urllib.request, "urlopen", _urlopen)
    assert m.send_telegram("aviso") is False


def test_send_telegram_status_no_2xx_es_fallo(monkeypatch):
    monkeypatch.setenv("QZERO_TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("QZERO_TELEGRAM_CHAT_ID", "42")

    class _Resp:
        status = 500

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert m.send_telegram("aviso") is False


# ----------------------------------------------------------- build_critical_digest


def test_digest_cuenta_todas_pero_lista_diez():
    alertas = [
        {"agent_name": "a", "src": "1.1.1.1", "dst": "2.2.2.2", "dst_port": 80,
         "protocol": "TCP"}
        for _ in range(23)
    ]
    texto = m.build_critical_digest(alertas)
    assert "23 alerta(s) CRITICAL" in texto
    assert texto.count("•") == 10
    assert "y 13 más" in texto


def test_digest_cae_a_agent_id_y_a_interrogantes():
    texto = m.build_critical_digest([{"agent_id": "sin-nombre"}])
    assert "sin-nombre" in texto
    assert "?" in texto


def test_digest_vacio_no_revienta():
    assert "0 alerta(s)" in m.build_critical_digest([])


# ------------------------------------------------------------------ _parse_ts


@pytest.mark.parametrize("valor", ["", "no-es-fecha", None, 12345])
def test_parse_ts_devuelve_none_en_basura(valor):
    assert m._parse_ts(valor) is None


def test_parse_ts_acepta_naive_y_aware():
    assert m._parse_ts("2026-01-01T10:00:00") is not None
    assert m._parse_ts("2026-01-01T10:00:00+00:00") is not None


# --------------------------------------------------------------- maintenance_loop


class _HubFalso:
    def __init__(self, agents=None, criticos=None, falla_purge=False):
        self.purges = []
        self.marked = []
        self.agents = agents or []
        self.criticos = criticos or []
        self.falla_purge = falla_purge

    def purge_old_alerts(self, dias):
        self.purges.append(dias)
        if self.falla_purge:
            raise RuntimeError("db bloqueada")
        return 3

    def pop_pending_criticals(self):
        return self.criticos

    def mark_criticals_notified(self, ids):
        self.marked.extend(ids)

    def list_agents(self):
        return self.agents


def _correr_un_tick(hub, monkeypatch, env=None):
    """Ejecuta maintenance_loop hasta el primer sleep y lo cancela."""
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)

    async def _main():
        task = asyncio.create_task(m.maintenance_loop(hub))
        await asyncio.sleep(1.2)  # el bucle duerme scan_sec antes del 1er tick
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_main())


def test_loop_purga_con_retencion_configurada(monkeypatch):
    hub = _HubFalso()
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_ALERT_RETENTION_DAYS": "30",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_RETENTION_INTERVAL_SEC": "1",
    })
    assert hub.purges == [30]


def test_loop_no_purga_si_retencion_es_cero(monkeypatch):
    hub = _HubFalso()
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_ALERT_RETENTION_DAYS": "0",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_RETENTION_INTERVAL_SEC": "1",
    })
    assert hub.purges == []


def test_loop_sobrevive_a_purga_que_falla(monkeypatch):
    """Una excepción de SQLite no puede matar el único task de mantenimiento."""
    hub = _HubFalso(falla_purge=True)
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_ALERT_RETENTION_DAYS": "30",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_RETENTION_INTERVAL_SEC": "1",
    })
    assert hub.purges == [30]  # lo intentó


def test_loop_envia_digest_y_marca_solo_lo_entregado(monkeypatch):
    hub = _HubFalso(criticos=[
        {"id": 1, "agent_name": "a", "src": "1.1.1.1", "dst": "2.2.2.2",
         "dst_port": 80, "protocol": "TCP"},
        {"id": 2, "agent_name": "b", "src": "3.3.3.3", "dst": "4.4.4.4",
         "dst_port": 443, "protocol": "TCP"},
    ])
    monkeypatch.setattr(m, "send_telegram", lambda texto: True)
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_TELEGRAM_BOT_TOKEN": "t",
        "QZERO_TELEGRAM_CHAT_ID": "1",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_ALERT_RETENTION_DAYS": "0",
    })
    assert hub.marked == [1, 2]


def test_loop_no_marca_nada_si_telegram_falla(monkeypatch):
    """El bug viejo: marcar por severidad perdía alertas no entregadas."""
    hub = _HubFalso(criticos=[{"id": 7, "agent_name": "a"}])
    monkeypatch.setattr(m, "send_telegram", lambda texto: False)
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_TELEGRAM_BOT_TOKEN": "t",
        "QZERO_TELEGRAM_CHAT_ID": "1",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_ALERT_RETENTION_DAYS": "0",
    })
    assert hub.marked == []


def test_loop_avisa_una_vez_de_agente_caido(monkeypatch):
    viejo = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
    hub = _HubFalso(agents=[{"agent_id": "caido", "agent_name": "Caido",
                             "last_seen": viejo}])
    avisos = []
    monkeypatch.setattr(m, "send_telegram", lambda texto: avisos.append(texto))
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_AGENT_OFFLINE_MIN": "5",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_ALERT_RETENTION_DAYS": "0",
    })
    assert len(avisos) == 1
    assert "sin heartbeat" in avisos[0]


def test_loop_avisa_vuelta_tras_recuperacion(monkeypatch):
    """Recuperado tras haber avisado: manda un único 'de vuelta'."""
    hub = _HubFalso(agents=[{"agent_id": "a1", "last_seen": "basura"}])
    monkeypatch.setattr(m, "send_telegram", lambda texto: True)
    # Sin last_seen parseable se ignora: no debe avisar.
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_AGENT_OFFLINE_MIN": "5",
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_ALERT_RETENTION_DAYS": "0",
    })
    assert hub.purges == []


def test_loop_sobrevive_si_list_agents_falla(monkeypatch):
    class _HubRoto(_HubFalso):
        def list_agents(self):
            raise RuntimeError("tabla corrupta")

    hub = _HubRoto()
    monkeypatch.setattr(m, "send_telegram", lambda texto: True)
    _correr_un_tick(hub, monkeypatch, {
        "QZERO_MAINT_INTERVAL_SEC": "1",
        "QZERO_ALERT_RETENTION_DAYS": "0",
    })
    assert isinstance(hub, _HubRoto)
