"""
Dashboard IoT — TimescaleDB Cloud.
Login: admin / admin
"""

from __future__ import annotations

import os
import secrets
from contextlib import nullcontext
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

DEFAULT_DASHBOARD_USER = "admin"
DEFAULT_DASHBOARD_PASSWORD = "admin"
SENSOR_INTERVAL_SEC = 5
AUTO_REFRESH_SEC = 30
DB_CONNECT_TIMEOUT = 8
TZ = "America/Bogota"

SCHEMA_ALTER_SQL = [
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS temp_movil DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS hum_movil DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS temp_norm DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS hum_norm DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS valida BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS fuente TEXT DEFAULT 'counterfit';",
]

st.set_page_config(
    page_title="Dashboard IoT — TimescaleDB",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def _dashboard_credentials() -> tuple[str, str]:
    user = os.environ.get("DASHBOARD_USER", "").strip() or DEFAULT_DASHBOARD_USER
    password = os.environ.get("DASHBOARD_PASSWORD", "").strip() or DEFAULT_DASHBOARD_PASSWORD
    return user, password


def _verify_login(username: str, password: str) -> bool:
    expected_user, expected_password = _dashboard_credentials()
    return (
        secrets.compare_digest(username.strip(), expected_user)
        and secrets.compare_digest(password.strip(), expected_password)
    )


def _render_login() -> None:
    st.title("Acceso al dashboard IoT")
    if st.session_state.pop("login_error", None):
        st.error("Usuario o contraseña incorrectos.")
    _l, col, _r = st.columns([1, 1.2, 1])
    with col:
        with st.form("login_form"):
            username = st.text_input("Usuario", value="admin")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Iniciar sesion", use_container_width=True)
    if submitted:
        if _verify_login(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username.strip()
            st.rerun()
        st.session_state.login_error = True
        st.rerun()


if not st.session_state.authenticated:
    _render_login()
    st.stop()


@st.cache_resource
def get_engine():
    host = os.environ["TS_HOST"]
    port = int(os.environ.get("TS_PORT", 33711))
    db = os.environ.get("TS_DB", "tsdb")
    user = os.environ.get("TS_USER", "tsdbadmin")
    password = os.environ["TS_PASSWORD"]
    url = (
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        f"?sslmode=require&connect_timeout={DB_CONNECT_TIMEOUT}"
    )
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": DB_CONNECT_TIMEOUT})


def query(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


@st.cache_resource
def ensure_schema() -> None:
    with get_engine().connect() as conn:
        for stmt in SCHEMA_ALTER_SQL:
            conn.execute(text(stmt))
        conn.commit()


def _in_clause(field: str, values: Sequence[int], prefix: str) -> tuple[str, dict]:
    if len(values) == 1:
        return f"{field} = :{prefix}_0", {f"{prefix}_0": values[0]}
    placeholders = ", ".join(f":{prefix}_{i}" for i in range(len(values)))
    params = {f"{prefix}_{i}": v for i, v in enumerate(values)}
    return f"{field} IN ({placeholders})", params


def _where_filtros(
    year: Optional[int],
    months: Optional[Sequence[int]],
    days: Optional[Sequence[int]],
    hour: Optional[int],
) -> tuple[str, dict]:
    parts = ["COALESCE(valida, TRUE) = TRUE"]
    params: dict = {}
    ts_expr = f"ts AT TIME ZONE '{TZ}'"
    if year is not None:
        parts.append(f"EXTRACT(YEAR FROM {ts_expr}) = :year")
        params["year"] = year
    if months:
        clause, month_params = _in_clause(
            f"EXTRACT(MONTH FROM {ts_expr})::int", sorted(months), "month"
        )
        parts.append(clause)
        params.update(month_params)
    if days:
        clause, day_params = _in_clause(
            f"EXTRACT(DAY FROM {ts_expr})::int", sorted(days), "day"
        )
        parts.append(clause)
        params.update(day_params)
    if hour is not None:
        parts.append(f"EXTRACT(HOUR FROM {ts_expr}) = :hour")
        params["hour"] = hour
    return " AND ".join(parts), params


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_years() -> list[int]:
    ensure_schema()
    df = query(f"""
        SELECT DISTINCT EXTRACT(YEAR FROM ts AT TIME ZONE '{TZ}')::int AS y
        FROM lecturas_iot
        ORDER BY y;
    """)
    return df["y"].tolist()


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_months(year: Optional[int]) -> list[int]:
    ensure_schema()
    where, params = _where_filtros(year, None, None, None)
    df = query(f"""
        SELECT DISTINCT EXTRACT(MONTH FROM ts AT TIME ZONE '{TZ}')::int AS m
        FROM lecturas_iot
        WHERE {where}
        ORDER BY m;
    """, params)
    return df["m"].tolist()


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_days(year: Optional[int], months: Optional[tuple[int, ...]]) -> list[int]:
    ensure_schema()
    where, params = _where_filtros(year, months, None, None)
    df = query(f"""
        SELECT DISTINCT EXTRACT(DAY FROM ts AT TIME ZONE '{TZ}')::int AS d
        FROM lecturas_iot
        WHERE {where}
        ORDER BY d;
    """, params)
    return df["d"].tolist()


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_hours(
    year: Optional[int],
    months: Optional[tuple[int, ...]],
    days: Optional[tuple[int, ...]],
) -> list[int]:
    ensure_schema()
    where, params = _where_filtros(year, months, days, None)
    df = query(f"""
        SELECT DISTINCT EXTRACT(HOUR FROM ts AT TIME ZONE '{TZ}')::int AS h
        FROM lecturas_iot
        WHERE {where}
        ORDER BY h;
    """, params)
    return df["h"].tolist()


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_total() -> int:
    ensure_schema()
    return int(query("SELECT COUNT(*) AS n FROM lecturas_iot;")["n"].iloc[0])


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_filtered(
    year: Optional[int],
    months: Optional[tuple[int, ...]],
    days: Optional[tuple[int, ...]],
    hour: Optional[int],
) -> pd.DataFrame:
    ensure_schema()
    where, params = _where_filtros(year, months, days, hour)
    df = query(f"""
        SELECT ts AT TIME ZONE '{TZ}' AS ts_local,
               temperatura_c, humedad_pct, fuente
        FROM lecturas_iot
        WHERE {where}
        ORDER BY ts;
    """, params)
    df["ts_local"] = pd.to_datetime(df["ts_local"])
    return df


@st.cache_data(ttl=AUTO_REFRESH_SEC, show_spinner=False)
def load_recent(limit: int = 120) -> pd.DataFrame:
    ensure_schema()
    df = query(f"""
        SELECT ts AT TIME ZONE '{TZ}' AS ts_local,
               temperatura_c, humedad_pct, fuente
        FROM lecturas_iot
        WHERE COALESCE(valida, TRUE) = TRUE
        ORDER BY ts DESC
        LIMIT {limit};
    """)
    df["ts_local"] = pd.to_datetime(df["ts_local"])
    return df.sort_values("ts_local")


def _filtro_resumen(
    year: Optional[int],
    months: Optional[Sequence[int]],
    days: Optional[Sequence[int]],
    hour: Optional[int],
) -> str:
    meses = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    partes = []
    if year is not None:
        partes.append(str(year))
    if months:
        if len(months) == 1:
            partes.append(meses[months[0]])
        else:
            partes.append(", ".join(meses[m] for m in sorted(months)))
    if days:
        if len(days) == 1:
            partes.append(f"dia {days[0]}")
        else:
            partes.append("dias " + ", ".join(str(d) for d in sorted(days)))
    if hour is not None:
        partes.append(f"{hour:02d}:00")
    return " · ".join(partes) if partes else "Sin filtros (todos los datos)"


def _chart_correlacion(df: pd.DataFrame) -> None:
    if len(df) < 2:
        st.info("Se necesitan al menos 2 lecturas para correlacion y dispersion.")
        return
    pearson = df["temperatura_c"].corr(df["humedad_pct"])
    spearman = df["temperatura_c"].corr(df["humedad_pct"], method="spearman")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pearson (T vs HR)", f"{pearson:.3f}")
    c2.metric("Spearman (T vs HR)", f"{spearman:.3f}")
    c3.metric("Muestras", f"{len(df):,}")
    fig = px.scatter(
        df,
        x="temperatura_c",
        y="humedad_pct",
        color_discrete_sequence=["#7b68ee"],
        labels={
            "temperatura_c": "Temperatura (°C)",
            "humedad_pct": "Humedad (%)",
        },
        title="Dispersion: temperatura vs humedad",
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


def _chart_series(df: pd.DataFrame, titulo: str) -> None:
    if df.empty:
        st.info("No hay lecturas para mostrar.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["ts_local"], y=df["temperatura_c"],
        name="Temperatura (°C)", line=dict(color="#e94560", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df["ts_local"], y=df["humedad_pct"],
        name="Humedad (%)", line=dict(color="#4a90e2", width=2), yaxis="y2",
    ))
    fig.update_layout(
        title=titulo,
        yaxis=dict(title="Temperatura (°C)", color="#e94560"),
        yaxis2=dict(title="Humedad (%)", color="#4a90e2", overlaying="y", side="right"),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)


def _clear_caches() -> None:
    load_years.clear()
    load_months.clear()
    load_days.clear()
    load_hours.clear()
    load_total.clear()
    load_filtered.clear()
    load_recent.clear()


# ── Sidebar: filtros ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"**Sesion:** {st.session_state.get('username', 'admin')}")
    if st.button("Cerrar sesion", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.pop("_auto_refresh_armed", None)
        st.session_state.pop("_suppress_auto_once", None)
        st.session_state.pop("_data_loaded", None)
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("## Segmentacion temporal")
    st.caption("Filtra por ano, uno o varios meses/dias, y hora.")

    try:
        years = load_years()
    except Exception as e:
        st.error(f"Error BD: {e}")
        st.stop()

    opt_anio = st.selectbox("Ano", ["Todos"] + [str(y) for y in years], key="filt_anio")
    f_year = int(opt_anio) if opt_anio != "Todos" else None

    months_avail = load_months(f_year)
    mes_labels = {
        "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
        "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
        "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
    }
    opt_meses = st.multiselect(
        "Mes",
        options=[f"{m:02d}" for m in months_avail],
        format_func=lambda x: mes_labels.get(x, x),
        placeholder="Todos los meses",
        key="filt_mes",
    )
    f_months = tuple(sorted(int(m) for m in opt_meses)) if opt_meses else None

    days_avail = load_days(f_year, f_months)
    opt_dias = st.multiselect(
        "Dia",
        options=[str(d) for d in days_avail],
        placeholder="Todos los dias",
        key="filt_dia",
    )
    f_days_raw = [int(d) for d in opt_dias] if opt_dias else []
    valid_days = set(days_avail)
    f_days = tuple(sorted(d for d in f_days_raw if d in valid_days)) or None

    hours_avail = load_hours(f_year, f_months, f_days)
    opt_hora = st.selectbox(
        "Hora",
        ["Todas"] + [f"{h:02d}:00" for h in hours_avail],
        key="filt_hora",
    )
    f_hour = int(opt_hora.split(":")[0]) if opt_hora != "Todas" else None

    if st.button("Limpiar filtros", use_container_width=True):
        for key in ("filt_anio", "filt_mes", "filt_dia", "filt_hora"):
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown("---")
    if st.button("Actualizar ahora", use_container_width=True, type="primary"):
        _clear_caches()
        st.session_state._last_data_refresh = datetime.now()
        st.session_state.pop("_suppress_auto_once", None)
        st.rerun()

    ultima = st.session_state.get("_last_data_refresh")
    if ultima:
        st.caption(f"Ultima actualizacion: {ultima.strftime('%d/%m/%Y %H:%M:%S')}")
    st.caption(
        f"Captura en vivo cada **{SENSOR_INTERVAL_SEC} s** (CounterFit → TimescaleDB). "
        f"Actualizacion automatica cada **{AUTO_REFRESH_SEC} s**."
    )


# ── Carga ─────────────────────────────────────────────────────────────────────

st.title("Monitoreo Ambiental IoT")

try:
    loading = not st.session_state.get("_data_loaded")
    loader = st.spinner("Cargando datos...") if loading else nullcontext()
    with loader:
        total = load_total()
        df_filt = load_filtered(f_year, f_months, f_days, f_hour)
        df_live = load_recent()
    st.session_state._data_loaded = True
    if "_last_data_refresh" not in st.session_state:
        st.session_state._last_data_refresh = datetime.now()
except Exception as e:
    st.error(f"Error de conexion: {e}")
    st.stop()

resumen_filtro = _filtro_resumen(f_year, f_months, f_days, f_hour)

st.info(
    f"**{total:,}** lecturas en BD · **{len(df_filt):,}** con filtro actual "
    f"({resumen_filtro})"
)

st.divider()

tab_vivo, tab_filt, tab_stats = st.tabs([
    "En vivo (ultimas)",
    "Datos filtrados",
    "Estadisticas",
])

with tab_vivo:
    st.caption("Ultimas 120 lecturas del sensor (sin filtros del sidebar).")
    if df_live.empty:
        st.info("Sin lecturas recientes.")
    else:
        u = df_live.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("Temperatura", f"{u['temperatura_c']:.2f} °C")
        c2.metric("Humedad", f"{u['humedad_pct']:.1f} %")
        c3.metric("Hora", u["ts_local"].strftime("%H:%M:%S"))
        _chart_series(df_live, "Ultimas lecturas CounterFit")

with tab_filt:
    st.caption(f"Mostrando lecturas individuales · {resumen_filtro}")
    if df_filt.empty:
        st.warning("Ninguna lectura coincide con los filtros. Prueba ampliar el rango.")
    else:
        u = df_filt.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ultima temp.", f"{u['temperatura_c']:.2f} °C")
        c2.metric("Ultima humedad", f"{u['humedad_pct']:.1f} %")
        c3.metric("Lecturas", f"{len(df_filt):,}")
        c4.metric("Timestamp", u["ts_local"].strftime("%d/%m %H:%M"))
        _chart_series(df_filt, f"Serie temporal · {resumen_filtro}")
        st.dataframe(
            df_filt.sort_values("ts_local", ascending=False)
            .rename(columns={
                "ts_local": "Fecha y hora",
                "temperatura_c": "Temperatura (°C)",
                "humedad_pct": "Humedad (%)",
                "fuente": "Fuente",
            }),
            use_container_width=True,
            hide_index=True,
        )

with tab_stats:
    base = df_filt if not df_filt.empty else df_live
    st.caption(f"Estadisticas · {resumen_filtro if not df_filt.empty else 'ultimas lecturas'}")
    if base.empty:
        st.info("Sin datos.")
    else:
        st.markdown("#### Correlacion y dispersion")
        _chart_correlacion(base)
        st.markdown("#### Distribucion y resumen")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                px.histogram(base, x="temperatura_c", nbins=25, color_discrete_sequence=["#e94560"]),
                use_container_width=True,
            )
        with c2:
            st.plotly_chart(
                px.histogram(base, x="humedad_pct", nbins=25, color_discrete_sequence=["#4a90e2"]),
                use_container_width=True,
            )
        st.dataframe(base[["temperatura_c", "humedad_pct"]].describe().round(2), use_container_width=True)


@st.fragment(run_every=timedelta(seconds=AUTO_REFRESH_SEC))
def _auto_refresh():
    if not st.session_state.get("_auto_refresh_armed"):
        st.session_state._auto_refresh_armed = True
        return
    if st.session_state.pop("_suppress_auto_once", False):
        return
    _clear_caches()
    st.session_state._last_data_refresh = datetime.now()
    st.session_state._suppress_auto_once = True
    st.rerun()


_auto_refresh()
