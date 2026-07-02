"""
Network traffic analyzer for QZero.
Extracts features from PCAP files and runs quantum anomaly detection.
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class NetworkTrafficAnalyzer:
    """
    Analyzes network traffic using QZero quantum models.
    Extracts features from PCAP files and detects anomalies.

    Usage:
        predictor = QZeroPredictor(...)
        predictor.train_all()

        analyzer = NetworkTrafficAnalyzer(predictor=predictor)
        result = analyzer.analyze("traffic.pcap")
    """

    def __init__(self, predictor=None, n_qubits: int = 4):
        """
        Initialize the analyzer.

        Args:
            predictor: Trained QZeroPredictor instance. Required for predictions.
            n_qubits: Number of qubits (used when building a fresh FeatureEngineer).
        """
        self.predictor = predictor
        self.n_qubits = n_qubits

    def analyze(
        self,
        pcap_file: str,
        method: str = "best",
        output_file: Optional[str] = None,
    ) -> Dict:
        """
        Analyze a PCAP file for anomalous traffic.

        Args:
            pcap_file: Path to the PCAP file.
            method: Detection method ('qsvm', 'qivae', 'best').
            output_file: Optional path to save JSON results.

        Returns:
            Analysis result dictionary.
        """
        from scapy.all import rdpcap
        import json

        logger.info(f"Analyzing PCAP: {pcap_file}")

        try:
            packets = rdpcap(pcap_file)
        except Exception as e:
            return {"status": "error", "message": f"Cannot read PCAP: {e}"}

        if len(packets) == 0:
            return {"status": "error", "message": "PCAP is empty or corrupt"}

        logger.info(f"  Packets read: {len(packets)}")

        features = self._extract_features(packets)
        if features is None or len(features) == 0:
            return {"status": "error", "message": "Could not extract features"}

        results = self._predict(features, method)

        analysis_result = {
            "status": "success",
            "filename": Path(pcap_file).name,
            "total_packets": len(packets),
            "features_extracted": len(features),
            "method": method,
            "results": results,
            "timestamp": pd.Timestamp.now().isoformat(),
        }

        if output_file:
            with open(output_file, "w") as f:
                json.dump(analysis_result, f, indent=2)
            logger.info(f"  Results saved to: {output_file}")

        return analysis_result

    def _extract_features(
        self,
        packets: List,
        max_packets: int = 1000,
    ) -> Optional[pd.DataFrame]:
        """
        Extract numerical features from Scapy packets.

        Args:
            packets: List of Scapy packets.
            max_packets: Maximum number of packets to process.

        Returns:
            DataFrame with per-packet features, or None on failure.
        """
        try:
            import scapy
            from scapy.all import IP, TCP, UDP

            features = []
            for packet in packets[:max_packets]:
                if not packet.haslayer(IP):
                    continue

                ip = packet[IP]
                sport = dport = 0

                if packet.haslayer(TCP):
                    sport = packet[TCP].sport
                    dport = packet[TCP].dport
                elif packet.haslayer(UDP):
                    sport = packet[UDP].sport
                    dport = packet[UDP].dport

                src_ip_sum = sum(int(b) for b in ip.src.split("."))
                dst_ip_sum = sum(int(b) for b in ip.dst.split("."))

                features.append(
                    {
                        "src_ip_sum": src_ip_sum,
                        "dst_ip_sum": dst_ip_sum,
                        "protocol": ip.proto,
                        "src_port": sport,
                        "dst_port": dport,
                        "packet_size": len(bytes(packet)),
                    }
                )

            if not features:
                return None

            return pd.DataFrame(features)

        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None

    def _predict(self, features: pd.DataFrame, method: str = "best") -> Dict:
        """
        Run anomaly detection on extracted features.

        Args:
            features: DataFrame with per-packet features.
            method: 'qsvm', 'qivae', or 'best'.

        Returns:
            Prediction result dictionary.
        """
        if self.predictor is None or not self.predictor.model_fitted:
            return {
                "status": "no_model",
                "message": (
                    "No trained predictor available. "
                    "Pass a fitted QZeroPredictor to NetworkTrafficAnalyzer."
                ),
                "predictions": [],
                "anomaly_scores": [],
                "n_anomalies_detected": 0,
                "anomaly_percentage": 0.0,
            }

        try:
            from ..preprocessing.feature_engineering import FeatureEngineer

            X = features.values.astype(float)

            # Scale with the predictor's fitted scaler, then reduce dims for quantum
            if self.predictor.scaler is not None:
                # Pad or trim columns to match training data dimensionality
                n_train_features = self.predictor.scaler.n_features_in_
                if X.shape[1] < n_train_features:
                    padding = np.zeros((X.shape[0], n_train_features - X.shape[1]))
                    X = np.hstack([X, padding])
                elif X.shape[1] > n_train_features:
                    X = X[:, :n_train_features]
                X = self.predictor.scaler.transform(X)

            predictions = self.predictor.predict(X, method=method)
            n_anomalies = int(predictions.sum())

            # Get anomaly scores when possible
            try:
                scores = self.predictor.get_anomaly_score(X).tolist()
            except Exception:
                scores = predictions.astype(float).tolist()

            return {
                "predictions": predictions.tolist(),
                "anomaly_scores": scores,
                "n_anomalies_detected": n_anomalies,
                "anomaly_percentage": round(
                    n_anomalies / len(predictions) * 100, 2
                ),
            }

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "predictions": [],
                "anomaly_scores": [],
                "n_anomalies_detected": 0,
                "anomaly_percentage": 0.0,
            }
