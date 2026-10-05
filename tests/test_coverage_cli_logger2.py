"""Cobertura extra: CLI monitor/agent + logger (markdown, rotador, telegram)."""

import json
import sys
import types

import pytest
from click.testing import CliRunner

from qzero.cli.main import cli
from qzero import logger as lg


@pytest.fixture()
def runner():
    return CliRunner()


class FakeQZ:
    def __init__(self, *a, **k):
        self.predictor = object()

    def load(self, d): pass
    def train(self, **k): return {"training_time": 0.1}


# ── CLI monitor ───────────────────────────────────────────────────────────

def test_monitor_sniff_loop(runner, monkeypatch, tmp_path):
    calls = {"n": 0}

    class FakePcap(list):
        pass

    def fake_sniff(iface=None, promisc=False, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return FakePcap([1, 2])  # primera vuelta: con paquetes
        raise KeyboardInterrupt

    def fake_wrpcap(path, pkts):
        tmp_path.joinpath("dump.pcap").write_bytes(b"d")

    scapy_all = types.ModuleType("scapy.all")
    scapy_all.sniff = fake_sniff
    scapy_all.wrpcap = fake_wrpcap
    scapy_mod = types.ModuleType("scapy")
    scapy_mod.all = scapy_all
    monkeypatch.setitem(sys.modules, "scapy", scapy_mod)
    monkeypatch.setitem(sys.modules, "scapy.all", scapy_all)

    import qzero.core.detector as det

    class FakeAnalyzer:
        def __init__(self, predictor=None): pass
        def analyze(self, path):
            return {"timestamp": "2026-09-25T00:00:00", "features_extracted": 2,
                    "results": {"n_anomalies_detected": 1, "anomaly_percentage": 50.0}}

    monkeypatch.setattr(det, "NetworkTrafficAnalyzer", FakeAnalyzer)
    monkeypatch.setattr("qzero.QZero", FakeQZ)

    res = runner.invoke(cli, ["monitor", "-i", "lo", "--interval", "1"])
    assert res.exit_code == 0
    assert "ALERT" in res.output


def test_monitor_scapy_missing(runner, monkeypatch):
    # forzar ImportError de scapy.all
    import builtins
    real_import = builtins.__import__

    def no_scapy(name, *a, **k):
        if name.startswith("scapy"):
            raise ImportError("no scapy")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_scapy)
    monkeypatch.setattr("qzero.QZero", FakeQZ)
    res = runner.invoke(cli, ["monitor", "-i", "lo"])
    assert res.exit_code == 1
    assert "Scapy" in res.output


# ── CLI agent ─────────────────────────────────────────────────────────────

def test_agent_builds_config_and_runs(runner, monkeypatch):
    captured = {}

    class FakeConfig:
        def __init__(self, **kw):
            captured.update(kw)
            for k, v in kw.items():
                setattr(self, k, v)

    class FakeAgent:
        def __init__(self, config): captured["config"] = config
        def run(self): captured["started"] = True
        def start(self): captured["started"] = True

    qzero_agent = types.ModuleType("qzero.agent")
    qzero_agent.QZeroAgent = FakeAgent
    qzero_agent.AgentConfig = FakeConfig
    monkeypatch.setitem(sys.modules, "qzero.agent", qzero_agent)

    res = runner.invoke(cli, ["agent", "-i", "eth9", "--hub-url", "http://h:1",
                              "--agent-id", "a1", "--no-qsvm", "--threshold", "3.5"])
    assert res.exit_code == 0, res.output
    assert captured["config"].agent_id == "a1"
    assert captured["config"].interface == "eth9"
    assert captured["started"] is True


# ── logger: formateo markdown ─────────────────────────────────────────────

def test_format_markdown_completo(tmp_path):
    l = lg.QZeroLogger(log_dir=str(tmp_path))
    out = l.format_result({
        "task": "analisis", "timestamp": "2026-01-01",
        "summary": {"flows": 10},
        "anomalies": [{"type": "ddos", "confidence": 0.9, "description": "x"}],
    }, format_type="markdown")
    assert "## analisis" in out and "ddos" in out


def test_format_markdown_error(tmp_path):
    l = lg.QZeroLogger(log_dir=str(tmp_path))
    out = l.format_result({"task": "t", "error": "roto"}, format_type="markdown")
    assert "roto" in out


def test_format_plain(tmp_path):
    l = lg.QZeroLogger(log_dir=str(tmp_path))
    assert l.format_result({"a": 1}, format_type="texto") == "{'a': 1}"


# ── logger: LogRotator ────────────────────────────────────────────────────

def test_log_rotator_by_age(tmp_path):
    import os, gzip, time
    ld = tmp_path / "logs"
    ld.mkdir()
    old = ld / "old.log"
    old.write_text("datos")
    gz = ld / "old.log.gz"
    with gzip.open(gz, "wb") as f:
        f.write(b"datos")
    os.remove(old)
    # creamos el .gz viejo y un .log viejo normal
    old.write_text("x")
    st = os.stat(old)
    os.utime(old, (st.st_atime - 40 * 86400, st.st_atime - 40 * 86400))
    r = lg.LogRotator(log_dir=ld, keep_days=30, max_size_mb=1)
    r.rotate()  # no debe reventar


def test_log_rotator_by_size(tmp_path):
    ld = tmp_path / "logs"
    ld.mkdir()
    big = ld / "big.log"
    big.write_bytes(b"x" * 2000)
    r = lg.LogRotator(log_dir=ld, max_size_mb=1)
    r.max_size_bytes = 1000
    r.rotate()
    assert big.with_suffix(".log.old").exists()


# ── logger: AlertManager notificaciones ──────────────────────────────────

def test_send_notification_imprime(tmp_path, capsys):
    am = lg.AlertManager(alerts_dir=str(tmp_path / "a"), log_file=str(tmp_path / "l.log"))
    al = am.create_alert("task", "critical", "boom", {"k": "v"})
    am._send_notification(al)
    out = capsys.readouterr().out
    assert "boom" in out


def test_send_telegram_alert_ok(tmp_path, monkeypatch, capsys):
    class Resp:
        status_code = 200
        text = ""

    posted = {}

    class FakeReq:
        @staticmethod
        def post(url, json=None, timeout=None):
            posted["url"] = url
            posted["json"] = json
            return Resp()

    monkeypatch.setitem(sys.modules, "requests", FakeReq)
    am = lg.AlertManager(alerts_dir=str(tmp_path / "a"), log_file=str(tmp_path / "l.log"))
    al = am.create_alert("t", "critical", "hola", {"a": 1})
    am.send_telegram_alert(al, "TOKEN", "42")
    assert "botTOKEN" in posted["url"]
    assert "hola" in posted["json"]["text"]
    assert "✅" in capsys.readouterr().out


def test_send_telegram_alert_error_http(tmp_path, monkeypatch, capsys):
    class Resp:
        status_code = 403
        text = "denied"

    class FakeReq:
        @staticmethod
        def post(url, json=None, timeout=None):
            return Resp()

    monkeypatch.setitem(sys.modules, "requests", FakeReq)
    am = lg.AlertManager(alerts_dir=str(tmp_path / "a"), log_file=str(tmp_path / "l.log"))
    al = am.create_alert("t", "critical", "x")
    am.send_telegram_alert(al, "T", "1")
    assert "❌" in capsys.readouterr().out


def test_send_telegram_alert_exception(tmp_path, monkeypatch, capsys):
    class FakeReq:
        @staticmethod
        def post(*a, **k):
            raise RuntimeError("red caida")

    monkeypatch.setitem(sys.modules, "requests", FakeReq)
    am = lg.AlertManager(alerts_dir=str(tmp_path / "a"), log_file=str(tmp_path / "l.log"))
    al = am.create_alert("t", "warn", "x")
    am.send_telegram_alert(al, "T", "1")
    assert "red caida" in capsys.readouterr().out
