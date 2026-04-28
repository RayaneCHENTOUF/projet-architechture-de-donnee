# 🏗️ Architecture — Urban Data Explorer

## Vue d'ensemble

Le projet suit l'architecture **Medallion** (Bronze → Silver → Gold), un pattern standard en Data Engineering qui garantit la traçabilité, la qualité et la réutilisabilité des données à chaque étape de transformation.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCES OPEN DATA                            │
│   data.gouv.fr  │  Ville de Paris  │  INSEE  │  Préfecture Police  │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Téléchargement manuel / automatisé
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        🥉 COUCHE BRONZE                             │
│                         data/bronze/                                │
│                                                                     │
│  valeurs_foncieres.csv  │  loyers.csv  │  dataset_delinquances.csv  │
│  hlm.csv  │  quartier_paris.csv  │  iris.csv  │  dans-ma-rue.csv   │
│  commissariats.csv  │  cameras.csv  │  gares.csv  │  ...           │
└────────────────────────────┬────────────────────────────────────────┘
                             │  src/pipeline/silver/run_silver.py
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        🥈 COUCHE SILVER                             │
│                          data/silver/                               │
│                                                                     │
│  commun/          │  immobilier/        │  surete/   │  confort/   │
│  ─────────────    │  ───────────────    │  ────────  │  ─────────  │
│  quartiers_       │  dvf_clean.csv      │  delinquan │  dans_ma_   │
│  clean.csv        │  hlm_clean.csv      │  ce_clean  │  rue_clean  │
│  iris_clean.csv   │  encadrement_       │  .csv      │  .csv       │
│  arrondisse-      │  loyers_clean.csv   │  commis-   │  gares_     │
│  ments_clean.csv  │                     │  sariats_  │  clean.csv  │
│                   │                     │  clean.csv │  paris_se_  │
│                   │                     │  cameras_  │  transforme │
│                   │                     │  clean.csv │  _clean.csv │
└────────────────────────────┬────────────────────────────────────────┘
                             │  src/pipeline/gold/run_gold.py
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         🥇 COUCHE GOLD                              │
│                           data/gold/                                │
│                                                                     │
│  kpi_prix_m2_quartier_annuel.csv                                    │
│  kpi_comparaison_achat_location_arrondissement.csv                  │
│  kpi_comparaison_achat_location_quartier_estime.csv                 │
│  kpi_loyers_quartier.csv                                            │
│  kpi_repartition_logements_sociaux.csv                              │
│  gold_kpi_confort_urbain.csv                                        │
│  kpi_score_surete_quartier_estime_depuis_iris.csv                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │  sql/*.sql
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BASES DE DONNÉES                              │
│   Relationnel: tables KPI / dimensions   │  NoSQL: GeoJSON / points │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API / DATAVIZ                                │
│              FastAPI + front/ pour consommer les données             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Détail des couches

### 🥉 Bronze — Données brutes

**Chemin :** `data/bronze/`

**Principe :** Les données sont stockées telles quelles, sans aucune modification. Cette couche garantit la **traçabilité** et la possibilité de **rejouer** tout le pipeline depuis la source.

| Fichier Bronze                                        | Domaine    | Taille approx. |
| ----------------------------------------------------- | ---------- | -------------- |
| `valeurs_foncieres.csv`                               | Immobilier | ~240 Mo        |
| `loyers.csv`                                          | Immobilier | ~79 Mo         |
| `hlm.csv` / `logements-sociaux-finances-a-paris.csv`  | Immobilier | ~1 Mo          |
| `dataset_delinquances.csv`                            | Sûreté     | ~621 Mo        |
| `cartographie-des-emplacements-des-commissariats.csv` | Sûreté     | ~12 Ko         |
| `points.csv`                                          | Sûreté     | ~289 Ko        |
| `dans-ma-rue.csv`                                     | Confort    | ~360 Mo        |
| `parissetransforme.csv`                               | Confort    | ~2.4 Mo        |
| `emplacement-des-gares-idf.csv`                       | Confort    | ~506 Ko        |
| `quartier_paris.csv`                                  | Géographie | ~357 Ko        |
| `iris.csv`                                            | Géographie | ~698 Ko        |
| `arrondissements.csv`                                 | Géographie | ~210 Ko        |
| `75.csv`                                              | Géographie | ~15 Mo         |

---

### 🥈 Silver — Données nettoyées

**Chemin :** `data/silver/<domaine>/`  
**Scripts :** `src/pipeline/silver/`

**Principe :** Chaque script Silver prend un ou plusieurs fichiers Bronze en entrée et produit des artefacts CSV propres et stables, avec des colonnes normalisées, des types corrects et des outliers traités.

#### Conventions Silver

- Les colonnes `arrondissement` sont normalisées en chaîne 2 caractères (`01`..`20`).
- Les codes `code_insee_quartier` sont en 7 chiffres, préfixés `751`.
- Les géo-points `geo_point_2d` sont splitté en `latitude` / `longitude`.
- Les valeurs numériques sont nettoyées (virgules → points, espaces retirés).
- Les fichiers Silver se terminent toujours par `_clean.csv`.

#### Scripts Silver

| Script                | Entrée (Bronze)                                               | Sorties (Silver)                                                                                    |
| --------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `clean_immobilier.py` | `valeurs_foncieres.csv`, `loyers.csv`, `hlm.csv`              | `immobilier/dvf_clean.csv`, `immobilier/encadrement_loyers_clean.csv`, `immobilier/hlm_clean.csv`   |
| `clean_geographie.py` | `quartier_paris.csv`, `iris.csv`, `arrondissements.csv`       | `commun/quartiers_clean.csv`, `commun/iris_clean.csv`, `commun/arrondissements_clean.csv`           |
| `clean_surete.py`     | `dataset_delinquances.csv`, `commissariats.csv`, `points.csv` | `surete/delinquance_clean.csv`, `surete/commissariats_clean.csv`, `surete/cameras_clean.csv`        |
| `clean_confort.py`    | `dans-ma-rue.csv`, `gares.csv`, `parissetransforme.csv`       | `confort/dans_ma_rue_clean.csv`, `confort/gares_clean.csv`, `confort/paris_se_transforme_clean.csv` |

---

### 🥇 Gold — KPI finaux

**Chemin :** `data/gold/`  
**Scripts :** `src/pipeline/gold/`

**Principe :** Les scripts Gold lisent en priorité les artefacts Silver (fallback Bronze si absent) et produisent des KPI agrégés, directement injectables en base de données.

#### Stratégie de projection Quartier

Quand les données DVF ne disposent pas du `code_insee_quartier`, la projection se fait via la **proportion de surface** :

```
part_surface = surface_quartier_m2 / surface_arrondissement_m2
nb_ventes_quartier_estime = nb_ventes_arrondissement × part_surface
```

Ce calcul utilise `commun/quartiers_clean.csv` comme référentiel géographique.

#### KPI et formules

| Script Gold                                             | KPI produit                             | Formule clé                                                                  |
| ------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------- |
| `gold_kpi_prix_m2_quartier_annuel.py`                   | Prix médian m² par quartier/année       | `median(prix_m2)` par `(annee, quartier)`                                    |
| `gold_kpi_comparaison_achat_location_arrondissement.py` | Ratio achat/location                    | `prix_m2_median / (loyer_ref_median × 12)`                                   |
| `gold_kpi_comparaison_achat_location_quartier.py`       | Ratio achat/location (quartier, estimé) | Projection surface depuis arrondissement                                     |
| `gold_kpi_loyers_quartier.py`                           | Loyers de référence par quartier        | `median(loyer_reference)` par `(annee, arrondissement, code_insee_quartier)` |
| `gold_kpi_repartition_hlm_arrondissement.py`            | Répartition logements sociaux           | Comptages + géolocalisation nearest-quartier                                 |
| `gold_kpi_confort_urbain.py`                            | Score confort urbain                    | Scores normalisés (signalements, gares, chantiers)                           |
| `gold_kpi_surete_quartier.py`                           | Score sûreté par quartier               | `0.7×délinquance + 0.2×distance_commissariat + 0.1×couverture_cameras`       |

---

## 🗄️ Couche SQL

**Chemin :** `sql/`

Les scripts SQL créent les tables de destination pour chaque KPI Gold dans la base de données cible. Ils correspondent 1-pour-1 aux fichiers CSV Gold.

| Script SQL                              | Table créée                                                  |
| --------------------------------------- | ------------------------------------------------------------ |
| `geo_info.sql`                          | Table de référence géographique (quartiers, arrondissements) |
| `kpi_prix_m2_quartier_annuel.sql`       | `kpi_prix_m2_quartier_annuel`                                |
| `kpi_comparaison_achat_location.sql`    | `kpi_comparaison_achat_location`                             |
| `kpi_loyers_quartier.sql`               | `kpi_loyers_quartier`                                        |
| `kpi_confort_urbain.sql`                | `kpi_confort_urbain`                                         |
| `kpi_repartition_logements_sociaux.sql` | `kpi_repartition_logements_sociaux`                          |
| `kpi_surete_quartier.sql`               | `kpi_surete_quartier`                                        |

### Chargement relationnel

Le script `src/pipeline/export/build_storage_exports.py` génère `sql/load_gold_kpis.psql`, un loader PostgreSQL basé sur `\copy` pour injecter les KPI Gold dans les tables relationnelles.

### Export NoSQL / GeoJSON

Le même script exporte des documents GeoJSON dans `data/exports/nosql/` pour les ensembles géographiques et les positions ponctuelles. L'export IRIS utilise les contours polygonaux du fichier bronze `iris.csv` :

- `quartiers.geojson`
- `iris.geojson` avec géométries `Polygon`
- `commissariats.geojson`
- `cameras.geojson`
- `gares.geojson`

Ces fichiers sont prêts pour une collection MongoDB ou tout autre stockage NoSQL orienté documents.

---

## 🔧 Utilitaires

### `src/utils/config.py`

Centralise les chemins du projet pour éviter les chemins relatifs éparpillés dans les scripts :

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR    = PROJECT_ROOT / "data"
BRONZE_DIR  = DATA_DIR / "bronze"
SILVER_DIR  = DATA_DIR / "silver"
GOLD_DIR    = DATA_DIR / "gold"
```

Tous les scripts Silver et Gold importent `config.py` pour référencer les chemins.

---

## 📓 Notebooks

**Chemin :** `notebooks/`

Les notebooks Jupyter ont été utilisés pour le **prototypage** des transformations. Les logiques validées ont été portées en scripts Python dans `src/pipeline/`.

| Notebook                                    | Équivalent Python                            |
| ------------------------------------------- | -------------------------------------------- |
| `pipeline_prix_m2.ipynb`                    | `gold_kpi_prix_m2_quartier_annuel.py`        |
| `pipeline_surete.ipynb`                     | `gold_kpi_surete_quartier.py`                |
| `kpi_confort_urbain.ipynb`                  | `gold_kpi_confort_urbain.py`                 |
| `pipeline_comparaison_achat_location.ipynb` | `gold_kpi_comparaison_achat_location_*.py`   |
| `kpi_hlm_et_location.ipynb`                 | `gold_kpi_repartition_hlm_arrondissement.py` |

---

## 🔄 Flux d'exécution complet

```
1. Télécharger les sources → data/bronze/
2. python src/pipeline/silver/run_silver.py   → data/silver/
3. python src/pipeline/gold/run_gold.py        → data/gold/
4. Exécuter les scripts sql/*.sql              → Base de données
5. Lancer l'API (src/api/)                     → Endpoint REST
6. Afficher via front/                          → Dataviz
```

---

## 📐 Conventions de nommage

| Niveau        | Convention                         | Exemple                           |
| ------------- | ---------------------------------- | --------------------------------- |
| Bronze        | `<sujet>.csv` (source originale)   | `valeurs_foncieres.csv`           |
| Silver        | `<sujet>_clean.csv`                | `dvf_clean.csv`                   |
| Gold          | `kpi_<metrique>_<granularite>.csv` | `kpi_prix_m2_quartier_annuel.csv` |
| Script Silver | `clean_<domaine>.py`               | `clean_immobilier.py`             |
| Script Gold   | `gold_kpi_<metrique>.py`           | `gold_kpi_surete_quartier.py`     |
| Table SQL     | `kpi_<metrique>_<granularite>`     | `kpi_prix_m2_quartier_annuel`     |
