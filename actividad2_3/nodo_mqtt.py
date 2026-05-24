"""
Actividad 2/3 — Transmision IoT: CounterFit (DHT11 virtual) -> SQLite + MQTT -> Adafruit IO.

Flujo por muestra:
  1. Leer temperatura y humedad (CounterFit o --simulate).
  2. Persistir en SQLite (tabla `lecturas`).
  3. Publicar en Adafruit IO via MQTT:
       - feed  <usuario>/feeds/temperatura  -> valor numerico de temperatura
       - feed  <usuario>/feeds/humedad      -> valor numerico de humedad

Credenciales en archivo .env (ver .env.example en la raiz del proyecto):
  AIO_USERNAME=<tu usuario de Adafruit IO>
  AIO_KEY=<tu AIO Key>

Uso rapido (modo simulado, sin CounterFit):
  python nodo_mqtt.py --simulate --samples 5 --interval-sec 10

Prueba oficial (3 horas, CounterFit activo en puerto 5050):
  python nodo_mqtt.py --port 5050 --interval-sec 30 --samples 360 --db nodo_mqtt.db
"""

import argparse
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from typing import Optional, Tuple

from dotenv import load_dotenv

# ── Helpers de sensor (auto-contenidos en este modulo) ────────────────────────

CREATE_LECTURAS_SQL = """
CREATE TABLE IF NOT EXISTS lecturas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,
    temperatura_c   REAL NOT NULL,
    humedad_pct     REAL NOT NULL
);
"""

INSERT_SQL = "INSERT INTO lecturas (ts, temperatura_c, humedad_pct) VALUES (?, ?, ?);"


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(CREATE_LECTURAS_SQL)
    con.commit()


def read_simulated_pair() -> Tuple[float, float]:
    """Temperatura y humedad plausibles sin CounterFit."""
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


# ── MQTT ──────────────────────────────────────────────────────────────────────

BROKER = "io.adafruit.com"
PORT_MQTT = 1883
FEED_TEMP = "{username}/feeds/temperatura"
FEED_HUM = "{username}/feeds/humedad"
KEEPALIVE = 60


def build_mqtt_client(username: str, aio_key: str):
    """Crea, configura y conecta el cliente MQTT a Adafruit IO."""
    try:
        import paho.mqtt.client as mqtt
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="nodo-iot")
        except AttributeError:
            client = mqtt.Client(client_id="nodo-iot")

        client.username_pw_set(username, aio_key)

        def on_connect(c, userdata, flags, rc, *args):
            code = rc if isinstance(rc, int) else rc.value
            if code == 0:
                print(f"MQTT conectado a {BROKER} como '{username}'", flush=True)
            else:
                print(f"MQTT error de conexion rc={code}", flush=True)

        def on_publish(c, userdata, mid, *args):
            pass

        client.on_connect = on_connect
        client.on_publish = on_publish
        client.connect(BROKER, PORT_MQTT, KEEPALIVE)
        client.loop_start()
        return client
    except Exception as exc:
        print(f"No se pudo conectar al broker MQTT: {exc}", file=sys.stderr)
        raise


def publish_reading(client, username: str, temp: float, hum: float) -> None:
    client.publish(FEED_TEMP.format(username=username), f"{temp:.2f}")
    client.publish(FEED_HUM.format(username=username), f"{hum:.2f}")


# ── Argparse ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Actividad 2/3: CounterFit -> SQLite + MQTT -> Adafruit IO.",
        epilog=(
            "Ejemplos:\n"
            "  python nodo_mqtt.py --simulate --samples 5 --interval-sec 10\n"
            "  python nodo_mqtt.py --port 5050 --interval-sec 30 --samples 360 --db nodo_mqtt.db"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--simulate", action="store_true",
                   help="Generar valores sinteticos (sin CounterFit)")
    p.add_argument("--host", default="127.0.0.1",
                   help="Host de CounterFit (ignorado con --simulate)")
    p.add_argument("--port", type=int, default=5000,
                   help="Puerto HTTP de CounterFit")
    p.add_argument("--dht-pin", type=int, default=5,
                   help="Pin de humedad en CounterFit (temperatura = pin+1)")
    p.add_argument("--interval-sec", type=int, default=30,
                   help="Segundos entre muestras")
    p.add_argument("--samples", type=int, default=360,
                   help="Numero total de lecturas")
    p.add_argument("--db", default="nodo_mqtt.db",
                   help="Ruta del archivo SQLite")
    p.add_argument("--no-progress", action="store_true",
                   help="Desactiva la barra de progreso tqdm")
    p.add_argument("--no-mqtt", action="store_true",
                   help="Solo SQLite, sin publicar en Adafruit IO")
    return p.parse_args()


# ── Bucle principal ───────────────────────────────────────────────────────────

def run(reader, args: argparse.Namespace, mqtt_client, username: str) -> None:
    con = sqlite3.connect(args.db)
    try:
        ensure_schema(con)
        mqtt_status = "deshabilitado (--no-mqtt)" if args.no_mqtt else f"Adafruit IO ({username})"
        print(
            f"Inicio: {args.samples} muestras cada {args.interval_sec}s | "
            f"SQLite: {args.db} | MQTT: {mqtt_status}",
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
                pbar = tqdm(sample_range, total=args.samples, desc="Captura+MQTT",
                            unit="muestra", dynamic_ncols=True, file=sys.stdout)
                log_fn = tqdm.write
            except ImportError:
                pbar = None

        loop = pbar if pbar is not None else sample_range
        for i in loop:
            hum, temp = reader()
            ts = datetime.now().replace(microsecond=0).isoformat()
            con.execute(INSERT_SQL, (ts, temp, hum))
            con.commit()
            if not args.no_mqtt and mqtt_client is not None:
                publish_reading(mqtt_client, username, temp, hum)
            line = (
                f"[{i}/{args.samples}] {ts}  T={temp:.2f}C  HR={hum:.2f}%  "
                f"{'-> MQTT OK' if not args.no_mqtt else ''}"
            )
            log_fn(line)
            if pbar is not None:
                pbar.set_postfix(T=f"{temp:.1f}", HR=f"{hum:.1f}")
            if i < args.samples:
                time.sleep(args.interval_sec)

        total = con.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0]
        print(f"\nTotal en tabla lecturas: {total} filas ({args.db})", flush=True)
    finally:
        con.close()
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
    args = parse_args()
    username = os.getenv("AIO_USERNAME", "")
    aio_key = os.getenv("AIO_KEY", "")
    mqtt_client = None
    if not args.no_mqtt:
        if not username or not aio_key:
            print(
                "ERROR: Faltan credenciales. Completa el archivo .env en la raiz del proyecto.\n"
                "  O usa --no-mqtt para pruebas locales.",
                file=sys.stderr,
            )
            return 1
        mqtt_client = build_mqtt_client(username, aio_key)

    if args.simulate:
        print("Modo --simulate activo (valores sinteticos, sin CounterFit).", flush=True)
        run(read_simulated_pair, args, mqtt_client, username)
        return 0

    from counterfit_connection import CounterFitConnection
    from counterfit_shims_seeed_python_dht import DHT

    CounterFitConnection.init(args.host, args.port)
    sensor = DHT("11", args.dht_pin)
    run(lambda: read_humidity_temperature(sensor), args, mqtt_client, username)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.", file=sys.stderr)
        raise SystemExit(130) from None
