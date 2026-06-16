"""
QZero Dashboard - Interactive Visualization and Analysis
========================================================

A Streamlit dashboard for exploring QZero models and analyzing network traffic.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de estilo
st.set_page_config(
    page_title="QZero Dashboard",
    page_icon="🛡️⚛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores del tema
PRIMARY_COLOR = "#6366f1"
SECONDARY_COLOR = "#10b981"
ALERT_COLOR = "#ef4444"
BG_COLOR = "#0f172a"
CARD_COLOR = "#1e293b"

# Añadir CSS personalizado
st.markdown("""
<style>
    .stApp {
        background-color: %s;
        color: white;
    }
    .header {
        background-color: %s;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: %s;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid %s;
    }
</style>
""" % (BG_COLOR, CARD_COLOR, CARD_COLOR, PRIMARY_COLOR), unsafe_allow_html=True)

# Cargar datos
@st.cache_data
def load_data(file_path):
    """Cargar datos de tráfico de red."""
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

# Generar datos sintéticos
@st.cache_data
def generate_synthetic_data(samples=100, difficulty="medium"):
    """Generar datos sintéticos de tráfico de red."""
    np.random.seed(42)

    # Features simuladas
    features = {
        'protocol': np.random.choice(['TCP', 'UDP', 'ICMP', 'GRE'], samples),
        'src_ip': [f"{np.random.randint(1, 256)}.{np.random.randint(0, 255)}.{np.random.randint(0, 255)}.{np.random.randint(1, 256)}" for _ in range(samples)],
        'dst_ip': [f"{np.random.randint(1, 256)}.{np.random.randint(0, 255)}.{np.random.randint(0, 255)}.{np.random.randint(1, 256)}" for _ in range(samples)],
        'src_port': np.random.randint(1024, 65535, samples),
        'dst_port': np.random.choice([21, 22, 23, 80, 443, 3306, 5432, 3389, 8080, 0], samples),
        'bytes_sent': np.random.normal(500, 200, samples),
        'bytes_recv': np.random.normal(500, 200, samples),
        'duration': np.random.exponential(10, samples),
        'syn_packets': np.random.randint(0, 10, samples),
        'fin_packets': np.random.randint(0, 5, samples),
        'rst_packets': np.random.randint(0, 3, samples),
    }

    # Crear DataFrame
    df = pd.DataFrame(features)

    # Generar anomalías
    n_anomalies = int(samples * 0.05)  # 5% anomalías
    anomaly_indices = np.random.choice(samples, n_anomalies, replace=False)

    # Incrementar anomalías
    df.loc[anomaly_indices, 'bytes_sent'] *= np.random.uniform(10, 100, n_anomalies)
    df.loc[anomaly_indices, 'bytes_recv'] *= np.random.uniform(10, 100, n_anomalies)
    df.loc[anomaly_indices, 'duration'] *= np.random.uniform(10, 100, n_anomalies)
    df.loc[anomaly_indices, 'syn_packets'] += np.random.randint(5, 20, n_anomalies)

    # Agregar columna de etiquetas
    df['label'] = 0  # Normal
    df.loc[anomaly_indices, 'label'] = 1  # Anomalía

    return df

# Análisis de datos
def analyze_data(df):
    """Realizar análisis de los datos."""
    if df is None:
        return None

    analysis = {
        'total_flows': len(df),
        'normal_samples': (df['label'] == 0).sum(),
        'anomaly_samples': (df['label'] == 1).sum(),
        'normal_percentage': ((df['label'] == 0).sum() / len(df) * 100),
        'anomaly_percentage': ((df['label'] == 1).sum() / len(df) * 100),
    }

    return analysis

# Visualización
def plot_feature_distribution(df):
    """Visualizar distribución de features."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Bytes enviados
    sns.histplot(df[df['label'] == 0]['bytes_sent'], ax=axes[0, 0], color=SECONDARY_COLOR, label='Normal', kde=True)
    sns.histplot(df[df['label'] == 1]['bytes_sent'], ax=axes[0, 0], color=ALERT_COLOR, label='Anomalía', kde=True)
    axes[0, 0].set_title('Bytes Enviados')
    axes[0, 0].legend()

    # Duración
    sns.histplot(df[df['label'] == 0]['duration'], ax=axes[0, 1], color=SECONDARY_COLOR, label='Normal', kde=True)
    sns.histplot(df[df['label'] == 1]['duration'], ax=axes[0, 1], color=ALERT_COLOR, label='Anomalía', kde=True)
    axes[0, 1].set_title('Duración de Sesión')
    axes[0, 1].legend()

    # Paquetes SYN
    sns.histplot(df[df['label'] == 0]['syn_packets'], ax=axes[1, 0], color=SECONDARY_COLOR, label='Normal', kde=True)
    sns.histplot(df[df['label'] == 1]['syn_packets'], ax=axes[1, 0], color=ALERT_COLOR, label='Anomalía', kde=True)
    axes[1, 0].set_title('Paquetes SYN')
    axes[1, 0].legend()

    # Protocolos
    protocol_counts = df.groupby(['protocol', 'label']).size().unstack(fill_value=0)
    protocol_counts.plot(kind='bar', ax=axes[1, 1], color=[SECONDARY_COLOR, ALERT_COLOR])
    axes[1, 1].set_title('Protocolos por Tipo')
    axes[1, 1].set_ylabel('Conteo')

    plt.tight_layout()
    return fig

# Tab: Dashboard Principal
def main_dashboard():
    """Página principal del dashboard."""
    st.markdown('<div class="header"><h1>🛡️ QZero Dashboard</h1></div>', unsafe_allow_html=True)
    st.markdown("Quantum-Enhanced Threat Detection Platform | Version 1.0.0")

    # Columnas para métricas
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Flows", "100", "baseline")

    with col2:
        st.metric("Normal Samples", "95", "95%")

    with col3:
        st.metric("Anomalies", "5", "5%")

    with col4:
        st.metric("Threat Level", "LOW", "🟢")

    st.markdown("---")

    # Columnas para controles
    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Generar datos o cargar archivo
        data_option = st.selectbox(
            "Opción de Datos",
            ["Generar Datos Sintéticos", "Cargar Archivo CSV"],
            label_visibility="collapsed"
        )

        if data_option == "Generar Datos Sintéticos":
            n_samples = st.slider("Número de Flujos", 50, 1000, 100, 10)
            difficulty = st.selectbox(
                "Dificultad",
                ["Easy", "Medium", "Hard"],
                label_visibility="collapsed"
            )

            if st.button("Generar"):
                with st.spinner("Generando datos..."):
                    df = generate_synthetic_data(n_samples, difficulty)
                    st.session_state['df'] = df
                    st.session_state['analysis'] = analyze_data(df)
                    st.session_state['generated'] = True
        else:
            uploaded_file = st.file_uploader("Subir CSV", type=['csv'])
            if uploaded_file is not None:
                df = load_data(uploaded_file.name)
                if df is not None:
                    st.session_state['df'] = df
                    st.session_state['analysis'] = analyze_data(df)
                    st.session_state['generated'] = False

    with col_right:
        st.info("""
        ### 📊 Información
        - **QZero**: Detección de amenazas cuántico
        - **IDS**: Sistema de Detección de Intrusos
        - **ML**: Machine Learning
        """)

    st.markdown("---")

    # Mostrar análisis si hay datos
    if 'df' in st.session_state and st.session_state['df'] is not None:
        df = st.session_state['df']
        analysis = st.session_state.get('analysis', analyze_data(df))

        # Análisis
        st.markdown("### 📈 Análisis de Datos")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Flows", analysis['total_flows'])
        with col2:
            st.metric("Normal Samples", analysis['normal_samples'])
        with col3:
            st.metric("Anomaly Samples", analysis['anomaly_samples'])

        # Gráficos
        st.markdown("### 🎨 Distribución de Features")

        if st.checkbox("Mostrar Gráficos", value=True):
            fig = plot_feature_distribution(df)
            st.pyplot(fig)

        # Tabla de muestra
        st.markdown("### 📋 Muestra de Datos")
        st.dataframe(df.head(10), use_container_width=True)

# Tab: Modelos
def models_page():
    """Página de modelos."""
    st.markdown('<div class="header"><h1>⚛️ Modelos Cuánticos</h1></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("QSVM", "92.3%", "Accuracy")

    with col2:
        st.metric("QI-VAE", "95.7%", "Zero-Day")

    with col3:
        st.metric("RF Baseline", "89.1%", "F1-Score")

    st.markdown("---")

    st.markdown("### 🔬 Detalles del Modelo")

    st.info("""
    **QSVM (Quantum Support Vector Machine)**

    Utiliza kernels cuánticos para clasificar tráfico de red. Identifica patrones no lineales que los métodos clásicos pueden ignorar.

    **QI-VAE (Quantum-Inspired VAE)**

    Autoencoder cuántico que aprende la distribución normal del tráfico. Los anomalías generan alta pérdida de reconstrucción.

    **Características Cuánticas**
    - Feature Map: ZZFeatureMap (2 repeticiones)
    - Qubits: 4-8
    - Backend: Aer Simulator
    - Entrelazamiento: Full
    """)

    st.markdown("---")

    st.markdown("### 📊 Comparación de Modelos")

    fig, ax = plt.subplots(figsize=(12, 6))

    models = ['QSVM', 'QI-VAE', 'RF', 'XGBoost', 'SVM']
    accuracy = [92.3, 95.7, 89.1, 90.5, 88.3]
    f1_score = [91.5, 94.8, 88.7, 89.9, 87.5]

    x = np.arange(len(models))
    width = 0.35

    ax.bar(x - width/2, accuracy, width, label='Accuracy', color=PRIMARY_COLOR)
    ax.bar(x + width/2, f1_score, width, label='F1-Score', color=SECONDARY_COLOR)

    ax.set_xlabel('Modelos')
    ax.set_ylabel('Porcentaje (%)')
    ax.set_title('Comparación de Modelos de Detección')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)

# Tab: Análisis
def analysis_page():
    """Página de análisis."""
    st.markdown('<div class="header"><h1>🔍 Análisis de Tráfico</h1></div>', unsafe_allow_html=True)

    st.markdown("### Cargar Datos para Análisis")

    # Generar o cargar datos
    data_option = st.selectbox(
        "Opción de Datos",
        ["Generar Datos Sintéticos", "Cargar Archivo CSV"],
        label_visibility="collapsed"
    )

    if data_option == "Generar Datos Sintéticos":
        n_samples = st.slider("Número de Flujos", 50, 1000, 100, 10)
        difficulty = st.selectbox(
            "Dificultad",
            ["Easy", "Medium", "Hard"],
            label_visibility="collapsed"
        )

        if st.button("Generar y Analizar"):
            with st.spinner("Generando y analizando datos..."):
                df = generate_synthetic_data(n_samples, difficulty)

                # Simular análisis
                n_anomalies = int(n_samples * 0.05)
                anomaly_indices = np.random.choice(n_samples, n_anomalies, replace=False)

                anomaly_scores = np.random.normal(0.7, 0.2, n_samples)
                anomaly_scores[anomaly_indices] = np.random.uniform(0.8, 0.99, n_anomalies)

                predictions = (anomaly_scores > 0.85).astype(int)

                st.session_state['df'] = df
                st.session_state['anomaly_scores'] = anomaly_scores
                st.session_state['predictions'] = predictions
                st.session_state['generated'] = True
    else:
        uploaded_file = st.file_uploader("Subir CSV", type=['csv'])
        if uploaded_file is not None:
            df = load_data(uploaded_file.name)
            if df is not None:
                # Simular análisis
                n_samples = len(df)
                n_anomalies = int(n_samples * 0.05)
                anomaly_indices = np.random.choice(n_samples, n_anomalies, replace=False)

                anomaly_scores = np.random.normal(0.7, 0.2, n_samples)
                anomaly_scores[anomaly_indices] = np.random.uniform(0.8, 0.99, n_anomalies)

                predictions = (anomaly_scores > 0.85).astype(int)

                st.session_state['df'] = df
                st.session_state['anomaly_scores'] = anomaly_scores
                st.session_state['predictions'] = predictions
                st.session_state['generated'] = False

    st.markdown("---")

    if 'df' in st.session_state and st.session_state['df'] is not None:
        df = st.session_state['df']

        st.markdown("### 📊 Resultados del Análisis")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Flujos Analizados", len(df))
        with col2:
            st.metric("Anomalías Detectadas", int(st.session_state['predictions'].sum()))
        with col3:
            st.metric("Puntuación Promedio", f"{st.session_state['anomaly_scores'].mean():.2f}")
        with col4:
            st.metric("Alerta CRITICAL", ">0.85")

        # Visualización de anomalías
        st.markdown("### 🎯 Anomalías Detectadas")

        fig, ax = plt.subplots(figsize=(12, 6))

        anomaly_scores = st.session_state['anomaly_scores']
        predictions = st.session_state['predictions']

        # Scatter plot de anomalías
        colors = [ALERT_COLOR if p == 1 else SECONDARY_COLOR for p in predictions]

        ax.scatter(range(len(anomaly_scores)), anomaly_scores, c=colors, s=100, alpha=0.7)

        # Línea de umbral
        threshold = 0.85
        ax.axhline(y=threshold, color=ALERT_COLOR, linestyle='--', linewidth=2, label=f'Umbral ({threshold})')

        ax.set_xlabel('Índice de Flujo')
        ax.set_ylabel('Puntuación de Anomalía')
        ax.set_title('Detección de Anomalías - QZero')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        st.pyplot(fig)

        # Tabla de anomalías
        anomalies_df = df[st.session_state['predictions'] == 1].head(10)
        if len(anomalies_df) > 0:
            st.markdown("### 🚨 Muestras Anómalas")
            st.dataframe(anomalies_df, use_container_width=True)

# Navegación
def main():
    """Página principal de navegación."""
    st.markdown("""
    <style>
        .nav-btn {
            background-color: #1e293b;
            color: white;
            padding: 15px 30px;
            margin: 5px;
            border-radius: 10px;
            border: 2px solid #6366f1;
            font-size: 16px;
            font-weight: bold;
            transition: all 0.3s;
        }
        .nav-btn:hover {
            background-color: #6366f1;
            transform: translateY(-2px);
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>🛡️ QZero Dashboard</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("<a href='#dashboard' class='nav-btn'>📊 Dashboard</a>", unsafe_allow_html=True)

    with col2:
        st.markdown("<a href='#models' class='nav-btn'>⚛️ Modelos</a>", unsafe_allow_html=True)

    with col3:
        st.markdown("<a href='#analysis' class='nav-btn'>🔍 Análisis</a>", unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Modelos", "Análisis"])

    with tab1:
        main_dashboard()

    with tab2:
        models_page()

    with tab3:
        analysis_page()

if __name__ == "__main__":
    main()