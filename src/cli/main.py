#!/usr/bin/env python3
"""
CLI Principal para QZero
"""

import argparse
import sys
import logging
from pathlib import Path

from qzero.core.monitor import QZeroMonitor
from qzero.interface.promiscuous import PromiscuousInterface


def setup_logging(verbose=False):
    """Configurar logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def monitor_command(args):
    """Comando para iniciar monitor en tiempo real"""
    setup_logging(args.verbose)
    
    if args.promiscuous:
        print("🔄 Activando modo PROMISCUO...")
        interface = PromiscuousInterface(args.interface)
        interface.activate()
    
    monitor = QZeroMonitor(
        interface=args.interface,
        promiscuous=args.promiscuous,
        output_dir=args.output
    )
    
    monitor.start()


def pcap_command(args):
    """Comando para analizar PCAP"""
    setup_logging(args.verbose)
    
    from qzero.analysis.pcap import PCAPAnalyzer
    
    analyzer = PCAPAnalyzer(args.file)
    results = analyzer.analyze()
    
    print(f"📊 Análisis completado:")
    print(f"   - Total paquetes: {results['total_packets']}")
    print(f"   - Anomalías detectadas: {results['anomalies']}")
    print(f"   - Amenazas: {results['threats']}")


def detect_command(args):
    """Comando para ejecutar detección"""
    setup_logging(args.verbose)
    
    from qzero.core.detector import AnomalyDetector
    
    detector = AnomalyDetector(
        mode=args.mode,
        threshold=args.threshold
    )
    
    results = detector.run()
    
    print(f"🔍 Detección completada:")
    print(f"   - Modo: {results['mode']}")
    print(f"   - Umbral: {results['threshold']}")
    print(f"   - Anomalías: {results['anomalies']}")
    
    return results


def interface_command(args):
    """Comando para gestionar interfaces"""
    setup_logging(args.verbose)
    
    if args.mode == "promiscuous":
        interface = PromiscuousInterface(args.interface)
        
        if args.activate:
            interface.activate()
            print(f"✅ Interfaz {args.interface} activada en modo promiscuo")
        elif args.deactivate:
            interface.deactivate()
            print(f"⬇️  Interfaz {args.interface} desactivada")
        else:
            status = interface.get_status()
            print(f"📊 Estado: {status}")


def main():
    """CLI Principal"""
    parser = argparse.ArgumentParser(
        prog='qzero',
        description='Sistema de Detección de Anomalías y Monitoreo de Seguridad'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='QZero v1.0.0'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Iniciar monitor en tiempo real')
    monitor_parser.add_argument('--interface', required=True, help='Interfaz de red')
    monitor_parser.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')
    monitor_parser.add_argument('--output', default='reports', help='Directorio de salida')
    monitor_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    monitor_parser.set_defaults(func=monitor_command)
    
    # PCAP command
    pcap_parser = subparsers.add_parser('pcap', help='Analizar archivo PCAP')
    pcap_parser.add_argument('--file', required=True, help='Archivo PCAP')
    pcap_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    pcap_parser.set_defaults(func=pcap_command)
    
    # Detect command
    detect_parser = subparsers.add_parser('detect', help='Ejecutar detección')
    detect_parser.add_argument('--mode', choices=['real-time', 'batch', 'predictive'], 
                              default='real-time', help='Modo de detección')
    detect_parser.add_argument('--threshold', type=float, default=0.7, 
                              help='Umbral de detección')
    detect_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    detect_parser.set_defaults(func=detect_command)
    
    # Interface command
    interface_parser = subparsers.add_parser('interface', help='Gestionar interfaces')
    interface_parser.add_argument('--interface', required=True, help='Interfaz de red')
    interface_parser.add_argument('--activate', action='store_true', help='Activar promiscuo')
    interface_parser.add_argument('--deactivate', action='store_true', help='Desactivar')
    interface_parser.add_argument('--verbose', '-v', action='store_true', help='Modo detallado')
    interface_parser.set_defaults(func=interface_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()
