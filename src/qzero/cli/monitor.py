#!/usr/bin/env python3
"""
Módulo de monitor de tráfico en tiempo real para QZero
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """Monitor de tráfico de red en tiempo real"""

    def __init__(self, interface: str, promiscuous: bool = False, output_dir: str = "reports"):
        """
        Inicializa el monitor.

        Args:
            interface: Interfaz de red a monitorear
            promiscuous: Modo promiscuo activado
            output_dir: Directorio para logs
        """
        self.interface = interface
        self.promiscuous = promiscuous
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.running = False
        self.packet_count = 0

        logger.info(f"Inicializando monitor en interfaz: {interface}")
        if promiscuous:
            logger.info("Modo PROMISCUO activado")

    def start(self, interval: float = 1.0):
        """
        Inicia el monitoreo.

        Args:
            interval: Intervalo de muestra en segundos
        """
        self.running = True
        logger.info(f"Iniciando monitoreo... (presione Ctrl+C para detener)")

        try:
            while self.running:
                self._monitor_tick()
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Monitoreo detenido por usuario")
            self.stop()

    def stop(self):
        """Detiene el monitoreo"""
        self.running = False
        logger.info(f"Monitoreo detenido. Total paquetes: {self.packet_count}")

    def _monitor_tick(self):
        """Tick de monitoreo"""
        self.packet_count += 1

        # TODO: Implementar captura real de paquetes con scapy
        # Por ahora, solo contamos paquetes simulados
        if self.packet_count % 100 == 0:
            logger.debug(f"Paquetes capturados: {self.packet_count}")


class RealTimeMonitor(NetworkMonitor):
    """Monitor de tiempo real con detección de anomalías"""

    def __init__(self, *args, threshold: float = 0.7, **kwargs):
        """
        Inicializa el monitor de tiempo real.

        Args:
            *args: Argumentos para NetworkMonitor
            threshold: Umbral de detección
            **kwargs: Argumentos adicionales para NetworkMonitor
        """
        super().__init__(*args, **kwargs)
        self.threshold = threshold
        self.anomalies = []

    def start(self, interval: float = 1.0):
        """Inicia el monitoreo en tiempo real"""
        self.running = True
        logger.info(f"Iniciando monitoreo en tiempo real (threshold: {self.threshold})")
        logger.info("Presione Ctrl+C para detener")

        try:
            while self.running:
                self._monitor_tick()
                self._detect_anomalies()

                if self.running and self.packet_count % 100 == 0:
                    logger.info(f"Paquetes: {self.packet_count} | Anomalías: {len(self.anomalies)}")

        except KeyboardInterrupt:
            logger.info("Monitoreo detenido por usuario")
            self.stop()

    def _detect_anomalies(self):
        """Detecta anomalías basadas en patrones"""
        # TODO: Implementar detección real de anomalías
        # Por ahora, detecta aleatoriamente
        import random
        if random.random() < 0.01:  # 1% de probabilidad de anomalía
            self.anomalies.append({
                "timestamp": datetime.now().isoformat(),
                "type": random.choice(["Port Scan", "Malicious Traffic", "Suspicious Pattern"]),
                "confidence": random.uniform(0.6, 0.95)
            })

    def stop(self):
        """Detiene el monitoreo y guarda reporte"""
        self.running = False
        logger.info(f"Monitoreo detenido. Total paquetes: {self.packet_count}")

        # Guardar reporte de anomalías
        if self.anomalies:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.output_dir / f"realtime-monitor-{timestamp}.json"

            with open(report_path, 'w') as f:
                import json
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "interface": self.interface,
                    "packet_count": self.packet_count,
                    "threshold": self.threshold,
                    "anomalies": self.anomalies,
                    "total_anomalies": len(self.anomalies)
                }, f, indent=2)

            logger.info(f"Reporte de anomalías guardado en: {report_path}")

            # Mostrar resumen
            threats = [a for a in self.anomalies if a["confidence"] > self.threshold]
            logger.info(f"⚠️  Amenazas detectadas: {len(threats)}")


def start_monitor(args):
    """Función de CLI para iniciar monitor"""
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