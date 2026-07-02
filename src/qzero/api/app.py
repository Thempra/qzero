"""
QZero REST API — FastAPI application.

Endpoints:
  GET  /           — API info
  GET  /health     — Health check
  GET  /models     — Loaded model status
  GET  /stats      — Runtime statistics
  POST /analyze    — Analyze a PCAP file
"""

import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import StatusResponse, AnalyzeResponse

logger = logging.getLogger(__name__)

# Lazy import — Predictor is only needed at request time
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


@app.get("/")
async def root():
    return {
        "name": "QZero API",
        "version": "3.0.0",
        "status": "operational" if PREDICTOR_AVAILABLE else "degraded",
        "endpoints": {
            "POST /analyze": "Analyze a PCAP file",
            "GET /health": "Health check",
            "GET /models": "Model status",
            "GET /stats": "Runtime statistics",
        },
    }


@app.get("/health", response_model=StatusResponse)
async def health():
    predictor = _get_predictor()
    fitted = predictor.model_fitted
    return StatusResponse(
        status="healthy",
        message="ready" if fitted else "not_trained",
    )


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


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pcap(
    file: UploadFile = File(...),
    method: Optional[str] = "best",
):
    """Upload and analyze a PCAP file."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pcap") as tmp:
            tmp_path = tmp.name
            tmp.write(await file.read())

        predictor = _get_predictor()

        from ..core.detector import NetworkTrafficAnalyzer
        analyzer = NetworkTrafficAnalyzer(predictor=predictor)
        result = analyzer.analyze(tmp_path, method=method)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error analyzing PCAP")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


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


def create_app() -> FastAPI:
    """Return the FastAPI application instance."""
    return app


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Start the Uvicorn server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)
