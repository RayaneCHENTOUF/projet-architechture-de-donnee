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


def pick_column(df, candidates):
    normalized_map = {normalize_text(col): col for col in df.columns}
    for candidate in candidates:
        key = normalize_text(candidate)
        if key in normalized_map:
            return normalized_map[key]
    for candidate in candidates:
        key = normalize_text(candidate)
        for normalized_col, original_col in normalized_map.items():
            if key in normalized_col:
                return original_col
    return None


def to_numeric(series):
    cleaned = (
        series.astype(str)
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_postal_code(series):
    extracted = series.astype(str).str.extract(r"(\d+)")[0]
    return extracted.str.zfill(5)


def split_geo_point(series):
    geo = series.astype(str).str.split(",", n=1, expand=True)
    lat = pd.to_numeric(geo[0], errors="coerce")
    lon = pd.to_numeric(geo[1], errors="coerce")
    return lat, lon


def load_csv_if_exists(path, **kwargs):
    if not path.exists():
        return None
    if kwargs.get("engine") == "python":
        kwargs.pop("low_memory", None)
    return pd.read_csv(path, **kwargs)


def clean_dvf():
    """Nettoyage et standardisation de la base DVF."""
    print("Nettoyage DVF (Immo) - Approche Industrielle...")
    sources = [BRONZE_DIR / "75.csv", BRONZE_DIR / "valeurs_foncieres.csv"]
    frames = []

    for source in sources:
        df = load_csv_if_exists(source, sep=",", low_memory=False)
        if df is None:
            continue

        df.columns = [normalize_text(col) for col in df.columns]

        rename_map = {}
        for source_name in [
            "date_mutation",
            "valeur_fonciere",
            "surface_reelle_bati",
            "code_postal",
            "type_local",
            "id_mutation",
            "nature_mutation",
            "code_commune",
            "nom_commune",
            "adresse_numero",
            "adresse_nom_voie",
            "nombre_pieces_principales",
            "longitude",
            "latitude",
        ]:
            col = pick_column(df, [source_name])
            if col is not None:
                rename_map[col] = source_name

        df = df.rename(columns=rename_map)

        required = ["date_mutation", "valeur_fonciere", "surface_reelle_bati", "code_postal", "type_local"]
        available_required = [col for col in required if col in df.columns]
        if len(available_required) < len(required):
            missing = sorted(set(required) - set(available_required))
            raise ValueError(f"Colonnes DVF manquantes dans {source.name}: {missing}")

        keep_columns = [
            "id_mutation",
            "date_mutation",
            "nature_mutation",
            "valeur_fonciere",
            "adresse_numero",
            "adresse_nom_voie",
            "code_postal",
            "code_commune",
            "nom_commune",
            "type_local",
            "surface_reelle_bati",
            "nombre_pieces_principales",
            "longitude",
            "latitude",
        ]
        df = df[[col for col in keep_columns if col in df.columns]].copy()

        df = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati", "date_mutation", "code_postal"])
        df["date_mutation"] = pd.to_datetime(df["date_mutation"], errors="coerce")
        df = df.dropna(subset=["date_mutation"])

        df["valeur_fonciere"] = to_numeric(df["valeur_fonciere"])
        df["surface_reelle_bati"] = to_numeric(df["surface_reelle_bati"])
        if "nombre_pieces_principales" in df.columns:
            df["nombre_pieces_principales"] = to_numeric(df["nombre_pieces_principales"])
        if "longitude" in df.columns:
            df["longitude"] = to_numeric(df["longitude"])
        if "latitude" in df.columns:
            df["latitude"] = to_numeric(df["latitude"])

        df = df.dropna(subset=["valeur_fonciere", "surface_reelle_bati"])
        df = df[(df["surface_reelle_bati"] > 9) & (df["valeur_fonciere"] > 10000)]

        df["code_postal"] = parse_postal_code(df["code_postal"])
        df = df[df["code_postal"].str.startswith("75", na=False)]
        df["arrondissement"] = df["code_postal"].str[-2:]
        df = df[df["arrondissement"].isin([f"{i:02d}" for i in range(1, 21)])]

        if "type_local" in df.columns:
            df["type_local"] = df["type_local"].astype(str).str.strip()
            df = df[df["type_local"].map(normalize_text).isin(["appartement", "maison"])]

        df = df[df["surface_reelle_bati"] < 500]
        df["prix_m2"] = df["valeur_fonciere"] / df["surface_reelle_bati"]
        q_low, q_high = df["prix_m2"].quantile([0.01, 0.99])
        if pd.notna(q_low) and pd.notna(q_high):
            df = df[(df["prix_m2"] >= q_low) & (df["prix_m2"] <= q_high)]

        df["annee"] = df["date_mutation"].dt.year.astype("Int64")
        df = df.drop_duplicates()
        frames.append(df)

    if not frames:
        print("-> DVF : aucun fichier trouvé.")
        return

    final = pd.concat(frames, ignore_index=True).drop_duplicates()
    final = final.sort_values(["annee", "arrondissement", "date_mutation"]).reset_index(drop=True)

    out = SILVER_DIR / "immobilier" / "dvf_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out, index=False)
    print(f"-> DVF : {len(final)} lignes traitées.")


def clean_hlm():
    """Nettoyage et standardisation du jeu HLM / logements sociaux."""
    print("Nettoyage HLM (Immo) - Approche Industrielle...")
    sources = [BRONZE_DIR / "hlm.csv", BRONZE_DIR / "logements-sociaux-finances-a-paris.csv"]
    frames = []

    for source in sources:
        df = load_csv_if_exists(source, sep=";", low_memory=False)
        if df is None:
            continue

        df.columns = [normalize_text(col) for col in df.columns]

        rename_pairs = {
            "identifiant_livraison": "identifiant_livraison",
            "adresse_du_programme": "adresse_du_programme",
            "code_postal": "code_postal",
            "ville": "ville",
            "annee_du_financement_agrement": "annee_financement",
            "bailleur_social": "bailleur_social",
            "nombre_total_de_logements_finances": "nb_logements_finances",
            "dont_nombre_de_logements_pla_i": "nb_pla_i",
            "dont_nombre_de_logements_plus": "nb_plus",
            "dont_nombre_de_logements_plus_cd": "nb_plus_cd",
            "dont_nombre_de_logements_pls": "nb_pls",
            "mode_de_realisation": "mode_de_realisation",
            "commentaires": "commentaires",
            "arrondissement": "arrondissement_source",
            "nature_de_programme": "nature_de_programme",
            "coordonnee_en_x_l93": "x_l93",
            "coordonnee_en_y_l93": "y_l93",
            "geo_shape": "geo_shape",
            "geo_point_2d": "geo_point_2d",
        }

        actual_rename = {}
        for source_name, target_name in rename_pairs.items():
            col = pick_column(df, [source_name])
            if col is not None:
                actual_rename[col] = target_name

        df = df.rename(columns=actual_rename)

        if "geo_point_2d" in df.columns:
            df["latitude"], df["longitude"] = split_geo_point(df["geo_point_2d"])

        for col in ["code_postal", "annee_financement", "nb_logements_finances", "nb_pla_i", "nb_plus", "nb_plus_cd", "nb_pls", "x_l93", "y_l93", "latitude", "longitude"]:
            if col in df.columns:
                df[col] = to_numeric(df[col])

        if "code_postal" in df.columns:
            df["code_postal"] = df["code_postal"].astype("Int64").astype(str).str.zfill(5)
            df = df[df["code_postal"].str.startswith("75", na=False)]

        if "arrondissement_source" in df.columns:
            arrondissement = to_numeric(df["arrondissement_source"]).astype("Int64").astype(str).str.zfill(2)
            df["arrondissement"] = arrondissement
        elif "code_postal" in df.columns:
            df["arrondissement"] = df["code_postal"].str[-2:]

        df = df[df["arrondissement"].isin([f"{i:02d}" for i in range(1, 21)])]

        if "annee_financement" in df.columns:
            df["annee_financement"] = df["annee_financement"].astype("Int64")
            df["annee"] = df["annee_financement"]

        if "nb_logements_finances" in df.columns:
            df["nb_logements_finances"] = df["nb_logements_finances"].fillna(0).astype("Int64")
        for col in ["nb_pla_i", "nb_plus", "nb_plus_cd", "nb_pls"]:
            if col in df.columns:
                df[col] = df[col].fillna(0).astype("Int64")

        if "mode_de_realisation" in df.columns:
            df["mode_de_realisation"] = df["mode_de_realisation"].astype(str).str.strip()
            mode_norm = df["mode_de_realisation"].map(normalize_text)

            def encode_mode(value):
                if "neuve" in value or "construction_neuve" in value:
                    return 0
                if "rehabilitation" in value:
                    return 1
                if "conventionnement" in value:
                    return 2
                return pd.NA

            df["mode_de_realisation_code"] = mode_norm.apply(encode_mode).astype("Int64")

        if "nature_de_programme" in df.columns:
            df["nature_de_programme"] = df["nature_de_programme"].astype(str).str.strip()
            df["nature_de_programme_norm"] = df["nature_de_programme"].map(normalize_text)

        if "adresse_du_programme" in df.columns:
            df["adresse_du_programme"] = df["adresse_du_programme"].astype(str).str.strip()
        if "bailleur_social" in df.columns:
            df["bailleur_social"] = df["bailleur_social"].astype(str).str.strip()

        df = df.drop(columns=[col for col in ["commentaires", "ville"] if col in df.columns])
        df = df.dropna(subset=[col for col in ["arrondissement", "nb_logements_finances"] if col in df.columns])
        df = df.fillna("non_renseigne")
        df = df.drop_duplicates()
        frames.append(df)

    if not frames:
        print("-> HLM : aucun fichier trouvé.")
        return

    final = pd.concat(frames, ignore_index=True).drop_duplicates()
    sort_columns = [col for col in ["arrondissement", "annee_financement"] if col in final.columns]
    if sort_columns:
        final = final.sort_values(sort_columns).reset_index(drop=True)

    out = SILVER_DIR / "immobilier" / "hlm_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out, index=False)
    print(f"-> HLM : {len(final)} lignes traitées.")


def clean_loyers():
    """Nettoyage et standardisation du jeu loyers de référence."""
    print("Nettoyage Loyers (Immo) - Approche Industrielle...")
    sources = [BRONZE_DIR / "loyers.csv" ]
    frames = []

    for source in sources:
        df = load_csv_if_exists(source, sep=";", encoding="utf-8-sig", low_memory=False)
        if df is None:
            continue

        df.columns = [normalize_text(col) for col in df.columns]

        rename_pairs = {
            "annee": "annee",
            "secteurs_geographiques": "secteurs_geographiques",
            "numero_du_quartier": "numero_quartier",
            "nom_du_quartier": "nom_quartier",
            "nombre_de_pieces_principales": "nombre_pieces_principales",
            "epoque_de_construction": "epoque_construction",
            "type_de_location": "type_location",
            "loyers_de_reference": "loyer_reference",
            "loyers_de_reference_majores": "loyer_reference_majore",
            "loyers_de_reference_minores": "loyer_reference_minore",
            "ville": "ville",
            "numero_insee_du_quartier": "code_insee_quartier",
            "geo_shape": "geo_shape",
            "geo_point_2d": "geo_point_2d",
        }

        actual_rename = {}
        for source_name, target_name in rename_pairs.items():
            col = pick_column(df, [source_name])
            if col is not None:
                actual_rename[col] = target_name

        df = df.rename(columns=actual_rename)

        if "geo_point_2d" in df.columns:
            df["latitude"], df["longitude"] = split_geo_point(df["geo_point_2d"])

        numeric_columns = [
            "annee",
            "numero_quartier",
            "nombre_pieces_principales",
            "loyer_reference",
            "loyer_reference_majore",
            "loyer_reference_minore",
            "code_insee_quartier",
            "latitude",
            "longitude",
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = to_numeric(df[col])

        if "annee" in df.columns:
            df["annee"] = df["annee"].astype("Int64")

        if "type_location" in df.columns:
            df["type_location"] = df["type_location"].astype(str).str.strip()
            type_norm = df["type_location"].map(normalize_text)
            df["type_location_code"] = type_norm.map(lambda value: 1 if value == "meuble" else 0 if value == "non_meuble" else pd.NA).astype("Int64")

        if "epoque_construction" in df.columns:
            df["epoque_construction"] = df["epoque_construction"].astype(str).str.strip()
            df["epoque_construction_norm"] = df["epoque_construction"].map(normalize_text)

        if "secteurs_geographiques" in df.columns:
            secteurs = to_numeric(df["secteurs_geographiques"])
            secteurs = secteurs.where((secteurs >= 1) & (secteurs <= 20))
            df["arrondissement"] = secteurs.astype("Int64").astype(str).str.zfill(2)

        if ("arrondissement" not in df.columns) or df["arrondissement"].isna().all():
            if "code_insee_quartier" in df.columns:
                code_insee = df["code_insee_quartier"].astype("Int64").astype(str).str.zfill(7)
                df["arrondissement"] = code_insee.str[3:5]

        if "code_insee_quartier" in df.columns:
            df["code_insee_quartier"] = df["code_insee_quartier"].astype("Int64").astype(str).str.zfill(7)

        if "arrondissement" in df.columns:
            df = df[df["arrondissement"].isin([f"{i:02d}" for i in range(1, 21)])]

        critical_columns = [col for col in ["annee", "loyer_reference", "arrondissement"] if col in df.columns]
        df = df.dropna(subset=critical_columns)

        if "loyer_reference_majore" in df.columns:
            df["loyer_reference_majore"] = pd.to_numeric(df["loyer_reference_majore"], errors="coerce")
        if "loyer_reference_minore" in df.columns:
            df["loyer_reference_minore"] = pd.to_numeric(df["loyer_reference_minore"], errors="coerce")

        df = df.fillna("non_renseigne")

        keep_columns = [
            "annee",
            "arrondissement",
            "secteurs_geographiques",
            "numero_quartier",
            "nom_quartier",
            "nombre_pieces_principales",
            "epoque_construction",
            "epoque_construction_norm",
            "type_location",
            "type_location_code",
            "loyer_reference",
            "loyer_reference_majore",
            "loyer_reference_minore",
            "code_insee_quartier",
            "geo_shape",
            "geo_point_2d",
            "latitude",
            "longitude",
        ]
        df = df[[col for col in keep_columns if col in df.columns]].copy()
        df = df.drop_duplicates()
        frames.append(df)

    if not frames:
        print("-> Loyers : aucun fichier trouvé.")
        return

    final = pd.concat(frames, ignore_index=True).drop_duplicates()
    sort_columns = [col for col in ["annee", "arrondissement", "numero_quartier"] if col in final.columns]
    if sort_columns:
        final = final.sort_values(sort_columns).reset_index(drop=True)

    out = SILVER_DIR / "immobilier" / "encadrement_loyers_clean.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out, index=False)
    print(f"-> Loyers : {len(final)} lignes traitées.")


if __name__ == "__main__":
    clean_dvf()
    clean_hlm()
    clean_loyers()
