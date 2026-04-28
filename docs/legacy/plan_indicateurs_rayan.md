Conclusion rapide

Oui, vous pouvez relier presque tous les datasets aux zones IRIS.
Le plus fiable: faire une jointure spatiale point/polygone avec les polygones IRIS de iris.csv.
Un dataset reste limité: la délinquance est au niveau commune/arrondissement, pas IRIS natif.
Dataset par dataset

iris.csv
Contient Geo Shape + Geo Point + CODE_IRIS.
C’est votre référentiel géographique principal.
Très bien.
arrondissements.csv
Référentiel arrondissement avec géométrie.
Utile pour agrégation macro.
points.csv
Caméras avec lat/lon.
Liaison IRIS simple via point-in-polygon.
Attention encodage colonne NUMÉRO (affichée en NUMÃ‰RO), à nettoyer.
cartographie-des-emplacements-des-commissariats-a-paris-et-petite-couronne.csv
Coordonnées via geo_point_2d.
Liaison IRIS simple via point-in-polygon ou distance au centroïde IRIS.
75.csv
Longitude/latitude présentes.
Liaison IRIS simple via point-in-polygon.
Très bon candidat IRIS.
emplacement-des-gares-idf.csv
Geo Point présent.
Liaison IRIS simple via point-in-polygon.
logements-sociaux-finances-a-paris.csv
geo_point_2d + geometry + coordonnées L93.
Faisable, mais il faut être cohérent sur le système de coordonnées (WGS84 vs L93).
logement-encadrement-des-loyers.csv
Géométrie de “quartiers”, pas IRIS.
Liaison IRIS possible par intersection spatiale, mais plus complexe (many-to-many / recouvrement partiel).
dataset_delinquances.csv
Niveau CODGEO commune/arrondissement.
Pas de géométrie IRIS.
Donc rattachement IRIS direct impossible sans règle d’allocation (approximation).
Recommandation opérationnelle

Standardiser toutes les géométries en WGS84.
Construire une table de correspondance zone:
point datasets -> CODE_IRIS par point-in-polygon
datasets polygonaux non IRIS -> intersection pondérée
Garder la délinquance au niveau arrondissement, puis ventiler en IRIS seulement si vous assumez une règle métier explicite.
