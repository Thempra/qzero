#!/usr/bin/env python3
"""
Standalone QZero detection demo.

This script demonstrates detection without using the predictor,
using a simple heuristic-based approach.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from detection import (
    DetectionStream,
    DetectionResult,
    QZeroDetector,
    NetFlowHandler,
    PCAPHandler,
    LoggerHandler,
)


def simple_anomaly_detector(features):
    """
    Simple anomaly detector using feature thresholds.

    In production, this would use trained ML models.
    """
    # Simple heuristics
    byte_ratio = features[0] / (features[1] + 1)  # bytes_sent / bytes_recv
    duration = features[4]
    port_diff = abs(features[6]) if len(features) > 6 else 0

    # Anomaly thresholds
    score = 0.0

    # High byte ratio (possible exfiltration)
    if byte_ratio > 10:
        score += 0.4
    elif byte_ratio > 5:
        score += 0.2

    # Long duration
    if duration > 60:
        score += 0.2
    elif duration > 30:
        score += 0.1

    # Large port difference
    if port_diff > 1000:
        score += 0.1

    # Random noise
    score += 0.1

    return min(score, 1.0)


async def run_detection():
    """Run detection demo."""
    import argparse

    parser = argparse.ArgumentParser(description="QZero Detection Demo")
    parser.add_argument(
        "stream_type",
        choices=["netflow", "pcap", "logs"],
        default="netflow",
        help="Type of stream to process"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("QZero Detection Demo")
    print(f"Stream Type: {args.stream_type.upper()}")
    print(f"{'='*60}\n")

    # Create detector
    detector = QZeroDetector()

    # Add handler based on stream type
    if args.stream_type == "netflow":
        handler = NetFlowHandler()
        print("Handler: NetFlow (mock data)")
    elif args.stream_type == "pcap":
        handler = PCAPHandler()
        print("Handler: PCAP (mock data)")
    elif args.stream_type == "logs":
        handler = LoggerHandler()
        print("Handler: Logs (mock data)")

    detector.add_stream_handler(handler)

    # Process stream
    max_samples = 100
    print(f"\nProcessing {max_samples} samples...")

    try:
        results = await detector.process_stream(handler, max_samples=max_samples)
        stats = detector.get_statistics()

        print(f"\n{'='*60}")
        print("Detection Statistics")
        print(f"{'='*60}")
        print(f"Total samples:     {stats['total_samples']}")
        print(f"Anomalies:         {stats['anomalies_detected']}")
        print(f"Anomaly rate:      {stats['anomaly_rate']:.2%}")
        print(f"Mean score:        {stats['mean_anomaly_score']:.3f}")
        print(f"Max score:         {stats['max_anomaly_score']:.3f}")
        print(f"Critical alerts:   {stats['critical_alerts']}")
        print(f"{'='*60}")

        # Show sample results
        print(f"\n{'='*60}")
        print("Sample Results")
        print(f"{'='*60}")

        for i, result in enumerate(detector.current_results[:10]):
            print(f"Sample {i+1:2d}: score={result.anomaly_score:5.2f} "
                  f"severity={result.severity:6s} "
                  f"anomaly={result.is_anomaly}")

        print(f"{'='*60}\n")

        if stats['critical_alerts'] > 0:
            print(f"⚠️  CRITICAL ALERTS DETECTED!")
            print(f"   Review the alert log for details.\n")
        else:
            print(f"✓ No critical alerts detected.\n")

    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_detection())