#!/usr/bin/env python3
"""
Tests básicos para QZero
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test que todos los módulos se pueden importar"""
    print("Testing imports...")

    try:
        from qzero.config import QZeroConfig, setup_logging
        print("✅ qzero.config")
    except Exception as e:
        print(f"❌ qzero.config: {e}")
        return False

    try:
        from qzero.cli import PCAPAnalyzer, analyze_pcap
        print("✅ qzero.cli.analyzer")
    except Exception as e:
        print(f"❌ qzero.cli.analyzer: {e}")
        return False

    try:
        from qzero.cli import NetworkMonitor, start_monitor
        print("✅ qzero.cli.monitor")
    except Exception as e:
        print(f"❌ qzero.cli.monitor: {e}")
        return False

    try:
        from qzero.cli import DaemonManager
        print("✅ qzero.cli.daemon")
    except Exception as e:
        print(f"❌ qzero.cli.daemon: {e}")
        return False

    try:
        from qzero.cli import QZeroTrainer, train_model
        print("✅ qzero.cli.trainer")
    except Exception as e:
        print(f"❌ qzero.cli.trainer: {e}")
        return False

    return True


def test_config():
    """Test que la configuración funciona"""
    print("\nTesting config...")

    try:
        from qzero.config import QZeroConfig

        config = QZeroConfig()
        output_dir = config.get("output_dir")

        print(f"✅ Config loaded. Output dir: {output_dir}")

        # Probar getters y setters
        config.set("test_key", "test_value")
        value = config.get("test_key")
        assert value == "test_value", "Set/get failed"
        print("✅ Config get/set works")

        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


def test_analyzer():
    """Test que el analizador funciona"""
    print("\nTesting analyzer...")

    try:
        from qzero.cli import PCAPAnalyzer
        from pathlib import Path

        # Crear un PCAP simulado
        test_pcap = Path("test.pcap")
        test_pcap.write_bytes(b"FAKEDATA")

        analyzer = PCAPAnalyzer(str(test_pcap), output_dir="test_reports")
        results = analyzer.analyze()

        assert "timestamp" in results
        assert "anomalies" in results
        print(f"✅ Analyzer works. Found {len(results['anomalies'])} anomalies")

        # Limpiar
        test_pcap.unlink(missing_ok=True)

        return True
    except Exception as e:
        print(f"❌ Analyzer test failed: {e}")
        return False


def main():
    """Ejecutar todos los tests"""
    print("="*60)
    print("QZero Tests")
    print("="*60)

    results = []

    results.append(test_imports())
    results.append(test_config())
    results.append(test_analyzer())

    print("\n" + "="*60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("="*60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*60)
        return 1


if __name__ == '__main__':
    sys.exit(main())