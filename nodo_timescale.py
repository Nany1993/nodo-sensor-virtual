"""
Actividad 4 — Almacenamiento IoT en TimescaleDB Cloud (Tiger Cloud).

Flujo independiente de las actividades anteriores:
  CounterFit (DHT11 virtual) o --simulate
      → nodo_timescale.py
          → TimescaleDB Cloud  (hypertable lecturas_iot)

Credenciales en .env:
  TS_HOST, TS_PORT, TS_DB, TS_USER, TS_PASSWORD

Uso rápido (simulado):
  python nodo_timescale.py --simulate --samples 20 --interval-sec 5

Prueba con CounterFit (3 horas):
  python nodo_timescale.py --interval-sec 30 --samples 360
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from nodo_sensor import read_humidity_temperature, read_simulated_pair

import psycopg2
from psycopg2.extras import execute_values

# ── SQL ───────────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS lecturas_iot (
    ts              TIMESTAMPTZ NOT NULL,
    temperatura_c   DOUBLE PRECISION NOT NULL,
    humedad_pct     DOUBLE PRECISION NOT NULL,
    fuente          TEXT DEFAULT 'counterfit'
);
"""

HYPERTABLE_SQL = """
SELECT create_hypertable('lecturas_iot', 'ts', if_not_exists => TRUE);
"""

INSERT_SQL = """
INSERT INTO lecturas_iot (ts, temperatura_c, humedad_pct, fuente)
VALUES (%s, %s, %s, %s);
"""


# ── Conexión ──────────────────────────────────────────────────────────────────

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
        try:
            cur.execute(HYPERTABLE_SQL)
        except Exception:
            pass  # ya existe como hypertable
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_lecturas_iot_ts ON lecturas_iot (ts DESC);"
        )
    conn.commit()


# ── Argparse ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Nodo IoT Actividad 4: CounterFit → TimescaleDB Cloud.",
        epilog=(
            "Ejemplos:\n"
            "  python nodo_timescale.py --simulate --samples 20 --interval-sec 5\n"
            "  python nodo_timescale.py --interval-sec 30 --samples 360"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--simulate", action="store_true",
                   help="Generar valores sintéticos sin CounterFit")
    p.add_argument("--host", default="127.0.0.1",
                   help="Host de CounterFit (ignorado con --simulate)")
    p.add_argument("--port", type=int, default=5000,
                   help="Puerto HTTP de CounterFit")
    p.add_argument("--dht-pin", type=int, default=5,
                   help="Pin de humedad en CounterFit")
    p.add_argument("--interval-sec", type=int, default=30,
                   help="Segundos entre muestras")
    p.add_argument("--samples", type=int, default=360,
                   help="Número total de lecturas")
    p.add_argument("--no-progress", action="store_true",
                   help="Desactiva la barra tqdm")
    return p.parse_args()


# ── Bucle principal ───────────────────────────────────────────────────────────

def run(reader, args: argparse.Namespace, conn) -> None:
    fuente = "simulate" if args.simulate else "counterfit"

    print(
        f"Inicio Actividad 4: {args.samples} muestras cada {args.interval_sec}s"
        f" -> TimescaleDB Cloud (lecturas_iot) | fuente={fuente}",
        flush=True,
    )

    sample_range = range(1, args.samples + 1)
    pbar = None

    def log(msg: str) -> None:
        print(msg, flush=True)

    log_fn = log
    if not args.no_progress:
        try:
            from tqdm import tqdm
            pbar = tqdm(
                sample_range,
                total=args.samples,
                desc="IoT→TimescaleDB",
                unit="muestra",
                dynamic_ncols=True,
                file=sys.stdout,
            )
            log_fn = tqdm.write
        except ImportError:
            pbar = None

    loop = pbar if pbar is not None else sample_range

    with conn.cursor() as cur:
        for i in loop:
            hum, temp = reader()
            ts = datetime.now(tz=timezone.utc)

            cur.execute(INSERT_SQL, (ts, temp, hum, fuente))
            conn.commit()

            line = (
                f"[{i}/{args.samples}] {ts.strftime('%Y-%m-%dT%H:%M:%SZ')}  "
                f"T={temp:.2f}C  HR={hum:.2f}%  -> TimescaleDB OK"
            )
            log_fn(line)
            if pbar is not None:
                pbar.set_postfix(T=f"{temp:.1f}", HR=f"{hum:.1f}")

            if i < args.samples:
                time.sleep(args.interval_sec)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM lecturas_iot;")
        total = cur.fetchone()[0]

    print(f"\nTotal acumulado en lecturas_iot: {total} filas.", flush=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    load_dotenv()
    args = parse_args()

    for var in ("TS_HOST", "TS_PASSWORD"):
        if not os.environ.get(var):
            print(
                f"ERROR: variable {var} no encontrada. Completa el archivo .env",
                file=sys.stderr,
            )
            return 1

    print("Conectando a TimescaleDB Cloud...", flush=True)
    conn = get_connection()
    ensure_schema(conn)
    print("Esquema verificado.", flush=True)

    if args.simulate:
        print("Modo --simulate activo (valores sintéticos).", flush=True)
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
