#!/usr/bin/env python3
"""Docker seeder — creates MySQL schema and loads all data into MySQL + MongoDB.

Runs once at container startup. Safe to re-run (idempotent via IF NOT EXISTS + TRUNCATE).
"""

import os
import time
import csv
import json
from pathlib import Path

import mysql.connector
from pymongo import MongoClient

# ─── Config from environment ──────────────────────────────────────────────────

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB  = os.environ.get("MONGODB_DB", "urban_data")

MYSQL_HOST  = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT  = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_DB    = os.environ.get("MYSQL_DATABASE", "urban_data")
MYSQL_USER  = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS  = os.environ.get("MYSQL_PASSWORD", "")

APP_ROOT = Path(__file__).resolve().parents[3]
SQL_DIR  = APP_ROOT / "sql"
GOLD_DIR = APP_ROOT / "data" / "gold"
GEOJSON_DIR = APP_ROOT / "data" / "exports" / "nosql"

SQL_FILES = [
    "kpi_confort_urbain.sql",
    "kpi_surete_quartier.sql",
    "kpi_prix_m2_quartier_annuel.sql",
    "kpi_loyers_quartier.sql",
    "kpi_repartition_logements_sociaux.sql",
    "kpi_comparaison_achat_location.sql",
    "geo_info.sql",
    "create_iris_to_quartier_mysql.sql",
]

CSV_TO_TABLE = {
    "kpi_prix_m2_quartier_annuel.csv":                   "fact_kpi_prix_m2_quartier_annuel",
    "kpi_comparaison_achat_location_arrondissement.csv": "fact_kpi_comparaison_achat_location_arrondissement",
    "kpi_comparaison_achat_location_quartier_estime.csv":"fact_kpi_comparaison_achat_location_quartier",
    "kpi_loyers_quartier.csv":                           "fact_kpi_loyers_quartier",
    "gold_kpi_confort_urbain.csv":                       "fact_kpi_confort_quartier",
    "kpi_repartition_logements_sociaux.csv":             "fact_kpi_repartition_logements_sociaux",
    "kpi_score_surete_quartier_estime_depuis_iris.csv":  "fact_kpi_surete_quartier",
}

GEOJSON_TO_COLLECTION = {
    "iris.geojson":            "geo_iris",
    "quartiers.geojson":       "geo_quartiers",
    "commissariats.geojson":   "geo_commissariats",
    "cameras.geojson":         "geo_cameras",
    "gares.geojson":           "geo_gares",
    "arrondissements.geojson": "geo_arrondissements",
}

RELATIONAL_DIR = APP_ROOT / "data" / "exports" / "relational"


# ─── Wait helpers ─────────────────────────────────────────────────────────────

def wait_for_mysql(retries: int = 30, delay: int = 3):
    print("Waiting for MySQL...")
    for i in range(retries):
        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST, port=MYSQL_PORT,
                user=MYSQL_USER, password=MYSQL_PASS,
                database=MYSQL_DB,
            )
            conn.close()
            print("[OK] MySQL ready")
            return
        except Exception:
            print(f"  MySQL not ready ({i+1}/{retries}), retrying in {delay}s...")
            time.sleep(delay)
    raise RuntimeError("MySQL did not become ready in time")


def wait_for_mongo(retries: int = 30, delay: int = 3):
    print("Waiting for MongoDB...")
    for i in range(retries):
        try:
            MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000).admin.command("ping")
            print("[OK] MongoDB ready")
            return
        except Exception:
            print(f"  MongoDB not ready ({i+1}/{retries}), retrying in {delay}s...")
            time.sleep(delay)
    raise RuntimeError("MongoDB did not become ready in time")


# ─── MySQL schema creation ────────────────────────────────────────────────────

def run_sql_files():
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB,
    )
    cursor = conn.cursor()

    for filename in SQL_FILES:
        path = SQL_DIR / filename
        if not path.exists():
            print(f"  [SKIP] SQL file not found: {filename}")
            continue

        sql = path.read_text(encoding="utf-8")
        statements = [s.strip() for s in sql.split(";") if s.strip()]

        for stmt in statements:
            upper = stmt.upper().lstrip()
            # Skip transaction markers, comments, and LOAD DATA (handled in Python loader)
            if upper in ("BEGIN", "COMMIT"):
                continue
            if upper.startswith("--") or upper.startswith("LOAD DATA") or upper.startswith("TRUNCATE"):
                continue
            try:
                cursor.execute(stmt)
            except mysql.connector.errors.ProgrammingError as e:
                if "already exists" not in str(e).lower():
                    print(f"  [WARN] {filename}: {e}")
            except Exception as e:
                print(f"  [WARN] {filename}: {e}")

        conn.commit()
        print(f"[OK] Schema: {filename}")

    cursor.close()
    conn.close()


# ─── MySQL CSV loading ────────────────────────────────────────────────────────

def insert_csv(conn, path: Path, table: str,
               cols_override: list[str] | None = None,
               with_meta: bool = True):
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return 0

    cols = cols_override or [c for c in rows[0].keys() if c not in ("source_file", "loaded_at")]
    placeholders = ", ".join(["%s"] * len(cols))
    col_sql = ", ".join(f"`{c}`" for c in cols)

    if with_meta:
        insert_sql = (
            f"INSERT INTO `{table}` ({col_sql}, `source_file`, `loaded_at`) "
            f"VALUES ({placeholders}, %s, NOW())"
        )
    else:
        insert_sql = f"INSERT INTO `{table}` ({col_sql}) VALUES ({placeholders})"

    batch = []
    for row in rows:
        vals = [None if (v := row.get(c, "")) == "" else v for c in cols]
        if with_meta:
            vals.append(path.name)
        batch.append(tuple(vals))

    cursor = conn.cursor()
    cursor.execute(f"TRUNCATE TABLE `{table}`")
    cursor.executemany(insert_sql, batch)
    conn.commit()
    cursor.close()
    return len(batch)


def load_csv_to_mysql():
    conn = mysql.connector.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB,
        charset="utf8mb4",
        autocommit=False,
    )

    # Gold KPI tables
    for csv_name, table in CSV_TO_TABLE.items():
        path = GOLD_DIR / csv_name
        if not path.exists():
            print(f"  [SKIP] CSV not found: {csv_name}")
            continue
        count = insert_csv(conn, path, table)
        print(f"[OK] MySQL: {csv_name} → {table} ({count} rows)")

    # Relational export: iris_to_quartier
    iris_path = RELATIONAL_DIR / "iris_to_quartier.csv"
    if iris_path.exists():
        iris_cols = ["code_iris", "code_insee_quartier", "nom_quartier",
                     "insee_com", "arrondissement", "nom_iris"]
        count = insert_csv(conn, iris_path, "iris_to_quartier", cols_override=iris_cols, with_meta=False)
        print(f"[OK] MySQL: iris_to_quartier.csv → iris_to_quartier ({count} rows)")
    else:
        print(f"  [SKIP] CSV not found: iris_to_quartier.csv")

    conn.close()


# ─── MongoDB GeoJSON loading ──────────────────────────────────────────────────

def load_geojson_to_mongo():
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]

    for filename, collection_name in GEOJSON_TO_COLLECTION.items():
        path = GEOJSON_DIR / filename
        if not path.exists():
            print(f"  [SKIP] GeoJSON not found: {filename}")
            continue

        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        features = payload.get("features", []) if isinstance(payload, dict) else payload

        col = db[collection_name]
        col.drop()
        if features:
            col.insert_many(features, ordered=False)
        print(f"[OK] MongoDB: {filename} → {collection_name} ({len(features)} docs)")

    client.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("Urban Data Lake — Docker Seeder")
    print("=" * 50)

    wait_for_mysql()
    wait_for_mongo()

    print("\n--- MySQL schema ---")
    run_sql_files()

    print("\n--- MySQL data ---")
    load_csv_to_mysql()

    print("\n--- MongoDB data ---")
    load_geojson_to_mongo()

    print("\n[OK] Seeding complete.")


if __name__ == "__main__":
    main()
