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
import math
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
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
-- Fase 1.1: aggregation by 5-tuple over a time window.
--   idx_alerts_flow_window is COVERING for the GROUP BY query: the range on
--   timestamp narrows to the window and every projected column (5-tuple,
--   severity, anomaly_score) is inside the index, so SQLite never touches the
--   alerts table. Without it the same query is a full table scan + temp b-tree.
--   idx_alerts_flow_score is the per-flow access path used to compute the
--   score percentiles (equality on the 4 tuple columns, range on timestamp,
--   anomaly_score covered). Sus columnas de puerto/protocolo usan la MISMA
--   expresión COALESCE(x,0) que las consultas de percentil: con columnas
--   desnudas el planner no puede usar el índice para esos dos términos y el
--   COUNT pasaba de 0,2 ms a 2,6 ms por flujo (×limit=200 -> +350 ms en la
--   petición). El índice por expresión además conserva la semántica: una
--   alerta con dst_port NULL cae en el flujo ",0" igual que en la agregación.
CREATE INDEX IF NOT EXISTS idx_alerts_flow_window
    ON alerts(timestamp, src, dst, dst_port, protocol, severity, anomaly_score);
CREATE INDEX IF NOT EXISTS idx_alerts_flow_score
    ON alerts(src, dst, COALESCE(dst_port, 0), COALESCE(protocol, 0),
              timestamp, anomaly_score);
-- Fase 1.2: analyst triage state per flow (5-tuple). Survives alert purges on
-- purpose: a flow marked 'benigno' must stay benigno after retention deletes
-- the underlying alerts.
CREATE TABLE IF NOT EXISTS flow_state (
    flow_key    TEXT PRIMARY KEY,       -- 'src,dst,dst_port,protocol'
    state       TEXT NOT NULL,          -- 'nuevo'|'investigando'|'benigno'|'malicioso'
    note        TEXT,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_config (
    agent_id        TEXT PRIMARY KEY,
    alert_threshold REAL,               -- per-agent override (Hito 1/6)
    whitelist_private INTEGER,          -- 0/1; DMZ agents may differ from LAN
    updated_at      TEXT
);
CREATE TABLE IF NOT EXISTS ip_intel (
    ip          TEXT PRIMARY KEY,
    org         TEXT,
    asn         TEXT,
    country     TEXT,
    anycast     INTEGER DEFAULT 0,
    fetched_at  TEXT                    -- ISO8601; stale rows re-fetched (Hito 3.8)
);
"""

# Optional columns added after the table was first created (pre-migration hubs
# created the alerts table without these). Kept idempotent so existing volumes
# are upgraded in place instead of being dropped.
_SCHEMA_MIGRATIONS = [
    ("alerts", "packets", "INTEGER DEFAULT 0"),
    ("alerts", "detail", "TEXT"),
    ("alerts", "notified_telegram", "INTEGER DEFAULT 0"),
]

# ── Fase 1.1 / 1.2: flujos agregados ───────────────────────────────────────
# El analista no puede triar 8.473 alertas/hora una a una. Un "flujo" es la
# 5-tupla (src, dst, dst_port, protocol) — src_port se excluye a propósito:
# efímero, multiplicaría las filas sin añadir información de triaje.
FLOW_STATES = ("nuevo", "investigando", "benigno", "malicioso")
# Estados que significan "ya triado" (only_untriaged los excluye). 'nuevo'
# existe para poder devolver un flujo a la cola, no para marcarlo como visto.
TRIAGED_STATES = ("investigando", "benigno", "malicioso")
FLOWS_DEFAULT_MINUTES = 60
FLOWS_MAX_MINUTES = 1440
FLOWS_DEFAULT_LIMIT = 50
FLOWS_MAX_LIMIT = 200

# Rank numérico de severidad, para MAX() dentro del GROUP BY.
_SEV_RANK_SQL = (
    "MAX(CASE UPPER(COALESCE(severity, '')) "
    "WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3 "
    "WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 1 ELSE 0 END)"
)
_SEV_BY_RANK = {4: "CRITICAL", 3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "UNKNOWN"}


def flow_key(src: str, dst: str, dst_port, protocol) -> str:
    """Clave estable de un flujo: ``"src,dst,dst_port,protocol"``.

    Misma cadena para la misma 5-tupla venga de SQLite (ints) o de JSON
    (strings), y para NULL (que el esquema histórico permite) que se normaliza
    a 0 igual que en la expresión SQL de ``aggregate_flows``. La coma es el
    separador y no aparece en IPv4 ni en IPv6 textual, así que la clave es
    unívoca.
    """
    def _canon_int(value):
        if value is None or value == "":
            return "0"
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value)

    return "{},{},{},{}".format(
        src, dst, _canon_int(dst_port), _canon_int(protocol)
    )


# Expresión SQL equivalente a flow_key() sobre una fila de ``alerts``. Se usa
# en el LEFT JOIN contra flow_state: si se desalineara con flow_key(), un flujo
# marcado como benigno volvería a aparecer en la cola de triaje.
_FLOW_KEY_SQL = (
    "({src} || ',' || {dst} || ',' || COALESCE({dst_port}, 0)"
    " || ',' || COALESCE({protocol}, 0))"
)


def _flow_key_sql(alias: str = "") -> str:
    p = f"{alias}." if alias else ""
    return _FLOW_KEY_SQL.format(src=f"{p}src", dst=f"{p}dst",
                                dst_port=f"{p}dst_port",
                                protocol=f"{p}protocol")


# Acceso al índice por ventana temporal. Medido en el banco de 1,7 M alertas
# (docs/research/impl-flows.md): sin la pista el planificador elige
# idx_alerts_flow_score (su GROUP BY no necesita b-tree temporal) y hace
# "SCAN a USING INDEX idx_alerts_flow_score" sobre el índice ENTERO, incluidas
# las filas fuera de la ventana: mediana 411 ms frente a 44 ms con
# idx_alerts_flow_window, que acota por timestamp y es covering para esta
# consulta ("SEARCH a USING COVERING INDEX ... (timestamp>?)").
_FLOW_INDEX_HINT = "INDEXED BY idx_alerts_flow_window"


def build_flows_query(only_untriaged: bool = False) -> tuple:
    """Devuelve (sql, params) de la agregación por 5-tupla.

    Forma: AGREGAR PRIMERO, cruzar con flow_state DESPUÉS. El LEFT JOIN contra
    ``flow_state`` va sobre el resultado ya agrupado (~400 filas), no sobre las
    alertas de la ventana (hasta 203 k en 24 h). Con el join dentro del scan el
    concatenado de la 5-tupla se evalúa una vez por alerta y la consulta pasaba
    de ~590 ms a ~910 ms en la ventana de 1440 min (medido).

    ``total_flows`` sale de ``COUNT(*) OVER ()``: es el número de grupos tras
    el filtro y antes del LIMIT, así que no hace falta un segundo recorrido de
    la ventana (el COUNT aparte costaba 335 ms más en 1440 min).

    ``params`` son los placeholders de ``sql`` salvo ``since`` y ``limit``:
    el llamante los sustituye (posición 0) y añade el límite al final.
    Existe como función de módulo para que el banco de pruebas y
    ``EXPLAIN QUERY PLAN`` midan EXACTAMENTE la consulta de producción y no
    una copia que se desincronice.
    """
    filter_sql = ""
    if only_untriaged:
        marks = ",".join("?" * len(TRIAGED_STATES))
        filter_sql = f" AND COALESCE(fs.state, 'nuevo') NOT IN ({marks})"

    sql = (
        "SELECT g.src AS src, g.dst AS dst, g.dst_port AS dst_port, "
        "       g.protocol AS protocol, "
        f"      {_flow_key_sql('g')} AS flow_key, "
        "       g.count AS count, g.first_seen AS first_seen, "
        "       g.last_seen AS last_seen, g.score_max AS score_max, "
        "       g.sev_rank AS sev_rank, "
        "       COUNT(*) OVER () AS total_flows, "
        "       COALESCE(fs.state, 'nuevo') AS state, fs.note AS note "
        "FROM ("
        "  SELECT a.src AS src, a.dst AS dst, "
        "         COALESCE(a.dst_port, 0) AS dst_port, "
        "         COALESCE(a.protocol, 0) AS protocol, "
        "         COUNT(*) AS count, "
        "         MIN(a.timestamp) AS first_seen, "
        "         MAX(a.timestamp) AS last_seen, "
        "         MAX(a.anomaly_score) AS score_max, "
        f"        {_SEV_RANK_SQL} AS sev_rank "
        f"  FROM alerts a {_FLOW_INDEX_HINT} "
        "  WHERE a.timestamp >= ? "
        "  GROUP BY a.src, a.dst, COALESCE(a.dst_port, 0), "
        "           COALESCE(a.protocol, 0)"
        ") g "
        f"LEFT JOIN flow_state fs ON fs.flow_key = {_flow_key_sql('g')} "
        f"WHERE 1=1{filter_sql} "
        # Orden: severidad máxima desc, luego score_max desc, luego volumen.
        "ORDER BY g.sev_rank DESC, g.score_max DESC, g.count DESC "
        "LIMIT ?"
    )
    params: list = [None] + (list(TRIAGED_STATES) if only_untriaged else [])
    return sql, params


def build_flow_percentile_queries() -> tuple:
    """(count_sql, nth_sql) para p50/p99 nearest-rank de un flujo concreto."""
    count_sql = (
        "SELECT COUNT(*) AS n FROM alerts "
        "WHERE src = ? AND dst = ? AND COALESCE(dst_port, 0) = ? "
        "  AND COALESCE(protocol, 0) = ? AND timestamp >= ? "
        "  AND anomaly_score IS NOT NULL"
    )
    nth_sql = (
        "SELECT anomaly_score FROM alerts "
        "WHERE src = ? AND dst = ? AND COALESCE(dst_port, 0) = ? "
        "  AND COALESCE(protocol, 0) = ? AND timestamp >= ? "
        "  AND anomaly_score IS NOT NULL "
        "ORDER BY anomaly_score ASC LIMIT 1 OFFSET ?"
    )
    return count_sql, nth_sql


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
    # Per-agent config (Hito 2.6): threshold / whitelist overrides
    # ------------------------------------------------------------------

    def set_agent_config(self, agent_id, alert_threshold=None,
                         whitelist_private=None) -> Dict:
        """Upsert a per-agent override; NULL column = use agent default."""
        current = self.get_agent_config(agent_id)
        threshold = (alert_threshold if alert_threshold is not None
                     else current.get("alert_threshold"))
        if whitelist_private is not None:
            whitelist = int(bool(whitelist_private))
        else:
            whitelist = current.get("whitelist_private")
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO agent_config (agent_id, alert_threshold,
                                          whitelist_private, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    alert_threshold   = excluded.alert_threshold,
                    whitelist_private = excluded.whitelist_private,
                    updated_at        = excluded.updated_at
                """,
                (agent_id, threshold, whitelist,
                 datetime.now().isoformat()),
            )
            self._conn.commit()
        # outside the lock: get_agent_config takes it itself
        return self.get_agent_config(agent_id)

    def get_agent_config(self, agent_id: str) -> Dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM agent_config WHERE agent_id = ?", (agent_id,)
            ).fetchone()
        return dict(row) if row else {}

    # ------------------------------------------------------------------
    # IP intel cache (Hito 3.8)
    # ------------------------------------------------------------------

    def get_ip_intel(self, ip: str) -> Dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM ip_intel WHERE ip = ?", (ip,)
            ).fetchone()
        if not row:
            return {}
        d = dict(row)
        d["anycast"] = bool(d.get("anycast"))
        return d

    def put_ip_intel(self, ip: str, org="", asn="", country="",
                     anycast=False) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ip_intel (ip, org, asn, country, anycast, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ip) DO UPDATE SET
                    org = excluded.org, asn = excluded.asn,
                    country = excluded.country, anycast = excluded.anycast,
                    fetched_at = excluded.fetched_at
                """,
                (ip, org, asn, country, int(bool(anycast)),
                 datetime.now().isoformat()),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Retention (Hito 1.1)
    # ------------------------------------------------------------------

    # Batch size and inter-batch yield for purge_old_alerts(). Measured on the
    # production container: ~627 deleted rows/s, i.e. ~7.6 s per 5000-row batch
    # and ~9.3 min to purge 349,955 rows. Holding self._lock for the WHOLE loop
    # (the old behaviour) starved ingest_alert_batch for that entire window —
    # run_in_executor only keeps the event loop free, not the hub lock. 1000
    # rows ≈ 1.5 s of lock per batch, and the sleep lets a waiting ingest win
    # the lock between batches (<500 ms ingest latency, verified by tests).
    PURGE_BATCH_SIZE = 1000
    PURGE_YIELD_SEC = 0.005

    def purge_old_alerts(self, retention_days: int,
                         batch_size: int | None = None,
                         yield_sec: float | None = None) -> int:
        """Delete alerts older than retention_days in batches. Returns deleted.

        The alert volume on Nuke (~1.9M rows historically) makes an unbounded
        SQLite file a real operational risk. Rows are deleted in batches, and
        the write lock is taken and RELEASED per batch (never around the whole
        loop) so concurrent ingest keeps reporting while a long purge runs.
        The O(1) counters stay truthful because a full recount runs afterwards
        (ingest only ever adds; the recount is the only post-purge cost).

        NOTE: this only empties free pages, it does not shrink hub.db — see
        vacuum() for that, which must be triggered explicitly/scheduled.
        """
        if retention_days <= 0:  # 0/negative disables retention (keep all)
            return 0
        batch = batch_size if batch_size is not None else self.PURGE_BATCH_SIZE
        pause = yield_sec if yield_sec is not None else self.PURGE_YIELD_SEC
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        deleted = 0
        while True:
            with self._lock:  # held for ONE batch only, then dropped
                cur = self._conn.execute(
                    "DELETE FROM alerts WHERE id IN ("
                    " SELECT id FROM alerts WHERE timestamp < ? LIMIT ?)",
                    (cutoff, batch),
                )
                n = cur.rowcount
                self._conn.commit()
            deleted += n
            if n < batch:
                break
            if pause:
                time.sleep(pause)  # yield: let a waiting ingest grab the lock
        if deleted:
            # Purges are rare; afford a full recount so by_severity is truthful
            # too (the incremental counters only know about inserts).
            with self._lock:
                self._counts = None
            self._ensure_counts()
            logger.info("Retention: purged %d alert(s) older than %d days",
                        deleted, retention_days)
        return deleted

    def vacuum(self) -> Dict:
        """Rebuild hub.db to hand free pages back to the filesystem.

        Delete-only purges never shrink the file (auto_vacuum=0,
        journal_mode=delete — measured: identical size before/after), so this
        is the only way to reclaim disk after a large purge.

        WARNING — this BLOCKS ALL WRITES for as long as it takes (SQLite needs
        exclusive access) and needs up to ~1x the DB size in free disk space
        for the temporary copy. Never call it from the maintenance loop, never
        while a purge is running: only on demand / from a scheduled job outside
        ingest hours.

        Returns {"size_before": bytes, "size_after": bytes, "reclaimed": bytes}.
        """
        # Outside any transaction: VACUUM cannot run inside one.
        size_before = self.db_path.stat().st_size if self.db_path.exists() else 0
        with self._lock:
            self._conn.commit()
            self._conn.execute("VACUUM")
            self._conn.commit()
        size_after = self.db_path.stat().st_size if self.db_path.exists() else 0
        logger.info("Hub VACUUM: %d -> %d bytes (reclaimed %d)",
                    size_before, size_after, size_before - size_after)
        return {
            "size_before": size_before,
            "size_after": size_after,
            "reclaimed": size_before - size_after,
        }

    # ------------------------------------------------------------------
    # Telegram CRITICAL digest (Hito 1.2) — queue side
    # ------------------------------------------------------------------

    def pop_pending_criticals(self, limit: int = 50) -> list:
        """Return critical alerts not yet digested (max `limit`). Not marked yet
        — call mark_criticals_notified(ids) with the ids returned here, only
        after a successful send.

        The `id` column is included so the caller can acknowledge exactly what
        it delivered. Acknowledging by severity alone (the old contract) marked
        every pending CRITICAL, so anything beyond the LIMIT was silently
        swallowed and never notified.
        """
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, agent_name, src, dst, dst_port, protocol, severity "
                "FROM alerts WHERE severity = 'CRITICAL' "
                "AND notified_telegram = 0 ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_criticals_notified(self, ids: Optional[List[int]] = None) -> int:
        """Mark CRITICAL alerts as digested. Returns the number of rows marked.

        Pass the exact ids returned by pop_pending_criticals() — that is the
        only loss-safe way: a severity-wide UPDATE also marks the alerts that
        were NOT in the digest (over the LIMIT), losing them forever.

        Backwards compatibility: calling with no argument keeps the old
        signature working, but is capped to the same newest-50 window that
        pop_pending_criticals() returns instead of every pending row, so a
        legacy caller cannot silently drop a backlog either.
        """
        with self._lock:
            if ids is None:
                cur = self._conn.execute(
                    "UPDATE alerts SET notified_telegram = 1 WHERE id IN ("
                    " SELECT id FROM alerts WHERE severity = 'CRITICAL' "
                    " AND notified_telegram = 0 ORDER BY id DESC LIMIT 50)"
                )
            else:
                ids = [int(i) for i in ids]
                if not ids:
                    return 0
                placeholders = ",".join("?" * len(ids))
                cur = self._conn.execute(
                    "UPDATE alerts SET notified_telegram = 1 "
                    f"WHERE id IN ({placeholders}) "
                    "AND severity = 'CRITICAL' AND notified_telegram = 0",
                    ids,
                )
            n = cur.rowcount
            self._conn.commit()
        return n

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

    # ------------------------------------------------------------------
    # Fase 1.1 — flujos agregados (5-tupla)
    # ------------------------------------------------------------------

    def aggregate_flows(
        self,
        minutes: int = FLOWS_DEFAULT_MINUTES,
        limit: int = FLOWS_DEFAULT_LIMIT,
        only_untriaged: bool = False,
    ) -> Dict:
        """Agrupa alertas por (src, dst, dst_port, protocol) en una ventana.

        Args:
            minutes: ventana hacia atrás; se capa a [1, 1440].
            limit: nº de flujos devueltos; se capa a [1, 200].
            only_untriaged: excluye los flujos cuyo estado ya no es 'nuevo'.

        Returns:
            {"flows": [...], "minutes": int, "limit": int, "has_more": bool,
             "total_flows": int}

        Percentiles: nearest-rank sobre el score ya normalizado a [0,100]
        (``predictor.normalize_score``, ya en dev). Se calculan en Python y no
        con una función de ventana de SQLite por dos razones: (a) el rango de
        la ventana ya sale del índice, y (b) ``ROW_NUMBER()`` sobre 1,7 M
        filas dentro de la ventana mataría la latencia; el desglose por flujo
        se pide solo para los ``limit`` flujos devueltos.
        """
        minutes = self._clamp_int(minutes, 1, FLOWS_MAX_MINUTES,
                                  FLOWS_DEFAULT_MINUTES)
        limit = self._clamp_int(limit, 1, FLOWS_MAX_LIMIT, FLOWS_DEFAULT_LIMIT)
        since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

        sql, params = build_flows_query(only_untriaged)
        params[0] = since
        params.append(limit)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
            flows = [self._flow_row_to_dict(r, minutes) for r in rows]
            # COUNT(*) OVER () viene en la primera fila; 0 si no hay flujos.
            total = int(rows[0]["total_flows"]) if rows else 0
            self._attach_percentiles(flows, since)

        return {
            "flows": flows,
            "minutes": minutes,
            "limit": limit,
            # has_more: hay flujos agregables por encima de los devueltos.
            "has_more": total > len(flows),
            "total_flows": total,
        }

    def _flow_row_to_dict(self, row: sqlite3.Row, minutes: int) -> Dict:
        count = int(row["count"])
        return {
            "flow_key": row["flow_key"],
            "src": row["src"],
            "dst": row["dst"],
            "dst_port": int(row["dst_port"]),
            "protocol": int(row["protocol"]),
            "count": count,
            "severity": _SEV_BY_RANK.get(int(row["sev_rank"]), "UNKNOWN"),
            "score_max": float(row["score_max"] or 0.0),
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "alerts_per_minute": (count / minutes) if minutes else 0.0,
            "state": row["state"],
            "note": row["note"],
        }

    def _attach_percentiles(self, flows: List[Dict], since: str) -> None:
        """p50/p99 nearest-rank por flujo, solo para los flujos devueltos.

        Coste acotado a ``limit`` flujos (máx. 200): un COUNT y dos búsquedas
        por offset dentro del flujo. El índice idx_alerts_flow_score deja el
        ORDER BY anomaly_score servido por el índice (igualdad en la 5-tupla),
        así que el OFFSET avanza sin ordenar ni tocar la tabla.
        """
        for f in flows:
            n = self._scored_count(f, since)
            if n == 0:
                f["score_p50"] = 0.0
                f["score_p99"] = 0.0
                continue
            f["score_p50"] = self._nth_score(
                f, since, max(0, math.ceil(0.50 * n) - 1))
            f["score_p99"] = self._nth_score(
                f, since, max(0, math.ceil(0.99 * n) - 1))

    def _scored_count(self, flow: Dict, since: str) -> int:
        count_sql, _ = build_flow_percentile_queries()
        row = self._conn.execute(
            count_sql,
            (flow["src"], flow["dst"], flow["dst_port"], flow["protocol"], since),
        ).fetchone()
        return int(row["n"] or 0)

    def _nth_score(self, flow: Dict, since: str, offset: int) -> float:
        _, nth_sql = build_flow_percentile_queries()
        row = self._conn.execute(
            nth_sql,
            (flow["src"], flow["dst"], flow["dst_port"], flow["protocol"],
             since, offset),
        ).fetchone()
        return 0.0 if row is None else float(row["anomaly_score"])

    @staticmethod
    def _clamp_int(value, low: int, high: int, default: int) -> int:
        try:
            v = int(value)
        except (TypeError, ValueError):
            return default
        return max(low, min(high, v))

    # ------------------------------------------------------------------
    # Fase 1.2 — estado de triaje por flujo
    # ------------------------------------------------------------------

    def get_flow_state(self, key: str) -> Dict:
        """Estado del flujo o ``{}`` si nunca se ha triado."""
        with self._lock:
            row = self._conn.execute(
                "SELECT flow_key, state, note, updated_at FROM flow_state "
                "WHERE flow_key = ?", (key,),
            ).fetchone()
        return dict(row) if row else {}

    def set_flow_state(self, key: str, state: str,
                       note: Optional[str] = None) -> Dict:
        """Upsert del estado de un flujo. ``ValueError`` si el estado no vale."""
        if state not in FLOW_STATES:
            raise ValueError(
                f"estado inválido: {state!r}; permitidos: {', '.join(FLOW_STATES)}")
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT INTO flow_state (flow_key, state, note, updated_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(flow_key) DO UPDATE SET "
                "  state = excluded.state, "
                "  note = COALESCE(excluded.note, flow_state.note), "
                "  updated_at = excluded.updated_at",
                (key, state, note, now),
            )
            self._conn.commit()
        return self.get_flow_state(key)

    def close(self) -> None:
        with self._lock:
            self._conn.close()


# Global singleton
hub_store = HubStore()
