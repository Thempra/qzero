#!/usr/bin/env python3
"""
Motor de Inferencia Rápida para QZero

Integra el pipeline con análisis de anomalías usando modelos ML
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import numpy as np
import json

logger = logging.getLogger(__name__)


class InferenceEngine:
    """Motor de inferencia para detección de anomalías"""

    def __init__(self, model_path: Optional[str] = None, threshold: float = 0.7):
        """
        Inicializa el motor de inferencia.

        Args:
            model_path: Ruta al modelo ML
            threshold: Umbral de detección (0-1)
        """
        self.model_path = model_path
        self.threshold = threshold

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"InferenceEngine inicializado con threshold: {threshold}")

        # Cargar modelo si está disponible
        self.model = None
        self.features = self._get_feature_names()

        if model_path and Path(model_path).exists():
            self.model = self._load_model(model_path)

    def _get_feature_names(self) -> List[str]:
        """Obtiene nombres de features"""
        return [
            "packet_size",
            "inter_packet_gap",
            "source_entropy",
            "destination_entropy",
            "protocol_type",
            "ttl",
            "flag_count",
            "payload_length"
        ]

    def _load_model(self, model_path: str):
        """Carga un modelo ML"""
        try:
            # Intentar cargar con sklearn
            from sklearn.externals import joblib
            self.logger.info(f"Cargando modelo desde {model_path}")
            model = joblib.load(model_path)
            return model
        except ImportError:
            try:
                # Intentar con pickle
                import pickle
                with open(model_path, 'rb') as f:
                    self.logger.info(f"Cargando modelo pickle desde {model_path}")
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"No se pudo cargar el modelo: {e}")
                return None

    def extract_features(self, packet: Dict[str, Any]) -> np.ndarray:
        """
        Extrae features de un paquete.

        Args:
            packet: Paquete con metadata

        Returns:
            Array de features
        """
        features = []

        # Packet size
        features.append(packet.get('size', 0) / 1024.0)  # Normalizado

        # Inter packet gap (placeholder)
        features.append(0.0)

        # Source entropy (simple hash-based)
        src_hash = hash(packet.get('source', ''))
        features.append(src_hash / 10000.0)

        # Destination entropy
        dst_hash = hash(packet.get('destination', ''))
        features.append(dst_hash / 10000.0)

        # Protocol type (one-hot)
        protocol = packet.get('protocol', 'unknown').lower()
        if protocol == 'tcp':
            features.extend([1.0, 0.0, 0.0])
        elif protocol == 'udp':
            features.extend([0.0, 1.0, 0.0])
        elif protocol == 'icmp':
            features.extend([0.0, 0.0, 1.0])
        else:
            features.extend([0.0, 0.0, 0.0])

        # TTL
        features.append(packet.get('metadata', {}).get('ttl', 64) / 255.0)

        # Flag count
        flags = packet.get('metadata', {}).get('flags', '')
        flags_count = flags.count('F') + flags.count('S') + flags.count('R')
        features.append(flags_count / 4.0)

        # Payload length
        payload = packet.get('payload', b'')
        features.append(len(payload) / 1024.0)

        return np.array(features).reshape(1, -1)

    def predict(self, packet: Dict[str, Any]) -> float:
        """
        Predice si el paquete es anómalo.

        Args:
            packet: Paquete a analizar

        Returns:
            Probabilidad de anomalía (0-1)
        """
        if not self.model:
            # Fallback: simulación de inferencia
            return self._simulate_prediction(packet)

        try:
            features = self.extract_features(packet)
            prediction = self.model.predict(features)[0]
            probability = self.model.predict_proba(features)[0][1]  # Probabilidad de clase 1 (anomaly)

            return float(probability)

        except Exception as e:
            self.logger.warning(f"Error en inferencia: {e}")
            return self._simulate_prediction(packet)

    def _simulate_prediction(self, packet: Dict[str, Any]) -> float:
        """
        Simula predicción cuando el modelo no está disponible.

        Args:
            packet: Paquete a analizar

        Returns:
            Probabilidad de anomalía simulada
        """
        # Simular anomalías basadas en patrones
        source = packet.get('source', '')
        destination = packet.get('destination', '')
        protocol = packet.get('protocol', '').lower()

        # Detectar port scanning
        if protocol == 'tcp':
            src_hash = hash(source)
            if src_hash % 7 == 0:  # Patrón aleatorio
                return 0.85 + np.random.random() * 0.14

        # Detectar tráfico anómalo
        if len(source) > 15 or len(destination) > 15:
            return 0.60 + np.random.random() * 0.30

        # Tráfico normal
        return np.random.random() * 0.20

    def is_anomaly(self, packet: Dict[str, Any]) -> tuple:
        """
        Determina si el paquete es una anomalía.

        Args:
            packet: Paquete a analizar

        Returns:
            (is_anomaly, probability, confidence)
        """
        probability = self.predict(packet)
        confidence = min(1.0, max(0.0, probability))

        is_anomaly = confidence >= self.threshold

        return is_anomaly, confidence, probability


class FastInferencePipeline:
    """Pipeline de inferencia rápido en tiempo real"""

    def __init__(
        self,
        engine: InferenceEngine,
        window_size: int = 100,
        min_samples: int = 10
    ):
        """
        Inicializa el pipeline de inferencia.

        Args:
            engine: InferenceEngine
            window_size: Ventana de análisis
            min_samples: Muestras mínimas para entrenar
        """
        self.engine = engine
        self.window_size = window_size
        self.min_samples = min_samples

        self.window = []
        self.anomaly_count = 0
        self.total_packets = 0

        self.inference_callback: Optional[Callable] = None
        self.alert_callback: Optional[Callable] = None

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"FastInferencePipeline inicializado")

    def add_packet(self, packet: Dict[str, Any]):
        """
        Añade un paquete al pipeline.

        Args:
            packet: Paquete con metadata
        """
        self.total_packets += 1

        # Extraer features y predecir
        is_anomaly, confidence, probability = self.engine.is_anomaly(packet)

        # Agregar a la ventana
        packet_analysis = {
            "timestamp": time.time(),
            "packet": packet,
            "is_anomaly": is_anomaly,
            "confidence": confidence,
            "probability": probability
        }

        self.window.append(packet_analysis)

        # Mantener solo la ventana de tamaño
        if len(self.window) > self.window_size:
            self.window.pop(0)

        # Contar anomalías
        if is_anomaly:
            self.anomaly_count += 1

        # Callback de inferencia
        if self.inference_callback:
            self.inference_callback(packet_analysis)

        # Alertar anomalía crítica
        if is_anomaly and confidence >= 0.9:
            alert = {
                "timestamp": datetime.now().isoformat(),
                "packet_id": packet.get('metadata', {}).get('id', ''),
                "type": "CRITICAL_ANOMALY",
                "confidence": confidence,
                "probability": probability,
                "source": packet.get('source'),
                "destination": packet.get('destination'),
                "protocol": packet.get('protocol')
            }

            if self.alert_callback:
                self.alert_callback(alert)

            self.logger.warning(f"⚠️ Alerta: {alert['type']} ({confidence:.2f})")

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del pipeline"""
        return {
            "total_packets": self.total_packets,
            "anomaly_count": self.anomaly_count,
            "anomaly_rate": (self.anomaly_count / self.total_packets * 100) if self.total_packets > 0 else 0,
            "window_size": len(self.window),
            "window_anomalies": sum(1 for p in self.window if p['is_anomaly'])
        }

    def train_from_window(self):
        """Entrena el modelo con la ventana actual"""
        if len(self.window) < self.min_samples:
            self.logger.info(f"Ventana insuficiente: {len(self.window)} < {self.min_samples}")
            return

        self.logger.info(f"Entrenando modelo con {len(self.window)} muestras")
        # TODO: Implementar entrenamiento real
        self.logger.info("Modelo entrenado (simulación)")

    def get_anomaly_pattern(self) -> Optional[Dict[str, Any]]:
        """
        Detecta patrón de anomalías en la ventana.

        Returns:
            Patrón detectado o None
        """
        if not self.window:
            return None

        # Agrupar por fuente y destino
        from collections import defaultdict

        flows = defaultdict(list)
        for analysis in self.window:
            src = analysis['packet'].get('source', '')
            dst = analysis['packet'].get('destination', '')
            flows[(src, dst)].append(analysis)

        # Encontrar flujos sospechosos
        suspicious_flows = []
        for flow, analyses in flows.items():
            anomaly_count = sum(1 for a in analyses if a['is_anomaly'])
            if anomaly_count > len(analyses) * 0.3:
                suspicious_flows.append({
                    "source": flow[0],
                    "destination": flow[1],
                    "packet_count": len(analyses),
                    "anomaly_count": anomaly_count,
                    "rate": anomaly_count / len(analyses)
                })

        return suspicious_flows[:5]  # Top 5 flujos sospechosos


class FastInferenceCLI:
    """CLI para Fast Inference"""

    @staticmethod
    def run(args):
        """Ejecuta el pipeline de inferencia"""
        setup_logging(args.verbose)

        try:
            # Inicializar motor de inferencia
            engine = InferenceEngine(
                model_path=args.model,
                threshold=args.threshold
            )

            pipeline = FastInferencePipeline(
                engine=engine,
                window_size=args.window,
                min_samples=args.min_samples
            )

            print(f"🚀 Iniciando Fast Inference Pipeline")
            print(f"   Model: {args.model or 'Simulación'}")
            print(f"   Threshold: {args.threshold}")
            print(f"   Window size: {args.window}")
            print(f"   Presiona Ctrl+C para detener\n")

            # Simular captura de paquetes
            import random
            import time

            def generate_packet():
                """Genera paquetes simulados"""
                protocols = ['TCP', 'UDP', 'ICMP']
                sources = ['192.168.1.1', '10.0.0.1', '172.16.0.1', '10.0.0.5', '192.168.1.100']
                destinations = ['192.168.1.100', '10.0.0.100', '172.16.0.100', '8.8.8.8']

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
                        "flags": random.choice(['S', 'F', 'S+F', '']),
                        "protocol": random.choice(protocols).lower()
                    }
                }
                return packet

            # Callbacks
            def on_inference(packet_analysis):
                if args.verbose and packet_analysis['is_anomaly']:
                    print(f"  ⚠️  Anomalía detectada: {packet_analysis['confidence']:.2f} - "
                          f"{packet_analysis['packet']['source']} → "
                          f"{packet_analysis['packet']['destination']}")

            pipeline.inference_callback = on_inference

            # Ejecutar
            try:
                for i in range(args.duration):
                    packet = generate_packet()
                    pipeline.add_packet(packet)

                    stats = pipeline.get_stats()
                    print(f"\r📊 Stats: {stats['total_packets']} paquetes | "
                          f"Anomalías: {stats['anomaly_count']} | "
                          f"Rate: {stats['anomaly_rate']:.2f}%", end="")

                    time.sleep(0.1)

            except KeyboardInterrupt:
                print(f"\n\n✅ Pipeline detenido")

            # Mostrar resumen
            print(f"\n{'='*60}")
            print("Fast Inference - Resumen")
            print(f"{'='*60}")
            stats = pipeline.get_stats()
            print(f"📊 Paquetes procesados: {stats['total_packets']}")
            print(f"⚠️  Anomalías detectadas: {stats['anomaly_count']}")
            print(f"📈 Tasa de anomalías: {stats['anomaly_rate']:.2f}%")
            print(f"{'='*60}\n")

            # Detectar patrones
            pattern = pipeline.get_anomaly_pattern()
            if pattern:
                print(f"🔍 Patrones sospechosos detectados:\n")
                for p in pattern:
                    print(f"  • {p['source']} → {p['destination']}")
                    print(f"    {p['packet_count']} paquetes, {p['anomaly_count']} anomalías")
                    print(f"    Rate: {p['rate']:.2%}\n")

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
            logging.FileHandler(log_dir / "inference.log")
        ]
    )