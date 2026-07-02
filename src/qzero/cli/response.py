"""
Módulo de CLI para Motor de Respuesta de QZero
"""

import sys
from pathlib import Path
import argparse
import logging
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qzero.response import (
    Alert,
    AlertLevel,
    AlertType,
    AlertManager,
    ResponseEngine
)


def setup_logging(verbose: bool = False):
    """Configurar logging"""
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_dir = Path.home() / ".qzero" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "response.log")
        ]
    )


def cmd_alerts_list(args):
    """Lista alertas"""
    setup_logging(args.verbose)

    try:
        alert_manager = AlertManager()

        pending = alert_manager.get_pending_alerts()

        if not pending:
            print("✅ No hay alertas pendientes")
            return

        print(f"⚠️  Alertas pendientes ({len(pending)}):\n")

        for alert_data in pending:
            alert = Alert(
                id=alert_data['id'],
                timestamp=datetime.fromisoformat(alert_data['timestamp']),
                level=AlertLevel(alert_data['level']),
                alert_type=AlertType(alert_data['type']),
                source=alert_data['source'],
                destination=alert_data['destination'],
                message=alert_data['message'],
                details=alert_data.get('details'),
                confidence=alert_data.get('confidence', 0.0),
                is_acknowledged=alert_data.get('acknowledged', False)
            )

            status = "✅ RECONOCIDA" if alert.is_acknowledged else "⏳ PENDIENTE"
            print(f"{'='*60}")
            print(f"ID: {alert.id}")
            print(f"📅 {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🚨 {alert.level.value.upper()} - {alert.alert_type.value}")
            print(f"📍 {alert.source} → {alert.destination}")
            print(f"📝 {alert.message}")
            print(f"📊 Conf: {alert.confidence:.2f}")
            print(f"   {status}")
            print(f"{'='*60}\n")

        stats = alert_manager.get_stats()
        print(f"📊 Estadísticas: {stats['total_alerts']} alertas totales")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_alerts_create(args):
    """Crea una alerta manual"""
    setup_logging(args.verbose)

    try:
        alert_manager = AlertManager()

        alert = alert_manager.create_alert(
            alert_type=AlertType(args.type),
            level=AlertLevel(args.level),
            source=args.source,
            destination=args.destination,
            message=args.message,
            details=json.loads(args.details) if args.details else None,
            confidence=args.confidence
        )

        print(f"✅ Alerta creada: {alert.id}")
        print(f"📄 {alert.message}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_alerts_acknowledge(args):
    """Reconoce alertas"""
    setup_logging(args.verbose)

    try:
        alert_manager = AlertManager()

        for alert_id in args.ids:
            alert_manager.acknowledge_alert(alert_id)

        print(f"✅ Alertas reconocidas: {len(args.ids)}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_alerts_stats(args):
    """Muestra estadísticas de alertas"""
    setup_logging(args.verbose)

    try:
        alert_manager = AlertManager()

        print(f"📊 AlertManager Stats")
        print(f"{'='*60}")

        stats = alert_manager.get_stats()
        for key, value in stats.items():
            print(f"{key.capitalize()}: {value}")

        print(f"{'='*60}\n")

        # Reglas
        print(f"📋 Reglas activas ({len(alert_manager.rules)}):\n")
        for rule in alert_manager.rules:
            print(f"   • {rule.alert_type.value} [{rule.level.value}]")
            print(f"     Threshold: {rule.threshold}, Min samples: {rule.min_samples}")
            print(f"     Actions: {', '.join(rule.actions)}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_alerts_send_telegram(args):
    """Envía alertas a Telegram"""
    setup_logging(args.verbose)

    if not args.bot_token or not args.chat_id:
        print("❌ Se requiere --bot-token y --chat-id")
        return

    try:
        alert_manager = AlertManager()

        pending = alert_manager.get_pending_alerts()

        if not pending:
            print("✅ No hay alertas pendientes")
            return

        print(f"🚀 Enviando {len(pending)} alertas a Telegram...\n")

        for alert_data in pending:
            alert = Alert(
                id=alert_data['id'],
                timestamp=datetime.fromisoformat(alert_data['timestamp']),
                level=AlertLevel(alert_data['level']),
                alert_type=AlertType(alert_data['type']),
                source=alert_data['source'],
                destination=alert_data['destination'],
                message=alert_data['message'],
                details=alert_data.get('details'),
                confidence=alert_data.get('confidence', 0.0),
                is_acknowledged=alert_data.get('acknowledged', False)
            )

            alert_manager._send_telegram_alert(alert)
            alert_manager.acknowledge_alert(alert.id)

        print(f"✅ {len(pending)} alertas enviadas a Telegram")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)