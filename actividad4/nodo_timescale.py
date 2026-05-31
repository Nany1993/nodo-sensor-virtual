"""
Actividad 4 — Almacenamiento IoT en TimescaleDB Cloud (Tiger Cloud).

Pipeline de datos (cada ciclo de captura):
  1. CAPTURA        CounterFit (DHT11 virtual) o --simulate
  2. PREPROCESAMIENTO  validacion de rangos; descarta anomalias
  3. FILTRADO          anti-duplicados por marca de tiempo minima
  4. TRANSFORMACION    promedio movil (ventana 5) + normalizacion min-max
  5. ALMACENAMIENTO    INSERT con datos crudos Y procesados en una sola fila

Credenciales en .env (raiz del proyecto):
  TS_HOST, TS_PORT, TS_DB, TS_USER, TS_PASSWORD

Uso rapido (simulado, sin CounterFit):
  python nodo_timescale.py --simulate --samples 20 --interval-sec 5

Con CounterFit activo en puerto 5050 (3 horas):
  python nodo_timescale.py --port 5050 --interval-sec 30 --samples 360
"""

import argparse
import os
import random
import sys
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
import psycopg2

# ── Helpers de sensor (auto-contenidos) ───────────────────────────────────────

def read_simulated_pair() -> Tuple[float, float]:
    """Temperatura y humedad plausibles sin CounterFit."""
    temp_c  = max(17.5, min(34.5, random.gauss(23.8, 1.8)))
    hum_pct = max(34.0, min(93.0, random.gauss(59.5, 5.5)))
    return round(hum_pct, 2), round(temp_c, 2)


def read_humidity_temperature(sensor, retries: int = 5) -> Tuple[float, float]:
    last_err: Optional[Exception] = None
    for _ in range(retries):
        try:
            hum, temp = sensor.read()
            return float(hum), float(temp)
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"Lectura DHT virtual fallida tras {retries} intentos") from last_err


# ── Rangos validos del sensor DHT11 virtual (CounterFit) ──────────────────────

TEMP_MIN, TEMP_MAX = 17.0, 36.0   # °C
HUM_MIN,  HUM_MAX  = 33.0, 94.0   # %
VENTANA_MA         = 5             # muestras para el promedio movil


# ── Procesamiento en linea ─────────────────────────────────────────────────────

class Procesador:
    """
    Aplica preprocesamiento, filtrado y transformacion a cada lectura
    antes de que sea almacenada en TimescaleDB.
    """

    def __init__(self, ventana: int = VENTANA_MA):
        self._ventana   = ventana
        self._temps     = deque(maxlen=ventana)   # historial para promedio movil
        self._hums      = deque(maxlen=ventana)
        self._temp_min  = float("inf")            # running min/max para normalizacion
        self._temp_max  = float("-inf")
        self._hum_min   = float("inf")
        self._hum_max   = float("-inf")
        self._descartadas = 0
        self._ultimo_ts: Optional[datetime] = None

    # 1) Preprocesamiento ------------------------------------------------------
    def _validar(self, temp: float, hum: float) -> bool:
        """Devuelve True si la lectura esta dentro del rango operacional."""
        return (TEMP_MIN <= temp <= TEMP_MAX) and (HUM_MIN <= hum <= HUM_MAX)

    # 2) Filtrado --------------------------------------------------------------
    def _es_duplicado(self, ts: datetime, intervalo_min_s: int = 5) -> bool:
        """Descarta lecturas que lleguen demasiado rapido (< intervalo_min_s)."""
        if self._ultimo_ts is None:
            return False
        delta = (ts - self._ultimo_ts).total_seconds()
        return delta < intervalo_min_s

    # 3) Transformacion --------------------------------------------------------
    def _actualizar_historico(self, temp: float, hum: float) -> None:
        self._temps.append(temp)
        self._hums.append(hum)
        if temp < self._temp_min: self._temp_min = temp
        if temp > self._temp_max: self._temp_max = temp
        if hum  < self._hum_min:  self._hum_min  = hum
        if hum  > self._hum_max:  self._hum_max  = hum

    def _promedio_movil(self) -> Tuple[float, float]:
        return (
            round(sum(self._temps) / len(self._temps), 4),
            round(sum(self._hums)  / len(self._hums),  4),
        )

    def _normalizar(self, temp: float, hum: float) -> Tuple[float, float]:
        t_rng = self._temp_max - self._temp_min
        h_rng = self._hum_max  - self._hum_min
        t_norm = round((temp - self._temp_min) / t_rng, 4) if t_rng > 0 else 0.0
        h_norm = round((hum  - self._hum_min)  / h_rng, 4) if h_rng > 0 else 0.0
        return t_norm, h_norm

    # Pipeline completo --------------------------------------------------------
    def procesar(
        self, temp: float, hum: float, ts: datetime, intervalo_min_s: int = 5
    ) -> Optional[dict]:
        """
        Ejecuta el pipeline completo.
        Devuelve un dict con todos los campos listos para INSERT,
        o None si la lectura debe descartarse.
        """
        # Preprocesamiento: validacion de rango
        valida = self._validar(temp, hum)
        if not valida:
            self._descartadas += 1
            return None

        # Filtrado: anti-duplicados
        if self._es_duplicado(ts, intervalo_min_s):
            return None

        # Transformacion: actualizar historico y calcular
        self._actualizar_historico(temp, hum)
        temp_ma, hum_ma   = self._promedio_movil()
        temp_norm, hum_norm = self._normalizar(temp, hum)

        self._ultimo_ts = ts

        return {
            "ts":           ts,
            "temperatura_c": temp,
            "humedad_pct":   hum,
            "temp_movil":    temp_ma,
            "hum_movil":     hum_ma,
            "temp_norm":     temp_norm,
            "hum_norm":      hum_norm,
            "valida":        True,
        }

    @property
    def descartadas(self) -> int:
        return self._descartadas


# ── SQL ───────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lecturas_iot (
    ts              TIMESTAMPTZ      NOT NULL,
    temperatura_c   DOUBLE PRECISION NOT NULL,
    humedad_pct     DOUBLE PRECISION NOT NULL,
    temp_movil      DOUBLE PRECISION,
    hum_movil       DOUBLE PRECISION,
    temp_norm       DOUBLE PRECISION,
    hum_norm        DOUBLE PRECISION,
    valida          BOOLEAN          DEFAULT TRUE,
    fuente          TEXT             DEFAULT 'counterfit'
);
"""

# Columnas nuevas — se agregan si la tabla ya existia sin ellas
ALTER_COLUMNS_SQL = [
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS temp_movil DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS hum_movil  DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS temp_norm  DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS hum_norm   DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS valida      BOOLEAN DEFAULT TRUE;",
]

HYPERTABLE_SQL = "SELECT create_hypertable('lecturas_iot', 'ts', if_not_exists => TRUE);"

INSERT_SQL = """
INSERT INTO lecturas_iot
    (ts, temperatura_c, humedad_pct, temp_movil, hum_movil, temp_norm, hum_norm, valida, fuente)
VALUES
    (%(ts)s, %(temperatura_c)s, %(humedad_pct)s,
     %(temp_movil)s, %(hum_movil)s, %(temp_norm)s, %(hum_norm)s,
     %(valida)s, %(fuente)s);
"""


# ── Conexion ──────────────────────────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["TS_HOST"],
        port=int(os.environ.get("TS_PORT", 33711)),
        dbname=os.environ.get("TS_DB", "tsdb"),
        user=os.environ.get("TS_USER", "tsdbadmin"),
        password=os.environ["TS_PASSWORD"],
        sslmode="require",
        connect_timeout=15,
    )


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        cur.execute(CREATE_TABLE_SQL)
        for stmt in ALTER_COLUMNS_SQL:
            cur.execute(stmt)
        try:
            cur.execute(HYPERTABLE_SQL)
        except Exception:
            pass
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_lecturas_iot_ts ON lecturas_iot (ts DESC);"
        )
    conn.commit()


# ── Argparse ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Actividad 4: CounterFit -> Preprocesamiento/Filtrado/Transformacion -> TimescaleDB Cloud.",
        epilog=(
            "Ejemplos:\n"
            "  python nodo_timescale.py --simulate --samples 20 --interval-sec 5\n"
            "  python nodo_timescale.py --port 5050 --interval-sec 10 --samples 360"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--simulate", action="store_true",
                   help="Generar valores sinteticos sin CounterFit")
    p.add_argument("--host", default="127.0.0.1",
                   help="Host de CounterFit (ignorado con --simulate)")
    p.add_argument("--port", type=int, default=5000,
                   help="Puerto HTTP de CounterFit")
    p.add_argument("--dht-pin", type=int, default=5,
                   help="Pin de humedad en CounterFit")
    p.add_argument("--interval-sec", type=int, default=5,
                   help="Segundos entre muestras")
    p.add_argument("--samples", type=int, default=1440,
                   help="Numero total de lecturas intentadas (1440 = 2 h cada 5 s)")
    p.add_argument("--no-progress", action="store_true",
                   help="Desactiva la barra tqdm")
    return p.parse_args()


# ── Bucle principal ───────────────────────────────────────────────────────────

def run(reader, args: argparse.Namespace, conn) -> None:
    fuente     = "simulate" if args.simulate else "counterfit"
    procesador = Procesador(ventana=VENTANA_MA)
    insertadas = 0

    print(
        f"\nInicio Actividad 4 | {args.samples} lecturas cada {args.interval_sec}s"
        f" | fuente={fuente} | ventana_MA={VENTANA_MA}"
        f"\nPipeline: CAPTURA -> PREPROCESAMIENTO -> FILTRADO -> TRANSFORMACION -> TimescaleDB\n",
        flush=True,
    )

    sample_range = range(1, args.samples + 1)
    pbar     = None
    log_fn   = lambda msg: print(msg, flush=True)

    if not args.no_progress:
        try:
            from tqdm import tqdm
            pbar   = tqdm(sample_range, total=args.samples, desc="Pipeline IoT",
                          unit="lectura", dynamic_ncols=True, file=sys.stdout)
            log_fn = tqdm.write
        except ImportError:
            pbar = None

    loop = pbar if pbar is not None else sample_range

    with conn.cursor() as cur:
        for i in loop:
            hum, temp = reader()
            ts = datetime.now(tz=timezone.utc)

            # ── Pipeline de procesamiento ─────────────────────────────────────
            fila = procesador.procesar(temp, hum, ts, intervalo_min_s=max(1, args.interval_sec - 5))

            if fila is None:
                log_fn(
                    f"[{i}/{args.samples}] {ts.strftime('%H:%M:%S')}  "
                    f"T={temp:.2f}C HR={hum:.2f}%  DESCARTADA (fuera de rango)"
                )
                if i < args.samples:
                    time.sleep(args.interval_sec)
                continue

            fila["fuente"] = fuente

            # ── INSERT en TimescaleDB ─────────────────────────────────────────
            cur.execute(INSERT_SQL, fila)
            conn.commit()
            insertadas += 1

            log_fn(
                f"[{i}/{args.samples}] {ts.strftime('%Y-%m-%dT%H:%M:%SZ')}  "
                f"T={temp:.2f}C  HR={hum:.2f}%  "
                f"MA=({fila['temp_movil']:.2f}C,{fila['hum_movil']:.2f}%)  "
                f"norm=({fila['temp_norm']:.3f},{fila['hum_norm']:.3f})  "
                f"-> OK"
            )
            if pbar is not None:
                pbar.set_postfix(T=f"{temp:.1f}", MA=f"{fila['temp_movil']:.1f}")

            if i < args.samples:
                time.sleep(args.interval_sec)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM lecturas_iot;")
        total = cur.fetchone()[0]

    print(
        f"\n--- Resumen del pipeline ---"
        f"\n  Lecturas intentadas : {args.samples}"
        f"\n  Insertadas en BD    : {insertadas}"
        f"\n  Descartadas         : {procesador.descartadas}"
        f"\n  Total acumulado     : {total} filas en lecturas_iot",
        flush=True,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
    args = parse_args()

    for var in ("TS_HOST", "TS_PASSWORD"):
        if not os.environ.get(var):
            print(
                f"ERROR: variable {var} no encontrada en .env",
                file=sys.stderr,
            )
            return 1

    print("Conectando a TimescaleDB Cloud...", flush=True)
    conn = get_connection()
    ensure_schema(conn)
    print("Esquema verificado (columnas de procesamiento presentes).", flush=True)

    if args.simulate:
        print("Modo --simulate activo (valores sinteticos).", flush=True)
        run(read_simulated_pair, args, conn)
        conn.close()
        return 0

    from counterfit_connection import CounterFitConnection
    from counterfit_shims_seeed_python_dht import DHT

    CounterFitConnection.init(args.host, args.port)
    sensor = DHT("11", args.dht_pin)
    run(lambda: read_humidity_temperature(sensor), args, conn)
    conn.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        raise SystemExit(130) from None
