#!/usr/bin/env python3
"""
End-to-end pipeline demo for QZero.
Runs synthetic data through classical baselines, QSVM, and QI-VAE.
"""

import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader
from preprocessing.feature_engineering import FeatureEngineer
from classical.baseline import run_all_baselines, print_comparison_table
from quantum.qsvm import QSVM, QSVMConfig
from quantum.qivae import QIVAE, QIVAEConfig
from evaluation.metrics import (
    evaluate_model,
    evaluate_zero_day_detection,
    print_evaluation_report,
)


def main():
    print("=" * 70)
    print("QZero - Quantum Zero-Day Detection System")
    print("End-to-End Pipeline Demo")
    print("=" * 70)
    
    # Step 1: Generate synthetic data
    print("\n📊 Step 1: Generating synthetic data...")
    start = time.time()
    X, y = generate_synthetic_data(
        n_samples=2000, # Reduced for speed
        anomaly_ratio=0.15,
        signature_ratio=0.20,
    )
    print(f"  Generated {len(X)} samples in {time.time() - start:.2f}s")
    print(f"  Class distribution: {y.value_counts().to_dict()}")
    
    # Step 2: Prepare data
    print("\n🔧 Step 2: Preparing data...")
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)
    print(f"  Train: {data['X_train'].shape}")
    print(f"  Val:   {data['X_val'].shape}")
    print(f"  Test:  {data['X_test'].shape}")
    
    # Step 3: Run classical baselines
    print("\n🤖 Step 3: Running classical baselines...")
    classical_results = run_all_baselines(
        data["X_train"],
        data["y_train"],
        data["X_test"],
        data["y_test"],
        models=["random_forest", "svm_rbf", "mlp"] # Reduced list
    )
    print_comparison_table(classical_results)
    
    # Step 4: Prepare quantum-ready features
    print("\n⚛️ Step 4: Preparing quantum features (4 qubits)...")
    engineer = FeatureEngineer(n_qubits=4, reduction_method="pca")
    X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
    X_test_q = engineer.transform(data["X_test"])
    print(f"  Quantum features shape: {X_train_q.shape}")
    
    # Step 5: Run QSVM
    print("\n🔮 Step 5: Running QSVM...")
    config = QSVMConfig(
        n_qubits=4,
        max_samples_quantum=200,
        use_classical_fallback=True,
    )
    qsvm = QSVM(config)
    
    qsvm_result = qsvm.fit_evaluate(
        X_train_q[:config.max_samples_quantum],
        data["y_train"][:config.max_samples_quantum],
        X_test_q,
        data["y_test"]
    )
    
    print(f"  QSVM Results: Acc={qsvm_result.accuracy:.4f}, F1={qsvm_result.f1_score:.4f}, UsedQuantum={qsvm_result.used_quantum}")

    # Step 6: Run QI-VAE
    print("\n🌌 Step 6: Running QI-VAE (Anomaly Detection)...")
    
    # Train on normal data only
    normal_mask = data["y_train"] == 0
    X_train_normal = data["X_train"][normal_mask]
    
    qivae_config = QIVAEConfig(
        input_dim=data["X_train"].shape[1],
        latent_dim=4,
        hidden_dims=(64, 32),
        epochs=20,
        batch_size=32,
    )
    
    qivae = QIVAE(qivae_config)
    
    # Suppress verbose training output
    qivae_result = qivae.fit_evaluate(
        X_train_normal,
        data["X_test"],
        data["y_test"],
        verbose=False
    )
    
    print(f"  QI-VAE Results: Acc={qivae_result.accuracy:.4f}, F1={qivae_result.f1_score:.4f}, Threshold={qivae_result.anomaly_threshold:.4f}")
    
    # Step 7: Final comparison
    print("\n📈 Step 7: Final Comparison")
    print("=" * 80)
    print(f"{'Model':<25} {'Accuracy':>12} {'F1':>12}")
    print("-" * 80)
    
    for r in sorted(classical_results, key=lambda x: x.f1, reverse=True):
        print(f"{r.name:<25} {r.accuracy:>12.4f} {r.f1:>12.4f}")
    
    quantum_label = "QSVM (quantum)" if qsvm_result.used_quantum else "QSVM (classical)"
    print(f"{quantum_label:<25} {qsvm_result.accuracy:>12.4f} {qsvm_result.f1_score:>12.4f}")
    
    print(f"{'QI-VAE (Anomaly)':<25} {qivae_result.accuracy:>12.4f} {qivae_result.f1_score:>12.4f}")
    print("=" * 80)
    
    print("\n🎉 Pipeline complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
