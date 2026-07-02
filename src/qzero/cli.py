"""
QZero Command Line Interface

Unified CLI for running QZero detection, training, and monitoring.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any
import subprocess
import argparse

from qzero.config import get_config
from qzero.utils import setup_logging, save_json, create_timestamped_filename


def cmd_train(config: argparse.Namespace):
    """Train models and show results."""
    setup_logging(config.verbose)

    print(f"\n{'='*60}")
    print("QZero Training & Evaluation")
    print(f"{'='*60}\n")

    # Load or generate data
    if config.real_data and (Path("data/raw/final(2).csv").exists()):
        print("Loading UGRansome dataset...")
        from src.preprocessing.data_loader import DataLoader
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
        from src.preprocessing.data_loader import generate_synthetic_data
        X, y = generate_synthetic_data(
            n_samples=config.samples,
            difficulty=config.difficulty
        )
        print(f"Generated {len(X)} samples with {X.shape[1]} features")

    print(f"Class distribution: Normal={sum(y==0)}, Anomaly={sum(y==1)}")

    # Feature engineering
    print("\nFeature engineering...")
    from src.preprocessing.feature_engineering import FeatureEngineer
    engineer = FeatureEngineer(n_qubits=config.n_qubits, reduction_method="pca")
    X_reduced = engineer.fit_transform(X)
    print(f"Reduced to {X_reduced.shape[1]} features (for {config.n_qubits} qubits)")

    # Split data
    from sklearn.model_selection import train_test_split
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_reduced, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"Train: {len(X_train)} | Test: {len(X_test)}")
    except ValueError as e:
        # Handle case where stratification fails (e.g., too few samples from a class)
        if "stratify" in str(e) and "too few" in str(e).lower():
            print(f"Warning: {e}")
            print("Falling back to non-stratified split...")
            X_train, X_test, y_train, y_test = train_test_split(
                X_reduced, y, test_size=0.2, random_state=42
            )
            print(f"Train: {len(X_train)} | Test: {len(X_test)}")
        else:
            raise

    # Train classical models
    if config.models:
        print("\n" + "="*60)
        print("Classical Baselines")
        print("="*60)
        from src.classical.baseline import ClassicalBaseline, run_all_baselines, print_comparison_table
        models = config.models.split(",")
        results = run_all_baselines(X_train, y_train, X_test, y_test, models=models)
        print_comparison_table(results)

    # Train QI-VAE
    print("\n" + "="*60)
    print("Quantum-Inspired VAE (QI-FAE)")
    print("="*60)

    # Train on normal samples only
    normal_mask = y_train == 0
    X_train_normal = X_train[normal_mask]
    print(f"Training on {len(X_train_normal)} normal samples")

    from src.quantum.qivae import QIVAE, QIVAEConfig
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
    print("QIVAE Results")
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
        save_json(results_dict, Path(config.output_file))
        print(f"Saved!")


def cmd_batch(config: argparse.Namespace):
    """Batch analyze PCAP or log files."""
    setup_logging(config.verbose)

    print(f"\n{'='*60}")
    print("QZero Batch Analysis")
    print(f"{'='*60}\n")

    files = config.files
    model = config.model
    threshold = config.threshold
    n_qubits = config.n_qubits

    results = []

    for file_path in files:
        print(f"\nAnalyzing: {file_path}")
        print("-" * 60)

        file_path = Path(file_path)

        if not file_path.exists():
            print(f"✗ File not found: {file_path}")
            continue

        try:
            # Setup stream based on file extension
            if file_path.suffix == '.pcap':
                from detection import PCAPHandler
                handler = PCAPHandler()
                stream_type = 'pcap'
            elif file_path.suffix in ['.csv', '.txt', '.log']:
                from detection import LoggerHandler
                handler = LoggerHandler()
                stream_type = 'logs'
            else:
                print(f"✗ Unsupported format: {file_path.suffix}")
                continue

            from detection import QZeroDetector
            detector = QZeroDetector()

            if model == 'qivae':
                from src.predictor import QZeroPredictor
                predictor = QZeroPredictor(
                    n_qubits=n_qubits,
                    use_qsvm=False,
                    use_qivae=True,
                    use_classical=False,
                )
                detector.predictor = predictor
            elif model == 'classical':
                from src.predictor import QZeroPredictor
                predictor = QZeroPredictor(
                    n_qubits=n_qubits,
                    use_qsvm=False,
                    use_qivae=False,
                    use_classical=True,
                )
                detector.predictor = predictor

            result = detector.analyze(file_path, threshold=threshold)
            results.append(result)

            print(f"✓ Analysis completed:")
            print(f"  - Anomalies: {result.get('anomalies', 0)}")
            print(f"  - Threats: {result.get('threats', 0)}")

        except Exception as e:
            print(f"✗ Error analyzing file: {e}")
            continue

    # Save batch results
    if results:
        output_file = create_timestamped_filename("batch-analysis")
        save_json({
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': len(results),
            'results': results
        }, Path(output_file))

        print(f"\n{'='*60}")
        print(f"Batch analysis complete. Results saved to: {output_file}")
        print(f"{'='*60}")


def cmd_detect(config: argparse.Namespace):
    """Real-time detection."""
    setup_logging(config.verbose)

    print(f"\n{'='*60}")
    print("QZero Real-Time Detection")
    print(f"{'='*60}\n")

    interface = config.interface
    mode = config.mode
    threshold = config.threshold
    promiscuous = config.promiscuous

    # Activate promiscuous mode if requested
    if promiscuous:
        print("🔄 Activando modo PROMISCUO...")
        try:
            from qzero.interface.promiscuous import PromiscuousInterface
            interface_obj = PromiscuousInterface(interface)
            interface_obj.activate()
            print(f"✅ Interfaz {interface} activada en modo promiscuo")
        except Exception as e:
            print(f"⚠️  Error activando promiscuo: {e}")
            print("Continuando sin modo promiscuo...")

    # Start detection
    print(f"🔍 Iniciando detección en tiempo real...")
    print(f"   - Interfaz: {interface}")
    print(f"   - Modo: {mode}")
    print(f"   - Umbral: {threshold}")
    print(f"   - Promiscuo: {promiscuous}")

    try:
        from qzero.core.monitor import QZeroMonitor
        monitor = QZeroMonitor(
            interface=interface,
            promiscuous=promiscuous,
            output_dir=config.output
        )
        monitor.start()
    except KeyboardInterrupt:
        print("\n\n⏹️  Detección detenida por usuario")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


def cmd_interface(config: argparse.Namespace):
    """Manage network interfaces."""
    setup_logging(config.verbose)

    interface = config.interface
    action = config.action

    try:
        from qzero.interface.promiscuous import PromiscuousInterface

        interface_obj = PromiscuousInterface(interface)

        if action == "activate":
            interface_obj.activate()
            print(f"✅ Interfaz {interface} activada en modo promiscuo")

        elif action == "deactivate":
            interface_obj.deactivate()
            print(f"⬇️  Interfaz {interface} desactivada")

        elif action == "status":
            status = interface_obj.get_status()
            print(f"📊 Estado: {status}")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def cmd_daemon(config: argparse.Namespace):
    """Start QZero daemon for scheduled tasks."""
    setup_logging(config.verbose)

    print(f"\n{'='*60}")
    print("QZero Daemon")
    print(f"{'='*60}\n")

    try:
        from qzero.daemons.scheduler import QZeroScheduler

        scheduler = QZeroScheduler()
        scheduler.start()

    except KeyboardInterrupt:
        print("\n\n⏹️  Daemon detenido por usuario")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def main():
    """CLI Main"""
    parser = argparse.ArgumentParser(
        prog='qzero',
        description='Sistema de Detección de Anomalías y Monitoreo de Seguridad - QZero v2.0'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='QZero v2.0.0'
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Train command
    train_parser = subparsers.add_parser('train', help='Entrenar modelos')
    train_parser.add_argument('--samples', type=int, default=5000, help='Número de muestras')
    train_parser.add_argument('--difficulty', type=str, default='medium', choices=['easy', 'medium', 'hard'])
    train_parser.add_argument('--n-qubits', type=int, default=4, help='Número de qubits')
    train_parser.add_argument('--epochs', type=int, default=50, help='Epochs de entrenamiento')
    train_parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    train_parser.add_argument('--hidden-dims', type=int, nargs='*', default=[64, 32], help='Dimensiones ocultas')
    train_parser.add_argument('--real-data', action='store_true', help='Usar dataset real')
    train_parser.add_argument('--output-file', type=str, help='Archivo de salida')
    train_parser.add_argument('--models', type=str, help='Modelos clásicos (comma separated)')
    train_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    train_parser.set_defaults(func=cmd_train)

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Análisis por lotes')
    batch_parser.add_argument('files', nargs='+', help='Archivos a analizar')
    batch_parser.add_argument('--model', type=str, default='qivae', choices=['qivae', 'classical'])
    batch_parser.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')
    batch_parser.add_argument('--n-qubits', type=int, default=4, help='Número de qubits')
    batch_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    batch_parser.set_defaults(func=cmd_batch)

    # Detect command
    detect_parser = subparsers.add_parser('detect', help='Detección en tiempo real')
    detect_parser.add_argument('--interface', required=True, help='Interfaz de red')
    detect_parser.add_argument('--mode', type=str, default='real-time', choices=['real-time', 'batch', 'predictive'])
    detect_parser.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')
    detect_parser.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    detect_parser.add_argument('--output', type=str, default='output', help='Directorio de salida')
    detect_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    detect_parser.set_defaults(func=cmd_detect)

    # Interface command
    interface_parser = subparsers.add_parser('interface', help='Gestionar interfaces')
    interface_parser.add_argument('--interface', required=True, help='Interfaz de red')
    interface_parser.add_argument('action', choices=['activate', 'deactivate', 'status'], help='Acción')
    interface_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    interface_parser.set_defaults(func=cmd_interface)

    # Daemon command
    daemon_parser = subparsers.add_parser('daemon', help='Iniciar daemon de tareas')
    daemon_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    daemon_parser.set_defaults(func=cmd_daemon)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()