"""
F3 — Threshold calibration for QZero.

Instead of the hardcoded `alert_threshold` (4.2 in AgentConfig, 0.5 in the CLI
default — an inconsistency that made thresholding meaningless), this script
runs the fitted model over a corpus of KNOWN-BENIGN traffic (or the captured
baseline PCAPs) and reports the score distribution. You then set the alert
threshold to a high percentile (e.g. p99.9) of the benign scores.

Usage:
    python -m qzero.preprocessing.calibrate_threshold \
        --model-dir /path/to/models \
        --pcaps /path/to/benign/*.pcap \
        --percentile 99.9

Prints mean/std/p50/p90/p99/p99.9/p100 of benign anomaly scores plus a
recommended threshold.
"""

from __future__ import annotations

import argparse
import glob
import logging
from pathlib import Path
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


def collect_scores(model_dir: str, pcap_paths: List[str], method: str = "best") -> np.ndarray:
    """Run the fitted predictor over benign PCAPs and collect per-flow scores."""
    from qzero import QZero
    from qzero.core.detector import NetworkTrafficAnalyzer

    qzero = QZero()
    qzero.load(model_dir)
    analyzer = NetworkTrafficAnalyzer(predictor=qzero.predictor)

    scores: List[float] = []
    for path in pcap_paths:
        result = analyzer.analyze(path, method=method)
        res = result.get("results", {})
        batch = res.get("anomaly_scores", [])
        scores.extend(float(s) for s in batch)
        logger.info("%s: %d flows → %d scores", path, result.get("flows_extracted", 0), len(batch))

    return np.asarray(scores, dtype=float)


def recommend_threshold(scores: np.ndarray, percentile: float = 99.9) -> dict:
    if scores.size == 0:
        raise ValueError("No scores collected — nothing to calibrate against.")

    qs = {p: float(np.percentile(scores, p)) for p in [50, 90, 95, 99, percentile, 100]}
    return {
        "n_scores": int(scores.size),
        "mean": float(scores.mean()),
        "std": float(scores.std()),
        "percentiles": qs,
        "recommended_threshold": qs[percentile],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate QZero alert threshold")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--pcaps", required=True, help="Comma-separated or glob of benign PCAPs")
    parser.add_argument("--percentile", type=float, default=99.9)
    parser.add_argument("--method", default="best")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    paths = []
    for pat in args.pcaps.split(","):
        pat = pat.strip()
        paths.extend(glob.glob(pat) if any(c in pat for c in "*?[") else [pat])

    if not paths:
        logger.error("No PCAP files matched.")
        return

    scores = collect_scores(args.model_dir, paths, args.method)
    report = recommend_threshold(scores, args.percentile)

    print("\n=== Threshold calibration report ===")
    print(f"Scores evaluated : {report['n_scores']}")
    print(f"Mean / Std       : {report['mean']:.3f} / {report['std']:.3f}")
    for p, v in report["percentiles"].items():
        print(f"  p{p:<6}: {v:.3f}")
    print(f"\nRecommended alert_threshold = {report['recommended_threshold']:.3f}")
    print("Set it via env QZERO_ALERT_THRESHOLD or the --threshold CLI arg.")


if __name__ == "__main__":
    main()
