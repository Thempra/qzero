"""
QZero Dashboard - Quantum Zero-Day Detection
Interactive visualization and model comparison
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from qzero.preprocessing.data_loader import generate_synthetic_data, DataLoader
from qzero.preprocessing.feature_engineering import FeatureEngineer
from pathlib import Path
from qzero.classical.baseline import ClassicalBaseline, run_all_baselines
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

# Page config
st.set_page_config(
    page_title="QZero - Quantum Zero-Day Detection",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e, #2d2d44);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #3d3d5c;
    }
    .stMetric {
        background: linear-gradient(135deg, #1e1e2e, #2d2d44);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #3d3d5c;
    }
    .success-box {
        background: linear-gradient(135deg, #064e3b, #065f46);
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #10b981;
    }
    .quantum-box {
        background: linear-gradient(135deg, #312e81, #3730a3);
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #6366f1;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Header
    st.markdown('<h1 class="main-header">⚛️ QZero Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #888;">Quantum Zero-Day Detection System</p>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/quantum-computing.png", width=80)
        st.title("Configuration")
        
        st.subheader("📊 Data Settings")
        
        # Check if real dataset exists
        data_dir = Path(__file__).parent.parent / "data" / "raw"
        real_dataset_exists = (data_dir / "final(2).csv").exists()
        
        data_source = st.radio(
            "Data Source",
            ["Synthetic", "Real (UGRansome)"] if real_dataset_exists else ["Synthetic"],
            help="UGRansome dataset contains ~149K ransomware samples"
        )
        
        if data_source == "Synthetic":
            n_samples = st.slider("Number of samples", 100, 5000, 1000, 100)
            difficulty = st.select_slider("Difficulty", ["easy", "medium", "hard"], "medium")
        else:
            n_samples = st.slider("Sample limit (0=all)", 0, 50000, 10000, 1000,
                                  help="Limit samples for faster processing (0 = use all ~149K)")
            difficulty = None  # Not applicable for real data
        
        st.subheader("⚛️ Quantum Settings")
        n_qubits = st.slider("Number of qubits", 2, 8, 4)
        feature_map = st.selectbox("Feature Map", ["ZZ", "ZZZ", "Pauli", "Z"])
        reps = st.slider("Repetitions", 1, 4, 2)
        
        st.subheader("🎯 Actions")
        run_experiment = st.button("🚀 Run Full Experiment", type="primary", use_container_width=True)
        
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Data", "🤖 Classical", "⚛️ Quantum", "📈 Results"])
    
    # Initialize session state
    if 'data_generated' not in st.session_state:
        st.session_state.data_generated = False
    if 'classical_results' not in st.session_state:
        st.session_state.classical_results = None
    if 'quantum_results' not in st.session_state:
        st.session_state.quantum_results = None
    
    # Tab 1: Data
    with tab1:
        st.header("📊 Data Generation & Exploration")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if data_source == "Synthetic":
                if st.button("Generate Synthetic Data", type="primary"):
                    with st.spinner("Generating data..."):
                        X, y = generate_synthetic_data(n_samples=n_samples, difficulty=difficulty)
                        st.session_state.X = X
                        st.session_state.y = y
                        st.session_state.data_generated = True
                        st.session_state.data_source = "synthetic"
                    st.success(f"✅ Generated {n_samples} samples with {X.shape[1]} features")
            else:
                if st.button("Load UGRansome Dataset", type="primary"):
                    with st.spinner("Loading real dataset..."):
                        loader = DataLoader()
                        X, y = loader.load_ugransome()
                        
                        # Apply sample limit if specified
                        if n_samples > 0 and n_samples < len(X):
                            # Stratified sampling to maintain class distribution
                            from sklearn.model_selection import train_test_split
                            X, _, y, _ = train_test_split(
                                X, y, train_size=n_samples, stratify=y, random_state=42
                            )
                        
                        st.session_state.X = X
                        st.session_state.y = y
                        st.session_state.data_generated = True
                        st.session_state.data_source = "real"
                        st.session_state.label_names = loader.get_label_names()
                    st.success(f"✅ Loaded {len(X)} samples with {X.shape[1]} features")
        
        with col2:
            if st.session_state.data_generated:
                st.metric("Samples", len(st.session_state.X))
                st.metric("Features", st.session_state.X.shape[1])
                if hasattr(st.session_state, 'data_source'):
                    st.metric("Source", st.session_state.data_source.title())
        
        if st.session_state.data_generated:
            st.subheader("Class Distribution")
            
            # Class names depend on data source
            if hasattr(st.session_state, 'data_source') and st.session_state.data_source == "real":
                label_names = st.session_state.get('label_names', {})
                class_counts = pd.Series(st.session_state.y).value_counts().sort_index()
                class_labels = [label_names.get(i, f"Class {i}") for i in class_counts.index]
            else:
                class_names = ["Normal", "Signature", "Zero-Day"]
                class_counts = pd.Series(st.session_state.y).value_counts().sort_index()
                class_labels = [class_names[i] if i < len(class_names) else f"Class {i}" for i in class_counts.index]
            
            fig = px.pie(
                values=class_counts.values,
                names=class_labels,
                color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
                hole=0.4
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Feature engineering preview
            st.subheader("Feature Engineering (PCA)")
            engineer = FeatureEngineer(n_qubits=min(3, n_qubits), reduction_method='pca')
            X_reduced = engineer.fit_transform(st.session_state.X)
            
            # Map class indices to names for the scatter plot
            if hasattr(st.session_state, 'data_source') and st.session_state.data_source == "real":
                label_names = st.session_state.get('label_names', {})
                class_mapping = {i: label_names.get(i, f"Class {i}") for i in st.session_state.y.unique()}
            else:
                class_names = ["Normal", "Signature", "Zero-Day"]
                class_mapping = {i: class_names[i] if i < len(class_names) else f"Class {i}" 
                                for i in st.session_state.y.unique()}
            
            df_pca = pd.DataFrame(X_reduced[:, :2], columns=['PC1', 'PC2'])
            df_pca['Class'] = [class_mapping[c] for c in st.session_state.y]
            
            fig = px.scatter(
                df_pca, x='PC1', y='PC2', color='Class',
                color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444", "#8b5cf6"],
                opacity=0.7
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,30,46,1)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 2: Classical Models
    with tab2:
        st.header("🤖 Classical Machine Learning Baselines")
        
        if not st.session_state.data_generated:
            st.warning("⚠️ Generate data first in the Data tab")
        else:
            if st.button("Train Classical Models", type="primary"):
                with st.spinner("Training models..."):
                    # Feature engineering
                    engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method='pca')
                    X_reduced = engineer.fit_transform(st.session_state.X)
                    
                    # Split
                    X_train, X_test, y_train, y_test = train_test_split(
                        X_reduced, st.session_state.y, test_size=0.2, random_state=42
                    )
                    
                    # Train all baselines
                    results = run_all_baselines(X_train, y_train, X_test, y_test)
                    st.session_state.classical_results = results
                    st.session_state.X_train = X_train
                    st.session_state.X_test = X_test
                    st.session_state.y_train = y_train
                    st.session_state.y_test = y_test
                
                st.success("✅ Classical models trained!")
            
            if st.session_state.classical_results:
                # Results table
                results_df = pd.DataFrame([
                    {
                        "Model": r.model_name,
                        "Accuracy": f"{r.accuracy:.4f}",
                        "Precision": f"{r.precision:.4f}",
                        "Recall": f"{r.recall:.4f}",
                        "F1-Score": f"{r.f1:.4f}",
                        "Time (s)": f"{r.train_time:.3f}"
                    }
                    for r in st.session_state.classical_results
                ])
                
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                
                # Bar chart comparison
                fig = go.Figure()
                models = [r.model_name for r in st.session_state.classical_results]
                metrics = ['accuracy', 'precision', 'recall', 'f1']
                colors = ['#6366f1', '#8b5cf6', '#a855f7', '#c084fc']
                
                for i, metric in enumerate(metrics):
                    values = [getattr(r, metric) for r in st.session_state.classical_results]
                    fig.add_trace(go.Bar(
                        name=metric.replace('_', ' ').title(),
                        x=models,
                        y=values,
                        marker_color=colors[i]
                    ))
                
                fig.update_layout(
                    barmode='group',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(30,30,46,1)',
                    font_color='white',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: Quantum
    with tab3:
        st.header("⚛️ Quantum Machine Learning")
        
        st.markdown("""
        <div class="quantum-box">
            <h4>🔬 Quantum Configuration</h4>
            <p>Using {qubits} qubits with {fm} feature map ({reps} reps)</p>
        </div>
        """.format(qubits=n_qubits, fm=feature_map, reps=reps), unsafe_allow_html=True)
        
        if not st.session_state.data_generated:
            st.warning("⚠️ Generate data first in the Data tab")
        else:
            st.info("⚠️ Quantum simulation is computationally intensive. Using subset of data.")
            
            max_samples = st.slider("Max quantum samples", 50, 300, 100)
            
            if st.button("Train QSVM", type="primary"):
                with st.spinner("Training quantum model... (this may take a while)"):
                    try:
                        from qzero.quantum.qsvm import QSVM, QSVMConfig
                        
                        # Feature engineering
                        engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method='pca')
                        X_reduced = engineer.fit_transform(st.session_state.X)
                        
                        # Use subset for quantum
                        X_q = X_reduced[:max_samples]
                        y_q = st.session_state.y[:max_samples]
                        
                        X_train, X_test, y_train, y_test = train_test_split(
                            X_q, y_q, test_size=0.2, random_state=42
                        )
                        
                        # Configure and train QSVM
                        config = QSVMConfig(
                            n_qubits=n_qubits,
                            feature_map_reps=reps,
                            use_classical_fallback=True
                        )
                        
                        qsvm = QSVM(config=config)
                        start = time.time()
                        qsvm.fit(X_train, y_train)
                        y_pred = qsvm.predict(X_test)
                        train_time = time.time() - start
                        
                        from sklearn.metrics import accuracy_score, f1_score
                        accuracy = accuracy_score(y_test, y_pred)
                        f1 = f1_score(y_test, y_pred, average='weighted')
                        
                        st.session_state.quantum_results = {
                            'accuracy': accuracy,
                            'f1': f1,
                            'time': train_time,
                            'used_quantum': qsvm._used_quantum
                        }
                        
                        st.success("✅ QSVM trained!")
                        
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            if st.session_state.quantum_results:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Accuracy", f"{st.session_state.quantum_results['accuracy']:.4f}")
                with col2:
                    st.metric("F1-Score", f"{st.session_state.quantum_results['f1']:.4f}")
                with col3:
                    st.metric("Time", f"{st.session_state.quantum_results['time']:.2f}s")
                with col4:
                    backend = "Quantum" if st.session_state.quantum_results['used_quantum'] else "Classical"
                    st.metric("Backend", backend)
    
    # Tab 4: Results Comparison
    with tab4:
        st.header("📈 Results Comparison")
        
        if st.session_state.classical_results and st.session_state.quantum_results:
            # Get best classical
            best_classical = max(st.session_state.classical_results, key=lambda x: x.f1)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                <div class="success-box">
                    <h3>🤖 Best Classical Model</h3>
                </div>
                """, unsafe_allow_html=True)
                st.metric("Model", best_classical.model_name)
                st.metric("F1-Score", f"{best_classical.f1:.4f}")
                st.metric("Accuracy", f"{best_classical.accuracy:.4f}")
            
            with col2:
                st.markdown("""
                <div class="quantum-box">
                    <h3>⚛️ Quantum QSVM</h3>
                </div>
                """, unsafe_allow_html=True)
                st.metric("Model", "QSVM")
                st.metric("F1-Score", f"{st.session_state.quantum_results['f1']:.4f}")
                st.metric("Accuracy", f"{st.session_state.quantum_results['accuracy']:.4f}")
            
            # Comparison chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Classical (Best)',
                x=['Accuracy', 'F1-Score'],
                y=[best_classical.accuracy, best_classical.f1],
                marker_color='#10b981'
            ))
            
            fig.add_trace(go.Bar(
                name='Quantum QSVM',
                x=['Accuracy', 'F1-Score'],
                y=[st.session_state.quantum_results['accuracy'], 
                   st.session_state.quantum_results['f1']],
                marker_color='#6366f1'
            ))
            
            fig.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,30,46,1)',
                font_color='white',
                title="Classical vs Quantum Comparison"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("Train both classical and quantum models to see comparison")
    
    # Run full experiment if button pressed
    if run_experiment:
        st.toast("🚀 Running full experiment...")
        # This would trigger all training steps


if __name__ == "__main__":
    main()
