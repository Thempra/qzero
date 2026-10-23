"""Hub background maintenance (Hito 1): retention, Telegram digest, liveness.

One asyncio task started at API startup:
  1. Retention   — purge alerts older than QZERO_ALERT_RETENTION_DAYS hourly,
                   so hub.db cannot grow without bound on Nuke.
  2. Telegram    — batched CRITICAL digest (never per-alert) when
                   QZERO_TELEGRAM_BOT_TOKEN + QZERO_TELEGRAM_CHAT_ID are set.
                   Rate-limited: at most one message per
                   QZERO_TELEGRAM_MIN_INTERVAL_MIN (storm of FPs -> one digest).
  3. Liveness    — if an agent's heartbeat ceases for more than
                   QZERO_AGENT_OFFLINE_MIN minutes, notify once per agent
                   (Hito 1.3 acceptance: 'nota en Agents' + aviso Telegram).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.request
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def send_telegram(text: str) -> bool:
    """Send one message to the configured ops chat. Best-effort."""
    token = _env("QZERO_TELEGRAM_BOT_TOKEN")
    chat = _env("QZERO_TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    try:
        req = urllib.request.Request(
            "https://api.telegram.org/bot{}/sendMessage".format(token),
            data=json.dumps({
                "chat_id": chat,
                "text": text,
                "parse_mode": "Markdown",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as e:  # noqa: BLE001 — never let notify break the hub
        logger.warning("Telegram send failed: %s", e)
        return False


def _parse_ts(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            # Hub writes last_seen with naive datetime.now() (local); keep
            # the comparison in the same reference frame.
            dt = dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return dt
    except (ValueError, TypeError):
        return None


def build_critical_digest(alerts: list) -> str:
    lines = ["🚨 *QZero — {} alerta(s) CRITICAL*".format(len(alerts))]
    for a in alerts[:10]:
        who = a.get("agent_name") or a.get("agent_id") or "?"
        lines.append(
            "• `{}` → `{}:{}` ({}) — {}".format(
                who, a.get("src", "?"), a.get("dst_port", "?"),
                a.get("dst", "?"), a.get("protocol", "?"),
            )
        )
    if len(alerts) > 10:
        lines.append("… y {} más".format(len(alerts) - 10))
    return "\n".join(lines)


async def maintenance_loop(hub_store) -> None:
    """Single loop; each sub-task runs on its own cadence, never raises.

    CONFIG IS READ ONCE, AT STARTUP (below). Changing
    QZERO_ALERT_RETENTION_DAYS (or any other QZERO_MAINT_* env) requires an API
    restart — editing the env of a running container has no effect until then.
    Accepted as-is (documented, not fixed): the loop is a single long-lived
    task and re-reading envs per tick would hide misconfiguration instead of
    surfacing it at deploy time.
    """
    retention_days = int(_env("QZERO_ALERT_RETENTION_DAYS", "90") or 0)
    scan_sec = int(_env("QZERO_MAINT_INTERVAL_SEC", "60") or 60)
    purge_sec = int(_env("QZERO_RETENTION_INTERVAL_SEC", "3600") or 3600)
    tg_min_interval = int(_env("QZERO_TELEGRAM_MIN_INTERVAL_MIN", "15") or 15)
    offline_min = int(_env("QZERO_AGENT_OFFLINE_MIN", "10") or 10)

    last_purge = 0.0
    last_tg = None  # datetime of last digest sent
    # KNOWN LIMITATION: in-memory only, so every restart forgets what was
    # already warned about and re-sends one "agente caído" per stale agent
    # (false offline notice right after each deploy/restart). Persisting it
    # (e.g. an agents.offline_notified column) is pending — see
    # docs/research/impl-fase0-retencion.md.
    offline_notified: set = set()  # agents already warned (reset on recovery)
    loop = asyncio.get_event_loop()

    while True:
        await asyncio.sleep(scan_sec)
        now = loop.time()

        # 1) Retention ------------------------------------------------
        # purge_old_alerts() now takes/releases the hub lock PER BATCH, so this
        # executor thread no longer starves ingest for the whole purge. It runs
        # in an executor only to keep the event loop free.
        # NOT done here: VACUUM. hub_store.vacuum() blocks every write for the
        # length of a full DB rebuild and needs ~1x the DB size free — trigger
        # it explicitly (scheduled/manual), never from this loop.
        if retention_days > 0 and now - last_purge >= purge_sec:
            last_purge = now
            try:
                deleted = await loop.run_in_executor(
                    None, hub_store.purge_old_alerts, retention_days)
                if deleted:
                    logger.info("Retention pass freed %d rows; run a scheduled "
                                "VACUUM to reclaim disk", deleted)
            except Exception as e:  # noqa: BLE001
                logger.warning("Retention purge failed: %s", e)

        # 2) Telegram CRITICAL digest (rate-limited) -------------------
        if _env("QZERO_TELEGRAM_BOT_TOKEN") and _env("QZERO_TELEGRAM_CHAT_ID"):
            cooldown = timedelta(minutes=tg_min_interval)
            if last_tg is None or datetime.now(timezone.utc) - last_tg >= cooldown:
                try:
                    pending = hub_store.pop_pending_criticals()
                except Exception as e:  # noqa: BLE001
                    logger.warning("Critical query failed: %s", e)
                    pending = []
                if pending:
                    ok = await loop.run_in_executor(
                        None, send_telegram, build_critical_digest(pending))
                    if ok:
                        # Acknowledge ONLY the ids actually delivered: the old
                        # severity-wide UPDATE also marked every CRITICAL past
                        # the pop limit, silently losing them.
                        hub_store.mark_criticals_notified(
                            [a["id"] for a in pending])
                        last_tg = datetime.now(timezone.utc)
                        logger.info(
                            "Telegram digest: %d CRITICAL alert(s)", len(pending))

        # 3) Agent liveness (Hito 1.3) ---------------------------------
        try:
            agents = hub_store.list_agents()
        except Exception:  # noqa: BLE001
            agents = []
        now_dt = datetime.now(timezone.utc)
        for ag in agents:
            aid = ag.get("agent_id")
            seen = _parse_ts(ag.get("last_seen") or "")
            if not aid or not seen:
                continue
            stale = now_dt - seen
            if stale > timedelta(minutes=offline_min):
                if aid not in offline_notified:
                    offline_notified.add(aid)
                    logger.warning(
                        "Agent %s heartbeat ceased %.0f min ago",
                        aid, stale.total_seconds() / 60)
                    await loop.run_in_executor(
                        None, send_telegram,
                        "⚠️ Agente QZero *{}* sin heartbeat hace "
                        "{:.0f} min".format(ag.get("agent_name") or aid,
                                            stale.total_seconds() / 60))
            else:
                if aid in offline_notified:
                    offline_notified.discard(aid)
                    await loop.run_in_executor(
                        None, send_telegram,
                        "✅ Agente QZero *{}* de vuelta".format(
                            ag.get("agent_name") or aid))
