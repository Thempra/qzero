#!/usr/bin/env python3
"""
Tests para CLI de QZero
"""

import sys
import argparse
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_sniffer_cli():
    """Test del CLI de sniffer"""
    print("Testing sniffer CLI...")

    try:
        from qzero.cli.sniffer import RealTimeSniffer, list_interfaces

        # Test que list_interfaces funciona
        list_interfaces()

        print("✅ Sniffer CLI works")

        return True
    except Exception as e:
        print(f"❌ Sniffer CLI test failed: {e}")
        return False


def test_pipeline_cli():
    """Test del CLI de pipeline"""
    print("\nTesting pipeline CLI...")

    try:
        from qzero.cli.pipeline import MemoryPipelineCLI

        print("✅ Pipeline CLI importable")

        return True
    except Exception as e:
        print(f"❌ Pipeline CLI test failed: {e}")
        return False


def test_inference_cli():
    """Test del CLI de inference"""
    print("\nTesting inference CLI...")

    try:
        from qzero.cli.inference import cmd_inference_stats

        # Test con argumentos mínimos
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', '-m')
        parser.add_argument('--verbose', '-v', action='store_true')
        args = parser.parse_args([])

        # No debería fallar
        cmd_inference_stats(args)

        print("✅ Inference CLI works")

        return True
    except Exception as e:
        print(f"❌ Inference CLI test failed: {e}")
        return False


def test_response_cli():
    """Test del CLI de response"""
    print("\nTesting response CLI...")

    try:
        from qzero.cli.response import cmd_alerts_list, cmd_alerts_stats

        print("✅ Response CLI importable")

        return True
    except Exception as e:
        print(f"❌ Response CLI test failed: {e}")
        return False


def test_containers_cli():
    """Test del CLI de containers"""
    print("\nTesting containers CLI...")

    try:
        from qzero.cli.containers import cmd_containers_list

        print("✅ Containers CLI importable")

        return True
    except Exception as e:
        print(f"❌ Containers CLI test failed: {e}")
        return False


def test_cli_entrypoint():
    """Test del entrypoint del CLI"""
    print("\nTesting CLI entrypoint...")

    try:
        import subprocess
        result = subprocess.run(
            ["qzero", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        assert "QZero" in result.stdout
        assert "sniffer" in result.stdout.lower()

        print("✅ CLI entrypoint works")

        return True
    except Exception as e:
        print(f"❌ CLI entrypoint test failed: {e}")
        return False


def main():
    """Ejecutar todos los tests del CLI"""
    print("="*60)
    print("QZero CLI Tests")
    print("="*60)

    results = []

    results.append(test_sniffer_cli())
    results.append(test_pipeline_cli())
    results.append(test_inference_cli())
    results.append(test_response_cli())
    results.append(test_containers_cli())
    results.append(test_cli_entrypoint())

    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✅ ALL {total} CLI TESTS PASSED")
        print("="*60)
        return 0
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print(f"❌ {total - passed} tests failed")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())