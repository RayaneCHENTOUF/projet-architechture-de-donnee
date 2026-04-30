#!/usr/bin/env python3
"""Build IRIS -> quartier mapping from existing cleaned geography data.

Rule used:
- Paris INSEE_COM codes follow the pattern 751XX where XX = arrondissement number.
- Arrondissement is extracted from INSEE_COM: arr = INSEE_COM[-2:] (last 2 digits).
- Each IRIS is linked to ALL quartiers of its arrondissement (1-to-many).

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
        default="../../../data/exports/relational/iris_to_quartier.csv",
        help="Output mapping CSV path",
    )
    parser.add_argument(
        "--output-sql", 
        default="../../../sql/create_iris_to_quartier_mysql.sql",
        help="Output SQL path",
    )
    return parser.parse_args()


def load_quartiers_by_arrondissement(quartiers_csv: Path) -> dict[str, list[dict[str, str]]]:
    """Load quartiers grouped by arrondissement number (2-digit string like '01', '16')."""
    arr_map: dict[str, list[dict[str, str]]] = {}
    with quartiers_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            arr = (row.get("arrondissement") or "").strip()
            code_insee = (row.get("code_insee_quartier") or "").strip()
            nom = (row.get("nom_quartier") or "").strip()
            if arr and code_insee:
                arr_map.setdefault(arr, []).append({
                    "code_insee_quartier": code_insee,
                    "nom_quartier": nom,
                })
    return arr_map


def insee_com_to_arrondissement(insee_com: str) -> str:
    """Extract 2-digit arrondissement from INSEE_COM.

    Paris INSEE_COM = 751XX where XX = arrondissement (01-20).
    Examples: 75101 -> '01', 75116 -> '16', 75120 -> '20'.
    """
    if len(insee_com) == 5 and insee_com.startswith("751"):
        return insee_com[-2:]
    return ""


def build_mapping_rows(
    iris_csv: Path,
    quartiers_by_arr: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    """Build mapping rows: each IRIS is linked to all quartiers of its arrondissement."""
    rows: list[dict[str, str]] = []
    matched_iris = 0
    unmatched_iris = 0

    with iris_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_iris = (row.get("CODE_IRIS") or "").strip()
            insee_com = (row.get("INSEE_COM") or "").strip()
            nom_iris = (row.get("NOM_IRIS") or "").strip()

            if not code_iris:
                continue

            arr = insee_com_to_arrondissement(insee_com)
            quartiers = quartiers_by_arr.get(arr, [])

            if not quartiers:
                unmatched_iris += 1
                # Still add the row with arrondissement info only
                rows.append({
                    "code_iris": code_iris,
                    "code_insee_quartier": "",
                    "nom_quartier": "",
                    "insee_com": insee_com,
                    "arrondissement": arr,
                    "nom_iris": nom_iris,
                })
                continue

            matched_iris += 1
            for q in quartiers:
                rows.append({
                    "code_iris": code_iris,
                    "code_insee_quartier": q["code_insee_quartier"],
                    "nom_quartier": q["nom_quartier"],
                    "insee_com": insee_com,
                    "arrondissement": arr,
                    "nom_iris": nom_iris,
                })

    print(f"[INFO] IRIS matched to arrondissement: {matched_iris}")
    if unmatched_iris:
        print(f"[WARN] IRIS without matching arrondissement: {unmatched_iris}")

    return rows


def write_mapping_csv(output_csv: Path, rows: list[dict[str, str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "code_iris",
        "code_insee_quartier",
        "nom_quartier",
        "insee_com",
        "arrondissement",
        "nom_iris",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_sql(output_csv: Path) -> str:
    csv_path = output_csv.resolve().as_posix()
    return f"""CREATE TABLE IF NOT EXISTS iris_to_quartier (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code_iris VARCHAR(16) NOT NULL,
    code_insee_quartier VARCHAR(16) NOT NULL,
    nom_quartier VARCHAR(100),
    insee_com VARCHAR(16),
    arrondissement VARCHAR(2),
    nom_iris VARCHAR(100),
    INDEX idx_iris_code (code_iris),
    INDEX idx_quartier_code (code_insee_quartier),
    INDEX idx_arrondissement (arrondissement)
);

TRUNCATE TABLE iris_to_quartier;

LOAD DATA LOCAL INFILE '{csv_path}'
INTO TABLE iris_to_quartier
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\\n'
IGNORE 1 LINES
(code_iris, code_insee_quartier, nom_quartier, insee_com, arrondissement, nom_iris);
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

    quartiers_by_arr = load_quartiers_by_arrondissement(quartiers_csv)
    print(f"[INFO] Loaded {sum(len(v) for v in quartiers_by_arr.values())} quartiers across {len(quartiers_by_arr)} arrondissements")

    rows = build_mapping_rows(iris_csv, quartiers_by_arr)
    write_mapping_csv(output_csv, rows)

    sql = build_sql(output_csv)
    write_sql(output_sql, sql)

    print(f"[OK] Mapping CSV written: {output_csv}")
    print(f"[OK] SQL file written: {output_sql}")
    print(f"[OK] Rows: {len(rows)}")


if __name__ == "__main__":
    main()
