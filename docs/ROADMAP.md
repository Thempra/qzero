# Roadmap QZero: De Scripts a Solución Enterprise

## 📋 Resumen

Este documento detalla el plan de evolución de QZero desde un conjunto de scripts sueltos a una solución de detección de anomalías enterprise-ready.

## 🗺️ FASE 1: Reestructuración y Paquetización (The Foundation)

**Estado:** ✅ Completado

### Objetivo
Crear la estructura de un paquete Python profesional con CLI unificado, configuración centralizada y documentación completa.

### Tareas Completadas

#### ✅ Tarea 1.1: Estructura de directorios base
- Crear `src/qzero/` como paquete principal
- Organizar módulos: `core/`, `cli/`, `models/`, `utils/`, `sniffer/`
- Estructura limpia y mantenible

#### ✅ Tarea 1.2: Consolidación del CLI
- Unificar `qzero-cli.py` como entrada principal
- Comandos: `analyze`, `monitor`, `daemon`, `train`
- Ayuda integrada con argparse

#### ✅ Tarea 1.3: Refactorización de configuración
- Crear `src/qzero/config.py` con `QZeroConfig`
- Soporte para archivo YAML (`~/.qzero/qzero.yaml`)
- Variables de entorno para configuración

#### ✅ Tarea 1.4: Actualización de pyproject.toml
- Entrypoints configurados: `qzero`, `qzero-cli`, `qzero-analyze`, etc.
- Dependencias definidas
- Scripts de instalación y testing

## 🚧 FASE 2: Unificación de Tareas Autónomas (The Engine)

**Estado:** ✅ Completado

### Objetivo
Convertir múltiples scripts cron en un servicio unificado con scheduler interno.

### Tareas Completadas

#### ✅ Tarea 2.1: Consolidación de monitores
- Agrupar `autonomous-*.py` en `src/qzero/daemons.py`
- Crear módulos: `CodeQualityTask`, `AnomalyDetectionTask`, `DataEngineerTask`, `DailyReportTask`
- Sistema de ejecución de tareas

#### ✅ Tarea 2.2: Implementar un Scheduler interno
- Comando `qzero daemon run` con intervalo configurable
- Comando `qzero daemons run` para tareas autónomas
- Sistema de registro y logging
- Guardado de resultados en JSON

#### ✅ Tarea 2.3: Centralización de Logs y Alertas
- **LogRotator**: Rotación automática (10 MB, 7 días)
- **QZeroLogger**: Logger centralizado con formato consistente
- **AlertManager**: Gestión de alertas con archivos JSON
- **Telegram Integration**: Comando para enviar alertas a Telegram

## 🛡️ FASE 3: Análisis en Tiempo Real (The Shield)

**Estado:** 🚧 En Progreso (20%)

### Objetivo
Implementar captura en modo promiscuo para análisis desde el minuto 0 (IDS/IPS real).

### Tareas Completadas

#### ✅ Tarea 3.1: Módulo de Captura de Red
- **ScapySniffer**: Captura usando Scapy
- **TcpDumpSniffer**: Captura usando TcpDump
- **BaseSniffer**: Clase base con funcionalidad común
- **NetworkInterface**: Gestor de interfaces de red
- **Packet**: Representación de paquetes capturados
- **RealTimeSniffer**: Sniffer en tiempo real con detección

### Tareas Pendientes

#### [ ] Tarea 3.2: Pipeline de Ingesta en Memoria
- Ring buffer para paquetes capturados
- Procesamiento por lotes sin escribir PCAPs temporales
- Bajo overhead de CPU y RAM

#### [ ] Tarea 3.3: Integración de Inferencia Rápida
- Flujo de paquetes en tiempo real
- Conexión con motor de inferencia de anomalías
- Configuración de thresholds para minimizar falsos positivos

#### [ ] Tarea 3.4: Motor de Respuesta (Alertas)
- Detección de anomalías críticas
- Disparar eventos: logs, webhooks, notificaciones Telegram
- Reglas de respuesta configurables

#### [ ] Tarea 3.5: Soporte para Contenedores
- Namespaces de red de Docker
- Pods de Kubernetes
- Monitorización de tráfico intra-contenedor

## 📊 Métricas de Progreso

| Fase | Tareas | Completadas | Progreso |
|------|--------|-------------|----------|
| FASE 1 | 4 | 4 | 100% ✅ |
| FASE 2 | 3 | 3 | 100% ✅ |
| FASE 3 | 5 | 1 | 20% 🚧 |
| **TOTAL** | **12** | **8** | **67%** |

## 🎯 Próximos Pasos

1. **FASE 3 - Tarea 3.2**: Pipeline de ingestión en memoria
2. **FASE 3 - Tarea 3.3**: Integración de inferencia rápida
3. **FASE 3 - Tarea 3.4**: Motor de respuesta
4. **FASE 3 - Tarea 3.5**: Soporte para contenedores

## 📅 Timeline Estimado

- **FASE 1**: ✅ Completado (1-2 días)
- **FASE 2**: ✅ Completado (2-3 días)
- **FASE 3**: 🚧 Estimado 1-2 semanas (50% completado)

## 📦 Versiones

- **v3.0.0**: FASE 3 iniciada - Módulo de Captura de Network
- **v2.3.0**: FASE 2 completada - Logs y Alertas centralizados
- **v2.2.0**: FASE 2 Tareas 2.1-2.2 - Daemons y Scheduler
- **v2.1.0**: FASE 1 completada - CLI unificado y paquetización

---

**Última actualización:** 2026-03-05
**Versión actual:** 3.0.0
**Progreso total:** 67% (8/12 tareas)