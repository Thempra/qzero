"""
QZero REST API — FastAPI application.

Endpoints:
  GET  /                 — API info
  GET  /health           — Health check
  GET  /models           — Loaded model status
  GET  /stats            — Runtime statistics
  POST /analyze          — Analyze a PCAP file
  GET  /dashboard        — Real-time web dashboard (HTML)
  WS   /ws               — WebSocket live data stream
  POST /monitor/start    — Start real-time traffic monitoring
  POST /monitor/stop     — Stop monitoring
"""

import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import (FastAPI, UploadFile, File, HTTPException, Query, WebSocket,
                     WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .schemas import StatusResponse, AnalyzeResponse
from .monitor import monitor_service
from .hub import hub_store, FLOW_STATES
from .observability import init_sentry, sentry_capture

logger = logging.getLogger(__name__)

try:
    from ..core.predictor import QZeroPredictor
    PREDICTOR_AVAILABLE = True
except ImportError:
    PREDICTOR_AVAILABLE = False

_predictor: Optional["QZeroPredictor"] = None


def _get_predictor() -> "QZeroPredictor":
    global _predictor
    if not PREDICTOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="QZeroPredictor not available")
    if _predictor is None:
        _predictor = QZeroPredictor(n_qubits=4)
    return _predictor


app = FastAPI(
    title="QZero — Quantum Threat Detection API",
    description="Quantum-algorithm-based network anomaly detection.",
    version="3.0.0",
)

# Referencias fuertes a las tareas de fondo: el event loop solo guarda
# referencias débiles y el GC puede llevarse una tarea a medio ejecutar.
_BACKGROUND_TASKS: set = set()


def _on_background_done(task) -> None:
    """Olvida la tarea y reporta su muerte si terminó con excepción.

    El mantenimiento es un `while True` que solo sale si algo lo rompe. Sin
    este callback, esa rotura queda como "Task exception was never retrieved"
    en stderr y el hub se queda sin retención, sin digest y sin avisos de
    agente caído, aparentemente sano.
    """
    _BACKGROUND_TASKS.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Tarea de fondo terminó con error", exc_info=exc)
        sentry_capture(exc, task="maintenance_loop")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth a nivel de app (Hito 3.7) ──────────────────────────────────────────
# Protege rutas de CONSULTA del hub y la API clásica. NO protege /health
# (healthcheck del contenedor) ni el ingest de agentes (usa X-Agent-Token
# opcional). Fail-closed: sin ADMIN_PASSWORD, las rutas protegidas dan 503.

from . import auth as _auth  # noqa: E402
from fastapi import Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

# Prefijos/rutas exentos de token SPA (data-plane de agentes + salud + login).
_AUTH_EXEMPT_PREFIXES = (
    "/health",
    "/api/v1/auth/",
    "/metrics",
)
_AUTH_EXEMPT_EXACT = {"/", "/dashboard", "/hub", "/api/v1/hub", "/ws", "/consola"}
_AUTH_EXEMPT_INGEST_SUFFIXES = ("/alerts", "/heartbeat")


def _is_exempt(path: str) -> bool:
    if any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
        return True
    if path in _AUTH_EXEMPT_EXACT:
        return True
    # ingest/heartbeat de agentes: LAN data-plane, token opcional aparte
    if path.startswith("/api/v1/agents/") and path.endswith(
            _AUTH_EXEMPT_INGEST_SUFFIXES):
        return True
    return False


@app.middleware("http")
async def spa_auth_middleware(request: Request, call_next):
    """Fail-closed: sin ADMIN_PASSWORD, las rutas protegidas dan 503.

    Antes (Fase 0.1, bug B-1) el early-return sin credenciales dejaba pasar
    TODO: ``GET /api/v1/alerts`` respondía 200 sin auth. Ahora el modo lo
    decide ``_auth.auth_enforced()`` (default fail-closed fuera de pytest).
    """
    path = request.url.path
    # ingest de agentes: X-Agent-Token si QZERO_AGENT_TOKEN está definido
    if path.startswith("/api/v1/agents/") and path.endswith(
            _AUTH_EXEMPT_INGEST_SUFFIXES) and request.method == "POST":
        if _auth.agent_token_required():
            if not _auth.agent_token():
                # flag activo sin token que comparar -> fail-closed
                return JSONResponse({"detail": "agent token not configured"}, 503)
            if not _auth.check_agent_token(request.headers.get("x-agent-token")):
                return JSONResponse({"detail": "invalid agent token"}, 401)
        return await call_next(request)
    if _is_exempt(path):
        return await call_next(request)
    if not _auth.auth_enabled():
        if not _auth.auth_enforced():
            return await call_next(request)
        # fail-closed: sin credenciales configuradas NUNCA se abren rutas
        return JSONResponse({"detail": "AUTH_NOT_CONFIGURED: set ADMIN_PASSWORD"},
                            503)
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else None
    if not _auth.verify_token(token):
        return JSONResponse({"detail": "unauthorized"}, 401)
    return await call_next(request)


@app.get("/api/v1/auth/status")
async def auth_status():
    """Si el cliente (dashboard/SPA) necesita loguearse."""
    return _auth.auth_status()


@app.post("/api/v1/auth/login")
async def auth_login(payload: dict, request: Request):
    """Login SPA: {password} -> token bearer con exp + token_version.

    Rate limit en memoria por IP: máx. ``LOGIN_MAX_ATTEMPTS`` fallos por
    ``LOGIN_WINDOW_SECONDS`` -> 429 con ``Retry-After``.
    """
    if not _auth.auth_enabled():
        raise HTTPException(status_code=503,
                            detail="AUTH_NOT_CONFIGURED: set ADMIN_PASSWORD")
    client_ip = request.client.host if request.client else "unknown"
    retry_after = _auth.login_retry_after(client_ip)
    if retry_after:
        logger.warning("Login bloqueado por rate limit: ip=%s", client_ip)
        raise HTTPException(status_code=429, detail="too many login attempts",
                            headers={"Retry-After": str(retry_after)})
    result = _auth.login(payload.get("password", ""))
    if result is None:
        _auth.register_login_failure(client_ip)
        raise HTTPException(status_code=401, detail="invalid credentials")
    _auth.reset_login_limits()
    return result


# ── Root ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "QZero API",
        "version": "3.0.0",
        "status": "operational" if PREDICTOR_AVAILABLE else "degraded",
        "dashboard": "/dashboard",
        "endpoints": {
            "GET  /dashboard":      "Real-time web dashboard",
            "WS   /ws":            "WebSocket live data stream",
            "POST /analyze":        "Analyze a PCAP file",
            "GET  /health":         "Health check",
            "GET  /models":         "Model status",
            "GET  /stats":          "Runtime statistics",
            "POST /monitor/start":  "Start live monitoring",
            "POST /monitor/stop":   "Stop live monitoring",
            "GET  /api/v1/hub/summary": "Aggregate agent alert stats",
            "GET  /api/v1/agents":      "List reporting agents",
            "GET  /api/v1/alerts":      "Query stored alerts",
            "POST /api/v1/agents/{id}/alerts": "Ingest agent alerts (internal)",
        },
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=StatusResponse)
async def health():
    predictor = _get_predictor()
    fitted = predictor.model_fitted
    return StatusResponse(
        status="healthy",
        message="ready" if fitted else "not_trained",
    )


# ── Models ────────────────────────────────────────────────────────────────────

@app.get("/models")
async def get_models():
    try:
        predictor = _get_predictor()
        return {
            "status": "ready" if predictor.model_fitted else "not_trained",
            "models": {
                "qsvm": predictor.use_qsvm,
                "qivae": predictor.use_qivae,
                "classical": predictor.use_classical,
            },
            "training_info": predictor.training_info if predictor.model_fitted else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Analyze PCAP ──────────────────────────────────────────────────────────────

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pcap(
    file: UploadFile = File(...),
    method: Optional[str] = "best",
):
    """Upload and analyze a PCAP file."""

    def _run_sync() -> AnalyzeResponse:
        # Trabajo bloqueante (pcap en disco + análisis) fuera del event
        # loop: se ejecuta vía asyncio.to_thread (S7493).
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pcap") as tmp:
                tmp_path = tmp.name
                tmp.write(file.file.read())

            predictor = _get_predictor()
            from ..core.detector import NetworkTrafficAnalyzer
            analyzer = NetworkTrafficAnalyzer(predictor=predictor)
            return analyzer.analyze(tmp_path, method=method)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    try:
        return await asyncio.to_thread(_run_sync)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error analyzing PCAP")
        raise HTTPException(status_code=500, detail=str(e))


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats():
    try:
        predictor = _get_predictor()
        stats = {
            "n_qubits": predictor.n_qubits,
            "use_qsvm": predictor.use_qsvm,
            "use_qivae": predictor.use_qivae,
            "use_classical": predictor.use_classical,
            "model_fitted": predictor.model_fitted,
        }
        if predictor.model_fitted:
            stats["training_info"] = predictor.training_info
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard ─────────────────────────────────────────────────────────────────

_DASHBOARD_HTML: Optional[str] = None

def _load_dashboard_html() -> str:
    global _DASHBOARD_HTML
    if _DASHBOARD_HTML is None:
        html_path = Path(__file__).parent / "dashboard.html"
        _DASHBOARD_HTML = html_path.read_text(encoding="utf-8")
    return _DASHBOARD_HTML


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the real-time monitoring dashboard."""
    return HTMLResponse(content=_load_dashboard_html())


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await monitor_service.connect(ws)
    try:
        while True:
            # Keep connection alive; client doesn't send data
            await ws.receive_text()
    except WebSocketDisconnect:
        monitor_service.disconnect(ws)
    except Exception:
        monitor_service.disconnect(ws)


# ── Monitor control ───────────────────────────────────────────────────────────

class MonitorStartRequest(BaseModel):
    interface: str = "eth0"
    promiscuous: bool = False
    interval: float = 5.0


@app.post("/monitor/start")
async def monitor_start(req: MonitorStartRequest):
    """Start the real-time traffic monitoring loop."""
    if monitor_service.is_running:
        return {"status": "already_running", "interface": req.interface}

    predictor = _get_predictor()
    monitor_service.configure(
        predictor=predictor,
        interface=req.interface,
        promiscuous=req.promiscuous,
        interval=req.interval,
    )
    monitor_service.start()
    return {"status": "started", "interface": req.interface, "interval": req.interval}


@app.post("/monitor/stop")
async def monitor_stop():
    """Stop the monitoring loop."""
    monitor_service.stop()
    return {"status": "stopped"}


# ── Hub: distributed agent alert aggregation ─────────────────────────────────
#
# Deployable QZero Agents on ANY server push their alerts here, so they can be
# reflected in one central place. The agent (qzero.agent) POSTs to:
#     POST /api/v1/agents/{agent_id}/alerts


def _hub_recent_since(minutes: int = 60) -> str:
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


@app.get("/api/v1/hub/summary")
async def hub_summary():
    """Aggregate alert statistics across all agents."""
    return hub_store.summary()


@app.get("/api/v1/agents")
async def hub_agents():
    """List all agents that have reported alerts."""
    return hub_store.list_agents()


@app.get("/api/v1/alerts")
async def hub_alerts(
    limit: int = 100,
    severity: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Query stored alerts (across all agents)."""
    return hub_store.list_alerts(
        limit=limit, severity=severity, agent_id=agent_id
    )


@app.get("/api/v1/alerts/recent")
async def hub_alerts_recent(minutes: int = 60):
    """Alerts from the last N minutes (for the live dashboard)."""
    since = _hub_recent_since(minutes)
    return hub_store.list_alerts(limit=500, since=since)


# ── Fase 1.1 / 1.2 — flujos agregados y triaje ───────────────────────────────
# Un flujo es la 5-tupla (src, dst, dst_port, protocol) agregada sobre una
# ventana temporal. Es la unidad que el analista puede triar: 8.473 alertas/hora
# no se revisan una a una, pero se reducen a decenas de flujos.
# Ambas rutas caen bajo spa_auth_middleware (no están exentas): sin
# ADMIN_PASSWORD en modo enforced -> 503, igual que /api/v1/alerts.

def _get_hub_store():
    """Resuelve el store en runtime (permite sustituirlo en tests)."""
    from . import hub as _hub
    return _hub.hub_store


@app.get("/api/v1/flows")
async def hub_flows(
    minutes: int = Query(60, ge=1, description="Ventana hacia atrás en minutos"),
    limit: int = Query(50, ge=1, description="Máximo de flujos devueltos"),
    only_untriaged: bool = Query(
        False, description="Excluir flujos ya marcados (investigando/benigno/malicioso)"),
):
    """Agregación de alertas por flujo (5-tupla) en una ventana temporal.

    ``minutes`` se capa a 1440 (24 h) y ``limit`` a 200: los topes se aplican
    recortando el valor, no rechazándolo (un dashboard que pide 10.000 quiere
    los 200 peores, no un 422). Valores < 1 sí son un error del cliente (422).
    Devuelve ``has_more``/``total_flows`` para que la consola sepa si hay cola
    detrás de la página.
    """
    return _get_hub_store().aggregate_flows(
        minutes=minutes, limit=limit, only_untriaged=only_untriaged)


@app.patch("/api/v1/flows/{key}/state")
async def hub_set_flow_state(key: str, payload: dict):
    """Marca el estado de triaje de un flujo.

    Body: ``{"state": "nuevo"|"investigando"|"benigno"|"malicioso",
    "note": "<opcional>"}``. Estado desconocido -> 400 con la lista válida en
    el detalle (no 422: el body es válido, el valor no).
    """
    store = _get_hub_store()
    state = payload.get("state")
    note = payload.get("note")
    if not isinstance(state, str) or state not in FLOW_STATES:
        raise HTTPException(
            status_code=400,
            detail="invalid state {!r}; allowed: {}".format(
                state, ", ".join(FLOW_STATES)),
        )
    try:
        return store.set_flow_state(key, state, note=note)
    except ValueError as exc:  # defensa en profundidad: misma validación abajo
        raise HTTPException(status_code=400, detail=str(exc)) from exc



_HUB_DASHBOARD_HTML: Optional[str] = None


def _load_hub_dashboard_html() -> str:
    global _HUB_DASHBOARD_HTML
    if _HUB_DASHBOARD_HTML is None:
        html_path = Path(__file__).parent / "hub_dashboard.html"
        _HUB_DASHBOARD_HTML = html_path.read_text(encoding="utf-8")
    return _HUB_DASHBOARD_HTML


@app.get("/api/v1/hub", response_class=HTMLResponse)
async def hub_dashboard():
    """Central dashboard reflecting alerts from all deployed agents."""
    return HTMLResponse(content=_load_hub_dashboard_html())


# ── Fase 1.3 — consola "Mesa de triaje" ─────────────────────────────────────
# Mismo patrón de servido que /dashboard y /api/v1/hub (HTML en un fichero
# junto a app.py, leído una vez y cacheado).
#
# ``/consola`` va EXENTO de auth, igual que ``/dashboard`` y ``/hub``. No es un
# descuido: el shell es HTML+JS sin datos y el navegador NO puede mandar la
# cabecera ``Authorization`` en una navegación normal, así que protegerlo con
# bearer lo hacía inalcanzable (401 siempre, aunque el token estuviera en
# localStorage). La consola trae su propio formulario de login: pide
# ``POST /api/v1/auth/login``, guarda el token y lo manda en cada ``fetch``
# posterior. Los DATOS siguen protegidos: ``/api/v1/flows`` y
# ``PATCH /api/v1/flows/{key}/state`` NO están exentos y devuelven 401 sin
# token. El HTML en sí no filtra nada — la geometría de la red vive en la API.
_CONSOLA_HTML: Optional[str] = None


def _load_consola_html() -> str:
    global _CONSOLA_HTML
    if _CONSOLA_HTML is None:
        html_path = Path(__file__).parent / "consola.html"
        _CONSOLA_HTML = html_path.read_text(encoding="utf-8")
    return _CONSOLA_HTML


@app.get("/consola", response_class=HTMLResponse)
async def consola():
    """Mesa de triaje (Fase 1.3): cola de casos + inspector fijo 62/38."""
    return HTMLResponse(content=_load_consola_html())


@app.post("/api/v1/agents/{agent_id}/alerts")
async def hub_ingest_agent_alerts(agent_id: str, payload: dict):
    """Ingest an alert batch pushed by a QZero agent (internal API)."""
    payload["agent_id"] = agent_id
    result = hub_store.ingest_alert_batch(payload)
    # Push the latest state out to any connected dashboard clients
    await monitor_service._broadcast({"type": "hub_update", "summary": hub_store.summary()})
    return result


@app.post("/api/v1/agents/{agent_id}/heartbeat")
async def hub_agent_heartbeat(agent_id: str, payload: dict | None = None):
    """Keep an agent's last_seen fresh even when it has NO alerts to push.

    The response carries the agent's per-agent config overrides (Hito 2.6)
    so the agent picks up threshold/whitelist changes without restart.
    """
    payload = payload or {}
    agent_name = payload.get("agent_name", "")
    interface = payload.get("interface", "")
    result = hub_store.heartbeat(agent_id, agent_name, interface)
    result["config"] = hub_store.get_agent_config(agent_id)
    return result


@app.get("/api/v1/agents/{agent_id}/config")
async def hub_get_agent_config(agent_id: str):
    """Per-agent detection config overrides."""
    return hub_store.get_agent_config(agent_id)


@app.get("/api/v1/intel/{ip}")
async def hub_ip_intel(ip: str):
    """ASN/org enrichment for an IP, served from the hub's ip_intel cache
    (Hito 3.8). Network hit only on cache miss/stale; private IPs → LAN stub."""
    from .intel import enrich_ip
    return enrich_ip(hub_store, ip)


@app.put("/api/v1/agents/{agent_id}/config")
async def hub_set_agent_config(agent_id: str, payload: dict):
    """Set per-agent overrides: {alert_threshold?: float, whitelist_private?: bool}."""
    return hub_store.set_agent_config(
        agent_id,
        alert_threshold=payload.get("alert_threshold"),
        whitelist_private=payload.get("whitelist_private"),
    )


@app.on_event("startup")
async def _start_hub_maintenance():
    """Hito 1: background retention + Telegram digest + agent liveness."""
    # El tracker se inicializa aquí y no al importar el módulo: los tests
    # importan app sin querer enviar nada, y el arranque es el único punto
    # donde ya está leído el entorno del contenedor.
    init_sentry()

    from .maintenance import maintenance_loop
    # S7502: la tarea debe quedar referenciada. El event loop solo mantiene
    # referencias débiles a las tareas, así que sin guardarla aquí el GC
    # puede recolectarla a mitad de ejecución y el mantenimiento moriría en
    # silencio (el bug clásico de asyncio.create_task).
    task = asyncio.create_task(maintenance_loop(hub_store))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_on_background_done)


@app.on_event("shutdown")
async def _stop_hub_maintenance():
    """Cancela el mantenimiento para no dejar tareas colgando al cerrar."""
    for task in list(_BACKGROUND_TASKS):
        task.cancel()
    if _BACKGROUND_TASKS:
        await asyncio.gather(*_BACKGROUND_TASKS, return_exceptions=True)
    _BACKGROUND_TASKS.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def _report_unhandled(request, exc):
    """Cualquier excepción no controlada llega al tracker antes del 500.

    FastAPI/Starlette ya devuelve 500 y escribe el error al log, pero nadie lo
    envía a BugSink: sin este handler, un fallo en producción solo existe en
    los logs del contenedor y se pierde al rotar.
    """
    sentry_capture(
        exc,
        path=str(request.url.path),
        method=request.method,
    )
    logger.error("Excepción no controlada en %s %s", request.method,
                 request.url.path, exc_info=exc)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail": "internal server error"})


def create_app() -> FastAPI:
    """Return the FastAPI application instance."""
    return app


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the Uvicorn server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
