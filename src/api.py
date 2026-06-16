from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pandas as pd
import io
import uvicorn
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pickle

from src.preprocessing.data_loader import DataLoader, generate_synthetic_data
from src.preprocessing.feature_engineering import FeatureEngineer
from src.quantum.qsvm import QSVM, QSVMConfig
from src.quantum.qivae import QIVAE, QIVAEConfig
from src.classical.baseline import ClassicalBaseline
from src.predictor import QZeroPredictor

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
    anomaly_score: float
    quantum_anomaly_score: float
    reconstruction_loss: Optional[float] = None
    model_used: str
    status: str
    detailed_results: Optional[Dict[str, Any]] = None

class ModelConfig(BaseModel):
    """Model configuration for analysis."""
    use_qsvm: bool = True
    use_qivae: bool = True
    use_classical: bool = True
    classical_models: list = ["random_forest", "svm_rbf"]
    n_qubits: int = 4
    max_samples_quantum: int = 200
    train_data_samples: int = 5000
    use_real_data: bool = False

# Global predictor instance
predictor: Optional[Any] = None
models_path = Path(__file__).parent.parent / "models"

@app.on_event("startup")
async def startup_event():
    """Initialize predictor on startup."""
    global predictor
    logger.info("Initializing QZero predictor...")

    # Create models directory if it doesn't exist
    models_path.mkdir(parents=True, exist_ok=True)

    # Try to load existing models
    model_files = list(models_path.glob("*.pkl"))
    if len(model_files) >= 3:  # At least one of each type
        logger.info("Loading pre-trained models...")
        predictor = QZeroPredictor(n_qubits=4)
        predictor.load(models_path)
        logger.info("Models loaded successfully")
    else:
        logger.info("No pre-trained models found, using defaults")

@app.get("/")
def health_check():
    """Health check endpoint."""
    status = "online"
    backend = "quantum-simulator"
    if predictor and predictor.qsvm_model:
        backend = "quantum-enabled"
    if predictor and predictor.qivae_model:
        backend = "vae-enabled"

    return {
        "status": status,
        "backend": backend,
        "version": "1.0.0",
        "models_loaded": predictor is not None,
        "predictor": str(predictor) if predictor else None,
    }

@app.get("/models/info")
def get_model_info():
    """Get information about loaded models."""
    if predictor is None:
        raise HTTPException(status_code=503, detail="No models trained")

    info = {
        "n_qubits": predictor.n_qubits,
        "training_info": predictor.training_info,
        "models": {},
    }

    if predictor.qsvm_result:
        info["models"]["qsvm"] = {
            "accuracy": predictor.qsvm_result.accuracy,
            "f1_score": predictor.qsvm_result.f1_score,
            "used_quantum": predictor.qsvm_result.used_quantum,
        }

    if predictor.qivae_result:
        info["models"]["qivae"] = {
            "accuracy": predictor.qivae_result.accuracy,
            "f1_score": predictor.qivae_result.f1_score,
            "anomaly_threshold": predictor.qivae_result.anomaly_threshold,
        }

    if predictor.classical_results:
        info["models"]["classical"] = {
            name: {
                "accuracy": r.accuracy,
                "f1_score": r.f1,
            }
            for name, r in predictor.classical_results.items()
        }

    return info

@app.post("/train")
def train_model(config: ModelConfig):
    """
    Train or retrain models with the provided configuration.
    """
    global predictor

    logger.info(f"Starting training with config: {config.dict()}")

    predictor = QZeroPredictor(
        n_qubits=config.n_qubits,
        use_qsvm=config.use_qsvm,
        use_qivae=config.use_qivae,
        use_classical=config.use_classical,
        classical_models=config.classical_models,
    )

    # Train models
    summary = predictor.train_all(
        n_samples=config.train_data_samples,
        use_real_data=config.use_real_data,
        use_qsvm=config.use_qsvm,
        use_qivae=config.use_qivae,
        use_classical=config.use_classical,
        classical_models=config.classical_models,
    )

    # Save models
    predictor.save(models_path)

    logger.info("Training complete")

    return {
        "status": "success",
        "training_time": summary.get("training_time"),
        "summary": summary,
    }

@app.get("/compare")
def compare_models():
    """Get comparison of all models."""
    if predictor is None:
        raise HTTPException(status_code=503, detail="No models trained")

    return {
        "comparison": predictor.compare_models(),
        "training_info": predictor.training_info,
    }

@app.post("/analyze", response_model=AnalysisResult)
async def analyze_traffic(
    file: UploadFile = File(...),
    model_config: Optional[ModelConfig] = None,
    threshold: float = 0.85,
):
    """
    Endpoint principal para analizar tráfico de red (CSV/NetFlow).

    Args:
        file: CSV file with network traffic data
        model_config: Optional model configuration
        threshold: Anomaly score threshold for CRITICAL status

    Returns:
        Analysis result with anomaly scores and classification
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files supported in this version")

    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))

        logger.info(f"Processing file: {file.filename} with {len(df)} flows")

        # If predictor not loaded or config provided, use model
        use_model = predictor is not None and (model_config is None or model_config.use_qsvm or model_config.use_qivae)

        if use_model and predictor.model_fitted:
            # Use trained model
            features = df.values

            # Get anomaly scores
            anomaly_scores = predictor.get_anomaly_score(features, method="qivae")

            # Aggregate scores from multiple methods
            if predictor.qsvm_model:
                try:
                    qsvm_proba = predictor.qsvm_model.model.predict_proba(features)
                    if qsvm_proba.shape[1] == 2:
                        qsvm_scores = qsvm_proba[:, 1]
                    else:
                        qsvm_scores = qsvm_proba[:, 1]  # Anomaly class
                    anomaly_scores = (anomaly_scores + qsvm_scores) / 2
                except:
                    pass

            # Normalize scores to [0, 1]
            if anomaly_scores.max() > 1:
                anomaly_scores = anomaly_scores / anomaly_scores.max()

            # Predict anomalies
            predictions = (anomaly_scores > threshold).astype(int)
            anomalies_detected = int(predictions.sum())

            # Get max score
            quantum_anomaly_score = float(anomaly_scores.max())

            # Determine status
            status = "CRITICAL" if quantum_anomaly_score >= threshold and anomalies_detected > 0 else "WARNING"
            if quantum_anomaly_score < 0.5:
                status = "SAFE"

            # Get model used
            model_used = "hybrid"
            if predictor.qivae_result and predictor.qivae_result.accuracy > predictor.qsvm_result.f1_score:
                model_used = "qivae"
            elif predictor.qsvm_result and predictor.qsvm_result.f1_score > 0.8:
                model_used = "qsvm"
            else:
                # Use classical as fallback
                if predictor.classical_results:
                    best_classical = max(predictor.classical_results.values(), key=lambda r: r.f1)
                    model_used = f"classical_{best_classical.name}"

            # Get reconstruction loss from QI-VAE if available
            reconstruction_loss = None
            if predictor.qivae_model and hasattr(predictor.qivae_result, 'reconstruction_errors'):
                errors = predictor.qivae_model.reconstruction_errors(features)
                reconstruction_loss = float(errors.mean())

            detailed_results = {
                "anomaly_scores": anomaly_scores.tolist(),
                "predictions": predictions.tolist(),
                "threshold": threshold,
                "model_used": model_used,
                "model_accuracy": (
                    predictor.qivae_result.accuracy
                    if model_used == "qivae" else
                    predictor.qsvm_result.accuracy
                    if model_used == "qsvm" else
                    predictor.classical_results.get(model_used.replace("classical_", ""), {}).accuracy
                ) if predictor.model_fitted else None,
            }

        else:
            # Use default behavior (simulate)
            logger.warning("No trained models available, using simulation")
            anomalies_detected = int(len(df) * 0.05)  # Simulación: 5% anomalías
            quantum_anomaly_score = 0.87  # High probability
            status = "CRITICAL" if anomalies_detected > 0 else "SAFE"
            model_used = "simulated"
            detailed_results = None
            reconstruction_loss = None

        return AnalysisResult(
            filename=file.filename,
            total_flows=len(df),
            anomalies_detected=anomalies_detected,
            anomaly_score=float(anomaly_scores.mean()) if 'anomaly_scores' in locals() else 0.0,
            quantum_anomaly_score=quantum_anomaly_score,
            reconstruction_loss=reconstruction_loss,
            model_used=model_used,
            status=status,
            detailed_results=detailed_results,
        )

    except Exception as e:
        logger.error(f"Error analyzing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/detailed")
def detailed_health_check():
    """Detailed health check with model status."""
    status = {
        "status": "online",
        "backend": "quantum-simulator",
        "version": "1.0.0",
    }

    if predictor:
        status["backend"] = "quantum-enabled" if predictor.qsvm_model else "vae-enabled"
        status["models_loaded"] = predictor.model_fitted
        status["training_info"] = predictor.training_info

        if predictor.qsvm_result:
            status["qsvm"] = {
                "accuracy": predictor.qsvm_result.accuracy,
                "f1_score": predictor.qsvm_result.f1_score,
            }

        if predictor.qivae_result:
            status["qivae"] = {
                "accuracy": predictor.qivae_result.accuracy,
                "f1_score": predictor.qivae_result.f1_score,
            }

        if predictor.classical_results:
            status["classical"] = {
                name: {"accuracy": r.accuracy, "f1": r.f1}
                for name, r in predictor.classical_results.items()
            }

    return status

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
