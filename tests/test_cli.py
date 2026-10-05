#!/usr/bin/env python3
"""
Tests para CLI de QZero (click). Estilo pytest: fallos reales, sin try/except
que los trague (S5779).
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Añadir src al path (para ejecución sin instalar el paquete)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture()
def cli_group():
    from qzero.cli.main import cli

    return cli


def test_cli_group_commands(cli_group):
    """El grupo CLI registra todos los subcomandos."""
    expected = {"train", "analyze", "server", "monitor", "agent"}
    assert expected <= set(cli_group.commands)


def test_cli_train_help(cli_group):
    """`qzero train --help` describe sus opciones."""
    from click.testing import CliRunner

    result = CliRunner().invoke(cli_group, ["train", "--help"])

    assert result.exit_code == 0
    assert "--samples" in result.output


def test_cli_analyze_requires_pcap(cli_group):
    """`qzero analyze` sin PCAP sale con error de uso."""
    from click.testing import CliRunner

    result = CliRunner().invoke(cli_group, ["analyze"])

    assert result.exit_code != 0


def test_cli_entrypoint():
    """El entrypoint `qzero --help` responde con el uso esperado."""
    exe = shutil.which("qzero")
    if exe is None:
        pytest.skip("binario qzero no instalado en PATH")

    result = subprocess.run(
        [str(exe), "--help"], capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 0
    assert "Usage" in result.stdout or "qzero" in result.stdout.lower()
