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

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .schemas import StatusResponse, AnalyzeResponse
from .monitor import monitor_service
from .hub import hub_store

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    from .maintenance import maintenance_loop
    asyncio.create_task(maintenance_loop(hub_store))


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Return the FastAPI application instance."""
    return app


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the Uvicorn server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
