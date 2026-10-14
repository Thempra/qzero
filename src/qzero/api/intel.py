"""Server-side IP enrichment cache (Hito 3.8).

The dashboard used to call ipinfo.io synchronously per alert render
(st.cache_data only caches per Streamlit process/session). This module
caches ASN/org in the hub DB table `ip_intel` so repeat IPs never hit the
network again, and exposes GET /api/v1/intel/{ip} for the dashboard.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address

logger = logging.getLogger("qzero.intel")

CACHE_TTL_DAYS = 7


def is_private_ip(ip: str) -> bool:
    try:
        return ip_address(ip).is_private
    except ValueError:
        return True  # unparseable → treat as LAN, never query external APIs


def lookup_upstream(ip: str) -> dict:
    """Query ipinfo.io (primary) / ip-api.com (fallback). Best-effort."""
    for base in (
        "https://ipinfo.io/{ip}/json",
        "http://ip-api.com/json/{ip}?fields=status,country,org,as",  # NOSONAR S5332: fallback solo lectura sin credenciales (ip-api solo HTTPS de pago)
    ):
        try:
            url = base.format(ip=ip)
            req = urllib.request.Request(
                url, headers={"User-Agent": "qzero-hub"})
            with urllib.request.urlopen(req, timeout=3) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "ipinfo" in base:
                if d.get("org"):
                    asn, _, org = d["org"].partition(" ")
                    return {"org": org or d["org"], "asn": asn,
                            "country": d.get("country", ""),
                            "anycast": bool(d.get("anycast"))}
            elif d.get("status") == "success":
                return {"org": d.get("org", ""), "asn": d.get("as", ""),
                        "country": d.get("country", ""), "anycast": False}
        except Exception:  # noqa: BLE001
            continue
    return {"org": "", "asn": "", "country": "", "anycast": False}


def enrich_ip(hub_store, ip: str) -> dict:
    """Cached enrichment. Fresh cache row → zero network. Private → LAN stub."""
    if is_private_ip(ip):
        return {"ip": ip, "org": "LAN", "asn": "PRIVATE", "country": "",
                "anycast": False, "cached": True}
    row = hub_store.get_ip_intel(ip)
    if row and _fresh(row.get("fetched_at", "")):
        row["cached"] = True
        return row
    data = lookup_upstream(ip)
    hub_store.put_ip_intel(ip, **data)
    return {"ip": ip, **data, "cached": False}


def _fresh(fetched_at: str) -> bool:
    try:
        ts = datetime.fromisoformat(fetched_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    return datetime.now(timezone.utc) - ts < timedelta(days=CACHE_TTL_DAYS)
