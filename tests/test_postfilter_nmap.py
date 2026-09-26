"""
Regression test: NMAP / LAN-scan detection must NOT be suppressed by the
classical PostFilter's RFC1918 whitelist.

Historical bug (2026-09): PostFilterConfig.whitelist_private defaulted to True.
Because an agent deployed on the LAN always has a private source IP, and
internal LAN scans (the very threat an NDR sensor hunts) have private src AND
dst, EVERY alert was suppressed as "private_rfc1918". The hub reported
total_alerts=0 while the QI-VAE produced anomaly scores up to 1.9e9.

The fix flips the default to False: RFC1918 range is NOT a benign signal in a
network-monitoring context. This test pins that behaviour so it can't regress.
"""

import importlib.util
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def _load(name, rel):
    path = SRC / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


pf = _load("qzero_pf", "qzero/preprocessing/postfilter.py")
PostFilter, PostFilterConfig = pf.PostFilter, pf.PostFilterConfig
agent = _load("qzero_agent", "qzero/agent/agent.py")
AgentConfig = agent.AgentConfig


# Scenarios identical to a real NMAP launched from the LAN (agent on 192.168.50.x)
NMAP_SCANS = [
    # (name, flow, anomalous_score)
    ("nmap-sS publico:22",
     dict(src_ip="192.168.50.5", dst_ip="203.0.113.10", src_port=42000,
          dport=22, proto=6, total_length_fwd_packets=800,
          total_length_bwd_packets=120), 84.12),
    ("nmap-sS publico:443",
     dict(src_ip="192.168.50.5", dst_ip="198.51.100.7", src_port=42001,
          dport=443, proto=6, total_length_fwd_packets=600,
          total_length_bwd_packets=90), 35.47),
    ("nmap-sT barrido",
     dict(src_ip="192.168.50.5", dst_ip="203.0.113.99", src_port=41000,
          dport=8080, proto=6, total_length_fwd_packets=700,
          total_length_bwd_packets=50), 1918002816.0),
    ("nmap host interno",
     dict(src_ip="192.168.50.136", dst_ip="192.168.50.5", src_port=33000,
          dport=445, proto=6, total_length_fwd_packets=900,
          total_length_bwd_packets=200), 9.5),
    ("estrategia ver /22",
     dict(src_ip="192.168.50.5", dst_ip="192.168.50.1", src_port=30000,
          dport=23, proto=6, total_length_fwd_packets=300,
          total_length_bwd_packets=10), 15.3),
]


def test_nmap_scans_not_suppressed_by_private_whitelist():
    """Default PostFilter must NOT suppress LAN-sourced anomaly flows."""
    pf_inst = PostFilter()  # default config (whitelist_private=False)
    for name, flow, score in NMAP_SCANS:
        suppress, reason = pf_inst.should_suppress(flow, score)
        assert not suppress, (
            f"{name}: alert suppressed as {reason or 'unknown'} (score={score}). "
            "RFC1918 whitelist must default off for LAN-driven detection."
        )


def test_agent_config_default_whitelist_private_is_false():
    cfg = AgentConfig(interface="eth0")
    assert cfg.whitelist_private is False


def test_dns_still_suppressed():
    """DNS keepalive/resolution must remain suppressed (no FP explosion)."""
    p = PostFilter()
    req = dict(src_ip="192.168.50.5", dst_ip="8.8.8.8", src_port=53000,
               dport=53, proto=17, total_length_fwd_packets=80,
               total_length_bwd_packets=80)
    resp = dict(src_ip="8.8.8.8", dst_ip="192.168.50.5", src_port=53,
                dport=53000, proto=17, total_length_fwd_packets=80,
                total_length_bwd_packets=80)
    s1, r1 = p.should_suppress(req, 88.0)
    s2, r2 = p.should_suppress(resp, 44.0)
    assert s1 and r1 == "dns"
    assert s2 and r2 == "dns"


def test_private_opt_in_restores_old_behavior():
    """Explicitly opting in to private-suppression re-enables old behaviour."""
    p = PostFilter(PostFilterConfig(whitelist_private=True))
    flow, score = NMAP_SCANS[0][1], NMAP_SCANS[0][2]
    suppress, reason = p.should_suppress(flow, score)
    assert suppress and reason == "private_rfc1918"
