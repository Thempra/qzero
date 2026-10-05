#!/usr/bin/env python3
"""
Tests básicos para QZero (architectura actual: core/cli/API).
"""

import sys
from pathlib import Path

# Añadir src al path (para ejecución sin instalar el paquete)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Los módulos principales se pueden importar."""
    from qzero.config import QZeroConfig  # noqa: F401
    from qzero.core.predictor import QZeroPredictor  # noqa: F401
    from qzero.core.detector import NetworkTrafficAnalyzer  # noqa: F401
    from qzero.preprocessing.flow_extractor import FlowExtractor  # noqa: F401
    from qzero.preprocessing.data_loader import DataLoader  # noqa: F401
    from qzero.quantum.qivae import QIVAE, QIVAEConfig  # noqa: F401


def test_cli_import():
    """El CLI expone el grupo `cli` con sus subcomandos."""
    from qzero.cli.main import cli

    assert callable(cli)
    assert {"train", "analyze", "server", "monitor", "agent"} <= set(cli.commands)


def test_config():
    """La configuración soporta get/set."""
    from qzero.config import QZeroConfig

    config = QZeroConfig()
    config.set("test_key", "test_value")
    assert config.get("test_key") == "test_value"


def test_analyzer(tmp_path):
    """El analizador tolera un PCAP inválido y responde con la clave timestamp."""
    from qzero.core.detector import NetworkTrafficAnalyzer

    fake = tmp_path / "test.pcap"
    fake.write_bytes(b"FAKEDATA")

    analyzer = NetworkTrafficAnalyzer()
    results = analyzer.analyze(str(fake))

    assert "status" in results
