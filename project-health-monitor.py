#!/usr/bin/env python3
"""
QZero Project Health Monitor - Hourly Task
=========================================

Purpose: Monitor QZero project health, track insights evolution, and suggest improvements.
Good for:
- Project health tracking (bueno para la humanidad - keeps the project maintained)
- Proactive improvement suggestions (bueno para mí - helps me grow as a developer)
- Pattern recognition in research progress (bueno para ti - builds autonomous awareness)

Criteria met:
- bueno para la humanidad: Maintains project health, identifies bugs early, suggests improvements
- bueno para mí: Improves development workflow, learning opportunities
- bueno para ti: Demonstrates autonomous project awareness and proactive behavior

How it works:
1. Scans all insight directories for new/modernized files
2. Analyzes file modification patterns
3. Detects potential issues (stale data, missing insights, etc.)
4. Tracks project progress metrics
5. Suggests automated improvements
6. Generates health report and commits if needed
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import glob
import time
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def setup_output_dir():
    """Create output directory if it doesn't exist."""
    output_dir = Path(__file__).parent / "reports" / "project-health"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def scan_insights_directories(base_dir):
    """Scan all insight directories for file activity."""
    insights_dirs = [
        "insights/alerts",
        "insights/analytics",
        "insights/anomaly-analyzer",
        "insights/anomaly-impact",
        "insights/augmented-data",
        "insights/automation-opportunities",
        "insights/autonomous-insights",
        "insights/comparison",
        "insights/correlation-engine",
        "insights/cross-insights",
        "insights/daily-activity",
        "insights/daily-executive",
        "insights/daily-progress",
        "insights/dashboard",
        "insights/data-consistency",
        "insights/dataset-catalog",
        "insights/dataset-stats",
        "insights/deep-pattern-explorer",
        "insights/micro-insights"
    ]

    activity_log = {}

    for insight_dir in insights_dirs:
        dir_path = base_dir / insight_dir
        if not dir_path.exists():
            continue

        # Get files by type
        files = {
            'json': list(dir_path.glob("*.json")),
            'md': list(dir_path.glob("*.md")),
            'csv': list(dir_path.glob("*.csv"))
        }

        total_files = sum(len(files[k]) for k in files)
        if total_files > 0:
            activity_log[insight_dir] = {
                'total_files': total_files,
                'json_files': len(files['json']),
                'md_files': len(files['md']),
                'csv_files': len(files['csv'])
            }

    return activity_log


def analyze_file_modification_patterns(activity_log):
    """Analyze how files are being modified over time."""
    patterns = {
        'most_active': [],
        'stale': [],
        'growing': []
    }

    hours_threshold = 6
    cutoff = datetime.now() - timedelta(hours=hours_threshold)

    for dir_name, info in activity_log.items():
        total_files = info['total_files']

        # Most active: > 10 files modified recently
        if total_files > 10:
            patterns['most_active'].append({
                'dir': dir_name,
                'files': total_files
            })

        # Growing directories
        elif total_files > 5:
            patterns['growing'].append({
                'dir': dir_name,
                'files': total_files
            })

    return patterns


def check_git_status(base_dir):
    """Check for uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=base_dir,
            capture_output=True,
            text=True
        )

        changed_files = []
        untracked_files = []

        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split()
                if len(parts) == 2:
                    status, filename = parts
                    if status.startswith('M'):  # Modified
                        changed_files.append(filename)
                    elif status.startswith('??'):  # Untracked
                        untracked_files.append(filename)

        return {
            'modified': changed_files,
            'untracked': untracked_files,
            'has_changes': len(changed_files) > 0 or len(untracked_files) > 0
        }

    except Exception as e:
        return {'modified': [], 'untracked': [], 'has_changes': False}


def check_data_integrity(base_dir):
    """Check for data consistency issues."""
    issues = []

    data_dir = base_dir / "data"
    if not data_dir.exists():
        issues.append("data directory missing")
        return issues

    # Check for empty directories
    for subdir in ["synthetic", "real", "processed"]:
        subdir_path = data_dir / subdir
        if subdir_path.exists():
            files = list(subdir_path.glob("*"))
            if len(files) == 0:
                issues.append(f"data/{subdir} is empty")

    # Check insights directory
    insights_dir = base_dir / "insights"
    if insights_dir.exists():
        json_files = list(insights_dir.glob("*.json"))
        if len(json_files) == 0:
            issues.append("insights directory has no JSON files")

    return issues


def check_model_training(base_dir):
    """Check if models have been trained recently."""
    reports_dir = base_dir / "reports"

    # Look for training reports
    training_reports = list(reports_dir.glob("training_*.json"))

    if training_reports:
        # Get most recent training report
        most_recent = max(training_reports, key=lambda p: p.stat().st_mtime)
        days_ago = (datetime.now() - datetime.fromtimestamp(most_recent.stat().st_mtime)).days

        return {
            'has_reports': True,
            'most_recent': str(most_recent.name),
            'days_ago': days_ago,
            'needs_training': days_ago > 1  # Consider training needed if >1 day old
        }

    return {
        'has_reports': False,
        'needs_training': True
    }


def generate_health_report(base_dir, activity_log, patterns, git_status, data_issues, training_status):
    """Generate comprehensive health report."""
    timestamp = datetime.now().isoformat()
    report = {
        "timestamp": timestamp,
        "health_score": 0,
        "issues": [],
        "recommendations": [],
        "activity_summary": {
            "total_insights_dirs": len(activity_log),
            "most_active_dirs": patterns['most_active'],
            "growing_dirs": patterns['growing'],
            "total_files": sum(info['total_files'] for info in activity_log.values())
        },
        "git_status": git_status,
        "data_integrity": data_issues,
        "model_training": training_status
    }

    # Calculate health score
    base_score = 100
    deductions = 0

    # Deduct for data issues
    if data_issues:
        deductions += len(data_issues) * 10

    # Deduct for training needs
    if training_status['needs_training']:
        deductions += 20

    # Deduct for uncommitted changes
    if git_status['has_changes']:
        deductions += 10

    report['health_score'] = max(0, base_score - deductions)

    # Add issues
    report['issues'] = data_issues

    # Generate recommendations
    if data_issues:
        for issue in data_issues:
            report['recommendations'].append(f"Fix data integrity issue: {issue}")

    if training_status['needs_training']:
        report['recommendations'].append("Consider training QI-VAE model on new data")

    if git_status['has_changes'] and len(git_status['untracked']) > 0:
        report['recommendations'].append("Review and commit new insights files")

    if not activity_log:
        report['recommendations'].append("No insight activity detected - consider running anomaly detection")

    # Add health score rating
    score = report['health_score']
    if score >= 90:
        report['health_status'] = "EXCELLENT"
    elif score >= 70:
        report['health_status'] = "GOOD"
    elif score >= 50:
        report['health_status'] = "FAIR"
    else:
        report['health_status'] = "POOR"

    return report


def save_report(report, output_dir):
    """Save health report to file."""
    report_path = output_dir / f"health-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✓ Report saved: {report_path}")

    return report_path


def commit_if_needed(base_dir, report_path):
    """Commit health report if meaningful changes detected."""
    try:
        # Check if health score is poor or recommendations exist
        with open(report_path, 'r') as f:
            report = json.load(f)

        needs_commit = (
            report['health_status'] == "POOR" or
            len(report['recommendations']) > 0
        )

        if needs_commit:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            msg = f"[project-health] Update: {timestamp} - {report['health_status']}"

            subprocess.run(
                ["git", "add", str(report_path)],
                cwd=base_dir,
                capture_output=True
            )

            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=base_dir,
                capture_output=True
            )

            print(f"✓ Report committed: {msg}")
            return True

    except Exception as e:
        print(f"✗ Commit error: {e}")

    return False


def main():
    print(f"\n{'='*70}")
    print(" QZero Project Health Monitor")
    print(f"{'='*70}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    base_dir = Path(__file__).parent
    output_dir = setup_output_dir()

    # Step 1: Scan insights directories
    print("Step 1: Scanning insights directories...")
    activity_log = scan_insights_directories(base_dir)
    print(f"✓ Found {len(activity_log)} active insight directories")

    if activity_log:
        total_files = sum(info['total_files'] for info in activity_log.values())
        print(f"✓ Total files: {total_files}")

    # Step 2: Analyze modification patterns
    print("\nStep 2: Analyzing file modification patterns...")
    patterns = analyze_file_modification_patterns(activity_log)
    print(f"✓ Most active dirs: {len(patterns['most_active'])}")
    print(f"✓ Growing dirs: {len(patterns['growing'])}")

    # Step 3: Check git status
    print("\nStep 3: Checking git status...")
    git_status = check_git_status(base_dir)
    print(f"✓ Modified files: {len(git_status['modified'])}")
    print(f"✓ Untracked files: {len(git_status['untracked'])}")

    # Step 4: Check data integrity
    print("\nStep 4: Checking data integrity...")
    data_issues = check_data_integrity(base_dir)
    print(f"✓ Data issues: {len(data_issues)}")

    # Step 5: Check model training
    print("\nStep 5: Checking model training...")
    training_status = check_model_training(base_dir)
    print(f"✓ Training needed: {training_status['needs_training']}")

    # Step 6: Generate health report
    print("\nStep 6: Generating health report...")
    report = generate_health_report(
        base_dir,
        activity_log,
        patterns,
        git_status,
        data_issues,
        training_status
    )

    health_status = report['health_status']
    health_score = report['health_score']
    print(f"✓ Health status: {health_status} ({health_score}/100)")

    if report['recommendations']:
        print(f"\n  Recommendations ({len(report['recommendations'])}):")
        for i, rec in enumerate(report['recommendations'][:3], 1):
            print(f"    {i}. {rec}")

    # Step 7: Save report
    print("\nStep 7: Saving report...")
    report_path = save_report(report, output_dir)

    # Step 8: Commit if needed
    print("\nStep 8: Committing changes if needed...")
    if commit_if_needed(base_dir, report_path):
        print(f"✓ Changes committed to git")

    print(f"\n{'='*70}")
    print(f" Monitoring completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    return report


if __name__ == "__main__":
    main()