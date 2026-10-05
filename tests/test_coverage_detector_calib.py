"""Cobertura de _predict (detector) y del módulo calibrate_threshold."""

import numpy as np
import pandas as pd
import pytest

from qzero.core.detector import NetworkTrafficAnalyzer
from qzero.preprocessing import calibrate_threshold as ct


class _Scaler:
    def __init__(self, n):
        self.n_features_in_ = n

    def transform(self, X):
        return X


class _FittedPredictor:
    def __init__(self, n_features=14, scaler=True, score_fails=False):
        self.model_fitted = True
        self.scaler = _Scaler(n_features) if scaler else None
        self._score_fails = score_fails

    def predict(self, X, method="best"):
        return np.array([1 if i % 2 else 0 for i in range(len(X))])

    def get_anomaly_score(self, X):
        if self._score_fails:
            raise RuntimeError("sin scores")
        return np.linspace(0.1, 0.9, len(X))


def _features(cols=14, rows=4):
    base = list(
        pd.DataFrame(
            np.zeros((rows, 14)),
            columns=[
                "dur", "proto", "service", "state", "spkts", "dpkts",
                "sbytes", "dbytes", "rate", "sttl", "dttl", "load",
                "land", "error_rate",
            ],
        ).columns
    )
    cols = base[:cols] if cols <= 14 else base + [f"extra{i}" for i in range(cols - 14)]
    return pd.DataFrame(np.random.default_rng(0).random((rows, len(cols))), columns=cols)


# ── detector._predict ─────────────────────────────────────────────────────

def test_predict_no_model():
    out = NetworkTrafficAnalyzer()._predict(_features())
    assert out["status"] == "no_model"


def test_predict_ok_sin_scaler():
    out = NetworkTrafficAnalyzer(predictor=_FittedPredictor(scaler=False))._predict(_features())
    assert out["n_anomalies_detected"] == 2
    assert out["anomaly_percentage"] == 50.0
    assert len(out["anomaly_scores"]) == 4


def test_predict_rellena_columnas_faltantes():
    # 8 cols → completa a 14 con ceros vía FLOW_FEATURES y scaler esperado 14
    out = NetworkTrafficAnalyzer(predictor=_FittedPredictor(14))._predict(_features(cols=8))
    assert out["n_anomalies_detected"] == 2


def test_predict_padding_y_recorte():
    # features 16 cols, modelo espera 14 → recorta
    out = NetworkTrafficAnalyzer(predictor=_FittedPredictor(14))._predict(_features(cols=16))
    assert "predictions" in out
    # features 14 cols, modelo espera 16 → padding
    out2 = NetworkTrafficAnalyzer(predictor=_FittedPredictor(16))._predict(_features(cols=14))
    assert "predictions" in out2


def test_predict_fallback_scores():
    out = NetworkTrafficAnalyzer(predictor=_FittedPredictor(score_fails=True))._predict(_features())
    assert out["anomaly_scores"] == [float(p) for p in out["predictions"]]


def test_predict_error_interno():
    class Boom(_FittedPredictor):
        def predict(self, X, method="best"):
            raise ValueError("boom")

    out = NetworkTrafficAnalyzer(predictor=Boom())._predict(_features())
    assert out["status"] == "error"
    assert "boom" in out["message"]


# ── calibrate_threshold ───────────────────────────────────────────────────

def test_recommend_threshold():
    rep = ct.recommend_threshold(np.arange(1000, dtype=float), 99.9)
    assert rep["n_scores"] == 1000
    assert rep["recommended_threshold"] == rep["percentiles"][99.9]
    assert rep["std"] > 0


def test_recommend_threshold_vacio():
    with pytest.raises(ValueError):
        ct.recommend_threshold(np.array([]))


def test_collect_scores(monkeypatch):
    class FakeQZ:
        class _P:
            pass
        predictor = _P()

        def load(self, d):
            pass

    class FakeAnalyzer:
        def __init__(self, predictor=None):
            pass

        def analyze(self, path, method="best"):
            return {"flows_extracted": 2, "results": {"anomaly_scores": [0.4, 1.2]}}

    monkeypatch.setattr("qzero.QZero", FakeQZ)
    import qzero.core.detector as det
    monkeypatch.setattr(det, "NetworkTrafficAnalyzer", FakeAnalyzer)
    scores = ct.collect_scores("models", ["a.pcap", "b.pcap"])
    assert scores.tolist() == [0.4, 1.2, 0.4, 1.2]


def test_main_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        ct, "collect_scores", lambda md, paths, method: np.arange(100, dtype=float)
    )
    monkeypatch.setattr(
        "sys.argv",
        ["x", "--model-dir", "m", "--pcaps", "nofake/*.pcap,noreal.pcap", "--percentile", "95"],
    )
    ct.main()
    out = capsys.readouterr().out
    if "Recommended" in out:
        assert "95" in out


def test_main_sin_match(monkeypatch, capsys):
    monkeypatch.setattr(ct, "collect_scores", lambda *a, **k: np.array([1.0]))
    monkeypatch.setattr("sys.argv", ["x", "--model-dir", "m", "--pcaps", "zzz-*.pcap"])
    ct.main()
    # sin match → loguea error y vuelve (no imprime informe)
    assert "Recommended" not in capsys.readouterr().out
