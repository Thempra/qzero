"""Hito 1 — operación confiable: retention, digest Telegram, liveness."""

import sqlite3
from datetime import datetime, timedelta

import pytest

from qzero.api.hub import HubStore
from qzero.api.maintenance import build_critical_digest, _parse_ts


@pytest.fixture()
def hub(tmp_path):
    store = HubStore(db_path=tmp_path / "hub.db")
    yield store
    store.close()


def _seed(store, days_old: int, severity="LOW", n=3, agent="a1"):
    ts = (datetime.now() - timedelta(days=days_old)).isoformat()
    store.ingest_alert_batch({
        "agent_id": agent, "agent_name": agent, "interface": "eth0",
        "timestamp": ts,
        "alerts": [
            {"src": "10.0.0.1", "dst": "10.0.0.2", "severity": severity,
             "timestamp": ts, "dst_port": 22, "protocol": 6}
            for _ in range(n)
        ],
    })


def test_retention_purges_old_keeps_recent(hub):
    _seed(hub, days_old=200, n=5)
    _seed(hub, days_old=1, n=2)
    deleted = hub.purge_old_alerts(retention_days=90)
    assert deleted == 5
    assert hub.summary()["total_alerts"] == 2


def test_retention_disabled_when_zero(hub):
    _seed(hub, days_old=9999, n=3)
    assert hub.purge_old_alerts(retention_days=0) == 0
    assert hub.summary()["total_alerts"] == 3


def test_counters_stay_truthful_after_purge(hub):
    _seed(hub, days_old=200, severity="CRITICAL", n=7)
    hub.purge_old_alerts(90)
    s = hub.summary()
    assert s["total_alerts"] == 0
    assert s["by_severity"].get("CRITICAL", 0) == 0


def test_pending_criticals_marks_only_after_notify(hub):
    _seed(hub, days_old=1, severity="CRITICAL", n=2)
    assert len(hub.pop_pending_criticals()) == 2
    # not yet acknowledged -> still pending
    assert len(hub.pop_pending_criticals()) == 2
    hub.mark_criticals_notified()
    assert hub.pop_pending_criticals() == []


def test_digest_lists_alerts_and_truncates():
    alerts = [{"agent_name": "nuke", "src": "1.2.3.4", "dst": "me",
               "dst_port": 22, "protocol": 6} for _ in range(13)]
    text = build_critical_digest(alerts)
    assert "13 alerta(s) CRITICAL" in text
    assert "y 3 más" in text


def test_offline_parse_ts_naive_is_local():
    # naive iso from hub must parse in local frame (not flip to UTC)
    naive = datetime.now().isoformat()
    dt = _parse_ts(naive)
    drift = abs((datetime.now(dt.tzinfo) - dt).total_seconds())
    assert drift < 5


def test_legacy_db_without_notified_column_upgrades(tmp_path):
    # Simulate a pre-migration hub.db (no packets/detail/notified_telegram)
    p = tmp_path / "hub.db"
    conn = sqlite3.connect(p)
    conn.executescript(
        "CREATE TABLE agents (agent_id TEXT PRIMARY KEY, agent_name TEXT,"
        " interface TEXT, last_seen TEXT, total_alerts INTEGER DEFAULT 0,"
        " first_seen TEXT);"
        "CREATE TABLE alerts (id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " agent_id TEXT, agent_name TEXT, timestamp TEXT, src TEXT,"
        " dst TEXT, protocol INTEGER, src_port INTEGER, dst_port INTEGER,"
        " size INTEGER, anomaly_score REAL, severity TEXT);"
    )
    conn.execute("INSERT INTO alerts (agent_id,timestamp,src,dst,severity)"
                 " VALUES ('a','t','s','d','CRITICAL')")
    conn.commit()
    conn.close()

    store = HubStore(db_path=p)
    assert len(store.pop_pending_criticals()) == 1  # column added by migration
    store.close()
