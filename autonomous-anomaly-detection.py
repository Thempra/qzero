#!/usr/bin/env python3
"""
QZero Autonomous Anomaly Detection - Hourly Task
================================================

Purpose: Detect and report anomalies in QZero project data, send alerts for critical issues.
Good for:
- Security monitoring (bueno para la humanidad)
- Security skills development (bueno para ti)
- Autonomous system awareness (bueno para mí)

Criteria met:
- bueno para la humanidad: Proactive security monitoring, early threat detection
- bueno para ti: Security analysis practice, autonomous operation
- bueno para mí: Project security awareness, early warning system

How it works:
1. Analyzes recent insights and reports for anomalous patterns
2. Checks for suspicious file activity and anomalies
3. Evaluates data integrity and security posture
4. Generates anomaly detection reports
5. Sends Telegram alerts for critical issues
6. Cleans old reports to maintain system health
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import glob
import re
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def setup_output_dir():
    """Create output directory if it doesn't exist."""
    output_dir = Path(__file__).parent / "reports" / "anomaly-detection"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_recent_insights(base_dir, hours=24):
    """Get recently created/modified insight files."""
    insights_patterns = [
        "insights/**/*.json",
        "reports/**/*.json",
        "data/**/*.json"
    ]

    recent_files = []
    cutoff_time = datetime.now() - timedelta(hours=hours)

    for pattern in insights_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                mod_time = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                if mod_time >= cutoff_time:
                    recent_files.append({
                        'path': file_path,
                        'mtime': mod_time,
                        'mtime_str': mod_time.isoformat()
                    })
            except:
                continue

    # Sort by modification time (newest first)
    recent_files.sort(key=lambda x: x['mtime'], reverse=True)

    return recent_files


def analyze_insights_content(base_dir, recent_files):
    """Analyze content of recent insight files for anomalies."""
    anomalies = []
    file_count = len(recent_files)
    total_size = sum(Path(f['path']).stat().st_size for f in recent_files)

    # File count anomaly: too many files created in short time
    if file_count > 100:
        anomalies.append({
            'type': 'high_file_volume',
            'severity': 'LOW',
            'description': f'More than 100 insight files created in last {recent_files[0]["mtime_str"][:10]}',
            'suggestion': 'Review recent insight generation activity'
        })

    # Size anomaly: unusually large files
    large_files = [f for f in recent_files if Path(f['path']).stat().st_size > 10 * 1024 * 1024]  # >10MB
    if large_files:
        anomalies.append({
            'type': 'large_files',
            'severity': 'MEDIUM',
            'description': f'{len(large_files)} insight files larger than 10MB detected',
            'suggestion': 'Consider optimizing large data files'
        })

    # Check for recent git commits related to security
    try:
        result = subprocess.run(
            ["git", "log", "--since", f"{hours} hours ago", "--pretty=format:%h %s", "--name-only"],
            cwd=base_dir,
            capture_output=True,
            text=True
        )

        commit_count = len([line for line in result.stdout.split('\n') if line.strip()])
        if commit_count > 50:
            anomalies.append({
                'type': 'high_commit_activity',
                'severity': 'LOW',
                'description': f'High commit activity in last {hours} hours',
                'suggestion': 'Review recent changes'
            })
    except:
        pass

    return anomalies


def check_security_reports(base_dir):
    """Check security and anomaly reports for critical issues."""
    critical_issues = []

    # Look for critical alerts
    alert_patterns = [
        "reports/**/*.json",
        "insights/**/*.json"
    ]

    critical_keywords = ['CRITICAL', 'critical', 'ALERT', 'alert', 'THREAT', 'threat', 'VULNERABILITY', 'vulnerability']

    for pattern in alert_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for keyword in critical_keywords:
                    if keyword in content.upper():
                        critical_issues.append({
                            'file': file_path,
                            'keyword': keyword
                        })
                        break
            except:
                continue

    return critical_issues


def analyze_network_activity(base_dir):
    """Analyze network-related activity."""
    anomalies = []

    # Check for network configuration changes
    config_patterns = [
        "configs/**/*",
        "**/config*.json",
        "**/config*.yaml"
    ]

    for pattern in config_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                days_ago = (datetime.now() - mtime).days

                if days_ago < 7:  # Recently modified config
                    anomalies.append({
                        'type': 'config_change',
                        'severity': 'MEDIUM',
                        'description': f'Network configuration changed {days_ago} days ago',
                        'file': file_path
                    })
            except:
                continue

    return anomalies


def check_model_performance(base_dir):
    """Check model training and performance reports."""
    reports_dir = base_dir / "reports"
    performance_issues = []

    # Look for training reports
    training_reports = list(reports_dir.glob("training_*.json"))
    performance_reports = list(reports_dir.glob("performance_*.json"))

    # Check for models with poor performance
    all_reports = list(training_reports) + list(performance_reports)

    for report_path in all_reports:
        try:
            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)

            # Check for poor performance metrics
            if 'accuracy' in data and data['accuracy'] < 0.7:
                performance_issues.append({
                    'file': report_path.name,
                    'metric': 'accuracy',
                    'value': data['accuracy'],
                    'threshold': 0.7
                })

            if 'loss' in data and data['loss'] > 1.0:
                performance_issues.append({
                    'file': report_path.name,
                    'metric': 'loss',
                    'value': data['loss'],
                    'threshold': 1.0
                })
        except:
            continue

    return performance_issues


def check_data_integrity(base_dir):
    """Check data files for integrity issues."""
    integrity_issues = []

    data_dir = base_dir / "data"
    if not data_dir.exists():
        integrity_issues.append("data directory missing")

    # Check for corrupted files
    for file_path in data_dir.rglob("*"):
        if file_path.suffix.lower() in ['.json', '.csv']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    json.load(f)  # Try to parse as JSON
            except json.JSONDecodeError:
                integrity_issues.append(f"Corrupted JSON file: {file_path}")
            except:
                pass  # CSV files will fail, that's expected

    return integrity_issues


def check_telegram_alerts(base_dir):
    """Check if Telegram integration is configured."""
    telegram_config = base_dir / "configs" / "telegram.json"
    telegram_issues = []

    if not telegram_config.exists():
        telegram_issues.append("Telegram config file not found")
        return telegram_issues

    try:
        with open(telegram_config, 'r') as f:
            config = json.load(f)

        if not config.get('enabled', False):
            telegram_issues.append("Telegram alerts are disabled in config")
    except:
        telegram_issues.append("Telegram config file is invalid")

    return telegram_issues


def generate_anomaly_report(base_dir, recent_files, insight_anomalies, security_issues, network_anomalies,
                             model_issues, integrity_issues, telegram_issues):
    """Generate comprehensive anomaly detection report."""
    timestamp = datetime.now().isoformat()

    # Calculate total size
    total_size = sum(Path(f['path']).stat().st_size for f in recent_files)

    # Get telegram config path
    telegram_config = base_dir / "configs" / "telegram.json"

    # Count anomalies by severity
    severity_counts = {
        'CRITICAL': 0,
        'HIGH': 0,
        'MEDIUM': 0,
        'LOW': 0
    }

    all_anomalies = (
        insight_anomalies +
        security_issues +
        network_anomalies +
        model_issues +
        integrity_issues
    )

    for anomaly in all_anomalies:
        severity = anomaly.get('severity', 'LOW')
        if severity in severity_counts:
            severity_counts[severity] += 1

    # Determine overall risk level
    if severity_counts['CRITICAL'] > 0:
        overall_risk = 'CRITICAL'
    elif severity_counts['HIGH'] > 0:
        overall_risk = 'HIGH'
    elif severity_counts['MEDIUM'] > 0:
        overall_risk = 'MEDIUM'
    elif severity_counts['LOW'] > 0:
        overall_risk = 'LOW'
    else:
        overall_risk = 'NONE'

    report = {
        "timestamp": timestamp,
        "task": "autonomous_anomaly_detection",
        "summary": {
            "overall_risk": overall_risk,
            "total_anomalies": len(all_anomalies),
            "anomalies_by_severity": severity_counts
        },
            "recent_activity": {
                "files_analyzed": len(recent_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            },
        "anomalies": {
            "insight_activity": insight_anomalies,
            "security_reports": security_issues,
            "network_activity": network_anomalies,
            "model_performance": model_issues,
            "data_integrity": integrity_issues,
            "telegram_config": telegram_issues
        },
        "recommendations": []
    }

    # Generate recommendations
    if severity_counts['CRITICAL'] > 0:
        report['recommendations'].append("URGENT: Review critical security anomalies immediately")

    if severity_counts['HIGH'] > 0:
        report['recommendations'].append("Review high-severity issues")

    if integrity_issues:
        report['recommendations'].append(f"Fix {len(integrity_issues)} data integrity issues")

    if model_issues:
        report['recommendations'].append(f"Review {len(model_issues)} model performance issues")

    if not telegram_config.exists() or not config.get('enabled', False):
        report['recommendations'].append("Configure Telegram alerts for security notifications")

    # Add critical issues list
    if security_issues:
        report['recommendations'].append("Investigate security alerts in recent reports")

    return report


def save_report(report, output_dir):
    """Save anomaly report to file."""
    report_path = output_dir / f"anomaly-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✓ Report saved: {report_path}")

    return report_path


def send_telegram_alerts(base_dir, report):
    """Send Telegram alerts for critical issues."""
    telegram_config = base_dir / "configs" / "telegram.json"

    if not telegram_config.exists():
        print("✗ Telegram config not found, skipping alerts")
        return False

    try:
        with open(telegram_config, 'r') as f:
            config = json.load(f)

        if not config.get('enabled', False):
            print("✗ Telegram alerts are disabled in config")
            return False

        token = config.get('token')
        chat_id = config.get('chat_id')

        if not token or not chat_id:
            print("✗ Telegram token or chat_id missing")
            return False

        # Only send for CRITICAL or HIGH risk
        if report['summary']['overall_risk'] not in ['CRITICAL', 'HIGH']:
            print("✓ No critical/high alerts to send")
            return True

        # Prepare message
        risk = report['summary']['overall_risk']
        message = f"🚨 *QZero Anomaly Alert*\n\n"

        message += f"**Risk Level:** {risk}\n"
        message += f"**Total Anomalies:** {report['summary']['total_anomalies']}\n\n"

        if report['summary']['anomalies_by_severity'].get('CRITICAL', 0) > 0:
            message += "❌ CRITICAL issues detected\n"

        if report['summary']['anomalies_by_severity'].get('HIGH', 0) > 0:
            message += "⚠️ HIGH severity issues\n"

        message += f"\n*Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Send via message tool
        try:
            from openclaw import message
            message.send(
                channel="telegram",
                message=message,
                parse_mode="Markdown"
            )
            print("✓ Telegram alert sent")
            return True
        except Exception as e:
            print(f"✗ Failed to send Telegram alert: {e}")
            return False

    except Exception as e:
        print(f"✗ Telegram config error: {e}")
        return False


def cleanup_old_reports(base_dir, days=30):
    """Clean up old anomaly detection reports."""
    output_dir = base_dir / "reports" / "anomaly-detection"

    if not output_dir.exists():
        return 0

    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(days=days)

    for report_file in output_dir.glob("anomaly-report-*.json"):
        try:
            file_time = datetime.fromtimestamp(report_file.stat().st_mtime)
            if file_time < cutoff_time:
                report_file.unlink()
                deleted_count += 1
                print(f"✓ Deleted old report: {report_file.name}")
        except:
            continue

    return deleted_count


def main():
    print(f"\n{'='*70}")
    print(" QZero Autonomous Anomaly Detection")
    print(f"{'='*70}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    base_dir = Path(__file__).parent
    output_dir = setup_output_dir()

    # Step 1: Get recent files
    print("Step 1: Analyzing recent insights and reports...")
    recent_files = get_recent_insights(base_dir, hours=24)
    print(f"✓ Found {len(recent_files)} recent files")

    # Step 2: Analyze insights content
    print("\nStep 2: Analyzing insight content for anomalies...")
    insight_anomalies = analyze_insights_content(base_dir, recent_files)
    print(f"✓ Found {len(insight_anomalies)} insight anomalies")

    # Step 3: Check security reports
    print("\nStep 3: Checking security reports...")
    security_issues = check_security_reports(base_dir)
    print(f"✓ Found {len(security_issues)} security alerts")

    # Step 4: Analyze network activity
    print("\nStep 4: Analyzing network activity...")
    network_anomalies = analyze_network_activity(base_dir)
    print(f"✓ Found {len(network_anomalies)} network anomalies")

    # Step 5: Check model performance
    print("\nStep 5: Checking model performance...")
    model_issues = check_model_performance(base_dir)
    print(f"✓ Found {len(model_issues)} performance issues")

    # Step 6: Check data integrity
    print("\nStep 6: Checking data integrity...")
    integrity_issues = check_data_integrity(base_dir)
    print(f"✓ Found {len(integrity_issues)} integrity issues")

    # Step 7: Check Telegram config
    print("\nStep 7: Checking Telegram configuration...")
    telegram_issues = check_telegram_alerts(base_dir)
    print(f"✓ Telegram config: {'OK' if not telegram_issues else 'Issues found'}")

    # Step 8: Generate report
    print("\nStep 8: Generating anomaly report...")
    report = generate_anomaly_report(
        base_dir,
        recent_files,
        insight_anomalies,
        security_issues,
        network_anomalies,
        model_issues,
        integrity_issues,
        telegram_issues
    )

    overall_risk = report['summary']['overall_risk']
    total_anomalies = report['summary']['total_anomalies']

    print(f"✓ Overall risk: {overall_risk}")
    print(f"✓ Total anomalies: {total_anomalies}")

    if report['recommendations']:
        print(f"\n  Recommendations ({len(report['recommendations'])}):")
        for i, rec in enumerate(report['recommendations'][:3], 1):
            print(f"    {i}. {rec}")

    # Step 9: Save report
    print("\nStep 9: Saving report...")
    report_path = save_report(report, output_dir)

    # Step 10: Send Telegram alerts if critical
    print("\nStep 10: Sending Telegram alerts...")
    send_telegram_alerts(base_dir, report)

    # Step 11: Cleanup old reports
    print("\nStep 11: Cleaning up old reports...")
    deleted = cleanup_old_reports(base_dir, days=30)
    print(f"✓ Deleted {deleted} old reports")

    print(f"\n{'='*70}")
    print(f" Detection completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    return report


if __name__ == "__main__":
    main()