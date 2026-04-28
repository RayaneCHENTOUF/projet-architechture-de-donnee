# Documentation simple - KPI Rayan

## Objectif

Ce document decrit les KPI produits:

- KPI 1: prix median au m2 par annee et arrondissement
- KPI 2: score de surete par annee et arrondissement (agrege depuis IRIS)
- KPI 3: comparaison achat/location par arrondissement

## KPI 1 - Prix median au m2

- Pipeline: `pipeline/silver/pipeline_prix_m2.ipynb`
- Fichier de sortie attendu: `data/gold/kpi_prix_m2_arrondissement.csv`

### Granularite

- 1 ligne = 1 annee x 1 arrondissement

### Colonnes principales

- `annee`
- `arrondissement`
- `prix_m2_median`
- `prix_m2_moyen`
- `nb_transactions`

### Formule principale

- `prix_m2 = valeur_fonciere / surface_reelle_bati`
- `prix_m2_median = median(prix_m2)` par annee et arrondissement

## KPI 2 - Score de surete (agrege)

- Pipeline: `pipeline/silver/pipeline_surete.ipynb`
- Fichier IRIS: `data/gold/kpi_score_surete_iris.csv`
- Fichier agrege arrondissement: `data/gold/kpi_score_surete_arrondissement_agrege_depuis_iris.csv`

### Granularite

- IRIS: 1 ligne = 1 annee x 1 IRIS
- Agrege: 1 ligne = 1 annee x 1 arrondissement

### Colonnes principales (agrege)

- `annee`
- `arrondissement`
- `score_surete_zone_moyen_100`
- `score_risque_zone_moyen_100`
- `nb_iris`

### Logique de calcul (resume)

1. Calcul d'un score de risque delinquance (normalisation min-max par indicateur)
2. Ajout d'un risque lie aux cameras (plus de cameras = moins de risque)
3. Ajout d'un risque lie a la distance au commissariat (plus loin = plus de risque)
4. Score final de surete: `100 - score_risque_final_100`
5. Moyenne des scores IRIS pour obtenir le score agrege arrondissement

## KPI 3 - Comparaison achat/location

- Pipeline: `pipeline/silver/pipeline_comparaison_achat_location.ipynb`
- Fichier de sortie attendu: `data/gold/kpi_comparaison_achat_location.csv`

### Granularite

- 1 ligne = 1 arrondissement

### Colonnes principales

- `arrondissement`
- `prix_m2_median_2021`
- `prix_m2_median_2025`
- `loyer_reference_median_2021`
- `loyer_reference_median_2025`
- `kpi_comparaison_achat_location_2021`
- `kpi_comparaison_achat_location_2025`

### Formule principale

- `kpi_comparaison_achat_location = prix_m2_median / (loyer_reference_median * 12)`

### Interpretation

- Plus le ratio est eleve, plus l'achat est cher relativement a la location.

## Utilisation en base de donnees

- Charger les CSV dans des tables SQL de type `fact_kpi_*`
- Exposer ces tables via l'API pour le front
