#!/usr/bin/env python3
"""
QZero Health Check - Tarea cron automática
Verifica el estado del proyecto QZero y detecta problemas potenciales
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Paths del proyecto
PROJECT_ROOT = Path("/home/thempra/projects/qzero")
LOGS_DIR = PROJECT_ROOT / "logs"
INSIGHTS_DIR = PROJECT_ROOT / "insights"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Configuración
CHECKS = {
    "models": {
        "description": "Verificar modelos cuánticos",
        "path": PROJECT_ROOT / "src" / "quantum",
        "required_files": ["qsvm.py", "qivae.py"]
    },
    "api": {
        "description": "Verificar API de QZero",
        "path": PROJECT_ROOT / "src" / "api.py",
        "required_files": ["api.py"]
    },
    "logs": {
        "description": "Verificar logs del sistema",
        "path": LOGS_DIR,
        "required_files": []
    },
    "insights": {
        "description": "Verificar incidentes recientes",
        "path": INSIGHTS_DIR,
        "required_files": ["real-time-incident-log.jsonl"]
    },
    "disk": {
        "description": "Verificar espacio en disco",
        "path": "/",
        "required_files": []
    }
}

def check_models():
    """Verificar que los modelos cuánticos existen y son válidos"""
    errors = []
    model_dir = CHECKS["models"]["path"]

    if not model_dir.exists():
        errors.append(f"Model directory doesn't exist: {model_dir}")
        return {"status": "failed", "errors": errors}

    missing = [f for f in CHECKS["models"]["required_files"] if not (model_dir / f).exists()]
    if missing:
        errors.append(f"Missing model files: {', '.join(missing)}")

    # Verificar si hay archivos .pkl o .pth entrenados
    model_files = list(model_dir.glob("**/*.pkl")) + list(model_dir.glob("**/*.pth"))
    if not model_files:
        errors.append("No trained model files found (.pkl or .pth)")

    return {
        "status": "failed" if errors else "ok",
        "errors": errors,
        "model_files_found": len(model_files)
    }

def check_api():
    """Verificar API de QZero"""
    errors = []
    api_path = CHECKS["api"]["path"]

    if not api_path.exists():
        errors.append(f"API file doesn't exist: {api_path}")
        return {"status": "failed", "errors": errors}

    # Verificar si hay código válido (mínimo)
    try:
        with open(api_path, 'r') as f:
            content = f.read()
            if len(content) < 100:
                errors.append("API file seems empty or too small")
    except Exception as e:
        errors.append(f"Error reading API file: {e}")

    return {
        "status": "failed" if errors else "ok",
        "errors": errors
    }

def check_logs():
    """Verificar logs del sistema"""
    errors = []
    logs_dir = CHECKS["logs"]["path"]

    if not logs_dir.exists():
        errors.append(f"Logs directory doesn't exist: {logs_dir}")
    else:
        # Verificar logs recientes
        log_files = list(logs_dir.glob("*.log"))
        if not log_files:
            errors.append("No log files found")
        else:
            # Revisar el más reciente
            latest = max(log_files, key=lambda p: p.stat().st_mtime)
            file_size = latest.stat().st_size
            if file_size == 0:
                errors.append(f"Latest log file is empty: {latest.name}")
            else:
                # Verificar que no haya errores graves
                try:
                    with open(latest, 'r') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines[-10:], 1):
                            if "CRITICAL" in line or "ERROR" in line:
                                errors.append(f"Critical/ERROR found in logs: {line.strip()}")
                                if len(errors) >= 3:  # Limitar
                                    break
                except Exception as e:
                    errors.append(f"Error reading latest log: {e}")

    return {
        "status": "failed" if errors else "ok",
        "errors": errors,
        "log_files_count": len(log_files),
        "latest_log": max(log_files, key=lambda p: p.stat().st_mtime).name if log_files else None
    }

def check_insights():
    """Verificar incidentes recientes"""
    errors = []
    insights_dir = CHECKS["insights"]["path"]
    incident_log = insights_dir / "real-time-incident-log.jsonl"

    if not insights_dir.exists():
        errors.append(f"Insights directory doesn't exist: {insights_dir}")
        return {"status": "failed", "errors": errors}

    if not incident_log.exists():
        errors.append("No incident log file found")
        return {"status": "failed", "errors": errors}

    try:
        with open(incident_log, 'r') as f:
            lines = f.readlines()
            critical_count = sum(1 for line in lines if '"severity": "CRITICAL"' in line)

            if critical_count > 0:
                errors.append(f"Found {critical_count} CRITICAL incidents")

            if len(lines) > 100:
                errors.append(f"Large incident log: {len(lines)} entries")

    except Exception as e:
        errors.append(f"Error reading incident log: {e}")

    return {
        "status": "failed" if errors else "ok",
        "errors": errors,
        "incident_count": len(lines) if 'lines' in locals() else 0,
        "critical_count": critical_count if 'critical_count' in locals() else 0
    }

def check_disk():
    """Verificar espacio en disco"""
    errors = []
    stat = os.statvfs("/")

    # Usar porcentaje de espacio libre
    free_percent = (stat.f_bavail / stat.f_blocks) * 100

    if free_percent < 10:
        errors.append(f"Low disk space: {free_percent:.1f}% free")

    return {
        "status": "failed" if errors else "ok",
        "errors": errors,
        "free_percent": round(free_percent, 1),
        "free_gb": round(stat.f_bavail * stat.f_frsize / (1024**3), 2)
    }

def run_health_check():
    """Ejecutar todos los checks"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = {
        "timestamp": timestamp,
        "checks": {}
    }

    for check_name, check_config in CHECKS.items():
        print(f"[*] Running {check_name} check...")
        if check_name == "models":
            results["checks"][check_name] = check_models()
        elif check_name == "api":
            results["checks"][check_name] = check_api()
        elif check_name == "logs":
            results["checks"][check_name] = check_logs()
        elif check_name == "insights":
            results["checks"][check_name] = check_insights()
        elif check_name == "disk":
            results["checks"][check_name] = check_disk()
        print(f"    Status: {results['checks'][check_name]['status']}")

    # Generar resumen
    overall_status = all(
        c.get("status") == "ok"
        for c in results["checks"].values()
    )

    results["overall_status"] = "ok" if overall_status else "failed"
    results["check_count"] = len(results["checks"])
    results["failed_checks"] = [
        name for name, c in results["checks"].items()
        if c.get("status") == "failed"
    ]

    # Guardar resultado
    report_file = REPORTS_DIR / f"health-check-{timestamp.replace(' ', '-').replace(':', '-')}.json"
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Health check completed")
    print(f"  Report saved to: {report_file}")
    print(f"  Overall status: {results['overall_status']}")

    if results["failed_checks"]:
        print(f"  Failed checks: {', '.join(results['failed_checks'])}")

    return results

if __name__ == "__main__":
    run_health_check()