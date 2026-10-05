#!/usr/bin/env python3
"""Tests del CLI (click.testing.CliRunner) con QZero/uvicorn stubbeados:
verifican wiring de opciones y salidas sin entrenar modelos reales."""

import json

import pytest
from click.testing import CliRunner

from qzero.cli.main import cli


@pytest.fixture()
def runner():
    return CliRunner()


class FakeQZero:
    """Doble del facade QZero: registra llamadas, sin ML."""

    last = None

    def __init__(self, n_qubits=4, use_qsvm=True, use_qivae=True):
        self.n_qubits = n_qubits
        self.use_qsvm = use_qsvm
        self.use_qivae = use_qivae
        self.predictor = object()
        self.calls = []
        FakeQZero.last = self

    def train(self, n_samples=5000, use_real_data=False):
        self.calls.append(("train", n_samples, use_real_data))
        return {"training_time": 0.5}

    def load(self, d):
        self.calls.append(("load", d))

    def save(self, d):
        self.calls.append(("save", d))

    def analyze_traffic(self, pcap, method="best"):
        self.calls.append(("analyze", pcap, method))
        return {"status": "success", "features_extracted": 42,
                "results": {"n_anomalies_detected": 3,
                            "anomaly_percentage": 7.1}}


def test_help_lists_commands(runner):
    r = runner.invoke(cli, ["--help"])
    assert r.exit_code == 0
    for cmd in ("train", "analyze", "server", "monitor"):
        assert cmd in r.output


def test_train_flags_forwarded(runner, monkeypatch, tmp_path):
    monkeypatch.setattr("qzero.QZero", FakeQZero)
    r = runner.invoke(cli, ["train", "-n", "100", "--qubits", "2",
                            "--no-qsvm", "--save-dir", str(tmp_path)])
    assert r.exit_code == 0, r.output
    qz = FakeQZero.last
    assert qz.use_qsvm is False
    assert ("train", 100, False) in qz.calls
    assert ("save", str(tmp_path)) in qz.calls


def test_analyze_success_output(runner, monkeypatch, tmp_path):
    monkeypatch.setattr("qzero.QZero", FakeQZero)
    pcap = tmp_path / "x.pcap"
    pcap.write_bytes(b"\x00" * 8)
    out = tmp_path / "res.json"
    r = runner.invoke(cli, ["analyze", str(pcap), "--model-dir", "/absent-ok",
                            "-m", "qivae", "-o", str(out)])
    assert r.exit_code == 0, r.output
    assert "Anomalies found  : 3" in r.output
    assert json.loads(out.read_text())["features_extracted"] == 42


def test_analyze_failure_exits_1(runner, monkeypatch, tmp_path):
    class FailQ(FakeQZero):
        def analyze_traffic(self, pcap, method="best"):
            return {"status": "error", "message": "corrupt"}

    monkeypatch.setattr("qzero.QZero", FailQ)
    pcap = tmp_path / "x.pcap"
    pcap.write_bytes(b"\x00")
    r = runner.invoke(cli, ["analyze", str(pcap), "--model-dir", "m"])
    assert r.exit_code == 1
    assert "corrupt" in (r.output + (r.output_bytes.decode() or ""))


def test_analyze_requires_existing_file(runner, tmp_path):
    r = runner.invoke(cli, ["analyze", str(tmp_path / "nope.pcap")])
    assert r.exit_code != 0


def test_server_invokes_uvicorn(runner, monkeypatch):
    import types

    monkeypatch.setattr("qzero.QZero", FakeQZero)
    captured = {}

    def fake_run(app, host, port, reload):
        captured["args"] = (app, host, port)

    uv = types.ModuleType("uvicorn")
    uv.run = fake_run
    monkeypatch.setitem(__import__("sys").modules, "uvicorn", uv)
    import qzero.api.app as api
    monkeypatch.setattr(api, "_predictor", None, raising=False)

    r = runner.invoke(cli, ["server", "--host", "127.0.0.1", "--port", "9999"])
    assert r.exit_code == 0, r.output
    assert captured["args"] == ("qzero.api.app:app", "127.0.0.1", 9999)
