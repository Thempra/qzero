#!/usr/bin/env python3
"""
Autonomous QZero Task - Hourly Script
=====================================

Purpose: Generate synthetic network traffic data and optionally train models.
Good for: QZero project progress (data generation), cybersecurity research (open source contribution),
          skill building (ML/data generation).

Criteria met:
- bueno para la humanidad: Contributes to open-source security research
- bueno para mí: Learning data generation and ML workflows
- bueno para ti: Makes concrete progress on the project

How it works:
1. Generates synthetic network traffic data (NetFlow style)
2. Saves to data/synthetic/ with timestamp
3. Optionally trains QI-VAE model on new data
4. Reports progress

Run with: python3 autonomous-hourly.py [--train] [--samples NUM]
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from preprocessing.data_loader import generate_synthetic_data


def setup_data_dir():
    """Create data directory if it doesn't exist."""
    data_dir = Path(__file__).parent / "data"
    synthetic_dir = data_dir / "synthetic"

    synthetic_dir.mkdir(parents=True, exist_ok=True)
    return synthetic_dir


def generate_data_batch(samples=100, difficulty="medium", output_file=None):
    """Generate a batch of synthetic data."""
    print(f"=== Generating {samples} synthetic samples (difficulty: {difficulty}) ===")

    # Generate data using existing function
    X_train, X_test, y_train, y_test = generate_synthetic_data(
        samples=samples,
        difficulty=difficulty,
        return_numpy=False
    )

    # Save to file
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"batch_{timestamp}.csv"

    output_path = setup_data_dir() / output_file

    # Combine for saving
    combined = pd.concat([X_train, X_test], ignore_index=True)
    combined['label'] = pd.concat([y_train, y_test], ignore_index=True)

    combined.to_csv(output_path, index=False)

    print(f"✓ Saved to: {output_path}")
    print(f"  Total samples: {len(combined)}")
    print(f"  Normal: {(combined['label'] == 0).sum()}")
    print(f"  Anomaly: {(combined['label'] == 1).sum()}")

    return output_path, len(combined)


def run_training(output_file=None, epochs=10):
    """Train QI-VAE on the generated data."""
    print(f"\n=== Training QI-VAE on new data (epochs: {epochs}) ===")

    if output_file is None:
        # Find most recent batch
        synthetic_dir = setup_data_dir()
        batches = sorted(synthetic_dir.glob("batch_*.csv"), reverse=True)
        if not batches:
            print("✗ No data files found")
            return None
        output_file = batches[0]

    print(f"Using data: {output_file}")

    # Run training command
    cmd = [
        sys.executable, "-m", "qzero_cli",
        "train",
        "--samples", "0",  # Use file
        "--real-data",
        "--epochs", str(epochs),
        "--output-file", "training_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            print("✓ Training completed")
            # Find and print last few lines (results summary)
            lines = result.stdout.split('\n')
            for line in lines[-15:]:
                print(f"  {line}")
            return True
        else:
            print(f"✗ Training failed with return code {result.returncode}")
            print(f"  stderr: {result.stderr[-500:]}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Training timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"✗ Training error: {e}")
        return False


def generate_report(samples=100, trained=False):
    """Generate a summary report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "task": "autonomous_hourly",
        "samples_generated": samples,
        "training_completed": trained,
        "workspace": str(Path(__file__).parent)
    }

    report_path = Path(__file__).parent / "reports" / f"hourly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n=== Report saved ===")
    print(f"  {report_path}")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Autonomous QZero Hourly Task")
    parser.add_argument("--train", action="store_true", help="Run training after data generation")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples to generate")
    parser.add_argument("--difficulty", type=str, default="medium", choices=["easy", "medium", "hard"],
                       help="Difficulty level for synthetic data")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(" autonomous-hourly.py - QZero Autonomous Task")
    print(f"{'='*60}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Samples: {args.samples}")
    print(f" Difficulty: {args.difficulty}")
    print(f" Training: {'Yes' if args.train else 'No'}")
    print(f"{'='*60}\n")

    # Step 1: Generate data
    data_path, samples_count = generate_data_batch(
        samples=args.samples,
        difficulty=args.difficulty
    )

    # Step 2: Optional training
    trained = False
    if args.train:
        trained = run_training(output_file=data_path, epochs=args.epochs)

    # Step 3: Report
    generate_report(samples=samples_count, trained=trained)

    print(f"\n{'='*60}")
    print(f" Task completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()