#!/usr/bin/env python3
"""
Training script for QZero models.

This script trains all models (QSVM, QI-VAE, classical baselines) and saves them.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader
from preprocessing.feature_engineering import FeatureEngineer
from classical.baseline import run_all_baselines
from quantum.qsvm import QSVM, QSVMConfig
from quantum.qivae import QIVAE, QIVAEConfig
from evaluation.metrics import evaluate_model, evaluate_zero_day_detection


async def train_models():
    """Train all QZero models."""
    print(f"\n{'='*60}")
    print("QZero Model Training")
    print(f"{'='*60}\n")

    # Generate data
    print("Step 1: Generating synthetic data...")
    X, y = generate_synthetic_data(n_samples=5000, random_state=42)
    print(f"  ✓ Generated {X.shape[0]:,} samples ({X.shape[1]} features)")

    # Load and prepare data
    print("\nStep 2: Preparing data...")
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)
    print(f"  ✓ Training set: {data['X_train'].shape}")
    print(f"  ✓ Validation set: {data['X_val'].shape}")
    print(f"  ✓ Test set: {data['X_test'].shape}")

    # Classical baselines
    print("\nStep 3: Training classical baselines...")
    classical_results = run_all_baselines(
        data['X_train'],
        data['y_train'],
        data['X_test'],
        data['y_test'],
    )

    for result in classical_results:
        print(f"  ✓ {result.model}: {result.accuracy:.3f} accuracy, {result.f1:.3f} F1")

    # QSVM
    print("\nStep 4: Training QSVM...")
    engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")
    X_train_q = engineer.fit_transform(data['X_train'], data['y_train'])
    X_test_q = engineer.transform(data['X_test'])

    qsvm = QSVM(
        n_qubits=4,
        max_samples_quantum=200,
        use_aer=True,
    )

    qsvm.train(X_train_q, data['y_train'], X_test_q, data['y_test'])
    print(f"  ✓ QSVM trained. Accuracy: {qsvm.accuracy:.3f}")

    # QI-VAE
    print("\nStep 5: Training QI-VAE...")
    qivae = QIVAE(
        input_dim=14,
        latent_dim=4,
        n_qubits=4,
        use_quantum_encoder=False,
        use_aer=False,
    )

    normal_mask_train = data['y_train'] == 0
    X_train_normal = data['X_train'][normal_mask_train]

    qivae_result = qivae.train(X_train_normal)
    print(f"  ✓ QI-VAE trained. Train loss: {qivae_result.train_loss:.3f}")

    # Save models
    print("\nStep 6: Saving models...")
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    import pickle
    with open(models_dir / "qsvm_model.pkl", "wb") as f:
        pickle.dump(qsvm, f)

    with open(models_dir / "qivae_model.pkl", "wb") as f:
        pickle.dump(qivae, f)

    with open(models_dir / "classical_models.pkl", "wb") as f:
        pickle.dump(classical_results, f)

    print(f"  ✓ Models saved to {models_dir}")

    # Evaluation
    print("\nStep 7: Evaluating models...")
    qivae.eval(data['X_test'], data['y_test'])
    print(f"  ✓ QI-VAE: Accuracy {qivae.accuracy:.3f}, Precision {qivae.precision:.3f}, Recall {qivae.recall:.3f}")

    # Zero-day detection simulation
    print("\nStep 8: Simulating zero-day detection...")
    zero_day_results = evaluate_zero_day_detection(
        qivae,
        data['X_test'],
        data['y_test'],
        num_zero_days=50,
    )
    print(f"  ✓ Zero-day detection: {zero_day_results['precision']:.3f} precision, {zero_day_results['recall']:.3f} recall")

    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}\n")

    return qsvm, qivae, classical_results


if __name__ == "__main__":
    import asyncio
    asyncio.run(train_models())