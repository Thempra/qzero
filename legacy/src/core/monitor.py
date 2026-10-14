#!/usr/bin/env python3
"""
Módulo de Monitoreo de QZero
"""

import time
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from threading import Thread, Event

from qzero.interface.promiscuous import PromiscuousInterface
from qzero.core.detector import AnomalyDetector


class QZeroMonitor:
    """
    Monitor principal de QZero para análisis en tiempo real
    """
    
    def __init__(
        self,
        interface: str,
        promiscuous: bool = False,
        output_dir: str = "reports"
    ):
        """
        Inicializar monitor
        
        Args:
            interface: Nombre de la interfaz de red
            promiscuous: Usar modo promiscuo
            output_dir: Directorio para reportes
        """
        self.interface = interface
        self.promiscuous = promiscuous
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.running = False
        self.stop_event = Event()
        self.detector = AnomalyDetector()
        
        self.stats = {
            'start_time': None,
            'packets': 0,
            'anomalies': 0,
            'alerts': []
        }
        
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Iniciar monitoreo"""
        self.logger.info("🚀 Iniciando QZero Monitor...")
        
        if self.promiscuous:
            self.logger.info("📡 Usando modo PROMISCUO")
            self.interface = PromiscuousInterface(self.interface)
            if not self.interface.activate():
                self.logger.error("❌ No se pudo activar modo promiscuo")
                return
        
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()
        
        # Iniciar thread de monitoreo
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("✅ Monitor iniciado. Presiona Ctrl+C para detener")
    
    def stop(self):
        """Detener monitoreo"""
        self.logger.info("⏸️  Deteniendo monitor...")
        
        self.running = False
        self.stop_event.set()
        
        if self.promiscuous and hasattr(self, 'interface'):
            self.interface.deactivate()
        
        # Guardar estadísticas
        self._save_stats()
        
        self.logger.info("✅ Monitor detenido")
    
    def _monitor_loop(self):
        """Bucle principal de monitoreo"""
        try:
            while self.running and not self.stop_event.is_set():
                time.sleep(0.1)
                
                # Aquí iría la lógica de captura de paquetes
                # Por ahora, simulamos monitoreo
                self.stats['packets'] += 1
                
                # Analizar cada cierto tiempo
                if self.stats['packets'] % 100 == 0:
                    self._analyze()
        
        except Exception as e:
            self.logger.error(f"❌ Error en monitoreo: {e}")
    
    def _analyze(self):
        """Ejecutar análisis"""
        try:
            # Detectar anomalías
            result = self.detector.detect()
            
            if result['anomaly_detected']:
                self.stats['anomalies'] += 1
                alert = {
                    'timestamp': datetime.now().isoformat(),
                    'type': result['anomaly_type'],
                    'severity': result['severity'],
                    'details': result['details']
                }
                self.stats['alerts'].append(alert)
                
                self.logger.warning(f"⚠️  ALERTA: {result['anomaly_type']} ({result['severity']})")
            
        except Exception as e:
            self.logger.error(f"❌ Error en análisis: {e}")
    
    def _save_stats(self):
        """Guardar estadísticas"""
        output_file = self.output_dir / f"monitor-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        self.logger.info(f"💾 Estadísticas guardadas en {output_file}")
    
    def get_status(self) -> Dict:
        """Obtener estado"""
        return {
            'running': self.running,
            'packets': self.stats['packets'],
            'anomalies': self.stats['anomalies'],
            'alerts': len(self.stats['alerts']),
            'start_time': self.stats['start_time']
        }


def main():
    """Ejemplo de uso"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor de QZero')
    parser.add_argument('--interface', required=True, help='Interfaz de red')
    parser.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    parser.add_argument('--output', default='reports', help='Directorio de salida')
    
    args = parser.parse_args()
    
    monitor = QZeroMonitor(args.interface, args.promiscuous, args.output)
    
    try:
        monitor.start()
        
        # Mantener el script vivo
        while True:
            time.sleep(1)
            status = monitor.get_status()
            print(f"\r📊 Stats: {status['packets']} paquetes, {status['anomalies']} anomalías", end='')
    
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == '__main__':
    main()
