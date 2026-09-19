"""
QZero Hub — central alert aggregator.

Receives alerts pushed by distributed QZero agents, persists them to a local
SQLite database (stdlib only, no external deps), and exposes them for the
dashboard / API. This is what lets alerts from MANY servers be reflected in
one central place.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id      TEXT PRIMARY KEY,
    agent_name    TEXT,
    interface     TEXT,
    last_seen     TEXT,
    total_alerts  INTEGER DEFAULT 0,
    first_seen    TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id      TEXT,
    agent_name    TEXT,
    timestamp     TEXT,
    src           TEXT,
    dst           TEXT,
    protocol      INTEGER,
    src_port      INTEGER,
    dst_port      INTEGER,
    size          INTEGER,
    packets       INTEGER DEFAULT 0,
    detail        TEXT,
    anomaly_score REAL,
    severity      TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_sev ON alerts(severity);
"""

# Optional columns added after the table was first created (pre-migration hubs
# created the alerts table without these). Kept idempotent so existing volumes
# are upgraded in place instead of being dropped.
_SCHEMA_MIGRATIONS = [
    ("alerts", "packets", "INTEGER DEFAULT 0"),
    ("alerts", "detail", "TEXT"),
]


class HubStore:
    """Thread-safe SQLite-backed store for agents + their alerts."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = os.environ.get("QZERO_HUB_DB", "data/hub.db")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()  # reentrant: ingest -> _ensure_counts
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._migrate()
            self._conn.commit()
        # Incremental counters for summary(): the alerts table grew to ~1.9M
        # rows (the false-positive storm), so a COUNT(*) + GROUP BY per request
        # took 6-15s+ and blew the dashboard's timeout on every ingest-triggered
        # recompute. We seed the counters once (lazy), then update them
        # incrementally on each ingest — summary() is O(1) and never rescans.
        self._counts: Optional[dict] = None

    def _migrate(self) -> None:
        """Add any missing columns to existing tables (idempotent)."""
        for table, col, decl in _SCHEMA_MIGRATIONS:
            cols = {
                r["name"]
                for r in self._conn.execute(f"PRAGMA table_info({table})").fetchall()
            }
            if col not in cols:
                logger.info("Hub migration: adding column %s.%s %s", table, col, decl)
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    # ------------------------------------------------------------------
    # Summary counters (incremental, O(1))
    # ------------------------------------------------------------------

    def _ensure_counts(self) -> None:
        """Seed totals/severity counters from the DB (once, lazily)."""
        if self._counts is not None:
            return
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]
            by_sev = {
                r["severity"]: r["c"]
                for r in self._conn.execute(
                    "SELECT severity, COUNT(*) AS c FROM alerts GROUP BY severity"
                ).fetchall()
            }
        self._counts = {"total_alerts": total, "by_severity": by_sev}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _report_agent(self, agent_id, agent_name="", interface=""):
        now = datetime.now().isoformat()
        self._conn.execute(
            """
            INSERT INTO agents (agent_id, agent_name, interface, last_seen, total_alerts, first_seen)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(agent_id) DO UPDATE SET
                agent_name = COALESCE(NULLIF(excluded.agent_name, ''), agents.agent_name),
                interface   = COALESCE(NULLIF(excluded.interface, ''), agents.interface),
                last_seen   = excluded.last_seen
            """,
            (agent_id, agent_name, interface, now, now),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest_alert_batch(self, payload: Dict) -> Dict:
        """
        Accept a batch payload from an agent:
            {agent_id, agent_name, interface, timestamp, alerts: [...]}
        Returns summary counts.
        """
        agent_id = payload.get("agent_id", "unknown")
        agent_name = payload.get("agent_name", "")
        interface = payload.get("interface", "")
        alerts = payload.get("alerts", []) or []

        with self._lock:
            # Seed counters from the CURRENT DB state BEFORE inserting, so the
            # incremental adds below don't double-count the new rows.
            self._ensure_counts()
            self._report_agent(agent_id, agent_name, interface)
            n = 0
            for a in alerts:
                detail = a.get("detail")
                detail_json = None
                if detail is not None:
                    detail_json = detail if isinstance(detail, str) else json.dumps(detail)
                self._conn.execute(
                    """
                    INSERT INTO alerts
                        (agent_id, agent_name, timestamp, src, dst, protocol,
                         src_port, dst_port, size, packets, detail, anomaly_score, severity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        agent_id,
                        a.get("_agent_name", agent_name),
                        a.get("timestamp") or payload.get("timestamp"),
                        a.get("src", "?"),
                        a.get("dst", "?"),
                        a.get("protocol", 0),
                        a.get("src_port", 0),
                        a.get("dst_port", 0),
                        a.get("size", 0),
                        a.get("packets", 0),
                        detail_json,
                        a.get("anomaly_score", 0.0),
                        a.get("severity", "LOW"),
                    ),
                )
                n += 1
            # Update running total for agent
            self._conn.execute(
                "UPDATE agents SET total_alerts = total_alerts + ? WHERE agent_id = ?",
                (n, agent_id),
            )
            self._conn.commit()
            # Update incremental counters in O(1) — never rescan the table.
            self._ensure_counts()
            self._counts["total_alerts"] += n
            for a in alerts:
                sev = a.get("severity", "LOW")
                self._counts["by_severity"][sev] = self._counts["by_severity"].get(sev, 0) + 1

        logger.info("Hub ingested %d alert(s) from agent '%s'", n, agent_id)
        return {"received": n, "agent_id": agent_id}

    def heartbeat(self, agent_id: str, agent_name: str = "", interface: str = "") -> Dict:
        """
        Lightweight contact from an agent with NO alerts (keeps last_seen fresh).

        Agents are marked online by their last_seen. Before this endpoint, an
        agent only touched the hub when it had alerts to push; once false
        positives were suppressed the agent went silent and showed offline.
        Heartbeats solve that: the agent reports 'alive' periodically even when
        there is nothing to alert on.
        """
        with self._lock:
            self._report_agent(agent_id, agent_name, interface)
            # Only last_seen / agent presence changed; totals unchanged.
        return {"heartbeat": True, "agent_id": agent_id}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_agents(self) -> List[Dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM agents ORDER BY last_seen DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def list_alerts(
        self, limit: int = 100, severity: Optional[str] = None,
        agent_id: Optional[str] = None, since: Optional[str] = None,
    ) -> List[Dict]:
        sql = "SELECT * FROM alerts WHERE 1=1"
        params: list = []
        if severity:
            sql += " AND severity = ?"
            params.append(severity)
        if agent_id:
            sql += " AND agent_id = ?"
            params.append(agent_id)
        if since:
            sql += " AND timestamp >= ?"
            params.append(since)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        alerts = [dict(r) for r in rows]
        # Deserialize the detail JSON payload for API/dashboard consumers.
        for a in alerts:
            if a.get("detail"):
                try:
                    a["detail"] = json.loads(a["detail"])
                except (json.JSONDecodeError, TypeError):
                    pass
        return alerts

    def summary(self) -> Dict:
        # O(1): serve from incremental counters (seeded once, updated per
        # ingest). With ~1.9M alerts a COUNT+GROUP BY per request took 6-15s+
        # and blew the dashboard's 5s/15s timeout on every ingest. Never scan.
        self._ensure_counts()
        return {
            "total_alerts": self._counts["total_alerts"],
            "agents": self._count_agents(),
            "by_severity": self._counts["by_severity"],
        }

    def _count_agents(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) AS c FROM agents").fetchone()["c"]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# Global singleton
hub_store = HubStore()
