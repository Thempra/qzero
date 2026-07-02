# API Reference - QZero

## Módulo: sniffer.py

### Clases

#### `ScapySniffer`

Módulo de captura de paquetes usando Scapy.

**Constructor:**
```python
ScapySniffer(interface, promiscuous=False, buffer_size=10000)
```

**Parámetros:**
- `interface` (str): Nombre de la interfaz de red
- `promiscuous` (bool): Modo promiscuo (default: False)
- `buffer_size` (int): Tamaño del buffer (default: 10000)

**Métodos:**
- `start()`: Inicia la captura
- `stop()`: Detiene la captura
- `capture_packet()`: Captura un paquete
- `run(callback=None)`: Ejecuta captura en un loop

**Ejemplo:**
```python
from qzero.sniffer import ScapySniffer

sniffer = ScapySniffer("eth0", promiscuous=True)
sniffer.start()

# Capturar paquetes
while sniffer.running:
    packet = sniffer.capture_packet()
    if packet:
        process(packet)

sniffer.stop()
```

#### `TcpDumpSniffer`

Módulo de captura usando TcpDump como fallback.

**Constructor:**
```python
TcpDumpSniffer(interface, promiscuous=False, buffer_size=10000)
```

**Métodos:**
- Igual que `ScapySniffer`

#### `RealTimeSniffer`

Sniffer en tiempo real con detección de anomalías.

**Constructor:**
```python
RealTimeSniffer(interface, promiscuous=False, threshold=0.7, buffer_size=10000)
```

**Parámetros:**
- `threshold` (float): Umbral de detección (0-1)

**Métodos:**
- `start(interval=1.0)`: Inicia captura con intervalo

**Ejemplo:**
```python
from qzero.cli.sniffer import RealTimeSniffer

sniffer = RealTimeSniffer("eth0", promiscuous=True, threshold=0.8)
sniffer.start()
```

#### `NetworkInterface`

Gestor de interfaces de red.

**Constructor:**
```python
NetworkInterface(interface_name)
```

**Parámetros:**
- `interface_name` (str): Nombre de la interfaz

**Métodos:**
- `is_up()`: Verifica si está activa
- `set_promiscuous(enable)`: Activa/desactiva modo promiscuo
- `get_status()`: Obtiene estado completo

**Ejemplo:**
```python
from qzero.cli.sniffer import RealTimeSniffer

sniffer = RealTimeSniffer("eth0", promiscuous=True)
interface = sniffer.interface_obj
interface.set_promiscuous(True)
```

### Dataclasses

#### `Packet`

Representa un paquete capturado.

**Atributos:**
- `timestamp` (float): Timestamp de captura
- `source` (str): IP de origen
- `destination` (str): IP de destino
- `protocol` (str): Protocolo
- `size` (int): Tamaño en bytes
- `payload` (bytes): Payload del paquete
- `metadata` (dict): Metadata adicional

**Método:**
- `to_dict()`: Convierte a diccionario JSON

### Enums

#### `InterfaceType`

Tipos de interfaces de red.
- `ETHERNET`: Ethernet
- `WIFI`: WiFi
- `LOOPBACK`: Loopback
- `DOCKER`: Docker
- `KUBERNETES`: Kubernetes

---

## Módulo: pipeline.py

### Clases

#### `RingBuffer`

Buffer circular para paquetes.

**Constructor:**
```python
RingBuffer(max_size=10000)
```

**Parámetros:**
- `max_size` (int): Tamaño máximo del buffer

**Métodos:**
- `add_packet(packet)`: Añade paquete
- `get_packets(count=None)`: Obtiene paquetes
- `get_batches(batch_size=100)`: Genera batches
- `get_stats()`: Obtiene estadísticas

**Ejemplo:**
```python
from qzero.pipeline import RingBuffer, Packet

buffer = RingBuffer(max_size=10000)

for i in range(100):
    packet = Packet(
        timestamp=time.time(),
        source="192.168.1.1",
        destination="10.0.0.1",
        protocol="TCP",
        size=100,
        payload=b"test"
    )
    buffer.add_packet(packet)
```

#### `PacketProcessor`

Procesador de paquetes en tiempo real.

**Constructor:**
```python
PacketProcessor(buffer, batch_size=100, threshold=0.7)
```

**Parámetros:**
- `buffer` (RingBuffer): Buffer de paquetes
- `batch_size` (int): Tamaño de batches
- `threshold` (float): Umbral de detección

**Métodos:**
- `start()`: Inicia procesamiento
- `process_stream()`: Procesa stream completo

#### `MemoryEfficientSniffer`

Sniffer con ingestión eficiente en memoria.

**Constructor:**
```python
MemoryEfficientSniffer(interface, promiscuous=False, buffer_size=10000, batch_size=100)
```

**Métodos:**
- `start()`: Inicia sniffer
- `get_stats()`: Obtiene estadísticas

---

## Módulo: inference.py

### Clases

#### `InferenceEngine`

Motor de inferencia para detección de anomalías.

**Constructor:**
```python
InferenceEngine(model_path=None, threshold=0.7)
```

**Parámetros:**
- `model_path` (str): Ruta al modelo ML
- `threshold` (float): Umbral de detección

**Métodos:**
- `extract_features(packet)`: Extrae features
- `predict(packet)`: Predice anomalía
- `is_anomaly(packet)`: Determina si es anomalía
- `_simulate_prediction(packet)`: Predicción simulada

**Ejemplo:**
```python
from qzero.inference import InferenceEngine

engine = InferenceEngine(threshold=0.7)

packet = {
    "source": "192.168.1.1",
    "destination": "10.0.0.1",
    "protocol": "TCP",
    "size": 100,
    "payload": b"test",
    "metadata": {
        "ttl": 64,
        "flags": "S"
    }
}

is_anomaly, confidence, probability = engine.is_anomaly(packet)
```

#### `FastInferencePipeline`

Pipeline de inferencia rápido.

**Constructor:**
```python
FastInferencePipeline(engine, window_size=100, min_samples=10)
```

**Parámetros:**
- `engine` (InferenceEngine): Engine de inferencia
- `window_size` (int): Tamaño de ventana
- `min_samples` (int): Muestras mínimas

**Métodos:**
- `add_packet(packet)`: Añade paquete
- `get_stats()`: Obtiene estadísticas
- `train_from_window()`: Entrena con ventana
- `get_anomaly_pattern()`: Detecta patrones

---

## Módulo: response.py

### Clases

#### `Alert`

Representa una alerta.

**Atributos:**
- `id` (str): ID único
- `timestamp` (datetime): Timestamp
- `level` (AlertLevel): Nivel de severidad
- `alert_type` (AlertType): Tipo de alerta
- `source` (str): Fuente
- `destination` (str): Destino
- `message` (str): Mensaje
- `details` (dict): Detalles adicionales
- `confidence` (float): Confianza
- `is_acknowledged` (bool): Si está reconocida

**Método:**
- `to_dict()`: Convierte a diccionario

#### `AlertManager`

Gestor de alertas.

**Constructor:**
```python
AlertManager(alert_dir="/home/thempra/projects/qzero/alerts", max_age_hours=24)
```

**Parámetros:**
- `alert_dir` (str): Directorio de alertas
- `max_age_hours` (int): Máxima edad

**Métodos:**
- `create_alert(...)`: Crea alerta
- `check_anomaly(...)`: Verifica anomalía
- `acknowledge_alert(alert_id)`: Reconoce alerta
- `get_pending_alerts()`: Obtiene alertas pendientes
- `cleanup_old_alerts()`: Limpia alertas antiguas
- `get_stats()`: Obtiene estadísticas

**Ejemplo:**
```python
from qzero.response import AlertManager, AlertLevel, AlertType

manager = AlertManager()

alert = manager.create_alert(
    alert_type=AlertType.ANOMALY_DETECTED,
    level=AlertLevel.WARNING,
    source="192.168.1.1",
    destination="10.0.0.1",
    message="Tráfico anómalo detectado",
    confidence=0.8
)

manager.acknowledge_alert(alert.id)
```

#### `ResponseEngine`

Motor de respuesta automática.

**Constructor:**
```python
ResponseEngine(alert_manager)
```

**Métodos:**
- `register_callback(callback)`: Registra callback
- `process_alert(alert)`: Procesa alerta
- `auto_response(alert)`: Respuesta automática

---

## Módulo: containers.py

### Clases

#### `DockerNamespace`

Monitor de namespaces Docker.

**Constructor:**
```python
DockerNamespace(namespace="default")
```

**Parámetros:**
- `namespace` (str): Namespace de Docker

**Métodos:**
- `is_available()`: Verifica disponibilidad
- `list_containers()`: Lista contenedores
- `get_container_traffic(container_name)`: Obtiene tráfico
- `get_namespace_containers()`: Obtiene todos
- `get_container_stats(container_name)`: Obtiene stats

#### `KubeNamespace`

Monitor de namespaces Kubernetes.

**Constructor:**
```python
KubeNamespace(namespace="default")
```

**Parámetros:**
- `namespace` (str): Namespace de Kubernetes

**Métodos:**
- `is_available()`: Verifica disponibilidad
- `list_pods()`: Lista pods
- `get_pod_traffic(pod_name)`: Obtiene tráfico
- `get_namespace_pods()`: Obtiene todos
- `get_pod_stats(pod_name)`: Obtiene stats

#### `ContainerMonitor`

Monitor general de contenedores.

**Constructor:**
```python
ContainerMonitor(container_type, namespace="default")
```

**Parámetros:**
- `container_type` (ContainerType): Tipo de contenedor
- `namespace` (str): Namespace

**Métodos:**
- `get_containers()`: Lista contenedores
- `get_container_info(container_name)`: Información
- `get_all_containers_info()`: Todos
- `monitor_traffic(container_name, callback)`: Monitorea
- `start_namespace_monitor(interval, callback)`: Monitor namespace

#### `ContainerIntegration`

Integración de contenedores con QZero.

**Constructor:**
```python
ContainerIntegration()
```

**Métodos:**
- `is_available()`: Verifica disponibilidad
- `scan_containers()`: Escanea contenedores
- `get_container_alerts(container_name)`: Alertas
- `monitor_intra_container(container_name)`: Monitoreo intra-contenedor

---

## Enums

### `AlertLevel`

Niveles de alerta.
- `INFO`: Información
- `WARNING`: Advertencia
- `CRITICAL`: Crítico
- `SEVERE`: Severo

### `AlertType`

Tipos de alerta.
- `ANOMALY_DETECTED`: Anomalía detectada
- `PORT_SCAN`: Port scan
- `MALWARE_TRAFFIC`: Tráfico malware
- `SUSPICIOUS_PATTERN`: Patrón sospechoso
- `HIGH_RATE`: Tasa alta
- `NETWORK_SPAWN`: Spawn de red
- `RESOURCE_SPIKE`: Spike de recursos

### `ContainerType`

Tipos de contenedores.
- `DOCKER`: Docker
- `KUBERNETES`: Kubernetes
- `POD`: Pod

---

## Módulos CLI

### `qzero/cli/sniffer.py`

Funciones y clases para el CLI de sniffer.

### `qzero/cli/pipeline.py`

Funciones para el CLI de pipeline.

### `qzero/cli/inference.py`

Funciones para el CLI de inference.

### `qzero/cli/response.py`

Funciones para el CLI de response.

### `qzero/cli/containers.py`

Funciones para el CLI de containers.

---

## Comandos CLI

### `qzero sniffer list`
Lista interfaces de red.

### `qzero sniffer start --interface eth0 --promiscuous`
Inicia captura en tiempo real.

### `qzero pipeline run --interface eth0`
Ejecuta pipeline de ingestión.

### `qzero inference train --threshold 0.7`
Entrena modelo de inferencia.

### `qzero inference test --duration 50`
Testea modelo de inferencia.

### `qzero alerts list`
Lista alertas pendientes.

### `qzero alerts create --type anomaly_detected --level warning ...`
Crea alerta manual.

### `qzero containers list`
Lista contenedores.

### `qzero containers scan`
Escanea contenedores.

### `qzero containers info --container-type docker --container myapp`
Información de contenedor.

### `qzero containers monitor --container-type docker --container myapp`
Monitorea contenedor.

---

## Licencia

Este módulo es parte del proyecto QZero y está licenciado bajo la Licencia MIT.