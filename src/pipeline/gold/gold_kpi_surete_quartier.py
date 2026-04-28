from pathlib import Path
import numpy as np
import pandas as pd
import sys

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.utils.config import GOLD_DIR, BRONZE_DIR, SILVER_DIR


def minmax(series: pd.Series) -> pd.Series:
    smin = series.min()
    smax = series.max()
    if pd.isna(smin) or pd.isna(smax) or smin == smax:
        return pd.Series(0.5, index=series.index)
    return (series - smin) / (smax - smin)


def distance_km(lat1, lon1, lat2, lon2):
    dx = (lon2 - lon1) * 111 * np.cos(np.deg2rad(lat1))
    dy = (lat2 - lat1) * 111
    return np.sqrt(dx**2 + dy**2)


def first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').astype('Int64')
    # handle both 1..20 and 75001..75020 encodings
    values = values.where(values.notna())
    values = values.where(~((values >= 75001) & (values <= 75020)), values - 75000)
    values = values.where((values >= 1) & (values <= 20))
    return values.astype('string').str.zfill(2)


def compute_from_silver() -> pd.DataFrame:
    # Load datasets from bronze
    # prefer silver cleaned sources when available
    path_delinquance = Path(SILVER_DIR) / 'surete' / 'delinquance_clean.csv'
    if not path_delinquance.exists():
        path_delinquance = BRONZE_DIR / 'dataset_delinquances.csv'

    path_cameras = Path(SILVER_DIR) / 'surete' / 'cameras_clean.csv'
    if not path_cameras.exists():
        path_cameras = BRONZE_DIR / 'points.csv'

    path_commissariats = Path(SILVER_DIR) / 'surete' / 'commissariats_clean.csv'
    if not path_commissariats.exists():
        path_commissariats = BRONZE_DIR / 'cartographie-des-emplacements-des-commissariats-a-paris-et-petite-couronne.csv'

    path_iris = Path(SILVER_DIR) / 'commun' / 'iris_clean.csv'
    if not path_iris.exists():
        path_iris = BRONZE_DIR / 'commun' / 'iris.csv'

    # read files
    if path_delinquance.suffix == '.csv' and 'delinquance_clean' in path_delinquance.name:
        df_delinq = pd.read_csv(path_delinquance, low_memory=False)
    else:
        df_delinq = pd.read_csv(path_delinquance, sep=';', decimal=',', quotechar='"', na_values=['NA'], low_memory=False)

    if path_cameras.exists() and ('cameras_clean' in str(path_cameras) or 'points.csv' in str(path_cameras)):
        df_cam = pd.read_csv(path_cameras, low_memory=False)
    else:
        df_cam = pd.read_csv(path_cameras, sep=',', low_memory=False)

    if path_commissariats.exists() and 'commissariats_clean' in str(path_commissariats):
        df_comm = pd.read_csv(path_commissariats, low_memory=False)
    else:
        df_comm = pd.read_csv(path_commissariats, sep=';', low_memory=False)

    if 'iris_clean' in path_iris.name:
        df_iris = pd.read_csv(path_iris, low_memory=False)
    else:
        df_iris = pd.read_csv(path_iris, sep=';', low_memory=False)

    # Delinquence processing
    delinq = df_delinq.copy()
    col_codgeo = first_existing_col(delinq, ['codgeo', 'CODGEO_2025', 'codgeo_2025'])
    if col_codgeo is None:
        raise ValueError('Colonne codgeo introuvable dans la délinquance (silver/bronze).')
    delinq['codgeo'] = delinq[col_codgeo].astype(str).str.extract(r'(\d+)')[0].str.zfill(5)
    delinq = delinq[delinq['codgeo'].str.startswith('751')]
    delinq['arrondissement'] = normalize_arrondissement(delinq.get('arrondissement', delinq['codgeo'].str[-2:]))
    delinq = delinq[delinq['arrondissement'].isin([f'{i:02d}' for i in range(1, 21)])]

    delinq['taux_effectif'] = pd.to_numeric(delinq.get('taux_pour_mille', pd.Series()), errors='coerce')
    delinq['taux_effectif'] = delinq['taux_effectif'].fillna(pd.to_numeric(delinq.get('complement_info_taux', pd.Series()), errors='coerce'))

    delinq['annee'] = pd.to_numeric(delinq.get('annee', pd.Series()), errors='coerce')
    delinq['indicateur'] = delinq.get('indicateur', pd.Series()).astype(str).str.strip()
    delinq = delinq.dropna(subset=['annee', 'taux_effectif'])
    delinq['annee'] = delinq['annee'].astype(int)

    pivot = delinq.pivot_table(
        index=['annee', 'arrondissement'],
        columns='indicateur',
        values='taux_effectif',
        aggfunc='mean'
    ).sort_index()

    norm = pivot.apply(minmax, axis=0)
    score_delinq = norm.mean(axis=1).mul(100).rename('score_risque_delinq_100').reset_index()
    score_delinq['score_surete_delinq_100'] = 100 - score_delinq['score_risque_delinq_100']

    # Cameras
    cam = df_cam.copy()
    cam_arr_col = next((c for c in cam.columns if str(c).upper().startswith('ARRONDISSE')), None)
    if cam_arr_col is None:
        raise ValueError('Colonne arrondissement non trouvee dans points.csv')

    cam['arrondissement'] = normalize_arrondissement(cam[cam_arr_col])
    cam = cam[cam['arrondissement'].isin([f'{i:02d}' for i in range(1, 21)])]

    arrondissements = (
        cam.groupby('arrondissement', as_index=False)
        .size()
        .rename(columns={'size': 'nb_cameras'})
    )
    arrondissements['camera_risk_100'] = (1 - minmax(arrondissements['nb_cameras'])) * 100

    # Commissariats geocoding
    comm = df_comm.copy()
    if {'latitude', 'longitude'}.issubset(comm.columns):
        comm['lat'] = pd.to_numeric(comm['latitude'], errors='coerce')
        comm['lon'] = pd.to_numeric(comm['longitude'], errors='coerce')
    else:
        geo_col = 'geo_point_2d'
        if geo_col not in comm.columns:
            raise ValueError('Colonnes latitude/longitude ou geo_point_2d introuvables dans commissariats')
        geo_comm = comm[geo_col].astype(str).str.split(',', n=1, expand=True)
        comm['lat'] = pd.to_numeric(geo_comm[0], errors='coerce')
        comm['lon'] = pd.to_numeric(geo_comm[1], errors='coerce')
    comm = comm.dropna(subset=['lat', 'lon'])

    # IRIS processing
    iris = df_iris.copy()
    if 'INSEE_COM' not in iris.columns:
        raise ValueError('Colonne INSEE_COM introuvable dans iris_clean/iris source.')
    iris['codgeo'] = iris['INSEE_COM'].astype(str).str.extract(r'(\d+)')[0].str.zfill(5)
    iris = iris[iris['codgeo'].str.startswith('751')]
    iris['arrondissement'] = normalize_arrondissement(iris['codgeo'].str[-2:])
    iris = iris[iris['arrondissement'].isin([f'{i:02d}' for i in range(1, 21)])]

    geo = iris['Geo Point'].astype(str).str.split(',', n=1, expand=True)
    iris['lat'] = pd.to_numeric(geo[0], errors='coerce')
    iris['lon'] = pd.to_numeric(geo[1], errors='coerce')
    iris = iris.dropna(subset=['lat', 'lon'])

    iris_score = iris[['CODE_IRIS', 'NOM_IRIS', 'arrondissement', 'lat', 'lon']].drop_duplicates().copy()
    iris_score = iris_score.merge(score_delinq, on='arrondissement', how='left')
    iris_score = iris_score.merge(arrondissements[['arrondissement', 'nb_cameras', 'camera_risk_100']], on='arrondissement', how='left')

    comm_lat = comm['lat'].to_numpy()
    comm_lon = comm['lon'].to_numpy()

    def nearest_commissariat(lat, lon):
        if pd.isna(lat) or pd.isna(lon) or len(comm_lat) == 0:
            return np.nan
        dist = distance_km(lat, lon, comm_lat, comm_lon)
        return dist.min()

    iris_score['dist_commissariat_km'] = iris_score.apply(lambda r: nearest_commissariat(r['lat'], r['lon']), axis=1)
    iris_score['commissariat_risk_100'] = minmax(iris_score['dist_commissariat_km']) * 100

    iris_score['score_risque_final_100'] = (0.7 * iris_score['score_risque_delinq_100'] + 0.2 * iris_score['commissariat_risk_100'] + 0.1 * iris_score['camera_risk_100'])
    iris_score['score_surete_final_100'] = 100 - iris_score['score_risque_final_100']

    # Map IRIS to quartiers
    quartiers_silver = Path(SILVER_DIR) / 'commun' / 'quartiers_clean.csv'
    if quartiers_silver.exists():
        quartiers = pd.read_csv(quartiers_silver, low_memory=False)
        quartiers = quartiers.rename(columns={'code_quartier_id': 'code_quartier'})
    else:
        quartiers_path = BRONZE_DIR / 'commun' / 'quartier_paris.csv'
        quartiers = pd.read_csv(quartiers_path, sep=';', encoding='utf-8-sig')
        quartiers = quartiers.rename(
            columns={
                'C_QU': 'code_quartier',
                'C_QUINSEE': 'code_insee_quartier',
                'L_QU': 'nom_quartier',
                'C_AR': 'arrondissement_num',
                'Geometry X Y': 'geometry_xy'
            }
        )
        quartiers['arrondissement'] = normalize_arrondissement(quartiers['arrondissement_num'])

    quartiers['code_quartier'] = pd.to_numeric(quartiers['code_quartier'], errors='coerce').astype('Int64')
    quartiers['code_insee_quartier'] = pd.to_numeric(quartiers['code_insee_quartier'], errors='coerce').astype('Int64')

    q_geo = quartiers['geometry_xy'].astype(str).str.split(',', n=1, expand=True)
    quartiers['lat_q'] = pd.to_numeric(q_geo[0], errors='coerce')
    quartiers['lon_q'] = pd.to_numeric(q_geo[1], errors='coerce')
    if 'arrondissement' not in quartiers.columns:
        quartiers['arrondissement'] = normalize_arrondissement(quartiers['arrondissement_num'])
    else:
        quartiers['arrondissement'] = normalize_arrondissement(quartiers['arrondissement'])
    quartiers = quartiers.dropna(subset=['lat_q', 'lon_q'])

    insee_by_qu = (
        quartiers.dropna(subset=['code_quartier', 'code_insee_quartier'])
        .drop_duplicates(subset=['code_quartier'])
        .set_index('code_quartier')['code_insee_quartier']
        .to_dict()
    )

    quartiers_keep = quartiers[['code_quartier', 'code_insee_quartier', 'nom_quartier', 'arrondissement', 'lat_q', 'lon_q']].drop_duplicates()

    def nearest_quartier_in_arr(row):
        subset = quartiers_keep[quartiers_keep['arrondissement'] == row['arrondissement']]
        if subset.empty:
            return pd.Series([pd.NA, pd.NA, pd.NA])
        d = distance_km(row['lat'], row['lon'], subset['lat_q'].to_numpy(), subset['lon_q'].to_numpy())
        idx = int(np.argmin(d))
        ref = subset.iloc[idx]
        return pd.Series([ref['code_quartier'], ref['code_insee_quartier'], ref['nom_quartier']])

    def join_sorted_unique(values: pd.Series) -> str:
        unique_vals = sorted({str(v).strip() for v in values.dropna() if str(v).strip()})
        return ' | '.join(unique_vals)

    iris_score[['code_quartier_ref', 'code_insee_quartier', 'nom_quartier']] = iris_score.apply(nearest_quartier_in_arr, axis=1)

    iris_score['code_quartier_ref'] = pd.to_numeric(iris_score['code_quartier_ref'], errors='coerce').astype('Int64')
    iris_score['code_insee_quartier'] = pd.to_numeric(iris_score['code_insee_quartier'], errors='coerce').astype('Int64')
    mask_invalid = ~iris_score['code_insee_quartier'].astype('string').str.startswith('75')
    iris_score.loc[mask_invalid, 'code_insee_quartier'] = iris_score.loc[mask_invalid, 'code_quartier_ref'].map(insee_by_qu)
    iris_score = iris_score.dropna(subset=['code_insee_quartier']).copy()
    iris_score['code_insee_quartier'] = iris_score['code_insee_quartier'].astype('Int64').astype(str)

    kpi_surete_quartier = (
        iris_score.groupby(['annee', 'arrondissement', 'code_insee_quartier'], as_index=False)
        .agg(
            score_surete_quartier_moyen_100=('score_surete_final_100', 'mean'),
            score_risque_quartier_moyen_100=('score_risque_final_100', 'mean'),
            score_surete_iris_min_100=('score_surete_final_100', 'min'),
            score_surete_iris_max_100=('score_surete_final_100', 'max'),
            score_surete_iris_std_100=('score_surete_final_100', 'std'),
            score_risque_iris_min_100=('score_risque_final_100', 'min'),
            score_risque_iris_max_100=('score_risque_final_100', 'max'),
            score_risque_iris_std_100=('score_risque_final_100', 'std'),
            nb_iris_rattaches=('CODE_IRIS', 'nunique'),
            codes_iris_rattaches=('CODE_IRIS', join_sorted_unique),
            noms_iris_rattaches=('NOM_IRIS', join_sorted_unique),
            dist_commissariat_km_moyenne=('dist_commissariat_km', 'mean'),
            nb_cameras_arrondissement=('nb_cameras', 'max')
        )
    )

    for c in [
        'score_surete_quartier_moyen_100', 'score_risque_quartier_moyen_100',
        'score_surete_iris_min_100', 'score_surete_iris_max_100', 'score_surete_iris_std_100',
        'score_risque_iris_min_100', 'score_risque_iris_max_100', 'score_risque_iris_std_100',
        'dist_commissariat_km_moyenne'
     ]:
        if c in kpi_surete_quartier.columns:
            kpi_surete_quartier[c] = kpi_surete_quartier[c].round(4)

    return kpi_surete_quartier


def main():
    out = Path(GOLD_DIR) / 'kpi_score_surete_quartier_estime_depuis_iris.csv'
    kpi = compute_from_silver()
    kpi.to_csv(out, index=False)
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
