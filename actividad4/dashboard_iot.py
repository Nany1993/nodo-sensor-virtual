"""
Dashboard IoT en tiempo real — Actividad 4.

Flujo:
  nodo_timescale.py (captura) --> TimescaleDB Cloud --> este dashboard (Streamlit)

Uso:
  # Terminal 1: capturar datos desde CounterFit
  python nodo_timescale.py --port 5050 --interval-sec 30 --samples 360

  # Terminal 2: abrir dashboard
  streamlit run dashboard_iot.py

El dashboard se abre en http://localhost:8501 y se refresca automaticamente.
"""

import os
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Configuracion de pagina ───────────────────────────────────────────────────

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
    """Motor SQLAlchemy reutilizable (Streamlit lo cachea entre reruns)."""
    host     = os.environ["TS_HOST"]
    port     = int(os.environ.get("TS_PORT", 33711))
    db       = os.environ.get("TS_DB", "tsdb")
    user     = os.environ.get("TS_USER", "tsdbadmin")
    password = os.environ["TS_PASSWORD"]
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}?sslmode=require"
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 15})


def query(sql: str) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql_query(text(sql), conn)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://assets.timescale.com/docs/images/timescale-logo.svg",
        width=160,
    )
    st.markdown("## Configuracion del panel")

    refresco = st.selectbox(
        "Actualizar pantalla cada:",
        options=[10, 30, 60, 120],
        index=1,
        format_func=lambda x: f"{x} segundos",
    )

    ventana_ma = st.slider(
        "Suavizado del grafico (num. de muestras)",
        3, 20, 5,
        help="Cuantas lecturas consecutivas se promedian para suavizar la curva. "
             "Valor mas alto = curva mas lisa pero menos detalle.",
    )

    t_alerta = st.slider(
        "Temperatura de alerta (°C)",
        20, 35, 27,
        help="Si la temperatura supera este valor, se marca como condicion de alerta.",
    )
    h_alerta = st.slider(
        "Humedad de alerta (%)",
        50, 90, 75,
        help="Si la humedad supera este valor, se marca como condicion de alerta.",
    )

    st.markdown("---")
    st.markdown("**El sensor esta activo si los datos aumentan con cada refresco.**")
    st.markdown("---")
    st.caption("TimescaleDB Cloud — Tiger Cloud v2.27")

# ── Carga de datos ────────────────────────────────────────────────────────────

@st.cache_data(ttl=refresco)
def load_all() -> pd.DataFrame:
    df = query("""
        SELECT ts AT TIME ZONE 'America/Bogota' AS ts_local,
               temperatura_c,
               humedad_pct,
               temp_movil,
               hum_movil,
               temp_norm,
               hum_norm,
               valida,
               fuente
        FROM lecturas_iot
        WHERE valida = TRUE
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


# ── Encabezado principal ──────────────────────────────────────────────────────

st.title("Monitoreo Ambiental IoT en Tiempo Real")
st.caption(
    "Lecturas de temperatura y humedad generadas por el sensor virtual DHT11 (CounterFit), "
    "almacenadas en **TimescaleDB Cloud**. Actividad 4 — Maestria en Inteligencia Artificial."
)
st.info(
    "**Pipeline de procesamiento activo:** cada lectura pasa por "
    "**preprocesamiento** (validacion de rangos) → **filtrado** (anti-duplicados, time_bucket) → "
    "**transformacion** (promedio movil, normalizacion min-max) antes de almacenarse en TimescaleDB. "
    "Los valores procesados que ves en la pestana 'Datos procesados' se calcularon en el nodo sensor, no en el dashboard.",
    icon="⚙️",
)

col_ref, col_info = st.columns([1, 9])
with col_ref:
    if st.button("Actualizar ahora"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.info(
        f"La pantalla se actualiza automaticamente cada {refresco} segundos. "
        "Puedes cambiar este valor en el panel izquierdo."
    )

st.divider()

# ── Carga principal ───────────────────────────────────────────────────────────

try:
    df = load_all()
    total = load_total()
    df_hora = load_time_bucket("1 hour")
    df_dia  = load_time_bucket("1 day")
except Exception as e:
    st.error(f"No se pudo conectar a la base de datos: {e}")
    st.stop()

if df.empty:
    st.warning(
        "Aun no hay datos registrados. "
        "Inicia la captura con: `.venv\\Scripts\\python nodo_timescale.py --port 5050`"
    )
    st.stop()

# ── PESTANAS ──────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "📡  Datos en vivo",
    "📊  Analisis exploratorio",
    "⚙️  Datos procesados",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — DATOS EN VIVO
# ─────────────────────────────────────────────────────────────────────────────

with tab1:
    ultima = df.iloc[-1]

    st.subheader("Lectura mas reciente del sensor")
    st.caption(
        "Estos valores corresponden a la ultima lectura registrada por el sensor DHT11 virtual. "
        "La flecha indica si subio o bajo respecto a la lectura anterior."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Temperatura",
        f"{ultima['temperatura_c']:.2f} °C",
        delta=f"{ultima['temperatura_c'] - df.iloc[-2]['temperatura_c']:.2f} °C"
        if len(df) > 1 else None,
    )
    m2.metric(
        "Humedad relativa",
        f"{ultima['humedad_pct']:.1f} %",
        delta=f"{ultima['humedad_pct'] - df.iloc[-2]['humedad_pct']:.1f} %"
        if len(df) > 1 else None,
    )
    m3.metric(
        "Total de lecturas guardadas",
        f"{total:,}",
        help="Numero total de registros almacenados en TimescaleDB Cloud.",
    )
    m4.metric(
        "Hora de la ultima lectura",
        ultima["ts_local"].strftime("%H:%M:%S"),
    )

    st.divider()

    # Alertas activas
    alertas = df[(df["temperatura_c"] > t_alerta) | (df["humedad_pct"] > h_alerta)]
    if len(alertas) > 0:
        st.warning(
            f"**{len(alertas)} lecturas superan los umbrales de alerta** "
            f"(Temperatura > {t_alerta} °C o Humedad > {h_alerta} %) — "
            f"representa el {100*len(alertas)/len(df):.1f}% del total de registros. "
            "Puedes ajustar estos umbrales desde el panel izquierdo."
        )
    else:
        st.success(
            f"Todos los valores estan dentro de los rangos normales "
            f"(Temperatura <= {t_alerta} °C y Humedad <= {h_alerta} %)."
        )

    st.subheader("Ultimas 20 lecturas registradas")
    st.caption("Las lecturas mas recientes aparecen primero. La columna 'Fuente' indica si el dato vino del sensor virtual (counterfit) o de una simulacion interna.")
    st.dataframe(
        df.tail(20)[["ts_local", "temperatura_c", "humedad_pct", "fuente"]]
        .sort_values("ts_local", ascending=False)
        .rename(columns={
            "ts_local": "Fecha y hora",
            "temperatura_c": "Temperatura (°C)",
            "humedad_pct": "Humedad (%)",
            "fuente": "Fuente",
        }),
        width="stretch",
        hide_index=True,
    )

    st.subheader("Grafico de las ultimas 50 lecturas")
    st.caption(
        "Muestra como han variado la temperatura (rojo, eje izquierdo) y la humedad (azul, eje derecho) "
        "en las ultimas 50 mediciones. Cada punto es una lectura del sensor. "
        "Puedes hacer zoom con el mouse o descargar la imagen con los iconos de la esquina superior derecha."
    )
    df_live = df.tail(50)
    fig_live = go.Figure()
    fig_live.add_trace(go.Scatter(
        x=df_live["ts_local"], y=df_live["temperatura_c"],
        name="Temperatura (°C)", line=dict(color="#e94560", width=2),
        mode="lines+markers", marker=dict(size=4),
    ))
    fig_live.add_trace(go.Scatter(
        x=df_live["ts_local"], y=df_live["humedad_pct"],
        name="Humedad (%)", line=dict(color="#4a90e2", width=2),
        mode="lines+markers", marker=dict(size=4),
        yaxis="y2",
    ))
    fig_live.update_layout(
        xaxis_title="Hora de la lectura",
        yaxis=dict(title="Temperatura (°C)", color="#e94560"),
        yaxis2=dict(title="Humedad relativa (%)", color="#4a90e2", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        height=380,
    )
    st.plotly_chart(fig_live, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ANALISIS EXPLORATORIO
# ─────────────────────────────────────────────────────────────────────────────

with tab2:
    st.subheader("Comportamiento de los sensores a lo largo del tiempo")
    st.caption(
        "Esta grafica muestra TODOS los datos capturados desde que inicio la medicion. "
        "La linea roja es la temperatura (escala izquierda) y la azul es la humedad (escala derecha). "
        "Si las lineas son muy irregulares, es normal: los sensores tienen variaciones naturales entre lectura y lectura."
    )
    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=df["ts_local"], y=df["temperatura_c"],
        name="Temperatura (°C)", line=dict(color="#e94560", width=1.5),
    ))
    fig_ts.add_trace(go.Scatter(
        x=df["ts_local"], y=df["humedad_pct"],
        name="Humedad (%)", line=dict(color="#4a90e2", width=1.5),
        yaxis="y2",
    ))
    fig_ts.update_layout(
        xaxis_title="Fecha y hora de la lectura",
        yaxis=dict(title="Temperatura (°C)", color="#e94560"),
        yaxis2=dict(title="Humedad relativa (%)", color="#4a90e2", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        height=400,
    )
    st.plotly_chart(fig_ts, width="stretch")

    st.subheader("Distribucion de valores — Histogramas")
    st.caption(
        "Los histogramas muestran cuantas veces aparecio cada rango de valor. "
        "Una barra alta significa que ese rango de temperatura o humedad fue el mas frecuente. "
        "Si la distribucion es uniforme (todas las barras de altura similar), significa que el sensor genero valores de forma aleatoria en todo el rango configurado."
    )
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        fig_ht = px.histogram(
            df, x="temperatura_c", nbins=20,
            title="¿Cuantas veces se midio cada rango de temperatura?",
            labels={"temperatura_c": "Temperatura (°C)", "count": "Numero de lecturas"},
            color_discrete_sequence=["#e94560"],
        )
        fig_ht.update_layout(yaxis_title="Numero de lecturas")
        st.plotly_chart(fig_ht, width="stretch")
    with col_h2:
        fig_hh = px.histogram(
            df, x="humedad_pct", nbins=20,
            title="¿Cuantas veces se midio cada rango de humedad?",
            labels={"humedad_pct": "Humedad (%)", "count": "Numero de lecturas"},
            color_discrete_sequence=["#4a90e2"],
        )
        fig_hh.update_layout(yaxis_title="Numero de lecturas")
        st.plotly_chart(fig_hh, width="stretch")

    st.subheader("Resumen estadistico de los datos")
    st.caption(
        "Esta tabla resume el comportamiento de los datos: "
        "**count** = total de lecturas, **mean** = promedio, **std** = que tanto varian los datos respecto al promedio (variabilidad), "
        "**min/max** = valor mas bajo y mas alto registrado, **25%/50%/75%** = percentiles (el 50% es la mediana)."
    )
    stats = (
        df[["temperatura_c", "humedad_pct"]]
        .describe()
        .round(3)
        .rename(columns={"temperatura_c": "Temperatura (°C)", "humedad_pct": "Humedad (%)"})
        .rename(index={
            "count": "Total lecturas",
            "mean": "Promedio",
            "std": "Desviacion estandar",
            "min": "Valor minimo",
            "25%": "Percentil 25%",
            "50%": "Mediana (50%)",
            "75%": "Percentil 75%",
            "max": "Valor maximo",
        })
    )
    st.dataframe(stats, width="stretch")

    st.subheader("Lecturas que superan los umbrales de alerta")
    st.caption(
        f"Se filtran las lecturas donde la temperatura supero {t_alerta} °C o la humedad supero {h_alerta} %. "
        "En un sistema real, estas lecturas podrian activar una alarma o enviar una notificacion."
    )
    df_alertas = df[(df["temperatura_c"] > t_alerta) | (df["humedad_pct"] > h_alerta)].copy()
    if df_alertas.empty:
        st.success(f"No hay lecturas que superen los umbrales configurados ({t_alerta} °C / {h_alerta} %).")
    else:
        st.dataframe(
            df_alertas[["ts_local", "temperatura_c", "humedad_pct"]]
            .sort_values("ts_local", ascending=False)
            .rename(columns={
                "ts_local": "Fecha y hora",
                "temperatura_c": "Temperatura (°C)",
                "humedad_pct": "Humedad (%)",
            }),
            width="stretch",
            hide_index=True,
        )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — DATOS PROCESADOS
# ─────────────────────────────────────────────────────────────────────────────

with tab3:

    st.caption(
        "Los valores de esta pestana fueron calculados por el **nodo sensor** antes de ser almacenados "
        "en TimescaleDB. No son calculos del dashboard — son columnas reales de la base de datos."
    )

    # ── Promedio movil (columnas pre-calculadas en TimescaleDB) ───────────────
    st.subheader("Suavizado de la senal — Promedio movil (ventana: 5 lecturas)")
    st.caption(
        "Las lineas transparentes son los datos crudos del sensor. "
        "Las lineas solidas son el promedio movil de 5 muestras calculado en el nodo sensor "
        "y almacenado como columna `temp_movil` / `hum_movil` en TimescaleDB. "
        "Este suavizado reduce el ruido y revela la tendencia real de la senal."
    )

    tiene_movil = "temp_movil" in df.columns and df["temp_movil"].notna().any()

    fig_ma = go.Figure()
    fig_ma.add_trace(go.Scatter(
        x=df["ts_local"], y=df["temperatura_c"],
        name="Temperatura original", line=dict(color="rgba(233,69,96,0.3)", width=1),
    ))
    if tiene_movil:
        fig_ma.add_trace(go.Scatter(
            x=df["ts_local"], y=df["temp_movil"],
            name="Temperatura MA-5 (almacenada en BD)", line=dict(color="#e94560", width=2.5),
        ))
    fig_ma.add_trace(go.Scatter(
        x=df["ts_local"], y=df["humedad_pct"],
        name="Humedad original", line=dict(color="rgba(74,144,226,0.3)", width=1),
        yaxis="y2",
    ))
    if tiene_movil:
        fig_ma.add_trace(go.Scatter(
            x=df["ts_local"], y=df["hum_movil"],
            name="Humedad MA-5 (almacenada en BD)", line=dict(color="#4a90e2", width=2.5),
            yaxis="y2",
        ))
    fig_ma.update_layout(
        xaxis_title="Fecha y hora de la lectura",
        yaxis=dict(title="Temperatura (°C)", color="#e94560"),
        yaxis2=dict(title="Humedad relativa (%)", color="#4a90e2", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12),
        height=420,
    )
    st.plotly_chart(fig_ma, width="stretch")

    # ── Agregados por hora ────────────────────────────────────────────────────
    st.subheader("Promedio por hora — Resumen horario de los sensores")
    st.caption(
        "En lugar de mostrar cada lectura individual, esta grafica agrupa todas las lecturas de cada hora "
        "y calcula el promedio. Las barras rojas son la temperatura promedio por hora (las lineas verticales "
        "sobre cada barra muestran el rango entre el valor minimo y maximo de esa hora). "
        "La linea azul es la humedad promedio por hora. "
        "Este tipo de vista es util para detectar si hay horas del dia con condiciones ambientales diferentes."
    )
    if df_hora.empty:
        st.info("Aun no hay suficientes datos para calcular promedios por hora. Espera a que se acumulen mas lecturas.")
    else:
        df_hora["periodo"] = pd.to_datetime(df_hora["periodo"])
        fig_bucket = go.Figure()
        fig_bucket.add_trace(go.Bar(
            x=df_hora["periodo"], y=df_hora["temp_prom"],
            name="Temperatura promedio por hora", marker_color="#e94560", opacity=0.8,
            error_y=dict(
                type="data",
                symmetric=False,
                array=(df_hora["temp_max"] - df_hora["temp_prom"]).tolist(),
                arrayminus=(df_hora["temp_prom"] - df_hora["temp_min"]).tolist(),
            ),
        ))
        fig_bucket.add_trace(go.Scatter(
            x=df_hora["periodo"], y=df_hora["hum_prom"],
            name="Humedad promedio por hora", line=dict(color="#4a90e2", width=2),
            mode="lines+markers", yaxis="y2",
        ))
        fig_bucket.update_layout(
            xaxis_title="Hora del dia",
            yaxis=dict(title="Temperatura promedio (°C)"),
            yaxis2=dict(title="Humedad promedio (%)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1),
            height=380,
        )
        st.plotly_chart(fig_bucket, width="stretch")

        st.caption("Tabla de resumen por hora: muestra el promedio, minimo, maximo y cuantas lecturas se tomaron en cada franja horaria.")
        st.dataframe(
            df_hora.rename(columns={
                "periodo": "Hora",
                "temp_prom": "Temp. promedio (°C)",
                "temp_min": "Temp. minima (°C)",
                "temp_max": "Temp. maxima (°C)",
                "hum_prom": "Humedad prom. (%)",
                "n": "Num. lecturas",
            }),
            width="stretch",
            hide_index=True,
        )

    # ── Normalizacion (columnas pre-calculadas en TimescaleDB) ────────────────
    st.subheader("Comparacion normalizada de temperatura y humedad")
    st.caption(
        "La normalizacion min-max transforma los valores para que queden entre 0 y 1, donde "
        "0 es el valor mas bajo registrado y 1 el mas alto. "
        "Calculada por el nodo sensor y almacenada como columnas `temp_norm` / `hum_norm` en TimescaleDB. "
        "Permite comparar temperatura y humedad en la misma escala aunque tengan unidades diferentes."
    )
    tiene_norm = "temp_norm" in df.columns and df["temp_norm"].notna().any()
    fig_norm = go.Figure()
    if tiene_norm:
        fig_norm.add_trace(go.Scatter(
            x=df["ts_local"], y=df["temp_norm"],
            name="Temperatura normalizada (almacenada en BD)", line=dict(color="#e94560", width=2),
        ))
        fig_norm.add_trace(go.Scatter(
            x=df["ts_local"], y=df["hum_norm"],
            name="Humedad normalizada (almacenada en BD)", line=dict(color="#4a90e2", width=2),
        ))
    else:
        st.info("Ejecuta nodo_timescale.py actualizado para generar columnas normalizadas en la BD.")
    fig_norm.update_layout(
        xaxis_title="Fecha y hora de la lectura",
        yaxis_title="Valor normalizado (0 = minimo, 1 = maximo)",
        legend=dict(orientation="h", y=1.1),
        height=350,
    )
    if tiene_norm:
        st.plotly_chart(fig_norm, width="stretch")

    # ── Resumen diario ────────────────────────────────────────────────────────
    st.subheader("Resumen por dia")
    st.caption(
        "Agrupa todas las lecturas por dia y muestra el promedio y la variabilidad (desviacion estandar) "
        "de temperatura y humedad. Util para comparar el comportamiento ambiental entre diferentes dias."
    )
    if df_dia.empty:
        st.info("Aun no hay datos de dias completos. Esta tabla se llenara despues de 24 horas de medicion continua.")
    else:
        st.dataframe(
            df_dia.rename(columns={
                "periodo": "Fecha",
                "temp_prom": "Temp. promedio (°C)",
                "temp_min": "Temp. minima (°C)",
                "temp_max": "Temp. maxima (°C)",
                "hum_prom": "Humedad prom. (%)",
                "n": "Num. lecturas",
            }),
            width="stretch",
            hide_index=True,
        )

# ── Pie de pagina ─────────────────────────────────────────────────────────────

st.divider()
st.caption(
    f"Pantalla actualizada cada {refresco} segundos automaticamente. "
    "Para publicar este dashboard en internet ver: https://streamlit.io/cloud"
)

time.sleep(refresco)
st.rerun()
