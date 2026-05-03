"""Exporta la tabla lecturas de nodo_sensor.db a CSV (UTF-8)."""

import argparse
import csv
import sqlite3


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="nodo_sensor.db")
    p.add_argument("-o", "--output", default="lecturas.csv")
    args = p.parse_args()

    con = sqlite3.connect(args.db)
    try:
        rows = con.execute(
            "SELECT id, ts, temperatura_c, humedad_pct FROM lecturas ORDER BY id"
        ).fetchall()
    finally:
        con.close()

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "ts", "temperatura_c", "humedad_pct"])
        w.writerows(rows)

    print(f"Escritas {len(rows)} filas en {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
