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


def compute_loyers_from_silver() -> pd.DataFrame:
    # Prefer silver cleaned loyers if present
    loyers_silver = Path(SILVER_DIR) / 'immobilier' / 'encadrement_loyers_clean.csv'
    if loyers_silver.exists():
        df_loyers = pd.read_csv(loyers_silver, low_memory=False)
    else:
        loyers_path = BRONZE_DIR / 'immobilier' / 'logement-encadrement-des-loyers.csv'
        if not loyers_path.exists():
            loyers_path = BRONZE_DIR / 'immobilier' / 'loyers.csv'
        df_loyers = pd.read_csv(loyers_path, sep=';', encoding='utf-8-sig', low_memory=False)

    col_annee = pick_column(df_loyers, ['annee', 'ann'])
    col_arr = pick_column(df_loyers, ['secteurs geographiques', 'arrondissement'])
    col_quartier = pick_column(df_loyers, ['numero insee du quartier', 'code insee quartier', 'code_insee_quartier'])
    col_nom_quartier = pick_column(df_loyers, ['nom du quartier', 'nom_quartier'])
    col_loyer_ref = pick_column(df_loyers, ['loyers de reference', 'loyer reference'])
    col_loyer_majore = pick_column(df_loyers, ['loyers de reference majores', 'loyer_reference_majore'])
    col_loyer_minore = pick_column(df_loyers, ['loyers de reference minores', 'loyer_reference_minore'])
    col_pieces = pick_column(df_loyers, ['nombre de pieces principales', 'nombre_pieces_principales'])
    col_type_location = pick_column(df_loyers, ['type de location', 'type_location'])
    col_epoque = pick_column(df_loyers, ['epoque de construction', 'epoque_construction'])

    if not all([col_annee, col_arr, col_quartier, col_loyer_ref]):
        raise ValueError('Colonnes loyers introuvables pour calcul quartier annuel (annee/arrondissement/quartier/loyer_reference).')

    keep_cols = [
        col_annee, col_arr, col_quartier, col_loyer_ref,
        col_nom_quartier, col_loyer_majore, col_loyer_minore,
        col_pieces, col_type_location, col_epoque,
    ]
    keep_cols = [c for c in keep_cols if c is not None]
    loyers_work = df_loyers[keep_cols].copy()

    loyers_work[col_annee] = to_numeric(loyers_work[col_annee])
    loyers_work[col_arr] = normalize_arrondissement(loyers_work[col_arr])
    loyers_work[col_quartier] = to_numeric(loyers_work[col_quartier]).astype('Int64').astype('string').str.zfill(7)

    # Harmonize arrondissement using INSEE quartier when available to avoid mismatches.
    arr_from_quartier = loyers_work[col_quartier].str.slice(3, 5)
    valid_arr_from_quartier = arr_from_quartier.where(arr_from_quartier.isin([f'{i:02d}' for i in range(1, 21)]))
    loyers_work[col_arr] = valid_arr_from_quartier.fillna(loyers_work[col_arr])
    loyers_work[col_loyer_ref] = to_numeric(loyers_work[col_loyer_ref])
    if col_loyer_majore:
        loyers_work[col_loyer_majore] = to_numeric(loyers_work[col_loyer_majore])
    if col_loyer_minore:
        loyers_work[col_loyer_minore] = to_numeric(loyers_work[col_loyer_minore])
    if col_pieces:
        loyers_work[col_pieces] = to_numeric(loyers_work[col_pieces])
    loyers_work = loyers_work.dropna(subset=[col_annee, col_arr, col_quartier, col_loyer_ref])

    aggregations = {
        'loyer_reference_median': (col_loyer_ref, 'median'),
        'loyer_reference_moyen': (col_loyer_ref, 'mean'),
        'nb_observations': (col_loyer_ref, 'size'),
    }
    if col_loyer_majore:
        aggregations['loyer_reference_majore_median'] = (col_loyer_majore, 'median')
    if col_loyer_minore:
        aggregations['loyer_reference_minore_median'] = (col_loyer_minore, 'median')
    if col_pieces:
        aggregations['nombre_pieces_median'] = (col_pieces, 'median')

    loyers_quartier = (
        loyers_work.groupby([col_annee, col_arr, col_quartier], as_index=False)
        .agg(
            **aggregations
        )
        .rename(columns={
            col_annee: 'annee',
            col_arr: 'arrondissement',
            col_quartier: 'code_insee_quartier',
        })
    )

    loyers_quartier['annee'] = pd.to_numeric(loyers_quartier['annee'], errors='coerce').astype('Int64')
    loyers_quartier['arrondissement'] = normalize_arrondissement(loyers_quartier['arrondissement'])
    loyers_quartier['code_insee_quartier'] = loyers_quartier['code_insee_quartier'].astype('string').str.zfill(7)

    # optional descriptive columns (mode per group)
    if col_nom_quartier:
        nom_map = (
            loyers_work.groupby([col_annee, col_arr, col_quartier])[col_nom_quartier]
            .agg(lambda s: s.dropna().astype(str).mode().iat[0] if not s.dropna().empty else pd.NA)
            .reset_index()
            .rename(columns={
                col_annee: 'annee',
                col_arr: 'arrondissement',
                col_quartier: 'code_insee_quartier',
                col_nom_quartier: 'nom_quartier',
            })
        )
        nom_map['arrondissement'] = normalize_arrondissement(nom_map['arrondissement'])
        nom_map['code_insee_quartier'] = nom_map['code_insee_quartier'].astype('string').str.zfill(7)
        loyers_quartier = loyers_quartier.merge(nom_map, on=['annee', 'arrondissement', 'code_insee_quartier'], how='left')

    if col_type_location:
        type_map = (
            loyers_work.groupby([col_annee, col_arr, col_quartier])[col_type_location]
            .agg(lambda s: s.dropna().astype(str).mode().iat[0] if not s.dropna().empty else pd.NA)
            .reset_index()
            .rename(columns={
                col_annee: 'annee',
                col_arr: 'arrondissement',
                col_quartier: 'code_insee_quartier',
                col_type_location: 'type_location_mode',
            })
        )
        type_map['arrondissement'] = normalize_arrondissement(type_map['arrondissement'])
        type_map['code_insee_quartier'] = type_map['code_insee_quartier'].astype('string').str.zfill(7)
        loyers_quartier = loyers_quartier.merge(type_map, on=['annee', 'arrondissement', 'code_insee_quartier'], how='left')

    if col_epoque:
        epoque_map = (
            loyers_work.groupby([col_annee, col_arr, col_quartier])[col_epoque]
            .agg(lambda s: s.dropna().astype(str).mode().iat[0] if not s.dropna().empty else pd.NA)
            .reset_index()
            .rename(columns={
                col_annee: 'annee',
                col_arr: 'arrondissement',
                col_quartier: 'code_insee_quartier',
                col_epoque: 'epoque_construction_mode',
            })
        )
        epoque_map['arrondissement'] = normalize_arrondissement(epoque_map['arrondissement'])
        epoque_map['code_insee_quartier'] = epoque_map['code_insee_quartier'].astype('string').str.zfill(7)
        loyers_quartier = loyers_quartier.merge(epoque_map, on=['annee', 'arrondissement', 'code_insee_quartier'], how='left')

    loyers_quartier = loyers_quartier.sort_values(['annee', 'arrondissement', 'code_insee_quartier']).reset_index(drop=True)

    return loyers_quartier


def main():
    out_path = Path(GOLD_DIR) / 'kpi_loyers_quartier.csv'
    kpi = compute_loyers_from_silver()
    kpi.to_csv(out_path, index=False)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
