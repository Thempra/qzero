#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio
import argparse
from datetime import datetime
import json


def cmd_batch(config: argparse.Namespace):
    """Run batch analysis on multiple files."""
    from detection import PCAPHandler, QZeroDetector
    from src.predictor import QZeroPredictor

    print(f"\n{'='*60}")
    print("QZero Batch Analysis")
    print(f"{'='*60}\n")

    # Expand input files (support wildcards)
    input_files = []
    for pattern in config.input_files:
        files = list(Path('.').glob(pattern))
        if not files:
            print(f"Warning: No files found matching: {pattern}")
        input_files.extend(files)

    if not input_files:
        print("Error: No input files specified")
        sys.exit(1)

    print(f"Found {len(input_files)} file(s) to analyze\n")

    # Initialize predictor once for efficiency
    if config.model == 'qivae':
        predictor = QZeroPredictor(
            n_qubits=config.n_qubits,
            use_qsvm=False,
            use_qivae=True,
            use_classical=False,
        )
        print(f"Model: QI-VAE ({config.n_qubits} qubits)")
    elif config.model == 'classical':
        predictor = QZeroPredictor(
            n_qubits=config.n_qubits,
            use_qsvm=False,
            use_qivae=False,
            use_classical=True,
        )
        print(f"Model: Classical baselines")
    else:
        print(f"Model: {config.model}")
        predictor = None

    # Analyze each file
    all_results = []
    total_anomalies = 0
    total_samples = 0

    for i, file_path in enumerate(input_files, 1):
        print(f"[{i}/{len(input_files)}] Analyzing: {file_path.name}")

        async def analyze_file():
            handler = PCAPHandler() if file_path.suffix == '.pcap' else None
            if not handler:
                handler = type('Handler', (), {})()  # Dummy handler
            
            detector = QZeroDetector()
            detector.predictor = predictor
            detector.add_stream_handler(handler)
            await detector.process_stream(handler, max_samples=config.max_samples)
            stats = detector.get_statistics()
            
            return {
                'file': str(file_path),
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'statistics': {
                    'total_samples': stats.get('total_samples', 0),
                    'anomalies': stats.get('anomalies_detected', 0),
                    'anomaly_rate': stats.get('anomaly_rate', 0.0),
                    'mean_score': stats.get('mean_anomaly_score', 0.0),
                    'max_score': stats.get('max_anomaly_score', 0.0),
                    'critical_alerts': stats.get('critical_alerts', 0),
                },
            }

        try:
            result = asyncio.run(analyze_file())
            all_results.append(result)

            if result['status'] == 'success':
                total_samples += result['statistics']['total_samples']
                total_anomalies += result['statistics']['anomalies']

                if result['statistics']['critical_alerts'] > 0:
                    print(f"  ⚠️  {result['statistics']['critical_alerts']} critical alerts")
                else:
                    print(f"  ✓ Complete")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

            print()

        except Exception as e:
            print(f"  ✗ Failed: {e}\n")
            all_results.append({
                'file': str(file_path),
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            })

    # Summary
    print(f"{'='*60}")
    print("Batch Analysis Summary")
    print(f"{'='*60}")
    print(f"Total files processed: {len(all_results)}")
    print(f"Total samples analyzed: {total_samples}")
    print(f"Total anomalies found: {total_anomalies}")
    if total_samples > 0:
        print(f"Overall anomaly rate: {total_anomalies/total_samples:.2%}")
    else:
        print(f"Overall anomaly rate: 0.00%")
    print(f"{'='*60}\n")

    # Save results
    if config.output_file:
        print(f"Saving results to {config.output_file}...")
        output = {
            'summary': {
                'total_files': len(all_results),
                'total_samples': total_samples,
                'total_anomalies': total_anomalies,
                'overall_anomaly_rate': total_anomalies/total_samples if total_samples > 0 else 0,
            },
            'files': all_results,
            'timestamp': datetime.now().isoformat(),
        }
        with open(config.output_file, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Saved!\n")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="QZero Batch Analysis - Process multiple PCAP or log files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single file
  python qzero-cli-batch.py -f suspicious.pcap --model qivae

  # Analyze multiple files with wildcard
  python qzero-cli-batch.py -f *.pcap --model classical

  # Analyze with custom parameters
  python qzero-cli-batch.py -f suspicious.pcap -n 32 --output results.json
        """
    )

    parser.add_argument(
        '-f', '--files',
        nargs='+',
        required=True,
        help='Input file(s) to analyze (supports wildcards: *.pcap)'
    )

    parser.add_argument(
        '--model',
        choices=['qivae', 'classical', 'hybrid'],
        default='qivae',
        help='Model to use for analysis (default: qivae)'
    )

    parser.add_argument(
        '-n', '--n-qubits',
        type=int,
        default=32,
        help='Number of qubits for quantum models (default: 32)'
    )

    parser.add_argument(
        '-m', '--max-samples',
        type=int,
        default=1000,
        help='Maximum samples to process per file (default: 1000)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default='batch_results.json',
        help='Output JSON file for results (default: batch_results.json)'
    )

    args = parser.parse_args()
    cmd_batch(args)


if __name__ == "__main__":
    main()
