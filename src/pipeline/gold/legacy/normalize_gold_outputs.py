from pathlib import Path
import csv

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def detect_separator(file_path: Path) -> str:
    sample = file_path.read_text(encoding="utf-8")[:2048]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        return ","


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    def _norm(v: object) -> str:
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return s
        try:
            if "." in s:
                f = float(s)
                if f.is_integer():
                    return str(int(f)).zfill(2)
            return str(int(s)).zfill(2)
        except ValueError:
            return s

    return series.apply(_norm)


def normalize_file(file_path: Path) -> tuple[bool, str]:
    sep = detect_separator(file_path)
    df = pd.read_csv(file_path, sep=sep)

    rename_map: dict[str, str] = {}

    if file_path.name == "gold_kpi_confort_urbain.csv":
        rename_map.update(
            {
                "S1_proprete": "s1_proprete",
                "S2_incivilites": "s2_incivilites",
                "S3_amenagement": "s3_amenagement",
                "S4_accessibilite": "s4_accessibilite",
                "S5_transport": "s5_transport",
                "KPI_confort_urbain": "kpi_confort_urbain",
            }
        )

    if file_path.name == "kpi_prix_m2_arrondissement.csv" and "nb_ventes" in df.columns:
        rename_map["nb_ventes"] = "nb_transactions"

    if file_path.name == "kpi_score_surete_iris.csv":
        rename_map.update({"CODE_IRIS": "code_iris", "NOM_IRIS": "nom_iris"})

    if rename_map:
        df = df.rename(columns=rename_map)

    if "arrondissement" in df.columns:
        df["arrondissement"] = normalize_arrondissement(df["arrondissement"])

    # Write all Gold files with the project target separator.
    df.to_csv(file_path, index=False)

    return True, f"normalized (sep:{sep} -> ',')"


def main() -> int:
    csv_files = sorted(GOLD_DIR.glob("*.csv"))
    if not csv_files:
        print("No CSV files found in data/gold")
        return 1

    print("Gold normalization report")
    print("=" * 28)
    for file_path in csv_files:
        ok, msg = normalize_file(file_path)
        status = "OK" if ok else "FAIL"
        print(f"- {file_path.name}: {status} - {msg}")

    print("=" * 28)
    print("Normalization finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
