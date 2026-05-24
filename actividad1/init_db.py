"""
Crea el archivo SQLite y la tabla `lecturas` (vacía) antes de la primera corrida.

Uso: python init_db.py [--db nodo_sensor.db]
"""

import argparse
import sqlite3
import sys

from nodo_sensor import CREATE_LECTURAS_SQL


def main() -> int:
    p = argparse.ArgumentParser(description="Crea la BD y la tabla lecturas (sin datos).")
    p.add_argument("--db", default="nodo_sensor.db", help="Ruta del archivo .db a crear")
    args = p.parse_args()

    con = sqlite3.connect(args.db)
    try:
        con.executescript(CREATE_LECTURAS_SQL)
        con.commit()
    finally:
        con.close()

    print(f"Base de datos lista: {args.db} (tabla lecturas creada o ya existente).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
