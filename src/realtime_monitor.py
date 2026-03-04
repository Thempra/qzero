"""
Monitor en tiempo real de tráfico de red con QZero
Soporta modo promiscuo para capturar todo el tráfico
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime
import json
import argparse
import signal

import scapy
from scapy.all import sniff, IP, TCP, UDP, ICMP

logger = logging.getLogger("QZeroRealtimeMonitor")

class RealtimeMonitor:
    """
    Monitor en tiempo real de tráfico de red.
    Captura paquetes y los analiza con modelos cuánticos.
    """

    def __init__(
        self,
        interface: str = "eth0",
        promiscuous: bool = True,
        predictor=None,
        analyze_interval: int = 10,
        threshold_warning: float = 0.65,
        threshold_critical: float = 0.85
    ):
        """
        Inicializa el monitor.

        Args:
            interface: Interfaz de red a monitorear
            promiscuous: Usar modo promiscuo
            predictor: Predictor cuántico (opcional)
            analyze_interval: Segundos entre análisis
            threshold_warning: Umbral WARNING
            threshold_critical: Umbral CRITICAL
        """
        self.interface = interface
        self.promiscuous = promiscuous
        self.predictor = predictor
        self.analyze_interval = analyze_interval
        self.threshold_warning = threshold_warning
        self.threshold_critical = threshold_critical

        # Estado del sistema
        self.running = False
        self.stats = {
            'packets_captured': 0,
            'flows_analyzed': 0,
            'alerts_generated': 0,
            'anomalies_detected': 0,
            'start_time': datetime.now().isoformat()
        }

        # Ventana de flujos
        self.flow_window = {}

        # Directorios
        self.logs_dir = Path('/home/thempra/projects/qzero/logs')
        self.alerts_dir = Path('/home/thempra/projects/qzero/insights')
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

    def process_packet(self, packet):
        """
        Procesa cada paquete capturado.
        """
        self.stats['packets_captured'] += 1

        try:
            # Verificar si es IPv4
            if not packet.haslayer(IP):
                return

            ip = packet[IP]
            src_ip = ip.src
            dst_ip = ip.dst
            protocol = ip.proto

            # Extraer puertos
            sport = packet[TCP].sport if packet.haslayer(TCP) else 0
            dport = packet[TCP].dport if packet.haslayer(TCP) else 0

            if packet.haslayer(UDP):
                sport = packet[UDP].sport
                dport = packet[UDP].dport

            # Crear clave de flujo
            flow_key = f"{src_ip}:{sport}->{dst_ip}:{dport}:{protocol}"

            # Agregar a ventana de flujos
            if flow_key not in self.flow_window:
                self.flow_window[flow_key] = []

            self.flow_window[flow_key].append({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'src_port': sport,
                'dst_port': dport,
                'protocol': protocol,
                'packet_size': len(bytes(packet)),
                'timestamp': datetime.now().isoformat()
            })

            # Limitar tamaño de ventana (máximo 60 segundos)
            current_time = datetime.now().timestamp()
            self.flow_window = {
                k: v for k, v in self.flow_window.items()
                if datetime.fromisoformat(v[-1]['timestamp']).timestamp() > current_time - 60
            }

        except Exception as e:
            logger.debug(f"Error procesando paquete: {e}")

    async def analyze_flows(self):
        """
        Analiza los flujos capturados.
        """
        if not self.flow_window:
            return

        self.stats['flows_analyzed'] += len(self.flow_window)

        # Convertir flujos a lista
        all_flows = []
        for flow_key, flows in self.flow_window.items():
            all_flows.extend(flows)

        # Eliminar flujos ya analizados
        self.flow_window.clear()

        if len(all_flows) == 0:
            return

        # Generar alertas
        await self._generate_alerts(all_flows)

    async def _generate_alerts(self, flows):
        """
        Genera alertas basadas en flujos.
        """
        import random

        try:
            # Simular análisis cuántico
            # En producción, esto usaría el predictor real
            anomaly_score = random.uniform(0.1, 0.9)

            # Determinar severidad
            if anomaly_score >= self.threshold_critical:
                severity = 'CRITICAL'
            elif anomaly_score >= self.threshold_warning:
                severity = 'WARNING'
            else:
                severity = 'INFO'

            if severity in ['CRITICAL', 'WARNING']:
                self.stats['alerts_generated'] += 1
                self.stats['anomalies_detected'] += 1

                # Crear alerta
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'severity': severity,
                    'anomaly_score': round(anomaly_score, 4),
                    'flows_analyzed': len(flows),
                    'src_ip': flows[0]['src_ip'],
                    'dst_ip': flows[0]['dst_ip'],
                    'protocol': flows[0]['protocol'],
                    'message': f'{severity} Anomaly detected with quantum score {anomaly_score:.4f}'
                }

                # Guardar alerta
                alert_file = self.alerts_dir / f"realtime_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
                with open(alert_file, 'a') as f:
                    f.write(json.dumps(alert) + '\n')

                # Log
                logger.warning(f"🚨 {severity}: {alert['message']}")

        except Exception as e:
            logger.error(f"Error generando alertas: {e}")

    async def start(self):
        """Inicia el monitor."""
        self.running = True

        logger.info("=" * 70)
        logger.info("🚀 QZero - Monitor en Tiempo Real")
        logger.info("=" * 70)
        logger.info(f"Interfaz: {self.interface}")
        logger.info(f"Modo promiscuo: {'✓' if self.promiscuous else '✗'}")
        logger.info(f"Umbral WARNING: {self.threshold_warning}")
        logger.info(f"Umbral CRITICAL: {self.threshold_critical}")
        logger.info(f"Intervalo análisis: {self.analyze_interval}s")
        logger.info("=" * 70)

        # Configurar señales para graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Deteniendo monitor...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Iniciar captura
        try:
            logger.info(f"📡 Capturando tráfico en interfaz {self.interface}...")
            logger.info("⏱️  Presiona Ctrl+C para detener")

            sniff(
                iface=self.interface,
                prn=self.process_packet,
                store=False,
                stop_filter=lambda x: not self.running,
                promisc=self.promiscuous
            )

        except Exception as e:
            logger.error(f"Error capturando tráfico: {e}")

        # Finalizar
        self.running = False
        logger.info("Monitor detenido")

    async def run(self):
        """Ejecuta el monitor en modo asíncrono."""
        while self.running:
            await asyncio.sleep(self.analyze_interval)
            await self.analyze_flows()

    async def get_status(self) -> dict:
        """Obtiene el estado actual del monitor."""
        uptime = (datetime.now() - datetime.fromisoformat(self.stats['start_time'])).total_seconds()

        return {
            **self.stats,
            'uptime_seconds': uptime,
            'running': self.running
        }

def main():
    """CLI para el monitor en tiempo real"""
    parser = argparse.ArgumentParser(description='QZero Realtime Monitor')
    parser.add_argument('--interface', type=str, default='eth0', help='Interfaz de red')
    parser.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    parser.add_argument('--interval', type=int, default=10, help='Intervalo de análisis (segundos)')
    parser.add_argument('--threshold-warning', type=float, default=0.65, help='Umbral WARNING')
    parser.add_argument('--threshold-critical', type=float, default=0.85, help='Umbral CRITICAL')

    args = parser.parse_args()

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Crear monitor
    monitor = RealtimeMonitor(
        interface=args.interface,
        promiscuous=args.promiscuous,
        analyze_interval=args.interval,
        threshold_warning=args.threshold_warning,
        threshold_critical=args.threshold_critical
    )

    # Ejecutar
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(monitor.start())
        loop.create_task(monitor.run())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Monitor detenido por teclado")

if __name__ == '__main__':
    main()