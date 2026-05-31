"""
Inserta ~1000 lecturas ficticias repartidas en mayo de 2026 (TimescaleDB).
Uso: python actividad4/sembrar_datos_mayo.py
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

N = 1000
MAYO_INICIO = datetime(2026, 5, 1, 6, 0, 0, tzinfo=timezone.utc)
MAYO_FIN = datetime(2026, 5, 31, 22, 0, 0, tzinfo=timezone.utc)
FUENTE = "semilla_mayo"

INSERT = """
INSERT INTO lecturas_iot
    (ts, temperatura_c, humedad_pct, temp_movil, hum_movil, temp_norm, hum_norm, valida, fuente)
VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s);
"""


def _conn():
    return psycopg2.connect(
        host=os.environ["TS_HOST"],
        port=int(os.environ.get("TS_PORT", 33711)),
        dbname=os.environ.get("TS_DB", "tsdb"),
        user=os.environ.get("TS_USER", "tsdbadmin"),
        password=os.environ["TS_PASSWORD"],
        sslmode="require",
        connect_timeout=15,
    )


def main() -> None:
    rng = random.Random(202605)
    span = int((MAYO_FIN - MAYO_INICIO).total_seconds())
    rows = []

    for _ in range(N):
        ts = MAYO_INICIO + timedelta(seconds=rng.randint(0, span))
        # Variacion diurna simple
        hora = ts.hour + ts.minute / 60
        temp = 20 + 6 * abs((hora - 14) / 12) + rng.gauss(0, 1.2)
        hum = 68 - 12 * abs((hora - 14) / 12) + rng.gauss(0, 2.5)
        temp = round(max(17.0, min(35.0, temp)), 2)
        hum = round(max(35.0, min(92.0, hum)), 2)
        rows.append((ts, temp, hum, temp, hum, 0.5, 0.5, FUENTE))

    rows.sort(key=lambda r: r[0])

    conn = _conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM lecturas_iot WHERE fuente = %s;", (FUENTE,))
    cur.executemany(INSERT, rows)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM lecturas_iot WHERE fuente = %s;", (FUENTE,))
    n = cur.fetchone()[0]
    conn.close()
    print(f"Sembradas {n} lecturas ficticias de mayo 2026 (fuente={FUENTE}).")


if __name__ == "__main__":
    main()
