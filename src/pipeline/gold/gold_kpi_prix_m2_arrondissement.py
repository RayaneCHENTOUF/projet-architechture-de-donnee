from pathlib import Path
import pandas as pd
import sys

# Ajout du chemin racine du projet pour les imports
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from src.utils.config import GOLD_DIR, BRONZE_DIR, SILVER_DIR


def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_dvf_source(csv_file: Path) -> pd.DataFrame:
    use_cols_dvf = [
        'date_mutation',
        'valeur_fonciere',
        'surface_reelle_bati',
        'code_postal',
        'type_local',
    ]
    df_src = pd.read_csv(csv_file, usecols=use_cols_dvf, parse_dates=['date_mutation'], low_memory=False)
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
    return df_src


def compute_from_silver() -> pd.DataFrame:
    # Prefer SILVER if available
    dvf_silver = Path(SILVER_DIR) / 'immobilier' / 'dvf_clean.csv'
    if dvf_silver.exists():
        df = pd.read_csv(dvf_silver, low_memory=False)
        if {'prix_m2', 'arrondissement'}.issubset(df.columns):
            res = (
                df.groupby('arrondissement', as_index=False)
                .agg(prix_m2_moyen=('prix_m2', 'mean'))
                .sort_values('arrondissement')
            )
            return res
    # fallback to bronze
    sources_dvf = [
        BRONZE_DIR / 'immobilier' / '75.csv',
        BRONZE_DIR / 'immobilier' / 'valeurs_foncieres.csv',
    ]
    frames = [load_dvf_source(p) for p in sources_dvf if p.exists()]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        return pd.DataFrame()
    res = (
        df.groupby('arrondissement', as_index=False)
        .agg(prix_m2_moyen=('prix_m2', 'mean'))
        .sort_values('arrondissement')
    )
    return res


def main():
    out_path = Path(GOLD_DIR) / 'kpi_prix_m2_arrondissement.csv'
    kpi = compute_from_silver()
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
