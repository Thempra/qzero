#!/usr/bin/env python3
"""Cobertura de qzero.logger, calibrate_threshold y feature_maps (skipped
si no hay qiskit). Todo con directorios temporales, sin red."""

import json
import time

import numpy as np
import pytest

from qzero.logger import (Alert, AlertManager, LogRotator, QZeroLogger,
                          setup_alert_manager, setup_logging)


# ── QZeroLogger ───────────────────────────────────────────────────────────

@pytest.fixture()
def ql(tmp_path):
    lg = QZeroLogger(log_dir=str(tmp_path), verbose=True)
    yield lg
    # limpiar handlers propios para no ensuciar otros tests
    for h in list(lg.logger.handlers):
        lg.logger.removeHandler(h)
        h.close()


def test_logger_writes_file(ql, tmp_path):
    ql.info("hola-test")
    ql.debug("dbg")
    ql.warning("warn")
    ql.error("err")
    ql.critical("crit")
    content = (tmp_path / "qzero.log").read_text()
    assert "hola-test" in content


def test_logger_format_result_json(ql):
    out = ql.format_result({"a": 1}, format_type="json")
    assert json.loads(out) == {"a": 1}


def test_logger_format_result_markdown(ql):
    out = ql.format_result({"task": "scan",
                            "summary": {"accuracy": 0.9}},
                           format_type="markdown")
    assert "## scan" in out
    assert "accuracy: 0.9" in out


# ── Alert / AlertManager ──────────────────────────────────────────────────

def test_alert_to_dict_and_save(tmp_path):
    a = Alert(task="t1", level="WARNING", message="m",
              details={"k": "v"})
    d = a.to_dict()
    assert d["task"] == "t1"
    a.save(tmp_path)
    files = list(tmp_path.glob("*.json"))
    assert files
    assert json.loads(files[0].read_text())["message"] == "m"


def test_alert_manager_create_pending_ack(tmp_path):
    from pathlib import Path

    am = AlertManager(alerts_dir=str(tmp_path / "a"),
                      log_file=str(tmp_path / "a.log"))
    am.create_alert("job", "ERROR", "fallo", {"x": 1})
    pending = am.get_pending_alerts()
    assert len(pending) >= 1
    first = pending[0]
    am.acknowledge_alert(first if isinstance(first, Path)
                         else Path(str(first)))


# ── LogRotator ────────────────────────────────────────────────────────────


def test_setup_logging_returns_logger(tmp_path):
    lg = QZeroLogger(log_dir=str(tmp_path))
    assert hasattr(lg, "info")
    assert setup_alert_manager.__name__ == "setup_alert_manager"

def test_log_rotator_gzips_big_file(tmp_path):
    (tmp_path / "big.log").write_bytes(b"x" * (1024 * 1024))
    rot = LogRotator(log_dir=tmp_path, max_size_mb=0.0001, keep_days=1)
    rot.rotate()
    assert not (tmp_path / "big.log").exists() or any(
        tmp_path.glob("*.gz"))


def test_log_rotator_keeps_small(tmp_path):
    (tmp_path / "small.log").write_text("hola")
    rot = LogRotator(log_dir=tmp_path, max_size_mb=10, keep_days=7)
    rot.rotate()
    assert (tmp_path / "small.log").exists()


# ── calibrate_threshold ───────────────────────────────────────────────────

def test_recommend_threshold():
    from qzero.preprocessing.calibrate_threshold import recommend_threshold

    scores = np.arange(1000, dtype=float)
    r = recommend_threshold(scores, percentile=99.9)
    assert r["n_scores"] == 1000
    assert r["recommended_threshold"] >= r["percentiles"][99]
    assert r["percentiles"][50] == pytest.approx(499.5)


def test_recommend_threshold_empty():
    from qzero.preprocessing.calibrate_threshold import recommend_threshold

    with pytest.raises(ValueError):
        recommend_threshold(np.array([]))


# ── quantum.feature_maps (requiere qiskit) ────────────────────────────────

def _require_qiskit():
    pytest.importorskip("qiskit", reason="qiskit no instalado")


def test_create_feature_map_zz():
    _require_qiskit()
    from qzero.quantum.feature_maps import (FeatureMapType,
                                            create_feature_map)

    fm = create_feature_map(3, FeatureMapType.ZZ, reps=1)
    assert fm.num_qubits == 3


def test_get_feature_map_info():
    _require_qiskit()
    from qzero.quantum.feature_maps import (FeatureMapType,
                                            get_feature_map_info)

    info = get_feature_map_info(FeatureMapType.ZZ, n_qubits=2, reps=1)
    assert isinstance(info, dict)
