"""
QZero — alert identification & enrichment
==========================================
Adds an actionable layer on top of the raw anomaly alerts so an operator can
actually understand WHAT each alert is and WHAT to do about it.

The raw hub alerts only carry {src, dst, protocol, ports, size, anomaly_score,
severity} — no attack type, no direction, no context. This module enriches each
alert with:

  * direction       - INTERNAL / OUTBOUND / INBOUND / EXTERNAL
  * destination org - reverse of the raw IP (reverse-DNS / ASN / WHOIS org)
  * threat_type     - a human-readable classification (e.g. "SSH brute-force",
                      "TLS/HTTPS egress", ...)
  * explanation     - plain-language "what happened, why, what to do"

It uses only the Python stdlib (socket / urllib) so it needs no extra
dependencies, and every network call is short + cached so the dashboard stays
responsive.
"""

import ipaddress
import json
import os
import socket
import urllib.request

import streamlit as st

# ---------------------------------------------------------------------------
# Direction classification
# ---------------------------------------------------------------------------
def is_private_ip(ip: str) -> bool:
    """True for RFC1918 / loopback / link-local / CGNAT (i.e. not public routable)."""
    try:
        a = ipaddress.ip_address(ip)
    except Exception:
        return True
    return bool(a.is_private or a.is_loopback or a.is_link_local)


def classify_direction(src: str, dst: str) -> str:
    s_priv = is_private_ip(src)
    d_priv = is_private_ip(dst)
    if s_priv and d_priv:
        return "INTERNAL"
    if s_priv and not d_priv:
        return "OUTBOUND"      # local host -> internet
    if not s_priv and d_priv:
        return "INBOUND"       # internet -> local host
    return "EXTERNAL"          # internet <-> internet (shouldn't appear)


# ---------------------------------------------------------------------------
# Destination enrichment (ASN / org) — via ipinfo.io (HTTPS), heavily cached
# ---------------------------------------------------------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def asn_lookup(ip: str) -> dict:
    """Return {org, asn, country, anycast} for a public IP. LAN stub for private IPs."""
    if is_private_ip(ip):
        return {"org": "LAN", "asn": "PRIVATE", "country": "", "anycast": False}
    # Primary: ipinfo.io (HTTPS, free tier 50k/month). Fallback: ip-api.com (HTTP only).
    # NOSONAR S5332: ip-api.com solo ofrece HTTPS en plan de pago; es fallback de
    # solo lectura (enriquecimiento ASN/org, sin credenciales ni datos sensibles).
    for base in ("https://ipinfo.io/{ip}/json", "http://ip-api.com/json/{ip}?fields=status,country,org,as"):  # NOSONAR
        try:
            url = base.format(ip=ip)
            req = urllib.request.Request(url, headers={"User-Agent": "qzero-dashboard"})
            with urllib.request.urlopen(req, timeout=3) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "ipinfo" in base:
                if d.get("org"):
                    asn, _, org = d["org"].partition(" ")
                    return {"org": org or d["org"], "asn": asn,
                            "country": d.get("country", ""), "anycast": bool(d.get("anycast"))}
            elif d.get("status") == "success":
                return {"org": d.get("org", ""), "asn": d.get("as", ""),
                        "country": d.get("country", ""), "anycast": False}
        except Exception:
            continue
    return {"org": "?", "asn": "", "country": "", "anycast": False}


def enrich_destination(src: str, dst: str, direction: str) -> dict:
    """Best-effort human label for the remote end of the flow."""
    if direction == "INTERNAL":
        return {"org": "LAN internal", "asn": "", "country": "", "anycast": False}
    # El extremo remoto es dst en salientes y src en entrantes.
    if direction == "OUTBOUND":
        return asn_lookup(dst)
    if direction == "INBOUND":
        return asn_lookup(src)
    return {"org": "?", "asn": "", "country": "", "anycast": False}


# ---------------------------------------------------------------------------
# Threat classification (deterministic, port/direction based) + explanation
# ---------------------------------------------------------------------------
SSH_PORTS = {22, 2222, 22222}
WEB_EGRESS_PORTS = {443, 80}
THREAT_EGRESS = "Egress TLS/HTTPS"
MALWARE_PORTS = {4444, 5555, 6667, 31337, 1234}


def classify_threat(src, dst, _src_port, dst_port, protocol, size, direction,
                    score) -> tuple[str, str]:
    """Return (threat_type, explanation). Seeded by ports + direction + score."""
    proto = {6: "TCP", 17: "UDP", 1: "ICMP"}.get(protocol, f"proto{protocol}")

    # 1) Inbound / internal SSH
    if dst_port in SSH_PORTS and direction in ("INBOUND", "INTERNAL"):
        return (
            "Brute-force / recon SSH",
            f"Tráfico {proto} hacia el puerto {dst_port} (SSH) desde {src}. "
            "Múltiples conexiones a SSH son el patrón típico de fuerza bruta o "
            "escaneo. Acción: revisa los intentos de login (fail2ban/systemd), "
            "bloquea el origen si no debe acceder y revisa /var/log/auth.log.",
        )

    # 2) DNS egress
    if direction == "OUTBOUND" and dst_port == 53 and protocol in (6, 17):
        return (
            "Egress DNS",
            f"Consulta DNS saliente a {dst}:53. El score ({score:.1f}) suele "
            "deberse a volumen o a dominios nuevos, no a un ataque. Acción: si "
            "hay un pico inusual de resolución, revisa qué proceso consulta "
            "(posible beaconing DNS), pero por defecto es tráfico benigno.",
        )

    # 3) Egress TLS/HTTPS to a CDN — the dominant (usually benign) case
    if direction == "OUTBOUND" and dst_port in WEB_EGRESS_PORTS:
        return (
            THREAT_EGRESS,
            f"Conexión {proto} cifrada saliente hacia {dst}:{dst_port}. El score "
            f"({score:.1f}) refleja 'novedad' frente al baseline del modelo "
            "(el TLS cifrado es opaco), no necesariamente una amenaza. Acción: "
            "verifica que el destino sea un servicio esperado (CDN/API). Si es "
            "un servicio reputado y hace lo habitual, suele ser benigno.",
        )

    # 4) Inbound web
    if direction == "INBOUND" and dst_port in WEB_EGRESS_PORTS:
        return (
            "Servicio web (inbound)",
            f"Petición {proto} entrante hacia el puerto {dst_port} de un host "
            f"público. Acción: revisa logs del servidor web para abusos "
            "(Webshell, path traversal, bots).",
        )

    # 5) Response to an outbound flow (inbound to local ephemeral port)
    if direction == "INBOUND" and dst_port >= 32768:
        return (
            "Respuesta a conexión saliente",
            f"Paquete {proto} entrante hacia un puerto efímero local "
            f"({dst_port}): es la respuesta a una conexión iniciada por el "
            f"propio host (p. ej. HTTPS/API saliente). El score ({score:.1f}) "
            "refleja novedad del flujo, no un ataque. Acción: si el destino "
            "original era un servicio reputado, es benigno; revísalo solo si "
            "hay volumen anómalo o destinos desconocidos.",
        )

    # 6) ICMP
    if protocol == 1:
        return (
            "ICMP / sondeo",
            "Tráfico ICMP (ping/escaneo). Un volumen alto de ICMP desde una "
            "misma fuente puede ser sondeo de red. Acción: revisa la fuente y "
            "el volumen; considera limitar ICMP en el firewall si es abusivo.",
        )

    # 7) Listener on known-malicious ports
    if dst_port in MALWARE_PORTS and direction in ("INBOUND", "INTERNAL"):
        return (
            "Listener puerto sensible",
            f"Contacto hacia el puerto {dst_port}, asociado a malware/backdoors "
            "comunes. Acción: comprueba qué proceso escucha (ss -ltnp) e "
            "investiga el origen.",
        )

    # 8) Fallback
    return (
        "Anomalía de flujo",
        f"Flujo {proto} {direction.lower()} entre {src} y {dst} (puerto "
        f"{dst_port}, {size}B) con score atípico ({score:.1f}). Sin regla "
        "específica; revisa el contexto del puerto y el destino.",
    )


# ---------------------------------------------------------------------------
# Console convenience
# ---------------------------------------------------------------------------
def suggest_severity(_direction: str, threat_type: str) -> str:
    """Downgrade likely-benign egress noise so the console is actionable."""
    if threat_type == THREAT_EGRESS:
        return "INFO/revisar"
    if threat_type == "Brute-force / recon SSH":
        return "CRITICAL/actuar"
    return ""


def enrich_alert(a: dict) -> dict:
    """Return a copy of the alert with direction, org, threat_type, explanation."""
    direction = classify_direction(a.get("src", "?"), a.get("dst", "?"))
    remote = enrich_destination(a.get("src", "?"), a.get("dst", "?"), direction)
    threat_type, explanation = classify_threat(
        a.get("src", "?"), a.get("dst", "?"),
        a.get("src_port", 0), a.get("dst_port", 0),
        a.get("protocol", 0), a.get("size", 0),
        direction, a.get("anomaly_score", 0.0),
    )
    out = dict(a)
    out["direction"] = direction
    out["dest_org"] = remote["org"]
    out["dest_asn"] = remote["asn"]
    out["dest_anycast"] = remote.get("anycast", False)
    out["threat_type"] = threat_type
    # Note when the remote is an anycast CDN (extra confidence it's benign egress)
    if remote.get("anycast") and threat_type == THREAT_EGRESS:
        explanation += " Destino anycast (CDN) — muy probablemente tráfico legítimo."
    out["explanation"] = explanation
    out["action"] = suggest_severity(direction, threat_type)
    return out
