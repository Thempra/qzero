"""Tests de intel.py: caché de enriquecimiento sin tocar la red.

El valor de este módulo es justo lo contrario de lo que parece: no llamar a
ipinfo.io. Si la caché falla, cada render de alerta dispara una petición
externa y el dashboard se arrastra. Por eso casi todo lo que se prueba aquí
es "no se llama a la red".
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from qzero.api import intel


@pytest.mark.parametrize("ip", ["10.0.0.1", "192.168.1.5", "127.0.0.1",
                                "172.16.4.4", "no-es-ip", ""])
def test_private_o_basura_nunca_sale_a_la_red(ip, monkeypatch):
    def _boom(*a, **k):
        raise AssertionError(f"salió a la red con {ip!r}")

    monkeypatch.setattr(intel.urllib.request, "urlopen", _boom)
    assert intel.is_private_ip(ip) is True


def test_ip_publica_se_reconoce(monkeypatch):
    assert intel.is_private_ip("8.8.8.8") is False


class _HubFalso:
    def __init__(self, fila=None):
        self.fila = fila
        self.escritos = []

    def get_ip_intel(self, ip):
        return self.fila or {}

    def put_ip_intel(self, ip, **kw):
        self.escritos.append((ip, kw))


def test_cache_fresca_no_consulta_ni_escribe(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("no debe consultar con caché fresca")

    monkeypatch.setattr(intel.urllib.request, "urlopen", _boom)
    hub = _HubFalso({"ip": "8.8.8.8", "org": "Google", "asn": "AS15169",
                     "country": "US", "anycast": False,
                     "fetched_at": datetime.now().isoformat()})
    d = intel.enrich_ip(hub, "8.8.8.8")
    assert d["cached"] is True
    assert d["org"] == "Google"
    assert hub.escritos == []


def test_cache_caducada_refresca(monkeypatch):
    viejo = (datetime.now() - timedelta(days=intel.CACHE_TTL_DAYS + 1)).isoformat()
    hub = _HubFalso({"ip": "8.8.8.8", "org": "Viejo", "asn": "AS0",
                     "country": "US", "anycast": False, "fetched_at": viejo})
    monkeypatch.setattr(intel, "lookup_upstream",
                        lambda ip: {"org": "Nuevo", "asn": "AS1",
                                    "country": "ES", "anycast": False})
    d = intel.enrich_ip(hub, "8.8.8.8")
    assert d["cached"] is False
    assert d["org"] == "Nuevo"
    assert hub.escritos and hub.escritos[0][1]["org"] == "Nuevo"


def test_sin_cache_consulta_y_guarda(monkeypatch):
    hub = _HubFalso()
    monkeypatch.setattr(intel, "lookup_upstream",
                        lambda ip: {"org": "X", "asn": "AS2",
                                    "country": "DE", "anycast": True})
    d = intel.enrich_ip(hub, "1.1.1.1")
    assert d["cached"] is False and d["anycast"] is True
    assert hub.escritos[0][0] == "1.1.1.1"


def test_privada_devuelve_stub_lan_sin_cache(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("no red para privadas")

    monkeypatch.setattr(intel.urllib.request, "urlopen", _boom)
    hub = _HubFalso()
    d = intel.enrich_ip(hub, "10.1.2.3")
    assert d["org"] == "LAN" and d["asn"] == "PRIVATE"
    assert hub.escritos == []


def test_lookup_upstream_ipinfo_con_org(monkeypatch):
    class _R:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"org":"AS15169 Google LLC","country":"US"}'

    monkeypatch.setattr(intel.urllib.request, "urlopen", lambda *a, **k: _R())
    d = intel.lookup_upstream("8.8.8.8")
    assert d["asn"] == "AS15169"
    assert d["org"] == "Google LLC"


def test_lookup_upstream_degrada_a_vacio(monkeypatch):
    def _urlopen(*a, **k):
        raise OSError("sin red")

    monkeypatch.setattr(intel.urllib.request, "urlopen", _urlopen)
    d = intel.lookup_upstream("8.8.8.8")
    assert d == {"org": "", "asn": "", "country": "", "anycast": False}


def test_fresh_con_fecha_basura_es_caducada():
    assert intel._fresh("basura") is False
    assert intel._fresh("") is False
