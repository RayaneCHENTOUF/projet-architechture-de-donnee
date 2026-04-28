# KPI de Confort Urbain — Paris, 80 Quartiers
## Documentation Technique du Pipeline Gold

**Sources de données :** `dans-ma-rue.csv` · `parissetransforme.csv` · `logement-encadrement-des-loyers.csv` · `quartier_paris.csv` · `silver_gares.csv`
**Granularité :** 1 ligne = 1 quartier parmi les 80 quartiers administratifs de Paris
**Loyer médian parisien observé :** 29,15 €/m² (2025, non meublé, 2 pièces)

---

## Données et notations

Pour chaque quartier **q** parmi les **80 quartiers de Paris** (référentiel `quartier_paris.csv`) :

| Notation | Description | Source |
|---|---|---|
| **S(q)** | Surface du quartier en m² (colonne `SURFACE`) | `quartier_paris.csv` |
| **N_prop(q)** | Nombre de signalements Propreté/Voirie dans q | `dans-ma-rue.csv` |
| **N_incivil(q)** | Somme pondérée des signalements Incivilités dans q | `dans-ma-rue.csv` |
| **N_projets(q)** | Somme pondérée des projets d'aménagement dans q | `parissetransforme.csv` |
| **L(q)** | Loyer moyen de référence au m² dans q (2025, non meublé, 2 pièces) | `logement-encadrement-des-loyers.csv` |
| **G(q)** | Nombre de gares (métro, RER, tram) situées à moins de 800m du centre du quartier | `silver_gares.csv` |
| **rang(x)** | Rang centile de x parmi les 80 quartiers → valeur entre 0 et 1 | Calculé par `pandas.rank(pct=True)` |

> **Jointure géographique :** Les signalements `dans-ma-rue` sont rattachés aux quartiers via la colonne `CONSEIL DE QUARTIER` (matching sur nom normalisé ↔ `L_QU` du référentiel). Les loyers sont joints via le code INSEE du quartier (`Numéro INSEE du quartier` = `C_QUINSEE`). Les projets `parissetransforme` sont joints via le code postal (`75001` → arrondissement `1`) puis distribués uniformément sur les 4 quartiers de l'arrondissement.

---

## S1 — Score de Propreté

**Source :** `dans-ma-rue.csv`
**Types de signalements retenus :** `"Propreté"` + `"Voirie et espace public"`

```
              N_prop(q)
d_prop(q) = ─────────────       (densité de signalements / m²)
                S(q)

S1(q) = 10 * (1 - rang(d_prop(q)))
```

> Moins il y a de signalements rapportés à la surface → score plus élevé

**Valeurs observées (extrait) :**
- Quartiers ruraux/résidentiels (16ème, 7ème) : d_prop faible → S1 élevé
- Quartiers très denses et touristiques (9ème, 1er) : d_prop fort → S1 faible

---

## S2 — Score d'Incivilités

**Source :** `dans-ma-rue.csv`
**Types retenus :** `"Objets abandonnés"` + `"Graffitis, tags, affiches et autocollants"` + `"Mobiliers urbains"`

Chaque signalement reçoit un poids de gravité **w** selon son sous-type :

```
Sous-type (détecté par mots-clés dans SOUS TYPE DECLARATION)  w
────────────────────────────────────────────────────────────────
Objets infestés (punaises de lit)                             3.0
Épanchement d'urine                                           2.0
Graffitis sur mur / façade / rideau métallique                1.5
Déjections canines                                            1.5
Graffitis (autres)                                            1.3
Objets encombrants, cartons, gravats                          1.0
Autres (défaut)                                               1.0
```

```
I_incivil(q)  =  w(s1) + w(s2) + ... + w(sn)
                 (somme des poids de tous les signalements dans q)

                  I_incivil(q)
d_incivil(q)  =  ─────────────
                     S(q)

S2(q)  =  10 * (1 - rang(d_incivil(q)))
```

> Moins la pression d'incivilité pondérée est forte → score plus élevé

**Effet multiplicatif observé :** Belleville (20ème) présente `S2 ≈ 0.01`, ce qui ramène son KPI final à `0.27` malgré un excellent S3 = 10.0.

---

## S3 — Score d'Aménagement Urbain

**Source :** `parissetransforme.csv`
**Volume :** 3 262 projets référencés (dont 3 257 uniques après déduplication)

Chaque projet reçoit un poids **w** selon sa catégorie (`Catégorie`) :

```
Catégorie (colonne "Catégorie")                w     Nb projets observés
───────────────────────────────────────────────────────────────────────
Espace public / Nature en ville               2.0         408
Écoles et crèches                             1.8         333
Propreté (Stations Trilib, collecte…)         1.5         502
Sécurité et Prévention                        1.3          39
Sport                                         1.0          90
Autres catégories (Attractivité, Culture…)    0.5       1 890
```

```
I_am(q)   =  w(p1) + w(p2) + ... + w(pm)
             (somme des poids de tous les projets dans les 4 quartiers de l'arrondissement,
              répartis uniformément car les projets sont géolocalisés au niveau arrondissement)

              I_am(q)
d_am(q)  =  ──────────
               S(q)

S3(q)  =  10 * rang(d_am(q))
```

> Plus il y a de projets d'aménagement rapportés à la surface → score plus élevé

**Note :** Les arrondissements les plus denses en projets sont le 20ème (337 projets) et le 19ème (299 projets). Les plus aisés (16ème, 7ème) sont en queue de classement sur cet indicateur.

---

## S4 — Score d'Accessibilité du Logement

**Source :** `logement-encadrement-des-loyers.csv`
**Filtre :** Année 2025, type `"non meublé"`, 2 pièces principales, toutes époques de construction.
**Volume utilisé :** ~17 920 lignes de loyers encadrés par Paris.

```
             L(q, Avant 1946) + L(q, 1946-1970) + L(q, 1971-1990) + L(q, Après 1990)
L_moy(q)  =  ────────────────────────────────────────────────────────────────────────
                                              4

L_med  =  médiane de { L_moy(q) pour tous les q } = 29,15 €/m²   (médiane parisienne 2025)

             | L_moy(q) - L_med |
delta(q)  =  ────────────────────
                    L_med

                        delta(q)
S4(q)  =  10 * (1  -  ─────────────────────────)
                        max( delta(q') , q' ∈ Q )
```

> Le score est maximal quand le loyer est proche de la médiane parisienne (29,15 €/m²).
> Un loyer très haut (quartiers chics, inaccessibles) **ou** très bas (quartiers dégradés) → score faible.

**Imputation :** Les quartiers sans données de loyer directes sont imputés par la médiane de leur arrondissement.

---

---

## S5 — Score de Connectivité Transport

**Source :** `silver_gares.csv` (filtré depuis la donnée régionale)
**Méthodologie :** Rayon d'accessibilité piétonne locale (10 min de marche).

Pour chaque quartier, on calcule la distance à vol d'oiseau entre le centre du quartier (centroïde) et l'ensemble des gares (SNCF / RATP / Tram) de Paris. 

```
G(q) = Nombre de stations situées à moins de 0.8 km (800 m) du centre de q

S5(q)  =  10 * rang( G(q) )
```

> Plus un quartier est entouré de stations de transport lourd à courte distance, plus son score grimpe.

**Valeurs observées :**
- L'hypercentre présente logiquement des densités record de stations de métro dans un rayon de 800m.
- Les grands quartiers excentrés sont défavorisés sur ce critère très local.

---

## KPI Final — Indice de Confort Urbain

### Formule

```
KPI(q)  =  S1(q)^0.30  *  S2(q)^0.25  *  S3(q)^0.15  *  S4(q)^0.15  *  S5(q)^0.15
```

### Poids et justification

```
Composante       Exposant   Justification métier
────────────────────────────────────────────────────────────────────────────
S1  Propreté       0.30     Critère n°1 de satisfaction des habitants parisiens
S2  Incivilités    0.25     Impact direct sur la sécurité perçue et la qualité de vie
S3  Aménagement    0.15     Indicateur prospectif : investissements de la Ville
S4  Loyer          0.15     Dimension économique : accessibilité au logement
S5  Transport      0.15     Dimension mobilités : accessibilité à pied (<800m)
────────────────────────────────────────────────────────────────────────────
Somme              1.00
```

### Pourquoi une moyenne géométrique (et non additive) ?

```
Exemple :        S1    S2    S3    S4    Somme pondérée    KPI (géométrique)
─────────────────────────────────────────────────────────────────────────────
Quartier A       10     0    10    10         7.0  ← trop haut        ≈ 0  ✓
Quartier B        6     6     6     6         6.0                      6.0
```

Un quartier avec **S2 = 0** (incivilités catastrophiques) obtient un **KPI ≈ 0**,
même s'il est parfait sur les 3 autres axes.

→ C'est le même principe que l'**Indice de Développement Humain (IDH) de l'ONU** :
**un seul axe catastrophique suffit à plomber le score global.**

### Plage du KPI

```
0  ──────────────────────────────────────────────  10
Très inconfortable                     Très confortable
```

---

## Résultats Observés — Classement des 80 Quartiers

### Top 10 (Quartiers les plus confortables)

| Rang | Quartier | Arr. | S1_proprete | S2_incivilites | S3_amenagement | S4_accessibilite | S5_transport | KPI_confort_urbain |
|---|---|---|---|---|---|---|---|---|
| 1 | Porte-Saint-Denis | 10 | 5.94 | 5.94 | 9.75 | 10.00 | 8.56 | 7.31 |
| 2 | Sainte-Avoie | 3 | 5.94 | 5.94 | 8.75 | 10.00 | 9.44 | 7.29 |
| 3 | Porte-Saint-Martin | 10 | 5.94 | 5.94 | 9.12 | 10.00 | 8.25 | 7.19 |
| 4 | Folie-Méricourt | 11 | 5.94 | 5.94 | 9.62 | 10.00 | 7.69 | 7.18 |
| 5 | Saint-Merri | 4 | 5.94 | 5.94 | 8.62 | 10.00 | 8.25 | 7.13 |
| 6 | Sainte-Marguerite | 11 | 5.94 | 5.94 | 9.00 | 10.00 | 6.94 | 7.00 |
| 7 | Chaussée-d'Antin | 9 | 5.94 | 5.94 | 6.12 | 10.00 | 10.00 | 6.97 |
| 8 | Gaillon | 2 | 5.94 | 5.94 | 6.62 | 10.00 | 8.88 | 6.93 |
| 9 | Notre-Dame | 4 | 5.94 | 5.94 | 7.50 | 10.00 | 7.69 | 6.91 |
| 10 | Arts-et-Métiers | 3 | 5.94 | 5.94 | 6.00 | 10.00 | 9.44 | 6.89 |

### Bottom 10 (Quartiers les moins confortables)

| Rang | Quartier | Arr. | S1_proprete | S2_incivilites | S3_amenagement | S4_accessibilite | S5_transport | KPI_confort_urbain | Axe pénalisant principal |
|---|---|---|---|---|---|---|---|---|---|
| 71 | Monnaie | 6 | 0.75 | 0.37 | 9.38 | 10.00 | 8.25 | 1.95 | Faible propreté/investissements locaux ou loyer |
| 72 | Halles | 1 | 5.94 | 5.94 | 1.12 | 0.01 | 9.44 | 1.90 | Accessibilité loyer critique |
| 73 | Chaillot | 16 | 0.88 | 0.88 | 1.88 | 10.00 | 6.25 | 1.90 | S1 / S2 / S3 très faibles |
| 74 | Jardin-des-Plantes | 5 | 0.62 | 0.62 | 4.12 | 10.00 | 5.44 | 1.74 | S1 / S2 très faibles |
| 75 | Porte-Dauphine | 16 | 1.75 | 1.37 | 0.62 | 10.00 | 0.94 | 1.67 | S1 / S2 / S3 / S5 très faibles (excentré) |
| 76 | Val-de-Grace | 5 | 0.50 | 0.50 | 5.50 | 10.00 | 0.94 | 1.23 | Transport et propreté perçue très bas |
| 77 | Sorbonne | 5 | 0.25 | 0.25 | 8.88 | 10.00 | 6.25 | 1.20 | Propreté et incivilités extrêmes (S1/S2) |
| 78 | Gros-Caillou | 7 | 0.37 | 1.00 | 0.75 | 10.00 | 0.69 | 0.95 | Propreté, aménagement urbain, transport (excentré) |
| 79 | Faubourg-Montmartre | 9 | 0.01 | 0.12 | 8.12 | 10.00 | 8.00 | 0.40 | Propreté et incivilités virtuellement nuls |
| 80 | Belleville | 20 | 0.12 | 0.01 | 10.00 | 10.00 | 2.25 | 0.38 | Incivilités écrasantes effondrant le KPI |

---

## Limites et Pistes d'Amélioration

### Limites connues
- **Jointure sur nom de quartier** : seulement 10,5% des signalements `dans-ma-rue` ont pu être rattachés à un quartier précis (le reste ne dispose pas de `CONSEIL DE QUARTIER` renseigné). Le pipeline utilise uniquement les lignes avec jointure réussie.
- **S3 au niveau arrondissement** : `parissetransforme` ne donne pas la localisation infra-arrondissement. Le score est donc identique pour les 4 quartiers d'un même arrondissement, modulé uniquement par leur surface.
- **Biais de signalement** : Les quartiers avec plus de résidents connectés génèrent plus de signalements (notamment les bobos du centre). Un quartier "silencieux" peut avoir un S1 artificiellement bon.

### Améliorations possibles
- Utiliser `geo_point_2d` (coordonnées GPS dans les CSV) pour une jointure spatiale précise via `GeoPandas`
- Pondérer le nombre de signalements par la **population du quartier** (données `RECENSEMENT_IRIS_POPULATION`)
- Ajouter un **score de démographie** (densité, part des jeunes, taux d'étrangers) depuis la table `silver_demographie`
- Intégrer une **dimension temporelle** (évolution du KPI par année) grâce à la colonne `ANNEE DECLARATION`

---

*Document généré automatiquement à partir du pipeline `gold_kpi_confort_urbain.py` — Projet Urban Data Explorer*
*Données : Paris Open Data — Millésime 2025*
