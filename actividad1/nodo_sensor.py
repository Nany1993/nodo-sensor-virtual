"""
Nodo sensor virtual: CounterFit (DHT11 shim) → consola + SQLite tabla `lecturas`.

Cada lectura se escribe en la base de datos en el mismo ciclo: INSERT en `lecturas`
y commit() inmediato, para que los datos queden en disco aunque falle una lectura posterior.

En CounterFit, crear Humidity pin N y Temperature pin N+1 (por defecto 5 y 6).
Ejecutar `counterfit` en otra terminal antes de lanzar este script (--simulate omite CounterFit).

Nota: en algunas instalaciones CounterFit/eventlet falla con Python 3.13; usar Python 3.11 o 3.12
en un venv, o `--simulate` para probar el flujo archivo/consola sin simulador.
"""

import argparse
import random
import sqlite3
import sys
import time
from datetime import datetime
from typing import Callable, Optional, Tuple

CREATE_LECTURAS_SQL = """
CREATE TABLE IF NOT EXISTS lecturas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    temperatura_c   REAL NOT NULL,
    humedad_pct     REAL NOT NULL
);
"""

INSERT_SQL = "INSERT INTO lecturas (ts, temperatura_c, humedad_pct) VALUES (?, ?, ?);"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Captura periódica desde CounterFit hacia SQLite (práctica: 360 × 30 s).",
        epilog="Ejemplo: python nodo_sensor.py --samples 5 --interval-sec 15 --db nodo_sensor.db\n"
        "         python nodo_sensor.py --samples 5 --interval-sec 15 nodo_sensor.db  (ruta al final, sin --db)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--simulate",
        action="store_true",
        help="No usar CounterFit; genera valores sintéticos (pruebas de flujo)",
    )
    p.add_argument("--host", default="127.0.0.1", help="Host donde corre CounterFit")
    p.add_argument("--port", type=int, default=5000, help="Puerto HTTP de CounterFit")
    p.add_argument(
        "--dht-pin",
        type=int,
        default=5,
        help="Pin de humedad en CounterFit; temperatura debe estar en pin+1 (estándar DHT11: 5 y 6)",
    )
    p.add_argument("--interval-sec", type=int, default=30, help="Segundos entre muestras")
    p.add_argument("--samples", type=int, default=360, help="Número total de lecturas")
    p.add_argument("--db", default="nodo_sensor.db", help="Ruta del archivo SQLite")
    p.add_argument(
        "--init-db",
        action="store_true",
        help="Solo crear el archivo .db y la tabla lecturas (vacía), luego salir",
    )
    p.add_argument(
        "--no-progress",
        action="store_true",
        help="Desactiva la barra de progreso (solo líneas de texto)",
    )
    p.add_argument(
        "db_alternate",
        nargs="?",
        default=None,
        metavar="archivo.db",
        help="Opcional al final del comando: ruta del SQLite (equivalente a --db).",
    )
    ns = p.parse_args()
    if ns.db_alternate is not None:
        ns.db = ns.db_alternate
    return ns


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(CREATE_LECTURAS_SQL)
    con.commit()


def read_simulated_pair() -> Tuple[float, float]:
    """Temperatura y humedad plausibles (no conectadas a física ni CounterFit)."""
    temp_c = max(17.5, min(34.5, random.gauss(23.8, 1.8)))
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


def run_capture(reader: Callable[[], Tuple[float, float]], args: argparse.Namespace) -> None:
    con = sqlite3.connect(args.db)
    try:
        ensure_schema(con)
        print(
            f"Nodo: {args.samples} muestras, cada {args.interval_sec}s -> {args.db}",
            flush=True,
        )
        sample_range = range(1, args.samples + 1)
        pbar = None

        def log_line(msg: str) -> None:
            print(msg, flush=True)

        if not args.no_progress:
            try:
                from tqdm import tqdm

                pbar = tqdm(
                    sample_range,
                    total=args.samples,
                    desc="Captura",
                    unit="muestra",
                    dynamic_ncols=True,
                    file=sys.stdout,
                )
                log_line = tqdm.write
            except ImportError:
                pbar = None

        loop = pbar if pbar is not None else sample_range
        for i in loop:
            hum, temp = reader()
            ts = datetime.now().replace(microsecond=0).isoformat()
            con.execute(INSERT_SQL, (ts, temp, hum))
            con.commit()
            line = f"[{i}/{args.samples}] {ts}  T={temp:.2f}C  HR={hum:.2f}%"
            log_line(line)
            if pbar is not None:
                pbar.set_postfix(T=f"{temp:.1f}", HR=f"{hum:.1f}")
            if i < args.samples:
                time.sleep(args.interval_sec)
        total = con.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0]
        print(
            f"Persistencia: {total} filas en tabla lecturas (archivo {args.db}).",
            flush=True,
        )
    finally:
        con.close()


def main() -> int:
    args = parse_args()

    if args.init_db:
        con = sqlite3.connect(args.db)
        try:
            ensure_schema(con)
        finally:
            con.close()
        print(
            f"Solo init-db: {args.db} con tabla lecturas (vacia).",
            flush=True,
        )
        return 0

    if args.simulate:
        print("Modo --simulate activo (valores sintéticos, sin CounterFit).", flush=True)
        run_capture(read_simulated_pair, args)
        return 0

    from counterfit_connection import CounterFitConnection
    from counterfit_shims_seeed_python_dht import DHT

    CounterFitConnection.init(args.host, args.port)
    sensor = DHT("11", args.dht_pin)
    run_capture(lambda: read_humidity_temperature(sensor), args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        raise SystemExit(130) from None
