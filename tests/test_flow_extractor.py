"""Tests for the flow-level feature extractor (F1: fixes FP root cause)."""

import pytest

from qzero.preprocessing.flow_extractor import (
    FLOW_FEATURES,
    FLOW_FEATURE_COUNT,
    FlowExtractor,
)

# List of the 14 UGRansome training features — the contract with data_loader.
EXPECTED = [
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


def _make_packet(src, dst, sport, dport, proto=6, ts=0.0, flags="S", iplen=1500):
    """Build a minimal scapy packet (both direction orderings work)."""
    from scapy.all import IP, TCP, UDP, Ether
    from scapy.layers.inet import UDP as _UDP

    base = Ether() / IP(src=src, dst=dst)
    if proto == 17:
        pkt = base / UDP(sport=sport, dport=dport)
    else:
        pkt = base / TCP(sport=sport, dport=dport, flags=flags)
    pkt.time = ts
    return pkt


class TestFeatureContract:
    def test_exactly_14_ugransome_features(self):
        assert FLOW_FEATURE_COUNT == 14
        assert FLOW_FEATURES == EXPECTED
        # Same set as training loader (sanity, mirrored here)
        from qzero.preprocessing.data_loader import UGRANSOME_FEATURES

        assert set(FLOW_FEATURES) == set(UGRANSOME_FEATURES)


class TestAggregation:
    def test_single_bidirectional_flow(self):
        packets = [
            _make_packet("10.0.0.1", "10.0.0.2", 12345, 443, ts=0.0),
            _make_packet("10.0.0.2", "10.0.0.1", 443, 12345, ts=1.0),
        ]
        df = FlowExtractor().extract_flows_from_packets(packets)
        assert len(df) == 1
        row = df.iloc[0]
        assert row["total_fwd_packets"] == 1
        assert row["total_bwd_packets"] == 1
        assert row["fwd_psh_flags"] == 0
        assert row["bwd_psh_flags"] == 0
        # Duration in ms
        assert row["flow_duration"] == pytest.approx(1000.0, abs=1.0)

    def test_two_distinct_flows(self):
        packets = [
            _make_packet("10.0.0.1", "10.0.0.2", 12345, 443, ts=0.0),
            _make_packet("10.0.0.3", "10.0.0.4", 54321, 80, ts=0.0),
        ]
        df = FlowExtractor().extract_flows_from_packets(packets)
        assert len(df) == 2

    def test_psh_flags_aggregated_forward(self):
        packets = [
            _make_packet("10.0.0.1", "10.0.0.2", 12345, 443, ts=0.0, flags="PA"),
            _make_packet("10.0.0.1", "10.0.0.2", 12345, 443, ts=0.1, flags="PA"),
        ]
        df = FlowExtractor().extract_flows_from_packets(packets)
        row = df.iloc[0]
        assert row["fwd_psh_flags"] == 2
        assert row["bwd_psh_flags"] == 0

    def test_reverse_direction_bucket(self):
        # First packet anchors forward; reverse packets go to backward bucket.
        packets = [
            _make_packet("10.0.0.1", "10.0.0.2", 12345, 443, ts=0.0),
            _make_packet("10.0.0.2", "10.0.0.1", 443, 12345, ts=0.5, flags="PA"),
        ]
        df = FlowExtractor().extract_flows_from_packets(packets)
        row = df.iloc[0]
        assert row["total_fwd_packets"] == 1
        assert row["total_bwd_packets"] == 1
        assert row["fwd_psh_flags"] == 0
        # Backward packet has PSH -> bwd_psh_flags == 1
        assert row["bwd_psh_flags"] == 1

    def test_flows_empty_input(self):
        df = FlowExtractor().extract_flows_from_packets([])
        assert len(df) == 0


class TestDetectorIntegration:
    """Guard: detector must produce UGRansome features, not per-packet ones."""

    def test_analyzer_uses_flow_extractor(self):
        from qzero.core.detector import NetworkTrafficAnalyzer

        # The analyzer's _extract_features should reference FlowExtractor and
        # never produce per-packet columns like src_ip_sum.
        import inspect

        src = inspect.getsource(NetworkTrafficAnalyzer._extract_features)
        assert "FlowExtractor" in src
        assert "src_ip_sum" not in src
