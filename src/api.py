from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd
import io
import uvicorn
import os
import logging
from src.preprocessing.data_loader import DataLoader
# from src.quantum.qivae import QIVAE_Predictor # Placeholder import

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QZero-API")

app = FastAPI(
    title="QZero Quantum IDS",
    description="API for Quantum-Enhanced Zero-Day Detection",
    version="1.0.0"
)

class AnalysisResult(BaseModel):
    filename: str
    total_flows: int
    anomalies_detected: int
    quantum_anomaly_score: float
    status: str

@app.get("/")
def health_check():
    return {"status": "online", "backend": "quantum-simulator", "version": "1.0.0"}

@app.post("/analyze", response_model=AnalysisResult)
async def analyze_traffic(file: UploadFile = File(...)):
    """
    Endpoint principal para analizar tráfico de red (CSV/NetFlow).
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files supported in this version")
    
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        logger.info(f"Processing file: {file.filename} with {len(df)} flows")
        
        # TODO: Cargar modelo real y predecir
        # Por ahora simulamos la respuesta para demostrar la arquitectura
        
        anomalies = int(len(df) * 0.05) # Simulación: 5% anomalías
        
        return {
            "filename": file.filename,
            "total_flows": len(df),
            "anomalies_detected": anomalies,
            "quantum_anomaly_score": 0.87, # High probability
            "status": "CRITICAL" if anomalies > 0 else "SAFE"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
