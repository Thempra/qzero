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


# --- Rate-cap / feature-scale regression (2026-09) --------------------------
# A 1-packet flow yields duration~1e-9s, so bytes_per_sec / packets_per_sec
# become astronomically large (up to 1e11) and blow the QI-VAE score to ~1.9e9,
# flooding the hub with bogus CRITICALs. The extractor now caps the rate
# features; this pins the constants and the clamping behaviour.


def test_rate_cap_constants_are_reasonable():
    import re
    fe_src = (Path(__file__).resolve().parents[1]
              / "src" / "qzero" / "preprocessing" / "flow_extractor.py").read_text()
    cb = int(re.search(r"MAX_FLOW_BYTES_PER_SEC = ([\d_]+)", fe_src).group(1).replace("_", ""))
    cp = int(re.search(r"MAX_FLOW_PACKETS_PER_SEC = ([\d_]+)", fe_src).group(1).replace("_", ""))
    # Bounded to physically meaningful maxima (not 1e9+)
    assert cb <= 2_000_000_000, f"bytes/s cap too high: {cb}"
    assert cp <= 500_000, f"pkts/s cap too high: {cp}"
    assert "min(total_bytes / duration, MAX_FLOW_BYTES_PER_SEC)" in fe_src
    assert "min(total_pkts / duration, MAX_FLOW_PACKETS_PER_SEC)" in fe_src


def test_min_flow_bytes_default_raised_to_128():
    assert PostFilterConfig().min_flow_bytes >= 128


def test_https_keepalive_under_threshold_still_suppressed():
    # A tiny 443 keepalive (total 30 bytes < 128) is suppressed as no-payload.
    f = dict(src_ip="192.168.50.5", dst_ip="172.64.153.51", src_port=50000,
             dport=443, proto=6, total_length_fwd_packets=20,
             total_length_bwd_packets=10)
    sup, reason = PostFilter().should_suppress(f, 6.0)
    assert sup and reason == "https_no_payload", (sup, reason)


def test_https_real_traffic_over_threshold_not_suppressed():
    # A real TLS flow with payload (>128) on 443 must NOT be suppressed.
    f = dict(src_ip="192.168.50.5", dst_ip="172.64.153.51", src_port=50001,
             dport=443, proto=6, total_length_fwd_packets=1800,
             total_length_bwd_packets=2400)
    sup, reason = PostFilter().should_suppress(f, 7.0)
    assert not sup, reason


def test_single_packet_unicast_nmap_not_suppressed():
    """A 1-packet UNICAST SYN (nmap -sS to a host) is real scan signal -> NOT suppressed."""
    flows = [
        dict(src_ip="192.168.50.5", dst_ip="203.0.113.10", src_port=42000,
             dport=22, proto=6, total_length_fwd_packets=54,
             total_length_bwd_packets=0, total_fwd_packets=1, total_bwd_packets=0),
        dict(src_ip="192.168.50.5", dst_ip="1.1.1.1", src_port=42001,
             dport=8080, proto=6, total_length_fwd_packets=54,
             total_length_bwd_packets=0, total_fwd_packets=1, total_bwd_packets=0),
    ]
    pf_obj = PostFilter(PostFilterConfig())
    for f in flows:
        suppressed, reason = pf_obj.should_suppress(f, 24.0)
        assert not suppressed, f"unicast 1-pkt scan {f} wrongly suppressed: {reason}"


def test_single_packet_broadcast_ssdp_suppressed():
    """SSDP/broadcast discovery (Chromecast etc.) 1-pkt -> suppressed (noise, not attack)."""
    flows = [
        dict(src_ip="192.168.50.10", dst_ip="192.168.50.255", src_port=0,
             dport=32412, proto=17, total_length_fwd_packets=160,
             total_length_bwd_packets=0, total_fwd_packets=1, total_bwd_packets=0),
        dict(src_ip="192.168.50.10", dst_ip="224.0.0.251", src_port=0,
             dport=5353, proto=17, total_length_fwd_packets=160,
             total_length_bwd_packets=0, total_fwd_packets=1, total_bwd_packets=0),
    ]
    pf_obj = PostFilter(PostFilterConfig())
    for f in flows:
        suppressed, reason = pf_obj.should_suppress(f, 24.0)
        assert suppressed, f"broadcast 1-pkt {f} should be suppressed, got {reason}"


def test_multi_packet_broadcast_not_suppressed_by_min_packets():
    """A broadcast flow with >1 packet is NOT blocked by the single-packet rule
    (other checks still apply, but min_flow_packets alone must not drop it)."""
    f = dict(src_ip="192.168.50.10", dst_ip="192.168.50.255", src_port=0,
             dport=32412, proto=17, total_length_fwd_packets=400,
             total_length_bwd_packets=0, total_fwd_packets=5, total_bwd_packets=0)
    pf_obj = PostFilter(PostFilterConfig())
    suppressed, reason = pf_obj.should_suppress(f, 24.0)
    assert reason != "single_packet_broadcast", f"multi-pkt broadcast wrongly dropped: {reason}"


def test_https_volume_capped_below_critical():
    """High-volume HTTPS (legit web/CDN) must NEVER be CRITICAL regardless of score."""
    obj = PostFilter(PostFilterConfig())
    for score in (5.0, 6.0, 100.0, 50000.0, 835737.4):
        sev = obj.severity_for({"dst_port": 443}, score)
        assert sev in ("HIGH", "MEDIUM", "LOW"), f"https score={score} -> {sev} must be capped"
        assert sev != "CRITICAL", f"https score={score} wrongly CRITICAL"


def test_non_https_high_score_still_critical():
    """Real scan signal (non-HTTPS, high score) must remain CRITICAL."""
    obj = PostFilter(PostFilterConfig())
    for score in (5.0, 24.0, 1000.0):
        sev = obj.severity_for({"dst_port": 8080}, score)
        assert sev == "CRITICAL", f"non-https score={score} -> {sev}"


def test_https_small_score_ranges():
    """HTTPS with modest scores maps to LOW/MEDIUM normally."""
    obj = PostFilter(PostFilterConfig())
    assert obj.severity_for({"dst_port":443}, 3.0) == "LOW"
    assert obj.severity_for({"dst_port":443}, 3.5) == "LOW"
    assert obj.severity_for({"dst_port":443}, 4.0) == "MEDIUM"
