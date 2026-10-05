"""
Flow-based feature extraction for QZero.

Converts raw Scapy packets into aggregated flow records whose feature set is
IDENTICAL to the one the models are trained on (UGRANSOME_FEATURES from
qzero.preprocessing.data_loader). This fixes the root cause of the false
positive storm: the inference path used to extract 6 per-packet features
(src_ip_sum, dst_ip_sum, protocol, src_port, dst_port, packet_size) while the
model was trained on 14 flow-level features, then padded/truncated the columns
to force a dimension match — feeding the model completely out-of-distribution
data that scored almost everything as anomalous.

With this extractor, training and inference share the same feature space, so
the quantum models operate on real traffic semantics (durations, packet/byte
counts, inter-arrival times, flag counts) instead of synthetic per-packet noise.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Feature columns produced by this extractor (in order) — MUST match
# UGRANSOME_FEATURES in qzero/preprocessing/data_loader.py
FLOW_FEATURES = [
    "flow_duration",
    "total_fwd_packets",
    "total_bwd_packets",
    "total_length_fwd_packets",
    "total_length_bwd_packets",
    "flow_bytes_per_sec",
    "flow_packets_per_sec",
    "fwd_packet_length_mean",
    "bwd_packet_length_mean",
    "fwd_iat_mean",
    "bwd_iat_mean",
    "fwd_psh_flags",
    "bwd_psh_flags",
    "fwd_urg_flags",
]

# Guaranteed column order / count for training/inference consistency
FLOW_FEATURE_COUNT = len(FLOW_FEATURES)
# ----------------------------------------------------------------------
# Hard caps for rate-derived features.
# A short flow (e.g. a single nmap SYN, duration~0) can otherwise yield
# astronomically large bytes_per_sec / packets_per_sec that blow up the
# QI-VAE reconstruction error to ~1.9e9 and flood the hub with bogus
# CRITICAL alerts. These caps bound the rate features to physically
# meaningful maxima: 1 GiB/s bytes and 100k pkt/s.
MAX_FLOW_BYTES_PER_SEC = 1_073_741_824  # 1 GiB/s
MAX_FLOW_PACKETS_PER_SEC = 100_000      # 100k pkt/s


# Direction buckets
_FWD = "fwd"
_BWD = "bwd"


def _make_key(src_ip: str, sport: int, dst_ip: str, dport: int, proto: int) -> Tuple:
    """Build a directionless 5-tuple key, flattened to a sortable tuple."""
    return (src_ip, sport, dst_ip, dport, proto)


def _reverse_key(key: Tuple) -> Tuple:
    """The same flow with src/dst swapped (used to match reverse packets)."""
    src_ip, sport, dst_ip, dport, proto = key
    return (dst_ip, dport, src_ip, sport, proto)


class FlowExtractor:
    """
    Aggregate Scapy packets into bidirectional flows and compute UGRansome-style
    flow features.

    A flow is identified by the directionless 5-tuple (src_ip, src_port,
    dst_ip, dst_port, proto). The forward direction is anchored at the FIRST
    packet seen for that flow; packets arriving with swapped src/dst count as
    backward. This gives consistent, meaningful fwd/bwd statistics.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_flows_from_packets(self, packets: List) -> pd.DataFrame:
        """Return a flow-features DataFrame, one row per bidirectional flow."""
        flows = self._aggregate(packets)
        return self._to_dataframe(flows)

    def extract_flows_with_ids(self, packets: List) -> Tuple[pd.DataFrame, List[Tuple]]:
        """Like extract_flows_from_packets but also returns the flow key per row."""
        flows = self._aggregate(packets)
        df = self._to_dataframe(flows)
        flow_ids = list(flows.keys())
        return df, flow_ids

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _aggregate(self, packets: List) -> Dict[Tuple, dict]:
        acc: Dict[Tuple, dict] = {}

        for pkt in packets:
            parsed = self._parse_packet(pkt)
            if parsed is None:
                continue
            src_ip, dst_ip, sport, dport, proto, ts, iplen, psh, urg = parsed

            # Normalize direction: canonical key uses smaller (ip,port) first-seen.
            # We anchor direction on the first packet of the *conversation*.
            # Track both orientations mapping to the same canonical accumulator.
            can_key = self._canonical_key(src_ip, sport, dst_ip, dport, proto, acc)

            if can_key is None:
                can_key = _make_key(src_ip, sport, dst_ip, dport, proto)
                acc[can_key] = self._new_flow(ts, src_ip, sport, dst_ip, dport, proto)
                direction = _FWD
            else:
                entry_src = acc[can_key]["src_ip"]
                entry_sport = acc[can_key]["sport"]
                matches_forward = (src_ip == entry_src and sport == entry_sport)
                direction = _FWD if matches_forward else _BWD

            a = acc[can_key]
            self._add_packet(a, ts, iplen, psh, urg, direction)

        return acc

    def _canonical_key(self, src_ip, sport, dst_ip, dport, proto, acc) -> Optional[Tuple]:
        """Return the existing canonical key for this packet if the flow is known."""
        fwd = _make_key(src_ip, sport, dst_ip, dport, proto)
        if fwd in acc:
            return fwd
        rev = _reverse_key(fwd)
        if rev in acc:
            return rev
        return None

    @staticmethod
    def _new_flow(start_ts, src_ip, sport, dst_ip, dport, proto) -> dict:
        return {
            "src_ip": src_ip,
            "sport": sport,
            "dst_ip": dst_ip,
            "dport": dport,
            "proto": proto,
            "start": start_ts,
            "end": start_ts,
            "fwd_packets": 0,
            "bwd_packets": 0,
            "fwd_bytes": 0,
            "bwd_bytes": 0,
            "fwd_lens": [],
            "bwd_lens": [],
            "fwd_iat": [],
            "bwd_iat": [],
            "fwd_psh": 0,
            "bwd_psh": 0,
            "fwd_urg": 0,
            "last_fwd_ts": None,
            "last_bwd_ts": None,
        }

    @staticmethod
    def _add_packet(a: dict, ts: float, iplen: int, psh: bool, urg: bool, direction: str):
        a["end"] = max(a["end"], ts)
        a["start"] = min(a["start"], ts)

        if direction == _FWD:
            a["fwd_packets"] += 1
            a["fwd_bytes"] += iplen
            a["fwd_lens"].append(iplen)
            a["fwd_psh"] += int(psh)
            a["fwd_urg"] += int(urg)
            if a["last_fwd_ts"] is not None:
                a["fwd_iat"].append(ts - a["last_fwd_ts"])
            a["last_fwd_ts"] = ts
        else:
            a["bwd_packets"] += 1
            a["bwd_bytes"] += iplen
            a["bwd_lens"].append(iplen)
            a["bwd_psh"] += int(psh)
            if a["last_bwd_ts"] is not None:
                a["bwd_iat"].append(ts - a["last_bwd_ts"])
            a["last_bwd_ts"] = ts

    @staticmethod
    def _parse_packet(pkt) -> Optional[Tuple]:
        """Extract (src_ip, dst_ip, sport, dport, proto, ts, iplen, psh, urg)."""
        try:
            from scapy.all import IP, TCP, UDP

            if not pkt.haslayer(IP):
                return None

            ip = pkt[IP]
            src_ip = ip.src
            dst_ip = ip.dst
            proto = int(ip.proto)

            sport = dport = 0
            psh = urg = False
            if pkt.haslayer(TCP):
                sport = int(pkt[TCP].sport)
                dport = int(pkt[TCP].dport)
                flags = int(pkt[TCP].flags)
                psh = bool(flags & 0x08)  # PSH
                urg = bool(flags & 0x20)  # URG
            elif pkt.haslayer(UDP):
                sport = int(pkt[UDP].sport)
                dport = int(pkt[UDP].dport)

            # ip.len es None en paquetes recién construidos (sin serializar):
            # usar el tamaño serializado como fallback en ese caso.
            iplen = len(bytes(pkt))
            if ip.len is not None:
                iplen = max(int(ip.len), iplen)
            ts = float(getattr(pkt, "time", 0.0))

            return (src_ip, dst_ip, sport, dport, proto, ts, iplen, psh, urg)
        except Exception as e:  # noqa: BLE001 — skip malformed packets
            logger.debug("Packet parse skipped: %s", e)
            return None

    # ------------------------------------------------------------------
    # DataFrame conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dataframe(flows: Dict[Tuple, dict]) -> pd.DataFrame:
        rows = []
        for key, a in flows.items():
            duration = max(a["end"] - a["start"], 1e-9)
            total_pkts = a["fwd_packets"] + a["bwd_packets"]
            total_bytes = a["fwd_bytes"] + a["bwd_bytes"]

            fwd_len_mean = _safe_mean(a["fwd_lens"])
            bwd_len_mean = _safe_mean(a["bwd_lens"])
            fwd_iat_mean = _safe_mean(a["fwd_iat"])
            bwd_iat_mean = _safe_mean(a["bwd_iat"])

            rows.append(
                {
                    "flow_duration": round(duration * 1000, 3),  # ms
                    "total_fwd_packets": a["fwd_packets"],
                    "total_bwd_packets": a["bwd_packets"],
                    "total_length_fwd_packets": a["fwd_bytes"],
                    "total_length_bwd_packets": a["bwd_bytes"],
                    "flow_bytes_per_sec": round(min(total_bytes / duration, MAX_FLOW_BYTES_PER_SEC), 3),
                    "flow_packets_per_sec": round(min(total_pkts / duration, MAX_FLOW_PACKETS_PER_SEC), 3),
                    "fwd_packet_length_mean": round(fwd_len_mean, 3),
                    "bwd_packet_length_mean": round(bwd_len_mean, 3),
                    "fwd_iat_mean": round(fwd_iat_mean, 3),
                    "bwd_iat_mean": round(bwd_iat_mean, 3),
                    "fwd_psh_flags": a["fwd_psh"],
                    "bwd_psh_flags": a["bwd_psh"],
                    "fwd_urg_flags": a["fwd_urg"],
                }
            )

        df = pd.DataFrame(rows, columns=FLOW_FEATURES)
        df = df.fillna(0.0)
        return df


def _safe_mean(values: List[float]) -> float:
    return float(np.mean(values)) if values else 0.0
