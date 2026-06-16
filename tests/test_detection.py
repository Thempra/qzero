"""
Tests for real-time detection module.
"""

import pytest
import asyncio
import sys
import numpy as np
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detection import (
    DetectionStream,
    DetectionResult,
    StreamConfig,
    NetFlowHandler,
    PCAPHandler,
    LoggerHandler,
    QZeroDetector,
    run_detection_stream,
)


class TestDetectionStream:
    """Tests for DetectionStream enum."""

    def test_stream_values(self):
        """Test that all stream types have correct values."""
        assert DetectionStream.NETFLOW.value == "netflow"
        assert DetectionStream.PCAP.value == "pcap"
        assert DetectionStream.LOGS.value == "logs"
        assert DetectionStream.IDS.value == "ids"
        assert DetectionStream.METRICS.value == "metrics"


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = DetectionResult(
            timestamp=1234567890.0,
            is_anomaly=True,
            anomaly_score=0.9,
            model_used="qivae",
            source="netflow",
        )

        assert result.timestamp == 1234567890.0
        assert result.is_anomaly is True
        assert result.anomaly_score == 0.9
        assert result.model_used == "qivae"
        assert result.source == "netflow"
        assert result.severity == "low"  # default
        assert result.reconstruction_loss is None

    def test_with_all_fields(self):
        """Test with all fields specified."""
        result = DetectionResult(
            timestamp=1234567890.0,
            is_anomaly=True,
            anomaly_score=0.95,
            reconstruction_loss=0.5,
            model_used="qivae",
            source="netflow",
            severity="critical",
        )

        assert result.reconstruction_loss == 0.5
        assert result.severity == "critical"


class TestStreamConfig:
    """Tests for StreamConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = StreamConfig(stream_type=DetectionStream.NETFLOW)

        assert config.stream_type == DetectionStream.NETFLOW
        assert config.interval_seconds == 1.0
        assert config.batch_size == 32
        assert config.enable_qivae is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = StreamConfig(
            stream_type=DetectionStream.PCAP,
            interval_seconds=0.5,
            batch_size=64,
            enable_qivae=False,
            enable_qsvm=True,
        )

        assert config.stream_type == DetectionStream.PCAP
        assert config.interval_seconds == 0.5
        assert config.batch_size == 64
        assert config.enable_qivae is False
        assert config.enable_qsvm is True


class TestNetFlowHandler:
    """Tests for NetFlowHandler."""

    def test_init(self):
        """Test initialization."""
        handler = NetFlowHandler()
        assert handler.netflow_path is None
        config = handler.get_config()
        assert config.stream_type == DetectionStream.NETFLOW

    def test_init_with_path(self, tmp_path):
        """Test initialization with path."""
        path = tmp_path / "test.nflow"
        handler = NetFlowHandler(path)
        assert handler.netflow_path == path

    @pytest.mark.asyncio
    async def test_generate_data(self):
        """Test data generation."""
        handler = NetFlowHandler()
        samples = []
        async for data, timestamp in handler.generate_data():
            samples.append(data)
            if len(samples) >= 3:
                break

        assert len(samples) == 3
        assert all("src_ip" in s and "dst_ip" in s for s in samples)


class TestPCAPHandler:
    """Tests for PCAPHandler."""

    def test_init(self):
        """Test initialization."""
        handler = PCAPHandler()
        assert handler.pcap_path is None
        config = handler.get_config()
        assert config.stream_type == DetectionStream.PCAP

    @pytest.mark.asyncio
    async def test_generate_data(self):
        """Test data generation."""
        handler = PCAPHandler()
        samples = []
        async for data, timestamp in handler.generate_data():
            samples.append(data)
            if len(samples) >= 3:
                break

        assert len(samples) == 3
        assert all("src_mac" in s and "dst_mac" in s for s in samples)


class TestLoggerHandler:
    """Tests for LoggerHandler."""

    def test_init(self):
        """Test initialization."""
        handler = LoggerHandler()
        assert handler.log_dir is None
        config = handler.get_config()
        assert config.stream_type == DetectionStream.LOGS

    @pytest.mark.asyncio
    async def test_generate_data(self):
        """Test data generation."""
        handler = LoggerHandler()
        samples = []
        async for data, timestamp in handler.generate_data():
            samples.append(data)
            if len(samples) >= 3:
                break

        assert len(samples) == 3
        assert all("event_type" in s for s in samples)


class TestQZeroDetector:
    """Tests for QZeroDetector."""

    def test_init(self):
        """Test initialization."""
        detector = QZeroDetector()
        assert detector.predictor is not None
        assert detector.n_qubits == 4
        assert detector.stream_handlers == []
        assert detector.current_results == []

    def test_add_stream_handler(self, tmp_path):
        """Test adding stream handler."""
        detector = QZeroDetector()
        handler = NetFlowHandler(tmp_path / "test.nflow")
        detector.add_stream_handler(handler)

        assert len(detector.stream_handlers) == 1
        assert detector.stream_handlers[0] == handler

    def test_get_statistics_empty(self):
        """Test statistics with no data."""
        detector = QZeroDetector()
        stats = detector.get_statistics()
        assert stats == {}

    def test_get_alerts_empty(self):
        """Test alerts with no anomalies."""
        detector = QZeroDetector()
        alerts = detector.get_alerts()
        assert alerts == []

    def test_extract_features(self):
        """Test feature extraction."""
        detector = QZeroDetector()
        data = {
            "bytes_sent": 1024,
            "bytes_recv": 512,
            "packets_sent": 10,
            "packets_recv": 5,
            "duration": 0.5,
            "src_port": 12345,
            "dst_port": 80,
            "event_type": "login_success",
        }

        features = detector._extract_features(data)

        assert isinstance(features, np.ndarray)
        assert features.shape == (8,)
        assert features[0] > 0  # bytes_sent

    def test_extract_features_incomplete(self):
        """Test feature extraction with incomplete data."""
        detector = QZeroDetector()
        data = {
            "bytes_sent": 1024,
        }

        features = detector._extract_features(data)

        assert isinstance(features, np.ndarray)
        assert features.shape == (8,)

    def test_determine_severity(self):
        """Test severity determination."""
        detector = QZeroDetector()
        
        assert detector._determine_severity(0.96) == "critical"
        assert detector._determine_severity(0.90) == "high"
        assert detector._determine_severity(0.75) == "medium"
        assert detector._determine_severity(0.50) == "low"

    def test_simple_anomaly_score(self):
        """Test simple anomaly scoring fallback."""
        detector = QZeroDetector()
        
        # Normal features
        normal_features = np.array([100, 100, 5, 5, 0.5, 64, 1.0, 0.0])
        normal_score = detector._simple_anomaly_score(normal_features)
        assert 0 <= normal_score <= 1
        
        # Anomalous features (high byte ratio)
        anomaly_features = np.array([1000, 10, 5, 5, 0.5, 64, 1.0, 0.0])
        anomaly_score = detector._simple_anomaly_score(anomaly_features)
        assert anomaly_score > normal_score

    @pytest.mark.asyncio
    async def test_process_stream_netflow(self):
        """Test processing NetFlow stream."""
        detector = QZeroDetector()
        handler = NetFlowHandler()
        detector.add_stream_handler(handler)

        results = await detector.process_stream(handler, max_samples=10)

        assert len(results) == 10
        assert len(detector.current_results) == 10

        # Check results
        for result in detector.current_results:
            assert result.timestamp > 0
            assert 0 <= result.anomaly_score <= 1
            assert result.source == "netflow"


class TestRunDetectionStream:
    """Tests for run_detection_stream convenience function."""

    @pytest.mark.asyncio
    async def test_run_netflow(self):
        """Test running NetFlow stream."""
        results = await run_detection_stream(DetectionStream.NETFLOW, max_samples=5)

        assert len(results) == 5
        assert all(isinstance(r, DetectionResult) for r in results)

    @pytest.mark.asyncio
    async def test_run_pcap(self):
        """Test running PCAP stream."""
        results = await run_detection_stream(DetectionStream.PCAP, max_samples=5)

        assert len(results) == 5
        assert all(isinstance(r, DetectionResult) for r in results)

    @pytest.mark.asyncio
    async def test_run_logs(self):
        """Test running logs stream."""
        results = await run_detection_stream(DetectionStream.LOGS, max_samples=5)

        assert len(results) == 5
        assert all(isinstance(r, DetectionResult) for r in results)

    @pytest.mark.asyncio
    async def test_run_unknown_stream(self):
        """Test running unknown stream type."""
        with pytest.raises(ValueError):
            await run_detection_stream(DetectionStream.IDS)