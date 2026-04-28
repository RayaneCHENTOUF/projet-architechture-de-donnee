from pathlib import Path
import csv
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_DIR = PROJECT_ROOT / "data" / "gold"


REQUIRED_COLUMNS = {
    "kpi_prix_m2_arrondissement.csv": ["annee", "arrondissement", "prix_m2_median"],
    "kpi_evolution_achat_prix_m2.csv": ["annee", "arrondissement", "prix_m2_median"],
    "kpi_evolution_location_loyer.csv": ["annee", "arrondissement", "loyer_reference_median"],
    "kpi_score_surete_arrondissement_agrege_depuis_iris.csv": ["annee", "arrondissement", "score_surete_zone_moyen_100"],
    "kpi_score_surete_iris.csv": ["annee", "arrondissement", "code_iris", "score_surete_final_100"],
    "kpi_comparaison_achat_location.csv": ["arrondissement", "kpi_comparaison_achat_location_2021", "kpi_comparaison_achat_location_2025"],
    "kpi_repartition_logements_sociaux.csv": ["arrondissement"],
    "kpi_loyers.csv": ["arrondissement", "loyer_reference_median"],
    "kpi_loyer_par_arrondissement.csv": ["arrondissement", "loyer_reference_median"],
    "gold_kpi_confort_urbain.csv": ["arrondissement", "kpi_confort_urbain"],
}

# Optional aliases to support legacy files without breaking validation.
COLUMN_ALIASES = {
    "code_iris": ["CODE_IRIS"],
    "kpi_confort_urbain": ["KPI_confort_urbain"],
}


def detect_separator(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(2048)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return dialect.delimiter
    except csv.Error:
        return ","


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    def _norm(v: object) -> str:
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return s
        # Accept legacy forms like 1, 1.0, 01.
        try:
            if "." in s:
                f = float(s)
                if f.is_integer():
                    return str(int(f)).zfill(2)
            i = int(s)
            return str(i).zfill(2)
        except ValueError:
            return s

    return series.apply(_norm)


def has_column(df: pd.DataFrame, expected_col: str) -> bool:
    if expected_col in df.columns:
        return True
    aliases = COLUMN_ALIASES.get(expected_col, [])
    return any(alias in df.columns for alias in aliases)


def validate_file(file_path: Path) -> list[str]:
    errors: list[str] = []
    separator = detect_separator(file_path)
    df = pd.read_csv(file_path, sep=separator)

    expected_cols = REQUIRED_COLUMNS.get(file_path.name, [])
    for col in expected_cols:
        if not has_column(df, col):
            errors.append(f"Missing required column: {col}")

    if "arrondissement" in df.columns:
        normalized = normalize_arrondissement(df["arrondissement"])
        invalid = ~normalized.astype(str).str.match(r"^\d{2}$", na=False)
        if invalid.any():
            errors.append("arrondissement contains invalid values (expected 2-digit format)")

    if "annee" in df.columns:
        if not pd.api.types.is_numeric_dtype(df["annee"]):
            errors.append("annee is not numeric")

    if file_path.name == "kpi_prix_m2_arrondissement.csv" and "nb_ventes" in df.columns:
        errors.append("Legacy semantic name detected: nb_ventes (target standard: nb_transactions)")

    if file_path.name == "gold_kpi_confort_urbain.csv" and separator == ";":
        errors.append("Non-standard separator ';' detected (accepted temporarily)")

    return errors


def main() -> int:
    if not GOLD_DIR.exists():
        print(f"ERROR: Gold directory not found: {GOLD_DIR}")
        return 2

    csv_files = sorted(GOLD_DIR.glob("*.csv"))
    if not csv_files:
        print("ERROR: No CSV files found in data/gold")
        return 2

    has_blocking_errors = False
    print("Gold schema validation report")
    print("=" * 32)

    for file_path in csv_files:
        errors = validate_file(file_path)
        print(f"- {file_path.name}")
        if not errors:
            print("  OK")
            continue

        for err in errors:
            print(f"  WARN: {err}")
            if "Missing required column" in err or "not numeric" in err or "invalid values" in err:
                has_blocking_errors = True

    print("=" * 32)
    if has_blocking_errors:
        print("Validation finished with blocking errors.")
        return 1

    print("Validation finished (warnings only or fully OK).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
