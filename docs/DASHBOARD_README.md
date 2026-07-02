# QZero Dashboard

Dashboard interactivo para visualizar y analizar QZero.

## 🚀 Características

- **Dashboard Principal**: Visualización de datos de tráfico de red
- **Modelos Cuánticos**: Comparación de QSVM, QI-VAE y baselines clásicos
- **Análisis de Tráfico**: Simulación de detección de anomalías

## 📦 Requisitos

```bash
pip install streamlit pandas numpy matplotlib seaborn
```

## 🎮 Uso

### Modo Local

```bash
# Activar entorno virtual si existe
source venv/bin/activate  # o venv/Scripts/activate en Windows

# Ejecutar dashboard
streamlit run dashboard.py
```

### Modo Docker

```bash
docker-compose up --build dashboard
```

La dashboard estará disponible en `http://localhost:8501`

## 🎨 Tema

- **Tema**: Oscuro (Dark mode)
- **Colores**:
  - Azul cuántico (#6366f1)
  - Verde éxito (#10b981)
  - Rojo alerta (#ef4444)

## 📊 Funcionalidades

### Dashboard Principal
- Generar datos sintéticos de tráfico de red
- Cargar archivos CSV personalizados
- Visualizar distribución de features
- Tabla de muestra de datos

### Modelos
- Comparación visual de modelos
- Métricas de rendimiento
- Información sobre características cuánticas

### Análisis
- Simulación de detección de anomalías
- Visualización de puntuaciones
- Identificación de muestras anómalas

## 🛠️ Estructura

```
dashboard.py
├── Funciones de carga de datos
├── Generador de datos sintéticos
├── Funciones de análisis
├── Visualización de gráficos
└── Páginas del dashboard
```

## 📝 Notas

- El dashboard es una interfaz de visualización
- El análisis real requiere modelos entrenados
- Los datos sintéticos son para demostración

## 🔗 Enlaces

- [QZero Project](../)
- [API Documentation](../docs/API.md)
- [Streamlit Docs](https://docs.streamlit.io)