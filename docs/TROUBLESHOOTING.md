# Troubleshooting - QZero

## Problemas Comunes

### 1. ImportError: No module named 'scapy'

**Error:**
```
ModuleNotFoundError: No module named 'scapy'
```

**Solución:**
```bash
pip install scapy
```

O usar tcpdump como fallback:
```bash
sudo apt install tcpdump
```

---

### 2. Scapy no detecta la interfaz

**Error:**
```
RuntimeError: La interfaz eth0 no está activa
```

**Solución:**
```bash
# Verificar interfaces disponibles
ip addr show

# O usar una interfaz diferente
qzero sniffer start --interface docker0

# O habilitar la interfaz
sudo ip link set eth0 up
```

---

### 3. Permisos de root necesarios

**Error:**
```
Permission denied: Impossible to open device eth0 for sniffing
```

**Solución:**
```bash
# Método 1: Usar sudo
sudo qzero sniffer start --interface eth0

# Método 2: Ejecutar como root
sudo python3 -m qzero.cli.sniffer start --interface eth0

# Método 3: Usar sudo para tcpdump
sudo tcpdump -i eth0
```

---

### 4. TcpDump no disponible

**Error:**
```
FileNotFoundError: tcpdump not found
```

**Solución:**
```bash
# En Debian/Ubuntu
sudo apt install tcpdump

# En Fedora/RHEL
sudo dnf install tcpdump

# En macOS
brew install tcpdump
```

---

### 5. Importaciones duplicadas/recursión

**Error:**
```
RecursionError: maximum recursion depth exceeded
```

**Solución:**
Asegúrate de que los symlinks en `~/.local/bin/` no tengan bucles. Ejecuta:
```bash
~/.local/bin/qzero --version
```

Si falla, reinstala el CLI:
```bash
rm ~/.local/bin/qzero
python3 qzero-cli.py > ~/.local/bin/qzero
chmod +x ~/.local/bin/qzero
```

---

### 6. Telegram bot no responde

**Error:**
```
TelebotError: 401 Unauthorized
```

**Solución:**
1. Verifica el bot token
2. Verifica el chat ID
3. Genera un nuevo bot: [@BotFather](https://t.me/BotFather)
4. Configura correctamente en `~/.qzero/qzero.yaml`

```yaml
telegram:
  bot_token: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  chat_id: "4343515"
```

---

### 7. AlertManager no guarda alertas

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/tmp/qzero-alerts-test'
```

**Solución:**
```bash
# Crear directorio con permisos correctos
mkdir -p ~/.qzero/alerts
chmod 755 ~/.qzero/alerts
```

---

### 8. Docker no se detecta

**Error:**
```
Docker not available - tcpdump not found
```

**Solución:**
```bash
# Verificar Docker está corriendo
sudo systemctl status docker

# Si no está, iniciarlo
sudo systemctl start docker

# Verificar acceso del usuario a Docker
groups $USER | grep docker

# Si no, agregar usuario
sudo usermod -aG docker $USER
```

---

### 9. KubeConfig no se encuentra

**Error:**
```
kubectl: command not found
```

**Solución:**
```bash
# Instalar kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Configurar kubeconfig
export KUBECONFIG=~/.kube/config
```

---

### 10. Logs no se rotan

**Error:**
```
RuntimeError: Cannot rotate logs - file not found
```

**Solución:**
```bash
# Crear directorio de logs
mkdir -p ~/.qzero/logs

# Verificar permisos
chmod 755 ~/.qzero/logs
```

---

### 11. Memoria insuficiente

**Error:**
```
MemoryError: Buffer lleno
```

**Solución:**
```bash
# Reducir el tamaño del buffer
qzero sniffer start --interface eth0 --buffer 1000

# O en pipeline
qzero pipeline run --interface eth0 --buffer 5000
```

---

### 12. CPU alto durante captura

**Error:**
```
CPU usage: 95% (high)
```

**Solución:**
1. Reducir el intervalo de captura
2. Reducir el tamaño del buffer
3. Usar TcpDump en lugar de Scapy (menos CPU)
4. Ejecutar en sistema con suficiente RAM

```bash
# Ejecutar con menor intervalo
qzero sniffer start --interface eth0 --interval 0.5

# Usar TcpDump
qzero sniffer start --interface eth0 --promiscuous
# (TcpDump usa menos CPU que Scapy)
```

---

### 13. Modelos ML no cargan

**Error:**
```
ModelNotFoundError: No se pudo cargar el modelo
```

**Solución:**
```bash
# Crear directorio de modelos
mkdir -p ~/.qzero/models

# Entrenar modelo nuevo
qzero inference train --train-mode simulation --duration 200

# Verificar archivo de modelo
ls -lh ~/.qzero/models/anomaly_model.pkl
```

---

### 14. Contenedores no se escanean

**Error:**
```
ContainerScanError: Docker not available
```

**Solución:**
```bash
# Verificar disponibilidad
qzero containers scan

# Verificar logs
tail -f ~/.qzero/logs/containers.log
```

---

## Depuración

### Habilitar logging detallado

```bash
qzero sniffer start --interface eth0 --verbose
qzero pipeline run --interface eth0 --verbose
qzero inference train --verbose
```

### Ver logs en tiempo real

```bash
# Log principal
tail -f ~/.qzero/logs/qzero.log

# Log específico
tail -f ~/.qzero/logs/sniffer.log
tail -f ~/.qzero/logs/pipeline.log
tail -f ~/.qzero/logs/inference.log
tail -f ~/.qzero/logs/response.log
tail -f ~/.qzero/logs/containers.log
```

### Ejecutar tests

```bash
# Tests básicos
python3 tests/test_basic.py

# Tests FASE 3
python3 tests/test_fase3.py

# Tests CLI
python3 tests/test_cli.py

# Todos los tests
python3 -m pytest tests/
```

### Verificar instalación

```bash
# Verificar versión
qzero --version

# Verificar módulos
python3 -c "from qzero import *; print('All modules loaded')"

# Verificar CLI
qzero --help
```

---

## Comandos de Diagnóstico

### Verificar configuración

```bash
# Ver variables de entorno
echo $QZERO_LOG_DIR
echo $QZERO_ALERTS_DIR
echo $QZERO_INTERFACE

# Ver archivo de configuración
cat ~/.qzero/qzero.yaml
```

### Verificar recursos

```bash
# RAM
free -h

# CPU
top

# Disco
df -h

# Red
ip addr show
```

### Verificar servicios

```bash
# Docker
docker --version
docker ps

# Kubernetes
kubectl version --client
kubectl get pods

# Scapy
python3 -c "import scapy; print(scapy.__version__)"
```

---

## Reportar Bugs

Si encuentras un problema que no está documentado aquí:

1. **Recopilar información:**
   ```bash
   qzero --version
   python3 -m pytest tests/test_fase3.py
   tail -50 ~/.qzero/logs/qzero.log
   ```

2. **Añadir en el issue:**
   - Pasos para reproducir
   - Comando exacto usado
   - Error completo
   - Output de logs
   - Sistemas operativos/distribuciones

3. **Enviar pull request:**
   - Añadir test reproduciendo el bug
   - Documentar la solución

---

## Recursos de Ayuda

- 📚 [README.md](README.md)
- 🔍 [API.md](API.md)
- 🛠️ [Troubleshooting.md](TROUBLESHOOTING.md)
- 📖 [Plan de implementación](implementation-plan.md)

---

**Versión:** QZero v5.0.0