"""Agrega columnas de procesamiento a lecturas_iot si faltan."""
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

STMTS = [
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS temp_movil DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS hum_movil DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS temp_norm DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS hum_norm DOUBLE PRECISION;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS valida BOOLEAN DEFAULT TRUE;",
    "ALTER TABLE lecturas_iot ADD COLUMN IF NOT EXISTS fuente TEXT DEFAULT 'counterfit';",
]

conn = psycopg2.connect(
    host=os.environ["TS_HOST"],
    port=int(os.environ.get("TS_PORT", 33711)),
    dbname=os.environ.get("TS_DB", "tsdb"),
    user=os.environ.get("TS_USER", "tsdbadmin"),
    password=os.environ["TS_PASSWORD"],
    sslmode="require",
    connect_timeout=15,
)
cur = conn.cursor()
for stmt in STMTS:
    cur.execute(stmt)
conn.commit()
cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = 'lecturas_iot' ORDER BY 1"
)
print("Columnas:", [r[0] for r in cur.fetchall()])
conn.close()
print("Migracion OK")
