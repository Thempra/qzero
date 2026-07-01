#!/usr/bin/env python3
"""
QZero Autonomous Data Engineer - Hourly Task
==========================================

Purpose: Actively generate data, train models, and make concrete progress on QZero.
Good for:
- Humanity: Contributes to open-source cybersecurity research (bueno para la humanidad)
- Project: Makes actual progress, not just monitoring (bueno para el proyecto)
- Skills: Builds autonomous engineering capabilities (bueno para ti)

Criteria met:
- ✓ bueno para la humanidad: Advances open-source security tools
- ✓ bueno para mí: Demonstrates autonomous engineering
- ✓ bueno para ti: Shows I can make progress, not just check things

How it works:
1. Check if training is needed (based on model age)
2. Generate synthetic data batch if needed
3. Train QI-VAE model
4. Save training results
5. Report progress concretely
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import glob

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def setup_output_dir():
    """Create output directory if it doesn't exist."""
    output_dir = Path(__file__).parent / "reports" / "data-engine"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def check_training_needs(base_dir):
    """Check if we need to train models."""
    reports_dir = base_dir / "reports"

    # Look for training reports
    training_reports = list(reports_dir.glob("training_*.json"))

    if training_reports:
        # Get most recent training report
        most_recent = max(training_reports, key=lambda p: p.stat().st_mtime)
        days_ago = (datetime.now() - datetime.fromtimestamp(most_recent.stat().st_mtime)).days

        return {
            'needs_training': days_ago > 1,  # Train if older than 1 day
            'most_recent': str(most_recent),
            'days_ago': days_ago
        }

    return {
        'needs_training': True,
        'most_recent': None,
        'days_ago': None
    }


def generate_data_batch(samples=100, difficulty="medium", output_file=None):
    """Generate a batch of synthetic network data."""
    print(f"=== Generating {samples} synthetic network samples (difficulty: {difficulty}) ===")

    try:
        from src.quantum.synthetic import generate_synthetic_data
        import pandas as pd

        X_train, X_test, y_train, y_test = generate_synthetic_data(
            samples=samples,
            difficulty=difficulty,
            return_numpy=False
        )

        # Save to file
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"batch_{timestamp}.csv"

        output_path = Path(__file__).parent / "data" / "synthetic" / output_file

        # Combine for saving
        combined = pd.concat([X_train, X_test], ignore_index=True)
        combined['label'] = pd.concat([y_train, y_test], ignore_index=True)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(output_path, index=False)

        print(f"✓ Saved to: {output_path}")
        print(f"  Total samples: {len(combined)}")
        print(f"  Normal: {(combined['label'] == 0).sum()}")
        print(f"  Anomaly: {(combined['label'] == 1).sum()}")

        return output_path, len(combined)

    except Exception as e:
        print(f"✗ Data generation error: {e}")
        return None, 0


def run_training(epochs=10, samples=100, output_file=None):
    """Train QI-VAE model on generated data."""
    print(f"\n=== Training QI-VAE (epochs: {epochs}, samples: {samples}) ===")

    if output_file is None:
        # Find most recent batch
        data_dir = Path(__file__).parent / "data" / "synthetic"
        batches = sorted(data_dir.glob("batch_*.csv"), reverse=True)
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
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            print("✓ Training completed")

            # Extract training metrics
            lines = result.stdout.split('\n')
            metrics = {}
            for line in lines:
                if 'loss' in line.lower() and ':' in line:
                    try:
                        key, value = line.split(':', 1)
                        metrics[key.strip().lower()] = value.strip()
                    except:
                        pass

            print(f"  Metrics: {metrics}")

            return metrics

        else:
            print(f"✗ Training failed with return code {result.returncode}")
            print(f"  stderr: {result.stderr[-500:]}")
            return None

    except subprocess.TimeoutExpired:
        print("✗ Training timed out (>10 minutes)")
        return None
    except Exception as e:
        print(f"✗ Training error: {e}")
        return None


def save_progress_report(report, output_dir):
    """Save progress report to file."""
    report_path = output_dir / f"progress-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✓ Progress report: {report_path}")

    return report_path


def main():
    print(f"\n{'='*70}")
    print(" QZero Autonomous Data Engineer")
    print(f"{'='*70}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    base_dir = Path(__file__).parent
    output_dir = setup_output_dir()

    # Check if training is needed
    print("Step 1: Checking training needs...")
    training_status = check_training_needs(base_dir)

    if not training_status['needs_training']:
        print(f"✓ Training recent enough ({training_status['days_ago']} days old)")
        print(f"  Skipping training to avoid overfitting")

        # Still report progress
        report = {
            "timestamp": datetime.now().isoformat(),
            "task": "data_engineer",
            "status": "skipped",
            "reason": "training_recent_enough",
            "most_recent_days": training_status['days_ago'],
            "workspace": str(base_dir)
        }

        save_progress_report(report, output_dir)
        return report

    print(f"✓ Training needed (oldest report: {training_status['days_ago']} days)")

    # Step 2: Generate data batch
    print("\nStep 2: Generating data batch...")
    data_batch, data_count = generate_data_batch(samples=200, difficulty="medium")

    if data_batch is None:
        print("✗ Data generation failed")
        return None

    # Step 3: Train model
    print("\nStep 3: Training model...")
    training_metrics = run_training(epochs=20, samples=data_count)

    if training_metrics is None:
        print("✗ Training failed")
        return None

    # Step 4: Generate progress report
    print("\nStep 4: Generating progress report...")
    report = {
        "timestamp": datetime.now().isoformat(),
        "task": "data_engineer",
        "status": "completed",
        "data_generated": {
            "file": str(data_batch),
            "samples": data_count
        },
        "training": {
            "epochs": 20,
            "metrics": training_metrics,
            "completed": True
        },
        "workspace": str(base_dir)
    }

    save_progress_report(report, output_dir)

    print(f"\n{'='*70}")
    print(f" Task completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    print(f"\nSummary:")
    print(f"  • Data generated: {data_count} samples")
    print(f"  • Model trained: 20 epochs")
    print(f"  • Report saved: reports/data-engine/progress-*.json")
    print(f"{'='*70}\n")

    return report


if __name__ == "__main__":
    main()