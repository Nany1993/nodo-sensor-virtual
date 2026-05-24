"""
Dashboard IoT en tiempo real — Actividad 4.

Flujo:
  nodo_timescale.py (captura) --> TimescaleDB Cloud --> este dashboard (Streamlit)

Uso:
  # Terminal 1: capturar datos
  python nodo_timescale.py --simulate --interval-sec 10 --samples 500

  # Terminal 2: abrir dashboard
  streamlit run dashboard_iot.py

El dashboard se abre en http://localhost:8501 y se refresca automáticamente.
"""

import os
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from dotenv import load_dotenv

# ── Configuracion de página ───────────────────────────────────────────────────

st.set_page_config(
    page_title="Dashboard IoT — TimescaleDB",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()

# ── Conexion a TimescaleDB ────────────────────────────────────────────────────

@st.cache_resource
def get_engine():
    """Pool de conexiones reutilizable (Streamlit lo cachea entre reruns)."""
    return dict(
        host=os.environ["TS_HOST"],
        port=int(os.environ.get("TS_PORT", 33711)),
        dbname=os.environ.get("TS_DB", "tsdb"),
        user=os.environ.get("TS_USER", "tsdbadmin"),
        password=os.environ["TS_PASSWORD"],
        sslmode="require",
        connect_timeout=15,
    )


def query(sql: str, params=None) -> pd.DataFrame:
    conn_params = get_engine()
    with psycopg2.connect(**conn_params) as conn:
        return pd.read_sql_query(sql, conn, params=params)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://assets.timescale.com/docs/images/timescale-logo.svg",
        width=160,
    )
    st.markdown("## Configuracion")

    refresco = st.selectbox(
        "Auto-refresco cada:",
        options=[10, 30, 60, 120],
        index=1,
        format_func=lambda x: f"{x} segundos",
    )

    ventana_ma = st.slider("Ventana promedio movil (muestras)", 3, 20, 5)

    t_alerta = st.slider("Umbral alerta temperatura (C)", 20, 35, 27)
    h_alerta = st.slider("Umbral alerta humedad (%)", 50, 90, 75)

    st.markdown("---")
    st.markdown(
        "**Nodo sensor activo si ves filas nuevas.**\n\n"
        "```bash\npython nodo_timescale.py \\\n"
        "  --simulate \\\n"
        "  --interval-sec 10 \\\n"
        "  --samples 500\n```"
    )
    st.markdown("---")
    st.caption("TimescaleDB Cloud — Tiger Cloud v2.27")

# ── Carga de datos ────────────────────────────────────────────────────────────

@st.cache_data(ttl=refresco)
def load_all() -> pd.DataFrame:
    df = query("""
        SELECT ts AT TIME ZONE 'America/Bogota' AS ts_local,
               temperatura_c,
               humedad_pct,
               fuente
        FROM lecturas_iot
        ORDER BY ts;
    """)
    df["ts_local"] = pd.to_datetime(df["ts_local"])
    return df


@st.cache_data(ttl=refresco)
def load_time_bucket(bucket: str = "1 hour") -> pd.DataFrame:
    return query(f"""
        SELECT
            time_bucket('{bucket}', ts) AT TIME ZONE 'America/Bogota' AS periodo,
            ROUND(AVG(temperatura_c)::numeric, 2) AS temp_prom,
            ROUND(MIN(temperatura_c)::numeric, 2) AS temp_min,
            ROUND(MAX(temperatura_c)::numeric, 2) AS temp_max,
            ROUND(AVG(humedad_pct)::numeric,   2) AS hum_prom,
            COUNT(*) AS n
        FROM lecturas_iot
        GROUP BY periodo
        ORDER BY periodo;
    """)


@st.cache_data(ttl=refresco)
def load_total() -> int:
    return query("SELECT COUNT(*) AS n FROM lecturas_iot;")["n"].iloc[0]


# ── Header principal ──────────────────────────────────────────────────────────

st.title("Dashboard IoT — Monitoreo Ambiental en Tiempo Real")
st.caption(
    "Datos desde sensor DHT11 virtual (CounterFit) almacenados en "
    "**TimescaleDB Cloud (Tiger Cloud)**. Actividad 4 — Maestria en IA."
)

# Botón de refresco manual
col_ref, col_info = st.columns([1, 9])
with col_ref:
    if st.button("Refrescar ahora"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.info(f"Auto-refresco cada {refresco} s. Usa el sidebar para cambiar la frecuencia.")

st.divider()

# ── Carga principal ───────────────────────────────────────────────────────────

try:
    df = load_all()
    total = load_total()
    df_hora = load_time_bucket("1 hour")
    df_dia  = load_time_bucket("1 day")
except Exception as e:
    st.error(f"Error conectando a TimescaleDB: {e}")
    st.stop()

if df.empty:
    st.warning(
        "No hay datos en la hypertable aun. "
        "Ejecuta `python nodo_timescale.py --simulate --interval-sec 5 --samples 50` en otra terminal."
    )
    st.stop()

# ── PESTANAS ──────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "Datos en vivo",
    "Analisis exploratorio",
    "Datos procesados",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DATOS EN VIVO
# ─────────────────────────────────────────────────────────────────────────────

with tab1:
    ultima = df.iloc[-1]

    st.subheader("Estado actual del sensor")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Temperatura",
        f"{ultima['temperatura_c']:.2f} C",
        delta=f"{ultima['temperatura_c'] - df.iloc[-2]['temperatura_c']:.2f} C"
        if len(df) > 1 else None,
    )
    m2.metric(
        "Humedad relativa",
        f"{ultima['humedad_pct']:.1f} %",
        delta=f"{ultima['humedad_pct'] - df.iloc[-2]['humedad_pct']:.1f} %"
        if len(df) > 1 else None,
    )
    m3.metric("Total lecturas", f"{total:,}")
    m4.metric("Ultima lectura", ultima["ts_local"].strftime("%H:%M:%S"))

    st.divider()

    # Alertas activas
    alertas = df[(df["temperatura_c"] > t_alerta) | (df["humedad_pct"] > h_alerta)]
    if len(alertas) > 0:
        st.warning(
            f"**{len(alertas)} lecturas en condicion de alerta** "
            f"(T > {t_alerta} C o HR > {h_alerta} %) — "
            f"{100*len(alertas)/len(df):.1f}% del total."
        )
    else:
        st.success("Sin alertas activas en el rango actual.")

    st.subheader("Ultimas 20 lecturas")
    st.dataframe(
        df.tail(20)[["ts_local", "temperatura_c", "humedad_pct", "fuente"]]
        .sort_values("ts_local", ascending=False)
        .rename(columns={
            "ts_local": "Timestamp",
            "temperatura_c": "Temp (C)",
            "humedad_pct": "Humedad (%)",
            "fuente": "Fuente",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # Minigráfica en vivo (últimas 50 muestras)
    df_live = df.tail(50)
    fig_live = go.Figure()
    fig_live.add_trace(go.Scatter(
        x=df_live["ts_local"], y=df_live["temperatura_c"],
        name="Temperatura (C)", line=dict(color="#e94560", width=2),
        mode="lines+markers", marker=dict(size=4),
    ))
    fig_live.add_trace(go.Scatter(
        x=df_live["ts_local"], y=df_live["humedad_pct"],
        name="Humedad (%)", line=dict(color="#4a90e2", width=2),
        mode="lines+markers", marker=dict(size=4),
        yaxis="y2",
    ))
    fig_live.update_layout(
        title="Ultimas 50 lecturas (en vivo)",
        xaxis_title="Tiempo",
        yaxis=dict(title="Temperatura (C)", color="#e94560"),
        yaxis2=dict(title="Humedad (%)", color="#4a90e2", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        height=380,
    )
    st.plotly_chart(fig_live, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ANALISIS EXPLORATORIO
# ─────────────────────────────────────────────────────────────────────────────

with tab2:
    st.subheader("Serie temporal completa — datos crudos")

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=df["ts_local"], y=df["temperatura_c"],
        name="Temperatura (C)", line=dict(color="#e94560", width=1.5),
    ))
    fig_ts.add_trace(go.Scatter(
        x=df["ts_local"], y=df["humedad_pct"],
        name="Humedad (%)", line=dict(color="#4a90e2", width=1.5),
        yaxis="y2",
    ))
    fig_ts.update_layout(
        xaxis_title="Tiempo",
        yaxis=dict(title="Temperatura (C)", color="#e94560"),
        yaxis2=dict(title="Humedad (%)", color="#4a90e2", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        height=400,
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        fig_ht = px.histogram(
            df, x="temperatura_c", nbins=20,
            title="Distribucion de temperatura",
            labels={"temperatura_c": "Temperatura (C)"},
            color_discrete_sequence=["#e94560"],
        )
        st.plotly_chart(fig_ht, use_container_width=True)
    with col_h2:
        fig_hh = px.histogram(
            df, x="humedad_pct", nbins=20,
            title="Distribucion de humedad",
            labels={"humedad_pct": "Humedad (%)"},
            color_discrete_sequence=["#4a90e2"],
        )
        st.plotly_chart(fig_hh, use_container_width=True)

    st.subheader("Estadisticas descriptivas")
    stats = (
        df[["temperatura_c", "humedad_pct"]]
        .describe()
        .round(3)
        .rename(columns={"temperatura_c": "Temperatura (C)", "humedad_pct": "Humedad (%)"})
    )
    st.dataframe(stats, use_container_width=True)

    st.subheader("Lecturas en condicion de alerta")
    df_alertas = df[(df["temperatura_c"] > t_alerta) | (df["humedad_pct"] > h_alerta)].copy()
    if df_alertas.empty:
        st.success("Ninguna lectura supera los umbrales configurados.")
    else:
        st.dataframe(
            df_alertas[["ts_local", "temperatura_c", "humedad_pct"]]
            .rename(columns={
                "ts_local": "Timestamp",
                "temperatura_c": "Temp (C)",
                "humedad_pct": "Humedad (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — DATOS PROCESADOS
# ─────────────────────────────────────────────────────────────────────────────

with tab3:
    st.subheader(f"Promedio movil (ventana = {ventana_ma} muestras)")

    df_proc = df.copy()
    df_proc["temp_ma"] = df_proc["temperatura_c"].rolling(window=ventana_ma, center=True).mean()
    df_proc["hum_ma"]  = df_proc["humedad_pct"].rolling(window=ventana_ma, center=True).mean()

    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(
        x=df_proc["ts_local"], y=df_proc["temperatura_c"],
        name="Temp raw", line=dict(color="rgba(233,69,96,0.3)", width=1),
    ))
    fig_ma.add_trace(go.Scatter(
        x=df_proc["ts_local"], y=df_proc["temp_ma"],
        name=f"Temp MA-{ventana_ma}", line=dict(color="#e94560", width=2.5),
    ))
    fig_ma.add_trace(go.Scatter(
        x=df_proc["ts_local"], y=df_proc["humedad_pct"],
        name="Hum raw", line=dict(color="rgba(74,144,226,0.3)", width=1),
        yaxis="y2",
    ))
    fig_ma.add_trace(go.Scatter(
        x=df_proc["ts_local"], y=df_proc["hum_ma"],
        name=f"Hum MA-{ventana_ma}", line=dict(color="#4a90e2", width=2.5),
        yaxis="y2",
    ))
    fig_ma.update_layout(
        xaxis_title="Tiempo",
        yaxis=dict(title="Temperatura (C)", color="#e94560"),
        yaxis2=dict(title="Humedad (%)", color="#4a90e2", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12),
        height=420,
    )
    st.plotly_chart(fig_ma, use_container_width=True)

    st.subheader("Agregados por hora — time_bucket() en TimescaleDB")
    if df_hora.empty:
        st.info("Aun no hay suficientes datos para cubos horarios.")
    else:
        df_hora["periodo"] = pd.to_datetime(df_hora["periodo"])
        fig_bucket = go.Figure()
        fig_bucket.add_trace(go.Bar(
            x=df_hora["periodo"], y=df_hora["temp_prom"],
            name="Temp prom/hora", marker_color="#e94560", opacity=0.8,
            error_y=dict(
                type="data",
                symmetric=False,
                array=(df_hora["temp_max"] - df_hora["temp_prom"]).tolist(),
                arrayminus=(df_hora["temp_prom"] - df_hora["temp_min"]).tolist(),
            ),
        ))
        fig_bucket.add_trace(go.Scatter(
            x=df_hora["periodo"], y=df_hora["hum_prom"],
            name="Hum prom/hora", line=dict(color="#4a90e2", width=2),
            mode="lines+markers", yaxis="y2",
        ))
        fig_bucket.update_layout(
            xaxis_title="Hora",
            yaxis=dict(title="Temperatura prom (C)"),
            yaxis2=dict(title="Humedad prom (%)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1),
            height=380,
        )
        st.plotly_chart(fig_bucket, use_container_width=True)

        st.dataframe(
            df_hora.rename(columns={
                "periodo": "Hora",
                "temp_prom": "Temp prom (C)",
                "temp_min": "Temp min (C)",
                "temp_max": "Temp max (C)",
                "hum_prom": "Hum prom (%)",
                "n": "N lecturas",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Normalizacion min-max [0, 1]")
    df_proc["temp_norm"] = (
        (df_proc["temperatura_c"] - df_proc["temperatura_c"].min()) /
        (df_proc["temperatura_c"].max() - df_proc["temperatura_c"].min())
    )
    df_proc["hum_norm"] = (
        (df_proc["humedad_pct"] - df_proc["humedad_pct"].min()) /
        (df_proc["humedad_pct"].max() - df_proc["humedad_pct"].min())
    )
    fig_norm = go.Figure()
    fig_norm.add_trace(go.Scatter(
        x=df_proc["ts_local"], y=df_proc["temp_norm"],
        name="Temp normalizada", line=dict(color="#e94560", width=2),
    ))
    fig_norm.add_trace(go.Scatter(
        x=df_proc["ts_local"], y=df_proc["hum_norm"],
        name="Hum normalizada", line=dict(color="#4a90e2", width=2),
    ))
    fig_norm.update_layout(
        title="Temperatura y humedad normalizadas en la misma escala [0,1]",
        xaxis_title="Tiempo",
        yaxis_title="Valor normalizado",
        legend=dict(orientation="h", y=1.1),
        height=350,
    )
    st.plotly_chart(fig_norm, use_container_width=True)

    st.subheader("Resumen diario")
    if df_dia.empty:
        st.info("Aun no hay datos de dias completos.")
    else:
        st.dataframe(
            df_dia.rename(columns={
                "periodo": "Dia",
                "temp_prom": "Temp prom (C)",
                "temp_min": "Temp min (C)",
                "temp_max": "Temp max (C)",
                "hum_prom": "Hum prom (%)",
                "n": "N lecturas",
            }),
            use_container_width=True,
            hide_index=True,
        )

# ── Auto-refresco ─────────────────────────────────────────────────────────────

st.divider()
st.caption(
    f"Refrescando cada {refresco} s. "
    "Para despliegue en la nube ver: https://streamlit.io/cloud"
)

time.sleep(refresco)
st.rerun()
