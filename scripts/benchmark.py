#!/usr/bin/env python3
"""
QZero Benchmark Script
Runs full pipeline: data generation → classical baselines → quantum models → comparison
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import time
from datetime import datetime
from tabulate import tabulate

# Project imports
from src.preprocessing.data_loader import generate_synthetic_data, DataLoader
from src.preprocessing.feature_engineering import FeatureEngineer
from src.classical.baseline import ClassicalBaseline, run_all_baselines, print_comparison_table
from src.quantum.qsvm import QSVM, QSVMConfig
from src.evaluation.metrics import evaluate_model, print_evaluation_report

def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def run_benchmark(n_samples: int = 2000, n_qubits: int = 4, difficulty: str = "medium"):
    """Run full benchmark."""
    
    print_header("QZero Benchmark")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Samples: {n_samples} | Qubits: {n_qubits} | Difficulty: {difficulty}")
    
    # 1. Generate synthetic data
    print_header("1. Data Generation")
    X, y = generate_synthetic_data(n_samples=n_samples, difficulty=difficulty)
    print(f"Generated {len(X)} samples with {X.shape[1]} features")
    print(f"Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")
    
    # 2. Feature engineering
    print_header("2. Feature Engineering")
    engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method='pca')
    X_reduced = engineer.fit_transform(X)
    print(f"Reduced to {X_reduced.shape[1]} features (for {n_qubits} qubits)")
    
    # Split data
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X_reduced, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")
    
    # 3. Classical baselines
    print_header("3. Classical Baselines")
    classical_results = run_all_baselines(X_train, y_train, X_test, y_test)
    print_comparison_table(classical_results)
    
    # 4. Quantum QSVM
    print_header("4. Quantum QSVM")
    
    # Use smaller subset for quantum (computational limits)
    max_quantum = min(200, len(X_train))
    X_train_q = X_train[:max_quantum]
    y_train_q = y_train[:max_quantum]
    X_test_q = X_test[:min(50, len(X_test))]
    y_test_q = y_test[:min(50, len(y_test))]
    
    print(f"Quantum subset: Train {len(X_train_q)} | Test {len(X_test_q)}")
    
    qsvm_config = QSVMConfig(
        n_qubits=n_qubits,
        feature_map_reps=2,
        use_classical_fallback=True
    )
    
    qsvm = QSVM(config=qsvm_config)
    
    start = time.time()
    try:
        qsvm.fit(X_train_q, y_train_q)
        y_pred = qsvm.predict(X_test_q)
        qsvm_time = time.time() - start
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        qsvm_accuracy = accuracy_score(y_test_q, y_pred)
        qsvm_precision = precision_score(y_test_q, y_pred, average='weighted', zero_division=0)
        qsvm_recall = recall_score(y_test_q, y_pred, average='weighted', zero_division=0)
        qsvm_f1 = f1_score(y_test_q, y_pred, average='weighted', zero_division=0)
        
        print(f"QSVM Results:")
        print(f"  Accuracy:  {qsvm_accuracy:.4f}")
        print(f"  Precision: {qsvm_precision:.4f}")
        print(f"  Recall:    {qsvm_recall:.4f}")
        print(f"  F1-Score:  {qsvm_f1:.4f}")
        print(f"  Time:      {qsvm_time:.2f}s")
        print(f"  Backend:   {'Quantum Kernel' if qsvm.used_quantum else 'Classical Fallback'}")
        
    except Exception as e:
        print(f"QSVM Error: {e}")
        qsvm_accuracy = 0
        qsvm_f1 = 0
        qsvm_time = 0
    
    # 5. Comparison Summary
    print_header("5. Summary Comparison")
    
    # Get best classical
    best_classical = max(classical_results, key=lambda x: x.f1_score)
    
    comparison = [
        ["Best Classical", best_classical.model_name, f"{best_classical.f1_score:.4f}"],
        ["Quantum QSVM", "QSVM", f"{qsvm_f1:.4f}"],
    ]
    
    print(tabulate(comparison, headers=["Type", "Model", "F1-Score"], tablefmt="grid"))
    
    print_header("Benchmark Complete")
    
    return {
        'classical': [r.to_dict() for r in classical_results],
        'quantum': {
            'accuracy': qsvm_accuracy,
            'f1': qsvm_f1,
            'time': qsvm_time
        }
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="QZero Benchmark")
    parser.add_argument("--samples", type=int, default=1000, help="Number of samples")
    parser.add_argument("--qubits", type=int, default=4, help="Number of qubits")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default="medium")
    
    args = parser.parse_args()
    
    try:
        from tabulate import tabulate
    except ImportError:
        print("Installing tabulate...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "tabulate", "-q"])
        from tabulate import tabulate
    
    run_benchmark(
        n_samples=args.samples,
        n_qubits=args.qubits,
        difficulty=args.difficulty
    )
