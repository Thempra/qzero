#!/usr/bin/env python3
"""
Generador de PCAPs Sintéticos Etiquetados para QZero - VERSIÓN CORREGIDA
Crea tráfico de red etiquetado (normal vs ataque) para testing
"""

import scapy.all as scapy
import random
from datetime import datetime
from pathlib import Path
import argparse

# Tipos de tráfico
TRAFFIC_TYPES = {
    'normal': {
        'protocols': [1, 6, 17],  # ICMP, TCP, UDP
        'patterns': ['http', 'ssh', 'dns', 'ping'],
    },
    'ddos': {
        'protocols': [6, 17],  # TCP, UDP
        'patterns': ['syn_flood', 'udp_flood'],
        'rate_multiplier': 100,
    },
    'bruteforce': {
        'protocols': [6],  # TCP
        'patterns': ['ssh_bruteforce', 'telnet_bruteforce'],
        'rate_multiplier': 10,
    },
    'exfiltration': {
        'protocols': [6, 17],  # TCP, UDP
        'patterns': ['c2_comm', 'data_transfer'],
        'rate_multiplier': 50,
    },
    'malware': {
        'protocols': [6, 17],  # TCP, UDP
        'patterns': ['crypto_mining', 'spider_scan'],
        'rate_multiplier': 20,
    },
}

# Ranges de IPs
NORMAL_IPS = [f"192.168.1.{i}" for i in range(1, 100)]
ATTACK_IPS = [f"10.0.{i}.0" for i in range(1, 20)]
DESTINATION_IPS = [f"8.8.8.8", f"1.1.1.1", f"93.184.216.34"]

def generate_icmp_packet(src_ip, dst_ip, size=64):
    """Genera paquete ICMP"""
    payload = bytes([random.randint(0, 255)] * size)
    return scapy.IP(src=src_ip, dst=dst_ip) / scapy.ICMP() / payload

def generate_tcp_packet(src_ip, dst_ip, sport, dport, flags, size=128):
    """Genera paquete TCP"""
    payload = bytes([random.randint(0, 255)] * size)
    return scapy.IP(src=src_ip, dst=dst_ip) / scapy.TCP(sport=sport, dport=dport, flags=flags) / payload

def generate_udp_packet(src_ip, dst_ip, sport, dport, size=64):
    """Genera paquete UDP"""
    payload = bytes([random.randint(0, 255)] * size)
    return scapy.IP(src=src_ip, dst=dst_ip) / scapy.UDP(sport=sport, dport=dport) / payload

def generate_traffic(type_name, duration_seconds=10, rate=10):
    """
    Genera tráfico etiquetado

    Args:
        type_name: Tipo de tráfico ('normal', 'ddos', etc.)
        duration_seconds: Duración en segundos
        rate: Paquetes por segundo
    """
    if type_name not in TRAFFIC_TYPES:
        raise ValueError(f"Tipo de tráfico no válido: {type_name}")

    traffic_config = TRAFFIC_TYPES[type_name]
    packets = []

    total_packets = rate * duration_seconds

    for i in range(total_packets):
        # IP de origen según tipo de tráfico
        if type_name == 'normal':
            src_ip = random.choice(NORMAL_IPS)
        else:
            src_ip = random.choice(ATTACK_IPS)

        dst_ip = random.choice(DESTINATION_IPS)

        # Protocolo aleatorio según configuración
        protocol = random.choice(traffic_config['protocols'])

        # Generar según protocolo
        if protocol == 1:  # ICMP
            packet = generate_icmp_packet(src_ip, dst_ip)
        elif protocol == 6:  # TCP
            flags = random.choice(['S', 'A', 'F', 'P'])
            dport = random.randint(20, 65535)
            sport = random.randint(1024, 49151)
            packet = generate_tcp_packet(src_ip, dst_ip, sport, dport, flags)
        elif protocol == 17:  # UDP
            dport = random.choice([53, 123, 80, 443, 22])
            sport = random.randint(1024, 49151)
            packet = generate_udp_packet(src_ip, dst_ip, sport, dport)

        # Añadir metadata al paquete para etiquetado
        packet.qzero_label = type_name
        packet.qzero_attack_type = traffic_config['patterns'][0] if 'patterns' in traffic_config else 'unknown'
        packet.qzero_timestamp = datetime.now().isoformat()
        packet.qzero_packet_id = i

        packets.append(packet)

    return packets

def save_pcap(packets, output_file):
    """Guarda paquetes en archivo PCAP"""
    try:
        scapy.wrpcap(str(output_file), packets)
        print(f"✅ PCAP guardado: {output_file} ({len(packets)} paquetes)")
    except Exception as e:
        print(f"❌ Error guardando PCAP: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Generador de PCAPs sintéticos etiquetados para QZero')
    parser.add_argument('--type', choices=list(TRAFFIC_TYPES.keys()), default='normal',
                        help='Tipo de tráfico a generar')
    parser.add_argument('--duration', type=int, default=10,
                        help='Duración en segundos')
    parser.add_argument('--rate', type=int, default=10,
                        help='Paquetes por segundo')
    parser.add_argument('--output', type=str, help='Archivo de salida (PCAP)')
    parser.add_argument('--all', action='store_true',
                        help='Generar todos los tipos de tráfico')

    args = parser.parse_args()

    output_dir = Path(__file__).resolve().parent.parent / 'data' / 'synthetic-pcaps'
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        # Generar todos los tipos
        for traffic_type in TRAFFIC_TYPES.keys():
            print(f"\n📊 Generando tráfico: {traffic_type}")
            packets = generate_traffic(traffic_type, args.duration, args.rate)

            output_file = output_dir / f"{traffic_type}_traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pcap"
            save_pcap(packets, output_file)

    else:
        # Generar solo un tipo
        print(f"📊 Generando tráfico: {args.type}")
        packets = generate_traffic(args.type, args.duration, args.rate)

        if args.output:
            output_file = Path(args.output)
        else:
            output_file = output_dir / f"{args.type}_traffic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pcap"

        save_pcap(packets, output_file)

    print(f"\n✅ Fin de generación de PCAPs")
    print(f"📁 Directorio: {output_dir}")
    print("\n📋 Tipos de tráfico disponibles:")
    for t_type in TRAFFIC_TYPES.keys():
        print(f"   - {t_type}: {TRAFFIC_TYPES[t_type]['patterns']}")

if __name__ == '__main__':
    main()