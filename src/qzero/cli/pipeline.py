"""
Módulo de CLI para Pipeline de QZero
"""

import sys
from pathlib import Path
from datetime import datetime
import time
import signal
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qzero.pipeline import (
    Packet,
    PacketType,
    RingBuffer,
    PacketBatch,
    PacketProcessor,
    MemoryEfficientSniffer
)


class RingBufferCLI:
    """CLI para Ring Buffer"""

    @staticmethod
    def info(buffer_size: int = 10000):
        """Muestra información del buffer"""
        buffer = RingBuffer(max_size=buffer_size)

        print(f"📊 RingBuffer Info:")
        print(f"   Tamaño máximo: {buffer.max_size}")
        print(f"   Paquetes actuales: {buffer.current_size}")
        print(f"   Uso: {buffer.get_stats()['usage_percent']:.2f}%")
        print(f"   Slots disponibles: {buffer.get_stats()['available_slots']}")
        print()


class MemoryPipelineCLI:
    """CLI para Memory Pipeline"""

    @staticmethod
    def run(args):
        """Ejecuta el pipeline"""
        setup_logging(args.verbose)

        try:
            sniffer = MemoryEfficientSniffer(
                interface=args.interface,
                promiscuous=args.promiscuous,
                buffer_size=args.buffer,
                batch_size=args.batch_size
            )

            print(f"🚀 Iniciando pipeline de ingestión en memoria")
            print(f"   Interfaz: {args.interface}")
            print(f"   Modo promiscuo: {args.promiscuous}")
            print(f"   Buffer: {args.buffer}")
            print(f"   Batch size: {args.batch_size}")
            print(f"   Presiona Ctrl+C para detener\n")

            # Señal de interrupción
            def signal_handler(sig, frame):
                print(f"\n🛑 Deteniendo pipeline por usuario")
                sniffer.processor.stop()
                raise KeyboardInterrupt

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            try:
                sniffer.start()

                # Mostrar estadísticas en tiempo real
                while True:
                    stats = sniffer.get_stats()
                    buffer_usage = stats['buffer_stats']['usage_percent']
                    print(f"\r📊 Buffer: {buffer_usage:.1f}% | "
                          f"Paquetes: {stats['processor_stats']['packet_count']} | "
                          f"Anomalías: {stats['processor_stats']['anomaly_count']}", end="")
                    time.sleep(1)

            except KeyboardInterrupt:
                print(f"\n\n✅ Pipeline detenido")

            # Mostrar estadísticas finales
            final_stats = sniffer.get_stats()
            print(f"\n{'='*60}")
            print("Pipeline Detenido - Resumen")
            print(f"{'='*60}")
            print(f"📊 Paquetes procesados: {final_stats['processor_stats']['packet_count']}")
            print(f"⚠️  Anomalías detectadas: {final_stats['processor_stats']['anomaly_count']}")
            print(f"💾 Uso de buffer: {final_stats['buffer_stats']['usage_percent']:.1f}%")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"❌ Error: {e}", file=sys.stderr)
            sys.exit(1)


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
            logging.FileHandler(log_dir / "pipeline.log")
        ]
    )