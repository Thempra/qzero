#!/usr/bin/env python3
"""
Pipeline de Ingesta en Memoria para QZero

Ring buffer para paquetes con procesamiento por lotes
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Iterator
import threading
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class PacketType(Enum):
    """Tipos de paquetes"""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    OTHER = "other"


@dataclass
class PacketBatch:
    """Batch de paquetes para procesamiento"""
    timestamp: float
    packets: List['Packet']
    batch_id: str
    size_bytes: int
    packet_count: int


class RingBuffer:
    """Ring buffer para paquetes"""

    def __init__(self, max_size: int = 10000):
        """
        Inicializa el ring buffer.

        Args:
            max_size: Tamaño máximo del buffer
        """
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.current_size = 0
        self.lock = threading.Lock()

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"RingBuffer inicializado con tamaño: {max_size}")

    def add_packet(self, packet: 'Packet') -> bool:
        """
        Añade un paquete al buffer.

        Args:
            packet: Paquete a añadir

        Returns:
            True si se añadió, False si el buffer estaba lleno
        """
        with self.lock:
            if self.current_size >= self.max_size:
                self.logger.warning("RingBuffer lleno - eliminando paquete más antiguo")
                self.buffer.pop()
            else:
                self.current_size += 1

            self.buffer.append(packet)
            return True

    def get_packets(self, count: Optional[int] = None) -> List['Packet']:
        """
        Obtiene paquetes del buffer.

        Args:
            count: Número máximo de paquetes

        Returns:
            Lista de paquetes
        """
        with self.lock:
            if count:
                return list(self.buffer)[-count:]
            else:
                return list(self.buffer)

    def get_batches(self, batch_size: int = 100) -> Iterator[PacketBatch]:
        """
        Genera batches del buffer.

        Args:
            batch_size: Tamaño de cada batch

        Yields:
            PacketBatch
        """
        while True:
            with self.lock:
                packets = list(self.buffer)
                self.buffer.clear()
                self.current_size = 0

                if not packets:
                    break

                # Crear batches
                for i in range(0, len(packets), batch_size):
                    batch_packets = packets[i:i + batch_size]

                    batch_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{i}"
                    size_bytes = sum(p.size for p in batch_packets)

                    yield PacketBatch(
                        timestamp=time.time(),
                        packets=batch_packets,
                        batch_id=batch_id,
                        size_bytes=size_bytes,
                        packet_count=len(batch_packets)
                    )

            time.sleep(0.1)  # Breve pausa para evitar starvation

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del buffer"""
        with self.lock:
            return {
                "current_size": self.current_size,
                "max_size": self.max_size,
                "usage_percent": (self.current_size / self.max_size) * 100,
                "available_slots": self.max_size - self.current_size
            }


@dataclass
class Packet:
    """Representa un paquete"""
    timestamp: float
    source: str
    destination: str
    protocol: str
    size: int
    payload: Optional[bytes]
    type: PacketType = PacketType.OTHER
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "destination": self.destination,
            "protocol": self.protocol,
            "size": self.size,
            "payload": self.payload.hex() if self.payload else None,
            "type": self.type.value,
            "metadata": self.metadata
        }


class PacketProcessor:
    """Procesador de paquetes en tiempo real"""

    def __init__(self, buffer: RingBuffer, batch_size: int = 100, threshold: float = 0.7):
        """
        Inicializa el procesador.

        Args:
            buffer: RingBuffer para paquetes
            batch_size: Tamaño de batches
            threshold: Umbral de detección
        """
        self.buffer = buffer
        self.batch_size = batch_size
        self.threshold = threshold

        self.running = False
        self.packet_count = 0
        self.anomaly_count = 0

        self.processing_callback: Optional[Callable] = None
        self.anomaly_callback: Optional[Callable] = None

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"PacketProcessor inicializado con batch_size: {batch_size}")

    def start(self):
        """Inicia el procesador"""
        self.running = True
        self.logger.info("🚀 Iniciando procesador de paquetes")

    def stop(self):
        """Detiene el procesador"""
        self.running = False
        self.logger.info(f"🛑 Procesador detenido. Paquetes: {self.packet_count}, Anomalías: {self.anomaly_count}")

    def process_stream(self):
        """Procesa el stream de paquetes"""
        try:
            self.start()

            for batch in self.buffer.get_batches(self.batch_size):
                self._process_batch(batch)

                if not self.running:
                    break

        except KeyboardInterrupt:
            self.logger.info("Procesamiento detenido por usuario")
        finally:
            self.stop()

    def _process_batch(self, batch: PacketBatch):
        """Procesa un batch"""
        # Callback de procesamiento
        if self.processing_callback:
            self.processing_callback(batch)

        # TODO: Implementar análisis real de anomalías
        # Por ahora, simulamos
        import random

        # Analizar cada paquete del batch
        for packet in batch.packets:
            self.packet_count += 1

            # Detectar anomalías
            if random.random() < 0.01:  # 1% de probabilidad
                self.anomaly_count += 1
                anomaly = {
                    "timestamp": datetime.now().isoformat(),
                    "packet_id": batch.batch_id,
                    "packet_index": batch.packets.index(packet),
                    "type": random.choice(["Port Scan", "Malicious Traffic", "Suspicious Pattern"]),
                    "confidence": random.uniform(0.6, 0.95),
                    "description": f"Anomalía en batch {batch.batch_id}"
                }

                if self.anomaly_callback:
                    self.anomaly_callback(anomaly)

                self.logger.warning(f"Anomalía detectada: {anomaly['type']} ({anomaly['confidence']:.2f})")

        # Log de progreso cada 1000 paquetes
        if self.packet_count % 1000 == 0:
            self.logger.info(
                f"Paquetes procesados: {self.packet_count}, "
                f"Anomalías: {self.anomaly_count}"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del procesador"""
        return {
            "packet_count": self.packet_count,
            "anomaly_count": self.anomaly_count,
            "threshold": self.threshold,
            "batch_size": self.batch_size,
            "buffer_stats": self.buffer.get_stats()
        }


class MemoryEfficientSniffer:
    """Sniffer con ingestión eficiente en memoria"""

    def __init__(
        self,
        interface: str,
        promiscuous: bool = False,
        buffer_size: int = 10000,
        batch_size: int = 100
    ):
        """
        Inicializa el sniffer.

        Args:
            interface: Interfaz de red
            promiscuous: Modo promiscuo
            buffer_size: Tamaño del buffer
            batch_size: Tamaño de batches
        """
        self.interface = interface
        self.promiscuous = promiscuous
        self.buffer = RingBuffer(max_size=buffer_size)
        self.processor = PacketProcessor(
            buffer=self.buffer,
            batch_size=batch_size
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"MemoryEfficientSniffer inicializado")

    def start(self):
        """Inicia el sniffer"""
        from qzero.sniffer import ScapySniffer

        # Iniciar sniffer
        try:
            sniffer = ScapySniffer(self.interface, self.promiscuous, self.buffer.max_size)
            sniffer.start()

            # Procesar stream
            self.processor.process_stream()

        except Exception as e:
            self.logger.error(f"Error iniciando sniffer: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas"""
        return {
            "interface": self.interface,
            "promiscuous": self.promiscuous,
            "buffer_stats": self.buffer.get_stats(),
            "processor_stats": self.processor.get_stats()
        }