from pathlib import Path
import re
import unicodedata
import pandas as pd
import numpy as np
import sys

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.utils.config import GOLD_DIR, BRONZE_DIR, SILVER_DIR


def normalize_text(text: str) -> str:
    text = str(text).strip().lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


def pick_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
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


def to_numeric(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.replace('\xa0', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    return pd.to_numeric(cleaned, errors='coerce')


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').astype('Int64')
    values = values.where((values >= 1) & (values <= 20))
    return values.astype('string').str.zfill(2)


def distance_km(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111 * np.cos(np.deg2rad(lat1))
    dy = (lat2 - lat1) * 111
    return np.sqrt(dx ** 2 + dy ** 2)


def compute_from_silver() -> pd.DataFrame:
    # Prefer silver HLM if present
    path_silver = Path(SILVER_DIR) / 'immobilier' / 'hlm_clean.csv'
    if path_silver.exists():
        df = pd.read_csv(path_silver, low_memory=False)
    else:
        path = BRONZE_DIR / 'immobilier' / 'hlm.csv'
        df = pd.read_csv(path, sep=';', low_memory=False)
    col_arr = pick_column(df, ['arrondissement', 'arr'])
    col_year = pick_column(df, ['annee', 'annee_financement'])
    col_lat = pick_column(df, ['latitude', 'lat'])
    col_lon = pick_column(df, ['longitude', 'lon'])
    col_log_fin = pick_column(df, ['nombre total de logements finances', 'nombre_total_de_logements_finances', 'nb_logements_finances', 'nb_logements'])
    col_pla_i = pick_column(df, ['nb_pla_i'])
    col_plus = pick_column(df, ['nb_plus'])
    col_plus_cd = pick_column(df, ['nb_plus_cd'])
    col_pls = pick_column(df, ['nb_pls'])
    col_bailleur = pick_column(df, ['bailleur_social', 'bailleur'])

    if col_log_fin:
        df[col_log_fin] = to_numeric(df[col_log_fin])
    if col_pla_i:
        df[col_pla_i] = to_numeric(df[col_pla_i])
    if col_plus:
        df[col_plus] = to_numeric(df[col_plus])
    if col_plus_cd:
        df[col_plus_cd] = to_numeric(df[col_plus_cd])
    if col_pls:
        df[col_pls] = to_numeric(df[col_pls])
    if col_year:
        df[col_year] = to_numeric(df[col_year]).astype('Int64')
    if col_lat:
        df[col_lat] = to_numeric(df[col_lat])
    if col_lon:
        df[col_lon] = to_numeric(df[col_lon])

    if col_arr:
        df[col_arr] = normalize_arrondissement(df[col_arr])

    if not all([col_arr, col_log_fin]):
        return pd.DataFrame()

    # Enrich with nearest quartier using quartiers_clean geometry when possible.
    quartiers_path = Path(SILVER_DIR) / 'commun' / 'quartiers_clean.csv'
    if quartiers_path.exists() and col_lat and col_lon:
        quartiers = pd.read_csv(quartiers_path, low_memory=False)
        if {'arrondissement', 'code_insee_quartier', 'nom_quartier', 'geometry_xy'}.issubset(quartiers.columns):
            quartiers['arrondissement'] = normalize_arrondissement(quartiers['arrondissement'])
            geo = quartiers['geometry_xy'].astype(str).str.split(',', n=1, expand=True)
            quartiers['lat_q'] = pd.to_numeric(geo[0], errors='coerce')
            quartiers['lon_q'] = pd.to_numeric(geo[1], errors='coerce')
            quartiers = quartiers.dropna(subset=['arrondissement', 'lat_q', 'lon_q', 'code_insee_quartier'])

            def nearest_quartier(row):
                if pd.isna(row[col_lat]) or pd.isna(row[col_lon]) or pd.isna(row[col_arr]):
                    return pd.Series([pd.NA, pd.NA])
                subset = quartiers[quartiers['arrondissement'] == row[col_arr]]
                if subset.empty:
                    return pd.Series([pd.NA, pd.NA])
                d = distance_km(row[col_lat], row[col_lon], subset['lat_q'].to_numpy(), subset['lon_q'].to_numpy())
                idx = int(np.argmin(d))
                ref = subset.iloc[idx]
                return pd.Series([str(ref['code_insee_quartier']), str(ref['nom_quartier'])])

            df[['code_insee_quartier', 'nom_quartier']] = df.apply(nearest_quartier, axis=1)

    group_cols = [col_arr]
    if col_year:
        group_cols.append(col_year)
    if 'code_insee_quartier' in df.columns:
        group_cols.append('code_insee_quartier')
    if 'nom_quartier' in df.columns:
        group_cols.append('nom_quartier')

    df_grp = df.dropna(subset=[col_arr, col_log_fin]).copy()

    aggregations = {
        'logements_finances_total': (col_log_fin, 'sum'),
        'logements_finances_moyen': (col_log_fin, 'mean'),
        'nb_programmes': (col_log_fin, 'size'),
    }
    if col_bailleur:
        aggregations['nb_bailleurs'] = (col_bailleur, 'nunique')
    if col_pla_i:
        aggregations['nb_pla_i_total'] = (col_pla_i, 'sum')
    if col_plus:
        aggregations['nb_plus_total'] = (col_plus, 'sum')
    if col_plus_cd:
        aggregations['nb_plus_cd_total'] = (col_plus_cd, 'sum')
    if col_pls:
        aggregations['nb_pls_total'] = (col_pls, 'sum')
    if col_lat:
        aggregations['latitude_moyenne'] = (col_lat, 'mean')
    if col_lon:
        aggregations['longitude_moyenne'] = (col_lon, 'mean')

    rename_map = {col_arr: 'arrondissement'}
    if col_year:
        rename_map[col_year] = 'annee'

    hlm_kpi = (
        df_grp.groupby(group_cols, as_index=False)
        .agg(**aggregations)
        .rename(columns=rename_map)
    )

    sort_cols = [c for c in ['annee', 'arrondissement', 'code_insee_quartier', 'nom_quartier'] if c in hlm_kpi.columns]
    if sort_cols:
        hlm_kpi = hlm_kpi.sort_values(sort_cols)
    if 'logements_finances_moyen' in hlm_kpi.columns:
        hlm_kpi['logements_finances_moyen'] = hlm_kpi['logements_finances_moyen'].round(2)
    if 'latitude_moyenne' in hlm_kpi.columns:
        hlm_kpi['latitude_moyenne'] = hlm_kpi['latitude_moyenne'].round(6)
    if 'longitude_moyenne' in hlm_kpi.columns:
        hlm_kpi['longitude_moyenne'] = hlm_kpi['longitude_moyenne'].round(6)
    return hlm_kpi


def main():
    out_path = Path(GOLD_DIR) / 'kpi_repartition_logements_sociaux.csv'
    kpi = compute_from_silver()
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
