**Gold KPI Documentation**

- **Location:** `src/pipeline/gold/`
- **Purpose:** compute final KPIs from cleaned Silver artifacts (prefer) or Bronze (fallback) and write CSV outputs to `data/gold/`.

Overview of KPI scripts

1. `gold_kpi_prix_m2_quartier_annuel.py` -> `data/gold/kpi_prix_m2_quartier_annuel.csv`

- Purpose: estimate annual price per m2 at quartier level.
- Sources: `data/silver/immobilier/dvf_clean.csv` (preferred), fallback Bronze DVF files.
- Steps/formula:
  - Use `prix_m2` per transaction (DVF). Aggregate per `(annee, arrondissement)` computing median (`prix_m2_median`), mean and count.
  - Join `quartiers_clean.csv` to distribute arrondissement-level results to quartiers by surface share (`part_surface = surface_quartier_m2 / surface_arrondissement_m2`).
  - `nb_ventes_estime = nb_ventes * part_surface` (rounded).
- Assumptions: when DVF lacks `code_insee_quartier` we estimate via arrondissement→surface proportional split.

2. `gold_kpi_comparaison_achat_location_arrondissement.py` -> `data/gold/kpi_comparaison_achat_location_arrondissement.csv`

- Purpose: compute price-to-rent comparison per arrondissement.
- Sources: DVF (`dvf_clean.csv`) and loyers (`encadrement_loyers_clean.csv`).
- Formula: `kpi_comparaison_achat_location = prix_m2_median / (loyer_reference_median * 12)` (monthly rent \* 12 -> annualized).
- Aggregation: group by `(annee, arrondissement)`, compute medians/means and the KPI.

3. `gold_kpi_comparaison_achat_location_quartier.py` -> `data/gold/kpi_comparaison_achat_location_quartier_estime.csv`

- Purpose: project arrondissement-level `achat` to quartiers to compare with quartier-level `loyers`.
- Sources: output of arrondissement-level comparaison (above) and `quartiers_clean.csv` & loyers (quartier-level).
- Steps:
  - Reuse arrondissement `achat` KPI; normalize `arrondissement` formatting.
  - Merge with `quartiers_clean.csv`, compute `part_surface`, multiply arrondissement metrics by `part_surface` to estimate quartier `nb_transactions_estime` and other metrics.
- Note: this is an estimation; ideally we'd have DVF transactions tagged by `code_insee_quartier`.

4. `gold_kpi_loyers_quartier.py` -> `data/gold/kpi_loyers_quartier.csv`

- Purpose: produce robust quartier-level loyers summary used by other KPIs.
- Sources: `data/silver/immobilier/encadrement_loyers_clean.csv` (preferred) else Bronze loyers.
- Aggregation: group by `(annee, arrondissement, code_insee_quartier)` and compute median/mean of `loyer_reference`, counts, optionally median of `nombre_pieces`, and mode of `nom_quartier`, `type_location`, `epoque_construction`.
- Harmonization: arrondissement is aligned with the INSEE quartier (slice positions 3:5) when possible to avoid mismatch.

5. `gold_kpi_repartition_hlm_arrondissement.py` -> `data/gold/kpi_repartition_logements_sociaux.csv`

- Purpose: map HLM financing/programs, provide counts and localization; enriched to quartier-level when possible.
- Sources: `data/silver/immobilier/hlm_clean.csv` (preferred) else Bronze HLM.
- Aggregation: flexible grouping by `arrondissement`, `annee` and, when geolocated, `code_insee_quartier`/`nom_quartier`. Aggregates include totals/sums/means of `nb_logements_finances` and related fields, counts of programmes and distinct bailleurs, and mean lat/lon when available.
- Enrichment: when lat/lon are present, the script assigns the nearest quartier within the same arrondissement using `quartiers_clean.csv` geometry centroid.

6. `gold_kpi_confort_urbain.py` -> `data/gold/gold_kpi_confort_urbain.csv`

- Purpose: KPIs around confort urbain (dans_ma_rue, gares proximity, chantier counts) as implemented in the original notebook.
- Sources: `data/silver/confort/*`, `data/silver/commun/*`.
- Aggregation/metrics: per notebook logic (counts, normalized scores), see script for exact implementation.

7. `gold_kpi_surete_quartier.py` -> `data/gold/kpi_score_surete_quartier_estime_depuis_iris.csv`

- Purpose: compute a safety score per quartier by composing delinquance indices, camera coverage and proximity to commissariats.
- Sources: `data/silver/surete/*`, `data/silver/commun/iris_clean.csv`, `quartiers_clean.csv`.
- Steps:
  - Build pivot of delinquance indicators and normalize by min-max per indicator.
  - Compute mean risk score per `(annee, arrondissement)` and project to IRIS/quartier.
  - Compute distances to nearest commissariat and normalize; combine components with weights (0.7 delinquance, 0.2 commissariat distance, 0.1 camera coverage) as in the notebook.

General Gold conventions

- Scripts prefer `data/silver/*` artifacts and fall back to Bronze when missing.
- All `arrondissement` are normalized to 2-digit strings for merges.
- When DVF lacks direct quartier mapping, distribution from arrondissement→quartier is done via surface proportion of quartiers in the arrondissement.
- Outputs are written as CSVs to `data/gold/` with descriptive filenames.

Assumptions & recommendations

- If reproducibility with notebook outputs is critical, choose one canonical layer for contract (recommended: Silver). To reproduce notebooks exactly, port exact notebook cleaning into `clean_*` Silver scripts.
- Maintain `quartiers_clean.csv` geometry and surface fields; they are required for projection and nearest-quartier mapping.

Next steps

- If you approve these docs and the produced KPIs, I can scaffold scripts to create DB tables (e.g., SQL DDL or lightweight CSV-to-DB loaders) for the KPIs and geography tables. Suggested script names: `src/pipeline/gold/build_kpi_tables.py` and `src/pipeline/gold/build_geo_tables.py`.
