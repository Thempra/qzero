"""
QZero — Security Operations Center (SOC) Console
================================================
Professional SOC-style frontend over the central QZero hub, modeled on
commercial security consoles (Wazuh / Elastic / OpenSearch / Splunk).

Design principles:
  * Dark console theme, no Streamlit chrome (branding hidden via CSS).
  * Top SOC header bar: brand, environment badge, live clock, agents online,
    global refresh control.
  * Module navigation rendered as top pills (no sidebar) so the operator
    moves between Overview / Alerts / Threats / Network / Agents / Research.
  * Risk-first hierarchy: KPIs, severity distribution, timelines, agent
    health, threat-type identification with actionable explanations.

Data is fetched from the central hub API with the stdlib urllib client, and
every alert is enriched (direction / destination org / threat type /
explanation) by the intel module.
"""

import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except Exception:  # pragma: no cover
    _HAS_PLOTLY = False

API = os.environ.get("QZERO_API_URL", "http://qzero-api:8000").rstrip("/")
DIR_COL = "Dirección"
ENV_LABEL = os.environ.get("QZERO_ENV", "PRODUCTION")

try:
    from intel import enrich_alert
    _HAS_INTEL = True
except Exception:  # pragma: no cover
    _HAS_INTEL = False

    def enrich_alert(a):  # noqa: F811
        return a

SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
SEV_COLOR = {
    "CRITICAL": "#ef4444",
    "HIGH": "#f97316",
    "MEDIUM": "#f59e0b",
    "LOW": "#eab308",
    "INFO": "#38bdf8",
}

# ---------------------------------------------------------------------------
# SOC chrome / theme
# ---------------------------------------------------------------------------
SOC_CSS = """
<style>
  /* Hide Streamlit chrome */
  #MainMenu, footer, header[data-testid="stHeader"] { display:none !important; }
  .stApp { background-color:#0b0e14; }
  .block-container { padding-top:1rem; padding-bottom:2rem; }

  /* ---- SOC top header bar ---- */
  .soc-topbar {
    display:flex; align-items:center; gap:18px;
    background:linear-gradient(90deg,#0f1420 0%, #141a26 100%);
    border:1px solid #232b3a; border-radius:8px;
    padding:10px 18px; margin-bottom:16px;
  }
  .soc-brand { font-size:1.25rem; font-weight:800; letter-spacing:.5px; color:#e8edf5; }
  .soc-brand .dot { color:#6366f1; }
  .soc-env {
    font-size:.68rem; font-weight:700; letter-spacing:1.2px;
    padding:3px 8px; border-radius:4px;
    background:#14243a; color:#5aa2f5; border:1px solid #1d3557;
  }
  .soc-clock { font-size:.85rem; color:#9aa7b8; font-variant-numeric:tabular-nums; }
  .soc-legend { margin-left:auto;
    font-size:.78rem; color:#9aa7b8; white-space:nowrap; }
  .soc-legend b { color:#e8edf5; }

  /* ---- module nav pills ---- */
  .soc-nav { display:flex; gap:6px; flex-wrap:wrap; margin:4px 0 14px; }
  .soc-nav a {
    text-decoration:none; font-size:.82rem; font-weight:600; letter-spacing:.3px;
    color:#9aa7b8; padding:7px 14px; border-radius:6px; border:1px solid #232b3a;
    background:#101622; transition:all .12s;
  }
  .soc-nav a:hover { color:#e8edf5; border-color:#3b4a63; }
  .soc-nav a.active {
    color:#0b0e14; background:#6366f1; border-color:#6366f1;
  }

  /* ---- KPI cards ---- */
  .soc-kpi {
    background:#101622; border:1px solid #232b3a; border-radius:8px;
    padding:12px 16px; position:relative; overflow:hidden;
  }
  .soc-kpi .label { font-size:.68rem; letter-spacing:1px; text-transform:uppercase;
    color:#7d8ba1; }
  .soc-kpi .value { font-size:1.7rem; font-weight:800; color:#e8edf5;
    font-variant-numeric:tabular-nums; margin-top:2px;}
  .soc-kpi .sub { font-size:.72rem; color:#5f6d82; margin-top:2px; }
  .soc-kpi.viol { border-left:3px solid #ef4444; }
  .soc-kpi.high { border-left:3px solid #f97316; }
  .soc-kpi.med  { border-left:3px solid #f59e0b; }
  .soc-kpi.ok   { border-left:3px solid #34d399; }

  /* ---- severity badge ---- */
  .sev { display:inline-block; font-size:.68rem; font-weight:700; letter-spacing:.5px;
    padding:2px 8px; border-radius:4px; }
  .sev-CRITICAL { background:#3f1216; color:#ff6b6b; border:1px solid #7f1d1d; }
  .sev-HIGH      { background:#3a2410; color:#fca662; border:1px solid #7c4a12; }
  .sev-MEDIUM    { background:#3a3010; color:#f5c25b; border:1px solid #7c6012; }
  .sev-LOW       { background:#33391a; color:#e3e07a; border:1px solid #5f6b1d; }
  .sev-INFO      { background:#12283a; color:#7cc7f5; border:1px solid #1d5073; }

  .soc-section { font-size:1rem; font-weight:700; color:#e8edf5;
    margin:20px 0 10px; padding-bottom:6px; border-bottom:1px solid #232b3a; }
  .soc-muted { color:#7d8ba1; font-size:.8rem; }
</style>
"""
st.markdown(SOC_CSS, unsafe_allow_html=True)


def sev_badge(sev: str) -> str:
    return f'<span class="sev sev-{sev}">{sev}</span>'


def kpi_card(label: str, value: str, sub: str = "", tone: str = ""):
    tone_cls = {"viol": "viol", "high": "high", "med": "med", "ok": "ok"}.get(tone, "")
    st.markdown(
        f'<div class="soc-kpi {tone_cls}">'
        f'<div class="label">{label}</div><div class="value">{value}</div>'
        f'<div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Hub API client (stdlib urllib) + login SPA (Hito 3.7)
# ---------------------------------------------------------------------------
def _auth_status():
    try:
        req = urllib.request.Request(f"{API}/api/v1/auth/status",
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {"auth_required": False}


def _auth_headers() -> dict:
    tok = st.session_state.get("qzero_token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def do_login(password: str) -> bool:
    req = urllib.request.Request(
        f"{API}/api/v1/auth/login",
        data=json.dumps({"password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            st.session_state["qzero_token"] = json.loads(
                resp.read().decode())["access_token"]
        return True
    except Exception:
        return False


if _auth_status().get("auth_required") and not st.session_state.get("qzero_token"):
    with st.sidebar.form("login_form"):
        pw = st.text_input("Contraseña del hub", type="password")
        if st.form_submit_button("Entrar"):
            if do_login(pw):
                st.session_state.pop("_login_fail", None)
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    st.info("Introduce la contraseña del hub en la barra lateral.")
    st.stop()


def api_get(path: str, params: dict | None = None, timeout: float = 15.0):
    url = f"{API}{path}"
    if params:
        url += "?" + urlencode({k: v for k, v in params.items() if v is not None})
    headers = {"Accept": "application/json", **_auth_headers()}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:  # token caducado/revocado → reloguear
            st.session_state.pop("qzero_token", None)
            st.rerun()
        raise


@st.cache_data(ttl=3, show_spinner=False)
def hub_summary():
    return api_get("/api/v1/hub/summary")


@st.cache_data(ttl=3, show_spinner=False)
def hub_agents():
    return api_get("/api/v1/agents")


@st.cache_data(ttl=2, show_spinner=False)
def hub_alerts_recent(minutes: int = 60, limit: int = 400):
    return api_get("/api/v1/alerts/recent", {"minutes": minutes, "limit": limit})


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def _dark_layout(fig, height: int = 300):
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(16,22,34,1)", font_color="#d7dee8",
        margin={"l": 10, "r": 10, "t": 30, "b": 10}, showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    fig.update_xaxes(gridcolor="#1c2434", zeroline=False)
    fig.update_yaxes(gridcolor="#1c2434", zeroline=False)
    return fig


def severity_donut(sev_df):
    if _HAS_PLOTLY and not sev_df.empty:
        fig = px.pie(sev_df, names="Severity", values="Count",
                     color="Severity", color_discrete_map=SEV_COLOR, hole=0.62)
        fig.update_traces(textposition="inside", textinfo="percent")
        return _dark_layout(fig, 280)
    return None


def threat_type_bar(tc_df):
    if _HAS_PLOTLY and not tc_df.empty:
        fig = px.bar(tc_df.sort_values("N", ascending=True), x="N", y="Tipo",
                     orientation="h", color="N",
                     color_continuous_scale=["#f97316", "#eab308", "#6366f1"],
                     text="N")
        fig.update_traces(textposition="outside")
        return _dark_layout(fig, 300)
    return None


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def render_topbar(agents_online: int, agents_total: int):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    st.markdown(
        f"""
        <div class="soc-topbar">
          <span class="soc-brand"><span class="dot">◈</span> QZero <span style="color:#7d8ba1;font-weight:600">· SOC</span></span>
          <span class="soc-clock">🕐 {now}</span>
          <span class="soc-legend">Agentes: <b>{agents_online}</b>/<b>{agents_total}</b> online</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_nav(current: str) -> str:
    """SOC module pills.

    Uses Streamlit-native buttons (not raw <a> tags) so clicking navigates
    within the SAME browser tab. Raw `<a href="?module=...">` anchors get
    rewritten by Streamlit's markdown renderer with target="_blank", which
    causes every pill to open a new tab — the reported bug.
    """
    module_map = ["Overview", "Alerts", "Threats", "Network", "Agents", "Research"]
    cols = st.columns(len(module_map), gap="small")
    for col, m in zip(cols, module_map):
        with col:
            active = m == current
            label = f"**{m}**" if active else m
            if st.button(
                label,
                key=f"nav_{m}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state["module"] = m
                st.rerun()
    return current


# ---------------------------------------------------------------------------
# Overview module
# ---------------------------------------------------------------------------
def module_overview(online_window_min):
    try:
        summary = hub_summary()
    except Exception:
        summary = {}
    total = summary.get("total_alerts", 0)
    by_sev = summary.get("by_severity", {})
    n_agents = summary.get("agents", 0)

    crit = by_sev.get("CRITICAL", 0)
    high = by_sev.get("HIGH", 0)
    med = by_sev.get("MEDIUM", 0)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        kpi_card("Alertas totales", f"{total:,}", "histórico", "viol")
    with k2:
        kpi_card("Críticas", f"{crit:,}", "requieren acción", "viol")
    with k3:
        kpi_card("Alta", f"{high:,}", "revisar", "high")
    with k4:
        kpi_card("Media", f"{med:,}", "monitor", "med")
    with k5:
        kpi_card("Agentes", f"{n_agents}", "registrados", "ok")

    st.markdown('<div class="soc-section">Análisis de riesgo</div>',
                unsafe_allow_html=True)

    sev_df = pd.DataFrame(
        {"Severity": [s for s in SEV_ORDER if s in by_sev],
         "Count": [by_sev[s] for s in SEV_ORDER if s in by_sev]}
    )
    col_l, col_r = st.columns([1, 1.4])
    with col_l:
        st.markdown("##### Distribución por severidad")
        fig = severity_donut(sev_df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(sev_df, use_container_width=True, hide_index=True)

    with col_r:
        # Threat type distribution from the recent enriched feed
        st.markdown("##### Tipos de amenaza (últimas horas)")
        try:
            recent = hub_alerts_recent(minutes=max(60, online_window_min * 4))
        except Exception:
            recent = []
        enriched = [enrich_alert(a) for a in recent] if (_HAS_INTEL and recent) else recent
        if _HAS_INTEL and enriched:
            tc = pd.DataFrame(Counter(a.get("threat_type", "?") for a in enriched).items(),
                              columns=["Tipo", "N"])
            try:
                tc = tc.sort_values("N", ascending=False).reset_index(drop=True)
            except Exception:
                pass
            fig = threat_type_bar(tc.head(8))
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(tc.head(8), use_container_width=True, hide_index=True)
        else:
            st.info("Enriquecimiento no disponible.")

    st.markdown('<div class="soc-section">Salud de agentes</div>', unsafe_allow_html=True)
    rows = []
    try:
        agents = hub_agents()
    except Exception:
        agents = []
    if agents:
        now = datetime.now(timezone.utc)
        for a in agents:
            try:
                last = datetime.fromisoformat(a.get("last_seen", ""))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                age_min = (now - last).total_seconds() / 60.0
            except Exception:
                age_min = float("inf")
            status = "🟢 online" if age_min <= online_window_min else "🔴 offline"
            rows.append({
                "Agente": a.get("agent_name") or a.get("agent_id", "?"),
                "Interfaz": a.get("interface", "—"),
                "Alertas enviadas": f"{a.get('total_alerts', 0):,}",
                "Última actividad (min)": f"{age_min:.0f}" if age_min != float("inf") else "—",
                "Estado": status,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Sin agentes registrados todavía.")

    # timeline
    st.markdown('<div class="soc-section">Actividad reciente</div>', unsafe_allow_html=True)
    if not enriched:
        try:
            enriched = [enrich_alert(a) for a in hub_alerts_recent(minutes=120)]
        except Exception:
            enriched = []
    if enriched:
        dfr = pd.DataFrame(enriched)
        tl = pd.to_datetime(dfr["timestamp"], errors="coerce").dropna().dt.floor("min")
        tl_df = tl.value_counts().sort_index().reset_index()
        tl_df.columns = ["Minuto", "Alertas"]
        if _HAS_PLOTLY and not tl_df.empty:
            fig = go.Figure(go.Scatter(x=tl_df["Minuto"], y=tl_df["Alertas"],
                                       mode="lines+markers",
                                       line={"color": "#6366f1", "width": 2},
                                       fill="tozeroy", fillcolor="rgba(99,102,241,.15)"))
            fig.update_xaxes(title_text="Hora")
            fig.update_yaxes(title_text="Alertas/min")
            st.plotly_chart(_dark_layout(fig, 260), use_container_width=True)
    return enriched


# ---------------------------------------------------------------------------
# Alerts module
# ---------------------------------------------------------------------------
def module_alerts(enriched):
    st.markdown('<div class="soc-section">Feed de alertas (identificadas)</div>',
                unsafe_allow_html=True)

    if not enriched:
        st.info("Sin alertas recientes.")
        return

    type_opts = ["Todos"] + sorted({a.get("threat_type", "?") for a in enriched})
    sev_opts = ["Todas"] + [s for s in SEV_ORDER if s in {a.get("severity") for a in enriched}]
    dir_opts = ["Todas"] + sorted({a.get("direction", "?") for a in enriched})

    f1, f2, f3, f4 = st.columns([1, 1, 1, 1.5])
    sev_filter = f1.selectbox("Severidad", sev_opts)
    type_filter = f2.selectbox("Tipo", type_opts)
    dir_filter = f3.selectbox(DIR_COL, dir_opts)
    search = f4.text_input("🔍 Buscar (IP / org / puerto)", "").strip().lower()

    dfr = pd.DataFrame(enriched)
    if sev_filter != "Todas":
        dfr = dfr[dfr["severity"] == sev_filter]
    if type_filter != "Todos":
        dfr = dfr[dfr["threat_type"] == type_filter]
    if dir_filter != "Todas":
        dfr = dfr[dfr["direction"] == dir_filter]
    if search:
        mask = (
            dfr["src"].str.lower().str.contains(search, na=False)
            | dfr["dst"].str.lower().str.contains(search, na=False)
            | dfr.get("dest_org", "").astype(str).str.lower().str.contains(search, na=False)
            | dfr["dst_port"].astype(str).str.contains(search, na=False)
        )
        dfr = dfr[mask]

    if dfr.empty:
        st.caption("Sin coincidencias.")
        return

    view = dfr.head(200)[["timestamp", "severity", "direction", "threat_type",
                          "src", "dst", "dest_org", "dst_port", "anomaly_score"]].copy()
    view.columns = ["Timestamp", "Sev", "Dir", "Tipo",
                    "Src", "Dst", "Destino (org)", "Port", "Score"]

    # HTML severity badges for display
    disp = view.copy()
    disp["Sev"] = disp["Sev"].map(lambda s: sev_badge(s))
    st.markdown(disp.to_html(escape=False, index=False, border=0),
                unsafe_allow_html=True)

    st.caption(f"Mostrando {len(view):,} de {len(enriched):,} alertas en ventana.")

    # Actionable explanations
    st.markdown("#### ❓ ¿Qué es y qué hacer?")
    seen = []
    for _, row in dfr.head(60).iterrows():
        key = (row.get("threat_type"), row.get("explanation"))
        if key in seen:
            continue
        seen.append(key)
        with st.expander(f"**{row['threat_type']}** · {row['direction']} → "
                         f"{row.get('dest_org', '?')}", expanded=False):
            st.write(row["explanation"])


# ---------------------------------------------------------------------------
# Threats module
# ---------------------------------------------------------------------------
def module_threats(enriched):
    st.markdown('<div class="soc-section">Catálogo de tipos de amenaza</div>',
                unsafe_allow_html=True)
    st.caption("Agrupación de las alertas recientes por tipo, con su explicación "
               "y severidad sugerida para priorizar la respuesta.")

    if not enriched:
        st.info("Sin datos.")
        return

    tc = Counter(a.get("threat_type", "?") for a in enriched)
    df = pd.DataFrame(tc.items(), columns=["Tipo", "N"]).sort_values("N", ascending=False)

    col1, col2 = st.columns([1, 1.6])
    with col1:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with col2:
        fig = threat_type_bar(df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Detalle por tipo")
    seen = []
    for a in enriched:
        key = a.get("threat_type", "?")
        if key in seen:
            continue
        seen.append(key)
        with st.expander(f"{key} — {tc[key]} alertas", expanded=False):
            st.write(a.get("explanation", ""))


# ---------------------------------------------------------------------------
# Network module
# ---------------------------------------------------------------------------
def module_network(enriched):
    st.markdown('<div class="soc-section">Vista de red</div>', unsafe_allow_html=True)

    if not enriched:
        st.info("Sin datos.")
        return
    dfr = pd.DataFrame(enriched)

    # direction breakdown
    if "direction" in dfr:
        dir_df = dfr["direction"].value_counts().reset_index()
        dir_df.columns = [DIR_COL, "N"]
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown("##### Dirección del tráfico")
            if _HAS_PLOTLY:
                fig = px.pie(dir_df, names=DIR_COL, values="N", hole=0.55)
                fig.update_traces(marker={"colors": ["#38bdf8", "#6366f1",
                                                     "#8b5cf6", "#a78bfa"]})
                st.plotly_chart(_dark_layout(fig, 280), use_container_width=True)
            else:
                st.dataframe(dir_df, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("##### Origen por organización")
            orgs = dfr.get("dest_org", "").value_counts().head(8).reset_index()
            orgs.columns = ["Organización", "N"]
            if _HAS_PLOTLY and not orgs.empty:
                fig = px.bar(orgs, x="N", y="Organización", orientation="h",
                             color="N", color_continuous_scale="viridis")
                st.plotly_chart(_dark_layout(fig, 280), use_container_width=True)
            else:
                st.dataframe(orgs, use_container_width=True, hide_index=True)

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("##### Top IPs origen")
        top_src = dfr["src"].value_counts().head(10).reset_index()
        top_src.columns = ["Src IP", "N"]
        st.dataframe(top_src, use_container_width=True, hide_index=True)
    with g2:
        st.markdown("##### Top IPs destino")
        top_dst = dfr["dst"].value_counts().head(10).reset_index()
        top_dst.columns = ["Dst IP", "N"]
        st.dataframe(top_dst, use_container_width=True, hide_index=True)

    st.markdown("##### Puertos destino más frecuentes")
    if "dst_port" in dfr:
        port_df = dfr["dst_port"].value_counts().head(10).reset_index()
        port_df.columns = ["Puerto", "N"]
        port_df["Puerto"] = port_df["Puerto"].map(
            lambda p: {443: "443 (HTTPS)", 80: "80 (HTTP)", 53: "53 (DNS)",
                       22: "22 (SSH)", 2222: "2222 (SSH)", 8443: "8443"}.get(p, str(p)))
        st.dataframe(port_df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Agents module
# ---------------------------------------------------------------------------
def module_agents(online_window_min):
    st.markdown('<div class="soc-section">Agentes de detección</div>',
                unsafe_allow_html=True)
    try:
        agents = hub_agents()
    except Exception:
        agents = []
    if not agents:
        st.info("Sin agentes registrados.")
        return

    now = datetime.now(timezone.utc)
    cards = st.columns(len(agents))
    for col, a in zip(cards, agents):
        with col:
            try:
                last = datetime.fromisoformat(a.get("last_seen", ""))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                age_min = (now - last).total_seconds() / 60.0
            except Exception:
                age_min = float("inf")
            online = age_min <= online_window_min
            tone = "ok" if online else "viol"
            kpi_card(
                (a.get("agent_name") or a.get("agent_id", "?")).upper(),
                "ONLINE" if online else "OFFLINE",
                f"if {a.get('interface','—')} · {a.get('total_alerts',0):,} alertas",
                tone,
            )

    st.markdown("##### Detalle")
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
            "ID": a.get("agent_id", "?"),
            "Nombre": a.get("agent_name", "?"),
            "Interfaz": a.get("interface", "—"),
            "Alertas": a.get("total_alerts", 0),
            "Primera vez": a.get("first_seen", "—"),
            "Última actividad": a.get("last_seen", "—"),
            "Estado": "online" if age_min <= online_window_min else "offline",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Research module (uses inline controls, no sidebar)
# ---------------------------------------------------------------------------
def module_research():
    st.markdown('<div class="soc-section">🔬 Research / Benchmarking (clásico vs cuántico)</div>',
                unsafe_allow_html=True)
    st.caption("Laboratorio de investigación del motor de detección. "
               "Compara baselines clásicos con QSVM/QI-VAE.")
    try:
        import numpy as np  # noqa: F401
        from qzero.preprocessing.data_loader import generate_synthetic_data  # noqa: F401
    except Exception as exc:
        st.warning(f"Dependencias de investigación no disponibles: {exc}")
        return

    from pathlib import Path
    from sklearn.model_selection import train_test_split
    from qzero.classical.baseline import run_all_baselines
    from qzero.preprocessing.feature_engineering import FeatureEngineer

    # inline settings (previously sidebar)
    rc1, rc2, rc3 = st.columns(3)
    n_qubits = rc1.slider("Número de qubits", 2, 8, 4)
    rc2.selectbox("Feature map", ["ZZ", "ZZZ", "Pauli", "Z"])
    reps = rc3.slider("Repeticiones", 1, 4, 2)

    data_dir = Path(__file__).parent.parent / "data" / "raw"
    real_dataset_exists = (data_dir / "final(2).csv").exists()
    data_source = st.radio("Data source",
                           ["Synthetic", "Real (UGRansome)"] if real_dataset_exists
                           else ["Synthetic"])

    if "R_X" not in st.session_state:
        st.session_state.R_data_generated = False
        st.session_state.R_classical_results = None
        st.session_state.R_quantum_results = None

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Data", "🤖 Classical", "⚛️ Quantum", "📈 Results"])
    with tab1:
        st.header("Generación y exploración de datos")
        if data_source == "Synthetic":
            n_samples = st.slider("Nº de muestras", 100, 5000, 1000, 100, key="r_ns")
            difficulty = st.select_slider("Dificultad", ["easy", "medium", "hard"],
                                          "medium", key="r_diff")
            if st.button("Generate Synthetic Data", type="primary", key="r_gen"):
                with st.spinner("Generando..."):
                    X, y = generate_synthetic_data(n_samples=n_samples, difficulty=difficulty)
                    st.session_state.R_X, st.session_state.R_y = X, y
                    st.session_state.R_data_generated = True
                    st.session_state.R_source = "synthetic"
                st.success(f"✅ Generadas {n_samples} muestras, {X.shape[1]} features")
        else:
            n_samples = st.slider("Sample limit (0=todas)", 0, 50000, 10000, 1000, key="r_nl")
            if st.button("Load UGRansome Dataset", type="primary", key="r_load"):
                with st.spinner("Cargando..."):
                    from qzero.preprocessing.data_loader import DataLoader
                    loader = DataLoader()
                    X, y = loader.load_ugransome()
                    if 0 < n_samples < len(X):
                        X, _, y, _ = train_test_split(X, y, train_size=n_samples,
                                                      stratify=y, random_state=42)
                    st.session_state.R_X, st.session_state.R_y = X, y
                    st.session_state.R_data_generated = True
                    st.session_state.R_source = "real"
                st.success(f"✅ Cargadas {len(X)} muestras")

        if st.session_state.R_data_generated:
            X = st.session_state.R_X
            cm1, cm2 = st.columns(2)
            cm1.metric("Muestras", len(X))
            cm2.metric("Features", X.shape[1])

    with tab2:
        st.header("🤖 Classical ML baselines")
        if not st.session_state.R_data_generated:
            st.warning("Genera datos primero en la pestaña Data.")
        else:
            if st.button("Train Classical Models", type="primary", key="r_tr_cls"):
                with st.spinner("Entrenando modelos..."):
                    engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method="pca")
                    reduced_x = engineer.fit_transform(st.session_state.R_X)
                    x_train, x_val, yt, yv = train_test_split(reduced_x, st.session_state.R_y,
                                                      test_size=0.2, random_state=42)
                    st.session_state.R_classical_results = run_all_baselines(x_train, yt, x_val, yv)
                st.success("Modelos clásicos entrenados.")
            if st.session_state.R_classical_results:
                dfr = pd.DataFrame([{
                    "Model": r.model_name, "Accuracy": round(r.accuracy, 4),
                    "Precision": round(r.precision, 4), "Recall": round(r.recall, 4),
                    "F1": round(r.f1, 4), "Time (s)": round(r.train_time, 3),
                } for r in st.session_state.R_classical_results])
                st.dataframe(dfr, use_container_width=True, hide_index=True)

    with tab3:
        st.header("⚛️ Quantum ML (QSVM)")
        if not st.session_state.R_data_generated:
            st.warning("Genera datos primero en la pestaña Data.")
        else:
            st.info("La simulación cuántica es intensiva en cómputo. Se usa subconjunto.")
            max_samples = st.slider("Max quantum samples", 50, 300, 100, key="r_qm")
            if st.button("Train QSVM", type="primary", key="r_tr_q"):
                with st.spinner("Entrenando QSVM (puede tardar)..."):
                    try:
                        from qzero.quantum.qsvm import QSVM, QSVMConfig
                        from sklearn.metrics import accuracy_score, f1_score
                        engineer = FeatureEngineer(n_qubits=n_qubits, reduction_method="pca")
                        reduced_x = engineer.fit_transform(st.session_state.R_X)[:max_samples]
                        yq = st.session_state.R_y[:max_samples]
                        x_train, x_val, yt, yv = train_test_split(reduced_x, yq, test_size=0.2, random_state=42)
                        qsvm = QSVM(config=QSVMConfig(n_qubits=n_qubits,
                                                      feature_map_reps=reps,
                                                      use_classical_fallback=True))
                        start = time.time()
                        qsvm.fit(x_train, yt)
                        yp = qsvm.predict(x_val)
                        st.session_state.R_quantum_results = {
                            "accuracy": accuracy_score(yv, yp),
                            "f1": f1_score(yv, yp, average="weighted"),
                            "time": time.time() - start,
                            "used_quantum": qsvm._used_quantum,
                        }
                        st.success("QSVM entrenado.")
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
        st.header("Comparativa de resultados")
        if st.session_state.R_classical_results and st.session_state.R_quantum_results:
            best = max(st.session_state.R_classical_results, key=lambda x: x.f1)
            r = st.session_state.R_quantum_results
            c1, c2 = st.columns(2)
            c1.metric("Mejor clásico", f"{best.model_name} · F1 {best.f1:.4f}")
            c2.metric("Quantum QSVM", f"F1 {r['f1']:.4f}")
            if _HAS_PLOTLY:
                fig = go.Figure()
                fig.add_trace(go.Bar(name="Classical (best)", x=["F1"], y=[best.f1],
                                     marker_color="#10b981"))
                fig.add_trace(go.Bar(name="Quantum QSVM", x=["F1"], y=[r["f1"]],
                                     marker_color="#6366f1"))
                st.plotly_chart(_dark_layout(fig, 300), use_container_width=True)
        else:
            st.info("Entrena modelos clásico y cuántico para ver la comparativa.")


# ---------------------------------------------------------------------------
# Footer control strip (replaces the old sidebar)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="QZero SOC", page_icon="🛡️",
                       layout="wide", initial_sidebar_state="collapsed")

    # ---- controls (kept minimal in sidebar for refresh config only) ----
    with st.sidebar:
        st.markdown("### ⚙️ Consola")
        refresh_sec = st.selectbox("Auto-refresh",
                                   [0, 5, 10, 15, 30],
                                   format_func=lambda s: "Off" if s == 0 else f"Cada {s}s",
                                   index=2, key="cfg_refresh")
        online_window = st.slider("Ventana de agente online (min)", 1, 30, 5,
                                  key="cfg_window",
                                  help="Minutos sin notificar para marcar un agente offline.")
        if st.button("🔄 Refresh", use_container_width=True, key="cfg_refresh_btn"):
            st.cache_data.clear()
        st.caption(f"Hub: `{API}`")

    # ---- top bar + nav ----
    try:
        agents = hub_agents()
        n_online = 0
        now = datetime.now(timezone.utc)
        for a in agents if agents else []:
            try:
                last = datetime.fromisoformat(a.get("last_seen", ""))
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if (now - last).total_seconds() / 60.0 <= online_window:
                    n_online += 1
            except Exception:
                pass
    except Exception:
        agents, n_online = [], 0

    render_topbar(n_online, len(agents or []))

    # module selection: keep in session state, defaulting to the URL param
    # (for deep-linking) only on first load.
    valid_modules = ["Overview", "Alerts", "Threats", "Network", "Agents", "Research"]
    if "module" not in st.session_state:
        params = st.query_params
        module = params.get("module", "Overview")
        if module not in valid_modules:
            module = "Overview"
        st.session_state["module"] = module
    module = st.session_state["module"]
    render_nav(module)

    # ---- render module ----
    if module == "Research":
        module_research()
    else:
        # all operational modules share the enriched recent feed
        try:
            enriched = [enrich_alert(a) for a in hub_alerts_recent(
                minutes=max(60, online_window * 4))]
        except Exception:
            enriched = []

        if module == "Overview":
            module_overview(online_window)
        elif module == "Alerts":
            module_alerts(enriched)
        elif module == "Threats":
            module_threats(enriched)
        elif module == "Network":
            module_network(enriched)
        elif module == "Agents":
            module_agents(online_window)

    # ---- auto-refresh ----
    if refresh_sec > 0:
        time.sleep(refresh_sec)
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()


if __name__ == "__main__":
    main()
