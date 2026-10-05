#!/usr/bin/env python3
"""Cobertura de los bucles en vivo: MonitorService (loop, WS, capture) y
QZeroAgent.run (sniff stubbeado). Todo sin red ni interfaz real."""

import asyncio
import types

import pytest


# ── MonitorService ────────────────────────────────────────────────────────

class FakeWS:
    def __init__(self, fail=False):
        self.sent = []
        self._fail = fail

    async def accept(self):
        pass

    async def send_json(self, payload):
        if self._fail:
            raise RuntimeError("closed")
        self.sent.append(payload)


def _svc():
    from qzero.api.monitor import MonitorService

    s = MonitorService()
    s.configure(predictor=None, interface="lo", interval=0.01,
                promiscuous=False)
    return s


def test_ws_connect_broadcast_disconnect():
    svc = _svc()
    ws, bad = FakeWS(), FakeWS(fail=True)

    async def scenario():
        await svc.connect(ws)
        assert ws.sent and "stats" in ws.sent[0]
        await svc._broadcast({"x": 1})
        assert ws.sent[-1] == {"x": 1}
        await svc._send_to(bad, {"y": 2})  # lo descarta sin reventar
        svc.disconnect(ws)
        await svc._broadcast({"z": 3})   # ya no destinatarios vivos
    asyncio.run(scenario())
    assert ws not in svc._connections


def test_monitor_loop_runs_and_stops(monkeypatch):
    from scapy.all import IP, UDP, Ether

    pkt = Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=1, dport=2)
    svc = _svc()
    calls = {"n": 0}

    def fake_capture(timeout):
        calls["n"] += 1
        if calls["n"] >= 3:
            svc._running = False  # salida limpia por condición del while
        return [pkt]

    monkeypatch.setattr(svc, "_capture", fake_capture)
    svc._start_time = 0.0
    svc._running = True

    async def scenario():
        await asyncio.wait_for(svc._monitor_loop(), timeout=5)
    asyncio.run(scenario())
    # predictor=None -> analyze sale temprano; el loop debe al menos
    # haber completado iteraciones (uptime actualizado al final de cada
    # una) y terminar por la condición _running=False.
    assert calls["n"] >= 3
    assert svc.stats.uptime_seconds > 0


def test_monitor_loop_survives_capture_errors(monkeypatch):
    svc = _svc()

    def boom(timeout):
        raise OSError("no iface")

    monkeypatch.setattr(svc, "_capture", boom)

    async def scenario():
        svc._running = True
        svc._start_time = 0.0
        task = asyncio.create_task(svc._monitor_loop())
        await asyncio.sleep(0.05)
        svc.stop()
        await asyncio.wait_for(task, timeout=5)
    asyncio.run(scenario())


def test_capture_failure_returns_empty(monkeypatch):
    import scapy.all as scapy_all

    def bad_sniff(**kw):
        raise OSError("perm denied")

    monkeypatch.setattr(scapy_all, "sniff", bad_sniff)
    svc = _svc()
    assert svc._capture(0.01) == []


# ── QZeroAgent.run ────────────────────────────────────────────────────────

def _fake_scapy(monkeypatch, stop_after):
    import scapy.all as scapy_all

    calls = {"n": 0}

    def fake_sniff(**kw):
        calls["n"] += 1
        if calls["n"] >= stop_after:
            ag._running = False
        if calls["n"] == 2:  # una ventana con tráfico -> heartbeat
            from scapy.all import IP, UDP, Ether
            return [Ether() / IP(src="10.0.0.1", dst="10.0.0.2") / UDP(sport=1, dport=2)]
        return []

    monkeypatch.setattr(scapy_all, "sniff", fake_sniff)
    monkeypatch.setattr(scapy_all, "wrpcap", lambda *a, **k: None)
    return calls


class FakeResp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_agent_run_loop_and_heartbeat(monkeypatch, tmp_path):
    import urllib.request

    from qzero.agent.agent import AgentConfig, QZeroAgent

    cfg = AgentConfig(agent_id="T1", interface="lo", interval=0.01,
                      hub_url="http://127.0.0.1:1/",
                      model_dir=str(tmp_path / "m"))
    global ag
    ag = QZeroAgent(cfg)
    monkeypatch.setattr(QZeroAgent, "_ensure_models",
                        lambda self: None)
    calls = _fake_scapy(monkeypatch, stop_after=3)
    pushed = []
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda req, timeout=None: pushed.append(req.full_url) or FakeResp())

    ag.run(keep_running=True)
    assert calls["n"] >= 3
    assert any("/heartbeat" in u for u in pushed)


def test_agent_persist_and_ensure_models(monkeypatch, tmp_path):
    """_ensure_models entrena, persista y recarga desde model_dir."""
    from qzero import QZero
    from qzero.agent.agent import AgentConfig, QZeroAgent

    class DummyQZero:
        def __init__(self, **kw):
            self.predictor = "PRED"

        def train(self, n_samples=10):
            self.train_calls = getattr(self, "train_calls", 0) + 1

        def save(self, d):
            (tmp_path / "m" / "scaler.pkl").parent.mkdir(parents=True,
                                                          exist_ok=True)
            (tmp_path / "m" / "scaler.pkl").write_bytes(b"x")

        def load(self, d):
            pass

    monkeypatch.setattr("qzero.QZero", DummyQZero)
    cfg = AgentConfig(model_dir=str(tmp_path / "m"), interface="lo",
                      use_qsvm=False, use_qivae=False)
    a = QZeroAgent(cfg)
    a._ensure_models()
    assert a._predictor == "PRED"
    assert (tmp_path / "m" / "scaler.pkl").exists()
    assert a._analyzer is not None
    # segunda llamada es no-op
    a._ensure_models()
    assert a._predictor == "PRED"


def test_agent_persist_models_failure(monkeypatch, tmp_path):
    from qzero.agent.agent import AgentConfig, QZeroAgent

    class Boom:
        def save(self, d):
            raise RuntimeError("disk on fire")

    a = QZeroAgent(AgentConfig(model_dir=str(tmp_path / "z")))
    a._persist_models(Boom())  # loguea warning, no propaga


def test_agent_main_entry(monkeypatch):
    import sys

    from qzero.agent import agent as agmod

    monkeypatch.setattr(sys, "argv", ["agent", "--interface", "lo"])
    monkeypatch.setattr(agmod.QZeroAgent, "run",
                        lambda self, keep_running=True: None)
    agmod.main()
