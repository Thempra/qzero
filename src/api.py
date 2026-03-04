"""
API REST para QZero
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import uvicorn
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Models
class AnalyzeRequest(BaseModel):
    method: Optional[str] = "best"

class Alert(BaseModel):
    timestamp: str
    severity: str
    src_ip: str
    dst_ip: str
    protocol: str
    anomaly_score: float
    message: str

class StatusResponse(BaseModel):
    status: str
    message: str

# Global predictor - defined after import
global_predictor: Optional[QZeroPredictor] = None

# Importar predictor
try:
    from src.predictor import QZeroPredictor
    PREDICTOR_AVAILABLE = True
except:
    PREDICTOR_AVAILABLE = False

app = FastAPI(
    title="QZero - Quantum Threat Detection API",
    description="API para detección de anomalías cuánticas en tráfico de red",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class AnalyzeRequest(BaseModel):
    method: Optional[str] = "best"

class Alert(BaseModel):
    timestamp: str
    severity: str
    src_ip: str
    dst_ip: str
    protocol: str
    anomaly_score: float
    message: str

class StatusResponse(BaseModel):
    status: str
    message: str

# Global predictor
global_predictor: Optional[QZeroPredictor] = None

def get_predictor() -> QZeroPredictor:
    """Obtiene o crea el predictor global"""
    global global_predictor

    if global_predictor is None:
        if not PREDICTOR_AVAILABLE:
            raise HTTPException(status_code=503, detail="Predictor no disponible")

        global_predictor = QZeroPredictor(n_qubits=4)

    return global_predictor

@app.get("/")
async def root():
    """API root"""
    return {
        "name": "QZero API",
        "version": "2.0.0",
        "status": "operational" if PREDICTOR_AVAILABLE else "unavailable",
        "endpoints": {
            "/analyze": "Analizar archivo PCAP",
            "/health": "Estado del sistema",
            "/models": "Modelos entrenados",
            "/stats": "Estadísticas"
        }
    }

@app.get("/health")
async def health():
    """Health check"""
    status = {
        "status": "healthy",
        "predictor_available": PREDICTOR_AVAILABLE,
        "version": "2.0.0"
    }

    if PREDICTOR_AVAILABLE and global_predictor:
        status["predictor_status"] = "ready"
    elif PREDICTOR_AVAILABLE:
        status["predictor_status"] = "not_trained"

    return status

@app.get("/models")
async def get_models():
    """Obtener modelos entrenados"""
    try:
        predictor = get_predictor()
        return {
            "status": "ready" if predictor.model_fitted else "not_trained",
            "models": {
                "qsvm": predictor.use_qsvm,
                "qivae": predictor.use_qivae,
                "classical": predictor.use_classical
            },
            "training_info": predictor.training_info if predictor.model_fitted else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_pcap(
    file: UploadFile = File(...),
    method: Optional[str] = "best"
):
    """Analiza un archivo PCAP"""
    try:
        # Guardar archivo temporal
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pcap') as tmp:
            temp_path = tmp.name
            tmp.write(file.file.read())

        # Analizar
        from src.detection import NetworkTrafficAnalyzer
        analyzer = NetworkTrafficAnalyzer()
        result = analyzer.analyze(temp_path, method)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Limpiar archivo temporal
        if 'temp_path' in locals():
            Path(temp_path).unlink(missing_ok=True)

@app.get("/stats")
async def get_stats():
    """Obtener estadísticas del sistema"""
    try:
        predictor = get_predictor()

        stats = {
            "n_qubits": predictor.n_qubits,
            "use_qsvm": predictor.use_qsvm,
            "use_qivae": predictor.use_qivae,
            "use_classical": predictor.use_classical,
            "model_fitted": predictor.model_fitted
        }

        if predictor.model_fitted:
            stats["training_info"] = predictor.training_info

        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_app():
    """Crea y retorna la aplicación FastAPI"""
    return app

def start_server(host: str = "0.0.0.0", port: int = 8000):
    """Inicia el servidor API"""
    uvicorn.run(app, host=host, port=port)