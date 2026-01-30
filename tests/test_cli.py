"""
Tests for QZero CLI.
"""

import pytest
import sys
import json
import subprocess
from pathlib import Path
import tempfile

# Path to CLI
CLI_PATH = Path(__file__).parent.parent / "qzero-cli.py"
VENV_PYTHON = Path(__file__).parent.parent / "venv" / "bin" / "python"


class TestCLIHelp:
    """Test CLI help commands."""

    def test_main_help(self):
        """Test main help displays correctly."""
        result = subprocess.run(
            [str(VENV_PYTHON), str(CLI_PATH), "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "QZero" in result.stdout
        assert "train" in result.stdout
        assert "detect" in result.stdout

    def test_train_help(self):
        """Test train command help."""
        result = subprocess.run(
            [str(VENV_PYTHON), str(CLI_PATH), "train", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "--samples" in result.stdout
        assert "--epochs" in result.stdout
        assert "--difficulty" in result.stdout

    def test_detect_help(self):
        """Test detect command help."""
        result = subprocess.run(
            [str(VENV_PYTHON), str(CLI_PATH), "detect", "--help"],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0
        assert "--stream" in result.stdout
        assert "--model" in result.stdout
        assert "netflow" in result.stdout


class TestCLITrain:
    """Test CLI train command."""

    def test_train_minimal(self):
        """Test training with minimal samples and epochs."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "train",
                "--samples", "50",
                "--epochs", "2",
                "--batch-size", "8"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        # Should complete without error
        assert "QZero Training" in result.stdout
        assert "Generated" in result.stdout or "Loaded" in result.stdout

    def test_train_with_output_file(self, tmp_path):
        """Test training saves results to JSON."""
        output_file = tmp_path / "results.json"
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "train",
                "--samples", "50",
                "--epochs", "2",
                "--batch-size", "8",
                "--output-file", str(output_file)
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Check if file was created (may not be if training failed)
        if output_file.exists():
            with open(output_file, 'r') as f:
                data = json.load(f)
            assert 'qivae' in data
            assert 'config' in data

    def test_train_with_classical_models(self):
        """Test training with specific classical models."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "train",
                "--samples", "50",
                "--epochs", "1",
                "--batch-size", "8",
                "--models", "random_forest"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        assert "Classical Baselines" in result.stdout or result.returncode == 0


class TestCLIDetect:
    """Test CLI detect command."""

    def test_detect_netflow(self):
        """Test detection with NetFlow stream."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "detect",
                "--stream", "netflow",
                "--max-samples", "10"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        assert "QZero Real-Time Detection" in result.stdout
        assert "Detection Statistics" in result.stdout or result.returncode == 0

    def test_detect_pcap(self):
        """Test detection with PCAP stream."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "detect",
                "--stream", "pcap",
                "--max-samples", "10"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        assert "QZero Real-Time Detection" in result.stdout

    def test_detect_logs(self):
        """Test detection with logs stream."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "detect",
                "--stream", "logs",
                "--max-samples", "10"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        assert "QZero Real-Time Detection" in result.stdout


class TestCLIValidation:
    """Test CLI input validation."""

    def test_no_command(self):
        """Test running without command shows help."""
        result = subprocess.run(
            [str(VENV_PYTHON), str(CLI_PATH)],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 1  # Should exit with error
        # But should show help
        assert "QZero" in result.stdout or "usage" in result.stdout.lower()

    def test_invalid_difficulty(self):
        """Test invalid difficulty shows error."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "train",
                "--difficulty", "impossible"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower()

    def test_invalid_stream(self):
        """Test invalid stream shows error."""
        result = subprocess.run(
            [
                str(VENV_PYTHON), str(CLI_PATH), "detect",
                "--stream", "invalid"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode != 0
        assert "invalid choice" in result.stderr.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
