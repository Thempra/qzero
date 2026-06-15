#!/usr/bin/env python3
"""
Benchmark script for QZero.

Runs systematic experiments and saves results for comparison.
Results are saved in JSON format with timestamps for tracking progress.
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from typing import Dict, Any, List, Optional

import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from preprocessing.data_loader import generate_synthetic_data, DataLoader
from preprocessing.feature_engineering import FeatureEngineer
from classical.baseline import run_all_baselines
from quantum.qsvm import QSVM, QSVMConfig, QSVMResult
from quantum.qivae import QIVAE, QIVAEConfig, QIVAEResult
from evaluation.metrics import (
    evaluate_model,
    evaluate_zero_day_detection,
    calculate_quantum_advantage,
)


def run_classical_benchmarks(
    data: Dict[str, np.ndarray],
    models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run classical baseline benchmarks."""
    if models is None:
        models = ["random_forest", "svm_rbf", "gradient_boosting", "mlp", "logistic"]
    
    print("\n🤖 Running classical baselines...")
    results = run_all_baselines(
        data["X_train"],
        data["y_train"],
        data["X_test"],
        data["y_test"],
        models=models
    )
    
    return {
        r.name: {
            "accuracy": r.accuracy,
            "f1": r.f1,
            "train_time": r.train_time,
        }
        for r in results
    }


def run_qsvm_benchmark(
    data: Dict[str, np.ndarray],
    n_qubits: int = 4,
    max_samples: int = 300,
) -> Dict[str, Any]:
    """Run QSVM benchmark with quantum features."""
    print(f"\n⚛️ Running QSVM ({n_qubits} qubits, {max_samples} samples)...")
    
    # Prepare quantum features
    engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method="pca")
    X_train_q = engineer.fit_transform(data["X_train"], data["y_train"])
    X_test_q = engineer.transform(data["X_test"])
    
    config = QSVMConfig(
        n_qubits=n_qubits,
        max_samples_quantum=max_samples,
        use_classical_fallback=True,
    )
    
    qsvm = QSVM(config)
    result = qsvm.fit_evaluate(
        X_train_q[:max_samples],
        data["y_train"][:max_samples],
        X_test_q,
        data["y_test"]
    )
    
    return {
        "accuracy": result.accuracy,
        "f1_score": result.f1_score,
        "train_time": result.train_time,
        "kernel_time": result.kernel_computation_time,
        "n_support_vectors": result.n_support_vectors,
        "used_quantum": result.used_quantum,
        "n_qubits": n_qubits,
        "n_samples": max_samples,
    }


def run_qivae_benchmark(
    data: Dict[str, np.ndarray],
    latent_dim: int = 4,
    epochs: int = 50,
) -> Dict[str, Any]:
    """Run QI-VAE benchmark for anomaly detection."""
    print(f"\n🔮 Running QI-VAE (latent_dim={latent_dim}, epochs={epochs})...")
    
    # Train on normal samples only
    normal_mask = data["y_train"] == 0
    X_train_normal = data["X_train"][normal_mask]
    
    config = QIVAEConfig(
        input_dim=data["X_train"].shape[1],
        latent_dim=latent_dim,
        hidden_dims=(64, 32),
        epochs=epochs,
        batch_size=32,
        beta=1.0,
        anomaly_threshold_percentile=95.0,
    )
    
    qivae = QIVAE(config)
    result = qivae.fit_evaluate(
        X_train_normal,
        data["X_test"],
        data["y_test"],
        verbose=False,
    )
    
    return {
        "accuracy": result.accuracy,
        "precision": result.precision,
        "recall": result.recall,
        "f1_score": result.f1_score,
        "train_loss": result.train_loss,
        "val_loss": result.val_loss,
        "anomaly_threshold": result.anomaly_threshold,
        "train_time": result.train_time,
        "latent_dim": latent_dim,
        "epochs": epochs,
        "n_train_normal": len(X_train_normal),
    }


def run_full_benchmark(
    n_samples: int = 5000,
    n_qubits: int = 4,
    qsvm_samples: int = 300,
    qivae_epochs: int = 50,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Run full benchmark suite."""
    
    benchmark_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("=" * 70)
    print("QZero Benchmark Suite")
    print(f"ID: {benchmark_id}")
    print("=" * 70)
    
    # Generate data
    print(f"\n📊 Generating {n_samples} samples...")
    start = time.time()
    X, y = generate_synthetic_data(
        n_samples=n_samples,
        anomaly_ratio=0.15,
        signature_ratio=0.20,
        random_state=random_state,
    )
    
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)
    data_time = time.time() - start
    
    print(f"  Train: {data['X_train'].shape}")
    print(f"  Val:   {data['X_val'].shape}")
    print(f"  Test:  {data['X_test'].shape}")
    
    # Run benchmarks
    classical_results = run_classical_benchmarks(data)
    qsvm_results = run_qsvm_benchmark(data, n_qubits, qsvm_samples)
    qivae_results = run_qivae_benchmark(data, latent_dim=4, epochs=qivae_epochs)
    
    # Calculate quantum advantage
    best_classical = max(classical_results.values(), key=lambda x: x["f1"])
    qsvm_advantage = calculate_quantum_advantage(
        {"accuracy": qsvm_results["accuracy"], "f1": qsvm_results["f1_score"]},
        {"accuracy": best_classical["accuracy"], "f1": best_classical["f1"]},
    )
    
    # Compile results
    results = {
        "benchmark_id": benchmark_id,
        "timestamp": datetime.now().isoformat(),
        "config": {
            "n_samples": n_samples,
            "n_qubits": n_qubits,
            "qsvm_samples": qsvm_samples,
            "qivae_epochs": qivae_epochs,
            "random_state": random_state,
        },
        "data_info": {
            "train_size": len(data["X_train"]),
            "val_size": len(data["X_val"]),
            "test_size": len(data["X_test"]),
            "n_features": data["X_train"].shape[1],
            "data_prep_time": data_time,
        },
        "classical": classical_results,
        "qsvm": qsvm_results,
        "qivae": qivae_results,
        "quantum_advantage": qsvm_advantage,
    }
    
    return results


def print_summary(results: Dict[str, Any]) -> None:
    """Print benchmark summary."""
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    
    print("\n📊 Classical Baselines:")
    print(f"{'Model':<25} {'Accuracy':>12} {'F1':>12} {'Time (s)':>12}")
    print("-" * 61)
    for name, metrics in sorted(
        results["classical"].items(),
        key=lambda x: x[1]["f1"],
        reverse=True
    ):
        print(f"{name:<25} {metrics['accuracy']:>12.4f} {metrics['f1']:>12.4f} {metrics['train_time']:>12.2f}")
    
    print("\n⚛️ QSVM:")
    qsvm = results["qsvm"]
    print(f"  Accuracy:        {qsvm['accuracy']:.4f}")
    print(f"  F1 Score:        {qsvm['f1_score']:.4f}")
    print(f"  Used Quantum:    {qsvm['used_quantum']}")
    print(f"  Training Time:   {qsvm['train_time']:.2f}s")
    
    print("\n🔮 QI-VAE (Anomaly Detection):")
    qivae = results["qivae"]
    print(f"  Accuracy:        {qivae['accuracy']:.4f}")
    print(f"  Precision:       {qivae['precision']:.4f}")
    print(f"  Recall:          {qivae['recall']:.4f}")
    print(f"  F1 Score:        {qivae['f1_score']:.4f}")
    print(f"  Training Time:   {qivae['train_time']:.2f}s")
    
    print("\n📈 Quantum Advantage:")
    for key, value in results["quantum_advantage"].items():
        print(f"  {key}: {value:+.2f}%")
    
    print("\n" + "=" * 70)


def save_results(results: Dict[str, Any], output_dir: Path) -> Path:
    """Save benchmark results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"benchmark_{results['benchmark_id']}.json"
    filepath = output_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filepath}")
    return filepath


def load_and_compare(results_dir: Path, n: int = 5) -> None:
    """Load and compare recent benchmark results."""
    results_files = sorted(results_dir.glob("benchmark_*.json"), reverse=True)[:n]
    
    if not results_files:
        print("No benchmark results found.")
        return
    
    print("\n📊 Recent Benchmark Comparison:")
    print("-" * 80)
    print(f"{'ID':<20} {'Best Classical F1':>20} {'QSVM F1':>15} {'QI-VAE F1':>15}")
    print("-" * 80)
    
    for filepath in results_files:
        with open(filepath) as f:
            r = json.load(f)
        
        best_classical_f1 = max(m["f1"] for m in r["classical"].values())
        qsvm_f1 = r["qsvm"]["f1_score"]
        qivae_f1 = r["qivae"]["f1_score"]
        
        print(f"{r['benchmark_id']:<20} {best_classical_f1:>20.4f} {qsvm_f1:>15.4f} {qivae_f1:>15.4f}")


def main():
    parser = argparse.ArgumentParser(description="QZero Benchmark Suite")
    parser.add_argument("--samples", type=int, default=5000, help="Number of samples")
    parser.add_argument("--qubits", type=int, default=4, help="Number of qubits")
    parser.add_argument("--qsvm-samples", type=int, default=300, help="QSVM training samples")
    parser.add_argument("--qivae-epochs", type=int, default=50, help="QI-VAE epochs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=Path, default=Path("results"), help="Output directory")
    parser.add_argument("--compare", action="store_true", help="Compare recent results")
    parser.add_argument("--no-save", action="store_true", help="Don't save results")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    output_dir = project_root / args.output
    
    if args.compare:
        load_and_compare(output_dir)
        return 0
    
    # Run benchmark
    results = run_full_benchmark(
        n_samples=args.samples,
        n_qubits=args.qubits,
        qsvm_samples=args.qsvm_samples,
        qivae_epochs=args.qivae_epochs,
        random_state=args.seed,
    )
    
    print_summary(results)
    
    if not args.no_save:
        save_results(results, output_dir)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
