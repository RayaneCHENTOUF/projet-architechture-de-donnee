from pathlib import Path
import pandas as pd
import sys

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.utils.config import GOLD_DIR, SILVER_DIR, BRONZE_DIR


def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_csv(path: Path, **kwargs) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    return pd.read_csv(path, **kwargs)


def load_dvf_source(csv_file: Path) -> pd.DataFrame:
    use_cols_dvf = [
        'date_mutation',
        'valeur_fonciere',
        'surface_reelle_bati',
        'code_postal',
        'type_local',
    ]
    df_src = load_csv(csv_file, usecols=use_cols_dvf, parse_dates=['date_mutation'], low_memory=False)
    df_src = df_src.dropna(subset=['valeur_fonciere', 'surface_reelle_bati', 'date_mutation', 'code_postal'])
    df_src = df_src[df_src['surface_reelle_bati'] > 9]
    df_src = df_src[df_src['valeur_fonciere'] > 10000]
    df_src = df_src[df_src['type_local'].isin(['Appartement', 'Maison'])]
    df_src['code_postal'] = df_src['code_postal'].astype(int).astype(str).str.zfill(5)
    df_src = df_src[df_src['code_postal'].str.startswith('75')]
    df_src['prix_m2'] = df_src['valeur_fonciere'] / df_src['surface_reelle_bati']
    q_low = df_src['prix_m2'].quantile(0.01)
    q_high = df_src['prix_m2'].quantile(0.99)
    df_src = df_src[(df_src['prix_m2'] >= q_low) & (df_src['prix_m2'] <= q_high)]
    df_src['annee'] = df_src['date_mutation'].dt.year
    df_src['arrondissement'] = df_src['code_postal'].str[-2:]
    return df_src[['annee', 'arrondissement', 'prix_m2']].copy()


def normalize_arrondissement(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors='coerce').astype('Int64')
    values = values.where((values >= 1) & (values <= 20))
    return values.astype('string').str.zfill(2)


def compute_from_silver() -> pd.DataFrame:
    # Prefer SILVER DVF if present
    dvf_silver = Path(SILVER_DIR) / 'immobilier' / 'dvf_clean.csv'
    if dvf_silver.exists():
        df_all = load_csv(dvf_silver, low_memory=False)
        # dvf_clean already contains prix_m2, annee and arrondissement
        if {'prix_m2', 'annee', 'arrondissement'}.issubset(df_all.columns):
            df_dvf_all = df_all[['annee', 'arrondissement', 'prix_m2']].copy()
        else:
            # fallback: attempt to compute prix_m2 if raw cols exist
            df_dvf_all = df_all.copy()
            if 'valeur_fonciere' in df_dvf_all.columns and 'surface_reelle_bati' in df_dvf_all.columns:
                df_dvf_all['prix_m2'] = df_dvf_all['valeur_fonciere'] / df_dvf_all['surface_reelle_bati']
                df_dvf_all = df_dvf_all[['annee', 'arrondissement', 'prix_m2']]
            else:
                raise ValueError('dvf_clean présent mais colonnes nécessaires manquantes')
    else:
        # fallback to bronze sources
        sources_dvf = [
            BRONZE_DIR / 'immobilier' / '75.csv',
            BRONZE_DIR / 'immobilier' / 'valeurs_foncieres.csv',
        ]
        df_dvf_all = pd.concat([load_dvf_source(p) for p in sources_dvf if p.exists()], ignore_index=True)

    df_dvf_all['annee'] = pd.to_numeric(df_dvf_all['annee'], errors='coerce').astype('Int64')
    df_dvf_all['arrondissement'] = normalize_arrondissement(df_dvf_all['arrondissement'])
    df_dvf_all = df_dvf_all.dropna(subset=['annee', 'arrondissement', 'prix_m2'])

    def kpi_m2_q_annuel(df_in: pd.DataFrame) -> pd.DataFrame:
        out = (
            df_in.groupby(['annee', 'arrondissement'], as_index=False)
            .agg(
                prix_m2_median=('prix_m2', 'median'),
                prix_m2_moyen=('prix_m2', 'mean'),
                nb_ventes=('prix_m2', 'size')
            )
            .sort_values(['annee', 'arrondissement'])
        )
        out['arrondissement'] = out['arrondissement'].astype(str).str.zfill(2)
        return out

    kpi_prix_m2_annuel = kpi_m2_q_annuel(df_dvf_all)

    # load quartiers reference (prefer silver cleaned file)
    quartiers_path = Path(SILVER_DIR) / 'commun' / 'quartiers_clean.csv'
    if not quartiers_path.exists():
        quartiers_path = BRONZE_DIR / 'commun' / 'quartier_paris.csv'
        quartiers = load_csv(quartiers_path, sep=';', encoding='utf-8-sig', low_memory=False)
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
        quartiers = load_csv(quartiers_path, low_memory=False)

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

    kpi_prix_m2_quartier_estime = (
        kpi_prix_m2_annuel.merge(
            quartiers[['code_insee_quartier', 'arrondissement', 'surface_quartier_m2', 'part_surface']],
            on='arrondissement',
            how='left'
        )
    )

    kpi_prix_m2_quartier_estime['nb_ventes_estime'] = (
        kpi_prix_m2_quartier_estime['nb_ventes'] * kpi_prix_m2_quartier_estime['part_surface']
    ).round().astype('Int64')

    kpi_prix_m2_quartier_estime = kpi_prix_m2_quartier_estime[
        [
            'annee', 'arrondissement', 'code_insee_quartier',
            'prix_m2_median', 'prix_m2_moyen', 'nb_ventes', 'nb_ventes_estime',
            'surface_quartier_m2', 'part_surface'
        ]
    ].sort_values(['annee', 'arrondissement', 'code_insee_quartier'])

    return kpi_prix_m2_quartier_estime


def main():
    out_path = Path(GOLD_DIR) / 'kpi_prix_m2_quartier_annuel.csv'
    kpi = compute_from_silver()
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
