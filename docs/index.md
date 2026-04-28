# 📚 Index de la documentation — Urban Data Explorer

> Ce fichier centralise tous les documents de référence du projet.

---

## 🗂️ Structure de la documentation

```
docs/
├── index.md                          ← Ce fichier
├── architecture.md                   ← Architecture Medallion Bronze→Silver→Gold
├── silver_pipeline_documentation.md  ← Détail des scripts de nettoyage Silver
└── gold_kpi_documentation.md         ← Détail des KPI Gold et leurs formules
```

---

## 📄 Documents disponibles

### 🏗️ [Architecture](architecture.md)
Description complète de l'architecture Medallion du projet :
- Schéma de flux de données de Bronze à Gold
- Détail de chaque couche (Bronze, Silver, Gold, SQL)
- Conventions de nommage
- Flux d'exécution complet

---

### 🥈 [Pipeline Silver](silver_pipeline_documentation.md)
Documentation des scripts de transformation Bronze → Silver :

| Script | Domaine | Sorties |
|--------|---------|---------|
| `clean_immobilier.py` | Immobilier | `dvf_clean.csv`, `hlm_clean.csv`, `encadrement_loyers_clean.csv` |
| `clean_geographie.py` | Géographie | `quartiers_clean.csv`, `iris_clean.csv`, `arrondissements_clean.csv` |
| `clean_surete.py` | Sûreté | `delinquance_clean.csv`, `commissariats_clean.csv`, `cameras_clean.csv` |
| `clean_confort.py` | Confort urbain | `dans_ma_rue_clean.csv`, `gares_clean.csv`, `paris_se_transforme_clean.csv` |

→ **[Lire la documentation Silver complète](silver_pipeline_documentation.md)**

---

### 🥇 [KPI Gold](gold_kpi_documentation.md)
Documentation des KPI calculés par les scripts Gold :

| KPI | Script | Fichier de sortie |
|-----|--------|-------------------|
| Prix m² par quartier | `gold_kpi_prix_m2_quartier_annuel.py` | `kpi_prix_m2_quartier_annuel.csv` |
| Comparaison achat/location (arrondissement) | `gold_kpi_comparaison_achat_location_arrondissement.py` | `kpi_comparaison_achat_location_arrondissement.csv` |
| Comparaison achat/location (quartier, estimé) | `gold_kpi_comparaison_achat_location_quartier.py` | `kpi_comparaison_achat_location_quartier_estime.csv` |
| Loyers de référence par quartier | `gold_kpi_loyers_quartier.py` | `kpi_loyers_quartier.csv` |
| Logements sociaux (HLM) | `gold_kpi_repartition_hlm_arrondissement.py` | `kpi_repartition_logements_sociaux.csv` |
| Confort urbain | `gold_kpi_confort_urbain.py` | `gold_kpi_confort_urbain.csv` |
| Score sûreté par quartier | `gold_kpi_surete_quartier.py` | `kpi_score_surete_quartier_estime_depuis_iris.csv` |

→ **[Lire la documentation Gold complète](gold_kpi_documentation.md)**

---

## 🚀 Démarrage rapide

```bash
# 1. Nettoyage des données brutes (Bronze → Silver)
python src/pipeline/silver/run_silver.py

# 2. Calcul des KPI (Silver → Gold)
python src/pipeline/gold/run_gold.py

# 3. Injection SQL
# Exécuter les scripts dans sql/ sur votre base de données
```

---

## 🔗 Ressources liées

| Ressource | Chemin |
|-----------|--------|
| README principal | [`README.md`](../README.md) |
| Configuration des chemins | [`src/utils/config.py`](../src/utils/config.py) |
| Scripts SQL | [`sql/`](../sql/) |
| Notebooks exploratoires | [`notebooks/`](../notebooks/) |
| Données Gold (CSV) | [`data/gold/`](../data/gold/) |

---

## 📌 Conventions clés

| Règle | Valeur |
|-------|--------|
| Format `arrondissement` | String 2 chiffres, ex : `"01"`, `"20"` |
| Format `code_insee_quartier` | String 7 chiffres, préfixe `751`, ex : `"7510101"` |
| Fichiers Silver | Suffixe `_clean.csv` |
| Fichiers Gold | Préfixe `kpi_` |
| Couche de référence | Silver (Gold lit Silver en priorité, Bronze en fallback) |

---

*Dernière mise à jour : Avril 2026 — Projet EFREI Data Engineering*
