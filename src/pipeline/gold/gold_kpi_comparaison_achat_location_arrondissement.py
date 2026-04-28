from pathlib import Path
import re
import unicodedata
import pandas as pd
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


def load_dvf_source(csv_file: Path) -> pd.DataFrame:
    use_cols = ['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'code_postal', 'type_local']
    df = pd.read_csv(csv_file, usecols=use_cols, parse_dates=['date_mutation'], low_memory=False)
    df = df.dropna(subset=['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'code_postal'])
    df = df[df['surface_reelle_bati'] > 9]
    df = df[df['valeur_fonciere'] > 10000]
    df = df[df['type_local'].isin(['Appartement', 'Maison'])]
    df['code_postal'] = df['code_postal'].astype(int).astype(str).str.zfill(5)
    df = df[df['code_postal'].str.startswith('75')]
    df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
    q_low = df['prix_m2'].quantile(0.01)
    q_high = df['prix_m2'].quantile(0.99)
    df = df[(df['prix_m2'] >= q_low) & (df['prix_m2'] <= q_high)]
    df['annee'] = df['date_mutation'].dt.year
    df['arrondissement'] = df['code_postal'].str[-2:]
    return df[['annee', 'arrondissement', 'prix_m2']]


def compute_from_silver() -> pd.DataFrame:
    # Achat: prefer SILVER dvf_clean
    dvf_silver = Path(SILVER_DIR) / 'immobilier' / 'dvf_clean.csv'
    if dvf_silver.exists():
        achat_all = pd.read_csv(dvf_silver, low_memory=False)
        if {'annee', 'arrondissement', 'prix_m2'}.issubset(achat_all.columns):
            achat_all = achat_all[['annee', 'arrondissement', 'prix_m2']]
        else:
            achat_all = achat_all.copy()
            if 'valeur_fonciere' in achat_all.columns and 'surface_reelle_bati' in achat_all.columns:
                achat_all['prix_m2'] = achat_all['valeur_fonciere'] / achat_all['surface_reelle_bati']
                achat_all = achat_all[['annee', 'arrondissement', 'prix_m2']]
            else:
                # fallback to bronze when silver missing necessary cols
                achat_all = pd.concat([load_dvf_source(p) for p in [BRONZE_DIR / 'immobilier' / '75.csv', BRONZE_DIR / 'immobilier' / 'valeurs_foncieres.csv'] if p.exists()], ignore_index=True)
    else:
        achat_all = pd.concat([load_dvf_source(p) for p in [BRONZE_DIR / 'immobilier' / '75.csv', BRONZE_DIR / 'immobilier' / 'valeurs_foncieres.csv'] if p.exists()], ignore_index=True)

    achat_all['annee'] = pd.to_numeric(achat_all['annee'], errors='coerce').astype('Int64')
    achat_all['arrondissement'] = normalize_arrondissement(achat_all['arrondissement'])
    achat_all = achat_all.dropna(subset=['annee', 'arrondissement', 'prix_m2'])

    achat_arr_annuel = (
        achat_all.groupby(['annee', 'arrondissement'], as_index=False)
        .agg(
            prix_m2_median=('prix_m2', 'median'),
            prix_m2_moyen=('prix_m2', 'mean'),
            nb_transactions=('prix_m2', 'size')
        )
    )

    # Location: prefer SILVER encadrement_loyers_clean
    loyers_silver = Path(SILVER_DIR) / 'immobilier' / 'encadrement_loyers_clean.csv'
    if loyers_silver.exists():
        df_loyers = pd.read_csv(loyers_silver, low_memory=False)
    else:
        loyers_path = BRONZE_DIR / 'immobilier' / 'logement-encadrement-des-loyers.csv'
        df_loyers = pd.read_csv(loyers_path, sep=';', encoding='utf-8-sig', low_memory=False)

    col_annee = pick_column(df_loyers, ['annee', 'ann'])
    col_arr = pick_column(df_loyers, ['secteurs geographiques', 'arrondissement'])
    col_loyer_ref = pick_column(df_loyers, ['loyers de reference', 'loyer reference'])

    if not all([col_annee, col_arr, col_loyer_ref]):
        raise ValueError('Colonnes loyers introuvables pour calcul annuel (annee/arrondissement/loyer_reference).')

    loyers_work = df_loyers[[col_annee, col_arr, col_loyer_ref]].copy()
    loyers_work[col_annee] = to_numeric(loyers_work[col_annee])
    loyers_work[col_arr] = to_numeric(loyers_work[col_arr])
    loyers_work[col_loyer_ref] = to_numeric(loyers_work[col_loyer_ref])
    loyers_work = loyers_work.dropna(subset=[col_annee, col_arr, col_loyer_ref])

    loyers_arr_annuel = (
        loyers_work.groupby([col_annee, col_arr], as_index=False)
        .agg(
            loyer_reference_median=(col_loyer_ref, 'median'),
            loyer_reference_moyen=(col_loyer_ref, 'mean'),
            nb_observations=(col_loyer_ref, 'size')
        )
        .rename(columns={col_annee: 'annee', col_arr: 'arrondissement'})
    )
    loyers_arr_annuel['annee'] = pd.to_numeric(loyers_arr_annuel['annee'], errors='coerce').astype('Int64')
    loyers_arr_annuel['arrondissement'] = normalize_arrondissement(loyers_arr_annuel['arrondissement'])
    loyers_arr_annuel = loyers_arr_annuel.dropna(subset=['annee', 'arrondissement'])

    kpi_base_projection = achat_arr_annuel.merge(
        loyers_arr_annuel,
        on=['annee', 'arrondissement'],
        how='inner'
    )

    kpi_base_projection['kpi_comparaison_achat_location'] = (
        kpi_base_projection['prix_m2_median'] / (kpi_base_projection['loyer_reference_median'] * 12)
    )

    for c in ['prix_m2_median', 'prix_m2_moyen', 'loyer_reference_median', 'loyer_reference_moyen', 'kpi_comparaison_achat_location']:
        if c in kpi_base_projection.columns:
            kpi_base_projection[c] = kpi_base_projection[c].round(4)

    return kpi_base_projection


def main():
    out_path = Path(GOLD_DIR) / 'kpi_comparaison_achat_location_arrondissement.csv'
    kpi = compute_from_silver()
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
