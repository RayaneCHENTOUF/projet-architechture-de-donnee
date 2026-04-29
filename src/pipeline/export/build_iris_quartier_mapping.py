#!/usr/bin/env python3
"""Build IRIS -> quartier mapping from existing cleaned geography data.

Rule used:
- Paris IRIS code (9 digits) embeds quartier code in its first 7 digits.
- code_insee_quartier = left(CODE_IRIS, 7)

Outputs:
- data/exports/relational/iris_to_quartier.csv
- sql/create_iris_to_quartier_mysql.sql
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create IRIS to quartier mapping files.")
    parser.add_argument(
        "--iris-csv",
        default="../../../data/silver/commun/iris_clean.csv",
        help="Path to iris_clean.csv",
    )
    parser.add_argument(
        "--quartiers-csv",
        default="../../../data/silver/commun/quartiers_clean.csv",
        help="Path to quartiers_clean.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/exports/relational/iris_to_quartier.csv",
        help="Output mapping CSV path",
    )
    parser.add_argument(
        "--output-sql",
        default="sql/create_iris_to_quartier_mysql.sql",
        help="Output SQL path",
    )
    return parser.parse_args()


def load_quartier_codes(quartiers_csv: Path) -> set[str]:
    codes: set[str] = set()
    with quartiers_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code_insee_quartier") or "").strip()
            if code:
                codes.add(code)
    return codes


def build_mapping_rows(iris_csv: Path, quartier_codes: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    missing = 0

    with iris_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_iris = (row.get("CODE_IRIS") or "").strip()
            insee_com = (row.get("INSEE_COM") or "").strip()

            if not code_iris:
                continue

            code_insee_quartier = code_iris[:7]
            if code_insee_quartier not in quartier_codes:
                missing += 1

            rows.append(
                {
                    "code_iris": code_iris,
                    "code_insee_quartier": code_insee_quartier,
                    "insee_com": insee_com,
                }
            )

    if missing:
        print(
            f"[WARN] {missing} row(s) reference a quartier code absent from quartiers_clean.csv"
        )

    return rows


def write_mapping_csv(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["code_iris", "code_insee_quartier", "insee_com"],
        )
        writer.writeheader()
        writer.writerows(rows)


def build_sql(output_csv: Path) -> str:
    csv_path = output_csv.resolve().as_posix()
    return f"""CREATE TABLE IF NOT EXISTS iris_to_quartier (
    code_iris VARCHAR(16) PRIMARY KEY,
    code_insee_quartier VARCHAR(16) NOT NULL,
    insee_com VARCHAR(16),
    INDEX idx_iris_to_quartier_quartier (code_insee_quartier)
);

TRUNCATE TABLE iris_to_quartier;

LOAD DATA LOCAL INFILE '{csv_path}'
INTO TABLE iris_to_quartier
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 LINES
(code_iris, code_insee_quartier, insee_com);
"""


def write_sql(output_sql: Path, sql: str) -> None:
    output_sql.parent.mkdir(parents=True, exist_ok=True)
    output_sql.write_text(sql, encoding="utf-8")


def main() -> None:
    args = parse_args()

    iris_csv = Path(args.iris_csv)
    quartiers_csv = Path(args.quartiers_csv)
    output_csv = Path(args.output_csv)
    output_sql = Path(args.output_sql)

    if not iris_csv.exists():
        raise FileNotFoundError(f"Missing file: {iris_csv}")
    if not quartiers_csv.exists():
        raise FileNotFoundError(f"Missing file: {quartiers_csv}")

    quartier_codes = load_quartier_codes(quartiers_csv)
    rows = build_mapping_rows(iris_csv, quartier_codes)
    write_mapping_csv(output_csv, rows)

    sql = build_sql(output_csv)
    write_sql(output_sql, sql)

    print(f"[OK] Mapping CSV written: {output_csv}")
    print(f"[OK] SQL file written: {output_sql}")
    print(f"[OK] Rows: {len(rows)}")


if __name__ == "__main__":
    main()
