#!/usr/bin/env python3
"""
QZero Command Line Interface

Simple CLI for running QZero detection and evaluation.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio
import numpy as np
import pandas as pd

from src.preprocessing.data_loader import generate_synthetic_data, DataLoader
from src.preprocessing.feature_engineering import FeatureEngineer
from src.classical.baseline import ClassicalBaseline, run_all_baselines, print_comparison_table
from src.quantum.qivae import QIVAE, QIVAEConfig
from src.evaluation.metrics import evaluate_model, print_evaluation_report


def cmd_train(config: argparse.Namespace):
    """Train models and show results."""
    print(f"\n{'='*60}")
    print("QZero Training & Evaluation")
    print(f"{'='*60}\n")

    # Load or generate data
    if config.real_data and (Path("data/raw/final(2).csv").exists()):
        print("Loading UGRansome dataset...")
        loader = DataLoader()
        X, y = loader.load_ugransome()

        # Sample if needed
        if config.samples > 0 and config.samples < len(X):
            from sklearn.model_selection import train_test_split
            X, _, y, _ = train_test_split(
                X, y, train_size=config.samples, stratify=y, random_state=42
            )

        # Convert labels
        y = (y == 1).astype(int)

        print(f"Loaded {len(X)} samples with {X.shape[1]} features")
    else:
        print(f"Generating synthetic data ({config.samples} samples)...")
        X, y = generate_synthetic_data(
            n_samples=config.samples,
            difficulty=config.difficulty
        )
        print(f"Generated {len(X)} samples with {X.shape[1]} features")

    print(f"Class distribution: Normal={sum(y==0)}, Anomaly={sum(y==1)}")

    # Feature engineering
    print("\nFeature engineering...")
    engineer = FeatureEngineer(n_qubits=config.n_qubits, reduction_method="pca")
    X_reduced = engineer.fit_transform(X)
    print(f"Reduced to {X_reduced.shape[1]} features (for {config.n_qubits} qubits)")

    # Split data
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X_reduced, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # Train classical models
    if config.models:
        print("\n" + "="*60)
        print("Classical Baselines")
        print("="*60)
        models = config.models.split(",")
        results = run_all_baselines(X_train, y_train, X_test, y_test, models=models)
        print_comparison_table(results)

    # Train QI-VAE
    print("\n" + "="*60)
    print("Quantum-Inspired VAE (QI-VAE)")
    print("="*60)

    # Train on normal samples only
    normal_mask = y_train == 0
    X_train_normal = X_train[normal_mask]
    print(f"Training on {len(X_train_normal)} normal samples")

    qivae_config = QIVAEConfig(
        input_dim=X_train.shape[1],
        latent_dim=4,
        hidden_dims=tuple(config.hidden_dims),
        epochs=config.epochs,
        batch_size=config.batch_size,
        beta=1.0,
        anomaly_threshold_percentile=config.anomaly_threshold,
    )

    qivae = QIVAE(qivae_config)
    result = qivae.fit_evaluate(X_train_normal, X_test, y_test, verbose=True)

    print("\n" + "="*60)
    print("QI-VAE Results")
    print("="*60)
    print(f"Training Loss:      {result.train_loss:.4f}")
    print(f"Validation Loss:    {result.val_loss:.4f}")
    print(f"Anomaly Threshold:  {result.anomaly_threshold:.4f}")
    print(f"Accuracy:           {result.accuracy:.4f}")
    print(f"Precision:          {result.precision:.4f}")
    print(f"Recall:             {result.recall:.4f}")
    print(f"F1 Score:           {result.f1_score:.4f}")
    print(f"Training Time:      {result.train_time:.2f}s")
    print("="*60)

    # Save results
    if config.output_file:
        print(f"\nSaving results to {config.output_file}...")
        results_dict = {
            'classical': [r.to_dict() for r in results] if results else None,
            'qivae': {
                'accuracy': result.accuracy,
                'precision': result.precision,
                'recall': result.recall,
                'f1_score': result.f1_score,
                'train_loss': result.train_loss,
                'val_loss': result.val_loss,
                'anomaly_threshold': result.anomaly_threshold,
                'train_time': result.train_time,
            },
            'config': {
                'n_samples': config.samples,
                'n_qubits': config.n_qubits,
                'difficulty': config.difficulty,
            }
        }
        import json
        with open(config.output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        print(f"Saved!")


async def cmd_detect(config: argparse.Namespace):
    """Run real-time detection."""
    print(f"\n{'='*60}")
    print("QZero Real-Time Detection")
    print(f"{'='*60}\n")

    from detection import (
        DetectionStream,
        QZeroDetector,
        NetFlowHandler,
        PCAPHandler,
        LoggerHandler,
    )

    # Setup stream
    if config.stream == "netflow":
        handler = NetFlowHandler()
        print("Stream: NetFlow (mock data)")
    elif config.stream == "pcap":
        handler = PCAPHandler()
        print("Stream: PCAP (mock data)")
    elif config.stream == "logs":
        handler = LoggerHandler()
        print("Stream: Logs (mock data)")
    else:
        print(f"Unknown stream: {config.stream}")
        sys.exit(1)

    # Create detector
    detector = QZeroDetector()

    if config.model == "qivae":
        from src.predictor import QZeroPredictor
        predictor = QZeroPredictor(model_type="qivae", n_qubits=config.n_qubits)
        detector.predictor = predictor
        print(f"Model: QI-VAE ({config.n_qubits} qubits)")
    else:
        print(f"Model: {config.model}")

    detector.add_stream_handler(handler)

    # Process stream
    print(f"\nProcessing {config.max_samples} samples...\n")

    try:
        results = await detector.process_stream(handler, max_samples=config.max_samples)
        stats = detector.get_statistics()

        print(f"\n{'='*60}")
        print("Detection Statistics")
        print(f"{'='*60}")
        print(f"Total samples:     {stats['total_samples']}")
        print(f"Anomalies:         {stats['anomalies_detected']}")
        print(f"Anomaly rate:      {stats['anomaly_rate']:.2%}")
        print(f"Mean score:        {stats['mean_anomaly_score']:.3f}")
        print(f"Max score:         {stats['max_anomaly_score']:.3f}")
        print(f"Critical alerts:   {stats['critical_alerts']}")
        print(f"{'='*60}")

        if stats['critical_alerts'] > 0:
            print(f"\n⚠️  CRITICAL ALERTS DETECTED!")
            print(f"   Review the alert log for details.\n")
        else:
            print(f"\n✓ No critical alerts detected.\n")

        # Show top anomalies
        if len(detector.current_results) > 0:
            print(f"\nTop {min(5, len(detector.current_results))} anomalies by score:")
            sorted_results = sorted(
                detector.current_results,
                key=lambda x: x.anomaly_score,
                reverse=True
            )
            for i, r in enumerate(sorted_results[:5], 1):
                print(f"  {i}. Score: {r.anomaly_score:.4f} | "
                      f"{'Anomaly' if r.is_anomaly else 'Normal'} | "
                      f"{r.severity.upper()}")

    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="QZero - Quantum Zero-Day Detection CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default settings
  python qzero-cli.py train --samples 1000

  # Train with real data
  python qzero-cli.py train --real-data

  # Run real-time detection
  python qzero-cli.py detect --stream netflow --model qivae --samples 50

  # Compare multiple classical models
  python qzero-cli.py train --models random_forest,svm_rbf,logistic_regression
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Train command
    train_parser = subparsers.add_parser("train", help="Train models and evaluate")
    train_parser.add_argument("--samples", type=int, default=1000,
                            help="Number of samples")
    train_parser.add_argument("--real-data", action="store_true",
                            help="Use real UGRansome dataset")
    train_parser.add_argument("--difficulty", choices=["easy", "medium", "hard"],
                            default="medium", help="Difficulty for synthetic data")
    train_parser.add_argument("--n-qubits", type=int, default=4,
                            help="Number of qubits")
    train_parser.add_argument("--hidden-dims", type=str, default="64,32",
                            help="Hidden layer dimensions (comma-separated)")
    train_parser.add_argument("--epochs", type=int, default=50,
                            help="Training epochs")
    train_parser.add_argument("--batch-size", type=int, default=32,
                            help="Batch size")
    train_parser.add_argument("--anomaly-threshold", type=float, default=95.0,
                            help="Anomaly threshold percentile")
    train_parser.add_argument("--models", type=str, default="",
                            help="Classical models to run (comma-separated)")
    train_parser.add_argument("--output-file", type=str, default="",
                            help="Output JSON file for results")
    train_parser.set_defaults(func=cmd_train)

    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Run real-time detection")
    detect_parser.add_argument("--stream", type=str, default="netflow",
                             choices=["netflow", "pcap", "logs"],
                             help="Stream type")
    detect_parser.add_argument("--model", type=str, default="qivae",
                             choices=["qivae", "classical"],
                             help="Model type")
    detect_parser.add_argument("--n-qubits", type=int, default=4,
                            help="Number of qubits")
    detect_parser.add_argument("--max-samples", type=int, default=100,
                            help="Maximum samples to process")
    detect_parser.set_defaults(func=cmd_detect)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Parse hidden_dims
    if hasattr(args, 'hidden_dims'):
        args.hidden_dims = tuple(map(int, args.hidden_dims.split(',')))

    # Run command
    if asyncio.iscoroutinefunction(args.func):
        asyncio.run(args.func(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()