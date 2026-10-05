#!/usr/bin/env python3
"""Última tanda de cobertura: _analyze_window del agente, métricas de
evaluación y DataGenerator/real-time del data_loader."""

import numpy as np
import pytest


# ── agente._analyze_window con analyzer fake ──────────────────────────────

class FakeAnalyzer:
    def __init__(self, scores, meta=None, predictions=None):
        self._r = {"results": {"anomaly_scores": scores,
                               "predictions": predictions or [],
                               "flow_meta": meta or []}}

    def analyze(self, path, method="best"):
        return self._r


def _agent(**kw):
    scapy = pytest.importorskip("scapy")
    from qzero.agent.agent import AgentConfig, QZeroAgent

    cfg = AgentConfig(hub_url="", **kw)
    return QZeroAgent(cfg)


def test_analyze_window_empty_scores():
    from scapy.all import wrpcap
    ag = _agent()
    ag._analyzer = FakeAnalyzer([])
    assert ag._analyze_window([], wrpcap) == []


def test_analyze_window_alert_and_suppress(tmp_path):
    from scapy.all import wrpcap

    ag = _agent(alert_threshold=4.0)
    meta = [
        {"src_ip": "10.0.0.5", "dst_ip": "93.184.216.34", "proto": 6,
         "src_port": 40000, "dst_port": 443},
        {"src_ip": "10.0.0.6", "dst_ip": "8.8.8.8", "proto": 17,
         "src_port": 50000, "dst_port": 53},  # DNS -> suprimido
        {"src_ip": "10.0.0.7", "dst_ip": "185.220.101.7", "proto": 6,
         "src_port": 31337, "dst_port": 4444},  # alerta real
    ]
    ag._analyzer = FakeAnalyzer([4.9, 4.8, 9.5], meta=meta)
    alerts = ag._analyze_window([], wrpcap)
    srcs = {a["src"] for a in alerts}
    # HTTPS 443 benigno y DNS se suprimen; el flujo 31337->4444 alerta
    assert "10.0.0.5" not in srcs
    assert "10.0.0.6" not in srcs
    assert srcs == {"10.0.0.7"}


def test_analyze_window_error_returns_empty():
    class Boom:
        def analyze(self, *a, **k):
            raise RuntimeError("kaput")

    from scapy.all import wrpcap
    ag = _agent()
    ag._analyzer = Boom()
    assert ag._analyze_window([], wrpcap) == []


def test_analyze_window_no_analyzer():
    ag = _agent()
    ag._analyzer = None
    assert ag._analyze_window([], None) == []


# ── evaluation.metrics ────────────────────────────────────────────────────

def test_evaluate_with_proba_and_report(capsys):
    from qzero.evaluation.metrics import (evaluate_model,
                                          print_evaluation_report)

    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 60)
    score = rng.random(60)
    yhat = (score > 0.5).astype(int)
    res = evaluate_model(y, yhat, y_proba=score)
    print_evaluation_report(res, model_name="TESTMODEL")
    out = capsys.readouterr().out
    assert "TESTMODEL" in out


def test_evaluate_zero_day_detection():
    from qzero.evaluation.metrics import evaluate_zero_day_detection

    rng = np.random.default_rng(1)
    y = np.r_[np.zeros(50, int), np.ones(20, int)]
    score = rng.random(70)
    yhat = (score > 0.55).astype(int)
    yhat[50:] |= 1  # los "zero-day" detectados
    res = evaluate_zero_day_detection(y, yhat)
    assert isinstance(res, dict) and res


def test_quantum_advantage_positive():
    from qzero.evaluation.metrics import calculate_quantum_advantage

    adv = calculate_quantum_advantage({"accuracy": 0.99},
                                      {"accuracy": 0.90})
    assert isinstance(adv, dict) and adv


# ── data_loader extra ─────────────────────────────────────────────────────

def test_dataloader_prepare_with_val(tmp_path):
    from qzero.preprocessing.data_loader import (DataLoader,
                                                 generate_synthetic_data)

    X, y = generate_synthetic_data(n_samples=400)
    d = DataLoader()
    prep = d.prepare_data(X, y, binary=True, test_size=0.2, val_size=0.1)
    assert {"X_train", "X_val", "X_test"} <= set(prep)
    n = len(X)
    assert len(prep["X_train"]) + len(prep["X_val"]) + \
        len(prep["X_test"]) == n


def test_generate_synthetic_balance():
    from qzero.preprocessing.data_loader import generate_synthetic_data

    X, y = generate_synthetic_data(n_samples=200)
    assert len(X) == len(y) == 200
    # etiquetas multi-clase: 0 normal, 1 zero-day, 2 ataque conocido
    assert set(np.unique(y)) <= {0, 1, 2}
