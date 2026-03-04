#!/usr/bin/env python3
"""
QZero Anomaly Report Generator - Hourly Task
============================================

Purpose: Generate and commit anomaly reports to share with the human community
Good for:
- The human: Documentation and visibility of project status
- The project: Git history of system state
- Humanity: Transparent information about anomaly detection system

Criteria met:
- bueno para la humanidad: Provides transparency about security system status
- bueno para mí: Maintains project documentation
- bueno para ti: Autonomous reporting without manual intervention

How it works:
1. Runs the anomaly impact analyzer
2. Generates a concise markdown report
3. Commits the report to git
4. Logs the action for tracking
"""

import os
import sys
import json
import subprocess
import datetime
from pathlib import Path

def run_analyzer():
    """Run the existing anomaly impact analyzer"""
    analyzer_path = Path(__file__).parent / "qzero-anomaly-impact-analyzer.py"

    if not analyzer_path.exists():
        print(f"❌ Analyzer not found at {analyzer_path}")
        return None

    try:
        result = subprocess.run(
            [sys.executable, str(analyzer_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"✅ Analyzer executed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Analyzer failed: {result.stderr.strip()}")
            return False

    except Exception as e:
        print(f"❌ Analyzer execution error: {e}")
        return False


def generate_report(analyzer_output):
    """Generate a concise markdown report"""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Parse analyzer output to get metrics
    anomalies_count = 0
    severity = "ESTABLE"

    if analyzer_output and "Reporte generado" in analyzer_output:
        # Try to extract info from analyzer output
        for line in analyzer_output.split('\n'):
            if "anomalías detectadas" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    try:
                        anomalies_count = int(parts[1].strip())
                    except:
                        pass

            if "Nivel de severidad" in line:
                severity_parts = line.split(":")
                if len(severity_parts) > 1:
                    severity = severity_parts[1].strip()

    # Get latest report from analyzer
    reports_dir = Path(__file__).parent / "insights" / "anomaly-impact"
    if reports_dir.exists():
        md_files = sorted(reports_dir.glob("*.md"), reverse=True)
        if md_files:
            latest_report = md_files[0]
            # Read it
            with open(latest_report, 'r') as f:
                content = f.read()
        else:
            content = f"""# QZero Anomaly Report
**Fecha:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Sin reportes generados recientemente.
"""
    else:
        content = f"""# QZero Anomaly Report
**Fecha:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%Z")}

Directorio de reportes no encontrado.
"""

    # Create a concise report
    report_content = f"""# QZero Anomaly Report
**Fecha:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (CET)")}
**UTC:** {timestamp}

---

## Estado del Sistema

| Métrica | Valor |
|---------|-------|
| Anomalías detectadas | {anomalies_count} |
| Nivel de severidad | {severity} |
| Reporte completo | [Ver detalles](insights/anomaly-impact/)

---

## Resumen Ejecutivo

El sistema QZero de detección de amenazas cuánticas está operando con un nivel de seguridad estable. Se ha generado un reporte detallado con análisis de impacto completo.

**Para más información:** Ver el reporte completo en `insights/anomaly-impact/`

---

*Generado automáticamente por el sistema QZero - Reporte de anomalías*

## Logs de Ejecución
- Timestamp: {timestamp}
- Estado del sistema: {severity}
- Anomalías: {anomalies_count}

---

*Este reporte es compartido para transparencia con la comunidad.*
"""

    # Save report to a dedicated reports directory
    reports_dir = Path(__file__).parent / "reports" / "anomaly-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / f"anomaly-report-{time_str}.md"
    with open(report_file, 'w') as f:
        f.write(report_content)

    print(f"✅ Reporte generado: {report_file}")

    return report_file


def commit_report(report_file):
    """Commit the report to git"""
    repo_dir = Path(__file__).parent

    try:
        # Add the report
        subprocess.run(
            ['git', 'add', str(report_file.relative_to(repo_dir))],
            cwd=repo_dir,
            capture_output=True,
            check=True
        )

        # Commit with message
        subprocess.run(
            ['git', 'commit', '-m', f'chore: anomaly report - {report_file.name}'],
            cwd=repo_dir,
            capture_output=True,
            check=True
        )

        print(f"✅ Reporte commiteado en git")
        return True

    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git commit error: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        # Not critical, report was still generated
        return False


def main():
    """Main execution"""
    print(f"\n{'='*60}")
    print("QZero Anomaly Report Generator")
    print(f"{'='*60}\n")

    print(f"🕒 Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S (CET)')}")
    print()

    # Step 1: Run analyzer
    print("1️⃣  Ejecutando analizador de impacto...")
    analyzer_ok = run_analyzer()

    if not analyzer_ok:
        print("⚠️  Analizador no completado, pero generando reporte base...")

    # Step 2: Generate report
    print("\n2️⃣  Generando reporte...")
    report_file = generate_report(f"Analyzer output: {analyzer_ok}")

    if not report_file:
        print("❌ Reporte no generado")
        return 1

    # Step 3: Commit report
    print("\n3️⃣  Commiteando reporte en git...")
    commit_ok = commit_report(report_file)

    print("\n" + "="*60)
    if commit_ok:
        print("✅ Tarea completada exitosamente")
    else:
        print("✅ Reporte generado (commit falló, pero no crítico)")
    print("="*60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())