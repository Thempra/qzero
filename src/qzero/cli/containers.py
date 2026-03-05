"""
Módulo de CLI para Soporte de Contenedores de QZero
"""

import sys
from pathlib import Path
import argparse
import logging
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qzero.containers import (
    ContainerMonitor,
    ContainerIntegration,
    ContainerType
)


def setup_logging(verbose: bool = False):
    """Configurar logging"""
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    log_dir = Path.home() / ".qzero" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "containers.log")
        ]
    )


def cmd_containers_list(args):
    """Lista contenedores"""
    setup_logging(args.verbose)

    try:
        integration = ContainerIntegration()
        available = integration.is_available()

        print(f"🔍 Disponibilidad de Contenedores:")
        print(f"   Docker: {'✅' if available['docker'] else '❌'}")
        print(f"   Kubernetes: {'✅' if available['kubernetes'] else '❌'}")
        print()

        if not any(available.values()):
            print("❌ Ningún sistema de contenedores disponible")
            return

        # Escanear contenedores
        containers = integration.scan_containers()

        if not containers:
            print("ℹ️  No se encontraron contenedores")
            return

        print(f"📦 Contenedores Encontrados ({len(containers)}):\n")

        for container in containers:
            print(f"{'='*60}")
            print(f"🏷️  Tipo: {container['type'].upper()}")
            print(f"📦 Nombre: {container['name']}")
            print(f"🖼️  Imagen: {container['image']}")
            print(f"📊 Estado: {container['status']}")
            if container.get('networks'):
                print(f"🌐 Redes: {', '.join(container['networks'])}")
            if container.get('ports'):
                print(f"🔌 Puertos: {', '.join(container['ports'])}")
            print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_containers_scan(args):
    """Escanea contenedores"""
    setup_logging(args.verbose)

    try:
        integration = ContainerIntegration()

        print(f"🔍 Escaneando contenedores...\n")

        available = integration.is_available()
        results = integration.scan_containers()

        print(f"📊 Resultados:")
        print(f"   Docker: {'✅' if available['docker'] else '❌'}")
        print(f"   Kubernetes: {'✅' if available['kubernetes'] else '❌'}")
        print(f"   Contenedores: {len(results)}")
        print()

        # Guardar resultado
        output_file = Path("reports") / f"containers-scan-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"📄 Reporte guardado en: {output_file}")

        # Mostrar resumen
        print(f"\n{'='*60}")
        print("Resumen de Contenedores")
        print(f"{'='*60}")

        docker_count = sum(1 for c in results if c['type'] == 'docker')
        kube_count = sum(1 for c in results if c['type'] == 'kubernetes')

        print(f"   Docker: {docker_count}")
        print(f"   Kubernetes: {kube_count}")
        print(f"   Total: {len(results)}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_containers_info(args):
    """Obtiene información de un contenedor"""
    setup_logging(args.verbose)

    try:
        if args.container_type == 'docker':
            monitor = ContainerMonitor(ContainerType.DOCKER, args.namespace)
        elif args.container_type == 'kubernetes':
            monitor = ContainerMonitor(ContainerType.KUBERNETES, args.namespace)
        else:
            print(f"❌ Tipo no soportado: {args.container_type}", file=sys.stderr)
            sys.exit(1)

        container_info = monitor.get_container_info(args.container)

        if not container_info:
            print(f"❌ No se encontró contenedor: {args.container}")
            return

        print(f"📊 Información de Contenedor:")
        print(f"{'='*60}")
        print(f"📋 Nombre: {args.container}")
        print(f"🏷️  Tipo: {args.container_type}")
        print(f"📍 Namespace: {args.namespace}")

        if args.container_type == 'docker':
            print(f"🌐 IP: {container_info.get('ip_address', 'N/A')}")
            print(f"🔌 Conexiones: {container_info.get('outgoing_connections', 0)}")
            print(f"💾 CPU: {container_info.get('cpu_percent', 0)}%")
            print(f"🧠 RAM: {container_info.get('memory_percent', 0)}%")
        else:
            print(f"📦 Endpoints: {container_info.get('connected_endpoints', 0)}")
            print(f"✅ Contenedores: {container_info.get('ready_containers', 0)}/{container_info.get('total_containers', 0)}")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_containers_monitor(args):
    """Monitorea contenedores"""
    setup_logging(args.verbose)

    try:
        if args.container_type == 'docker':
            monitor = ContainerMonitor(ContainerType.DOCKER, args.namespace)
        elif args.container_type == 'kubernetes':
            monitor = ContainerMonitor(ContainerType.KUBERNETES, args.namespace)
        else:
            print(f"❌ Tipo no soportado: {args.container_type}", file=sys.stderr)
            sys.exit(1)

        print(f"🚀 Iniciando monitor de contenedores")
        print(f"   Tipo: {args.container_type}")
        print(f"   Namespace: {args.namespace}")
        print(f"   Presiona Ctrl+C para detener\n")

        # Callback para notificaciones
        def callback(data):
            print(f"\r📊 {data['container']} | {data['type']}", end="", flush=True)

        monitor.start_namespace_monitor(interval=args.interval, callback=callback)

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_containers_alerts(args):
    """Genera alertas para contenedores"""
    setup_logging(args.verbose)

    try:
        integration = ContainerIntegration()

        print(f"⚠️  Generando alertas de contenedores...\n")

        alerts = []

        # Escanear contenedores
        containers = integration.scan_containers()

        for container in containers:
            container_alerts = integration.get_container_alerts(container['name'])
            alerts.extend(container_alerts)

        if not alerts:
            print("✅ No se encontraron alertas")
            return

        print(f"📊 Alertas Generadas ({len(alerts)}):\n")

        for alert in alerts:
            print(f"{'='*60}")
            print(f"🚨 Tipo: {alert['type']}")
            print(f"⏰ Hora: {alert['timestamp']}")
            print(f"📍 Contenedor: {alert['container']}")
            print(f"📝 Mensaje: {alert['message']}")
            print(f"{'='*60}\n")

        # Guardar alertas
        output_file = Path("reports") / f"container-alerts-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(alerts, f, indent=2)

        print(f"📄 Alertas guardadas en: {output_file}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)