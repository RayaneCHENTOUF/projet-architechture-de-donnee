#!/usr/bin/env python3
"""Load KPI Gold CSV files into MySQL tables.

This script assumes KPI tables already exist (created from sql/kpi_*.sql).

Usage examples:
python src/pipeline/export/load_kpi_csv_to_mysql.py --truncate
python src/pipeline/export/load_kpi_csv_to_mysql.py --database urban_data --user root
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import mysql.connector


CSV_TO_TABLE = {
    "kpi_prix_m2_quartier_annuel.csv": "fact_kpi_prix_m2_quartier_annuel",
    "kpi_comparaison_achat_location_arrondissement.csv": "fact_kpi_comparaison_achat_location_arrondissement",
    "kpi_comparaison_achat_location_quartier_estime.csv": "fact_kpi_comparaison_achat_location_quartier",
    "kpi_loyers_quartier.csv": "fact_kpi_loyers_quartier",
    "gold_kpi_confort_urbain.csv": "fact_kpi_confort_quartier",
    "kpi_repartition_logements_sociaux.csv": "fact_kpi_repartition_logements_sociaux",
    "kpi_score_surete_quartier_estime_depuis_iris.csv": "fact_kpi_surete_quartier",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load KPI CSV files into MySQL.")
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--database", default=os.getenv("MYSQL_DATABASE", "urban_data"))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD", "dbl2025"))
    parser.add_argument(
        "--gold-dir",
        default="../../../data/gold",
        help="Directory that contains KPI CSV files.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate each target table before loading.",
    )
    return parser.parse_args()


def get_headers(csv_path: Path) -> list[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        headers = next(reader)
    return [h.strip() for h in headers]


def load_one_csv(conn, csv_path: Path, table_name: str, truncate: bool) -> int:
    headers = get_headers(csv_path)

    load_columns = [h for h in headers if h not in {"source_file", "loaded_at"}]
    if not load_columns:
        raise ValueError(f"No columns detected in {csv_path}")

    column_sql = ", ".join(f"`{c}`" for c in load_columns)
    local_path = csv_path.resolve().as_posix()
    source_name = csv_path.name.replace("'", "''")

    with conn.cursor() as cur:
        if truncate:
            cur.execute(f"TRUNCATE TABLE `{table_name}`")

        escaped_path = local_path.replace("'", "''")
        field_clause = "FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' "
        line_clause = "LINES TERMINATED BY '\\n' "

        sql = (
            f"LOAD DATA LOCAL INFILE '{escaped_path}' "
            f"INTO TABLE `{table_name}` "
            "CHARACTER SET utf8mb4 "
            f"{field_clause}"
            f"{line_clause}"
            "IGNORE 1 LINES "
            f"({column_sql}) "
            f"SET `source_file`='{source_name}', `loaded_at`=NOW()"
        )
        cur.execute(sql)
        loaded = cur.rowcount

    conn.commit()
    return max(loaded, 0)


def main() -> None:
    args = parse_args()

    gold_dir = Path(args.gold_dir)
    if not gold_dir.exists():
        raise FileNotFoundError(f"Gold directory not found: {gold_dir}")

    conn = mysql.connector.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        charset="utf8mb4",
        autocommit=False,
        use_pure=True,
        allow_local_infile=True,
    )

    total = 0
    try:
        for csv_name, table_name in CSV_TO_TABLE.items():
            csv_path = gold_dir / csv_name
            if not csv_path.exists():
                print(f"[SKIP] Missing file: {csv_path}")
                continue

            loaded = load_one_csv(conn, csv_path, table_name, args.truncate)
            total += loaded
            print(f"[OK] {csv_name} -> {table_name}: {loaded} row(s)")
    finally:
        conn.close()

    print(f"Done. Loaded {total} row(s) into '{args.database}'.")


if __name__ == "__main__":
    main()
