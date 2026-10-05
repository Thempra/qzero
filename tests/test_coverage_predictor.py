#!/usr/bin/env python3
"""Cobertura de QZeroPredictor (save/load, predict, scores) y
ClassicalBaseline (run_all, tabla). Solo classical models: sin qiskit."""

import numpy as np
import pytest

from qzero.classical.baseline import (ClassicalBaseline, ModelResult,
                                      print_comparison_table,
                                      run_all_baselines)
from qzero.core.predictor import QZeroPredictor
from qzero.preprocessing.data_loader import generate_synthetic_data


@pytest.fixture(scope="module")
def small_data():
    X, y = generate_synthetic_data(n_samples=300)
    return X, y


@pytest.fixture()
def fitted_classical():
    p = QZeroPredictor(use_qsvm=False, use_qivae=False,
                       use_classical=True)
    p.train_all(n_samples=400, use_qsvm=False, use_qivae=False,
                classical_models=["random_forest"])
    return p


# ── Predictor ─────────────────────────────────────────────────────────────

def test_predict_best_falls_back_to_classical(fitted_classical):
    p = fitted_classical
    preds = p.predict(p.X_test, method="best")
    assert preds.shape[0] == p.X_test.shape[0]


def test_predict_ensemble_default(fitted_classical):
    p = fitted_classical
    preds = p.predict(p.X_test)
    assert set(np.unique(preds)) <= {0, 1}


def test_get_anomaly_score_unknown_method(fitted_classical):
    with pytest.raises(ValueError):
        fitted_classical.get_anomaly_score(fitted_classical.X_test,
                                           method="quantum")


def test_get_anomaly_score_untrained_raises():
    p = QZeroPredictor()
    with pytest.raises(RuntimeError):
        p.get_anomaly_score(np.zeros((2, 4)))


def test_get_threshold_default():
    assert QZeroPredictor().get_threshold() == 0.5


def test_save_and_load_roundtrip(fitted_classical, tmp_path):
    p = fitted_classical
    out = tmp_path / "models"
    p.save(out)
    p2 = QZeroPredictor(use_qsvm=False, use_qivae=False,
                        classical_models=["random_forest"])
    p2.load(out)
    assert p2.model_fitted is True
    preds = p2.predict(p.X_test, method="best")
    assert preds.shape[0] == p.X_test.shape[0]


def test_repr_fitted(fitted_classical):
    assert isinstance(repr(fitted_classical), str)
    assert "QZeroPredictor" in repr(fitted_classical)


def test_compare_models_fitted(fitted_classical):
    txt = fitted_classical.compare_models()
    assert "Comparison" in txt or "random_forest" in txt


# ── ClassicalBaseline ─────────────────────────────────────────────────────

def test_run_all_baselines_subset(small_data):
    X, y = small_data
    from sklearn.model_selection import train_test_split

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3,
                                          random_state=0)
    res = run_all_baselines(Xtr, ytr, Xte, yte,
                            models=["random_forest", "noexiste"])
    assert len(res) == 1  # el inexistente se omite sin reventar
    assert isinstance(res[0], ModelResult)


def test_print_comparison_table(capsys, small_data):
    X, y = small_data
    from sklearn.model_selection import train_test_split

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3,
                                          random_state=0)
    res = run_all_baselines(Xtr, ytr, Xte, yte, models=["svm_rbf"])
    print_comparison_table(res)
    out = capsys.readouterr().out
    assert "CLASSICAL BASELINE COMPARISON" in out


def test_modelresult_to_dict():
    r = ModelResult(name="m", accuracy=0.5, precision=0.4, recall=0.3,
                    f1=0.35, roc_auc=0.6, train_time=1.0,
                    inference_time=0.1,
                    confusion_matrix=np.array([[1, 0], [0, 1]]))
    d = r.to_dict()
    assert d["name"] == "m" and d["f1"] == 0.35


def test_baseline_predict_proba(fitted_classical):
    bl = list(fitted_classical.classical_models_dict.values())[0]
    proba = bl.predict_proba(fitted_classical.X_test[:10])
    assert proba.shape[0] == 10
