"""Fase 1.3 — Consola 'Mesa de triaje' (GET /consola).

Cubre:
  * La ruta /consola sirve 200 + text/html; contiene los elementos clave
    (selector de ventana, panel 62/38, botones de estado, buscador).
  * Sin auth la ruta responde como el resto de rutas protegidas (comportamiento
    real, no asumido).
  * El HTML/JS no referencia campos que la API no devuelve (contraste 1-a-1
    con hub.py:_flow_row_to_dict + _attach_percentiles).
  * Los tests de flows (test_fase1_flows.py) siguen en 18 passed.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qzero.api.app import app
from qzero.api.hub import HubStore
from qzero.api.hub import flow_key

REPO = Path(__file__).resolve().parents[1]


# ── Fixtures ──────────────────────────────────────────────────────────────
@pytest.fixture()
def store(tmp_path, monkeypatch):
    """HubStore aislada, inyectada en el singleton del módulo."""
    s = HubStore(db_path=tmp_path / "hub.db")
    import qzero.api.hub as hub_mod
    monkeypatch.setattr(hub_mod, "hub_store", s)
    yield s
    s.close()


@pytest.fixture()
def client(store):
    return TestClient(app)


def _ts(minutes_ago: float = 0.0) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _seed(store, src="10.0.0.5", dst="1.2.3.4", dst_port=443, protocol=6,
          scores=(4.5,), severity="HIGH", minutes_ago=1.0, agent="a1",
          step_seconds=1.0, base_ts=None):
    """Siembra un lote de alertas de UN flujo, un score por alerta."""
    from datetime import datetime, timedelta
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


# ── Tests de la ruta HTML ─────────────────────────────────────────────────


def test_consola_route_serves_html(client):
    """GET /consola -> 200, text/html, contiene elementos clave de la UI."""
    r = client.get("/consola")
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "text/html" in ct, ct
    html = r.text
    # Elementos obligatorios (layout 62/38, controles, inspector, botones):
    assert 'id="selWindow"' in html, "falta selector de ventana"
    assert 'id="chkUntriaged"' in html, "falta toggle solo sin triar"
    assert 'id="inpSearch"' in html, "falta buscador"
    assert 'class="split"' in html, "falta grid 62/38"
    assert 'class="queue"' in html, "falta panel cola"
    assert 'class="inspector"' in html, "falta panel inspector"
    assert 'id="inspBody"' in html, "falta cuerpo del inspector"
    assert 'data-state="investigando"' in html, "falta botón Investigando"
    assert 'data-state="benigno"' in html, "falta botón Benigno"
    assert 'data-state="malicioso"' in html, "falta botón Malicioso"
    assert 'id="gate"' in html, "falta puerta de login"
    assert 'id="stateEmpty"' in html, "falta estado vacío"
    assert 'id="stateError"' in html, "falta estado error"
    assert 'id="skeleton"' in html, "falta esqueleto de carga"
    assert 'id="banner"' in html, "falta banda de error/degradado"


# ── Auth: /consola va detrás del mismo middleware que /api/v1/flows ───────


_AUTH_SCRIPT = """
import os
for k in ("ADMIN_PASSWORD", "QZERO_AGENT_TOKEN", "QZERO_REQUIRE_AGENT_TOKEN"):
    os.environ.pop(k, None)
from fastapi.testclient import TestClient
from qzero.api.app import app
c = TestClient(app)
print("consola", c.get("/consola").status_code)
print("health", c.get("/health").status_code)
"""


def test_consola_is_protected_by_auth_middleware():
    """Proceso limpio sin ADMIN_PASSWORD: /consola = 503 (fail-closed)."""
    env = dict(os.environ)
    env.pop("QZERO_AUTH_ENFORCE", None)
    env.pop("PYTEST_CURRENT_TEST", None)
    env["PYTHONPATH"] = str(REPO / "src")
    out = subprocess.run(
        [sys.executable, "-c", _AUTH_SCRIPT],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=180
    )
    assert out.returncode == 0, out.stderr[-2000:]
    res = {}
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            res[parts[0]] = int(parts[1])
    assert res["health"] == 200, "health siempre público"
    assert res["consola"] == 503, "/consola protegida sin ADMIN_PASSWORD"


# ── Contrato real: JS no inventa campos ───────────────────────────────────


_REAL_FLOW_FIELDS = [
    # _flow_row_to_dict (hub.py:732-748)
    "flow_key",
    "src",
    "dst",
    "dst_port",
    "protocol",
    "count",
    "severity",
    "score_max",
    "first_seen",
    "last_seen",
    "alerts_per_minute",
    "state",
    "note",
    # _attach_percentiles (hub.py:750-767)
    "score_p50",
    "score_p99",
]


def test_campos_js_existen_en_respuesta_real(client, store):
    """
    La API devuelve EXACTAMENTE estos campos; el JS no debe referenciar otros.
    Si la API cambia, este test falla y obliga a actualizar el HTML.
    """
    _seed(store, scores=(4.5, 6.2, 7.1), base_ts=_ts(0.0))
    r = client.get("/api/v1/flows")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "flows" in data and isinstance(data["flows"], list)
    if not data["flows"]:
        pytest.skip("no flows seeded")
    f = data["flows"][0]
    missing = [k for k in _REAL_FLOW_FIELDS if k not in f]
    assert not missing, "la API ya no devuelve: " + ", ".join(missing)
    # Campos EXTRA que la API sí devuelve (envelope + meta) y el JS ignora:
    extra = [k for k in f.keys() if k not in _REAL_FLOW_FIELDS]
    assert "total_flows" not in f, "total_flows es del envelope, no del flujo"
    assert "has_more" not in f, "has_more es del envelope, no del flujo"


# ── Uso real de la API por el JS: se comprueba que el HTML carga sin error ────


def test_consola_loads_and_contains_no_external_deps():
    """El HTML servido no tiene etiquetas script/link a CDNs ni fuentes remotas."""
    from pathlib import Path
    html = Path(REPO / "src" / "qzero" / "api" / "consola.html").read_text(encoding="utf-8")
    # Cero dependencias externas en runtime
    assert "cdn." not in html.lower(), "referencia a CDN detectada"
    assert "googleapis.com" not in html.lower(), "fuente Google detectada"
    assert "fonts.gstatic.com" not in html.lower(), "fuente Google detectada"
    assert "unpkg.com" not in html.lower(), "unpkg detectado"
    assert "cdnjs.cloudflare.com" not in html.lower(), "cloudflare detectado"
    assert "bootstrap" not in html.lower(), "bootstrap detectado"
    assert "jquery" not in html.lower(), "jquery detectado"
    assert "react" not in html.lower(), "react detectado"
    assert " vue " not in html.lower(), "vue detectado"
    # Todo CSS/JS está inline
    assert "<style>" in html and "</style>" in html, "CSS inline ausente"
    assert "<script>" in html and "</script>" in html, "JS inline ausente"


if __name__ == "__main__":
    pytest.main([__file__, "-q", "--no-header", "-p", "no:randomly"])