# QZero

<p align="center">
  <strong>Sistema de Detección de Anomalías y Monitoreo de Seguridad</strong>
</p>

<p align="center">
  <em>IDS/IPS Enterprise-Ready para redes y contenedores</em>
</p>

---

## 📖 Descripción

QZero es un sistema de detección de anomalías y monitoreo de seguridad completo que opera en tiempo real. Proporciona:

- 🛡️ **Detección de amenazas** - Monitoreo proactivo de tráfico de red
- 🐳 **Soporte de contenedores** - Docker y Kubernetes namespaces
- 📊 **Inferencia ML** - Análisis inteligente con modelos predictivos
- 🚨 **Sistema de alertas** - Notificaciones automáticas y configurables
- 🔧 **CLI unificado** - Interfaz de comandos profesional
- 📝 **Logs centralizados** - Rotación automática y gestión de alertas

## 🎯 Características Principales

### Detección en Tiempo Real
- Captura de tráfico usando Scapy o TcpDump
- Ring buffer para ingestión eficiente
- Procesamiento por lotes
- Bajo overhead de CPU y RAM

### Motor de Inferencia
- InferenceEngine con soporte para modelos ML
- Feature extraction automática (packet size, protocol, TTL, etc.)
- Thresholds configurables
- Simulación y modo producción

### Sistema de Alertas
- AlertManager con reglas configurables
- Múltiples niveles de severidad (info, warning, critical, severe)
- Acciones automáticas (log, telegram, webhook)
- Reconocimiento de alertas
- Limpieza automática

### Soporte de Contenedores
- Docker namespaces (contenedores, tráfico, stats)
- Kubernetes pods (health, tráfico, endpoints)
- Monitoreo intra-contenedor
- Escaneo automático

### Logs y Monitoreo
- LogRotator automático
- QZeroLogger centralizado
- AlertManager para notificaciones
- Telegram integration

## 📋 Requisitos

### Sistema Operativo
- Linux (Ubuntu 20.04+, Debian, Fedora)
- macOS 12+
- Windows 10+ (WSL2 recomendado)

### Dependencias Python
```
Python >= 3.8
pip >= 21.0
```

### Dependencias de Red
```
scapy >= 2.5.0
numpy >= 1.21.0
```

### Herramientas Opcionales
```
tcpdump (para Fallback)
docker (para monitoreo de contenedores)
kubectl (para Kubernetes)
```

## 🚀 Instalación

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/qzero.git
cd qzero
```

### Paso 2: Crear entorno virtual (recomendado)

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# o
venv\Scripts\activate  # Windows
```

### Paso 3: Instalar dependencias

```bash
pip install -e .
```

### Paso 4: Verificar instalación

```bash
qzero --version
```

Output esperado:
```
QZero v5.0.0
```

## ⚙️ Configuración

### Configuración Básica

Crear archivo `~/.qzero/qzero.yaml`:

```yaml
# Configuración principal
interface: eth0
promiscuous: false
threshold: 0.7

# Directorios
log_dir: ~/.qzero/logs
alerts_dir: ~/.qzero/alerts

# Telegram (opcional)
telegram:
  bot_token: "TU_BOT_TOKEN"
  chat_id: "TU_CHAT_ID"

# Modelo ML (opcional)
model_path: ~/.qzero/models/anomaly_model.pkl
```

### Variables de Entorno

```bash
export QZERO_LOG_DIR="$HOME/.qzero/logs"
export QZERO_ALERTS_DIR="$HOME/.qzero/alerts"
export QZERO_INTERFACE="eth0"
```

## 📖 Uso

### Comandos Disponibles

```bash
# Ver versión
qzero --version

# Mostrar ayuda
qzero --help

# Mostrar ayuda de un comando
qzero sniffer --help
qzero inference train --help
qzero alerts list --help
```

### 1. Captura de Tráfico (Sniffer)

```bash
# Listar interfaces disponibles
qzero sniffer list

# Iniciar captura en tiempo real
qzero sniffer start --interface eth0

# Iniciar con modo promiscuo
qzero sniffer start --interface eth0 --promiscuous

# Iniciar con parámetros personalizados
qzero sniffer start \
  --interface eth0 \
  --promiscuous \
  --threshold 0.8 \
  --buffer 5000 \
  --interval 1.0
```

### 2. Pipeline de Ingesta en Memoria

```bash
# Ejecutar pipeline de ingestión
qzero pipeline run \
  --interface eth0 \
  --promiscuous \
  --buffer 10000 \
  --batch-size 100

# Ejecutar con stats en tiempo real
qzero pipeline run \
  --interface eth0 \
  --promiscuous \
  --buffer 10000 \
  --batch-size 100 \
  --verbose
```

### 3. Motor de Inferencia

```bash
# Entrenar modelo con datos simulados
qzero inference train \
  --train-mode simulation \
  --duration 100 \
  --threshold 0.7

# Entrenar con window-based
qzero inference train \
  --train-mode window \
  --window 100 \
  --min-samples 10

# Testear modelo
qzero inference test \
  --duration 50 \
  --verbose

# Ver estadísticas del modelo
qzero inference stats
```

### 4. Sistema de Alertas

```bash
# Listar alertas pendientes
qzero alerts list

# Crear alerta manual
qzero alerts create \
  --type anomaly_detected \
  --level warning \
  --source 192.168.1.1 \
  --destination 10.0.0.1 \
  --message "Tráfico anómalo detectado"

# Reconocer alertas
qzero alerts acknowledge <alert-id-1> <alert-id-2>

# Enviar alertas a Telegram
qzero alerts send-telegram \
  --bot-token "TU_BOT_TOKEN" \
  --chat-id "TU_CHAT_ID"
```

### 5. Contenedores

```bash
# Listar contenedores
qzero containers list

# Escanear contenedores
qzero containers scan

# Información de un contenedor
qzero containers info \
  --container-type docker \
  --container myapp \
  --namespace default

# Monitorear contenedor
qzero containers monitor \
  --container-type docker \
  --container myapp \
  --namespace default \
  --interval 1.0

# Generar alertas de contenedores
qzero containers alerts
```

### 6. Análisis de PCAP

```bash
# Analizar archivo PCAP
qzero analyze --pcap /ruta/a/archivo.pcap

# Analizar con parámetros personalizados
qzero analyze \
  --pcap /ruta/a/archivo.pcap \
  --output ./reports \
  --threshold 0.7
```

### 7. Logs y Monitoreo

```bash
# Listar archivos de log
qzero logs list

# Ver tail de logs
qzero logs tail --lines 50

# Rotar logs manualmente
qzero logs rotate
```

## 🏗️ Arquitectura

### Estructura del Sistema

```
qzero/
├── src/qzero/              # Módulos principales
│   ├── sniffer.py         # Módulo de captura
│   ├── pipeline.py        # Pipeline de ingestión
│   ├── inference.py       # Motor de inferencia
│   ├── response.py        # Sistema de alertas
│   ├── containers.py      # Soporte de contenedores
│   ├── logger.py          # Sistema de logs
│   ├── daemons.py         # Tareas autónomas
│   └── cli/               # CLI de comandos
│       ├── sniffer.py
│       ├── pipeline.py
│       ├── inference.py
│       ├── response.py
│       ├── containers.py
│       └── ...
├── tests/                 # Tests unitarios
├── reports/               # Reportes generados
├── docs/                  # Documentación
└── qzero-cli.py           # Entrada principal
```

### Flujo de Trabajo

```
[Tráfico de Red] 
    ↓
[Sniffer] → Captura paquetes
    ↓
[Pipeline] → Ring Buffer
    ↓
[Inference] → Feature extraction + Predicción
    ↓
[Response] → AlertManager
    ↓
[Notificaciones] → Telegram, Webhook, Logs
```

## 📊 Ejemplos de Uso

### Ejemplo 1: Monitoreo de Red Local

```bash
# Iniciar sniffer
qzero sniffer start --interface eth0 --promiscuous

# En otro terminal, ejecutar pipeline
qzero pipeline run --interface eth0

# Ver alertas
qzero alerts list
```

### Ejemplo 2: Monitoreo de Contenedores

```bash
# Escanear contenedores
qzero containers scan

# Monitorear contenedor específico
qzero containers monitor \
  --container-type docker \
  --container my-web-app \
  --namespace default
```

### Ejemplo 3: Detección de Anomalías

```bash
# Entrenar modelo
qzero inference train --train-mode simulation --duration 200

# Monitorear tráfico con inferencia
qzero pipeline run --interface eth0
```

## 🔒 Seguridad

### Consideraciones de Seguridad

- **Privacidad**: No capturar paquetes sensibles sin autorización
- **Logs**: Logs contienen datos sensibles - protegerlos
- **Alertas**: No exponer alertas en canales públicos
- **Configuración**: No compartir archivo `~/.qzero/qzero.yaml`

### Recomendaciones

1. Ejecutar QZero como usuario con privilegios mínimos necesarios
2. Configurar thresholds apropiados para minimizar falsos positivos
3. Monitorear regularmente los logs
4. Implementar rotación de logs y alertas
5. Usar modos promiscuos solo cuando sea necesario

## 🚀 Despliegue

### Instalación en Servidor

```bash
# 1. Instalar dependencias
sudo apt update
sudo apt install python3 python3-pip tcpdump

# 2. Crear usuario de servicio
sudo useradd -r -s /bin/false qzero

# 3. Clonar repositorio
sudo git clone https://github.com/tu-usuario/qzero.git /opt/qzero
cd /opt/qzero

# 4. Instalar dependencias
sudo pip install -e .

# 5. Crear directorios
sudo mkdir -p ~/.qzero/logs ~/.qzero/alerts ~/.qzero/models

# 6. Configurar servicio (systemd)
sudo systemctl daemon-reload
sudo systemctl enable qzero
sudo systemctl start qzero
```

### Docker Deployment (opcional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY qzero-cli.py ./

RUN pip install scapy

ENTRYPOINT ["qzero"]
```

```bash
# Construir imagen
docker build -t qzero:latest .

# Ejecutar
docker run -it --rm \
  --network host \
  -v ~/.qzero:/root/.qzero \
  qzero:latest sniffer start --interface eth0 --promiscuous
```

## 📈 Monitoreo

### Logs

Logs están ubicados en: `~/.qzero/logs/`

```bash
# Ver log principal
tail -f ~/.qzero/logs/qzero.log

# Ver log del sniffer
tail -f ~/.qzero/logs/sniffer.log

# Ver log de inferencia
tail -f ~/.qzero/logs/inference.log
```

### Alertas

Alertas se guardan en: `~/.qzero/alerts/`

```bash
# Listar alertas
qzero alerts list

# Ver alertas en JSON
ls ~/.qzero/alerts/
```

## 🛠️ Contribución

Contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crear rama para tu feature (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abrir un Pull Request

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver archivo `LICENSE` para más detalles.

## 🤝 Soporte

Para soporte, reportar bugs o sugerir mejoras:

- 📧 Email: thempra@overxet.com
- 🐛 Issues: https://github.com/tu-usuario/qzero/issues
- 💬 Chat: Discord (comunidad QZero)

## 📄 Referencias

- [Scapy Documentation](https://scapy.readthedocs.io/)
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Anomaly Detection Systems](https://arxiv.org/abs/2102.07728)

---

<p align="center">
  <strong>Hecho con ❤️ para la seguridad de tus redes</strong>
</p>

<p align="center">
  <em>QZero v5.0.0 - IDS/IPS Enterprise-Ready</em>
</p>