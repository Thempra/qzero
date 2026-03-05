#!/usr/bin/env python3
"""
Módulo de Captura de Red para QZero

Captura tráfico de red en tiempo real usando scapy o tcpdump/tshark
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import threading
import queue
import socket
import re
import struct
from collections import deque
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class InterfaceType(Enum):
    """Tipos de interfaces"""
    ETHERNET = "ethernet"
    WIFI = "wifi"
    LOOPBACK = "loopback"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


@dataclass
class Packet:
    """Representa un paquete capturado"""
    timestamp: float
    source: str
    destination: str
    protocol: str
    size: int
    payload: Optional[bytes]
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
            "metadata": self.metadata
        }


class NetworkInterface:
    """Gestor de interfaces de red"""

    def __init__(self, interface_name: str):
        """
        Inicializa la interfaz.

        Args:
            interface_name: Nombre de la interfaz (ej. eth0, wlan0, docker0)
        """
        self.interface = interface_name
        self.type = self._detect_interface_type()
        self.promiscuous = False
        self.up = False

    def _detect_interface_type(self) -> InterfaceType:
        """Detecta el tipo de interfaz"""
        interface_type = InterfaceType.ETHERNET

        if self.interface.startswith("docker"):
            interface_type = InterfaceType.DOCKER
        elif self.interface.startswith("eth"):
            interface_type = InterfaceType.ETHERNET
        elif self.interface.startswith("wlan") or self.interface.startswith("wifi"):
            interface_type = InterfaceType.WIFI
        elif self.interface == "lo":
            interface_type = InterfaceType.LOOPBACK
        elif self.interface.startswith("kube"):
            interface_type = InterfaceType.KUBERNETES

        return interface_type

    def is_up(self) -> bool:
        """Verifica si la interfaz está activa"""
        try:
            # Usar socket para verificar si la interfaz está operativa
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
            return True
        except (socket.error, OSError):
            return False

    def set_promiscuous(self, enable: bool = True):
        """
        Activa o desactiva modo promiscuo.

        Args:
            enable: True para activar, False para desactivar
        """
        if enable:
            logger.info(f"🔄 Activando modo promiscuo en {self.interface}")
        else:
            logger.info(f"⬇️  Desactivando modo promiscuo en {self.interface}")

        self.promiscuous = enable

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado de la interfaz"""
        return {
            "interface": self.interface,
            "type": self.type.value,
            "promiscuous": self.promiscuous,
            "up": self.is_up(),
            "timestamp": datetime.now().isoformat()
        }


class BaseSniffer:
    """Base para capturadores de paquetes"""

    def __init__(self, interface: str, promiscuous: bool = False, buffer_size: int = 10000):
        """
        Inicializa el sniffer.

        Args:
            interface: Interfaz de red
            promiscuous: Modo promiscuo
            buffer_size: Tamaño del buffer
        """
        self.interface = interface
        self.promiscuous = promiscuous
        self.buffer_size = buffer_size

        self.interface_obj = NetworkInterface(interface)
        self.interface_obj.set_promiscuous(promiscuous)

        self.running = False
        self.packet_queue = queue.Queue(maxsize=buffer_size)
        self.packet_count = 0

        logger.info(f"Sniffer inicializado en {interface}")
        if promiscuous:
            logger.info("Modo promiscuo activado")

    def start(self):
        """Inicia la captura"""
        if not self.interface_obj.is_up():
            raise RuntimeError(f"La interfaz {self.interface} no está activa")

        if self.promiscuous and not self._check_promiscuous_support():
            logger.warning("Modo promiscuo puede no ser soportado")

        self.running = True
        logger.info(f"🚀 Iniciando captura en {self.interface} (presione Ctrl+C para detener)")

    def stop(self):
        """Detiene la captura"""
        self.running = False
        logger.info(f"🛑 Captura detenido. Total paquetes: {self.packet_count}")

    def _check_promiscuous_support(self) -> bool:
        """Verifica soporte para modo promiscuo"""
        # TODO: Implementar verificación real
        return True

    def capture_packet(self) -> Optional[Packet]:
        """
        Captura un paquete.

        Returns:
            Objeto Packet o None si no hay paquetes
        """
        raise NotImplementedError

    def run(self, callback: Optional[Callable] = None):
        """
        Ejecuta la captura en un loop.

        Args:
            callback: Función a llamar con cada paquete
        """
        try:
            self.start()

            while self.running:
                packet = self.capture_packet()
                if packet:
                    self.packet_queue.put(packet)
                    self.packet_count += 1

                    if callback:
                        callback(packet)

                    # Mostrar progreso cada 100 paquetes
                    if self.packet_count % 100 == 0:
                        logger.debug(f"Paquetes capturados: {self.packet_count}")

        except KeyboardInterrupt:
            logger.info("Captura detenido por usuario")
        finally:
            self.stop()

    def get_packets(self, count: Optional[int] = None) -> List[Packet]:
        """
        Obtiene paquetes del queue.

        Args:
            count: Número máximo de paquetes

        Returns:
            Lista de paquetes
        """
        packets = []

        if count:
            while len(packets) < count and not self.packet_queue.empty():
                try:
                    packets.append(self.packet_queue.get_nowait())
                except queue.Empty:
                    break
        else:
            while not self.packet_queue.empty():
                try:
                    packets.append(self.packet_queue.get_nowait())
                except queue.Empty:
                    break

        return packets


class ScapySniffer(BaseSniffer):
    """Sniffer usando scapy"""

    def __init__(self, *args, **kwargs):
        """Inicializa sniffer con scapy"""
        super().__init__(*args, **kwargs)

        try:
            from scapy.all import sniff, IP, TCP, UDP, ICMP, Raw
            self.sniff = sniff
            self.IP = IP
            self.TCP = TCP
            self.UDP = UDP
            self.ICMP = ICMP
            self.Raw = Raw
            logger.info("✅ Scapy importado correctamente")
        except ImportError:
            logger.error("❌ Scapy no instalado. Instala con: pip install scapy")
            raise

    def capture_packet(self) -> Optional[Packet]:
        """Captura un paquete usando scapy"""
        try:
            packets = self.sniff(iface=self.interface, count=1, timeout=1, store=False)

            if packets:
                pkt = packets[0]
                return self._parse_packet(pkt)

            return None

        except Exception as e:
            logger.error(f"Error capturando paquete: {e}")
            return None

    def _parse_packet(self, pkt) -> Packet:
        """Parsea un paquete Scapy a objeto Packet"""
        timestamp = time.time()

        # Parsear IP
        ip = pkt.getlayer(self.IP)
        if ip:
            source = f"{ip.src}"
            destination = f"{ip.dst}"
            protocol = ip.proto
            protocol_name = self._get_protocol_name(protocol)

            # Parsear payload
            payload = None
            if self.Raw in pkt:
                payload = bytes(pkt[self.Raw].load)

            metadata = {
                "ttl": ip.ttl,
                "id": ip.id,
                "flags": str(ip.flags),
                "protocol": protocol_name,
                "length": len(pkt)
            }

            return Packet(
                timestamp=timestamp,
                source=source,
                destination=destination,
                protocol=protocol_name,
                size=len(pkt),
                payload=payload,
                metadata=metadata
            )

        return Packet(
            timestamp=timestamp,
            source="unknown",
            destination="unknown",
            protocol="unknown",
            size=len(pkt),
            payload=None
        )

    def _get_protocol_name(self, protocol_num: int) -> str:
        """Obtiene nombre del protocolo"""
        protocol_names = {
            1: "ICMP",
            6: "TCP",
            17: "UDP",
            89: "OSPF",
            132: "SCTP"
        }
        return protocol_names.get(protocol_num, str(protocol_num))


class TcpDumpSniffer(BaseSniffer):
    """Sniffer usando tcpdump"""

    def __init__(self, *args, **kwargs):
        """Inicializa sniffer con tcpdump"""
        super().__init__(*args, **kwargs)

        try:
            import subprocess
            self.subprocess = subprocess
            logger.info("✅ TcpDump disponible")
        except ImportError:
            logger.error("❌ Subprocess no disponible")
            raise

    def capture_packet(self) -> Optional[Packet]:
        """Captura un paquete usando tcpdump"""
        try:
            # Ejecutar tcpdump para capturar 1 paquete
            cmd = [
                "tcpdump",
                "-i", self.interface,
                "-c", "1",
                "-w", "-",
                "-n"
            ]

            process = self.subprocess.Popen(
                cmd,
                stdout=self.subprocess.PIPE,
                stderr=self.subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=2)

            if stdout:
                return self._parse_tcpdump_output(stdout)

            return None

        except Exception as e:
            logger.error(f"Error capturando paquete: {e}")
            return None

    def _parse_tcpdump_output(self, output: str) -> Packet:
        """Parsea salida de tcpdump"""
        try:
            lines = output.strip().split('\n')
            if not lines:
                return None

            line = lines[0]

            # Parsear timestamp
            timestamp_match = re.match(r'\d+:\d+:\d+\.\d+', line)
            if timestamp_match:
                timestamp_str = timestamp_match.group()
                timestamp = datetime.strptime(timestamp_str, "%H:%M:%S.%f").timestamp()

            # Parsear IP origen y destino
            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
            if ip_match:
                source = ip_match.group(0)
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line[ip_match.end():])
                if ip_match:
                    destination = ip_match.group(0)

            # Parsear protocolo
            protocol_match = re.search(r'(TCP|UDP|ICMP)', line)
            protocol = protocol_match.group(1) if protocol_match else "unknown"

            # Parsear tamaño
            size_match = re.search(r'\s(\d+)\s$', line)
            size = int(size_match.group(1)) if size_match else len(output)

            return Packet(
                timestamp=timestamp,
                source=source,
                destination=destination,
                protocol=protocol,
                size=size,
                payload=None
            )

        except Exception as e:
            logger.error(f"Error parseando tcpdump: {e}")
            return None


def start_sniffer(interface: str, promiscuous: bool = False, buffer_size: int = 10000) -> BaseSniffer:
    """
    Inicia un sniffer automáticamente eligiendo la mejor opción.

    Args:
        interface: Interfaz de red
        promiscuous: Modo promiscuo
        buffer_size: Tamaño del buffer

    Returns:
        Sniffer inicializado
    """
    # Intentar usar scapy primero
    try:
        sniffer = ScapySniffer(interface, promiscuous, buffer_size)
        logger.info("✅ Usando Scapy como capturador")
        return sniffer
    except ImportError:
        logger.warning("Scapy no disponible, intentando tcpdump...")

    # Fallback a tcpdump
    try:
        sniffer = TcpDumpSniffer(interface, promiscuous, buffer_size)
        logger.info("✅ Usando TcpDump como capturador")
        return sniffer
    except Exception as e:
        logger.error(f"❌ No se pudo iniciar ningún sniffer: {e}")
        raise