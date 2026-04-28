from pathlib import Path
import pandas as pd
import sys

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))
    
from src.utils.config import GOLD_DIR, SILVER_DIR


def load(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    return pd.read_csv(path, low_memory=False)


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').astype('Int64')
    values = values.where(~((values >= 75001) & (values <= 75020)), values - 75000)
    values = values.where((values >= 1) & (values <= 20))
    return values.astype('string').str.zfill(2)


def parse_geo_point(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    parts = series.astype(str).str.split(',', n=1, expand=True)
    lat = pd.to_numeric(parts[0], errors='coerce')
    lon = pd.to_numeric(parts[1], errors='coerce')
    return lat, lon


def minmax(series: pd.Series) -> pd.Series:
    smin = series.min()
    smax = series.max()
    if pd.isna(smin) or pd.isna(smax) or smin == smax:
        return pd.Series(0.5, index=series.index)
    return (series - smin) / (smax - smin)


def compute_kpi(dmr: pd.DataFrame, gares: pd.DataFrame, travaux: pd.DataFrame, quartiers: pd.DataFrame) -> pd.DataFrame:
    # Build quartier reference with surface shares per arrondissement
    ref = quartiers[['arrondissement', 'code_insee_quartier', 'nom_quartier', 'surface_quartier_m2', 'geometry_xy']].copy()
    ref['arrondissement'] = normalize_arrondissement(ref['arrondissement'])
    ref['code_insee_quartier'] = ref['code_insee_quartier'].astype('string').str.zfill(7)
    ref['surface_quartier_m2'] = pd.to_numeric(ref['surface_quartier_m2'], errors='coerce')

    surface_arr = (
        ref.groupby('arrondissement', as_index=False)['surface_quartier_m2']
        .sum()
        .rename(columns={'surface_quartier_m2': 'surface_arrondissement_m2'})
    )
    ref = ref.merge(surface_arr, on='arrondissement', how='left')
    ref['part_surface'] = ref['surface_quartier_m2'] / ref['surface_arrondissement_m2']

    # DMR incidents by arrondissement
    dmr_arr_col = 'arrondissement' if 'arrondissement' in dmr.columns else None
    if dmr_arr_col is None and 'code_postal' in dmr.columns:
        dmr['arrondissement'] = normalize_arrondissement(dmr['code_postal'])
        dmr_arr_col = 'arrondissement'
    if dmr_arr_col is None:
        dmr_arr = pd.DataFrame(columns=['arrondissement', 'incidents'])
    else:
        dmr['arrondissement'] = normalize_arrondissement(dmr[dmr_arr_col])
        dmr_arr = dmr.dropna(subset=['arrondissement']).groupby('arrondissement', as_index=False).size().rename(columns={'size': 'incidents'})

    # Travaux by arrondissement
    if 'arrondissement' in travaux.columns:
        travaux['arrondissement'] = normalize_arrondissement(travaux['arrondissement'])
    elif 'code_postal' in travaux.columns:
        travaux['arrondissement'] = normalize_arrondissement(travaux['code_postal'])
    else:
        travaux['arrondissement'] = pd.NA
    travaux_arr = travaux.dropna(subset=['arrondissement']).groupby('arrondissement', as_index=False).size().rename(columns={'size': 'travaux'})

    # Gares by arrondissement using nearest arrondissement centroid from quartiers
    q_geo = ref['geometry_xy'].astype(str).str.split(',', n=1, expand=True)
    ref['lat_q'] = pd.to_numeric(q_geo[0], errors='coerce')
    ref['lon_q'] = pd.to_numeric(q_geo[1], errors='coerce')
    arr_centroids = (
        ref.dropna(subset=['lat_q', 'lon_q'])
        .groupby('arrondissement', as_index=False)
        .agg(lat_c=('lat_q', 'mean'), lon_c=('lon_q', 'mean'))
    )

    if 'geo_point' in gares.columns:
        gares['lat'], gares['lon'] = parse_geo_point(gares['geo_point'])
    elif {'latitude', 'longitude'}.issubset(gares.columns):
        gares['lat'] = pd.to_numeric(gares['latitude'], errors='coerce')
        gares['lon'] = pd.to_numeric(gares['longitude'], errors='coerce')
    else:
        gares['lat'] = pd.NA
        gares['lon'] = pd.NA

    def nearest_arr(lat, lon):
        if pd.isna(lat) or pd.isna(lon) or arr_centroids.empty:
            return pd.NA
        d2 = (arr_centroids['lat_c'] - lat) ** 2 + (arr_centroids['lon_c'] - lon) ** 2
        return arr_centroids.loc[d2.idxmin(), 'arrondissement']

    gares['arrondissement'] = gares.apply(lambda r: nearest_arr(r['lat'], r['lon']), axis=1)
    gares_arr = gares.dropna(subset=['arrondissement']).groupby('arrondissement', as_index=False).size().rename(columns={'size': 'gares'})

    # Merge arrondissement indicators then project to quartiers by surface share
    arr = dmr_arr.merge(travaux_arr, on='arrondissement', how='outer').merge(gares_arr, on='arrondissement', how='outer').fillna(0)
    out = ref.merge(arr, on='arrondissement', how='left').fillna({'incidents': 0, 'travaux': 0, 'gares': 0})

    out['incidents_estime'] = (out['incidents'] * out['part_surface']).round()
    out['travaux_estime'] = (out['travaux'] * out['part_surface']).round()
    out['gares_estime'] = (out['gares'] * out['part_surface']).round()

    # Score composite (incidents = risque, gares/travaux = confort)
    out['risque_incidents_100'] = minmax(out['incidents_estime']) * 100
    out['score_gares_100'] = minmax(out['gares_estime']) * 100
    out['score_travaux_100'] = minmax(out['travaux_estime']) * 100
    out['score_confort_urbain_100'] = (
        0.5 * (100 - out['risque_incidents_100'])
        + 0.25 * out['score_gares_100']
        + 0.25 * out['score_travaux_100']
    )

    keep_cols = [
        'arrondissement', 'code_insee_quartier', 'nom_quartier',
        'surface_quartier_m2', 'part_surface',
        'incidents_estime', 'travaux_estime', 'gares_estime',
        'risque_incidents_100', 'score_confort_urbain_100',
    ]
    out = out[keep_cols].sort_values(['arrondissement', 'code_insee_quartier']).reset_index(drop=True)
    return out


def main():
    dmr = load(Path(SILVER_DIR) / 'confort' / 'dans_ma_rue_clean.csv')
    gares = load(Path(SILVER_DIR) / 'confort' / 'gares_clean.csv')
    travaux = load(Path(SILVER_DIR) / 'confort' / 'paris_se_transforme_clean.csv')
    quartiers = load(Path(SILVER_DIR) / 'commun' / 'quartiers_clean.csv')
    kpi = compute_kpi(dmr, gares, travaux, quartiers)
    out_path = Path(GOLD_DIR) / 'gold_kpi_confort_urbain.csv'
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
