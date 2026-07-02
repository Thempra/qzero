"""
Módulo de CLI para Motor de Inferencia de QZero
"""

import sys
from pathlib import Path
import argparse
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qzero.inference import (
    InferenceEngine,
    FastInferencePipeline,
    FastInferenceCLI
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
            logging.FileHandler(log_dir / "inference.log")
        ]
    )


def cmd_inference_train(args):
    """Entrena el modelo de inferencia"""
    setup_logging(args.verbose)

    try:
        engine = InferenceEngine(model_path=args.model)

        if args.train_mode == 'simulation':
            print("📚 Modo: Simulación")
            print(f"   Model: {args.model or 'Simulado'}")
            print(f"   Threshold: {args.threshold}")
            print(f"   Presiona Ctrl+C para detener\n")

            import random
            import time

            for i in range(args.duration):
                # Generar paquetes simulados
                protocols = ['TCP', 'UDP', 'ICMP']
                sources = ['192.168.1.1', '10.0.0.1', '172.16.0.1', '10.0.0.5']
                destinations = ['192.168.1.100', '10.0.0.100', '172.16.0.100']

                packet = {
                    "timestamp": time.time(),
                    "source": random.choice(sources),
                    "destination": random.choice(destinations),
                    "protocol": random.choice(protocols),
                    "size": random.randint(64, 1500),
                    "payload": bytes([random.randint(0, 255) for _ in range(random.randint(0, 100))]),
                    "metadata": {
                        "ttl": random.randint(30, 255),
                        "id": random.randint(0, 9999),
                        "flags": random.choice(['S', 'F', '']),
                        "protocol": random.choice(protocols).lower()
                    }
                }

                # Extraer features y predecir
                is_anomaly, confidence, probability = engine.is_anomaly(packet)

                if args.verbose and is_anomaly:
                    print(f"  ⚠️  Anomalía: {confidence:.2f} - {packet['source']} → {packet['destination']}")

                if args.duration and i % 100 == 0:
                    print(f"   Paquetes: {i}")

                time.sleep(0.1)

            print(f"\n✅ Entrenamiento completado")

        elif args.train_mode == 'window':
            print("📊 Modo: Window-based Training")
            print(f"   Model: {args.model or 'Simulado'}")
            print(f"   Window size: {args.window}")
            print(f"   Min samples: {args.min_samples}")
            print(f"   Presiona Ctrl+C para detener\n")

            pipeline = FastInferencePipeline(
                engine=engine,
                window_size=args.window,
                min_samples=args.min_samples
            )

            import random
            import time

            def generate_packet():
                protocols = ['TCP', 'UDP', 'ICMP']
                sources = ['192.168.1.1', '10.0.0.1', '172.16.0.1']
                destinations = ['192.168.1.100', '10.0.0.100', '172.16.0.100']

                packet = {
                    "timestamp": time.time(),
                    "source": random.choice(sources),
                    "destination": random.choice(destinations),
                    "protocol": random.choice(protocols),
                    "size": random.randint(64, 1500),
                    "payload": bytes([random.randint(0, 255) for _ in range(random.randint(0, 100))]),
                    "metadata": {
                        "ttl": random.randint(30, 255),
                        "id": random.randint(0, 9999),
                        "flags": random.choice(['S', 'F', '']),
                        "protocol": random.choice(protocols).lower()
                    }
                }
                return packet

            try:
                for i in range(args.duration):
                    packet = generate_packet()
                    pipeline.add_packet(packet)

                    if args.duration and i % 100 == 0:
                        stats = pipeline.get_stats()
                        print(f"   Stats: {stats['total_packets']} | "
                              f"Anomalías: {stats['anomaly_count']}")

                    time.sleep(0.1)

            except KeyboardInterrupt:
                print(f"\n\n✅ Entrenamiento detenido")

            pipeline.train_from_window()
            print(f"\n✅ Modelo entrenado con ventana")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_inference_test(args):
    """Testea el modelo de inferencia"""
    setup_logging(args.verbose)

    try:
        engine = InferenceEngine(model_path=args.model, threshold=args.threshold)

        print(f"🧪 Testeando Inference Engine")
        print(f"   Model: {args.model or 'Simulado'}")
        print(f"   Threshold: {args.threshold}")
        print(f"   Presiona Ctrl+C para detener\n")

        import random
        import time

        for i in range(args.duration):
            # Generar paquetes
            protocols = ['TCP', 'UDP', 'ICMP']
            sources = ['192.168.1.1', '10.0.0.1', '172.16.0.1']
            destinations = ['192.168.1.100', '10.0.0.100', '172.16.0.100']

            packet = {
                "timestamp": time.time(),
                "source": random.choice(sources),
                "destination": random.choice(destinations),
                "protocol": random.choice(protocols),
                "size": random.randint(64, 1500),
                "payload": bytes([random.randint(0, 255) for _ in range(random.randint(0, 100))]),
                "metadata": {
                    "ttl": random.randint(30, 255),
                    "id": random.randint(0, 9999),
                    "flags": random.choice(['S', 'F', '']),
                    "protocol": random.choice(protocols).lower()
                }
            }

            # Predecir
            is_anomaly, confidence, probability = engine.is_anomaly(packet)

            if args.verbose:
                status = "⚠️  ANOMALÍA" if is_anomaly else "✅ NORMAL"
                print(f"  [{status}] {packet['source']} → {packet['destination']} "
                      f"| Conf: {confidence:.2f} | Prob: {probability:.2f}")

            if args.duration and i % 50 == 0:
                print(f"   Paquetes testeados: {i}")

            time.sleep(0.1)

        print(f"\n✅ Test completado")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_inference_stats(args):
    """Muestra estadísticas del modelo"""
    setup_logging(args.verbose)

    try:
        engine = InferenceEngine(model_path=args.model, threshold=args.threshold)

        print(f"📊 Inference Engine Stats")
        print(f"{'='*60}")

        if engine.model:
            print(f"Model: {args.model}")
            print(f"Features: {engine.features}")
            print(f"Status: ✅ Loaded")
        else:
            print(f"Model: {args.model or 'Simulado'}")
            print(f"Status: ⚠️  Simulation Mode")

        print(f"{'='*60}\n")

        # Simular algunas predicciones
        import random
        for i in range(5):
            protocols = ['TCP', 'UDP', 'ICMP']
            packet = {
                "source": f"192.168.1.{i+1}",
                "destination": f"10.0.0.{i+1}",
                "protocol": random.choice(protocols),
                "size": random.randint(64, 1500),
                "payload": bytes([random.randint(0, 255) for _ in range(10)]),
                "metadata": {
                    "ttl": random.randint(30, 255),
                    "flags": random.choice(['S', 'F', '']),
                    "protocol": random.choice(protocols).lower()
                }
            }

            is_anomaly, confidence, probability = engine.is_anomaly(packet)

            status = "⚠️  ANOMALÍA" if is_anomaly else "✅ NORMAL"
            print(f"  [{status}] {packet['source']} → {packet['destination']} "
                  f"| Prob: {probability:.3f} | Conf: {confidence:.2f}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)