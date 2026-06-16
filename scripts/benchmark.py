#!/usr/bin/env python3
"""
Benchmark script for QZero models.

Compares quantum and classical models on anomaly detection task.
Outputs performance metrics and timing comparisons.

Usage:
    python scripts/benchmark.py [--samples 1000] [--output results/benchmark.json]
"""

import sys
import argparse
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)

from preprocessing.data_loader import generate_synthetic_data, DataLoader

# Try importing models
try:
    from classical.baseline import RandomForestBaseline, XGBoostBaseline, IsolationForestBaseline
    CLASSICAL_AVAILABLE = True
except ImportError:
    CLASSICAL_AVAILABLE = False
    print("Warning: Classical baselines not available")

try:
    from quantum.qivae import QIVAE, QIVAEConfig
    QIVAE_AVAILABLE = True
except ImportError:
    QIVAE_AVAILABLE = False
    print("Warning: QI-VAE not available (needs PyTorch)")

try:
    from quantum.qsvm import QSVM, QSVMConfig
    QSVM_AVAILABLE = True
except ImportError:
    QSVM_AVAILABLE = False
    print("Warning: QSVM not available (needs Qiskit)")


@dataclass
class BenchmarkResult:
    """Results from a single model benchmark."""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    train_time: float
    predict_time: float
    confusion_matrix: List[List[int]]
    n_samples_train: int
    n_samples_test: int
    extra_info: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Convert numpy types to Python types for JSON serialization
        def convert(obj):
            if isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj
        return convert(d)


def benchmark_isolation_forest(X_train: np.ndarray, y_train: np.ndarray,
                                X_test: np.ndarray, y_test: np.ndarray) -> BenchmarkResult:
    """Benchmark Isolation Forest (unsupervised)."""
    from sklearn.ensemble import IsolationForest
    
    # Train on all data (unsupervised)
    model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    
    start = time.time()
    model.fit(X_train)
    train_time = time.time() - start
    
    start = time.time()
    # IsolationForest returns -1 for anomalies, 1 for normal
    y_pred_raw = model.predict(X_test)
    y_pred = (y_pred_raw == -1).astype(int)  # Convert to 0/1
    y_scores = -model.decision_function(X_test)  # Higher = more anomalous
    predict_time = time.time() - start
    
    return BenchmarkResult(
        model_name="IsolationForest",
        accuracy=accuracy_score(y_test, y_pred),
        precision=precision_score(y_test, y_pred, zero_division=0),
        recall=recall_score(y_test, y_pred, zero_division=0),
        f1_score=f1_score(y_test, y_pred, zero_division=0),
        roc_auc=roc_auc_score(y_test, y_scores),
        train_time=train_time,
        predict_time=predict_time,
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        n_samples_train=len(X_train),
        n_samples_test=len(X_test),
        extra_info={"contamination": 0.1, "n_estimators": 100}
    )


def benchmark_random_forest(X_train: np.ndarray, y_train: np.ndarray,
                             X_test: np.ndarray, y_test: np.ndarray) -> BenchmarkResult:
    """Benchmark Random Forest (supervised)."""
    from sklearn.ensemble import RandomForestClassifier
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    start = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start
    
    start = time.time()
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    predict_time = time.time() - start
    
    return BenchmarkResult(
        model_name="RandomForest",
        accuracy=accuracy_score(y_test, y_pred),
        precision=precision_score(y_test, y_pred, zero_division=0),
        recall=recall_score(y_test, y_pred, zero_division=0),
        f1_score=f1_score(y_test, y_pred, zero_division=0),
        roc_auc=roc_auc_score(y_test, y_proba),
        train_time=train_time,
        predict_time=predict_time,
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        n_samples_train=len(X_train),
        n_samples_test=len(X_test),
        extra_info={"n_estimators": 100}
    )


def benchmark_xgboost(X_train: np.ndarray, y_train: np.ndarray,
                       X_test: np.ndarray, y_test: np.ndarray) -> BenchmarkResult:
    """Benchmark XGBoost (supervised)."""
    try:
        from xgboost import XGBClassifier
    except ImportError:
        return None
    
    model = XGBClassifier(n_estimators=100, random_state=42, use_label_encoder=False, 
                          eval_metric='logloss', verbosity=0)
    
    start = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start
    
    start = time.time()
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    predict_time = time.time() - start
    
    return BenchmarkResult(
        model_name="XGBoost",
        accuracy=accuracy_score(y_test, y_pred),
        precision=precision_score(y_test, y_pred, zero_division=0),
        recall=recall_score(y_test, y_pred, zero_division=0),
        f1_score=f1_score(y_test, y_pred, zero_division=0),
        roc_auc=roc_auc_score(y_test, y_proba),
        train_time=train_time,
        predict_time=predict_time,
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        n_samples_train=len(X_train),
        n_samples_test=len(X_test),
        extra_info={"n_estimators": 100}
    )


def benchmark_qivae(X_train: np.ndarray, y_train: np.ndarray,
                    X_test: np.ndarray, y_test: np.ndarray) -> Optional[BenchmarkResult]:
    """Benchmark QI-VAE (unsupervised anomaly detection)."""
    if not QIVAE_AVAILABLE:
        return None
    
    # Train only on normal samples
    normal_mask = y_train == 0
    X_train_normal = X_train[normal_mask]
    
    config = QIVAEConfig(
        input_dim=X_train.shape[1],
        latent_dim=4,
        hidden_dims=(64, 32),
        epochs=30,
        batch_size=32,
        beta=0.5,
        anomaly_threshold_percentile=85.0,
    )
    
    model = QIVAE(config)
    
    start = time.time()
    model.fit(X_train_normal, verbose=False)
    train_time = time.time() - start
    
    start = time.time()
    y_pred = model.predict(X_test)
    y_scores = model.predict_anomaly_scores(X_test)
    predict_time = time.time() - start
    
    return BenchmarkResult(
        model_name="QI-VAE",
        accuracy=accuracy_score(y_test, y_pred),
        precision=precision_score(y_test, y_pred, zero_division=0),
        recall=recall_score(y_test, y_pred, zero_division=0),
        f1_score=f1_score(y_test, y_pred, zero_division=0),
        roc_auc=roc_auc_score(y_test, y_scores),
        train_time=train_time,
        predict_time=predict_time,
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        n_samples_train=len(X_train_normal),
        n_samples_test=len(X_test),
        extra_info={
            "latent_dim": config.latent_dim,
            "epochs": config.epochs,
            "threshold": model.anomaly_threshold,
        }
    )


def benchmark_qsvm(X_train: np.ndarray, y_train: np.ndarray,
                   X_test: np.ndarray, y_test: np.ndarray,
                   max_samples: int = 200) -> Optional[BenchmarkResult]:
    """Benchmark QSVM (supervised, limited samples due to runtime)."""
    if not QSVM_AVAILABLE:
        return None
    
    # QSVM is slow, limit samples
    if len(X_train) > max_samples:
        idx = np.random.choice(len(X_train), max_samples, replace=False)
        X_train_sub = X_train[idx]
        y_train_sub = y_train[idx]
    else:
        X_train_sub = X_train
        y_train_sub = y_train
    
    # Also limit features for speed
    n_features = min(4, X_train.shape[1])
    X_train_sub = X_train_sub[:, :n_features]
    X_test_sub = X_test[:, :n_features]
    
    from quantum.feature_maps import FeatureMapType
    
    config = QSVMConfig(
        n_qubits=n_features,
        feature_map_type=FeatureMapType.ZZ,
        feature_map_reps=2,
    )
    
    model = QSVM(config)
    
    start = time.time()
    model.fit(X_train_sub, y_train_sub)
    train_time = time.time() - start
    
    start = time.time()
    y_pred = model.predict(X_test_sub)
    predict_time = time.time() - start
    
    # QSVM may not have predict_proba, use raw predictions for AUC
    try:
        y_proba = model.predict_proba(X_test_sub)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)
    except:
        roc_auc = 0.0  # Not available
    
    return BenchmarkResult(
        model_name="QSVM",
        accuracy=accuracy_score(y_test, y_pred),
        precision=precision_score(y_test, y_pred, zero_division=0),
        recall=recall_score(y_test, y_pred, zero_division=0),
        f1_score=f1_score(y_test, y_pred, zero_division=0),
        roc_auc=roc_auc,
        train_time=train_time,
        predict_time=predict_time,
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        n_samples_train=len(X_train_sub),
        n_samples_test=len(X_test),
        extra_info={
            "n_qubits": n_features,
            "feature_map": "zz",
            "max_samples": max_samples,
        }
    )


def run_benchmark(n_samples: int = 1000, output_path: Optional[str] = None) -> Dict[str, Any]:
    """Run full benchmark suite."""
    print(f"\n{'='*60}")
    print("QZero Benchmark Suite")
    print(f"{'='*60}")
    
    # Generate data
    print(f"\nGenerating {n_samples} synthetic samples...")
    X, y = generate_synthetic_data(n_samples=n_samples, random_state=42)
    
    # Prepare data
    loader = DataLoader()
    data = loader.prepare_data(X, y, binary=True)
    
    X_train, y_train = data["X_train"], data["y_train"]
    X_test, y_test = data["X_test"], data["y_test"]
    
    print(f"Training samples: {len(X_train)}")
    print(f"Test samples: {len(X_test)}")
    print(f"Features: {X_train.shape[1]}")
    print(f"Attack ratio (train): {y_train.mean():.2%}")
    print(f"Attack ratio (test): {y_test.mean():.2%}")
    
    results = []
    
    # Classical baselines
    print(f"\n{'='*60}")
    print("Running Classical Baselines...")
    print(f"{'='*60}")
    
    print("\n[1/5] Isolation Forest...")
    try:
        result = benchmark_isolation_forest(X_train, y_train, X_test, y_test)
        results.append(result)
        print(f"      F1: {result.f1_score:.4f}, ROC-AUC: {result.roc_auc:.4f}, Time: {result.train_time:.2f}s")
    except Exception as e:
        print(f"      Error: {e}")
    
    print("\n[2/5] Random Forest...")
    try:
        result = benchmark_random_forest(X_train, y_train, X_test, y_test)
        results.append(result)
        print(f"      F1: {result.f1_score:.4f}, ROC-AUC: {result.roc_auc:.4f}, Time: {result.train_time:.2f}s")
    except Exception as e:
        print(f"      Error: {e}")
    
    print("\n[3/5] XGBoost...")
    try:
        result = benchmark_xgboost(X_train, y_train, X_test, y_test)
        if result:
            results.append(result)
            print(f"      F1: {result.f1_score:.4f}, ROC-AUC: {result.roc_auc:.4f}, Time: {result.train_time:.2f}s")
        else:
            print("      Skipped (not installed)")
    except Exception as e:
        print(f"      Error: {e}")
    
    # Quantum models
    print(f"\n{'='*60}")
    print("Running Quantum Models...")
    print(f"{'='*60}")
    
    print("\n[4/5] QI-VAE...")
    try:
        result = benchmark_qivae(X_train, y_train, X_test, y_test)
        if result:
            results.append(result)
            print(f"      F1: {result.f1_score:.4f}, ROC-AUC: {result.roc_auc:.4f}, Time: {result.train_time:.2f}s")
        else:
            print("      Skipped (PyTorch not installed)")
    except Exception as e:
        print(f"      Error: {e}")
    
    print("\n[5/5] QSVM...")
    # QSVM is slow and unreliable on synthetic data, skip by default
    print("      Skipped (too slow for benchmark, run separately)")
    # try:
    #     result = benchmark_qsvm(X_train, y_train, X_test, y_test, max_samples=200)
    #     if result:
    #         results.append(result)
    #         print(f"      F1: {result.f1_score:.4f}, ROC-AUC: {result.roc_auc:.4f}, Time: {result.train_time:.2f}s")
    #     else:
    #         print("      Skipped (Qiskit not installed)")
    # except Exception as e:
    #     print(f"      Error: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"\n{'Model':<20} {'F1':>8} {'ROC-AUC':>10} {'Train(s)':>10} {'Predict(s)':>12}")
    print("-" * 60)
    
    for r in sorted(results, key=lambda x: x.f1_score, reverse=True):
        print(f"{r.model_name:<20} {r.f1_score:>8.4f} {r.roc_auc:>10.4f} {r.train_time:>10.2f} {r.predict_time:>12.4f}")
    
    print("-" * 60)
    
    # Best model
    if results:
        best = max(results, key=lambda x: x.f1_score)
        print(f"\n🏆 Best Model: {best.model_name} (F1: {best.f1_score:.4f})")
    
    # Save results
    output_data = {
        "metadata": {
            "n_samples": n_samples,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": X_train.shape[1],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "results": [r.to_dict() for r in results]
    }
    
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {output_file}")
    
    return output_data


def main():
    parser = argparse.ArgumentParser(description="QZero Benchmark Suite")
    parser.add_argument("--samples", type=int, default=1000, help="Number of samples to generate")
    parser.add_argument("--output", type=str, default="results/benchmark.json", help="Output file path")
    args = parser.parse_args()
    
    run_benchmark(n_samples=args.samples, output_path=args.output)


if __name__ == "__main__":
    main()
