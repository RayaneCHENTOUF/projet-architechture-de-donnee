from pathlib import Path
import pandas as pd
import sys

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.utils.config import GOLD_DIR, BRONZE_DIR, SILVER_DIR


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').astype('Int64')
    values = values.where((values >= 1) & (values <= 20))
    return values.astype('string').str.zfill(2)


def compute_from_silver() -> pd.DataFrame:
    # Reuse arrondissement base from bronze sources and project to quartiers
    from src.pipeline.gold.gold_kpi_comparaison_achat_location_arrondissement import compute_from_silver as _arr_base

    kpi_base = _arr_base()
    kpi_base['arrondissement'] = normalize_arrondissement(kpi_base['arrondissement'])
    # load quartiers reference
    quartiers_path = Path(SILVER_DIR) / 'commun' / 'quartiers_clean.csv'
    if not quartiers_path.exists():
        quartiers_path = BRONZE_DIR / 'commun' / 'quartier_paris.csv'
        quartiers = pd.read_csv(quartiers_path, sep=';', encoding='utf-8-sig', low_memory=False)
        quartiers = quartiers.rename(
            columns={
                'C_QUINSEE': 'code_insee_quartier',
                'L_QU': 'nom_quartier',
                'C_AR': 'arrondissement_num',
                'SURFACE': 'surface_quartier_m2',
                'Geometry X Y': 'geometry_xy'
            }
        )
        quartiers['arrondissement'] = pd.to_numeric(quartiers['arrondissement_num'], errors='coerce').astype('Int64')
        quartiers['arrondissement'] = quartiers['arrondissement'].astype(int).astype(str).str.zfill(2)
        quartiers['surface_quartier_m2'] = pd.to_numeric(quartiers['surface_quartier_m2'], errors='coerce')
    else:
        quartiers = pd.read_csv(quartiers_path, low_memory=False)

    quartiers['arrondissement'] = normalize_arrondissement(quartiers['arrondissement'])
    quartiers['surface_quartier_m2'] = pd.to_numeric(quartiers['surface_quartier_m2'], errors='coerce')
    quartiers['code_insee_quartier'] = quartiers['code_insee_quartier'].astype('string')
    quartiers = quartiers.dropna(subset=['arrondissement'])

    surface_arr = (
        quartiers.groupby('arrondissement', as_index=False)['surface_quartier_m2']
        .sum()
        .rename(columns={'surface_quartier_m2': 'surface_arrondissement_m2'})
    )
    quartiers = quartiers.merge(surface_arr, on='arrondissement', how='left')
    quartiers['part_surface'] = quartiers['surface_quartier_m2'] / quartiers['surface_arrondissement_m2']

    kpi_quartier_annuel = (
        kpi_base.merge(
            quartiers[['code_insee_quartier', 'arrondissement', 'surface_quartier_m2', 'part_surface']],
            on='arrondissement',
            how='left'
        )
    ).sort_values(['annee', 'arrondissement', 'code_insee_quartier']).reset_index(drop=True)

    kpi_quartier_annuel['nb_transactions_estime'] = (
        kpi_quartier_annuel['nb_transactions'] * kpi_quartier_annuel['part_surface']
    ).round().astype('Int64')
    kpi_quartier_annuel['nb_observations_estime'] = (
        kpi_quartier_annuel['nb_observations'] * kpi_quartier_annuel['part_surface']
    ).round().astype('Int64')

    # keep columns consistent with notebook
    kpi_quartier_annuel = kpi_quartier_annuel[
        [
            'annee', 'arrondissement', 'code_insee_quartier',
            'prix_m2_median', 'prix_m2_moyen', 'nb_transactions',
            'loyer_reference_median', 'loyer_reference_moyen', 'nb_observations',
            'kpi_comparaison_achat_location',
            'surface_quartier_m2', 'part_surface',
            'nb_transactions_estime', 'nb_observations_estime'
        ]
    ]

    return kpi_quartier_annuel


def main():
    out_path = Path(GOLD_DIR) / 'kpi_comparaison_achat_location_quartier_estime.csv'
    kpi = compute_from_silver()
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
