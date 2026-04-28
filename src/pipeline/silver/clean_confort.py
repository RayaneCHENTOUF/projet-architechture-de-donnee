import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.utils.config import BRONZE_DIR, SILVER_DIR


def normalize_text(value):
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def to_numeric(series):
    cleaned = (
        series.astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def split_geo_point(series):
    geo = series.astype(str).str.split(",", n=1, expand=True)
    lat = pd.to_numeric(geo[0], errors="coerce")
    lon = pd.to_numeric(geo[1], errors="coerce")
    return lat, lon


def read_if_exists(path, **kwargs):
    if not path.exists():
        return None
    return pd.read_csv(path, **kwargs)


def clean_dans_ma_rue():
    """Nettoyage et catégorisation de Dans Ma Rue."""
    print("Nettoyage Dans Ma Rue (Confort) - Approche Industrielle...")
    p = BRONZE_DIR / "dans-ma-rue.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=";", low_memory=False)
    df.columns = [normalize_text(col) for col in df.columns]

    if "date_du_signalement" in df.columns:
        df["date_du_signalement"] = pd.to_datetime(df["date_du_signalement"], errors="coerce")
        df = df.dropna(subset=["date_du_signalement"])
        df["annee"] = df["date_du_signalement"].dt.year.astype("Int64")

    if "etat" in df.columns:
        df["etat"] = df["etat"].astype(str).str.strip()
        etat_norm = df["etat"].map(normalize_text)
        df = df[~etat_norm.isin(["annule", "non_fonde", "nonfonde"])]

    if "geo_point_2d" in df.columns:
        df["latitude"], df["longitude"] = split_geo_point(df["geo_point_2d"])

    if "code_postal" in df.columns:
        df["code_postal"] = df["code_postal"].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
        df["arrondissement"] = df["code_postal"].str[-2:]
        df = df[df["arrondissement"].isin([f"{i:02d}" for i in range(1, 21)])]

    def categorize_signalement(row):
        text = " ".join(
            [str(row.get("type_objet", "")), str(row.get("sous_type_objet", ""))]
        )
        text = normalize_text(text)
        if any(token in text for token in ["proprete", "dechet", "ordure", "salissure", "epanchement"]):
            return "proprete"
        if any(token in text for token in ["incivilite", "tag", "graffiti", "affichage", "bruit"]):
            return "incivilite"
        if any(token in text for token in ["voirie", "trou", "potelet", "chaussee", "trottoir"]):
            return "voirie"
        if any(token in text for token in ["eclairage", "lampe", "feu"]):
            return "eclairage"
        return "autre"

    if any(col in df.columns for col in ["type_objet", "sous_type_objet"]):
        df["categorie_signalement"] = df.apply(categorize_signalement, axis=1)

    if "conseil_de_quartier" in df.columns:
        df["nom_cq_norm"] = df["conseil_de_quartier"].apply(normalize_text)

    text_columns = df.select_dtypes(include=["object"]).columns
    for col in text_columns:
        df[col] = df[col].fillna("non_renseigne")

    df = df.drop_duplicates()
    out = SILVER_DIR / "confort" / "dans_ma_rue_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"-> Dans Ma Rue : {len(df)} lignes traitées.")


def clean_gares():
    """Nettoyage et standardisation des gares."""
    print("Nettoyage Gares (Confort) - Approche Industrielle...")
    p = BRONZE_DIR / "emplacement-des-gares-idf.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=";", low_memory=False)
    df.columns = [normalize_text(col) for col in df.columns]

    if "geo_point_2d" in df.columns:
        df["latitude"], df["longitude"] = split_geo_point(df["geo_point_2d"])

    col_name = next((c for c in df.columns if "nom_gare" in c or "nom_long" in c), None)
    col_cp = next((c for c in df.columns if "code_postal" in c), None)
    if col_name:
        df["nom_gare"] = df[col_name].astype(str).str.strip()

    if col_cp:
        df["code_postal"] = df[col_cp].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
        df = df[df["code_postal"].str.startswith("75", na=False)]
        df["arrondissement"] = df["code_postal"].str[-2:]

    if "latitude" in df.columns and "longitude" in df.columns:
        df = df.dropna(subset=["latitude", "longitude"])

    text_columns = df.select_dtypes(include=["object"]).columns
    for col in text_columns:
        df[col] = df[col].fillna("non_renseigne")

    df = df.drop_duplicates()
    out = SILVER_DIR / "confort" / "gares_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"-> Gares : {len(df)} lignes traitées.")


def clean_paris_se_transforme():
    """Nettoyage et standardisation de Paris se transforme."""
    print("Nettoyage Chantiers (Confort) - Approche Industrielle...")
    p = BRONZE_DIR / "parissetransforme.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=";", low_memory=False)
    df.columns = [normalize_text(col) for col in df.columns]

    title_col = next((c for c in df.columns if "titre_operation" in c or "titre" in c), None)
    if title_col:
        df["titre_operation"] = df[title_col].astype(str).str.strip()

    date_columns = [col for col in df.columns if any(token in col for token in ["date", "debut", "fin"])]
    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    if any(col in df.columns for col in date_columns):
        first_date = date_columns[0]
        df["annee"] = df[first_date].dt.year.astype("Int64")

    category_col = next((c for c in df.columns if any(token in c for token in ["categorie", "type_operation", "typologie"])), None)
    if category_col:
        df["categorie_operation"] = df[category_col].astype(str).str.strip()
        df["categorie_operation_norm"] = df["categorie_operation"].map(normalize_text)

    arrondissement_col = next((c for c in df.columns if "arrondissement" in c), None)
    if arrondissement_col:
        arrondissement = to_numeric(df[arrondissement_col]).astype("Int64")
        arrondissement = arrondissement.where((arrondissement >= 1) & (arrondissement <= 20))
        df["arrondissement"] = arrondissement.astype("Int64").astype(str).str.zfill(2)

    if "titre_operation" in df.columns:
        df = df.dropna(subset=["titre_operation"])

    text_columns = df.select_dtypes(include=["object"]).columns
    for col in text_columns:
        df[col] = df[col].fillna("non_renseigne")

    df = df.drop_duplicates()
    out = SILVER_DIR  / "confort" / "paris_se_transforme_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

  


if __name__ == "__main__":
    clean_dans_ma_rue()
    clean_gares()
    clean_paris_se_transforme()
