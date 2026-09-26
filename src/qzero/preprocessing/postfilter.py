"""
F5 — Classical post-filtering to cut false positives.

The quantum models can still score benign traffic as anomalous (e.g. a single
TLS SYN to port 443 from a monitoring VM is statistically deviant on
per-packet features). This module applies deterministic, low-risk classical
rules on top of the model's per-flow anomaly scores to suppress alerts that
correspond to normal, expected behaviour.

Rules are conservative: each one requires a strong, well-understood signal.
The goal is to REDUCE false positives without introducing false negatives
(bad traffic slipping through).
"""

from __future__ import annotations

import ipaddress
from typing import Dict, List, Optional

logger = __import__("logging").getLogger(__name__)


class PostFilterConfig:
    """Tunable knobs for the classical post-filter."""

    def __init__(
        self,
        whitelist_dns: bool = True,
        whitelist_https_no_payload: bool = True,
        whitelist_local: bool = True,
        whitelist_private: bool = False,
        min_flow_bytes: int = 64,
        suppress_below_score: float = 0.0,
    ) -> None:
        # DNS (UDP/TCP 53) is overwhelmingly benign resolution traffic.
        self.whitelist_dns = whitelist_dns
        # Pure TLS handshakes / small HTTPS flows with no meaningful payload
        # (e.g. < min_flow_bytes) are normal monitoring/keepalive chatter.
        self.whitelist_https_no_payload = whitelist_https_no_payload
        # Link-local / multicast / loopback / documentation ranges.
        self.whitelist_local = whitelist_local
        # RFC1918 private ranges (10/8, 172.16/12, 192.168/16).
        # NOTE(2026-09): default is now False. Private-range is NOT a
        # benign signal in a network-monitoring context: an agent deployed
        # ON the LAN has a private source IP, and internal LAN scans (the
        # real threat an NDR sensor hunts) have private src AND dst.
        # Whitelisting private traffic suppressed 100%% of alerts and made
        # the hub report 0 detections. Disabled by default; opt in only in
        # a DMZ where the host has a public IP. See fix/postfilter-*
        self.whitelist_private = whitelist_private
        # Flows with total bytes below this are considered "no payload".
        self.min_flow_bytes = min_flow_bytes
        # Optional hard floor: never alert on scores below this value.
        self.suppress_below_score = suppress_below_score


class PostFilter:
    """Applies classical suppression rules to per-flow anomaly results."""

    def __init__(self, config: Optional[PostFilterConfig] = None) -> None:
        self.config = config or PostFilterConfig()

    def should_suppress(
        self,
        flow: Dict,
        score: float,
    ) -> tuple[bool, str]:
        """
        Decide whether a given flow's alert should be suppressed.

        Args:
            flow: dict with at least keys 'src_ip','dst_ip','src_port',
                  'dport'/'dst_port','proto','total_length_fwd_packets',
                  'total_length_bwd_packets', and optionally 'packets'.
            score: the model anomaly score for this flow.

        Returns:
            (suppress, reason): suppress=True means don't alert; reason is the
            human-readable explanation.
        """
        cfg = self.config

        if score < cfg.suppress_below_score:
            return True, f"score_below_floor({score:.3f})"

        src_ip = flow.get("src_ip", "")
        dst_ip = flow.get("dst_ip", "")
        sport = int(flow.get("src_port", flow.get("sport", 0)))
        dport = int(flow.get("dport", flow.get("dst_port", 0)))
        proto = int(flow.get("proto", 0))
        fwd_bytes = int(flow.get("total_length_fwd_packets", 0))
        bwd_bytes = int(flow.get("total_length_bwd_packets", 0))
        total_bytes = fwd_bytes + bwd_bytes

        # DNS is almost always benign resolution.
        if cfg.whitelist_dns and (dport == 53 or sport == 53):
            return True, "dns"

        # Local / multicast / loopback ranges.
        if cfg.whitelist_local and (
            self._is_local(dst_ip) or self._is_local(src_ip)
        ):
            return True, "local_or_multicast"

        # Private RFC1918 traffic.
        if cfg.whitelist_private and (
            self._is_private(dst_ip) or self._is_private(src_ip)
        ):
            return True, "private_rfc1918"

        # HTTPS / TLS flows with essentially no payload are normal chatter.
        if cfg.whitelist_https_no_payload and (dport == 443 or sport == 443):
            if total_bytes < cfg.min_flow_bytes:
                return True, "https_no_payload"

        return False, ""

    @staticmethod
    def _is_local(ip: str) -> bool:
        if not ip:
            return False
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return a.is_link_local or a.is_multicast or a.is_loopback or a.is_unspecified

    @staticmethod
    def _is_private(ip: str) -> bool:
        if not ip:
            return False
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return a.is_private

    def annotate(self, flow: Dict, score: float, default_suppress: bool = False) -> Dict:
        """Return the flow dict with suppression decision attached."""
        suppress, reason = self.should_suppress(flow, score)
        if default_suppress:
            suppress, reason = True, "model_no_fit" if not suppress else reason
        out = dict(flow)
        out["suppressed"] = bool(suppress)
        out["suppress_reason"] = reason
        return out
