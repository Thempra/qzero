#!/usr/bin/env python3
"""
Simplified autonomous task for QZero - Hourly Data Generation
============================================================

This script generates synthetic network traffic data for QZero models.
It's designed to run autonomously without complex dependencies.

Good for:
- humanity: Contributes to open-source cybersecurity research
- them: QZero project gets more training data
- me: Learning about ML data generation workflows

Criteria: Code > prosa, makes concrete progress, not repetitive meaninglessly
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime


def generate_data_batch(samples=100, difficulty="medium"):
    """Generate synthetic data using existing QZero CLI."""
    print(f"\n{'='*60}")
    print(f" Autonomous Hourly Task - QZero Data Generation")
    print(f"{'='*60}")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Samples: {samples} | Difficulty: {difficulty}")
    print(f"{'='*60}\n")

    # Use qzero-cli.py to generate data (it handles dependencies)
    script_path = Path(__file__).parent / "qzero-cli.py"
    cmd = [
        "python3", str(script_path),
        "train",
        "--samples", str(samples),
        "--difficulty", difficulty,
        "--epochs", "0",  # Don't train, just generate
        "--output-file", f"hourly_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    ]

    print(f"Running: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        # Show output
        print(result.stdout)

        if result.stderr:
            print("Errors/Warnings:")
            print(result.stderr)

        # Check for success indicators
        if "Generated" in result.stdout and "Saved" in result.stdout:
            print(f"\n✓ Data generation successful")
            print(f"✓ Output saved to project/data/synthetic/")

            # Create brief report
            report = {
                "timestamp": datetime.now().isoformat(),
                "task": "autonomous_hourly_data_gen",
                "samples": samples,
                "difficulty": difficulty,
                "status": "success"
            }

            report_path = Path(__file__).parent / "reports" / f"hourly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path.parent.mkdir(exist_ok=True)

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"✓ Report saved to: {report_path}")
            return True
        else:
            print(f"\n⚠ Generation may have issues (check output above)")
            return False

    except subprocess.TimeoutExpired:
        print(f"\n✗ Timeout (>2 minutes)")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


if __name__ == "__main__":
    import sys

    samples = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    difficulty = sys.argv[2] if len(sys.argv) > 2 else "medium"

    success = generate_data_batch(samples, difficulty)

    sys.exit(0 if success else 1)