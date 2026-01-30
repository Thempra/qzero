"""
Real-time anomaly detection for QZero.

This module provides streaming detection capabilities for:
- NetFlow streams
- PCAP packet capture
- Log aggregation
- Security event feeds

Designed to run as a sidecar container for production deployment.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import time
import numpy as np

from src.preprocessing.data_loader import DataLoader
from src.preprocessing.feature_engineering import FeatureEngineer
from src.predictor import QZeroPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QZero-Detector")


class DetectionStream(Enum):
    """Types of detection streams."""
    NETFLOW = "netflow"
    PCAP = "pcap"
    LOGS = "logs"
    IDS = "ids"
    METRICS = "metrics"


@dataclass
class DetectionResult:
    """Detection result for a single data point."""
    timestamp: float
    is_anomaly: bool
    anomaly_score: float
    reconstruction_loss: Optional[float] = None
    model_used: str = "qivae"
    features: Optional[np.ndarray] = None
    source: str = "unknown"
    severity: str = "low"
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class StreamConfig:
    """Configuration for a detection stream."""
    stream_type: DetectionStream
    interval_seconds: float = 1.0
    max_buffer_size: int = 1000
    enable_qivae: bool = True
    enable_qsvm: bool = False
    enable_classical: bool = True
    batch_size: int = 32


class DetectionStreamHandler(ABC):
    """Abstract base class for detection stream handlers."""

    @abstractmethod
    async def generate_data(self) -> AsyncGenerator[Tuple[Dict, float], None]:
        """
        Generate data from the stream.

        Yields:
            Tuple of (data_point, timestamp)
        """
        pass

    @abstractmethod
    def get_config(self) -> StreamConfig:
        """Get stream configuration."""
        pass


class NetFlowHandler(DetectionStreamHandler):
    """Handler for NetFlow streams."""

    def __init__(self, netflow_path: Optional[Path] = None):
        """
        Initialize NetFlow handler.

        Args:
            netflow_path: Path to NetFlow file (for testing). If None, uses mock data.
        """
        self.netflow_path = netflow_path
        self.config = StreamConfig(
            stream_type=DetectionStream.NETFLOW,
            interval_seconds=0.1,
            batch_size=32
        )

    def get_config(self) -> StreamConfig:
        return self.config

    async def generate_data(self) -> AsyncGenerator[Tuple[Dict, float], None]:
        """Generate mock NetFlow data."""
        if self.netflow_path and self.netflow_path.exists():
            logger.info(f"Reading NetFlow file: {self.netflow_path}")
            with open(self.netflow_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        yield data, time.time()
        else:
            # Generate mock NetFlow data
            import random
            for _ in range(10000):
                data = {
                    "src_ip": f"192.168.1.{random.randint(1, 254)}",
                    "dst_ip": f"10.0.0.{random.randint(1, 254)}",
                    "src_port": random.randint(1, 65535),
                    "dst_port": random.randint(1, 65535),
                    "protocol": random.choice(["TCP", "UDP", "ICMP"]),
                    "bytes_sent": random.randint(64, 1500),
                    "bytes_recv": random.randint(64, 1500),
                    "packets_sent": random.randint(1, 20),
                    "packets_recv": random.randint(1, 20),
                    "duration": random.uniform(0.1, 60.0),
                    "flags": random.choice(["SYN", "ACK", "FIN", "RST", "PSH"]),
                }
                yield data, time.time()


class PCAPHandler(DetectionStreamHandler):
    """Handler for PCAP streams."""

    def __init__(self, pcap_path: Optional[Path] = None):
        """
        Initialize PCAP handler.

        Args:
            pcap_path: Path to PCAP file (for testing).
        """
        self.pcap_path = pcap_path
        self.config = StreamConfig(
            stream_type=DetectionStream.PCAP,
            interval_seconds=0.1,
            batch_size=64
        )

    def get_config(self) -> StreamConfig:
        return self.config

    async def generate_data(self) -> AsyncGenerator[Tuple[Dict, float], None]:
        """Generate mock PCAP data."""
        if self.pcap_path and self.pcap_path.exists():
            logger.info(f"Reading PCAP file: {self.pcap_path}")
            # In production, use pyshark or scapy to parse PCAP
            # For now, use mock data
            import random
            for _ in range(5000):
                data = {
                    "src_mac": f"00:1A:2B:3C:4D:5E",
                    "dst_mac": f"00:1A:2B:3C:4D:5F",
                    "src_ip": f"10.0.0.{random.randint(1, 100)}",
                    "dst_ip": f"172.16.0.{random.randint(1, 100)}",
                    "src_port": random.randint(1, 65535),
                    "dst_port": random.choice([80, 443, 22, 3389, 8080]),
                    "protocol": random.choice(["TCP", "UDP"]),
                    "payload_size": random.randint(64, 1500),
                    "packet_number": random.randint(1, 10000),
                }
                yield data, time.time()
        else:
            # Generate mock PCAP data
            import random
            for _ in range(5000):
                data = {
                    "src_mac": f"00:1A:2B:3C:4D:5E",
                    "dst_mac": f"00:1A:2B:3C:4D:5F",
                    "src_ip": f"10.0.0.{random.randint(1, 100)}",
                    "dst_ip": f"172.16.0.{random.randint(1, 100)}",
                    "src_port": random.randint(1, 65535),
                    "dst_port": random.choice([80, 443, 22, 3389, 8080]),
                    "protocol": random.choice(["TCP", "UDP"]),
                    "payload_size": random.randint(64, 1500),
                    "packet_number": random.randint(1, 10000),
                }
                yield data, time.time()


class LoggerHandler(DetectionStreamHandler):
    """Handler for log streams."""

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize log handler.

        Args:
            log_dir: Directory containing logs (for testing).
        """
        self.log_dir = log_dir
        self.config = StreamConfig(
            stream_type=DetectionStream.LOGS,
            interval_seconds=0.05,
            batch_size=64
        )

    def get_config(self) -> StreamConfig:
        return self.config

    async def generate_data(self) -> AsyncGenerator[Tuple[Dict, float], None]:
        """Generate mock log data."""
        if self.log_dir and self.log_dir.exists():
            # Read log files
            for log_file in self.log_dir.glob("*.log"):
                logger.info(f"Reading log file: {log_file}")
                with open(log_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = {"message": line.strip()}
                            yield data, time.time()
        else:
            # Generate mock log data
            import random
            import datetime
            for _ in range(8000):
                timestamp = datetime.datetime.now().isoformat()
                event_types = [
                    "login_success",
                    "login_failure",
                    "file_access",
                    "network_connection",
                    "process_start",
                    "process_exit",
                    "privilege_escalation",
                    "malicious_activity",
                ]
                data = {
                    "timestamp": timestamp,
                    "event_type": random.choice(event_types),
                    "source": random.choice(["server", "workstation", "router", "firewall"]),
                    "user": f"user_{random.randint(1, 100)}",
                }
                yield data, time.time()


class QZeroDetector:
    """
    Real-time anomaly detector for QZero.

    This class manages multiple detection streams and processes data in real-time.
    """

    def __init__(
        self,
        predictor: Optional[QZeroPredictor] = None,
        data_dir: Optional[Path] = None,
        n_qubits: int = 4,
        enable_qivae: bool = True,
        enable_qsvm: bool = False,
        enable_classical: bool = True,
    ):
        """
        Initialize QZero detector.

        Args:
            predictor: Optional pre-initialized predictor.
            data_dir: Path to data directory.
            n_qubits: Number of qubits for quantum models.
            enable_qivae: Whether to enable QI-VAE.
            enable_qsvm: Whether to enable QSVM.
            enable_classical: Whether to enable classical models.
        """
        self.predictor = predictor or QZeroPredictor(
            data_dir=data_dir,
            n_qubits=n_qubits,
            use_qivae=enable_qivae,
            use_qsvm=enable_qsvm,
            use_classical=enable_classical,
        )
        self.n_qubits = n_qubits
        self.stream_handlers: List[DetectionStreamHandler] = []
        self.current_results: List[DetectionResult] = []
        self.alerts = []
        self.running = False

    def add_stream_handler(self, handler: DetectionStreamHandler):
        """
        Add a stream handler.

        Args:
            handler: Stream handler to add.
        """
        self.stream_handlers.append(handler)

    async def process_stream(
        self,
        handler: DetectionStreamHandler,
        max_samples: int = 1000,
    ) -> List[DetectionResult]:
        """
        Process a detection stream.

        Args:
            handler: Stream handler to process.
            max_samples: Maximum number of samples to process.

        Returns:
            List of detection results.
        """
        config = handler.get_config()
        results = []
        samples_processed = 0

        logger.info(f"Starting stream processing: {config.stream_type.value}")

        async for data, timestamp in handler.generate_data():
            # Extract features from data
            features = self._extract_features(data)

            # Get anomaly score
            try:
                anomaly_score, reconstruction_loss, model_used = \
                    self.predictor.get_anomaly_score(features)
                is_anomaly = anomaly_score > self.predictor.get_threshold()
            except RuntimeError:
                # Fallback: use simple anomaly detector if models not trained
                anomaly_score = self._simple_anomaly_score(features)
                reconstruction_loss = None
                model_used = "heuristic"
                is_anomaly = anomaly_score > 0.7

            # Determine severity
            severity = self._determine_severity(anomaly_score)

            # Create detection result
            result = DetectionResult(
                timestamp=timestamp,
                is_anomaly=is_anomaly,
                anomaly_score=float(anomaly_score),
                reconstruction_loss=float(reconstruction_loss) if reconstruction_loss else None,
                model_used=model_used,
                features=features,
                source=config.stream_type.value,
                severity=severity,
                metadata={"data": data},
            )

            results.append(result)
            self.current_results.append(result)

            # Log high-severity anomalies
            if is_anomaly and severity == "critical":
                self._create_alert(result)

            samples_processed += 1
            if samples_processed >= max_samples:
                break

        logger.info(f"Stream processing complete: {samples_processed} samples")
        return results

    def _extract_features(self, data: Dict) -> np.ndarray:
        """
        Extract features from raw data.

        Args:
            data: Raw data dictionary.

        Returns:
            Feature array.
        """
        # This is a simplified feature extraction.
        # In production, this would be more sophisticated.
        feature_dict = {}

        # Common features for different stream types
        if "bytes_sent" in data:
            feature_dict["bytes_sent"] = data["bytes_sent"]
        if "bytes_recv" in data:
            feature_dict["bytes_recv"] = data["bytes_recv"]
        if "packets_sent" in data:
            feature_dict["packets_sent"] = data["packets_sent"]
        if "packets_recv" in data:
            feature_dict["packets_recv"] = data["packets_recv"]
        if "duration" in data:
            feature_dict["duration"] = data["duration"]
        if "payload_size" in data:
            feature_dict["payload_size"] = data["payload_size"]
        if "src_port" in data and "dst_port" in data:
            feature_dict["port_ratio"] = data["src_port"] / (data["dst_port"] + 1)

        # Handle log events
        if "event_type" in data:
            event_types = [
                "login_success", "login_failure", "file_access", "network_connection",
                "process_start", "process_exit", "privilege_escalation", "malicious_activity"
            ]
            feature_dict["event_type_encoded"] = event_types.index(data["event_type"]) / len(event_types)

        # Convert to numpy array
        feature_values = np.array([feature_dict.get(k, 0.0) for k in [
            "bytes_sent", "bytes_recv", "packets_sent", "packets_recv",
            "duration", "payload_size", "port_ratio", "event_type_encoded"
        ]])

        # Ensure correct shape and scale
        if feature_values.shape[0] < 8:
            feature_values = np.pad(feature_values, (0, 8 - feature_values.shape[0]))

        # Scale to [0, pi] for quantum
        if feature_values.max() > 0:
            feature_values = (feature_values / feature_values.max()) * np.pi

        return feature_values

    def _determine_severity(self, anomaly_score: float) -> str:
        """
        Determine anomaly severity based on score.

        Args:
            anomaly_score: Anomaly score from detector.

        Returns:
            Severity level.
        """
        if anomaly_score > 0.95:
            return "critical"
        elif anomaly_score > 0.85:
            return "high"
        elif anomaly_score > 0.7:
            return "medium"
        else:
            return "low"

    def _simple_anomaly_score(self, features: np.ndarray) -> float:
        """
        Simple heuristic-based anomaly scoring.
        
        Used as fallback when ML models are not trained.
        
        Args:
            features: Feature array from _extract_features.
            
        Returns:
            Anomaly score between 0 and 1.
        """
        score = 0.0
        
        # bytes_sent / bytes_recv ratio (index 0, 1)
        if features[1] > 0:
            byte_ratio = features[0] / features[1]
            if byte_ratio > 10:
                score += 0.3
            elif byte_ratio > 5:
                score += 0.15
        
        # Duration anomaly (index 4)
        duration = features[4] if len(features) > 4 else 0
        if duration > 2.5:  # scaled, so > 2.5 means very long
            score += 0.2
        elif duration > 1.5:
            score += 0.1
        
        # Port ratio anomaly (index 6)
        port_ratio = features[6] if len(features) > 6 else 0
        if port_ratio > 2.0:
            score += 0.15
        
        # Event type (index 7) - higher values = more suspicious
        event_score = features[7] if len(features) > 7 else 0
        if event_score > 2.0:  # privilege_escalation or malicious_activity
            score += 0.3
        elif event_score > 1.5:
            score += 0.15
        
        # Add some baseline
        score += 0.1
        
        return min(score, 1.0)

    def _create_alert(self, result: DetectionResult):
        """Create an alert for a critical anomaly."""
        alert = {
            "timestamp": result.timestamp,
            "severity": result.severity,
            "anomaly_score": result.anomaly_score,
            "source": result.source,
            "metadata": result.metadata,
        }
        self.alerts.append(alert)

        logger.warning(f"CRITICAL ALERT: {result.source} - Anomaly score: {result.anomaly_score:.2f}")

    def get_alerts(self) -> List[Dict]:
        """Get list of alerts."""
        return self.alerts

    def get_statistics(self) -> Dict[str, any]:
        """
        Get detection statistics.

        Returns:
            Dictionary with statistics.
        """
        if not self.current_results:
            return {}

        total = len(self.current_results)
        anomalies = sum(1 for r in self.current_results if r.is_anomaly)
        anomaly_scores = [r.anomaly_score for r in self.current_results]

        return {
            "total_samples": total,
            "anomalies_detected": anomalies,
            "anomaly_rate": anomalies / total if total > 0 else 0.0,
            "mean_anomaly_score": float(np.mean(anomaly_scores)) if anomaly_scores else 0.0,
            "max_anomaly_score": float(np.max(anomaly_scores)) if anomaly_scores else 0.0,
            "critical_alerts": len(self.alerts),
        }


async def run_detection_stream(
    stream_type: DetectionStream,
    stream_config: Optional[StreamConfig] = None,
    data_source: Optional[Path] = None,
    max_samples: int = 1000,
) -> List[DetectionResult]:
    """
    Convenience function to run detection on a stream type.

    Args:
        stream_type: Type of stream to process.
        stream_config: Optional stream configuration.
        data_source: Optional data source path.
        max_samples: Maximum samples to process.

    Returns:
        List of detection results.
    """
    # Create handler
    if stream_type == DetectionStream.NETFLOW:
        handler = NetFlowHandler(data_source)
    elif stream_type == DetectionStream.PCAP:
        handler = PCAPHandler(data_source)
    elif stream_type == DetectionStream.LOGS:
        handler = LoggerHandler(data_source)
    else:
        raise ValueError(f"Unsupported stream type: {stream_type}")

    # Create detector
    detector = QZeroDetector()
    detector.add_stream_handler(handler)

    # Process stream
    return await detector.process_stream(handler, max_samples)


if __name__ == "__main__":
    # Example usage
    import sys
    from pathlib import Path

    stream_type = DetectionStream.NETFLOW
    data_path = Path("/home/thempra/projects/qzero/data/raw/final(2).csv")

    if len(sys.argv) > 1:
        if sys.argv[1] == "netflow":
            stream_type = DetectionStream.NETFLOW
        elif sys.argv[1] == "pcap":
            stream_type = DetectionStream.PCAP
        elif sys.argv[1] == "logs":
            stream_type = DetectionStream.LOGS

    async def main():
        results = await run_detection_stream(stream_type, data_path)

        # Calculate statistics from results
        total_samples = len(results)
        anomalies_detected = sum(1 for r in results if r.is_anomaly)
        anomaly_rate = anomalies_detected / total_samples if total_samples > 0 else 0
        mean_score = sum(r.anomaly_score for r in results) / total_samples if total_samples > 0 else 0
        max_score = max((r.anomaly_score for r in results), default=0)
        critical_alerts = sum(1 for r in results if r.is_anomaly and r.anomaly_score >= 0.85)

        print("\n" + "="*50)
        print("Detection Statistics")
        print("="*50)
        print(f"Total samples: {total_samples}")
        print(f"Anomalies detected: {anomalies_detected}")
        print(f"Anomaly rate: {anomaly_rate:.2%}")
        print(f"Mean anomaly score: {mean_score:.3f}")
        print(f"Max anomaly score: {max_score:.3f}")
        print(f"Critical alerts: {critical_alerts}")
        print("="*50)

    # Run main
    import asyncio
    asyncio.run(main())