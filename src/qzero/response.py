#!/usr/bin/env python3
"""
Motor de Respuesta (Alertas) para QZero

Dispara eventos cuando se detectan anomalías críticas
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import json
import threading
from dataclasses import dataclass
from enum import Enum
import time
import hashlib

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveles de alerta"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SEVERE = "severe"


class AlertType(Enum):
    """Tipos de alerta"""
    ANOMALY_DETECTED = "anomaly_detected"
    PORT_SCAN = "port_scan"
    MALWARE_TRAFFIC = "malware_traffic"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    HIGH_RATE = "high_rate_anomaly"
    NETWORK_SPAWN = "network_spawn"
    RESOURCE_SPIKE = "resource_spike"


@dataclass
class Alert:
    """Representa una alerta"""
    id: str
    timestamp: datetime
    level: AlertLevel
    alert_type: AlertType
    source: str
    destination: str
    message: str
    details: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    is_acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "type": self.alert_type.value,
            "source": self.source,
            "destination": self.destination,
            "message": self.message,
            "details": self.details,
            "confidence": self.confidence,
            "acknowledged": self.is_acknowledged
        }


class AlertRule:
    """Regla de alerta"""

    def __init__(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        threshold: float = 0.7,
        min_samples: int = 10,
        actions: Optional[List[str]] = None
    ):
        """
        Inicializa una regla de alerta.

        Args:
            alert_type: Tipo de alerta
            level: Nivel de severidad
            threshold: Umbral de confianza mínima
            min_samples: Muestras mínimas para activar
            actions: Acciones a ejecutar (log, telegram, webhook)
        """
        self.alert_type = alert_type
        self.level = level
        self.threshold = threshold
        self.min_samples = min_samples
        self.actions = actions or []

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Regla creada: {alert_type.value} - {level.value}")

    def should_trigger(self, confidence: float, sample_count: int) -> bool:
        """
        Determina si la regla debe disparar.

        Args:
            confidence: Nivel de confianza
            sample_count: Conteo de muestras

        Returns:
            True si debe disparar
        """
        return (
            confidence >= self.threshold and
            sample_count >= self.min_samples
        )


class AlertManager:
    """Gestor de alertas"""

    def __init__(
        self,
        alert_dir: str = "/home/thempra/projects/qzero/alerts",
        max_age_hours: int = 24,
        storage_backend: str = "json"
    ):
        """
        Inicializa el gestor de alertas.

        Args:
            alert_dir: Directorio para guardar alertas
            max_age_hours: Máxima edad de alertas en horas
            storage_backend: Backend de almacenamiento (json, db)
        """
        self.alert_dir = Path(alert_dir)
        self.alert_dir.mkdir(parents=True, exist_ok=True)

        self.max_age_hours = max_age_hours
        self.storage_backend = storage_backend

        self.active_alerts: List[Alert] = []
        self.rules: List[AlertRule] = []

        self.alert_callbacks: List[Callable] = []

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"AlertManager inicializado en {alert_dir}")

        # Cargar reglas predefinidas
        self._load_default_rules()

    def _load_default_rules(self):
        """Carga reglas por defecto"""
        default_rules = [
            AlertRule(
                AlertType.PORT_SCAN,
                AlertLevel.WARNING,
                threshold=0.8,
                actions=["log", "telegram"]
            ),
            AlertRule(
                AlertType.MALWARE_TRAFFIC,
                AlertLevel.CRITICAL,
                threshold=0.9,
                actions=["log", "telegram", "webhook"]
            ),
            AlertRule(
                AlertType.ANOMALY_DETECTED,
                AlertLevel.CRITICAL,
                threshold=0.85,
                actions=["log", "telegram"]
            ),
            AlertRule(
                AlertType.SUSPICIOUS_PATTERN,
                AlertLevel.WARNING,
                threshold=0.75,
                actions=["log"]
            )
        ]

        for rule in default_rules:
            self.rules.append(rule)

        self.logger.info(f"Cargadas {len(default_rules)} reglas por defecto")

    def create_alert(
        self,
        alert_type: AlertType,
        source: str,
        destination: str,
        message: str,
        level: AlertLevel = AlertLevel.WARNING,
        details: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0
    ) -> Alert:
        """
        Crea una nueva alerta.

        Args:
            alert_type: Tipo de alerta
            source: Fuente
            destination: Destino
            message: Mensaje de la alerta
            level: Nivel de severidad
            details: Detalles adicionales
            confidence: Nivel de confianza

        Returns:
            Alert creada
        """
        alert_id = hashlib.md5(
            f"{datetime.now().isoformat()}-{source}-{destination}".encode()
        ).hexdigest()[:8]

        alert = Alert(
            id=alert_id,
            timestamp=datetime.now(),
            level=level,
            alert_type=alert_type,
            source=source,
            destination=destination,
            message=message,
            details=details,
            confidence=confidence
        )

        self.active_alerts.append(alert)
        self.logger.warning(
            f"⚠️  Alerta creada: [{level.value}] {message} "
            f"({source} → {destination}, {confidence:.2f})"
        )

        # Disparar callbacks
        for callback in self.alert_callbacks:
            callback(alert)

        # Guardar alerta
        self.save_alert(alert)

        return alert

    def check_anomaly(
        self,
        anomaly_type: str,
        source: str,
        destination: str,
        confidence: float,
        sample_count: int
    ) -> Optional[Alert]:
        """
        Verifica si una anomalía debe disparar una alerta.

        Args:
            anomaly_type: Tipo de anomalía
            source: Fuente
            destination: Destino
            confidence: Nivel de confianza
            sample_count: Conteo de muestras

        Returns:
            Alert creada o None
        """
        # Convertir tipo a AlertType
        try:
            alert_type = AlertType(anomaly_type.upper())
        except ValueError:
            alert_type = AlertType.ANOMALY_DETECTED

        # Verificar reglas
        for rule in self.rules:
            if rule.alert_type == alert_type and rule.should_trigger(confidence, sample_count):
                message = f"{anomaly_type} detectado: {source} → {destination}"

                alert = self.create_alert(
                    alert_type=alert_type,
                    source=source,
                    destination=destination,
                    message=message,
                    level=rule.level,
                    confidence=confidence,
                    details={
                        "confidence": confidence,
                        "samples": sample_count,
                        "actions": rule.actions
                    }
                )

                # Ejecutar acciones
                self._execute_actions(rule.actions, alert)

                return alert

        return None

    def _execute_actions(self, actions: List[str], alert: Alert):
        """
        Ejecuta las acciones configuradas para una alerta.

        Args:
            actions: Lista de acciones
            alert: Alerta a procesar
        """
        for action in actions:
            try:
                if action == "log":
                    self._log_alert(alert)

                elif action == "telegram":
                    self._send_telegram_alert(alert)

                elif action == "webhook":
                    self._send_webhook_alert(alert)

                else:
                    self.logger.warning(f"Acción desconocida: {action}")

            except Exception as e:
                self.logger.error(f"Error ejecutando acción {action}: {e}")

    def _log_alert(self, alert: Alert):
        """Registra la alerta en logs"""
        log_msg = (
            f"[{alert.level.value.upper()}] {alert.alert_type.value} - "
            f"{alert.message} (Conf: {alert.confidence:.2f}) - "
            f"{alert.source} → {alert.destination}"
        )
        self.logger.error(log_msg)

    def _send_telegram_alert(self, alert: Alert):
        """Envía alerta a Telegram"""
        message = (
            f"🚨 {alert.level.value.upper()}\n"
            f"📍 {alert.alert_type.value}\n"
            f"📄 {alert.message}\n"
            f"🔗 {alert.source} → {alert.destination}\n"
            f"📊 Conf: {alert.confidence:.2f}\n"
            f"⏰ {alert.timestamp.strftime('%H:%M:%S')}"
        )

        # TODO: Integrar con bot de Telegram
        self.logger.info(f"[Telegram] {message}")

    def _send_webhook_alert(self, alert: Alert):
        """Envía alerta vía webhook"""
        webhook_url = "http://localhost:8000/alerts"  # TODO: Configurable

        try:
            import requests
            requests.post(
                webhook_url,
                json=alert.to_dict(),
                timeout=5
            )
            self.logger.info(f"[Webhook] Alerta enviada a {webhook_url}")
        except Exception as e:
            self.logger.error(f"[Webhook] Error: {e}")

    def save_alert(self, alert: Alert):
        """Guarda alerta en archivo"""
        timestamp = alert.timestamp.strftime("%Y%m%d_%H%M%S")
        alert_file = self.alert_dir / f"alert-{alert.id}-{timestamp}.json"

        with open(alert_file, 'w') as f:
            json.dump(alert.to_dict(), f, indent=2)

        self.logger.debug(f"Alerta guardada: {alert_file}")

    def acknowledge_alert(self, alert_id: str):
        """Reconoce una alerta"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.is_acknowledged = True
                self.logger.info(f"Alerta reconocida: {alert_id}")
                break

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Obtiene alertas pendientes"""
        return [
            alert.to_dict()
            for alert in self.active_alerts
            if not alert.is_acknowledged
        ]

    def cleanup_old_alerts(self):
        """Limpia alertas antiguas"""
        now = datetime.now()
        cutoff = now - timedelta(hours=self.max_age_hours)

        # Filtrar alertas antiguas
        self.active_alerts = [
            alert for alert in self.active_alerts
            if alert.timestamp > cutoff
        ]

        self.logger.info(f"Limpieza completada: {len(self.active_alerts)} alertas restantes")

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas"""
        return {
            "total_alerts": len(self.active_alerts),
            "pending": len([a for a in self.active_alerts if not a.is_acknowledged]),
            "rules": len(self.rules),
            "storage_backend": self.storage_backend
        }


class ResponseEngine:
    """Motor de respuesta"""

    def __init__(self, alert_manager: AlertManager):
        """
        Inicializa el motor de respuesta.

        Args:
            alert_manager: AlertManager
        """
        self.alert_manager = alert_manager

        self.logger = logging.getLogger(__name__)
        self.logger.info("ResponseEngine inicializado")

    def register_callback(self, callback: Callable):
        """Registra callback para alertas"""
        self.alert_manager.alert_callbacks.append(callback)
        self.logger.info(f"Callback registrado: {callback.__name__}")

    def process_alert(self, alert: Alert):
        """
        Procesa una alerta según reglas de respuesta.

        Args:
            alert: Alerta a procesar
        """
        self.logger.info(f"Procesando alerta: {alert.id}")

        # TODO: Implementar reglas de respuesta complejas
        # - Bloquear tráfico
        # - Notificar administrador
        # - Iniciar contenedores de análisis
        # - Generar reporte de incidente

        if alert.level == AlertLevel.CRITICAL:
            self.logger.critical(f"ALERTA CRÍTICA: {alert.message}")
            # TODO: Notificar administrador directamente

        elif alert.level == AlertLevel.SEVERE:
            self.logger.error(f"ALERTA SEVERA: {alert.message}")

        elif alert.level == AlertLevel.WARNING:
            self.logger.warning(f"ALERTA WARNING: {alert.message}")

    def auto_response(self, alert: Alert):
        """
        Ejecuta respuesta automática para alertas críticas.

        Args:
            alert: Alerta a procesar
        """
        if alert.level.value in ["critical", "severe"]:
            self.logger.warning(
                f"Ejecutando respuesta automática para alerta {alert.id}"
            )

            # TODO: Implementar respuestas:
            # - Capturar packet trace
            # - Bloquear fuente temporalmente
            # - Generar reporte completo
            # - Iniciar workflow de incident response

            self.logger.info(f"Respuesta automática completada para {alert.id}")