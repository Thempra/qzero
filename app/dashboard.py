"""
QZero — Security Operations Console
====================================
Live security-operations view over the central QZero hub.

Connects to the central hub API (query parameters /api/v1/summary,
/api/v1/agents, /api/v1/alerts/recent) and renders:

  * Live KPIs (total alerts, active agents, recent alerts)
  * Severity distribution
  * Per-agent online status
  * Recent alert feed (filterable by severity / agent)
  * Top source IPs and a live alert timeline

Kept separate from the research/benchmarking lab (see the "Research" tab),
which is the original model-comparison UI.
"""

import json
import os
import time
import urllib.request
from urllib.parse import urlencode

import streamlit as st
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except Exception:  # pragma: no cover
    _HAS_PLOTLY = False

API = os.environ.get("QZERO_API_URL", "http://qzero-api:8000").rstrip("/")

try:
    from intel import enrich_alert, classify_direction
    _HAS_INTEL = True
except Exception:  # pragma: no cover
    _HAS_INTEL = False

    def enrich_alert(a):  # noqa: F811
        return a

    def classify_direction(src: str, dst: str) -> str:  # noqa: F811
        return "?"


# ---------------------------------------------------------------------------
# Hub API client (stdlib urllib only — no extra dependencies)
# ---------------------------------------------------------------------------
def api_get(path: str, params: dict | None = None, timeout: float = 5.0):
    url = f"{API}{path}"
    if params:
        url += "?" + urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


@st.cache_data(ttl=3, show_spinner=False)
def hub_summary():
    return api_get("/api/v1/hub/summary")


@st.cache_data(ttl=3, show_spinner=False)
def hub_agents():
    return api_get("/api/v1/agents")


@st.cache_data(ttl=3, show_spinner=False)
def hub_alerts_recent(minutes: int = 60):
    return api_get("/api/v1/alerts/recent", {"minutes": minutes})


SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
SEV_COLOR = {
    "CRITICAL": "#ef4444",
    "HIGH": "#f97316",
    "MEDIUM": "#f59e0b",
    "LOW": "#eab308",
    "INFO": "#3b82f6",
}


# ---------------------------------------------------------------------------
# Live operations console
# ---------------------------------------------------------------------------
def render_live_ops(agents_online_window_min: int):
    st.subheader("📡 Live operations — central hub")

    try:
        summary = hub_summary()
    except Exception as exc:
        st.error(f"⚠️ No se pudo contactar con el hub ({API}): {exc}")
        st.info("Comprueba que el contenedor qzero-api esté up y accesible desde el dashboard.")
        return

    total = summary.get("total_alerts", 0)
    by_sev = summary.get("by_severity", {})
    n_agents = summary.get("agents", 0)

    # ----- KPI row -----
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total alertas", f"{total:,}")
    k2.metric("Agentes registrados", n_agents)
    # severity breakdown
    crit = by_sev.get("CRITICAL", 0)
    k3.metric("Críticas", f"{crit:,}")
    k4.metric("HIGH", f"{by_sev.get('HIGH', 0):,}")

    # ----- Severity distribution -----
    sev_df = pd.DataFrame(
        {"Severity": [s for s in SEV_ORDER if s in by_sev],
         "Count": [by_sev[s] for s in SEV_ORDER if s in by_sev]}
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("##### Distribución por severidad")
        if _HAS_PLOTLY and not sev_df.empty:
            fig = px.bar(
                sev_df, x="Severity", y="Count",
                color="Severity", color_discrete_map=SEV_COLOR,
                text="Count",
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(30,30,46,1)",
                              font_color="white", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(sev_df, use_container_width=True)

    # ----- Agents status -----
    with c2:
        st.markdown("##### Estado de agentes")
        try:
            agents = hub_agents()
        except Exception:
            agents = []
        if agents:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            rows = []
            for a in agents:
                try:
                    last = datetime.fromisoformat(a.get("last_seen", ""))
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    age_min = (now - last).total_seconds() / 60.0
                except Exception:
                    age_min = float("inf")
                rows.append({
                    "Agente": a.get("agent_name") or a.get("agent_id", "?"),
                    "Interfaz": a.get("interface", "—"),
                    "Alertas": a.get("total_alerts", 0),
                    "Estado": "🟢 online" if age_min <= agents_online_window_min else "🔴 offline",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Sin agentes registrados todavía.")

    st.divider()

    # ----- Recent alerts (enriched) -----
    st.markdown("##### 🔔 Alertas recientes (identificadas)")
    try:
        recent = hub_alerts_recent(minutes=max(60, agents_online_window_min * 4))
    except Exception:
        recent = []

    # Enrich each alert (direction, destination org, threat type, explanation)
    enriched = [enrich_alert(a) for a in recent] if (_HAS_INTEL and recent) else recent

    # Counts by threat type (identification summary)
    if _HAS_INTEL and enriched:
        from collections import Counter
        type_counts = Counter(a.get("threat_type", "?") for a in enriched)
        st.markdown("**Distribución por tipo detectado:**")
        tc = pd.DataFrame(type_counts.items(), columns=["Tipo", "N"])
        c1, c2 = st.columns([1, 2])
        with c1:
            st.dataframe(tc.sort_values("N", ascending=False),
                         use_container_width=True, hide_index=True)
        with c2:
            st.caption(
                "Cada alerta se clasifica por dirección (IN/OUT) + puerto + contexto "
                "para darle un *tipo* y una explicación accionable, en vez de solo un "
                "número de anomalía."
            )
        st.divider()

    # Filters
    f1, f2 = st.columns([1, 1])
    if _HAS_INTEL and enriched:
        type_opts = ["Todos"] + sorted({a.get("threat_type", "?") for a in enriched})
        sev_opts = ["Todas"] + [s for s in SEV_ORDER if s in by_sev]
        sev_filter = f1.selectbox("Severidad", sev_opts, index=0)
        type_filter = f2.selectbox("Tipo", type_opts, index=0)
    else:
        sev_opts = ["Todas"] + [s for s in SEV_ORDER if s in by_sev]
        sev_filter = f1.selectbox("Severidad", sev_opts, index=0)
        type_filter = None

    df_recent = pd.DataFrame(enriched) if enriched else pd.DataFrame()
    if not df_recent.empty:
        if sev_filter != "Todas":
            df_recent = df_recent[df_recent["severity"] == sev_filter]
        if type_filter and type_filter != "Todos":
            df_recent = df_recent[df_recent["threat_type"] == type_filter]

    if not df_recent.empty:
        if _HAS_INTEL:
            view = df_recent.head(100)[
                ["timestamp", "severity", "direction", "threat_type",
                 "src", "dst", "dest_org", "dst_port", "anomaly_score"]
            ].copy()
            view.columns = ["Timestamp", "Sev", "Dir", "Tipo",
                            "Src", "Dst", "Destino (org)", "Port", "Score"]
            cols_to_style = ["Sev"]
        else:
            view = df_recent.head(100)[
                ["timestamp", "agent_name", "severity", "src", "dst",
                 "dst_port", "protocol", "anomaly_score"]
            ].copy()
            view.columns = ["Timestamp", "Agente", "Sev", "Src", "Dst",
                            "Port", "Proto", "Score"]
            cols_to_style = ["Sev"]
        if _HAS_PLOTLY:
            st.dataframe(
                view.style.map(
                    lambda v: f"color: {SEV_COLOR.get(v, 'white')}",
                    subset=cols_to_style,
                ),
                use_container_width=True, hide_index=True,
                height=min(420, 30 + 35 * min(len(view), 8)),
            )
        else:
            st.dataframe(view, use_container_width=True, hide_index=True)

        # Explanation of the types present in the filtered view
        if _HAS_INTEL and "explanation" in df_recent.columns:
            st.markdown("##### ❓ ¿Qué es y qué hacer?")
            seen = []
            for _, row in df_recent.head(50).iterrows():
                key = (row.get("threat_type"), row.get("explanation"))
                if key not in seen:
                    seen.append(key)
                    with st.expander(f"**{row['threat_type']}** — {row['direction']} · "
                                     f"→ {row.get('dest_org','?')}", expanded=False):
                        st.write(row["explanation"])
        elif _HAS_INTEL:
            st.caption("Sin coincidencias con los filtros seleccionados.")
    else:
        st.caption("Sin alertas recientes que coincidan con los filtros.")

    # ----- Top source IPs + timeline -----
    st.divider()
    g1, g2 = st.columns([1, 1])
    with g1:
        st.markdown("##### 🌐 Top IPs origen (recientes)")
        if not df_recent.empty:
            top = df_recent["src"].value_counts().head(10).reset_index()
            top.columns = ["Src IP", "Count"]
            if _HAS_PLOTLY:
                fig = px.bar(top, x="Count", y="Src IP", orientation="h",
                             color="Count", color_continuous_scale="blues")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(30,30,46,1)",
                                  font_color="white", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(top, use_container_width=True, hide_index=True)
        else:
            st.caption("—")

    with g2:
        st.markdown("##### ⏱️ Timeline de alertas")
        if not df_recent.empty:
            if "timestamp" in df_recent:
                ts = pd.to_datetime(df_recent["timestamp"], errors="coerce")
                ts = ts.dropna()
                if not ts.empty:
                    ts = ts.dt.floor("min")
                    ts_df = ts.value_counts().sort_index().reset_index()
                    ts_df.columns = ["Minuto", "Alertas"]
                    if _HAS_PLOTLY:
                        fig = go.Figure(go.Scatter(
                            x=ts_df["Minuto"], y=ts_df["Alertas"],
                            mode="lines+markers", line=dict(color="#6366f1"),
                        ))
                        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                          plot_bgcolor="rgba(30,30,46,1)",
                                          font_color="white", xaxis_title="Hora",
                                          yaxis_title="Alertas/min")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.dataframe(ts_df.tail(30), use_container_width=True, hide_index=True)
                else:
                    st.caption("Sin timestamps válidos.")
            else:
                st.caption("—")
        else:
            st.caption("—")


# ---------------------------------------------------------------------------
# Research / benchmarking lab (kept from the original dashboard)
# ---------------------------------------------------------------------------
def render_research():
    import numpy as np
    from qzero.preprocessing.data_loader import generate_synthetic_data, DataLoader
    from qzero.preprocessing.feature_engineering import FeatureEngineer
    from pathlib import Path
    from qzero.classical.baseline import ClassicalBaseline, run_all_baselines
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import confusion_matrix

    st.subheader("🔬 Research / Benchmarking (clásico vs cuántico)")

    with st.sidebar:
        st.markdown("---")
        st.markdown("**Research settings**")
        n_qubits = st.slider("Número de qubits", 2, 8, 4)
        feature_map = st.selectbox("Feature map", ["ZZ", "ZZZ", "Pauli", "Z"])
        reps = st.slider("Repeticiones", 1, 4, 2)

    data_dir = Path(__file__).parent.parent / "data" / "raw"
    real_dataset_exists = (data_dir / "final(2).csv").exists()
    data_source = st.radio(
        "Data source",
        ["Synthetic", "Real (UGRansome)"] if real_dataset_exists else ["Synthetic"],
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Data", "🤖 Classical", "⚛️ Quantum", "📈 Results"]
    )

    if "R_X" not in st.session_state:
        st.session_state.R_data_generated = False
        st.session_state.R_classical_results = None
        st.session_state.R_quantum_results = None

    with tab1:
        st.header("📊 Data generation & exploration")
        if data_source == "Synthetic":
            n_samples = st.slider("Nº de muestras", 100, 5000, 1000, 100, key="r_ns")
            difficulty = st.select_slider("Dificultad", ["easy", "medium", "hard"],
                                          "medium", key="r_diff")
            if st.button("Generate Synthetic Data", type="primary", key="r_gen"):
                with st.spinner("Generando datos..."):
                    X, y = generate_synthetic_data(n_samples=n_samples,
                                                   difficulty=difficulty)
                    st.session_state.R_X = X
                    st.session_state.R_y = y
                    st.session_state.R_data_generated = True
                    st.session_state.R_source = "synthetic"
                st.success(f"✅ Generadas {n_samples} muestras, {X.shape[1]} features")
        else:
            n_samples = st.slider("Sample limit (0=todas)", 0, 50000, 10000, 1000,
                                  key="r_nl")
            if st.button("Load UGRansome Dataset", type="primary", key="r_load"):
                with st.spinner("Cargando dataset real..."):
                    loader = DataLoader()
                    X, y = loader.load_ugransome()
                    if 0 < n_samples < len(X):
                        X, _, y, _ = train_test_split(X, y, train_size=n_samples,
                                                      stratify=y, random_state=42)
                    st.session_state.R_X = X
                    st.session_state.R_y = y
                    st.session_state.R_data_generated = True
                    st.session_state.R_source = "real"
                st.success(f"✅ Cargadas {len(X)} muestras")

        if st.session_state.R_data_generated:
            X = st.session_state.R_X
            y = st.session_state.R_y
            source = st.session_state.get("R_source", "synthetic")
            cm1, cm2 = st.columns(2)
            cm1.metric("Muestras", len(X))
            cm2.metric("Features", X.shape[1])

            st.subheader("Distribución de clases")
            if source == "real":
                class_names = ["Normal", "Signature", "Zero-Day"]
                class_counts = pd.Series(y).value_counts().sort_index()
                labels = [class_names[i] if i < len(class_names) else f"Class {i}"
                          for i in class_counts.index]
            else:
                class_names = ["Normal", "Signature", "Zero-Day"]
                class_counts = pd.Series(y).value_counts().sort_index()
                labels = [class_names[i] if i < len(class_names) else f"Class {i}"
                          for i in class_counts.index]
            if _HAS_PLOTLY:
                fig = px.pie(values=class_counts.values, names=labels,
                             color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444"])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(30,30,46,1)", font_color="white")
                st.plotly_chart(fig, use_container_width=True)

            engineer = FeatureEngineer(n_qubits=min(3, n_qubits), reduction_method="pca")
            X_reduced = engineer.fit_transform(X)
            if _HAS_PLOTLY:
                df_pca = pd.DataFrame(X_reduced[:, :2], columns=["PC1", "PC2"])
                df_pca["Class"] = [labels[i] if i < len(labels) else f"C{i}"
                                   for i in y]
                fig = px.scatter(df_pca, x="PC1", y="PC2", color="Class",
                                 color_discrete_sequence=["#10b981", "#f59e0b", "#ef4444"],
                                 opacity=0.7)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(30,30,46,1)", font_color="white")
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.header("🤖 Classical ML baselines")
        if not st.session_state.R_data_generated:
            st.warning("⚠️ Genera datos primero en la pestaña Data")
        else:
            if st.button("Train Classical Models", type="primary", key="r_tr_cls"):
                with st.spinner("Entrenando modelos..."):
                    engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method="pca")
                    X_reduced = engineer.fit_transform(st.session_state.R_X)
                    X_train, X_test, y_train, y_test = train_test_split(
                        X_reduced, st.session_state.R_y, test_size=0.2, random_state=42)
                    results = run_all_baselines(X_train, y_train, X_test, y_test)
                    st.session_state.R_classical_results = results
                st.success("✅ Modelos clásicos entrenados")
            if st.session_state.R_classical_results:
                results = st.session_state.R_classical_results
                results_df = pd.DataFrame([{
                    "Model": r.model_name, "Accuracy": round(r.accuracy, 4),
                    "Precision": round(r.precision, 4), "Recall": round(r.recall, 4),
                    "F1": round(r.f1, 4), "Time (s)": round(r.train_time, 3),
                } for r in results])
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                if _HAS_PLOTLY:
                    fig = go.Figure()
                    for i, m in enumerate(["accuracy", "precision", "recall", "f1"]):
                        fig.add_trace(go.Bar(name=m.title(),
                                             x=[r.model_name for r in results],
                                             y=[getattr(r, m) for r in results],
                                             marker_color=["#6366f1", "#8b5cf6",
                                                           "#a855f7", "#c084fc"][i]))
                    fig.update_layout(barmode="group",
                                      paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(30,30,46,1)",
                                      font_color="white", legend=dict(orientation="h"))
                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.header("⚛️ Quantum ML (QSVM)")
        if not st.session_state.R_data_generated:
            st.warning("⚠️ Genera datos primero en la pestaña Data")
        else:
            st.info("⚠️ La simulación cuántica es intensiva en cómputo. Se usa subconjunto.")
            max_samples = st.slider("Max quantum samples", 50, 300, 100, key="r_qm")
            if st.button("Train QSVM", type="primary", key="r_tr_q"):
                with st.spinner("Entrenando QSVM (puede tardar)..."):
                    try:
                        from qzero.quantum.qsvm import QSVM, QSVMConfig
                        from sklearn.metrics import accuracy_score, f1_score
                        engineer = FeatureEngineer(n_qubits=n_qubits,
                                                   reduction_method="pca")
                        X_reduced = engineer.fit_transform(st.session_state.R_X)
                        X_q = X_reduced[:max_samples]
                        y_q = st.session_state.R_y[:max_samples]
                        X_train, X_test, y_train, y_test = train_test_split(
                            X_q, y_q, test_size=0.2, random_state=42)
                        config = QSVMConfig(n_qubits=n_qubits,
                                            feature_map_reps=reps,
                                            use_classical_fallback=True)
                        qsvm = QSVM(config=config)
                        start = time.time()
                        qsvm.fit(X_train, y_train)
                        y_pred = qsvm.predict(X_test)
                        train_time = time.time() - start
                        st.session_state.R_quantum_results = {
                            "accuracy": accuracy_score(y_test, y_pred),
                            "f1": f1_score(y_test, y_pred, average="weighted"),
                            "time": train_time,
                            "used_quantum": qsvm._used_quantum,
                        }
                        st.success("✅ QSVM entrenado")
                    except Exception as e:
                        st.error(f"Error: {e}")
            if st.session_state.R_quantum_results:
                r = st.session_state.R_quantum_results
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Accuracy", round(r["accuracy"], 4))
                c2.metric("F1", round(r["f1"], 4))
                c3.metric("Time", f'{r["time"]:.2f}s')
                c4.metric("Backend", "Quantum" if r["used_quantum"] else "Classical")

    with tab4:
        st.header("📈 Results comparison")
        if st.session_state.R_classical_results and st.session_state.R_quantum_results:
            best = max(st.session_state.R_classical_results, key=lambda x: x.f1)
            r = st.session_state.R_quantum_results
            c1, c2 = st.columns(2)
            c1.metric("Mejor clásico", f"{best.model_name} · F1 {best.f1:.4f}")
            c2.metric("Quantum QSVM", f"F1 {r['f1']:.4f}")
            if _HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Classical (best)", x=["F1"],
                                     y=[best.f1], marker_color="#10b981"))
                fig.add_trace(go.Bar(name="Quantum QSVM", x=["F1"],
                                     y=[r["f1"]], marker_color="#6366f1"))
                fig.update_layout(barmode="group", paper_bgcolor="rgba(0,0,0,0)",
                                  plot_bgcolor="rgba(30,30,46,1)", font_color="white")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Entrena modelos clásico y cuántico para ver la comparativa.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="QZero — Security Operations",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
    <style>
    .main-header { font-size:2.6rem; font-weight:bold;
        background:linear-gradient(90deg,#6366f1,#8b5cf6);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        text-align:center; margin-bottom:.4rem; }
    .sub { text-align:center; color:#888; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">🛡️ QZero — Security Operations</h1>',
                unsafe_allow_html=True)
    st.markdown('<p class="sub">Quantum threat detection · central hub console</p>',
                unsafe_allow_html=True)

    with st.sidebar:
        st.title("Control")
        refresh_sec = st.selectbox(
            "Auto-refresh",
            options=[0, 5, 10, 15, 30],
            format_func=lambda s: "Off (manual)" if s == 0 else f"Cada {s}s",
            index=2,
        )
        online_window = st.slider(
            "Ventana agente online (min)", 1, 30, 5,
            help="Tiempo sin notificar para marcar un agente como offline.",
        )
        if st.button("🔄 Refresh ahora", use_container_width=True):
            st.cache_data.clear()
        st.caption(f"Hub: {API}")

    tab_live, tab_research = st.tabs(["📡 Live Ops", "🔬 Research"])

    with tab_live:
        render_live_ops(agents_online_window_min=online_window)

    with tab_research:
        render_research()

    # Auto-refresh (live polling)
    if refresh_sec > 0:
        time.sleep(refresh_sec)
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()


if __name__ == "__main__":
    main()
