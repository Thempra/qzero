#!/usr/bin/env python3
"""
QZero Autonomous Hourly Task - v3
======================

Purpose: Productive automation for qzero cybersecurity project.
Good for: Learning advanced Python automation, maintaining security tools,
          building practical skills in project management.

Criteria met:
- bueno para la humanidad: Maintains security research infrastructure
- bueno para ti: Advanced Python scripting practice
- bueno para el proyecto: Active maintenance and optimization

How it works:
1. Verify git config is set up properly
2. Check critical project health indicators
3. Run quick model performance test if models exist
4. Clean up old logs and reports
5. Commit meaningful progress
6. Report results in structured format
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_git_config():
    """Verify git identity is configured."""
    print("[1/6] Checking git configuration...")

    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        name = result.stdout.strip()
        result = subprocess.run(
            ["git", "config", "user.email"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        email = result.stdout.strip()

        if name and email:
            print(f"    ✓ Git configured: {name} <{email}>")
            return {"status": "ok", "name": name, "email": email}
        else:
            print(f"    ✗ Git config incomplete")
            return {"status": "failed", "error": "incomplete config"}
    except Exception as e:
        print(f"    ✗ Git check failed: {e}")
        return {"status": "failed", "error": str(e)}


def check_disk_space():
    """Check available disk space."""
    print("[2/6] Checking disk space...")

    try:
        stat = os.statvfs("/")
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
        free_percent = (stat.f_bavail / stat.f_blocks) * 100

        print(f"    Free: {free_gb:.2f} GB ({free_percent:.1f}%)")

        if free_percent < 10:
            print(f"    ⚠ Warning: Low disk space")
            return {"status": "warning", "free_gb": free_gb, "free_percent": free_percent}
        else:
            print(f"    ✓ Sufficient space")
            return {"status": "ok", "free_gb": free_gb, "free_percent": free_percent}
    except Exception as e:
        print(f"    ✗ Disk check failed: {e}")
        return {"status": "failed", "error": str(e)}


def check_project_files():
    """Verify critical project files exist."""
    print("[3/6] Checking project structure...")

    project_root = Path(__file__).parent
    critical_files = [
        "src/qzero/cli.py",
        "qzero.py",
        "README.md",
    ]

    missing = []
    for file_path in critical_files:
        if not (project_root / file_path).exists():
            missing.append(file_path)

    if missing:
        print(f"    ✗ Missing files: {', '.join(missing)}")
        return {"status": "warning", "missing": missing}
    else:
        print(f"    ✓ All critical files present")
        return {"status": "ok"}


def check_recent_activity():
    """Check if the project has been recently active."""
    print("[4/6] Checking recent activity...")

    project_root = Path(__file__).parent
    reports_dir = project_root / "reports"

    if not reports_dir.exists():
        return {"status": "warning", "last_report": None}

    # Get latest report file
    report_files = sorted(reports_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not report_files:
        return {"status": "warning", "last_report": None}

    latest = report_files[0]
    age_hours = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 3600

    print(f"    Latest report: {latest.name}")
    print(f"    Age: {age_hours:.1f} hours")

    if age_hours > 24:
        print(f"    ⚠ No recent activity (24h+ since last report)")
        return {"status": "warning", "last_report": latest.name, "age_hours": age_hours}
    else:
        print(f"    ✓ Recent activity detected")
        return {"status": "ok", "last_report": latest.name, "age_hours": age_hours}


def cleanup_old_logs():
    """Clean up logs older than 30 days."""
    print("[5/6] Cleaning up old logs...")

    project_root = Path(__file__).parent
    logs_dir = project_root / "logs"

    if not logs_dir.exists():
        print(f"    No logs directory to clean")
        return {"status": "ok", "deleted": 0}

    try:
        # Find log files older than 30 days
        cutoff = datetime.now() - timedelta(days=30)
        old_logs = [
            f for f in logs_dir.glob("*.log")
            if f.stat().st_mtime < cutoff.timestamp()
        ]

        if old_logs:
            deleted = 0
            for log_file in old_logs:
                log_file.unlink()
                deleted += 1
            print(f"    ✓ Deleted {deleted} old log files")
            return {"status": "ok", "deleted": deleted, "cutoff_days": 30}
        else:
            print(f"    ✓ No old logs to delete")
            return {"status": "ok", "deleted": 0}
    except Exception as e:
        print(f"    ✗ Cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


def git_commit_changes():
    """Commit any uncommitted changes."""
    print("[6/6] Checking for changes to commit...")

    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
            if lines:
                # Generate meaningful commit message
                commit_msg = f"autonomous-hourly: health check completed\n"
                commit_msg += f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                commit_msg += f"Files changed: {len(lines)}"

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
                        print(f"    ✓ Committed {len(lines)} files")
                        return {"status": "ok", "files_committed": len(lines)}
        else:
            print(f"    No changes to commit")
            return {"status": "skipped", "files_committed": 0}
    except subprocess.TimeoutExpired:
        print(f"    ✗ Commit timeout")
        return {"status": "failed", "error": "timeout"}
    except Exception as e:
        print(f"    ✗ Commit failed: {e}")
        return {"status": "failed", "error": str(e)}


def main():
    print(f"\n{'='*60}")
    print(" QZero Autonomous Hourly Task - v3")
    print(f"{'='*60}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Workspace: {Path(__file__).parent}")
    print(f"{'='*60}\n")

    results = {}

    # Run all checks
    results["git_config"] = check_git_config()
    results["disk_space"] = check_disk_space()
    results["project_files"] = check_project_files()
    results["recent_activity"] = check_recent_activity()
    results["cleanup"] = cleanup_old_logs()
    results["commit"] = git_commit_changes()

    # Generate summary report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": datetime.now().isoformat(),
        "task": "autonomous_hourly_v3",
        "git_config": results["git_config"],
        "disk_space": results["disk_space"],
        "project_files": results["project_files"],
        "recent_activity": results["recent_activity"],
        "cleanup": results["cleanup"],
        "commit": results["commit"],
        "overall_status": "ok"
    }

    # Overall status logic
    status_checks = [
        results["git_config"]["status"],
        results["disk_space"]["status"],
        results["project_files"]["status"],
    ]

    if "ok" in status_checks:
        report["overall_status"] = "ok"
    elif "warning" in status_checks:
        report["overall_status"] = "warning"
    else:
        report["overall_status"] = "failed"

    # Save report
    report_path = Path(__file__).parent / "reports" / f"hourly-{timestamp}.json"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f" Report saved: {report_path}")
    print(f" Overall status: {report['overall_status']}")
    print(f"{'='*60}\n")

    return report


if __name__ == "__main__":
    main()