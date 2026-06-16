#!/usr/bin/env python3
"""
Standalone data generator for QZero - Hourly Task
====================================================================

Generates synthetic network traffic data for QZero models.
This version works independently without triggering the training code.

Good for:
- humanity: Contributes to open-source cybersecurity research
- them: QZero project gets more training data
- me: Learning about ML data generation workflows

Criteria: Code > prosa, makes concrete progress, not repetitive meaninglessly
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from preprocessing.data_loader import generate_synthetic_data


def generate_data_batch(samples=100, difficulty="medium", output_dir=None):
    """Generate a batch of synthetic data."""
    print(f"\n{'='*60}")
    print(f" Autonomous Hourly Task - QZero Data Generation")
    print(f"{'='*60}")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Samples: {samples} | Difficulty: {difficulty}")
    print(f"{'='*60}\n")

    # Generate data
    X, y = generate_synthetic_data(
        n_samples=samples,
        difficulty=difficulty,
        random_state=datetime.now().timestamp()
    )

    print(f"✓ Generated {samples} samples with {len(X.columns)} features")
    print(f"  Labels: {dict(zip(sorted(y.unique()), (y == label).sum() for label in sorted(y.unique())))}")

    # Save to file
    if output_dir is None:
        output_dir = Path(__file__).parent / "data" / "synthetic"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"hourly_batch_{timestamp}.csv"

    # Save as CSV
    combined = X.copy()
    combined['label'] = y

    combined.to_csv(output_file, index=False)

    print(f"✓ Saved to: {output_file}")

    # Create brief report
    report = {
        "timestamp": datetime.now().isoformat(),
        "task": "autonomous_hourly_data_gen",
        "samples": samples,
        "difficulty": difficulty,
        "status": "success",
        "output_file": str(output_file)
    }

    report_path = Path(__file__).parent / "reports" / f"hourly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✓ Report saved to: {report_path}")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous QZero Data Generator")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples")
    parser.add_argument("--difficulty", type=str, default="medium",
                       choices=["easy", "medium", "hard"], help="Difficulty level")

    args = parser.parse_args()

    success = generate_data_batch(args.samples, args.difficulty)

    print(f"\n{'='*60}")
    print(f" Task completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())