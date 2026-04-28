# Guide des datasets présents et de leurs attributes

1.  Transactions immobilières – DVF (Demands de Valeurs Foncières)

Source officielle des ventes immobilières (prix, surfaces, localisation)
Contient : prix, surface, type de bien, date, coordonnées géographiques…

Télécharger les données DVF (avec géolocalisation)
https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/

Remarque : il s’agit de la version DVF enrichie, plus facile à exploiter qu’avec le fichier brut.

2. Géographie administrative – IRIS

Découpage officiel des zones IRIS (polygons) utilisé par l’INSEE
Sert à agréger toutes les données au bon niveau géographique.

Contours des IRIS (lien de telechargement)
https://opendata.iledefrance.fr/api/explore/v2.1/catalog/datasets/iris/exports/csv?lang=fr&refine=dep%3A%2275%22&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B

3. Loyers de référence – Paris
   Jeux de données officiels des loyers par quartier à Paris
   Contient : loyers de référence, loyers majorés, loyers minorés + géométrie de quartier.

Encadrement des loyers – Paris Data
https://opendata.paris.fr/explore/dataset/logement-encadrement-des-loyers/

4. Logement social – Paris

Données du parc social / logements sociaux financés à Paris
Sert à mesurer la part de logement social par zone

Logements sociaux financés à Paris
https://opendata.paris.fr/explore/dataset/logement-social-finances-a-paris/

(c’est exactement le dataset dont tu m’as parlé, donc oui il est retenu)

5.  recencement des transport en ile de france (dataset externe, non present dans csv)
    https://data.iledefrance-mobilites.fr/explore/dataset/emplacement-des-gares-idf/export/?utm_source=chatgpt.com&location=8,48.69888,2.33131&basemap=jawg.streets

6.signalement de delinquance par la police (present dans csv)
https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales

7.consolation energetique par iris (dataset externe, non present dans csv) :
https://www.data.gouv.fr/datasets/consommation-annuelle-delectricite-et-gaz-par-iris

## Objectif

Ce document résume les datasets disponibles dans le project, leurs colonnes principles, les attributes les plus importants pour l'analyse, et la façon de les relier.

Source utilisée : documentation_urban_data_explorer.md + entêtes réelles des fichiers CSV dans le dossier csv.

## 1) Vue d'ensemble des datasets présents

| Fichier                                                           | Dataset                             | Rôle                                                       | Statut project |
| ----------------------------------------------------------------- | ----------------------------------- | ---------------------------------------------------------- | -------------- |
| csv/75.csv                                                        | DVF (transactions immobilières)     | Dataset coeur (prix, surface, type, date, géolocalisation) | Prioritaire    |
| csv/iris.csv                                                      | IRIS (INSEE)                        | Référentiel géographique (zones IRIS)                      | Prioritaire    |
| csv/logement-encadrement-des-loyers.csv                           | Loyers de référence Paris           | Comparer achat vs location                                 | Prioritaire    |
| csv/logements-sociaux-finances-a-paris.csv                        | Logements sociaux financés          | Contexte urbain/politique publique                         | Prioritaire    |
| csv/arrondissements.csv                                           | Limites administratives de Paris    | Jointures/cartographie d'appui                             | Support        |
| csv/donnee-data.gouv-2025-geographie2025-produit-le2026-02-03.csv | Délinquance signalée (par code géo) | Indicateur complémentaire (optionnel)                      | Optionnel      |

## 2) Attributs importants par dataset

### A. DVF - csv/75.csv

Colonnes disponibles (principales) :
id_mutation, date_mutation, nature_mutation, valeur_fonciere, adresse_numero, adresse_nom_voie, code_postal, nom_commune, type_local, surface_reelle_bati, nombre_pieces_principales, surface_terrain, longitude, latitude.

Attributs les plus importants :

| Attribut                  | Importance | Pourquoi                                       |
| ------------------------- | ---------- | ---------------------------------------------- |
| valeur_fonciere           | Critique   | Calcul du prix et du prix au m2                |
| surface_reelle_bati       | Critique   | Dénominateur du prix au m2                     |
| date_mutation             | Critique   | Analyse temporelle (evolution)                 |
| type_local                | Elevee     | Segmentation par type de bien                  |
| longitude, latitude       | Critique   | Jointure spatiale avec IRIS (point-in-polygon) |
| code_postal               | Elevee     | Contrôles territoriaux / agrégations           |
| nombre_pieces_principales | Moyenne    | Analyse typologique complémentaire             |

KPI direct :

- prix_m2 = valeur_fonciere / surface_reelle_bati

### B. IRIS - csv/iris.csv

Colonnes disponibles :
Geo Shape, DEP, INSEE_COM, NOM_COM, IRIS, CODE_IRIS, NOM_IRIS, TYP_IRIS, Geo Point, ID.

Attributs les plus importants :

| Attribut  | Importance | Pourquoi                                      |
| --------- | ---------- | --------------------------------------------- |
| CODE_IRIS | Critique   | Clé géographique cible pour agréger les KPI   |
| Geo Shape | Critique   | Polygone nécessaire pour la jointure spatiale |
| NOM_IRIS  | Elevee     | Lisibilité dans cartes/tableaux               |
| TYP_IRIS  | Moyenne    | Catégorisation urbaine                        |
| INSEE_COM | Elevee     | Contrôle de cohérence communale               |

### C. Loyers - csv/logement-encadrement-des-loyers.csv

Colonnes disponibles :
Année, Secteurs géographiques, Numéro du quartier, Nom du quartier, Nombre de pièces principales, Epoque de construction, Type de location, Loyers de référence, Loyers de référence majorés, Loyers de référence minorés, Ville, Numéro INSEE du quartier, geo_shape, geo_point_2d.

Attributs les plus importants :

| Attribut                     | Importance | Pourquoi                        |
| ---------------------------- | ---------- | ------------------------------- |
| Loyers de référence          | Critique   | Base du loyer de comparaison    |
| Loyers de référence majorés  | Elevee     | Encadrement haut                |
| Loyers de référence minorés  | Elevee     | Encadrement bas                 |
| Nombre de pièces principales | Elevee     | Comparaison loyer par typologie |
| Année                        | Critique   | Alignement temporel avec DVF    |
| geo_shape / geo_point_2d     | Critique   | Rattachement spatial aux zones  |
| Numéro INSEE du quartier     | Elevee     | Clé territoriale complémentaire |

KPI direct :

- tension_immobiliere = prix_m2 / loyer_m2
- rentabilite_locative_brute = (loyer_mensuel \* 12) / prix_bien

### D. Logements sociaux - csv/logements-sociaux-finances-a-paris.csv

Colonnes disponibles :
Identifiant livraison, Adresse du programme, Code postal, Ville, Année du financement - agrément, Bailleur social, Nombre total de logements financés, Dont nombre de logements PLA I, Dont nombre de logements PLUS, Dont nombre de logements PLUS CD, Dont nombre de logements PLS, Mode de réalisation, Commentaires, Arrondissement, Nature de programme, Coordonnée en X (L93), Coordonnée en Y (L93), geo_shape, geo_point_2d.

Attributs les plus importants :

| Attribut                                     | Importance | Pourquoi                                   |
| -------------------------------------------- | ---------- | ------------------------------------------ |
| Nombre total de logements financés           | Critique   | Mesure principale de l'effort social       |
| Arrondissement                               | Critique   | Agrégation territoriale simple             |
| Année du financement - agrément              | Elevee     | Analyse temporelle                         |
| Bailleur social                              | Moyenne    | Analyse acteur/opérateur                   |
| Coordonnée en X (L93), Coordonnée en Y (L93) | Elevee     | Géolocalisation (si conversion nécessaire) |
| geo_shape / geo_point_2d                     | Elevee     | Jointures spatiales                        |

### E. Arrondissements - csv/arrondissements.csv (support)

Colonnes utiles :
Numéro d'arrondissement, Numéro d'arrondissement INSEE, Nom de l'arrondissement, Surface, Périmètre, Geometry.

Utilité :

- cartographie de référence Paris,
- jointures administratives,
- normalisation des libellés d'arrondissement.

### F. Délinquance signalée - csv/donnee-data.gouv-2025-geographie2025-produit-le2026-02-03.csv (optionnel)

Colonnes disponibles :
CODGEO_2025, annee, indicateur, unite_de_compte, nombre, taux_pour_mille, est_diffuse, insee_pop, insee_pop_millesime, insee_log, insee_log_millesime, complement_info_nombre, complement_info_taux.

Attributs utiles (si activé plus tard) :

- CODGEO_2025,
- annee,
- indicateur,
- nombre / taux_pour_mille.

## 3) Clés de liaison recommandées

1. DVF -> IRIS : jointure spatiale

- Point : longitude, latitude (DVF)
- Polygone : Geo Shape (IRIS)
- Résultat : attribution d'un CODE_IRIS à chaque transaction.

2. KPI IRIS -> Loyers

- Priorité : jointure spatiale via geo_shape / geo_point_2d.
- Alternative : correspondance par quartier/INSEE si la géométrie n'est pas exploitable.

3. KPI IRIS -> Logements sociaux

- Option A (simple) : agrégation par Arrondissement.
- Option B (plus précise) : géolocalisation puis affectation par zone IRIS.

## 4) Attributs critiques minimum pour un pipeline fonctionnel

Pour avancer rapidement, garder au minimum ces champs :

- DVF : valeur_fonciere, surface_reelle_bati, date_mutation, type_local, longitude, latitude
- IRIS : CODE_IRIS, Geo Shape
- Loyers : Année, Loyers de référence, Nombre de pièces principales, geo_shape
- Logements sociaux : Nombre total de logements financés, Arrondissement, Année du financement - agrément

## 5) Table de sortie cible (rappel)

Table KPI recommandée : kpi_par_iris

- CODE_IRIS
- prix_m2_moyen
- prix_m2_median
- nb_transactions
- loyer_moyen
- rentabilite
- tension_immobiliere
- nb_logements_sociaux

Ce document est volontairement orienté exécution (ETL + KPI), pour servir de référence pendant le développement.

## 5. KPI attendus (brief projet)

1. **Prix median au m2 par arrondissement**
2. **Variation du prix au m2 dans le temps**
3. **Repartition du parc par type/surface**
4. **tension immobiliere (location vs vente)**

5. **Part de logements sociaux et evolution**
6. **Score de securité ?** **indice de delinquance ?**
7. **score de consomation energetique**
8. **accessibilité transport**

## 6) Calcul des indicateurs (version simplifiee)

Principe commun pour tous les indicateurs :

- choisir la meme zone pour tout le groupe (IRIS ou arrondissement),
- choisir la meme periode (exemple : 2022-2025),
- nettoyer les valeurs aberrantes avant calcul.

### A. 4 indicateurs obligatoires

1. Prix median au m2 par zone

- Donnees : valeur_fonciere, surface_reelle_bati, zone.
- Calcul :
  1. calculer prix_m2 = valeur_fonciere / surface_reelle_bati pour chaque vente,
  2. prendre la mediane des prix_m2 par zone et par annee.
- Resultat : prix_m2_median.

2. Variation du prix au m2 dans le temps

- Donnees : prix_m2 deja calcule, annee, zone.
- Calcul : comparer une annee avec l'annee precedente.
  variation_pct = ((valeur_annee_t - valeur_annee_t_1) / valeur_annee_t_1) x 100
- Resultat : evolution en pourcentage.

3. Repartition du parc par type et surface

- Donnees : type_local, surface_reelle_bati, zone, annee.
- Calcul :
  1. compter le nombre de ventes par type,
  2. compter le nombre de ventes par classe de surface,
  3. convertir en pourcentage du total de ventes.
- Resultat : parts en pourcentage par type et par classe de surface.

4. Tension immobiliere (achat vs location)

- Donnees : prix_m2 (DVF), loyer_m2 (loyers), zone, annee.
- Calcul : tension = prix_m2_moyen / loyer_m2_moyen.
- Resultat : indice de tension (plus c'est eleve, plus l'achat est cher par rapport a la location).

### B. Indicateurs complementaires (delinquance, energie, transport)

1. Niveau de delinquance

- Donnees : taux_pour_mille (ou nombre + population), zone, annee.
- Calcul :
  - si taux_pour_mille existe, prendre la moyenne par zone,
  - sinon calculer (nombre / population) x 1000.
- Resultat : niveau de delinquance comparable entre zones.

2. Indice securite + logement

- Donnees : tension immobiliere + delinquance.
- Calcul simple :
  indice = 0.6 x tension_normalisee + 0.4 x delinquance_normalisee.
- Resultat : score unique pour comparer les zones.

3. Consommation energetique

- Donnees : conso totale + nombre de logements (ou population), zone, annee.
- Calcul :
  - conso_par_logement = conso_totale / nb_logements,
  - ou conso_par_habitant = conso_totale / population.
- Resultat : intensite energetique par zone.

4. Accessibilite transport

- Donnees : positions des stations + zones (ou points de population/logements).
- Calcul (choisir une methode) :
  - methode distance : distance moyenne a la station la plus proche,
  - methode couverture : part de la population a moins de 500 m d'une station.
- Resultat : score d'accessibilite transport.

### C. Regles importantes pour eviter les erreurs

- Utiliser la meme unite partout (m2, euros, annee).
- Ecrire clairement les hypotheses dans le rapport.
- Pour le logement social, preciser qu'il s'agit de logements finances (flux), pas du stock total existant.

## Sources de donnees verifiees dans le dossier csv

- csv/75.csv
- csv/iris.csv
- csv/logement-encadrement-des-loyers.csv
- csv/logements-sociaux-finances-a-paris.csv
- csv/arrondissements.csv
- csv/donnee-data.gouv-2025-geographie2025-produit-le2026-02-03.csv
- csv/emplacement-des-gares-idf.csv

Rayan

indicateur obligatoire : median prix m² par arrondissment dataset : dvf, iris, arrondissement
supplementaire : indice de securité, : dataset : delinquance, camera , poste police ?
