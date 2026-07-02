#!/usr/bin/env python3
"""
Módulo de Logs y Alertas para QZero

Centraliza logs, formatea salida y envía alertas
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import json
import time
import gzip
import shutil
import os
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Niveles de log"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class Alert:
    """Representa una alerta"""
    task: str
    level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        data = asdict(self)
        data["timestamp"] = data["timestamp"] or datetime.now().isoformat()
        return data

    def save(self, alerts_dir: Path):
        """Guarda la alerta"""
        alerts_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alert_file = alerts_dir / f"alert-{timestamp}-{self.task.replace(' ', '-').lower()}.json"

        with open(alert_file, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        return alert_file


class QZeroLogger:
    """Logger centralizado para QZero"""

    def __init__(self, log_dir: Optional[str] = None, verbose: bool = False):
        """
        Inicializa el logger.

        Args:
            log_dir: Directorio para logs
            verbose: Modo detallado
        """
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".qzero" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.verbose = verbose
        self.logger = logging.getLogger("QZero")

        self._setup_logging()

    def _setup_logging(self):
        """Configura el logging"""
        level = logging.DEBUG if self.verbose else logging.INFO

        # Formato de log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler con rotación
        log_file = self.log_dir / "qzero.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)

        # Stream handler
        stream_handler = logging.StreamHandler()

        # Configurar logger
        self.logger.setLevel(level)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

        # Logs de daemon en archivo separado
        daemon_logger = logging.getLogger("Daemon")
        daemon_logger.setLevel(level)
        daemon_logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        """Debug log"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Info log"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Warning log"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """Error log"""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Critical log"""
        self.logger.critical(message, **kwargs)

    def format_result(self, result: Dict[str, Any], format_type: str = "json") -> str:
        """
        Formatea un resultado para salida.

        Args:
            result: Resultado a formatear
            format_type: Tipo de formato (json, markdown)

        Returns:
            String formateado
        """
        if format_type == "json":
            return json.dumps(result, indent=2)
        elif format_type == "markdown":
            return self._format_markdown(result)
        else:
            return str(result)

    def _format_markdown(self, result: Dict[str, Any]) -> str:
        """Formatea resultado como Markdown"""
        lines = []
        lines.append(f"## {result.get('task', 'QZero')}")

        if 'timestamp' in result:
            lines.append(f"**Timestamp:** {result['timestamp']}")

        if 'summary' in result:
            summary = result['summary']
            lines.append("\n### Summary")
            for key, value in summary.items():
                lines.append(f"- {key}: {value}")

        if 'anomalies' in result and result['anomalies']:
            lines.append("\n### Anomalies Detected")
            for anomaly in result['anomalies']:
                lines.append(f"- **{anomaly.get('type', 'Unknown')}**: {anomaly.get('confidence', 0):.2f}")
                lines.append(f"  - {anomaly.get('description', '')}")

        if 'error' in result:
            lines.append(f"\n❌ **Error:** {result['error']}")

        return "\n".join(lines)


class LogRotator:
    """Rotador de logs para mantener espacio"""

    def __init__(self, log_dir: Path, max_size_mb: int = 10, keep_days: int = 7):
        """
        Inicializa el rotador.

        Args:
            log_dir: Directorio de logs
            max_size_mb: Tamaño máximo por archivo en MB
            keep_days: Días a mantener
        """
        self.log_dir = log_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.keep_days = keep_days

    def rotate(self):
        """Rotar logs si es necesario"""
        now = time.time()

        # Rotar logs antiguos
        for log_file in self.log_dir.glob("*.log"):
            if now - log_file.stat().st_mtime > (self.keep_days * 86400):
                try:
                    log_file.rename(log_file.with_suffix('.log.gz'))
                    with gzip.open(log_file.with_suffix('.log.gz'), 'rb') as f_in:
                        with open(log_file.with_suffix('.log'), 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                except Exception as e:
                    print(f"Error al rotar log: {e}")

        # Rotar por tamaño
        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_size > self.max_size_bytes:
                try:
                    backup_file = log_file.with_suffix('.log.old')
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(backup_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    log_file.unlink()
                    print(f"Log rotado: {backup_file}")
                except Exception as e:
                    print(f"Error al rotar log por tamaño: {e}")


class AlertManager:
    """Gestor de alertas"""

    def __init__(self, alerts_dir: Optional[str] = None, log_file: Optional[str] = None):
        """
        Inicializa el gestor de alertas.

        Args:
            alerts_dir: Directorio para alertas
            log_file: Archivo de log para consultar
        """
        self.alerts_dir = Path(alerts_dir) if alerts_dir else Path.home() / ".qzero" / "alerts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = Path(log_file) if log_file else Path.home() / ".qzero" / "logs" / "qzero.log"
        self.acknowledged_file = self.alerts_dir / "acknowledged.json"

        # Cargar alertas reconocidas
        self.acknowledged = set()
        if self.acknowledged_file.exists():
            try:
                with open(self.acknowledged_file) as f:
                    self.acknowledged = set(json.load(f))
            except Exception:
                pass

    def create_alert(self, task: str, level: str, message: str, details: Optional[Dict] = None) -> Alert:
        """
        Crea una alerta.

        Args:
            task: Nombre de la tarea
            level: Nivel de alerta (INFO, WARNING, ERROR, CRITICAL)
            message: Mensaje de la alerta
            details: Detalles adicionales

        Returns:
            Alerta creada
        """
        alert = Alert(
            task=task,
            level=level,
            message=message,
            details=details
        )
        alert.save(self.alerts_dir)

        # Si es crítica, enviar notificación
        if level == "CRITICAL":
            self._send_notification(alert)

        return alert

    def acknowledge_alert(self, alert_file: Path):
        """Reconoce una alerta"""
        alert_file.unlink(missing_ok=True)
        self.acknowledged.add(alert_file.stem)

    def get_pending_alerts(self) -> list:
        """Obtiene alertas pendientes"""
        pending = []

        for alert_file in self.alerts_dir.glob("alert-*.json"):
            if alert_file.stem not in self.acknowledged:
                with open(alert_file) as f:
                    pending.append(json.load(f))

        return pending

    def _send_notification(self, alert: Alert):
        """Envía notificación"""
        # TODO: Implementar integración con Telegram
        # Por ahora, solo imprime
        print(f"\n{'='*60}")
        print(f"🚨 ALERTA CRÍTICA: {alert.task}")
        print(f"{'='*60}")
        print(f"Nivel: {alert.level}")
        print(f"Mensaje: {alert.message}")
        if alert.details:
            print(f"Detalles: {json.dumps(alert.details, indent=2)}")
        print(f"{'='*60}\n")

    def send_telegram_alert(self, alert: Alert, bot_token: str, chat_id: str):
        """
        Envía alerta a Telegram.

        Args:
            alert: Alerta a enviar
            bot_token: Token del bot de Telegram
            chat_id: ID del chat
        """
        try:
            import requests

            text = f"🚨 *ALERTA CRÍTICA - QZero*\n\n"
            text += f"📍 *Tarea:* {alert.task}\n"
            text += f"⏰ *Hora:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            text += f"⚠️ *Mensaje:* {alert.message}\n"

            if alert.details:
                text += f"\n*Detalles:*\n"
                for key, value in alert.details.items():
                    text += f"- {key}: {value}\n"

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }, timeout=10)

            if response.status_code == 200:
                print(f"✅ Alerta enviada a Telegram")
            else:
                print(f"❌ Error al enviar alerta a Telegram: {response.text}")

        except Exception as e:
            print(f"❌ Error al enviar alerta a Telegram: {e}")


def setup_logging(verbose: bool = False) -> QZeroLogger:
    """
    Configura logging para QZero.

    Args:
        verbose: Modo detallado

    Returns:
        QZeroLogger configurado
    """
    return QZeroLogger(verbose=verbose)


def setup_alert_manager() -> AlertManager:
    """
    Configura gestor de alertas.

    Returns:
        AlertManager configurado
    """
    return AlertManager()


def setup_log_rotator() -> LogRotator:
    """
    Configura rotador de logs.

    Returns:
        LogRotator configurado
    """
    return LogRotator(log_dir=Path.home() / ".qzero" / "logs")