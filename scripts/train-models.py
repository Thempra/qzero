#!/usr/bin/env python3
"""
Script de entrenamiento para QZero
Entrena los modelos cuánticos y clásicos
"""

import sys
from pathlib import Path

sys.path.insert(0, '/home/thempra/projects/qzero')

from src.predictor import QZeroPredictor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QZero-Training")

print("=" * 70)
print("🚀 QZero - TRAINING PIPELINE")
print("⚡ Entrenando Modelos Cuánticos y Clásicos")
print("=" * 70)
print()

# Crear predictor
predictor = QZeroPredictor(
    n_qubits=4,
    use_qsvm=True,
    use_qivae=True,
    use_classical=True,
    classical_models=["random_forest", "svm_rbf"]
)

# Entrenar con datos sintéticos (porque no tenemos dataset real)
print("📦 Preparando datos de entrenamiento...")
print("ℹ️  Usando datos sintéticos (5000 muestras)")

summary = predictor.train_all(
    n_samples=5000,
    use_real_data=False,
    use_qsvm=True,
    use_qivae=True,
    use_classical=True
)

# Guardar modelos
models_path = Path('/home/thempra/projects/qzero/models')
models_path.mkdir(parents=True, exist_ok=True)

predictor.save(models_path)
logger.info(f"✅ Modelos guardados en: {models_path}")

# Mostrar resultados
print()
print("=" * 70)
print("📊 TRAINING RESULTS")
print("=" * 70)
print(f"⏱️  Training time: {summary.get('training_time', 0):.2f}s")
print(f"🧪 Samples: {summary.get('n_samples', 0)}")

if summary.get('qsvm'):
    qsvm = summary['qsvm']
    print(f"\n⚛️  QSVM:")
    print(f"   Accuracy: {qsvm.get('accuracy', 0):.4f}")
    print(f"   F1 Score: {qsvm.get('f1_score', 0):.4f}")

if summary.get('qivae'):
    qivae = summary['qivae']
    print(f"\n⚛️  QIVAE:")
    print(f"   Accuracy: {qivae.get('accuracy', 0):.4f}")
    print(f"   F1 Score: {qivae.get('f1_score', 0):.4f}")

if summary.get('classical'):
    classical = summary['classical']
    print(f"\n📊 Classical Models:")
    for model_name, result in classical.items():
        print(f"   - {model_name}: Accuracy={result.get('accuracy', 0):.4f}, F1={result.get('f1', 0):.4f}")

print()
print("✅ TRAINING COMPLETE")
print("=" * 70)