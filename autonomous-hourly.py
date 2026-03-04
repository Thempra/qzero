#!/usr/bin/env python3
"""
Autonomous QZero Task - Hourly Script
=====================================

Purpose: Run comprehensive health checks, generate daily reports, and commit progress.
Good for: QZero project maintenance (ensures system health), cybersecurity research (open source contribution),
          skill building (automation and monitoring).

Criteria met:
- bueno para la humanidad: Maintains open-source security tools
- bueno para mí: Learning automation and monitoring workflows
- bueno para ti: Makes concrete progress on project reliability

How it works:
1. Run health checks on all QZero components
2. Generate daily summary report
3. Commit changes with meaningful message
4. Clean up old logs if needed

Run with: python3 autonomous-hourly.py [--verbose]
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

verbose_output = False

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


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


def run_health_check(verbose=False):
    """Run comprehensive health checks on QZero components."""
    print("[1/4] Running health checks...")

    health_checks = {
        "file_structure": check_file_structure(verbose),
        "models": check_models(verbose),
        "logs": check_logs(verbose),
        "disk": check_disk(verbose),
    }

    # Generate health report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = {
        "timestamp": timestamp,
        "checks": health_checks,
        "overall_status": "ok" if all(c.get("status") == "ok" for c in health_checks.values()) else "warning",
        "failed_checks": [name for name, c in health_checks.items() if c.get("status") != "ok"],
    }

    # Save health report
    report_path = Path(__file__).parent / "reports" / f"health-check-{timestamp.replace(' ', '-').replace(':', '-')}.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    if verbose:
        print(f"    Health report: {report_path}")

    return report


def generate_daily_summary(health_report):
    """Generate a daily summary from health report."""
    print("[2/4] Generating daily summary...")

    timestamp = datetime.now().strftime("%Y-%m-%d")
    summary = {
        "date": timestamp,
        "generated_at": datetime.now().isoformat(),
        "health_overall": health_report["overall_status"],
        "failed_checks": health_report["failed_checks"],
        "disk_space": health_report["checks"]["disk"].get("free_percent"),
    }

    summary_path = Path(__file__).parent / "reports" / f"daily-summary-{timestamp}.json"
    summary_path.parent.mkdir(exist_ok=True)

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"    Daily summary: {summary_path}")

    return summary


def git_commit(health_report, daily_summary):
    """Commit any uncommitted changes with meaningful message."""
    print("[3/4] Checking for changes to commit...")

    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            # Generate commit message
            files = result.stdout.strip().split('\n')
            changed_files = [f.strip().split()[-1] for f in files if f.strip()]

            if verbose_output:
                print(f"    Files to commit: {changed_files}")

            # Create commit
            commit_msg = f"autonomous-hourly: health check completed\n\n"
            commit_msg += f"Overall status: {health_report['overall_status']}\n"
            commit_msg += f"Failed checks: {', '.join(health_report['failed_checks'])}\n"
            commit_msg += f"Disk space: {daily_summary['disk_space']}% free\n"
            commit_msg += f"Files changed: {len(changed_files)}"

            result = subprocess.run(
                ["git", "add", "."],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                result = subprocess.run(
                    ["git", "commit", "-m", commit_msg],
                    cwd=Path(__file__).parent,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    print("    ✓ Changes committed")
                    return True

    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        print(f"    ✗ Commit failed: {e}")

    return False


def generate_report(health, daily, commit):
    """Generate final summary report."""
    print("[4/4] Generating final report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "task": "autonomous_hourly_health_check",
        "health_status": health["overall_status"],
        "failed_checks": health["failed_checks"],
        "disk_space": daily["disk_space"],
        "changes_committed": commit,
        "workspace": str(Path(__file__).parent)
    }

    report_path = Path(__file__).parent / "reports" / f"hourly_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"    Final report: {report_path}")
    print(json.dumps(report, indent=2))


# Helper functions
def check_file_structure(verbose=False):
    """Check if required directories and files exist."""
    errors = []
    project_root = Path(__file__).parent

    required_dirs = ["src", "logs", "reports", "insights"]
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            errors.append(f"Missing directory: {dir_name}")

    return {"status": "ok" if not errors else "failed", "errors": errors}


def check_models(verbose=False):
    """Check if model files exist."""
    errors = []
    model_dir = Path(__file__).parent / "src" / "quantum"

    if not model_dir.exists():
        errors.append(f"Model directory doesn't exist: {model_dir}")
        return {"status": "failed", "errors": errors}

    model_files = list(model_dir.glob("**/*.pkl")) + list(model_dir.glob("**/*.pth"))
    if not model_files and verbose:
        print(f"    No trained model files found (.pkl or .pth)")

    return {"status": "ok" if not errors else "failed", "errors": errors, "model_files": len(model_files)}


def check_logs(verbose=False):
    """Check if log files exist and are not empty."""
    errors = []
    logs_dir = Path(__file__).parent / "logs"

    if not logs_dir.exists():
        errors.append(f"Logs directory doesn't exist: {logs_dir}")
    else:
        log_files = list(logs_dir.glob("*.log"))
        if not log_files:
            errors.append("No log files found")
        else:
            if verbose:
                print(f"    Found {len(log_files)} log files")

    return {"status": "ok" if not errors else "failed", "errors": errors, "log_count": len(log_files)}


def check_disk(verbose=False):
    """Check disk space availability."""
    errors = []
    stat = os.statvfs("/")

    free_percent = (stat.f_bavail / stat.f_blocks) * 100

    if free_percent < 10:
        errors.append(f"Low disk space: {free_percent:.1f}% free")
    elif verbose:
        print(f"    Disk space: {free_percent:.1f}% free")

    return {"status": "ok" if not errors else "warning", "errors": errors, "free_percent": round(free_percent, 1)}


def main():
    parser = argparse.ArgumentParser(description="Autonomous QZero Hourly Task")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    global verbose_output
    verbose_output = args.verbose

    print(f"\n{'='*60}")
    print(" autonomous-hourly.py - QZero Autonomous Task")
    print(f"{'='*60}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Workspace: {Path(__file__).parent}")
    print(f"{'='*60}\n")

    # Step 1: Run health check
    health_report = run_health_check(verbose=args.verbose)

    # Step 2: Generate daily summary
    daily_summary = generate_daily_summary(health_report)

    # Step 3: Commit changes
    commit_result = git_commit(health_report, daily_summary)

    # Step 4: Report
    generate_report(health=health_report, daily=daily_summary, commit=commit_result)

    print(f"\n{'='*60}")
    print(f" Task completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()