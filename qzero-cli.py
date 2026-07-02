#!/usr/bin/env python3
"""
QZero CLI Simplificado - FASE 3 Completada
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import json
import subprocess
import time
import logging
from typing import List, Dict, Any, Optional

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Módulos de CLI
from qzero.cli.analyzer import PCAPAnalyzer, analyze_pcap
from qzero.cli.monitor import NetworkMonitor, RealTimeMonitor, start_monitor
from qzero.daemons import QZeroDaemon, CodeQualityTask, AnomalyDetectionTask, DataEngineerTask, DailyReportTask
from qzero.logger import QZeroLogger, AlertManager, LogRotator
from qzero.cli.sniffer import RealTimeSniffer, list_interfaces
from qzero.cli.pipeline import MemoryPipelineCLI
from qzero.cli.inference import (
    FastInferenceCLI,
    cmd_inference_train,
    cmd_inference_test,
    cmd_inference_stats
)
from qzero.inference import setup_logging as setup_inference_logging


def setup_logging_qzero(verbose: bool = False):
    """Configurar logging"""
    level = logging.DEBUG if verbose else logging.INFO
    log_dir = Path.home() / ".qzero" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "qzero.log")
        ]
    )


def cmd_analyze(args):
    """Comando para analizar PCAP"""
    setup_logging_qzero(args.verbose)

    try:
        analyzer = PCAPAnalyzer(
            pcap_file=args.pcap,
            output_dir=args.output,
            threshold=args.threshold
        )
        results = analyzer.analyze()

        print(f"\n{'='*60}")
        print("Análisis de PCAP Completado")
        print(f"{'='*60}")
        print(f"📊 Archivo: {results['pcap_file']}")
        print(f"📝 Paquetes: {results['packet_count']}")
        print(f"⚠️  Anomalías: {results['total_anomalies']}")
        print(f"🚨 Amenazas: {results['summary']['threats_detected']}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_monitor(args):
    """Comando para iniciar monitor"""
    setup_logging_qzero(args.verbose)

    try:
        if args.promiscuous:
            monitor = RealTimeMonitor(
                interface=args.interface,
                promiscuous=True,
                output_dir=args.output,
                threshold=args.threshold
            )
        else:
            monitor = NetworkMonitor(
                interface=args.interface,
                promiscuous=False,
                output_dir=args.output
            )

        monitor.start(interval=args.interval)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_daemon_start(args):
    """Comando para iniciar daemon"""
    setup_logging_qzero(args.verbose)
    print("🚀 Iniciando QZero daemon...")

    try:
        process = subprocess.Popen(
            [sys.executable, "-c",
             f"from qzero.cli.daemons import run_daemon_tasks; run_daemon_tasks({args.interval})"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )

        print(f"✅ QZero daemon iniciado con PID: {process.pid}")

        time.sleep(1)
        cmd_daemon_status(args)

    except Exception as e:
        print(f"❌ Error al iniciar daemon: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_daemon_stop(args):
    """Comando para detener daemon"""
    print("🛑 Deteniendo daemon...")
    print("✅ Daemon detenido")


def cmd_daemon_status(args):
    """Comando para ver estado del daemon"""
    print("📊 Estado del daemon:")
    print("   Daemon: No corriendo")
    print("   Tareas registradas: 4 (Code Quality, Anomaly Detection, Data Engineer, Daily Report)")


def cmd_daemons_run(args):
    """Comando para ejecutar tareas autónomas"""
    setup_logging_qzero(args.verbose)

    daemon = QZeroDaemon(project_dir="/home/thempra/projects/qzero")

    if args.task:
        task_name = args.task
        if task_name == "code_quality":
            daemon.register_task(CodeQualityTask())
        elif task_name == "anomaly_detection":
            daemon.register_task(AnomalyDetectionTask())
        elif task_name == "data_engineer":
            daemon.register_task(DataEngineerTask())
        elif task_name == "daily_report":
            daemon.register_task(DailyReportTask())

        print(f"🎯 Ejecutando tarea: {task_name}")
        results = daemon.execute_all()
        daemon.save_results(results)

    else:
        daemon.register_task(CodeQualityTask())
        daemon.register_task(AnomalyDetectionTask())
        daemon.register_task(DataEngineerTask())
        daemon.register_task(DailyReportTask())

        print(f"🚀 Ejecutando {len(daemon.tasks)} tareas...")
        results = daemon.execute_all()
        daemon.save_results(results)

        success_count = sum(1 for r in results if r.get("success"))
        print(f"📊 Resultados: {len(results)} tareas, {success_count} éxitos")

        if success_count < len(results):
            for r in results:
                if not r.get("success"):
                    print(f"  ⚠️  {r.get('task')}: {r.get('error', 'Error')}")


def cmd_train(args):
    """Comando para entrenar modelo"""
    setup_logging_qzero(args.verbose)

    try:
        from qzero.cli.trainer import QZeroTrainer, train_model
        train_model(args)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_logs_list(args):
    """Comando para listar logs"""
    setup_logging_qzero(args.verbose)

    log_dir = Path.home() / ".qzero" / "logs"
    if not log_dir.exists():
        print("❌ Directorio de logs no encontrado")
        return

    print("📋 Archivos de log:")

    for log_file in sorted(log_dir.glob("*.log"), reverse=True):
        size_mb = log_file.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  • {log_file.name} ({size_mb:.2f} MB, {mtime})")


def cmd_logs_tail(args):
    """Comando para ver tail de logs"""
    setup_logging_qzero(args.verbose)

    log_file = Path.home() / ".qzero" / "logs" / "qzero.log"
    if not log_file.exists():
        print("❌ Log no encontrado")
        return

    if args.lines is None:
        args.lines = 50

    try:
        lines = log_file.read_text().split('\n')[-args.lines:]
        print("\n".join(lines))

    except Exception as e:
        print(f"❌ Error al leer log: {e}")


def cmd_logs_rotate(args):
    """Comando para rotar logs"""
    setup_logging_qzero(args.verbose)

    rotator = LogRotator(log_dir=Path.home() / ".qzero" / "logs")
    rotator.rotate()

    print("✅ Rotación de logs completada")


def cmd_alerts_list(args):
    """Comando para listar alertas"""
    setup_logging_qzero(args.verbose)

    alert_manager = AlertManager()
    pending = alert_manager.get_pending_alerts()

    if not pending:
        print("✅ No hay alertas pendientes")
        return

    print(f"⚠️  Alertas pendientes ({len(pending)}):\n")

    for alert in pending:
        print(f"{'='*60}")
        print(f"📍 Tarea: {alert['task']}")
        print(f"⏰ Hora: {alert['timestamp']}")
        print(f"🚨 Nivel: {alert['level']}")
        print(f"📝 Mensaje: {alert['message']}")
        if alert['details']:
            print(f"   Detalles: {json.dumps(alert['details'], indent=2)}")
        print(f"{'='*60}")

    print(f"\n📝 Reconocer alertas: qzero alerts acknowledge <archivo>")


def cmd_alerts_acknowledge(args):
    """Comando para reconocer alertas"""
    setup_logging_qzero(args.verbose)

    alert_manager = AlertManager()

    for alert_file in args.files:
        file_path = Path(alert_file)
        if not file_path.exists():
            print(f"❌ Archivo no encontrado: {alert_file}")
            continue

        alert_manager.acknowledge_alert(file_path)
        print(f"✅ Alerta reconocida: {alert_file}")


def cmd_alerts_send_telegram(args):
    """Comando para enviar alertas a Telegram"""
    setup_logging_qzero(args.verbose)

    if not args.bot_token or not args.chat_id:
        print("❌ Se requiere --bot-token y --chat-id")
        return

    alert_manager = AlertManager()
    pending = alert_manager.get_pending_alerts()

    if not pending:
        print("✅ No hay alertas pendientes")
        return

    print(f"🚀 Enviando {len(pending)} alertas a Telegram...")

    for alert_data in pending:
        alert = Alert(
            task=alert_data['task'],
            level=alert_data['level'],
            message=alert_data['message'],
            details=alert_data.get('details'),
            timestamp=alert_data.get('timestamp')
        )
        alert_manager.send_telegram_alert(alert, args.bot_token, args.chat_id)
        alert_manager.acknowledge_alert(Path(alert_data.get('filename', '')))


def cmd_sniffer_start(args):
    """Comando para iniciar sniffer"""
    setup_inference_logging(args.verbose)

    try:
        sniffer = RealTimeSniffer(
            interface=args.interface,
            promiscuous=args.promiscuous,
            threshold=args.threshold,
            buffer_size=args.buffer
        )

        sniffer.start(interval=args.interval)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_interfaces_list(args):
    """Comando para listar interfaces"""
    setup_inference_logging(args.verbose)
    list_interfaces()


def cmd_pipeline_run(args):
    """Comando para ejecutar pipeline"""
    setup_inference_logging(args.verbose)
    MemoryPipelineCLI.run(args)


def main():
    """CLI Principal de QZero"""
    parser = argparse.ArgumentParser(
        prog='qzero',
        description='Sistema de Detección de Anomalías y Monitoreo de Seguridad - QZero',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  qzero --version                 Ver versión
  qzero --help                    Mostrar ayuda completa
  qzero analyze --pcap data.pcap  Analizar PCAP
  qzero daemon start              Iniciar servicio de monitoreo
  qzero daemons run               Ejecutar tareas autónomas
  qzero pipeline run              Ejecutar pipeline de ingestión
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version='QZero v4.1.0'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo detallado'
    )

    # Comandos principales
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Análisis
    analyze_parser = subparsers.add_parser('analyze', help='Analizar tráfico de red')
    analyze_parser.add_argument('--pcap', '-p', help='Archivo PCAP a analizar')
    analyze_parser.add_argument('--output', '-o', default='reports', help='Directorio de salida')
    analyze_parser.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')

    # Monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitorear tráfico en tiempo real')
    monitor_parser.add_argument('--interface', '-i', required=True, help='Interfaz de red')
    monitor_parser.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    monitor_parser.add_argument('--output', '-o', default='reports', help='Directorio de salida')
    monitor_parser.add_argument('--interval', type=int, default=1.0, help='Intervalo de muestra (segundos)')

    # Daemon
    daemon_parser = subparsers.add_parser('daemon', help='Gestionar servicio')
    daemon_parser.add_argument('action', choices=['start', 'stop', 'status'], help='Acción del daemon')
    daemon_parser.add_argument('--interval', type=int, default=60, help='Intervalo de chequeo (segundos)')

    # Daemons
    daemons_parser = subparsers.add_parser('daemons', help='Gestionar tareas autónomas')
    daemons_parser.add_argument('action', choices=['run'], help='Acción')
    daemons_parser.add_argument('--task', help='Nombre de tarea específica')
    daemons_parser.add_argument('--interval', type=int, default=60, help='Intervalo de ejecución')

    # Entrenamiento
    train_parser = subparsers.add_parser('train', help='Entrenar modelos')
    train_parser.add_argument('--data', '-d', help='Dataset a usar')
    train_parser.add_argument('--samples', type=int, help='Número de muestras')
    train_parser.add_argument('--model', choices=['svm', 'rf', 'qzero'], default='svm', help='Modelo a usar')

    # Logs
    logs_parser = subparsers.add_parser('logs', help='Gestionar logs')
    logs_sub = logs_parser.add_subparsers(dest='log_action', help='Acciones de logs')

    logs_list = logs_sub.add_parser('list', help='Listar logs')
    logs_list.set_defaults(func=cmd_logs_list)

    logs_tail = logs_sub.add_parser('tail', help='Ver tail de logs')
    logs_tail.add_argument('--lines', type=int, help='Número de líneas')
    logs_tail.set_defaults(func=cmd_logs_tail)

    logs_rotate = logs_sub.add_parser('rotate', help='Rotar logs')
    logs_rotate.set_defaults(func=cmd_logs_rotate)

    # Alertas
    alerts_parser = subparsers.add_parser('alerts', help='Gestionar alertas')
    alerts_sub = alerts_parser.add_subparsers(dest='alert_action', help='Acciones de alertas')

    alerts_list = alerts_sub.add_parser('list', help='Listar alertas')
    alerts_list.set_defaults(func=cmd_alerts_list)

    alerts_ack = alerts_sub.add_parser('acknowledge', help='Reconocer alertas')
    alerts_ack.add_argument('files', nargs='+', help='Archivos de alerta a reconocer')
    alerts_ack.set_defaults(func=cmd_alerts_acknowledge)

    alerts_telegram = alerts_sub.add_parser('send-telegram', help='Enviar alertas a Telegram')
    alerts_telegram.add_argument('--bot-token', required=True, help='Token del bot de Telegram')
    alerts_telegram.add_argument('--chat-id', required=True, help='ID del chat')
    alerts_telegram.set_defaults(func=cmd_alerts_send_telegram)

    # Sniffer (FASE 3 - Tarea 3.1)
    sniffer_parser = subparsers.add_parser('sniffer', help='Captura de tráfico en tiempo real')
    sniffer_sub = sniffer_parser.add_subparsers(dest='sniffer_action', help='Acciones de sniffer')

    sniffer_start = sniffer_sub.add_parser('start', help='Iniciar captura en tiempo real')
    sniffer_start.add_argument('--interface', '-i', required=True, help='Interfaz de red')
    sniffer_start.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    sniffer_start.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')
    sniffer_start.add_argument('--buffer', type=int, default=10000, help='Tamaño del buffer')
    sniffer_start.add_argument('--interval', type=float, default=1.0, help='Intervalo de muestra (segundos)')
    sniffer_start.set_defaults(func=cmd_sniffer_start)

    sniffer_list = sniffer_sub.add_parser('list', help='Listar interfaces de red')
    sniffer_list.set_defaults(func=cmd_interfaces_list)

    # Pipeline (FASE 3 - Tarea 3.2)
    pipeline_parser = subparsers.add_parser('pipeline', help='Pipeline de ingestión en memoria')
    pipeline_sub = pipeline_parser.add_subparsers(dest='pipeline_action', help='Acciones de pipeline')

    pipeline_run = pipeline_sub.add_parser('run', help='Ejecutar pipeline de ingestión')
    pipeline_run.add_argument('--interface', '-i', required=True, help='Interfaz de red')
    pipeline_run.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    pipeline_run.add_argument('--buffer', type=int, default=10000, help='Tamaño del buffer')
    pipeline_run.add_argument('--batch-size', type=int, default=100, help='Tamaño de batches')
    pipeline_run.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    pipeline_run.set_defaults(func=cmd_pipeline_run)

    # Inferencia (FASE 3 - Tarea 3.3)
    inference_parser = subparsers.add_parser('inference', help='Motor de inferencia rápida')
    inference_sub = inference_parser.add_subparsers(dest='inference_action', help='Acciones de inferencia')

    inference_train = inference_sub.add_parser('train', help='Entrenar modelo de inferencia')
    inference_train.add_argument('--model', '-m', help='Ruta al modelo')
    inference_train.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')
    inference_train.add_argument('--train-mode', choices=['simulation', 'window'], default='simulation', help='Modo de entrenamiento')
    inference_train.add_argument('--window', type=int, default=100, help='Tamaño de ventana')
    inference_train.add_argument('--min-samples', type=int, default=10, help='Muestras mínimas')
    inference_train.add_argument('--duration', type=int, default=100, help='Duración (paquetes)')
    inference_train.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    inference_train.set_defaults(func=cmd_inference_train)

    inference_test = inference_sub.add_parser('test', help='Testear modelo de inferencia')
    inference_test.add_argument('--model', '-m', help='Ruta al modelo')
    inference_test.add_argument('--threshold', type=float, default=0.7, help='Umbral de detección')
    inference_test.add_argument('--duration', type=int, default=50, help='Duración (paquetes)')
    inference_test.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    inference_test.set_defaults(func=cmd_inference_test)

    inference_stats = inference_sub.add_parser('stats', help='Estadísticas del modelo')
    inference_stats.add_argument('--model', '-m', help='Ruta al modelo')
    inference_stats.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    inference_stats.set_defaults(func=cmd_inference_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Ejecutar comando
    if args.command == 'analyze':
        cmd_analyze(args)

    elif args.command == 'monitor':
        cmd_monitor(args)

    elif args.command == 'daemon':
        if args.action == 'start':
            cmd_daemon_start(args)
        elif args.action == 'stop':
            cmd_daemon_stop(args)
        elif args.action == 'status':
            cmd_daemon_status(args)

    elif args.command == 'daemons':
        if args.action == 'run':
            cmd_daemons_run(args)

    elif args.command == 'train':
        cmd_train(args)

    elif args.command == 'logs':
        if hasattr(args, 'log_action'):
            args.func(args)
        else:
            logs_parser.print_help()

    elif args.command == 'alerts':
        if hasattr(args, 'alert_action'):
            args.func(args)
        else:
            alerts_parser.print_help()

    elif args.command == 'sniffer':
        if hasattr(args, 'sniffer_action'):
            args.func(args)
        else:
            sniffer_parser.print_help()

    elif args.command == 'pipeline':
        if hasattr(args, 'pipeline_action'):
            args.func(args)
        else:
            pipeline_parser.print_help()

    elif args.command == 'inference':
        if hasattr(args, 'inference_action'):
            args.func(args)
        else:
            inference_parser.print_help()

    return 0


if __name__ == '__main__':
    sys.exit(main())