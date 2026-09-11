#!/usr/bin/env python3
"""
QZero CLI — command-line interface for quantum threat detection.

Usage:
    qzero train   [options]   # Train models
    qzero analyze [options]   # Analyze a PCAP file
    qzero server  [options]   # Start REST API
    qzero monitor [options]   # Real-time traffic monitoring
"""

import sys
import json
import logging
from pathlib import Path

import click

from ..config import setup_logging


@click.group()
@click.version_option(package_name="qzero")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool):
    """QZero — Quantum-Algorithm-Based Threat Detection."""
    setup_logging(verbose=verbose)


@cli.command()
@click.option("--samples", "-n", default=5000, show_default=True, help="Synthetic training samples.")
@click.option("--real-data", is_flag=True, help="Use real UGRansome dataset.")
@click.option("--qubits", default=4, show_default=True, help="Number of qubits.")
@click.option("--save-dir", default=None, help="Directory to persist trained models.")
@click.option("--no-qsvm", is_flag=True, help="Skip QSVM training.")
@click.option("--no-qivae", is_flag=True, help="Skip QI-VAE training.")
def train(samples, real_data, qubits, save_dir, no_qsvm, no_qivae):
    """Train quantum anomaly-detection models."""
    from .. import QZero

    click.echo(f"Training QZero (qubits={qubits}, samples={samples}) …")

    qzero = QZero(n_qubits=qubits, use_qsvm=not no_qsvm, use_qivae=not no_qivae)
    result = qzero.train(n_samples=samples, use_real_data=real_data)

    click.echo(f"Training complete in {result.get('training_time', 0):.1f}s")

    if save_dir:
        qzero.save(save_dir)
        click.echo(f"Models saved to: {save_dir}")


@cli.command()
@click.argument("pcap_file", type=click.Path(exists=True))
@click.option("--method", "-m", default="best", show_default=True,
              type=click.Choice(["qsvm", "qivae", "best"]),
              help="Detection method.")
@click.option("--model-dir", default=None, help="Directory with pre-trained models.")
@click.option("--output", "-o", default=None, help="Save JSON results to this file.")
@click.option("--qubits", default=4, show_default=True, help="Number of qubits.")
def analyze(pcap_file, method, model_dir, output, qubits):
    """Analyze a PCAP file for anomalous traffic."""
    from .. import QZero

    qzero = QZero(n_qubits=qubits)

    if model_dir:
        click.echo(f"Loading models from: {model_dir}")
        qzero.load(model_dir)
    else:
        click.echo("No model dir specified — training on synthetic data first …")
        qzero.train(n_samples=2000)

    click.echo(f"Analyzing: {pcap_file} (method={method}) …")
    result = qzero.analyze_traffic(pcap_file, method=method)

    if result.get("status") == "success":
        r = result.get("results", {})
        click.echo(f"  Packets analyzed : {result['features_extracted']}")
        click.echo(f"  Anomalies found  : {r.get('n_anomalies_detected', 0)}")
        click.echo(f"  Anomaly rate     : {r.get('anomaly_percentage', 0):.1f}%")
    else:
        click.echo(f"Analysis failed: {result.get('message', 'unknown error')}", err=True)
        sys.exit(1)

    if output:
        Path(output).write_text(json.dumps(result, indent=2))
        click.echo(f"Results saved to: {output}")


@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, help="Bind port.")
@click.option("--model-dir", default=None, help="Directory with pre-trained models.")
@click.option("--qubits", default=4, show_default=True, help="Number of qubits.")
def server(host, port, model_dir, qubits):
    """Start the QZero REST API server."""
    import uvicorn
    from .. import QZero
    import qzero.api.app as _api

    qzero = QZero(n_qubits=qubits)
    if model_dir:
        click.echo(f"Loading models from: {model_dir}")
        qzero.load(model_dir)

    # Inject predictor into the API module
    _api._predictor = qzero.predictor

    click.echo(f"Starting QZero API  →  http://{host}:{port}")
    click.echo(f"Dashboard           →  http://{host}:{port}/dashboard")
    click.echo(f"WebSocket           →  ws://{host}:{port}/ws")
    uvicorn.run("qzero.api.app:app", host=host, port=port, reload=False)


@cli.command()
@click.option("--interface", "-i", default="eth0", show_default=True, help="Network interface.")
@click.option("--promiscuous", "-p", is_flag=True, help="Enable promiscuous mode (requires root).")
@click.option("--interval", default=10, show_default=True, help="Analysis interval in seconds.")
@click.option("--model-dir", default=None, help="Directory with pre-trained models.")
@click.option("--qubits", default=4, show_default=True, help="Number of qubits.")
def monitor(interface, promiscuous, interval, model_dir, qubits):
    """Monitor live network traffic for threats."""
    from .. import QZero
    from ..core.detector import NetworkTrafficAnalyzer

    qzero = QZero(n_qubits=qubits)
    if model_dir:
        click.echo(f"Loading models from: {model_dir}")
        qzero.load(model_dir)
    else:
        click.echo("Training on synthetic data before monitoring …")
        qzero.train(n_samples=2000)

    click.echo(
        f"Monitoring {interface} "
        f"({'promiscuous' if promiscuous else 'non-promiscuous'}) "
        f"— interval {interval}s"
    )
    click.echo("Press Ctrl-C to stop.\n")

    try:
        from scapy.all import sniff, wrpcap
        import tempfile
        import time

        analyzer = NetworkTrafficAnalyzer(predictor=qzero.predictor)

        while True:
            packets = sniff(iface=interface, promisc=promiscuous, timeout=interval)
            if not packets:
                continue

            with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as tmp:
                wrpcap(tmp.name, packets)
                result = analyzer.analyze(tmp.name)
                Path(tmp.name).unlink(missing_ok=True)

            r = result.get("results", {})
            ts = result.get("timestamp", "")[:19]
            n_pkt = result.get("features_extracted", 0)
            n_anom = r.get("n_anomalies_detected", 0)
            pct = r.get("anomaly_percentage", 0.0)

            status = "ALERT" if n_anom > 0 else "OK"
            click.echo(f"[{ts}] [{status}] packets={n_pkt}  anomalies={n_anom} ({pct:.1f}%)")

    except KeyboardInterrupt:
        click.echo("\nMonitoring stopped.")
    except ImportError:
        click.echo("Scapy not installed. Run: pip install scapy", err=True)
        sys.exit(1)


@cli.command()
@click.option("--interface", "-i", default="eth0", show_default=True, help="Network interface (default from QZERO_INTERFACE).")
@click.option("--promiscuous", "-p", is_flag=True, help="Enable promiscuous mode (requires root).")
@click.option("--interval", default=5.0, show_default=True, help="Capture window in seconds.")
@click.option("--hub-url", default=None, help="Central hub base URL, e.g. http://1.2.3.4:8000 (or QZERO_HUB_URL).")
@click.option("--agent-id", default=None, help="Agent identifier (default: hostname-interface).")
@click.option("--model-dir", default=None, help="Directory with pre-trained models.")
@click.option("--threshold", default=0.5, show_default=True, help="Anomaly score threshold for alerts.")
@click.option("--qubits", default=4, show_default=True, help="Number of qubits.")
def agent(interface, promiscuous, interval, hub_url, agent_id, model_dir, threshold, qubits):
    """Run real-time traffic monitoring as a deployable QZero agent (pushes alerts to a hub)."""
    import os
    from ..agent import QZeroAgent, AgentConfig

    config = AgentConfig(
        agent_id=agent_id or os.environ.get("QZERO_AGENT_ID", ""),
        interface=interface,
        promiscuous=promiscuous,
        interval=interval,
        hub_url=hub_url or os.environ.get("QZERO_HUB_URL", ""),
        model_dir=model_dir,
        n_qubits=qubits,
        alert_threshold=threshold,
    )

    click.echo("Starting QZero Agent …")
    if config.hub_url:
        click.echo(f"  → pushing alerts to hub: {config.hub_url}")
    else:
        click.echo("  → no hub configured: alerts will be spooled locally to ./qzero-alerts-*.jsonl")
    QZeroAgent(config).run()


if __name__ == "__main__":
    cli()
