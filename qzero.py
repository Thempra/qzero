#!/usr/bin/env python3
"""
QZero - Sistema Unificado de Detección de Anomalías Cuántico
Version: 2.0.0
Autor: QZero Development Team
"""

__version__ = "2.0.0"
__author__ = "QZero Development Team"
__license__ = "MIT"

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Importar módulos principales
from src.predictor import QZeroPredictor
from src.detection import NetworkTrafficAnalyzer
from src.api import create_app

# Clase principal
class QZero:
    """
    Clase principal para la plataforma QZero.

    Provee una interfaz unificada para:
    - Análisis de tráfico de red
    - Detección de anomalías cuánticas
    - API REST para integración
    - Análisis en tiempo real
    """

    def __init__(self, n_qubits: int = 4, use_qsvm: bool = True, use_qivae: bool = True):
        """
        Inicializa QZero con modelos cuánticos configurados.

        Args:
            n_qubits: Número de qubits para modelos cuánticos
            use_qsvm: Usar QSVM (Support Vector Machine cuántico)
            use_qivae: Usar QI-VAE (Variational Autoencoder cuántico)
        """
        self.predictor = QZeroPredictor(
            n_qubits=n_qubits,
            use_qsvm=use_qsvm,
            use_qivae=use_qivae
        )

    def train(self, n_samples: int = 5000, use_real_data: bool = False):
        """
        Entrena todos los modelos de QZero.

        Args:
            n_samples: Número de muestras para datos sintéticos
            use_real_data: Usar dataset real UGRansome
        """
        return self.predictor.train_all(
            n_samples=n_samples,
            use_real_data=use_real_data
        )

    def predict(self, X: list):
        """
        Realiza predicciones con los modelos entrenados.

        Args:
            X: Features de entrada

        Returns:
            Predicciones y scores
        """
        return self.predictor.predict(X)

    def analyze_traffic(self, pcap_file: str, method: str = "best"):
        """
        Analiza tráfico de red desde un archivo PCAP.

        Args:
            pcap_file: Ruta al archivo PCAP
            method: Método de análisis ('qsvm', 'qivae', 'best')

        Returns:
            Resultados del análisis
        """
        analyzer = NetworkTrafficAnalyzer()
        return analyzer.analyze(pcap_file, method)

    def get_api(self):
        """
        Obtiene la aplicación FastAPI para API REST.

        Returns:
            App FastAPI
        """
        return create_app(self.predictor)

    def start_realtime_monitor(self, interface: str = "eth0", promiscuous: bool = True):
        """
        Inicia monitor en tiempo real de tráfico de red.

        Args:
            interface: Interfaz de red a monitorear
            promiscuous: Usar modo promiscuo
        """
        # Importar el módulo de análisis en tiempo real
        from qzero.core.realtime_monitor import RealtimeMonitor

        monitor = RealtimeMonitor(
            interface=interface,
            promiscuous=promiscuous,
            predictor=self.predictor
        )

        return monitor

# CLI
def main():
    """CLI principal de QZero"""
    import argparse

    parser = argparse.ArgumentParser(description='QZero - Detección de Anomalías Cuántico')
    parser.add_argument('--version', action='version', version=f'QZero {__version__}')

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

    # Comando train
    train_parser = subparsers.add_parser('train', help='Entrenar modelos')
    train_parser.add_argument('--samples', type=int, default=5000, help='Número de muestras')
    train_parser.add_argument('--real-data', action='store_true', help='Usar datos reales')
    train_parser.add_argument('--qubits', type=int, default=4, help='Número de qubits')

    # Comando analyze
    analyze_parser = subparsers.add_parser('analyze', help='Analizar tráfico')
    analyze_parser.add_argument('--file', type=str, required=True, help='Archivo PCAP')
    analyze_parser.add_argument('--method', type=str, default='best', help='Método de análisis')

    # Comando server
    server_parser = subparsers.add_parser('server', help='Iniciar API REST')
    server_parser.add_argument('--host', type=str, default='0.0.0.0', help='Host')
    server_parser.add_argument('--port', type=int, default=8000, help='Puerto')
    server_parser.add_argument('--model-file', type=str, help='Archivo de modelo entrenado')

    # Comando monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitorear tráfico en tiempo real')
    monitor_parser.add_argument('--interface', type=str, default='eth0', help='Interfaz de red')
    monitor_parser.add_argument('--promiscuous', action='store_true', help='Modo promiscuo')

    args = parser.parse_args()

    if args.command == 'train':
        print(f"🧪 Entrenando QZero con {args.samples} muestras...")
        qzero = QZero(n_qubits=args.qubits)
        result = qzero.train(n_samples=args.samples, use_real_data=args.real_data)
        print(f"✅ Entrenamiento completado")

    elif args.command == 'analyze':
        print(f"🔍 Analizando {args.file}...")
        qzero = QZero()
        result = qzero.analyze_traffic(args.file, args.method)
        print(f"✅ Análisis completado: {result}")

    elif args.command == 'server':
        print(f"🚀 Iniciando servidor QZero en {args.host}:{args.port}")
        app = create_app()
        import uvicorn
        uvicorn.run(app, host=args.host, port=args.port)

    elif args.command == 'monitor':
        print(f"📡 Monitoreando interfaz {args.interface}...")
        print(f"{'Promiscuo' if args.promiscuous else 'No promiscuo'}")
        qzero = QZero()
        monitor = qzero.start_realtime_monitor(
            interface=args.interface,
            promiscuous=args.promiscuous
        )
        monitor.start()

    else:
        parser.print_help()

if __name__ == '__main__':
    main()