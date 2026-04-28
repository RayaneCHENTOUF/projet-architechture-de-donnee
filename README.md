# 🏙️ Urban Data Explorer — Projet Data EFREI

> Pipeline de données immobilières et urbaines sur Paris, structuré en architecture **Bronze → Silver → Gold**.

---

## 📌 Objectif

Ce projet construit des **indicateurs clés (KPI) immobiliers et urbains** sur Paris à partir de sources open data. Il suit une architecture Medallion en trois couches :

| Couche        | Rôle                                                                        |
| ------------- | --------------------------------------------------------------------------- |
| 🥉 **Bronze** | Données brutes, telles que téléchargées depuis les sources open data        |
| 🥈 **Silver** | Données nettoyées, normalisées et enrichies, prêtes pour l'analyse          |
| 🥇 **Gold**   | KPI finaux agrégés, prêts pour l'injection en base de données et la dataviz |

---

## 🗂️ Structure du projet

```
projet-data-dev/
│
├── data/
│   ├── bronze/              # Sources brutes (CSV open data)
│   ├── silver/              # Données nettoyées par domaine
│   │   ├── commun/          # Géographies (quartiers, IRIS, arrondissements)
│   │   ├── immobilier/      # DVF, loyers, HLM nettoyés
│   │   ├── surete/          # Délinquance, commissariats, caméras
│   │   └── confort/         # Signalements, gares, chantiers
│   └── gold/                # KPI finaux (CSV)
│
├── src/
│   ├── pipeline/
│   │   ├── silver/          # Scripts de nettoyage Bronze → Silver
│   │   │   ├── clean_immobilier.py
│   │   │   ├── clean_geographie.py
│   │   │   ├── clean_surete.py
│   │   │   ├── clean_confort.py
│   │   │   └── run_silver.py
│   │   └── gold/            # Scripts de calcul KPI Silver → Gold
│   │       ├── gold_kpi_prix_m2_quartier_annuel.py
│   │       ├── gold_kpi_comparaison_achat_location_arrondissement.py
│   │       ├── gold_kpi_comparaison_achat_location_quartier.py
│   │       ├── gold_kpi_loyers_quartier.py
│   │       ├── gold_kpi_repartition_hlm_arrondissement.py
│   │       ├── gold_kpi_confort_urbain.py
│   │       ├── gold_kpi_surete_quartier.py
│   │       └── run_gold.py
│   └── utils/
│       └── config.py        # Chemins centralisés du projet
│
├── notebooks/               # Notebooks exploratoires et de prototypage KPI
│   ├── pipeline_prix_m2.ipynb
│   ├── pipeline_surete.ipynb
│   ├── kpi_confort_urbain.ipynb
│   ├── pipeline_comparaison_achat_location.ipynb
│   └── kpi_hlm_et_location.ipynb
│
├── sql/                     # Scripts SQL de création des tables Gold
│   ├── geo_info.sql
│   ├── kpi_prix_m2_quartier_annuel.sql
│   ├── kpi_comparaison_achat_location.sql
│   ├── kpi_loyers_quartier.sql
│   ├── kpi_confort_urbain.sql
│   ├── kpi_repartition_logements_sociaux.sql
│   ├── kpi_surete_quartier.sql
│   └── load_gold_kpis.psql   # Chargement PostgreSQL des KPI Gold
│
├── data/
│   └── exports/             # Artefacts prêts pour les bases relationnelle et NoSQL
│       ├── relational/      # Manifest des tables KPI
│       └── nosql/           # GeoJSON prêts pour MongoDB
│
├── docs/                    # Documentation technique
│   ├── silver_pipeline_documentation.md
│   ├── gold_kpi_documentation.md
│   ├── architecture.md
│   └── index.md
│
├── front/                   # Interface de visualisation (à venir)
├── .env                     # Variables d'environnement (non versionné)
├── .gitignore
└── README.md
```

---

## 📊 KPI Gold disponibles

### KPI Immobiliers

| Fichier                                              | Description                                      |
| ---------------------------------------------------- | ------------------------------------------------ |
| `kpi_prix_m2_quartier_annuel.csv`                    | Prix médian au m² par quartier et par année      |
| `kpi_comparaison_achat_location_arrondissement.csv`  | Ratio achat/location par arrondissement          |
| `kpi_comparaison_achat_location_quartier_estime.csv` | Ratio achat/location estimé par quartier         |
| `kpi_loyers_quartier.csv`                            | Loyers de référence par quartier                 |
| `kpi_repartition_logements_sociaux.csv`              | Répartition et géolocalisation des logements HLM |

### KPI Urbains

| Fichier                                            | Description                                                          |
| -------------------------------------------------- | -------------------------------------------------------------------- |
| `gold_kpi_confort_urbain.csv`                      | Score de confort urbain (signalements, gares, chantiers)             |
| `kpi_score_surete_quartier_estime_depuis_iris.csv` | Score de sûreté par quartier (délinquance + commissariats + caméras) |

---

## 🚀 Lancement du pipeline

### Prérequis

- Python 3.9+
- Dépendances : `pandas`, `numpy`, `pathlib`

```bash
pip install pandas numpy
```

### Étape 1 — Pipeline Silver (nettoyage des données brutes)

```bash
python src/pipeline/silver/run_silver.py
```

> Lit les fichiers depuis `data/bronze/` et produit les fichiers nettoyés dans `data/silver/`.

### Étape 2 — Pipeline Gold (calcul des KPI)

```bash
python src/pipeline/gold/run_gold.py
```

> Lit les fichiers depuis `data/silver/` et produit les KPI finaux dans `data/gold/`.

### Étape 3 — Préparation des exports de stockage

```bash
python src/pipeline/export/build_storage_exports.py
```

> Génère un loader PostgreSQL pour les tables KPI dans `sql/load_gold_kpis.psql` et des documents GeoJSON dans `data/exports/nosql/` pour les géométries et positions, avec `iris.geojson` basé sur les contours polygonaux IRIS.

### Étape 4 — Injection SQL

Utiliser les scripts du dossier `sql/` pour créer et alimenter les tables dans votre base relationnelle.

---

## 🌐 Sources de données (Bronze)

| Fichier                                                                          | Source                  | Description                        |
| -------------------------------------------------------------------------------- | ----------------------- | ---------------------------------- |
| `valeurs_foncieres.csv`                                                          | DVF / data.gouv.fr      | Transactions immobilières Paris    |
| `loyers.csv`                                                                     | Ville de Paris          | Encadrement des loyers             |
| `hlm.csv` / `logements-sociaux-finances-a-paris.csv`                             | Ville de Paris          | Logements sociaux financés         |
| `quartier_paris.csv`                                                             | Ville de Paris          | Géographie des quartiers parisiens |
| `iris.csv`                                                                       | INSEE                   | Découpage IRIS                     |
| `arrondissements.csv`                                                            | Ville de Paris          | Contours des arrondissements       |
| `dataset_delinquances.csv`                                                       | Préfecture de Police    | Statistiques de délinquance        |
| `cartographie-des-emplacements-des-commissariats-a-paris-et-petite-couronne.csv` | Préfecture de Police    | Localisation des commissariats     |
| `points.csv`                                                                     | Ville de Paris          | Caméras de surveillance            |
| `dans-ma-rue.csv`                                                                | Ville de Paris          | Signalements urbains               |
| `emplacement-des-gares-idf.csv`                                                  | Île-de-France Mobilités | Gares Île-de-France                |
| `parissetransforme.csv`                                                          | Ville de Paris          | Chantiers et projets urbains       |
| `75.csv`                                                                         | INSEE / open data       | Données complémentaires Paris      |

---

## 📁 Documentation

| Document                                                                         | Description                      |
| -------------------------------------------------------------------------------- | -------------------------------- |
| [`docs/index.md`](docs/index.md)                                                 | Index de toute la documentation  |
| [`docs/architecture.md`](docs/architecture.md)                                   | Architecture détaillée du projet |
| [`docs/silver_pipeline_documentation.md`](docs/silver_pipeline_documentation.md) | Documentation des scripts Silver |
| [`docs/gold_kpi_documentation.md`](docs/gold_kpi_documentation.md)               | Documentation des KPI Gold       |

---

## 👥 Équipe

Chentouf Rayan -- Yacine Bakour -- Nawfel Younes -- Alexandre Kosutic
Projet réalisé dans le cadre du cursus **Data Engineering — EFREI Paris**.

---

## 📄 Licence

Usage académique — EFREI Paris.

# 🏙️ Urban Data Explorer — Paris Dashboard

> Interface moderne de visualisation des indicateurs clés (KPI) immobiliers et urbains de la ville de Paris.

Ce projet est une application frontend interactive permettant d'explorer les 80 quartiers administratifs de Paris à travers divers prismes : confort urbain, sûreté, prix de l'immobilier, encadrement des loyers et logements sociaux.

---

## 🚀 Fonctionnalités

- **Carte Interactive** : Navigation par quartier et arrondissement sur un fond de carte Mapbox.
- **Tableau de Bord KPI** : Visualisation détaillée des scores et données historiques pour chaque quartier.
- **Classement par Arrondissement** : Comparaison des quartiers au sein d'un même arrondissement.
- **Recherche d'Adresse** : Localisation précise et identification du quartier correspondant.
- **Design Premium** : Interface sombre moderne avec effets de flou (glassmorphism) et animations fluides.

---

## 🛠️ Installation et Lancement

### Prérequis

- [Node.js](https://nodejs.org/) (version 16+)
- [npm](https://www.npmjs.com/)

### Lancement local

1. Allez dans le dossier frontend :
   ```bash
   cd front
   ```
2. Installez les dépendances :
   ```bash
   npm install
   ```
3. Lancez le serveur de développement :
   ```bash
   npm run dev
   ```

L'application sera accessible sur `http://localhost:5173`.

---

## 📂 Structure du Projet

L'application est désormais **front-only**, utilisant des données locales pré-calculées :

```
projet-data/
│
├── front/                   # Application React + Vite + TypeScript
│   ├── src/
│   │   ├── components/      # Composants UI (Carte, Sidebar, KPI, Ranking)
│   │   ├── data/            # Données JSON locales (Quartiers, KPI, Mocks)
│   │   ├── services/        # Service de données (Mock API Service)
│   │   └── App.tsx          # Point d'entrée principal
│   ├── index.css            # Design system (TailwindCSS)
│   └── package.json         # Dépendances frontend
│
└── README.md
```

---

## 📊 Données

Les données affichées proviennent de sources Open Data Paris (DVF, INSEE, Ville de Paris) et ont été intégrées directement sous forme de fichiers JSON dans l'application pour permettre un fonctionnement autonome sans backend.

---

## 👥 Équipe

Réalisé par Chentouf Rayan, Yacine Bakour, Nawfel Younes et Alexandre Kosutic dans le cadre du cursus **Data Engineering — EFREI Paris**.
