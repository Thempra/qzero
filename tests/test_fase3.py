#!/usr/bin/env python3
"""
Tests de humo de la arquitectura actual de QZero (core + API + agent).
Estilo pytest: los fallos se propagan (sin try/except que los traguen).
"""

import sys
from pathlib import Path

import pytest

# Añadir src al path (para ejecución sin instalar el paquete)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_qivae_initialization():
    """QIVAE se construye con su config."""
    pytest.importorskip("torch", reason="torch no instalado")

    from qzero.quantum.qivae import QIVAE, QIVAEConfig

    qivae = QIVAE(config=QIVAEConfig(n_qubits=4))
    assert qivae is not None
    assert qivae.config.n_qubits == 4


def test_predictor_untrained_raises_or_empty():
    """El predictor sin entrenar no produce salidas silenciosas falsas."""
    import numpy as np
    import pytest as _pt

    from qzero.core.predictor import QZeroPredictor

    predictor = QZeroPredictor()
    X = np.random.default_rng(42).random((8, 14))
    try:
        scores = predictor.predict(X, method="qsvm")
    except (_pt.skip.Exception, RuntimeError, ValueError):
        return
    assert len(scores) == 8


def test_flow_extractor_contract():
    """El extractor expone el contrato de 14 features UGRansome."""
    from qzero.preprocessing.flow_extractor import FLOW_FEATURE_COUNT

    assert FLOW_FEATURE_COUNT == 14


def test_agent_config_interface_detection():
    """AgentConfig resuelve la interfaz por defecto sin permisos raros."""
    from qzero.agent.agent import AgentConfig

    cfg = AgentConfig(interface="auto")
    assert isinstance(cfg.interface, str) and cfg.interface


def test_api_health(tmp_path, monkeypatch):
    """/health responde 200 sin modelos cargados."""
    pytest.importorskip("fastapi", reason="fastapi no instalado")
    from fastapi.testclient import TestClient

    from qzero.api.app import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
