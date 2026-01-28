#!/usr/bin/env python3
"""
Generate markdown report with experiment results for iQuHACK presentation.

Usage:
    python scripts/generate_report.py --output results/report.md
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from tabulate import tabulate

from src.preprocessing.data_loader import generate_synthetic_data, DataLoader
from src.preprocessing.feature_engineering import FeatureEngineer
from src.classical.baseline import ClassicalBaseline, run_all_baselines
from src.quantum.qsvm import QSVM, QSVMConfig
from src.quantum.qivae import QIVAE, QIVAEConfig
from sklearn.model_selection import train_test_split


def generate_report(
    n_samples: int = 2000,
    n_qubits: int = 4,
    difficulty: str = "medium",
    output_path: str = None,
) -> str:
    """Generate comprehensive markdown report."""
    
    report_lines = []
    
    def add(line=""):
        report_lines.append(line)
    
    # Header
    add("# QZero Experiment Report")
    add()
    add(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add()
    add("## Experiment Configuration")
    add()
    add(f"| Parameter | Value |")
    add("|-----------|-------|")
    add(f"| Samples | {n_samples} |")
    add(f"| Qubits | {n_qubits} |")
    add(f"| Difficulty | {difficulty} |")
    add()
    
    # Generate data
    print("Generating synthetic data...", flush=True)
    X, y = generate_synthetic_data(n_samples=n_samples, difficulty=difficulty)
    
    add("## Dataset Statistics")
    add()
    add(f"- **Total samples:** {len(X)}")
    add(f"- **Features:** {X.shape[1]}")
    
    class_dist = dict(zip(*np.unique(y, return_counts=True)))
    add(f"- **Class distribution:**")
    for cls, count in class_dist.items():
        add(f"  - Class {cls}: {count} ({count/len(y)*100:.1f}%)")
    add()
    
    # Prepare data
    print("Preparing data...", flush=True)
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True, test_size=0.2)
    
    add(f"- **Training samples:** {len(data['X_train'])}")
    add(f"- **Test samples:** {len(data['X_test'])}")
    add()
    
    # Feature engineering for quantum
    print("Engineering features...", flush=True)
    engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method='pca')
    X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
    X_test_q = engineer.transform(data["X_test"])
    
    add("## Feature Engineering")
    add()
    add(f"- **Reduction method:** PCA")
    add(f"- **Original features:** {data['X_train'].shape[1]}")
    add(f"- **Quantum features:** {X_train_q.shape[1]} (for {n_qubits} qubits)")
    add(f"- **Feature range:** [0, π] (angle encoding)")
    add()
    
    # Classical baselines
    add("## Classical Baseline Results")
    add()
    print("Running classical baselines...", flush=True)
    # Use faster models for quick reports
    fast_models = ["random_forest", "logistic_regression", "knn", "svm_rbf"]
    classical_results = run_all_baselines(
        data["X_train"], data["y_train"],
        data["X_test"], data["y_test"],
        models=fast_models
    )
    
    # Sort by F1
    classical_results = sorted(classical_results, key=lambda x: x.f1, reverse=True)
    
    table_data = []
    for r in classical_results:
        table_data.append([
            r.name,
            f"{r.accuracy:.4f}",
            f"{r.precision:.4f}",
            f"{r.recall:.4f}",
            f"{r.f1:.4f}",
            f"{r.train_time:.3f}s"
        ])
    
    add("| Model | Accuracy | Precision | Recall | F1-Score | Train Time |")
    add("|-------|----------|-----------|--------|----------|------------|")
    for row in table_data:
        add(f"| {' | '.join(row)} |")
    add()
    
    best_classical = classical_results[0]
    add(f"**Best classical model:** {best_classical.name} (F1: {best_classical.f1:.4f})")
    add()
    
    # Quantum QSVM
    add("## Quantum QSVM Results")
    add()
    
    # Use subset for quantum
    max_quantum_train = min(200, len(X_train_q))
    max_quantum_test = min(100, len(X_test_q))
    
    add(f"*Note: Using {max_quantum_train} training and {max_quantum_test} test samples for quantum kernel computation.*")
    add()
    
    print(f"Running QSVM (quantum kernel with {max_quantum_train} samples)...")
    qsvm_config = QSVMConfig(
        n_qubits=n_qubits,
        feature_map_reps=2,
        max_samples_quantum=max_quantum_train,
        use_classical_fallback=True
    )
    
    qsvm = QSVM(config=qsvm_config)
    
    try:
        qsvm_result = qsvm.fit_evaluate(
            X_train_q[:max_quantum_train],
            data["y_train"][:max_quantum_train],
            X_test_q[:max_quantum_test],
            data["y_test"][:max_quantum_test]
        )
        
        add("| Metric | Value |")
        add("|--------|-------|")
        add(f"| Backend | {'Quantum Kernel' if qsvm._used_quantum else 'Classical Fallback'} |")
        add(f"| Feature Map | ZZ (reps=2) |")
        add(f"| Accuracy | {qsvm_result.accuracy:.4f} |")
        add(f"| F1-Score | {qsvm_result.f1_score:.4f} |")
        add(f"| Training Time | {qsvm_result.train_time:.2f}s |")
        add(f"| Support Vectors | {qsvm_result.n_support_vectors} |")
        add()
        
        qsvm_f1 = qsvm_result.f1_score
        qsvm_available = True
    except Exception as e:
        add(f"**Error:** QSVM failed - {e}")
        add()
        qsvm_f1 = 0
        qsvm_available = False
    
    # QI-VAE Anomaly Detection
    add("## Quantum-Inspired VAE Results")
    add()
    add("*QI-VAE trained on normal samples only for anomaly detection.*")
    add()
    
    print("Running QI-VAE...", flush=True)
    normal_mask = data["y_train"] == 0
    X_train_normal = data["X_train"][normal_mask]
    
    qivae_config = QIVAEConfig(
        input_dim=data["X_train"].shape[1],
        latent_dim=4,
        hidden_dims=(64, 32),
        epochs=30,
        batch_size=32,
        beta=1.0,
        anomaly_threshold_percentile=95.0,
    )
    
    try:
        qivae = QIVAE(qivae_config)
        qivae_result = qivae.fit_evaluate(
            X_train_normal,
            data["X_test"],
            data["y_test"],
            verbose=False,
        )
        
        add("| Metric | Value |")
        add("|--------|-------|")
        add(f"| Latent Dimension | {qivae_config.latent_dim} |")
        add(f"| Training Loss | {qivae_result.train_loss:.4f} |")
        add(f"| Anomaly Threshold | {qivae_result.anomaly_threshold:.4f} |")
        add(f"| Accuracy | {qivae_result.accuracy:.4f} |")
        add(f"| Precision | {qivae_result.precision:.4f} |")
        add(f"| Recall | {qivae_result.recall:.4f} |")
        add(f"| F1-Score | {qivae_result.f1_score:.4f} |")
        add(f"| Training Time | {qivae_result.train_time:.2f}s |")
        add()
        
        qivae_f1 = qivae_result.f1_score
    except Exception as e:
        add(f"**Error:** QI-VAE failed - {e}")
        add()
        qivae_f1 = 0
    
    # Summary comparison
    add("## Summary Comparison")
    add()
    
    add("| Approach | Model | F1-Score |")
    add("|----------|-------|----------|")
    add(f"| Classical | {best_classical.name} | **{best_classical.f1:.4f}** |")
    if qsvm_available:
        add(f"| Quantum QSVM | ZZ Feature Map | {qsvm_f1:.4f} |")
    add(f"| QI-VAE | Anomaly Detection | {qivae_f1:.4f} |")
    add()
    
    # Analysis
    add("## Analysis")
    add()
    
    if best_classical.f1 > qsvm_f1:
        add("Classical models outperform quantum approaches on this synthetic dataset, which is expected for several reasons:")
        add()
        add("1. **Dataset size:** Quantum kernels are limited to ~200 samples for computational feasibility")
        add("2. **Simulation overhead:** Qiskit simulation on CPU is much slower than classical methods")
        add("3. **Synthetic data:** The synthetic dataset may not have patterns that quantum kernels excel at capturing")
        add()
        add("**Key insight:** Quantum advantage is expected on real-world zero-day detection where:")
        add("- Feature correlations are complex and high-dimensional")
        add("- The classification boundary is non-linear in ways classical kernels can't capture")
        add("- Access to real quantum hardware eliminates simulation overhead")
    else:
        add("Quantum QSVM shows competitive performance with classical methods!")
        add()
        add("This suggests the quantum kernel is effectively capturing relevant feature correlations.")
    
    add()
    add("---")
    add()
    add("*Report generated by QZero - Quantum Zero-Day Detection System*")
    add()
    add("*For iQuHACK 2026*")
    
    # Join report
    report = "\n".join(report_lines)
    
    # Write to file if path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report)
        print(f"\nReport saved to: {output_path}", flush=True)
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate QZero experiment report")
    parser.add_argument("--samples", type=int, default=1000, help="Number of samples")
    parser.add_argument("--qubits", type=int, default=4, help="Number of qubits")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--output", "-o", type=str, default="results/report.md", help="Output file path")
    parser.add_argument("--print", action="store_true", help="Print report to stdout")
    
    args = parser.parse_args()
    
    try:
        from tabulate import tabulate
    except ImportError:
        print("Installing tabulate...", flush=True)
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "tabulate", "-q"])
    
    report = generate_report(
        n_samples=args.samples,
        n_qubits=args.qubits,
        difficulty=args.difficulty,
        output_path=args.output,
    )
    
    if args.print:
        print("\n" + "=" * 60, flush=True)
        print(report, flush=True)


if __name__ == "__main__":
    main()
