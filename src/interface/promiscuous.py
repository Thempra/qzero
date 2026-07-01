#!/usr/bin/env python3
"""
Módulo de Interfaz Promiscua
"""

import os
import socket
import struct
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class PromiscuousInterface:
    """
    Gestiona interfaces de red en modo promiscuo para captura de tráfico
    """
    
    def __init__(self, interface: str, log_dir: str = "logs"):
        """
        Inicializar interfaz promiscua
        
        Args:
            interface: Nombre de la interfaz (ej: eth0, wlan0)
            log_dir: Directorio para logs y capturas
        """
        self.interface = interface
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.socket: Optional[socket.socket] = None
        self.is_active = False
        self.packet_count = 0
        self.start_time = None
        
        self.logger = logging.getLogger(__name__)
    
    def activate(self) -> bool:
        """
        Activar modo promiscuo en la interfaz
        
        Returns:
            True si se activó correctamente
        """
        try:
            # Verificar si tenemos privilegios de root
            if os.geteuid() != 0:
                raise PermissionError("Se requieren privilegios de root para modo promiscuo")
            
            # Crear socket RAW
            self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
            
            # Activar modo promiscuo
            promiscuous = struct.pack('i', 1)
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.PROMISC, promiscuous)
            except PermissionError:
                # Fallback: verificar si tcpdump puede manejarlo
                self.logger.warning("No se pudo setear PROMISC, usando tcpdump como fallback")
                self.activate_with_tcpdump()
                return True
            
            # Verificar estado
            self.is_active = True
            self.start_time = datetime.now()
            self.logger.info(f"✅ Interfaz {self.interface} activada en modo PROMISCUO")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error al activar promiscuo: {e}")
            return False
    
    def activate_with_tcpdump(self):
        """
        Activar modo promiscuo usando tcpdump como fallback
        """
        import subprocess
        
        pcap_file = self.log_dir / f"capture_{self.interface}_{int(time.time())}.pcap"
        
        try:
            # Iniciar tcpdump en background
            cmd = [
                "tcpdump",
                "-i", self.interface,
                "-w", str(pcap_file),
                "not arp and not icmp"
            ]
            
            self.logger.info(f"📦 Iniciando tcpdump: {' '.join(cmd)}")
            
            # Ejecutar tcpdump en background
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.logger.info(f"✅ tcpdump iniciado (PID: {process.pid})")
            self.is_active = True
            
        except FileNotFoundError:
            raise FileNotFoundError("tcpdump no instalado. Instalar con: sudo apt install tcpdump")
    
    def deactivate(self) -> bool:
        """
        Desactivar modo promiscuo
        
        Returns:
            True si se desactivó correctamente
        """
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            
            self.is_active = False
            self.logger.info(f"⬇️  Interfaz {self.interface} desactivada")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error al desactivar: {e}")
            return False
    
    def get_status(self) -> Dict:
        """
        Obtener estado de la interfaz
        
        Returns:
            Diccionario con estado
        """
        return {
            'interface': self.interface,
            'active': self.is_active,
            'packet_count': self.packet_count,
            'start_time': self.start_time.isoformat() if self.start_time else None
        }
    
    def capture_packets(self, count: int = 100) -> List[Dict]:
        """
        Capturar paquetes específico
        
        Args:
            count: Número de paquetes a capturar
            
        Returns:
            Lista de paquetes capturados
        """
        packets = []
        
        try:
            while len(packets) < count and self.is_active:
                # Recibir paquete
                raw_data, _ = self.socket.recvfrom(65535)
                self.packet_count += 1
                
                # Procesar paquete
                packet = self._parse_packet(raw_data)
                packets.append(packet)
                
                # Pequeña pausa
                time.sleep(0.01)
            
            self.logger.info(f"📦 Capturados {len(packets)} paquetes")
            return packets
            
        except Exception as e:
            self.logger.error(f"❌ Error al capturar: {e}")
            return []
    
    def _parse_packet(self, data: bytes) -> Dict:
        """
        Parsear estructura del paquete
        
        Args:
            data: Datos del paquete crudo
            
        Returns:
            Diccionario con metadatos del paquete
        """
        # Estructura básica Ethernet
        if len(data) < 14:
            return {'error': 'Packet too short'}
        
        eth_header = data[:14]
        eth_dst, eth_src, eth_proto = struct.unpack('!6s6sH', eth_header)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'src_mac': ':'.join(f'{b:02x}' for b in eth_src),
            'dst_mac': ':'.join(f'{b:02x}' for b in eth_dst),
            'protocol': 'ETH' if eth_proto == 0x0800 else f'0x{eth_proto:04x}',
            'size': len(data)
        }
    
    def start_monitoring(self, duration: int = 60):
        """
        Iniciar monitoreo por duración
        
        Args:
            duration: Duración en segundos
        """
        self.logger.info(f"🔍 Iniciando monitoreo por {duration} segundos...")
        
        start = time.time()
        packets = []
        
        try:
            while time.time() - start < duration:
                raw_data, _ = self.socket.recvfrom(65535)
                self.packet_count += 1
                
                packet = self._parse_packet(raw_data)
                packets.append(packet)
                
                # Mostrar progreso
                if self.packet_count % 10 == 0:
                    self.logger.debug(f"📦 Capturados: {self.packet_count} paquetes")
            
            self.logger.info(f"✅ Monitoreo completado: {self.packet_count} paquetes")
            
            # Guardar captura
            self._save_capture(packets)
            
        except KeyboardInterrupt:
            self.logger.info("⏸️  Monitoreo interrumpido por usuario")
        except Exception as e:
            self.logger.error(f"❌ Error en monitoreo: {e}")
    
    def _save_capture(self, packets: List[Dict]):
        """
        Guardar captura de paquetes
        
        Args:
            packets: Lista de paquetes
        """
        from pathlib import Path
        
        output_file = self.log_dir / f"capture_{self.interface}_{int(time.time())}.jsonl"
        
        with open(output_file, 'w') as f:
            for packet in packets:
                f.write(f"{packet}\n")
        
        self.logger.info(f"💾 Captura guardada en {output_file}")


def main():
    """Ejemplo de uso"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Interfaz Promiscua de QZero')
    parser.add_argument('--interface', required=True, help='Interfaz de red')
    parser.add_argument('--activate', action='store_true', help='Activar promiscuo')
    parser.add_argument('--deactivate', action='store_true', help='Desactivar')
    parser.add_argument('--capture', action='store_true', help='Capturar paquetes')
    parser.add_argument('--count', type=int, default=100, help='Cantidad de paquetes')
    
    args = parser.parse_args()
    
    interface = PromiscuousInterface(args.interface)
    
    if args.activate:
        interface.activate()
    elif args.deactivate:
        interface.deactivate()
    elif args.capture:
        interface.activate()
        packets = interface.capture_packets(args.count)
        print(f"Capturados {len(packets)} paquetes")
    
    print(f"Estado: {interface.get_status()}")


if __name__ == '__main__':
    main()
