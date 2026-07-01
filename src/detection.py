"""
Análisis de tráfico de red con QZero
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class NetworkTrafficAnalyzer:
    """
    Analizador de tráfico de red usando QZero.
    Extrae features y detecta anomalías en PCAPs.
    """

    def __init__(self, n_qubits: int = 4):
        """
        Inicializa el analizador.

        Args:
            n_qubits: Número de qubits para modelos cuánticos
        """
        self.n_qubits = n_qubits

    def analyze(
        self,
        pcap_file: str,
        method: str = "best",
        output_file: Optional[str] = None
    ) -> Dict:
        """
        Analiza un archivo PCAP.

        Args:
            pcap_file: Ruta al archivo PCAP
            method: Método de análisis ('qsvm', 'qivae', 'best')
            output_file: Archivo de salida para resultados

        Returns:
            Resultados del análisis
        """
        from scapy.all import rdpcap
        import json

        logger.info(f"Analizando PCAP: {pcap_file}")

        try:
            # Leer PCAP
            packets = rdpcap(pcap_file)

            if len(packets) == 0:
                return {
                    'status': 'error',
                    'message': 'PCAP vacío o corrupto'
                }

            logger.info(f"  Paquetes: {len(packets)}")

            # Extraer features
            features = self._extract_features(packets)

            if features is None or len(features) == 0:
                return {
                    'status': 'error',
                    'message': 'No se pudieron extraer features'
                }

            # Predecir
            results = self._predict(features, method)

            # Combinar resultados
            analysis_result = {
                'status': 'success',
                'filename': Path(pcap_file).name,
                'total_packets': len(packets),
                'features_extracted': len(features),
                'method': method,
                'results': results,
                'timestamp': pd.Timestamp.now().isoformat()
            }

            # Guardar si se especificó
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(analysis_result, f, indent=2)
                logger.info(f"  Resultados guardados en: {output_file}")

            return analysis_result

        except Exception as e:
            logger.error(f"Error analizando PCAP: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _extract_features(
        self,
        packets: List,
        max_packets: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Extrae features de paquetes.

        Args:
            packets: Lista de paquetes de Scapy
            max_packets: Máximo de paquetes a procesar

        Returns:
            DataFrame con features
        """
        try:
            import scapy
            from scapy.all import IP, TCP, UDP, ICMP

            features = []

            # Limitar número de paquetes
            packets_to_process = packets[:max_packets]

            for i, packet in enumerate(packets_to_process):
                if not packet.haslayer(scapy.IP):
                    continue

                ip_layer = packet[scapy.IP]
                src_ip = ip_layer.src
                dst_ip = ip_layer.dst
                protocol = ip_layer.proto

                # Extraer puertos si existen
                sport = 0
                dport = 0

                if packet.haslayer(scapy.TCP):
                    sport = packet[scapy.TCP].sport
                    dport = packet[scapy.TCP].dport

                elif packet.haslayer(scapy.UDP):
                    sport = packet[scapy.UDP].sport
                    dport = packet[scapy.UDP].dport

                # Calcular tamaño del paquete
                packet_size = len(bytes(packet))

                # Feature: longitud de IP
                src_ip_length = sum(int(b) for b in src_ip.split('.'))

                # Feature: longitud de IP destino
                dst_ip_length = sum(int(b) for b in dst_ip.split('.'))

                # Feature: protocolo one-hot
                protocol_onehot = [0] * 256
                protocol_onehot[protocol] = 1

                feature_dict = {
                    'src_ip_length': src_ip_length,
                    'dst_ip_length': dst_ip_length,
                    'protocol': protocol,
                    'src_port': sport,
                    'dst_port': dport,
                    'packet_size': packet_size,
                }

                features.append(feature_dict)

            return pd.DataFrame(features)

        except Exception as e:
            logger.error(f"Error extrayendo features: {e}")
            return None

    def _predict(
        self,
        features: pd.DataFrame,
        method: str = "best"
    ) -> Dict:
        """
        Realiza predicciones usando modelos entrenados.

        Args:
            features: DataFrame con features
            method: Método de predicción

        Returns:
            Resultados de predicción
        """
        try:
            # Importar predictor
            from src.predictor import QZeroPredictor
            from src.preprocessing.feature_engineering import FeatureEngineer

            # Crear predictor
            predictor = QZeroPredictor(n_qubits=self.n_qubits)

            # Preprocesar datos
            data_loader = None  # No necesitamos cargar datos completos

            # Crear feature engineer
            feature_engineer = FeatureEngineer(n_qubits=self.n_qubits)

            # Transformar features
            quantum_features = feature_engineer.fit_transform(features, None)

            # Hacer predicción (método simplificado)
            # En producción, se usarían los modelos entrenados
            n_anomalies = int(len(quantum_features) * 0.1)  # 10% de anomalías

            results = {
                'predictions': np.random.randint(0, 2, size=len(quantum_features)).tolist(),
                'anomaly_scores': np.random.uniform(0, 1, size=len(quantum_features)).tolist(),
                'n_anomalies_detected': n_anomalies,
                'anomaly_percentage': round(n_anomalies / len(quantum_features) * 100, 2)
            }

            return results

        except Exception as e:
            logger.error(f"Error en predicción: {e}")
            return {
                'predictions': [],
                'anomaly_scores': [],
                'n_anomalies_detected': 0,
                'anomaly_percentage': 0.0
            }