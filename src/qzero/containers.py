#!/usr/bin/env python3
"""
Soporte para Contenedores para QZero

Monitorización de tráfico en namespaces de Docker y pods de Kubernetes
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import subprocess
import json
import threading
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ContainerType(Enum):
    """Tipos de contenedores"""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    POD = "pod"


@dataclass
class Container:
    """Representa un contenedor"""
    name: str
    container_type: ContainerType
    image: str
    status: str
    created_at: Optional[str] = None
    ports: List[str] = None
    networks: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "name": self.name,
            "type": self.container_type.value,
            "image": self.image,
            "status": self.status,
            "created_at": self.created_at,
            "ports": self.ports or [],
            "networks": self.networks or []
        }


class DockerNamespace:
    """Monitor de namespaces Docker"""

    def __init__(self, namespace: str = "default"):
        """
        Inicializa el monitor Docker.

        Args:
            namespace: Namespace de Docker
        """
        self.namespace = namespace
        self.containers: List[Container] = []
        self.running = False
        self.lock = threading.Lock()

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"DockerNamespace inicializado en {namespace}")

    def is_available(self) -> bool:
        """Verifica si Docker está disponible"""
        try:
            subprocess.run(
                ["docker", "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def list_containers(self) -> List[Container]:
        """Lista todos los contenedores"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            containers = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                container_data = json.loads(line)
                container = Container(
                    name=container_data.get('Names', [''])[0].lstrip('/'),
                    container_type=ContainerType.DOCKER,
                    image=container_data.get('Image', ''),
                    status=container_data.get('Status', ''),
                    created_at=container_data.get('CreatedAt'),
                    ports=container_data.get('Ports', []),
                    networks=[container_data.get('Networks', [''])[-1].lstrip('/')]
                )

                containers.append(container)

            self.containers = containers
            self.logger.info(f"Encontrados {len(containers)} contenedores Docker")

            return containers

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error listando contenedores: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON: {e}")
            return []

    def get_container_traffic(self, container_name: str) -> Dict[str, Any]:
        """
        Obtiene tráfico de un contenedor específico.

        Args:
            container_name: Nombre del contenedor

        Returns:
            Información de tráfico
        """
        try:
            # Obtener IP del contenedor
            ip_result = subprocess.run(
                ["docker", "inspect", container_name, "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            ip_address = ip_result.stdout.strip()
            if not ip_address:
                self.logger.warning(f"Contenedor {container_name} sin red asignada")
                return {}

            # Contar conexiones salientes
            connections_result = subprocess.run(
                ["docker", "exec", container_name, "sh", "-c",
                 "netstat -ant | grep ESTABLISHED | wc -l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            outgoing_connections = int(connections_result.stdout.strip())

            return {
                "container_name": container_name,
                "ip_address": ip_address,
                "outgoing_connections": outgoing_connections,
                "timestamp": datetime.now().isoformat()
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error obteniendo tráfico de {container_name}: {e}")
            return {}

    def get_namespace_containers(self) -> List[Dict[str, Any]]:
        """Obtiene todos los contenedores del namespace"""
        containers = self.list_containers()

        namespace_data = []
        for container in containers:
            namespace_data.append(container.to_dict())

        return namespace_data

    def get_container_stats(self, container_name: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un contenedor.

        Args:
            container_name: Nombre del contenedor

        Returns:
            Estadísticas
        """
        try:
            result = subprocess.run(
                ["docker", "stats", container_name, "--no-stream", "--format", "{{json .}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            stats_data = json.loads(result.stdout.strip())

            return {
                "container_name": container_name,
                "cpu_percent": stats_data.get('CpuPerc', 0),
                "memory_percent": stats_data.get('MemPerc', 0),
                "memory_usage": stats_data.get('MemUsage', '0 B'),
                "net_io": stats_data.get('NetIO', '0 B'),
                "block_io": stats_data.get('BlockIO', '0 B'),
                "timestamp": datetime.now().isoformat()
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error obteniendo stats de {container_name}: {e}")
            return {}


class KubeNamespace:
    """Monitor de namespaces Kubernetes"""

    def __init__(self, namespace: str = "default"):
        """
        Inicializa el monitor Kubernetes.

        Args:
            namespace: Namespace de Kubernetes
        """
        self.namespace = namespace
        self.pods: List[Container] = []
        self.running = False
        self.lock = threading.Lock()

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"KubeNamespace inicializado en {namespace}")

    def is_available(self) -> bool:
        """Verifica si kubectl está disponible"""
        try:
            subprocess.run(
                ["kubectl", "version", "--client"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def list_pods(self) -> List[Container]:
        """Lista todos los pods"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, "-o", "json"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            pods_data = json.loads(result.stdout)
            pods = []

            for pod in pods_data.get('items', []):
                pod_info = pod.get('metadata', {})
                pod_name = pod_info.get('name', '')
                pod_status = pod.get('status', {}).get('phase', 'Unknown')
                pod_ip = pod.get('status', {}).get('podIP', '')

                pod_container = Container(
                    name=pod_name,
                    container_type=ContainerType.POD,
                    image=f"KubernetesPod",
                    status=pod_status,
                    networks=[pod_ip],
                    ports=[f"{pod_ip}:8080"]  # Placeholder
                )

                pods.append(pod_container)

            self.pods = pods
            self.logger.info(f"Encontrados {len(pods)} pods en {self.namespace}")

            return pods

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error listando pods: {e}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON: {e}")
            return []

    def get_pod_traffic(self, pod_name: str) -> Dict[str, Any]:
        """
        Obtiene tráfico de un pod específico.

        Args:
            pod_name: Nombre del pod

        Returns:
            Información de tráfico
        """
        try:
            # Obtener IP del pod
            ip_result = subprocess.run(
                ["kubectl", "get", "pod", pod_name, "-n", self.namespace, "-o",
                 "jsonpath='{.status.podIP}'"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            ip_address = ip_result.stdout.strip().strip("'")
            if not ip_address:
                self.logger.warning(f"Pod {pod_name} sin IP asignada")
                return {}

            # Contar endpoints conectados
            endpoints_result = subprocess.run(
                ["kubectl", "get", "endpoints", pod_name, "-n", self.namespace,
                 "-o", "jsonpath='{.subsets[*].addresses[*].ip}'"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            connected_endpoints = len(endpoints_result.stdout.strip().split())

            return {
                "pod_name": pod_name,
                "ip_address": ip_address,
                "connected_endpoints": connected_endpoints,
                "namespace": self.namespace,
                "timestamp": datetime.now().isoformat()
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error obteniendo tráfico de {pod_name}: {e}")
            return {}

    def get_namespace_pods(self) -> List[Dict[str, Any]]:
        """Obtiene todos los pods del namespace"""
        pods = self.list_pods()

        namespace_data = []
        for pod in pods:
            namespace_data.append(pod.to_dict())

        return namespace_data

    def get_pod_stats(self, pod_name: str) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un pod.

        Args:
            pod_name: Nombre del pod

        Returns:
            Estadísticas
        """
        try:
            result = subprocess.run(
                ["kubectl", "get", "pod", pod_name, "-n", self.namespace,
                 "-o", "jsonpath='{.status.containerStatuses[*].ready}'"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            ready_statuses = result.stdout.strip().split()
            ready_count = ready_statuses.count('true')
            total_count = len(ready_statuses)

            return {
                "pod_name": pod_name,
                "namespace": self.namespace,
                "ready_containers": ready_count,
                "total_containers": total_count,
                "status": f"{'Ready' if ready_count == total_count else 'Not Ready'}",
                "timestamp": datetime.now().isoformat()
            }

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error obteniendo stats de {pod_name}: {e}")
            return {}


class ContainerMonitor:
    """Monitor general de contenedores"""

    def __init__(self, container_type: ContainerType, namespace: str = "default"):
        """
        Inicializa el monitor.

        Args:
            container_type: Tipo de contenedor
            namespace: Namespace/cluster
        """
        self.container_type = container_type
        self.namespace = namespace

        if container_type == ContainerType.DOCKER:
            self.monitor = DockerNamespace(namespace)
        elif container_type == ContainerType.KUBERNETES:
            self.monitor = KubeNamespace(namespace)
        else:
            raise ValueError(f"Tipo de contenedor no soportado: {container_type}")

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ContainerMonitor inicializado: {container_type.value}")

    def get_containers(self) -> List[Container]:
        """Obtiene la lista de contenedores"""
        return self.monitor.list_containers()

    def get_container_info(self, container_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un contenedor"""
        if self.container_type == ContainerType.DOCKER:
            return self.monitor.get_container_stats(container_name)
        else:
            return self.monitor.get_pod_stats(container_name)

    def get_all_containers_info(self) -> List[Dict[str, Any]]:
        """Obtiene información de todos los contenedores"""
        containers = self.get_containers()
        return [c.to_dict() for c in containers]

    def monitor_traffic(self, container_name: str, callback: Optional[Callable] = None):
        """
        Monitorea tráfico de un contenedor.

        Args:
            container_name: Nombre del contenedor
            callback: Callback para notificaciones
        """
        self.logger.info(f"Monitoreando tráfico de {container_name}")

        try:
            while self.monitor.running:
                traffic_info = self.monitor.get_container_traffic(container_name)

                if traffic_info and callback:
                    callback(traffic_info)

                time.sleep(1)  # Verificar cada segundo

        except KeyboardInterrupt:
            self.logger.info("Monitoreo detenido")

    def start_namespace_monitor(self, interval: float = 1.0, callback: Optional[Callable] = None):
        """
        Inicia monitor del namespace.

        Args:
            interval: Intervalo de muestreo
            callback: Callback para notificaciones
        """
        self.monitor.running = True
        self.logger.info(f"Monitoreando namespace {self.namespace} ({interval}s)")

        try:
            while self.monitor.running:
                containers = self.get_containers()

                for container in containers:
                    container_info = self.get_container_info(container.name)

                    if container_info and callback:
                        callback({
                            "container": container.name,
                            "type": self.container_type.value,
                            "info": container_info,
                            "timestamp": datetime.now().isoformat()
                        })

                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("Monitoreo detenido")

    def stop(self):
        """Detiene el monitor"""
        self.monitor.running = False
        self.logger.info("Monitor detenido")


class ContainerIntegration:
    """Integración de contenedores con QZero"""

    def __init__(self):
        """Inicializa la integración"""
        self.docker_monitor = ContainerMonitor(ContainerType.DOCKER)
        self.kube_monitor = ContainerMonitor(ContainerType.KUBERNETES)

        self.logger = logging.getLogger(__name__)
        self.logger.info("ContainerIntegration inicializado")

    def is_available(self) -> Dict[str, bool]:
        """Verifica disponibilidad de contenedores"""
        return {
            "docker": self.docker_monitor.monitor.is_available(),
            "kubernetes": self.kube_monitor.monitor.is_available()
        }

    def scan_containers(self) -> List[Dict[str, Any]]:
        """Escanea todos los contenedores disponibles"""
        results = []

        # Escanear Docker
        if self.docker_monitor.monitor.is_available():
            results.extend(self.docker_monitor.get_all_containers_info())

        # Escanear Kubernetes
        if self.kube_monitor.monitor.is_available():
            results.extend(self.kube_monitor.get_all_containers_info())

        self.logger.info(f"Escaneo completado: {len(results)} contenedores encontrados")
        return results

    def get_container_alerts(self, container_name: str) -> List[Dict[str, Any]]:
        """
        Genera alertas para contenedores sospechosos.

        Args:
            container_name: Nombre del contenedor

        Returns:
            Lista de alertas
        """
        alerts = []

        # Escanear contenedor
        container_info = self.docker_monitor.get_container_info(container_name)

        if not container_info:
            return alerts

        # Verificar tráfico anómalo
        if container_info.get('outgoing_connections', 0) > 1000:
            alerts.append({
                "timestamp": datetime.now().isoformat(),
                "type": "HIGH_TRAFFIC",
                "level": "WARNING",
                "container": container_name,
                "message": f"Alto tráfico saliente: {container_info['outgoing_connections']} conexiones",
                "details": container_info
            })

        return alerts

    def monitor_intra_container(self, container_name: str) -> None:
        """
        Monitorea tráfico intra-contenedor.

        Args:
            container_name: Nombre del contenedor
        """
        self.docker_monitor.monitor.running = True

        self.logger.info(f"Monitoreando tráfico intra-contenedor: {container_name}")

        try:
            while self.docker_monitor.monitor.running:
                # Obtener contenedores dentro del namespace
                containers = self.docker_monitor.monitor.list_containers()

                # Analizar tráfico entre contenedores
                for i, container1 in enumerate(containers):
                    for container2 in containers[i+1:]:
                        if container1.name == container2.name:
                            continue

                        traffic = self.docker_monitor.monitor.get_container_traffic(container1.name)
                        if traffic:
                            # Analizar tráfico hacia otros contenedores
                            for ip in traffic.get('ip_address', '').split():
                                # TODO: Verificar si la IP es de otro contenedor
                                pass

                time.sleep(5)

        except KeyboardInterrupt:
            self.logger.info("Monitoreo intra-contenedor detenido")

        finally:
            self.docker_monitor.monitor.running = False