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
    if kwargs.get("engine") == "python":
        kwargs.pop("low_memory", None)
    return pd.read_csv(path, **kwargs)


def extract_arrondissement(series):
    postal = to_numeric(series).astype("Int64")
    arrondissement = postal - 75000
    arrondissement = arrondissement.where((arrondissement >= 1) & (arrondissement <= 20))
    return arrondissement.astype("Int64").astype(str).str.zfill(2)


def clean_delinquance():
    """Nettoyage et standardisation de la délinquance."""
    print("Nettoyage Délinquance (Sûreté) - Approche Industrielle...")
    p = BRONZE_DIR / "dataset_delinquances.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=";", decimal=",", quotechar='"', na_values=["NA"], low_memory=False)
    df.columns = [normalize_text(col) for col in df.columns]

    col_faits = next((c for c in df.columns if c in ["nombre", "faits", "nb_faits"] or "nombre" in c), None)
    col_annee = next((c for c in df.columns if "annee" in c), None)
    col_indicateur = next((c for c in df.columns if "indicateur" in c or "libelle" in c or "index" in c), None)
    col_geo = next((c for c in df.columns if "codgeo" in c or "codgeo" in c or c.startswith("codgeo")), None)

    if col_faits:
        df["faits"] = to_numeric(df[col_faits]).fillna(0).astype("Int64")

    if col_annee:
        df["annee"] = to_numeric(df[col_annee]).astype("Int64")
    if col_indicateur:
        df["indicateur"] = df[col_indicateur].astype(str).str.strip()
    if col_geo:
        df["codgeo"] = df[col_geo].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
        df = df[df["codgeo"].str.startswith("751", na=False)]
        df["arrondissement"] = df["codgeo"].str[-2:]
        df = df[df["arrondissement"].isin([f"{i:02d}" for i in range(1, 21)])]

    if col_annee and col_indicateur:
        df = df.dropna(subset=["annee", "indicateur"])
        df["indicateur"] = df["indicateur"].astype(str).str.strip()

        if "taux_pour_mille" in df.columns:
            df["taux_pour_mille"] = to_numeric(df["taux_pour_mille"])
        if "complement_info_taux" in df.columns:
            df["complement_info_taux"] = to_numeric(df["complement_info_taux"])
        if "taux_pour_mille" in df.columns:
            df["taux_effectif"] = df["taux_pour_mille"]
            if "complement_info_taux" in df.columns:
                df["taux_effectif"] = df["taux_effectif"].fillna(df["complement_info_taux"])

    if "est_diffuse" in df.columns:
        df["est_diffuse"] = df["est_diffuse"].astype(str).str.strip()

    text_columns = df.select_dtypes(include=["object"]).columns
    for col in text_columns:
        if col not in {"indicateur", "codgeo"}:
            df[col] = df[col].fillna("non_renseigne")

    df = df.drop_duplicates()
    out = SILVER_DIR / "surete" / "delinquance_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"-> Délinquance : {len(df)} lignes traitées.")


def clean_commissariats():
    """Nettoyage et standardisation des commissariats."""
    print("Nettoyage Commissariats (Sûreté) - Approche Industrielle...")
    p = BRONZE_DIR / "cartographie-des-emplacements-des-commissariats-a-paris-et-petite-couronne.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=";", low_memory=False)
    df.columns = [normalize_text(col) for col in df.columns]

    col_geo = next((c for c in df.columns if "geo_point" in c or ("geo" in c and "point" in c)), None)
    if col_geo:
        df["latitude"], df["longitude"] = split_geo_point(df[col_geo])

    col_cp = next((c for c in df.columns if "code" in c and "postal" in c), None)
    if col_cp:
        df["code_postal"] = df[col_cp].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
        df = df[df["code_postal"].str.startswith("75", na=False)]
        df["arrondissement"] = extract_arrondissement(df["code_postal"])

    df = df.dropna(subset=["latitude", "longitude"])
    df = df.fillna("non_renseigne")
    df = df.drop_duplicates()

    out = SILVER_DIR / "surete" / "commissariats_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"-> Commissariats : {len(df)} lignes traitées.")


def clean_points_video():
    """Nettoyage et standardisation des points vidéo / caméras."""
    print("Nettoyage Vidéo (Sûreté) - Approche Industrielle...")
    p = BRONZE_DIR / "points.csv"
    if not p.exists():
        return

    df = read_if_exists(p, sep=",", low_memory=False)
    if df is None:
        return

    df.columns = [normalize_text(col) for col in df.columns]

    col_coord = next((c for c in df.columns if "coordonnees" in c or "coordonnee" in c or "geo_point" in c), None)
    if col_coord:
        df["latitude"], df["longitude"] = split_geo_point(df[col_coord])

    col_ar = next((c for c in df.columns if "arrondissement" in c), None)
    if col_ar:
        arrondissement = to_numeric(df[col_ar]).astype("Int64")
        arrondissement = arrondissement.where((arrondissement >= 1) & (arrondissement <= 20))
        df["arrondissement"] = arrondissement.astype("Int64").astype(str).str.zfill(2)

    col_cp = next((c for c in df.columns if "code" in c and "postal" in c), None)
    if col_cp:
        df["code_postal"] = df[col_cp].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)

    df = df.dropna(subset=[col for col in ["latitude", "longitude"] if col in df.columns])
    df = df.fillna("non_renseigne")
    if "arrondissement" in df.columns:
        df = df[df["arrondissement"].isin([f"{i:02d}" for i in range(1, 21)])]

    df = df.drop_duplicates()
    out = SILVER_DIR / "surete" / "cameras_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)



if __name__ == "__main__":
    clean_delinquance()
    clean_commissariats()
    clean_points_video()
