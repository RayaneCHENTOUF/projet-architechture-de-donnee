# KPI de Confort Urbain — Paris, 80 Quartiers

---

## Données et notations

Pour chaque quartier **q** parmi les 80 quartiers de Paris :

- **S(q)** = surface du quartier en m²
- **N_prop(q)** = nombre de signalements Propreté/Voirie dans q
- **N_incivil(q)** = nombre de signalements Incivilités dans q
- **N_projets(q)** = nombre de projets d'aménagement dans q
- **L(q)** = loyer moyen de référence au m² dans q (2025, non meublé, 2 pièces)
- **rang(x)** = rang centile de x parmi les 80 quartiers → valeur entre 0 et 1

---

## S1 — Score de Propreté

**Types de signalements retenus :** "Propreté" + "Voirie et espace public"

```
                N_prop(q)
d_prop(q)  =  ─────────────
                  S(q)

S1(q)  =  10 * (1 - rang(d_prop(q)))
```

> Moins il y a de signalements rapportés à la surface → score plus élevé

---

## S2 — Score d'Incivilités

**Types retenus :** "Objets abandonnés" + "Graffitis/Tags" + "Mobiliers urbains"

Chaque signalement reçoit un poids de gravité **w** selon son sous-type :

```
Sous-type                              w
─────────────────────────────────────────
Objets encombrants, cartons, gravats   1.0
Graffitis sur rideau métallique        1.3
Graffitis sur mur / façade             1.5
Déjections canines                     1.5
Épanchement d'urine                    2.0
Objets infestés (punaises de lit)      3.0
```

```
I_incivil(q)  =  w(s1) + w(s2) + w(s3) + ... + w(sn)
                 (somme des poids de tous les signalements dans q)

                  I_incivil(q)
d_incivil(q)  =  ─────────────
                     S(q)

S2(q)  =  10 * (1 - rang(d_incivil(q)))
```

> Moins la pression d'incivilité pondérée est forte → score plus élevé

---

## S3 — Score d'Aménagement Urbain

**Catégories de projets retenues :** depuis `parissetransforme`

Chaque projet reçoit un poids **w** selon sa catégorie :

```
Catégorie                          w
─────────────────────────────────────
Espace public / Nature en ville    2.0
Écoles et crèches                  1.8
Propreté (Stations Trilib…)        1.5
Sécurité et Prévention             1.3
Sport                              1.0
```

```
I_am(q)  =  w(p1) + w(p2) + w(p3) + ... + w(pm)
            (somme des poids de tous les projets dans q)

              I_am(q)
d_am(q)  =  ──────────
               S(q)

S3(q)  =  10 * rang(d_am(q))
```

> Plus il y a de projets d'aménagement rapportés à la surface → score plus élevé

---

## S4 — Score d'Accessibilité du Logement

**Données :** Loyer de référence 2025, non meublé, 2 pièces. Moyenne sur les 4 époques de construction.

```
             L(q, époque1) + L(q, époque2) + L(q, époque3) + L(q, époque4)
L_moy(q)  =  ──────────────────────────────────────────────────────────────
                                          4


L_med  =  médiane de { L_moy(q) pour tous les q }   (médiane parisienne)


             | L_moy(q) - L_med |
delta(q)  =  ────────────────────
                    L_med


                         delta(q)
S4(q)  =  10 *  (1  -  ─────────────────────────)
                         max( delta(q') , q' ∈ Q )
```

> Le score est maximal quand le loyer est proche de la médiane parisienne.
> Un loyer très haut (inaccessible) **ou** très bas (quartier dégradé) → score faible.

---

## KPI Final — Indice de Confort Urbain

### Formule

```
KPI(q)  =  S1(q)^0.35  *  S2(q)^0.30  *  S3(q)^0.20  *  S4(q)^0.15
```

### Poids

```
Composante       Exposant   Justification
────────────────────────────────────────────────────────────────────
S1  Propreté       0.35     Critère n°1 du confort selon les habitants
S2  Incivilités    0.30     Impact direct sur la qualité de vie
S3  Aménagement    0.20     Investissements de la Ville pour les habitants
S4  Loyer          0.15     L'accessibilité contribue, mais ne définit pas tout
────────────────────────────────────────────────────────────────────
Somme              1.00
```

### Pourquoi multiplier (et non additionner) ?

```
Exemple :        S1    S2    S3    S4    Somme ponderée    KPI (géométrique)
─────────────────────────────────────────────────────────────────────────────
Quartier A       10     0    10    10         7.0  ← trop haut        ≈ 0  ✓
Quartier B        6     6     6     6         6.0                      6.0
```

Un quartier avec **S2 = 0** (incivilités catastrophiques) obtient un **KPI ≈ 0**,
même s'il est parfait sur les 3 autres axes.

→ C'est le même principe que l'Indice de Développement Humain (IDH) de l'ONU :
**un seul axe catastrophique suffit à plomber le score global.**

### Plage du KPI

```
0  ──────────────────────────────────────────────  10
Très inconfortable                     Très confortable
```
