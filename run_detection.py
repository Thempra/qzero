#!/usr/bin/env python3
"""
Example script for running QZero detection on different stream types.

Usage:
    python run_detection.py netflow
    python run_detection.py pcap
    python run_detection.py logs
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from detection import (
    DetectionStream,
    run_detection_stream,
    QZeroDetector,
    NetFlowHandler,
    PCAPHandler,
    LoggerHandler,
)


async def main():
    """Main function to run detection."""
    # Parse command line arguments
    if len(sys.argv) > 1:
        stream_arg = sys.argv[1].lower()
        if stream_arg == "netflow":
            stream_type = DetectionStream.NETFLOW
        elif stream_arg == "pcap":
            stream_type = DetectionStream.PCAP
        elif stream_arg == "logs":
            stream_type = DetectionStream.LOGS
        else:
            print(f"Unknown stream type: {stream_arg}")
            print("Usage: python run_detection.py [netflow|pcap|logs]")
            sys.exit(1)
    else:
        print("Using default stream type: netflow")
        stream_type = DetectionStream.NETFLOW

    print(f"\n{'='*60}")
    print(f"QZero Real-Time Detection")
    print(f"Stream Type: {stream_type.value.upper()}")
    print(f"{'='*60}\n")

    # Create detector
    detector = QZeroDetector()

    # Add handler based on stream type
    if stream_type == DetectionStream.NETFLOW:
        handler = NetFlowHandler()
        print("Handler: NetFlow (mock data)")
    elif stream_type == DetectionStream.PCAP:
        handler = PCAPHandler()
        print("Handler: PCAP (mock data)")
    elif stream_type == DetectionStream.LOGS:
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

        if stats['critical_alerts'] > 0:
            print(f"\n⚠️  CRITICAL ALERTS DETECTED!")
            print(f"   Review the alert log for details.\n")
        else:
            print(f"\n✓ No critical alerts detected.\n")

    except Exception as e:
        print(f"\n❌ Error during detection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())