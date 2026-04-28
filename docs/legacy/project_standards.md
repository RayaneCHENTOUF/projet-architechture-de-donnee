# Standards Projet - Urban Data Explorer

## 1) Convention de nommage

### Fichiers

- KPI Gold: `kpi_<nom_indicateur>.csv`
- Table SQL: `fact_kpi_<nom_indicateur>`
- Notebook pipeline: `pipeline_<nom>.ipynb`

### Colonnes

- snake_case uniquement
- Pas d'accents, pas d'espaces
- Suffixes temporels explicites si snapshot (`_2021`, `_2025`)

## 2) Cles de reference

- `arrondissement`: chaine sur 2 caracteres (`01` a `20`)
- `annee`: entier quand la table est temporelle
- Tables geo fines: `code_iris` pour l'IRIS

## 3) Formats CSV

Standard cible Gold:

- Delimiter: `,`
- Encoding: `utf-8`
- Header: obligatoire
- Decimal: point (`.`)

Exception temporaire (historique):

- `gold_kpi_confort_urbain.csv` peut rester en `;` tant que le notebook source n'est pas migre.

## 4) Contrats minimaux par famille KPI

### KPI arrondissement temporel

Colonnes minimales:

- `annee`
- `arrondissement`
- metriques KPI

Exemples:

- `kpi_prix_m2_arrondissement.csv`
- `kpi_evolution_achat_prix_m2.csv`
- `kpi_score_surete_arrondissement_agrege_depuis_iris.csv`

### KPI arrondissement snapshot

Colonnes minimales:

- `arrondissement`
- metriques KPI

Exemples:

- `kpi_comparaison_achat_location.csv`
- `kpi_loyer_par_arrondissement.csv`

### KPI infra-arrondissement

Colonnes minimales:

- `annee` (si temporel)
- `arrondissement`
- cle fine (`code_iris` ou `code_quartier`)

Exemples:

- `kpi_score_surete_iris.csv`
- `gold_kpi_confort_urbain.csv`

## 5) Unification semantique

Noms preferes:

- `nb_transactions` (au lieu de melanger avec `nb_ventes`)
- `prix_m2_median`
- `loyer_reference_median`

Regle:

- Si un legacy existe, conserver le nom legacy dans la source et documenter une alias map dans le pipeline/API.

## 6) Documentation obligatoire d'un KPI

Chaque KPI doit documenter:

1. Source(s)
2. Formule
3. Granularite
4. Colonnes de sortie
5. Limites

## 7) Validation avant publication Gold

Checks minimum:

1. Fichier lisible
2. Colonnes minimales presentes
3. `arrondissement` normalise sur 2 caracteres quand present
4. Pas de duplication de cle metier principale
5. Type de `annee` numerique quand present
