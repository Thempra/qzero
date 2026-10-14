"""Hito 2.6 — config por agente (umbral / whitelist) persistida en el hub."""

import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ.setdefault("QZERO_HUB_DB", _tmp)

from fastapi.testclient import TestClient  # noqa: E402

from qzero.api.app import app  # noqa: E402

client = TestClient(app)


def test_config_roundtrip_per_agent():
    # two fictional agents: DMZ raises whitelist, LAN keeps defaults
    r = client.put("/api/v1/agents/dmz-fw/config", json={
        "alert_threshold": 3.5, "whitelist_private": True})
    assert r.status_code == 200
    assert r.json()["alert_threshold"] == 3.5
    assert r.json()["whitelist_private"] == 1

    r = client.get("/api/v1/agents/dmz-fw/config")
    assert r.json()["alert_threshold"] == 3.5

    # other agent unaffected (per-agent, not global)
    assert client.get("/api/v1/agents/lan-sw/config").json() == {}


def test_heartbeat_returns_config_and_upsert_keeps_unset_fields():
    client.put("/api/v1/agents/dmz-keep/config",
               json={"alert_threshold": 4.9, "whitelist_private": True})
    client.put("/api/v1/agents/dmz-keep/config", json={"alert_threshold": 5.1})
    hb = client.post("/api/v1/agents/dmz-keep/heartbeat",
                     json={"agent_name": "dmz", "interface": "eth0"})
    assert hb.status_code == 200
    cfg = hb.json()["config"]
    # upsert with only threshold must NOT clobber whitelist set earlier
    assert cfg["alert_threshold"] == 5.1
    assert cfg["whitelist_private"] == 1


def test_agent_applies_remote_overrides():
    import json as _json
    from qzero.agent.agent import QZeroAgent, AgentConfig

    agent = QZeroAgent(AgentConfig(agent_id="t", hub_url=""))
    assert agent.config.alert_threshold == 4.2
    agent._apply_remote_config(_json.dumps(
        {"heartbeat": True, "config": {"alert_threshold": 5.5,
                                       "whitelist_private": 1}}).encode())
    assert agent.config.alert_threshold == 5.5
    assert agent.config.whitelist_private is True
    # empty/absent config leaves the agent untouched
    agent._apply_remote_config(b'{"heartbeat": true}')
    assert agent.config.alert_threshold == 5.5
