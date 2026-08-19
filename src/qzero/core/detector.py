"""
Network traffic analyzer for QZero.
Extracts flow-level features from PCAP files and runs quantum anomaly detection.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class NetworkTrafficAnalyzer:
    """
    Analyzes network traffic using QZero quantum models.

    Extracts UGRansome-style FLOW features (not per-packet features) and
    detects anomalies. Flow-level features keep training and inference in the
    same feature space, which eliminates the out-of-distribution scoring that
    caused the false positive storm.

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

        logger.info(f"Analyzing PCAP: {pcap_file}")

        try:
            packets = rdpcap(pcap_file)
        except Exception as e:
            return {"status": "error", "message": f"Cannot read PCAP: {e}"}

        if len(packets) == 0:
            return {"status": "error", "message": "PCAP is empty or corrupt"}

        logger.info(f"  Packets read: {len(packets)}")

        features, flow_meta = self._extract_features(packets)
        if features is None or len(features) == 0:
            return {"status": "error", "message": "Could not extract features"}

        results = self._predict(features, method)
        # Attach flow metadata (src/dst/ports/proto/bytes) aligned to each score
        # so consumers (agent, postfilter) can reason per-flow instead of per-packet.
        results["flow_meta"] = flow_meta if flow_meta else []

        analysis_result = {
            "status": "success",
            "filename": Path(pcap_file).name,
            "total_packets": len(packets),
            "flows_extracted": len(features),
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
        max_packets: int = 100_000,
    ) -> tuple:
        """
        Extract FLOW features from Scapy packets using FlowExtractor.

        Args:
            packets: List of Scapy packets.
            max_packets: Maximum number of packets to process.

        Returns:
            (features_df, flow_meta) where features_df has the UGRansome flow
            features (one row per flow) and flow_meta is a list of dicts, one
            per flow, with 'src_ip','dst_ip','src_port','dst_port','proto',
            'packets' and byte counts — aligned with DataFrame row order.
            On failure returns (None, []).
        """
        try:
            from ..preprocessing.flow_extractor import FlowExtractor

            extractor = FlowExtractor()
            features, flow_ids = extractor.extract_flows_with_ids(packets[:max_packets])

            if features is None or len(features) == 0:
                return None, []

            flow_meta = [self._flow_meta(fid) for fid in flow_ids]
            # Merge the computed features into each flow dict so downstream
            # consumers (agent postfilter) can reason on bytes/packet counts.
            for i, meta in enumerate(flow_meta):
                if i < len(features):
                    meta.update(features.iloc[i].to_dict())
            return features, flow_meta

        except Exception as e:
            logger.error(f"Flow feature extraction error: {e}")
            return None, []

    @staticmethod
    def _flow_meta(fid) -> Dict:
        """Map a flow key (src, sport, dst, dport, proto) to an alertable dict."""
        src_ip, sport, dst_ip, dport, proto = fid
        return {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": sport,
            "dst_port": dport,
            "proto": proto,
        }

    def _predict(self, features: pd.DataFrame, method: str = "best") -> Dict:
        """
        Run anomaly detection on extracted flow features.

        Args:
            features: DataFrame with UGRansome flow features (14 columns).
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
            from ..preprocessing.flow_extractor import FLOW_FEATURES
            from ..preprocessing.feature_engineering import FeatureEngineer

            # Reindex to the exact training feature set (guaranteed order).
            for col in FLOW_FEATURES:
                if col not in features.columns:
                    features[col] = 0.0
            X = features[FLOW_FEATURES].values.astype(float)

            # No padding/trimming hacks anymore: the FeatureEngineer already
            # reduces to n_qubits via PCA, matching training exactly.
            if self.predictor.scaler is not None:
                expected = self.predictor.scaler.n_features_in_
                if X.shape[1] != expected:
                    logger.warning(
                        "Feature dim mismatch: got %d, model expects %d. "
                        "Re-train the model with the FlowExtractor first.",
                        X.shape[1],
                        expected,
                    )
                    if X.shape[1] < expected:
                        padding = np.zeros((X.shape[0], expected - X.shape[1]))
                        X = np.hstack([X, padding])
                    else:
                        X = X[:, :expected]
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
