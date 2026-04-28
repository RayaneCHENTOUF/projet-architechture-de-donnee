**Silver Pipeline Documentation**

- **Location:** `src/pipeline/silver/`
- **Purpose:** standardize, clean and enrich raw Bronze datasets into stable, well-named CSV artifacts under `data/silver/*` that are safe and consistent for downstream Gold KPIs.

Summary of scripts and outputs

1. `clean_immobilier.py` -> `data/silver/immobilier/`

- Files produced: `dvf_clean.csv`, `hlm_clean.csv`, `encadrement_loyers_clean.csv`.
- Main treatments:
  - Column normalization and flexible column matching (function `pick_column`).
  - Parsing and standardizing postal codes (`parse_postal_code`) and arrondissement (`arrondissement` as zero-padded string `01`..`20`).
  - Date parsing for transaction dates (`date_mutation`) and `annee` extraction.
  - Numeric cleaning with `to_numeric` (removes non-numeric spaces, fixes commas/decimal points).
  - Geometry extraction: parse `geo_point_2d` into `latitude` / `longitude` where available.
  - Filters and quality rules applied to DVF: remove records with small surface (< 10 m2), low transaction value (< 10k), remove extreme `prix_m2` outliers (01/99 quantiles), keep only `Appartement` or `Maison`.
  - HLM: standardize financing year (`annee_financement` -> `annee`), numeric counts (`nb_logements_finances` etc), normalize program modes and nature, compute `mode_de_realisation_code`.
  - Loyers: normalize `annee`, `code_insee_quartier` (zero-padded 7), compute `arrondissement` from `code_insee_quartier` when necessary, parse `geo_point_2d`.
- Columns retained and re-emitted (non-exhaustive): `date_mutation`, `valeur_fonciere`, `surface_reelle_bati`, `prix_m2`, `annee`, `code_postal`, `arrondissement`, `type_local`, `nombre_pieces_principales`, `longitude`, `latitude`, `id_mutation`, `nb_logements_finances`, `code_insee_quartier`, `loyer_reference`, `loyer_reference_majore`, `loyer_reference_minore`.

2. `clean_geographie.py` -> `data/silver/commun/`

- Files produced: `quartiers_clean.csv`, `iris_clean.csv`, `arrondissements_clean.csv`.
- Main treatments:
  - Normalization of column names and robust column detection for varied source schema.
  - `quartiers_clean.csv`: produces columns `arrondissement` (zfilled), `code_quartier_id`, `code_insee_quartier` (7-digit, prefixed with 751), `nom_quartier`, `surface_quartier_m2`, `geometry_xy` (lat,lon string). Surface used for projection from arrondissement to quartier.
  - `iris_clean.csv`: emits `INSEE_COM`, `CODE_IRIS`, `NOM_IRIS`, `Geo Point` and `Geo Shape` so downstream exports can build polygon GeoJSON from IRIS contours while keeping the centroïd available for legacy joins.
  - `arrondissements_clean.csv`: standardized `arrondissement` numbers.

3. `clean_surete.py` -> `data/silver/surete/`

- Files produced: `delinquance_clean.csv`, `commissariats_clean.csv`, `cameras_clean.csv`.
- Main treatments:
  - Normalize indicator names and text fields.
  - Ensure `codgeo` codes are zero-padded to 5 and filtered to Paris (`751..`).
  - Compute `arrondissement` from `codgeo` where applicable.
  - Parse and expose `taux_pour_mille` / `complement_info_taux` and unify into `taux_effectif` when possible.
  - Parse `geo_point_2d` into `latitude` / `longitude` for cameras and commissariats.

4. `clean_confort.py` -> `data/silver/confort/`

- Files produced: `dans_ma_rue_clean.csv`, `gares_clean.csv`, `paris_se_transforme_clean.csv`.
- Main treatments:
  - Date parsing and extraction of `annee` for signals.
  - Category extraction and normalization (`categorie_signalement`).
  - Geo parsing into lat/lon and arrondissement extraction from postal code when available.

General conventions and assumptions (Silver)

- All `arrondissement` fields are normalized to 2-character strings `01`..`20` for consistent joins.
- Numeric parsing uses `to_numeric` helper which removes non-digit characters and interprets commas as decimals.
- Geo points are kept as both raw `geo_point_2d` and parsed `latitude`/`longitude` when possible.
- Files are written under `data/silver/<domain>/` with descriptive filenames ending in `_clean.csv`.
- If multiple Bronze sources exist for a concept, Silver concatenates and deduplicates with consistent column mapping.
- Outlier clipping (e.g., DVF `prix_m2`) follows quantile-based trimming (default 1%/99%) to match notebooks' approach.

How these affect Gold

- Gold scripts now read Silver first (preferred), falling back to Bronze only if Silver artifact is missing.
- Any change in Silver filtering, renaming, or column type will propagate to Gold aggregations and can change KPI results vs legacy notebooks.

---

File references (quick):

- `src/pipeline/silver/clean_immobilier.py` -> `data/silver/immobilier/dvf_clean.csv`
- `src/pipeline/silver/clean_geographie.py` -> `data/silver/commun/quartiers_clean.csv`, `iris_clean.csv`
- `src/pipeline/silver/clean_surete.py` -> `data/silver/surete/*`
- `src/pipeline/silver/clean_confort.py` -> `data/silver/confort/*`

Notes and next steps

- If you need strict reproductions of notebook outputs, we should either (A) adopt exact notebook cleaning steps in Silver, or (B) update Gold to match legacy expectations. Decide which layer should be the canonical contract (I recommend Silver as contract).
- I can produce a shorter CSV schema file describing columns for each Silver artifact if you want machine-readable schemas.
