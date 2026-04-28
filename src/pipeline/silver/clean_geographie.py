import pandas as pd
import sys
import os
import unicodedata
from pathlib import Path

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

# Import relatif au dossier src
from src.utils.config import BRONZE_DIR, SILVER_DIR


def normalize_text(s):
    """Normalisation Unicode standard pour tout le projet"""
    if pd.isna(s):
        return "inconnu"
    s = str(s).lower().strip()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s.replace('-', ' ').replace('_', ' ')


def clean_quartiers():
    """Nettoyage industriel du référentiel Quartiers"""
    print("Nettoyage Quartiers (Géo) - Approche Industrielle...")
    p = BRONZE_DIR / "quartier_paris.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=';')

    # keep original column names for mapping but build a normalized map
    cols_norm = {c: normalize_text(c).replace(' ', '_') for c in df.columns}
    inv_norm = {v: k for k, v in cols_norm.items()}

    def find_col_keywords(keywords):
        for k, orig in inv_norm.items():
            if all(kw in k for kw in keywords):
                return orig
        return None

    # attempt to find useful columns
    col_ar = find_col_keywords(['c_ar']) or find_col_keywords(['arrondissement'])
    col_qu = find_col_keywords(['l_qu']) or find_col_keywords(['quartier', 'nom'])
    col_cqu = find_col_keywords(['c_qu']) or find_col_keywords(['code_quartier'])
    col_cquinsee = find_col_keywords(['c_quinsee']) or find_col_keywords(['quinsee', 'insee'])
    col_surface = find_col_keywords(['surface']) or find_col_keywords(['surf'])
    col_geometry = find_col_keywords(['geometry', 'geometry_x_y']) or find_col_keywords(['geometry', 'x', 'y'])

    # build output frame with expected column names for downstream gold
    out = pd.DataFrame()

    # arrondissement
    if col_ar:
        out['arrondissement'] = df[col_ar].astype(float).astype(int).astype(str).str.zfill(2)
    else:
        out['arrondissement'] = 'non_renseigne'

    # code_quartier id and code_insee_quartier
    if col_cqu:
        out['code_quartier_id'] = df[col_cqu].astype(float).astype(int).astype(str).str.zfill(2)
    else:
        out['code_quartier_id'] = None

    if col_cquinsee:
        out['code_insee_quartier'] = df[col_cquinsee].astype(str).str.zfill(7)
    else:
        out['code_insee_quartier'] = ('751' + out['arrondissement'].astype(str).str.zfill(2) + out['code_quartier_id'].fillna('00').astype(str))

    # quartier name
    if col_qu:
        out['nom_quartier'] = df[col_qu].astype(str).str.strip()
    else:
        out['nom_quartier'] = out['code_insee_quartier']

    # surface
    if col_surface:
        out['surface_quartier_m2'] = pd.to_numeric(df[col_surface], errors='coerce')
    else:
        out['surface_quartier_m2'] = pd.NA

    # geometry
    if col_geometry:
        out['geometry_xy'] = df[col_geometry].astype(str)
    else:
        # try other geometry-like names
        geo_candidate = next((c for c in df.columns if 'geom' in c.lower() or 'geometry' in c.lower()), None)
        out['geometry_xy'] = df[geo_candidate].astype(str) if geo_candidate else None

    out = out.fillna('non_renseigne')
    out = out.drop_duplicates()

    out_path = SILVER_DIR / "commun" / "quartiers_clean.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"-> Quartiers : {len(out)} lignes traitées.")


def clean_iris():
    """Nettoyage industriel du référentiel IRIS"""
    print("Nettoyage IRIS (Géo) - Approche Industrielle...")
    p = BRONZE_DIR / "iris.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=';')

    # build normalized map
    cols_norm = {c: normalize_text(c).replace(' ', '_') for c in df.columns}
    inv_norm = {v: k for k, v in cols_norm.items()}

    def find_col(names):
        for n in names:
            if n in inv_norm:
                return inv_norm[n]
        # try contains
        for k, orig in inv_norm.items():
            for n in names:
                if n in k:
                    return orig
        return None

    col_insee = find_col(['insee_com', 'insee', 'code_commune', 'insee_com'])
    col_code_iris = find_col(['code_iris', 'code', 'iris'])
    col_nom = find_col(['nom_iris', 'nom'])
    col_geo = find_col(['geo_point', 'geo_point_2d', 'geo', 'geometry'])
    col_geo_shape = find_col(['geo_shape', 'geometry'])

    out = pd.DataFrame()

    # INSEE_COM as expected by Gold
    if col_insee:
        out['INSEE_COM'] = df[col_insee].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)
    else:
        out['INSEE_COM'] = pd.NA

    # CODE_IRIS and NOM_IRIS
    if col_code_iris:
        out['CODE_IRIS'] = df[col_code_iris].astype(str).str.extract(r"(\d+)")[0].str.zfill(9)
    else:
        out['CODE_IRIS'] = pd.NA

    if col_nom:
        out['NOM_IRIS'] = df[col_nom].astype(str)
    else:
        out['NOM_IRIS'] = pd.NA

    # Geo Point: try to preserve original string 'lat,lon'
    if col_geo:
        # if column contains two coords separated by comma, keep as-is
        out['Geo Point'] = df[col_geo].astype(str)
    else:
        # try to build from lat/lon cols
        lat_col = find_col(['latitude', 'lat'])
        lon_col = find_col(['longitude', 'lon'])
        if lat_col and lon_col:
            out['Geo Point'] = df[lat_col].astype(str) + ',' + df[lon_col].astype(str)
        else:
            out['Geo Point'] = pd.NA

    # Geo Shape: keep the polygonal contour when present so downstream exports can build polygon GeoJSON.
    if col_geo_shape:
        out['Geo Shape'] = df[col_geo_shape].astype(str)
    else:
        geo_shape_candidate = next((c for c in df.columns if 'geo shape' in c.lower() or 'geo_shape' in c.lower()), None)
        out['Geo Shape'] = df[geo_shape_candidate].astype(str) if geo_shape_candidate else pd.NA

    out = out.drop_duplicates()
    out_path = SILVER_DIR / "commun" / "iris_clean.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"-> IRIS : {len(out)} lignes traitées.")


def clean_arrondissements():
    """Nettoyage industriel des arrondissements"""
    print("Nettoyage Arrondissements (Géo) - Approche Industrielle...")
    p = BRONZE_DIR / "arrondissements.csv"
    if not p.exists():
        return

    df = pd.read_csv(p, sep=';')
    df.columns = [normalize_text(c).replace(' ', '_') for c in df.columns]

    # Recherche de la colonne numéro d'arrondissement
    col_ar = next((c for c in df.columns if 'numero' in c and 'arrondissement' in c), None)
    if not col_ar:
        col_ar = next((c for c in df.columns if 'c_ar' in c or 'arrondissement' in c), None)

    if col_ar:
        df = df.dropna(subset=[col_ar])
        df['arrondissement'] = df[col_ar].astype(float).astype(int).astype(str).str.zfill(2)

    df = df.fillna(0)
    df = df.drop_duplicates()

    out_path = SILVER_DIR / "commun" / "arrondissements_clean.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"-> Arrondissements : {len(df)} lignes traitées.")


if __name__ == "__main__":
    clean_quartiers()
    clean_iris()
    clean_arrondissements()
