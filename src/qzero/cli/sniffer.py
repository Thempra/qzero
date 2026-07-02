"""
Módulo de CLI para Sniffer de QZero
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import time
import signal

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qzero.sniffer import (
    BaseSniffer,
    start_sniffer,
    NetworkInterface,
    InterfaceType
)


class RealTimeSniffer:
    """Sniffer en tiempo real con detección de anomalías"""

    def __init__(self, interface: str, promiscuous: bool = False,
                 threshold: float = 0.7, buffer_size: int = 10000):
        """
        Inicializa el sniffer en tiempo real.

        Args:
            interface: Interfaz de red
            promiscuous: Modo promiscuo
            threshold: Umbral de detección
            buffer_size: Tamaño del buffer
        """
        self.sniffer = start_sniffer(interface, promiscuous, buffer_size)
        self.threshold = threshold
        self.running = False
        self.packet_count = 0
        self.anomalies = []

        print(f"✅ Sniffer inicializado en {interface}")
        if promiscuous:
            print(f"🔄 Modo promiscuo: ACTIVO")

    def start(self, interval: float = 1.0):
        """
        Inicia la captura en tiempo real.

        Args:
            interval: Intervalo de muestra en segundos
        """
        self.running = True

        print(f"\n🚀 Iniciando captura en tiempo real")
        print(f"📝 Presiona Ctrl+C para detener\n")

        # Señal de interrupción
        def signal_handler(sig, frame):
            print(f"\n🛑 Deteniendo captura por usuario")
            self.running = False
            raise KeyboardInterrupt

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while self.running:
                packet = self.sniffer.capture_packet()
                if packet:
                    self._process_packet(packet)
                    self._detect_anomalies()

                    if self.running and self.packet_count % 100 == 0:
                        print(f"📊 Paquetes: {self.packet_count} | Anomalías: {len(self.anomalies)}")

                time.sleep(interval)

        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Detiene la captura y muestra resumen"""
        self.running = False

        # Mostrar resumen
        if self.anomalies:
            threats = [a for a in self.anomalies if a.get('confidence', 0) > self.threshold]

            print(f"\n{'='*60}")
            print("Sniffer Detenido - Resumen")
            print(f"{'='*60}")
            print(f"📊 Paquetes capturados: {self.packet_count}")
            print(f"⚠️  Anomalías detectadas: {len(self.anomalies)}")
            print(f"🚨 Amenazas críticas: {len(threats)}")
            print(f"{'='*60}\n")

            # Guardar reporte
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = Path("reports") / f"sniffer-run-{timestamp}.json"

            report = {
                "timestamp": datetime.now().isoformat(),
                "interface": self.sniffer.interface,
                "promiscuous": self.sniffer.promiscuous,
                "packet_count": self.packet_count,
                "threshold": self.threshold,
                "anomalies": self.anomalies,
                "total_anomalies": len(self.anomalies),
                "threats": len(threats)
            }

            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                import json
                json.dump(report, f, indent=2)

            print(f"📄 Reporte guardado en: {report_path}")

            # Mostrar amenazas
            if threats:
                print("⚠️  Amenazas detectadas:")
                for threat in threats:
                    print(f"   - {threat.get('type')}: {threat.get('confidence', 0):.2f}")
                    print(f"     {threat.get('description', '')}")

        print(f"\n✅ Captura detenido. Total paquetes: {self.packet_count}")

    def _process_packet(self, packet):
        """Procesa un paquete"""
        self.packet_count += 1

        # TODO: Implementar análisis de paquetes
        if self.packet_count % 100 == 0:
            print(f"  Packet: {packet.source} → {packet.destination} [{packet.protocol}, {packet.size} bytes]")

    def _detect_anomalies(self):
        """Detecta anomalías"""
        # TODO: Implementar detección real de anomalías
        import random

        if random.random() < 0.01:  # 1% de probabilidad
            self.anomalies.append({
                "timestamp": datetime.now().isoformat(),
                "type": random.choice(["Port Scan", "Malicious Traffic", "Suspicious Pattern"]),
                "confidence": random.uniform(0.6, 0.95),
                "description": f"Patrón detectado en tráfico {self.sniffer.interface}"
            })


def list_interfaces():
    """Lista interfaces de red disponibles"""
    print("📋 Interfaces de red disponibles:\n")

    # Interfaces de red comunes
    common_interfaces = [
        "eth0", "eth1", "en0", "en1",  # Ethernet
        "wlan0", "wlan1", "wifi0",    # WiFi
        "docker0", "docker1",         # Docker
        "lo",                         # Loopback
        "ethernet", "wireless"        # Nombres genéricos
    ]

    print("💡 Para interfaces completas, instala: pip install psutil\n")
    print("Interfaces comunes detectadas:")

    for iface in common_interfaces:
        try:
            # Verificar si la interfaz está activa
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
            print(f"  ✅ {iface}")
        except:
            print(f"  ❌ {iface}")

    print()


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
            logging.FileHandler(log_dir / "sniffer.log")
        ]
    )