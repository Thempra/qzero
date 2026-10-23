"""Fase 1.1 / 1.2 — flujos agregados (5-tupla) y estado de flujo.

Cubre:
  * GET  /api/v1/flows            — agregación por (src,dst,dst_port,protocol)
  * PATCH /api/v1/flows/{key}/state — triaje ('nuevo'|'investigando'|'benigno'|'malicioso')

Los tests usan una HubStore temporal por test y la inyectan en el singleton del
módulo (``qzero.api.hub.hub_store``), de modo que la app resuelve el store en
cada petición. No se toca data/hub.db.

El test de auth corre un intérprete LIMPIO (subprocess) porque tests/conftest.py
declara QZERO_AUTH_ENFORCE=0 para el resto de la suite: el punto es demostrar
que en un despliegue real (sin ADMIN_PASSWORD) las rutas nuevas dan 503, igual
que /api/v1/alerts.
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import qzero.api.hub as hub_mod
from qzero.api.hub import HubStore, flow_key
from qzero.api.app import app

REPO = Path(__file__).resolve().parents[1]


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture()
def store(tmp_path, monkeypatch):
    """HubStore aislada, inyectada donde la app la resuelve en runtime."""
    s = HubStore(db_path=tmp_path / "hub.db")
    monkeypatch.setattr(hub_mod, "hub_store", s)
    yield s
    s.close()


@pytest.fixture()
def client(store):
    return TestClient(app)


def _ts(minutes_ago: float = 0.0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _seed(store, src="10.0.0.5", dst="1.2.3.4", dst_port=443, protocol=6,
          scores=(4.5,), severity="HIGH", minutes_ago=1.0, agent="a1",
          step_seconds=1.0, base_ts=None):
    """Siembra un lote de alertas de UN flujo, un score por alerta.

    ``step_seconds`` separa las alertas en el tiempo para que first_seen y
    last_seen no coincidan (así el orden de inserción no altera los extremos).
    ``base_ts`` fija la marca de la alerta más reciente: los tests que comparan
    dos BD necesitan timestamps idénticos, no dos ``now()`` distintos.
    """
    n = len(scores)
    alerts = []
    for i, score in enumerate(scores):
        alerts.append({
            "src": src, "dst": dst, "dst_port": dst_port, "protocol": protocol,
            "src_port": 40000 + i, "severity": severity, "anomaly_score": float(score),
            "timestamp": _ts(minutes_ago + (n - 1 - i) * step_seconds / 60.0),
        })
    if base_ts is not None:
        base = datetime.fromisoformat(base_ts)
        for i, a in enumerate(alerts):
            a["timestamp"] = (
                base - timedelta(seconds=(n - 1 - i) * step_seconds)).isoformat()
    return store.ingest_alert_batch({
        "agent_id": agent, "agent_name": agent, "interface": "eth0",
        "timestamp": alerts[0]["timestamp"], "alerts": alerts,
    })


# ── flow_key: forma canónica ──────────────────────────────────────────────

def test_flow_key_is_canonical_and_order_independent():
    assert flow_key("10.0.0.5", "1.2.3.4", 443, 6) == "10.0.0.5,1.2.3.4,443,6"
    # mismos valores, tipos "de red" (str) -> misma clave
    assert flow_key("10.0.0.5", "1.2.3.4", "443", "6") == "10.0.0.5,1.2.3.4,443,6"
    # IPv6 con ':' no colisiona con el separador ','
    assert flow_key("2001:db8::1", "2001:db8::2", 53, 17) == \
        "2001:db8::1,2001:db8::2,53,17"


def test_same_flow_key_regardless_of_insertion_order(tmp_path):
    """Mismo flujo sembrado en orden inverso -> misma clave y mismas métricas."""
    a = HubStore(db_path=tmp_path / "a.db")
    b = HubStore(db_path=tmp_path / "b.db")
    base = _ts(minutes_ago=5)
    try:
        _seed(a, scores=(4.5, 6.0, 9.5), base_ts=base)
        _seed(b, scores=(9.5, 6.0, 4.5), base_ts=base)
        fa = a.aggregate_flows(minutes=60)["flows"]
        fb = b.aggregate_flows(minutes=60)["flows"]
    finally:
        a.close()
        b.close()
    assert len(fa) == len(fb) == 1
    assert fa[0]["flow_key"] == fb[0]["flow_key"]
    for k in ("count", "score_p50", "score_p99", "score_max", "severity"):
        assert fa[0][k] == fb[0][k], k
    assert fa[0]["first_seen"] == fb[0]["first_seen"]
    assert fa[0]["last_seen"] == fb[0]["last_seen"]


# ── Agregación y percentiles ──────────────────────────────────────────────

def test_flows_aggregation_counts_percentiles_and_extremes(client, store):
    # Un flujo con scores 1..100 (una alerta por segundo, todas dentro de 60').
    _seed(store, scores=tuple(range(1, 101)), severity="HIGH",
          minutes_ago=10, step_seconds=1.0)
    r = client.get("/api/v1/flows", params={"minutes": 60})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["minutes"] == 60
    assert len(body["flows"]) == 1

    f = body["flows"][0]
    assert f["flow_key"] == "10.0.0.5,1.2.3.4,443,6"
    assert (f["src"], f["dst"], f["dst_port"], f["protocol"]) == \
        ("10.0.0.5", "1.2.3.4", 443, 6)
    assert f["count"] == 100
    # nearest-rank a mano: ceil(0.50*100)=50 -> score 50; ceil(0.99*100)=99 -> 99
    assert f["score_p50"] == pytest.approx(50.0)
    assert f["score_p99"] == pytest.approx(99.0)
    assert f["score_max"] == pytest.approx(100.0)
    assert f["severity"] == "HIGH"
    # ventana de 60' con 100 alertas
    assert f["alerts_per_minute"] == pytest.approx(100 / 60, abs=1e-6)
    assert f["first_seen"] < f["last_seen"]


def test_single_alert_percentiles_equal_its_score(client, store):
    _seed(store, scores=(7.5,), severity="MEDIUM")
    f = client.get("/api/v1/flows").json()["flows"][0]
    assert f["count"] == 1
    assert f["score_p50"] == f["score_p99"] == f["score_max"] == pytest.approx(7.5)


def test_severity_max_and_ordering(client, store):
    _seed(store, src="10.0.0.1", scores=(4.4, 4.6), severity="LOW")
    _seed(store, src="10.0.0.2", scores=(50.0,), severity="CRITICAL")
    _seed(store, src="10.0.0.3", scores=(20.0, 30.0), severity="MEDIUM")
    flows = client.get("/api/v1/flows").json()["flows"]
    assert [f["severity"] for f in flows] == ["CRITICAL", "MEDIUM", "LOW"]
    assert [f["src"] for f in flows] == ["10.0.0.2", "10.0.0.3", "10.0.0.1"]


def test_distinct_flows_are_not_merged(client, store):
    # mismo par IP pero distinto puerto/protocolo -> flujos distintos
    _seed(store, dst_port=443, protocol=6, scores=(5.0,))
    _seed(store, dst_port=443, protocol=17, scores=(5.0,))
    _seed(store, dst_port=22, protocol=6, scores=(5.0,))
    keys = sorted(f["flow_key"] for f in client.get("/api/v1/flows").json()["flows"])
    assert keys == ["10.0.0.5,1.2.3.4,22,6", "10.0.0.5,1.2.3.4,443,17",
                    "10.0.0.5,1.2.3.4,443,6"]


# ── Ventana temporal ──────────────────────────────────────────────────────

def test_window_excludes_older_alerts(client, store):
    _seed(store, src="10.0.3.1", scores=(5.0,), minutes_ago=5)      # dentro
    _seed(store, src="10.0.3.2", scores=(5.0,), minutes_ago=120)    # fuera de 60'
    assert len(client.get("/api/v1/flows", params={"minutes": 60}).json()["flows"]) == 1
    assert len(client.get("/api/v1/flows", params={"minutes": 1440}).json()["flows"]) == 2


def test_minutes_is_clamped_to_max_1440(client, store):
    _seed(store, scores=(5.0,), minutes_ago=1500)   # 25 h: fuera incluso de 1440'
    body = client.get("/api/v1/flows", params={"minutes": 99999}).json()
    assert body["minutes"] == 1440
    assert body["flows"] == []


def test_minutes_rejects_zero_and_negative(client, store):
    assert client.get("/api/v1/flows", params={"minutes": 0}).status_code == 422
    assert client.get("/api/v1/flows", params={"minutes": -5}).status_code == 422


# ── limit ─────────────────────────────────────────────────────────────────

def test_limit_caps_at_200_and_flags_more(client, store):
    for i in range(5):
        _seed(store, src=f"10.0.1.{i}", scores=(float(i) + 10.0,), severity="HIGH")
    body = client.get("/api/v1/flows", params={"limit": 2}).json()
    assert body["limit"] == 2
    assert len(body["flows"]) == 2
    assert body["has_more"] is True

    body = client.get("/api/v1/flows", params={"limit": 9999}).json()
    assert body["limit"] == 200            # capado, no 422
    assert len(body["flows"]) == 5         # solo hay 5 flujos
    assert body["has_more"] is False

    assert client.get("/api/v1/flows", params={"limit": 0}).status_code == 422


# ── only_untriaged y estado ───────────────────────────────────────────────

def test_only_untriaged_excludes_marked_flows(client, store):
    _seed(store, src="10.0.2.1", scores=(9.0,), severity="HIGH")
    _seed(store, src="10.0.2.2", scores=(8.0,), severity="HIGH")
    k1 = "10.0.2.1,1.2.3.4,443,6"
    r = client.patch(f"/api/v1/flows/{k1}/state",
                     json={"state": "benigno", "note": "backup nocturno"})
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "benigno"

    all_flows = client.get("/api/v1/flows").json()["flows"]
    assert len(all_flows) == 2
    marked = next(f for f in all_flows if f["flow_key"] == k1)
    assert marked["state"] == "benigno"
    assert marked["note"] == "backup nocturno"

    untriaged = client.get("/api/v1/flows",
                           params={"only_untriaged": "true"}).json()["flows"]
    assert [f["flow_key"] for f in untriaged] == ["10.0.2.2,1.2.3.4,443,6"]


def test_state_nuevo_still_counts_as_untriaged(client, store):
    _seed(store, scores=(9.0,))
    key = "10.0.0.5,1.2.3.4,443,6"
    assert client.patch(f"/api/v1/flows/{key}/state",
                        json={"state": "nuevo"}).status_code == 200
    flows = client.get("/api/v1/flows",
                       params={"only_untriaged": "true"}).json()["flows"]
    assert [f["flow_key"] for f in flows] == [key]


def test_patch_invalid_state_returns_400(client, store):
    _seed(store, scores=(9.0,))
    key = "10.0.0.5,1.2.3.4,443,6"
    r = client.patch(f"/api/v1/flows/{key}/state", json={"state": "descartado"})
    assert r.status_code == 400
    assert "descartado" in r.json()["detail"]
    assert "investigando" in r.json()["detail"]   # lista de permitidos
    # no se ha persistido nada
    assert store.get_flow_state(key) == {}
    # sigue apareciendo en only_untriaged
    assert len(client.get("/api/v1/flows",
                          params={"only_untriaged": "true"}).json()["flows"]) == 1


def test_patch_all_valid_states_and_overwrite(client, store):
    key = "10.0.0.5,1.2.3.4,443,6"
    for state in ("nuevo", "investigando", "benigno", "malicioso"):
        r = client.patch(f"/api/v1/flows/{key}/state", json={"state": state})
        assert r.status_code == 200, (state, r.text)
        assert store.get_flow_state(key)["state"] == state
    # el último gana y updated_at es ISO8601
    st = store.get_flow_state(key)
    datetime.fromisoformat(st["updated_at"])


def test_flow_state_store_roundtrip_and_note_optional(store):
    key = "10.9.9.9,8.8.8.8,53,17"
    assert store.get_flow_state(key) == {}
    store.set_flow_state(key, "investigando")
    st = store.get_flow_state(key)
    assert st["state"] == "investigando"
    assert st["note"] in (None, "")
    store.set_flow_state(key, "malicioso", note="C2 conocido")
    st = store.get_flow_state(key)
    assert (st["state"], st["note"]) == ("malicioso", "C2 conocido")


def test_set_flow_state_rejects_invalid_state(store):
    with pytest.raises(ValueError):
        store.set_flow_state("a,b,1,6", "cerrado")


# ── Auth: las rutas nuevas van detrás del middleware existente ────────────

_AUTH_SCRIPT = """
import os
for k in ("ADMIN_PASSWORD", "QZERO_AGENT_TOKEN", "QZERO_REQUIRE_AGENT_TOKEN"):
    os.environ.pop(k, None)
from fastapi.testclient import TestClient
from qzero.api.app import app
c = TestClient(app)
print("alerts", c.get("/api/v1/alerts").status_code)
print("flows", c.get("/api/v1/flows").status_code)
print("flows_patch", c.patch("/api/v1/flows/10.0.0.5,1.2.3.4,443,6/state",
                             json={"state": "benigno"}).status_code)
print("health", c.get("/health").status_code)
"""


def test_flows_routes_are_behind_auth_middleware():
    """Proceso limpio sin ADMIN_PASSWORD: nuevo = 503 igual que /api/v1/alerts."""
    env = dict(os.environ)
    env.pop("QZERO_AUTH_ENFORCE", None)   # no heredar el opt-out de conftest
    env.pop("PYTEST_CURRENT_TEST", None)
    env["PYTHONPATH"] = str(REPO / "src")
    out = subprocess.run([sys.executable, "-c", _AUTH_SCRIPT], cwd=str(REPO),
                         env=env, capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr[-2000:]
    res = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            res[parts[0]] = int(parts[1])
    assert res["alerts"] == 503
    assert res["flows"] == 503
    assert res["flows_patch"] == 503
    assert res["health"] == 200


def test_python_and_sql_flow_keys_never_diverge(store):
    """flow_key() y _flow_key_sql() deben dar la MISMA cadena en todos los casos.

    Si divergen, el PATCH guarda una clave que el LEFT JOIN del listado no
    encuentra: el analista marca un flujo como benigno y el flujo reaparece en
    la cola de triaje. La cadena vacía era el caso roto (SQL la dejaba pasar,
    Python la normalizaba a 0); se cierra con NULLIF antes del COALESCE.
    """
    from qzero.api.hub import _flow_key_sql

    cases = [
        (443, 6), (None, None), ("", ""), ("", 6), (443, ""),
        (443.0, 6.0), (" 443", 6), ("abc", "x"), (0, 0),
    ]
    for dst_port, protocol in cases:
        _seed(store, dst_port=dst_port, protocol=protocol)
        row = store._conn.execute(
            "SELECT typeof(dst_port), dst_port, typeof(protocol), protocol "
            "FROM alerts ORDER BY id DESC LIMIT 1").fetchone()
        sql_key = store._conn.execute(
            f"SELECT {_flow_key_sql()} FROM alerts ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        py_key = flow_key("10.0.0.5", "1.2.3.4", row[1], row[3])
        assert py_key == sql_key, (
            f"divergen con dst_port={dst_port!r} protocol={protocol!r} "
            f"(guardado como {row[0]}/{row[2]}): python={py_key!r} sql={sql_key!r}")
        store._conn.execute("DELETE FROM alerts")
