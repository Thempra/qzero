#!/usr/bin/env python3
"""
Tests completos para QZero - FASE 3
"""

import sys
from pathlib import Path
import tempfile
import time

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_sniffer_imports():
    """Test que los módulos del sniffer se pueden importar"""
    print("Testing sniffer imports...")

    try:
        from qzero.sniffer import (
            ScapySniffer,
            TcpDumpSniffer,
            BaseSniffer,
            RealTimeSniffer,
            NetworkInterface,
            Packet,
            InterfaceType
        )
        print("✅ qzero.sniffer.all_imports")
        return True
    except Exception as e:
        print(f"❌ qzero.sniffer imports failed: {e}")
        return False


def test_pipeline_imports():
    """Test que los módulos del pipeline se pueden importar"""
    print("\nTesting pipeline imports...")

    try:
        from qzero.pipeline import (
            RingBuffer,
            Packet,
            PacketType,
            PacketBatch,
            PacketProcessor,
            MemoryEfficientSniffer
        )
        print("✅ qzero.pipeline.all_imports")
        return True
    except Exception as e:
        print(f"❌ qzero.pipeline imports failed: {e}")
        return False


def test_inference_imports():
    """Test que los módulos de inferencia se pueden importar"""
    print("\nTesting inference imports...")

    try:
        from qzero.inference import (
            InferenceEngine,
            FastInferencePipeline
        )
        print("✅ qzero.inference.all_imports")
        return True
    except Exception as e:
        print(f"❌ qzero.inference imports failed: {e}")
        return False


def test_response_imports():
    """Test que los módulos de respuesta se pueden importar"""
    print("\nTesting response imports...")

    try:
        from qzero.response import (
            Alert,
            AlertLevel,
            AlertType,
            AlertManager,
            ResponseEngine
        )
        print("✅ qzero.response.all_imports")
        return True
    except Exception as e:
        print(f"❌ qzero.response imports failed: {e}")
        return False


def test_containers_imports():
    """Test que los módulos de contenedores se pueden importar"""
    print("\nTesting containers imports...")

    try:
        from qzero.containers import (
            ContainerMonitor,
            ContainerIntegration,
            ContainerType
        )
        print("✅ qzero.containers.all_imports")
        return True
    except Exception as e:
        print(f"❌ qzero.containers imports failed: {e}")
        return False


def test_ring_buffer():
    """Test del Ring Buffer"""
    print("\nTesting Ring Buffer...")

    try:
        from qzero.pipeline import RingBuffer

        buffer = RingBuffer(max_size=100)

        # Agregar paquetes
        packet = Packet(
            timestamp=time.time(),
            source="192.168.1.1",
            destination="10.0.0.1",
            protocol="TCP",
            size=100,
            payload=b"test"
        )

        for i in range(50):
            buffer.add_packet(packet)

        # Obtener stats
        stats = buffer.get_stats()
        assert stats['current_size'] == 50
        assert stats['max_size'] == 100
        assert stats['usage_percent'] == 50

        print(f"✅ Ring Buffer works. Size: {stats['current_size']}, Usage: {stats['usage_percent']}%")

        return True
    except Exception as e:
        print(f"❌ Ring Buffer test failed: {e}")
        return False


def test_packet_processor():
    """Test del Packet Processor"""
    print("\nTesting Packet Processor...")

    try:
        from qzero.pipeline import RingBuffer, PacketProcessor

        buffer = RingBuffer(max_size=1000)
        processor = PacketProcessor(buffer=buffer, batch_size=50)

        # Simular procesamiento
        packet = Packet(
            timestamp=time.time(),
            source="192.168.1.1",
            destination="10.0.0.1",
            protocol="TCP",
            size=100,
            payload=b"test"
        )

        processor.add_packet(packet)

        stats = processor.get_stats()
        assert stats['packet_count'] >= 1

        print(f"✅ Packet Processor works. Packets: {stats['packet_count']}")

        return True
    except Exception as e:
        print(f"❌ Packet Processor test failed: {e}")
        return False


def test_inference_engine():
    """Test del Inference Engine"""
    print("\nTesting Inference Engine...")

    try:
        from qzero.inference import InferenceEngine

        engine = InferenceEngine(threshold=0.7)

        # Probar predicción
        packet = {
            "source": "192.168.1.1",
            "destination": "10.0.0.1",
            "protocol": "TCP",
            "size": 100,
            "payload": b"test",
            "metadata": {
                "ttl": 64,
                "flags": "S",
                "protocol": "tcp"
            }
        }

        is_anomaly, confidence, probability = engine.is_anomaly(packet)

        assert isinstance(is_anomaly, bool)
        assert isinstance(confidence, float)
        assert isinstance(probability, float)

        print(f"✅ Inference Engine works. Anomaly: {is_anomaly}, Conf: {confidence:.2f}")

        return True
    except Exception as e:
        print(f"❌ Inference Engine test failed: {e}")
        return False


def test_alert_manager():
    """Test del Alert Manager"""
    print("\nTesting Alert Manager...")

    try:
        from qzero.response import AlertManager, AlertLevel, AlertType

        manager = AlertManager(alert_dir="/tmp/qzero-alerts-test")

        # Crear alerta
        alert = manager.create_alert(
            alert_type=AlertType.ANOMALY_DETECTED,
            level=AlertLevel.WARNING,
            source="192.168.1.1",
            destination="10.0.0.1",
            message="Tráfico anómalo detectado",
            confidence=0.8
        )

        assert alert is not None
        assert alert.level == AlertLevel.WARNING

        # Obtener stats
        stats = manager.get_stats()
        assert stats['total_alerts'] >= 1

        print(f"✅ Alert Manager works. Alerts: {stats['total_alerts']}")

        return True
    except Exception as e:
        print(f"❌ Alert Manager test failed: {e}")
        return False


def test_container_monitor():
    """Test del Container Monitor"""
    print("\nTesting Container Monitor...")

    try:
        from qzero.containers import ContainerIntegration

        integration = ContainerIntegration()

        # Verificar disponibilidad
        available = integration.is_available()

        # Escanear contenedores
        containers = integration.scan_containers()

        if not any(available.values()):
            print("⚠️  No contenedores disponibles, test skipped")
            return True

        print(f"✅ Container Monitor works. Found {len(containers)} containers")

        return True
    except Exception as e:
        print(f"❌ Container Monitor test failed: {e}")
        return False


def test_cli_commands():
    """Test que los comandos CLI funcionan"""
    print("\nTesting CLI commands...")

    try:
        from qzero.cli.sniffer import RealTimeSniffer
        from qzero.cli.pipeline import MemoryPipelineCLI
        from qzero.cli.inference import cmd_inference_stats
        from qzero.cli.response import cmd_alerts_stats
        from qzero.cli.containers import cmd_containers_list

        print("✅ CLI commands importable")

        return True
    except Exception as e:
        print(f"❌ CLI commands test failed: {e}")
        return False


def test_version():
    """Test que la versión funciona"""
    print("\nTesting version...")

    try:
        import subprocess
        result = subprocess.run(
            ["qzero", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        assert result.returncode == 0
        assert "QZero" in result.stdout

        print(f"✅ Version: {result.stdout.strip()}")

        return True
    except Exception as e:
        print(f"❌ Version test failed: {e}")
        return False


def main():
    """Ejecutar todos los tests"""
    print("="*70)
    print("QZero Tests - FASE 3")
    print("="*70)

    results = []

    # Tests de imports
    results.append(test_sniffer_imports())
    results.append(test_pipeline_imports())
    results.append(test_inference_imports())
    results.append(test_response_imports())
    results.append(test_containers_imports())

    # Tests funcionales
    results.append(test_ring_buffer())
    results.append(test_packet_processor())
    results.append(test_inference_engine())
    results.append(test_alert_manager())
    results.append(test_container_monitor())

    # Tests CLI
    results.append(test_cli_commands())

    # Tests de versión
    results.append(test_version())

    print("\n" + "="*70)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"✅ ALL {total} TESTS PASSED")
        print("="*70)
        return 0
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print(f"❌ {total - passed} tests failed")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(main())