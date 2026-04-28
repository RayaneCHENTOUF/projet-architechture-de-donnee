# Audit Phase 1 - Nettoyage Structurel du Projet

Date: 2026-04-26  
Scope: structure, nommage, coherence des KPI Gold, SQL, documentation.

## 1) Resume executif

Le projet contient les briques metier importantes (notebooks de calcul KPI, zone Gold, scripts SQL), mais la coherence transversale est insuffisante pour une industrialisation propre. Les principaux risques ne sont pas dans les formules KPI, mais dans:

- la divergence de formats CSV,
- les conventions de nommage heterogenes,
- la documentation fragmentee et partiellement obsolete,
- l'absence de README racine consolidant l'architecture et les flux.

Conclusion Phase 1: la base est exploitable, mais un nettoyage de standardisation est necessaire avant d'aller plus loin sur API/front/deploiement.

## 2) Inventaire rapide

Top-level detecte:

- `.env`, `.git`, `.gitignore`, `.venv`
- `api`, `data`, `docs`, `front`, `pipeline`, `sql`
- `guide_datasets_attributs.md`, `implementation_plan.md`, `plan_indicateurs_rayan.md`, `README.md`

Points notables:

- `README.md` existe mais est vide.
- `api` et `front` existent (contenu non structure dans cet audit).
- Les notebooks KPI principaux sont presents dans `pipeline/silver`.

## 3) Audit coherence data/gold

### 3.1 Fichiers Gold identifies

- `gold_kpi_confort_urbain.csv`
- `kpi_comparaison_achat_location.csv`
- `kpi_evolution_achat_prix_m2.csv`
- `kpi_evolution_location_loyer.csv`
- `kpi_loyers.csv`
- `kpi_loyer_par_arrondissement.csv`
- `kpi_prix_m2_arrondissement.csv`
- `kpi_repartition_logements_sociaux.csv`
- `kpi_score_surete_arrondissement_agrege_depuis_iris.csv`
- `kpi_score_surete_iris.csv`

### 3.2 Ecarts de format et schema

| Axe                | Constat                                                                                                                          | Impact                                                        |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Separateur CSV     | `gold_kpi_confort_urbain.csv` utilise `;`, la majorite des autres fichiers utilisent `,`                                         | Risque de lecture incoherente (ETL, SQL COPY, scripts pandas) |
| Cle geographique   | `arrondissement` present dans la majorite des KPI, mais heterogene selon formats amont (01 vs 1 selon sources)                   | Jointures fragiles si non normalisees                         |
| Temporalite        | Certaines tables ont `annee`, d'autres non (`kpi_loyers.csv`, `kpi_loyer_par_arrondissement.csv`, `gold_kpi_confort_urbain.csv`) | Difficulte de comparaison temporelle uniforme                 |
| Nommage semantique | `nb_ventes` vs `nb_transactions` pour une meme notion                                                                            | Ambiguite metier et mapping API/BI                            |
| Redondance         | KPI de loyer en double granularite (`kpi_loyers.csv` vs `kpi_loyer_par_arrondissement.csv`)                                      | Risque d'usage non maitrise de la mauvaise table              |

## 4) Audit SQL vs Gold

Fichiers SQL analyses:

- `sql/create_tables_kpi_rayan.sql`
- `sql/create_tables_gold_kpi_confort.sql`

Points constates:

- Les tables `fact_kpi_*` couvrent globalement les KPI majeurs (prix, surete, confort, comparaison).
- Plusieurs definitions se recouvrent entre les deux scripts (redondance DDL).
- Avec `IF NOT EXISTS`, l'execution ne casse pas toujours, mais la maintenance devient confuse.

Mapping principal observe:

| Table SQL                             | KPI Gold cible                                           |
| ------------------------------------- | -------------------------------------------------------- |
| `fact_kpi_prix_m2_arrondissement`     | `kpi_prix_m2_arrondissement.csv`                         |
| `fact_kpi_surete_arrondissement`      | `kpi_score_surete_arrondissement_agrege_depuis_iris.csv` |
| `fact_kpi_surete_iris`                | `kpi_score_surete_iris.csv`                              |
| `fact_kpi_confort_quartier`           | `gold_kpi_confort_urbain.csv`                            |
| `fact_kpi_comparaison_achat_location` | `kpi_comparaison_achat_location.csv`                     |

## 5) Audit documentation

| Element             | Constat                                                                              | Impact                                                         |
| ------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| `README.md`         | vide                                                                                 | Pas de point d'entree projet pour un nouveau membre ou un jury |
| `docs/kpi_rayan.md` | references `data/silver/...` alors que les sorties finales sont en `data/gold/...`   | Documentation contradictoire                                   |
| Docs KPI multiples  | recouvrement entre `kpi_nawfel.md`, `kpi_yacine.md`, `KPI_confort_urbain 1.md`, etc. | Difficulte a identifier la version de reference                |

## 6) Score de maturite (0-5)

| Axe                                   | Score | Justification courte                                       |
| ------------------------------------- | ----: | ---------------------------------------------------------- |
| Structure projet                      |     3 | Dossiers presents mais conventions non stabilisees         |
| Qualite data Gold                     |     3 | KPI produits, mais schemas/format pas totalement homogenes |
| Coherence KPI metier                  |     4 | Formules et calculs globalement en place                   |
| Couche SQL                            |     3 | DDL presents, redondance et couplage CSV a fiabiliser      |
| Documentation                         |     2 | Documentation riche mais dispersee, README vide            |
| Industrialisation (API/front/runbook) |     1 | Base encore insuffisamment operationalisee                 |

## 7) Priorisation de nettoyage

### P0 (immediat - faible risque)

- Definir et appliquer un standard unique CSV Gold (separateur, encodage, arrondi).
- Normaliser la cle `arrondissement` en `VARCHAR(2)` avec zero-padding (`01`..`20`) partout.
- Unifier les noms de colonnes semantiques (`nb_transactions` ou `nb_ventes`, un seul choix).
- Corriger `docs/kpi_rayan.md` pour pointer vers `data/gold/...`.
- Remplir `README.md` avec: architecture, flux Bronze->Silver->Gold, liste KPI, comment lancer.

### P1 (court terme - risque modere)

- Supprimer la redondance des DDL SQL (fichier unique ou separation claire par domaine sans overlap).
- Introduire un contrat schema par KPI Gold (colonnes obligatoires + types + cle unique).
- Clarifier la relation entre `kpi_loyers.csv` et `kpi_loyer_par_arrondissement.csv` (source de verite).

### P2 (apres stabilisation)

- Ajouter des scripts de validation automatique (schema + quality checks) avant publication Gold.
- Poser une structure API/front minimale branchee sur les tables `fact_kpi_*`.
- Mettre en place un data catalog centralise (source, frequence, limites, responsable par KPI).

## 8) Checklist executable (phase 2)

- [ ] Ecrire le README racine (vue globale projet)
- [ ] Fixer conventions globales (fichier de standards)
- [ ] Harmoniser colonnes KPI Gold (`arrondissement`, noms de compteurs)
- [ ] Harmoniser format CSV Gold (un seul separateur)
- [ ] Corriger les docs KPI obsoletes (`data/silver` -> `data/gold`)
- [ ] Consolider SQL DDL sans duplication
- [ ] Ajouter script de controle de schema Gold
- [ ] Generer rapport de non-regression KPI apres nettoyage

## 9) Garde-fous anti-perte (important)

Pour ne rien perdre des elements metier importants:

- Ne pas modifier la logique des notebooks KPI dans un premier temps.
- Separarer "refactor structure" et "refactor calcul" dans des commits distincts.
- Conserver les formules et justifications de sources dans une doc canonique unique.
- Comparer avant/apres par KPI: nombre de lignes, cles, stats (medianes/moyennes), champs obligatoires.

Fin Phase 1.
