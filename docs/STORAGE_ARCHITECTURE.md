# Architecture de Stockage des Données

## Vue d'ensemble

Le projet utilise une **architecture dual storage** :

- **MySQL** : stocke les indicateurs KPI (données métier) + mapping IRIS↔quartier
- **MongoDB** : stocke les géométries et couches cartographiques (GeoJSON)

Cette séparation permet une requête efficace : requêtes analytiques en MySQL, requêtes spatiales en MongoDB.

---

## 1. MySQL (`urban_data`)

### 1.1 Tables KPI

#### `fact_kpi_prix_m2_quartier_annuel`

Prix immobilier par quartier et année.

```sql
SELECT * FROM fact_kpi_prix_m2_quartier_annuel
WHERE annee = 2023 AND code_insee_quartier = '7501101';
```

**Colonnes clés :**

- `annee` : année du KPI
- `code_insee_quartier` : identifiant du quartier (7 chiffres, ex: 7501101)
- `arrondissement` : numéro d'arrondissement (ex: 01)
- `prix_m2_median`, `prix_m2_moyen` : prix au m² en €
- `nb_ventes` : nombre de ventes observées

#### `fact_kpi_comparaison_achat_location_arrondissement` & `fact_kpi_comparaison_achat_location_quartier`

Comparaison achat/location par arrondissement ou quartier.

```sql
SELECT * FROM fact_kpi_comparaison_achat_location_quartier
WHERE annee = 2023 AND code_insee_quartier = '7501101';
```

**Colonnes clés :**

- `annee` : année
- `code_insee_quartier` : quartier (ou `arrondissement` pour l'autre table)
- `prix_m2_median`, `loyer_reference_median` : prix médian achat et location
- `kpi_comparaison_achat_location` : ratio/score comparaison

#### `fact_kpi_loyers_quartier`

Loyers de référence par quartier et année.

```sql
SELECT * FROM fact_kpi_loyers_quartier
WHERE annee = 2023 AND code_insee_quartier = '7501101';
```

**Colonnes clés :**

- `annee`, `code_insee_quartier` : identifiants
- `loyer_reference_median`, `loyer_reference_moyen` : loyer en €/mois
- `nombre_pieces_median` : nombre de pièces médian
- `type_location_mode`, `epoque_construction_mode` : modes (meublé, non-meublé, etc.)

#### `fact_kpi_confort_quartier`

Score de confort urbain par quartier (sans dimension temps).

```sql
SELECT * FROM fact_kpi_confort_quartier
WHERE code_insee_quartier = '7501101';
```

**Colonnes clés :**

- `code_insee_quartier` : quartier
- `score_confort_urbain_100` : score 0-100
- `risque_incidents_100` : score incidents 0-100
- `surface_quartier_m2` : surface du quartier

#### `fact_kpi_surete_quartier`

Sécurité et risques par quartier et année (agrégé depuis IRIS).

```sql
SELECT * FROM fact_kpi_surete_quartier
WHERE annee = 2023 AND code_insee_quartier = '7501101';
```

**Colonnes clés :**

- `annee`, `code_insee_quartier` : identifiants
- `score_surete_quartier_moyen_100`, `score_risque_quartier_moyen_100` : scores 0-100
- `nb_iris_rattaches` : nombre d'IRIS agrégés
- `dist_commissariat_km_moyenne` : distance moyenne au commissariat
- `nb_cameras_arrondissement` : nombre de caméras

#### `fact_kpi_repartition_logements_sociaux`

Distribution des logements sociaux par quartier et année.

```sql
SELECT * FROM fact_kpi_repartition_logements_sociaux
WHERE annee = 2023 AND code_insee_quartier = '7501101';
```

**Colonnes clés :**

- `annee`, `code_insee_quartier` : identifiants
- `logements_finances_total` : nombre total de logements
- `nb_pla_i_total`, `nb_plus_total`, `nb_pls_total` : types de logements sociaux
- `latitude_moyenne`, `longitude_moyenne` : centroïde

### 1.2 Mapping IRIS ↔ Quartier

#### `iris_to_quartier`

Table de correspondance : chaque IRIS (subdivisions fines) est mappé à un quartier.

```sql
SELECT * FROM iris_to_quartier
WHERE code_iris LIKE '7501101%';
```

**Colonnes :**

- `code_iris` : code IRIS (9 chiffres, ex: 751010101)
- `code_insee_quartier` : code quartier correspondant (7 chiffres, ex: 7501101)
- `insee_com` : code commune INSEE

**Utilité :** agréger des données IRIS (par ex. sécurité) au niveau quartier, ou afficher des polygones IRIS avec leurs KPI quartier.

### 1.3 Requêtes courantes

**Récupérer tous les KPI d'un quartier (année 2023) :**

```sql
SELECT
    kpi1.annee,
    kpi1.code_insee_quartier,
    kpi1.prix_m2_median,
    kpi2.loyer_reference_median,
    kpi3.score_confort_urbain_100,
    kpi4.score_surete_quartier_moyen_100
FROM fact_kpi_prix_m2_quartier_annuel kpi1
LEFT JOIN fact_kpi_loyers_quartier kpi2
    ON kpi1.code_insee_quartier = kpi2.code_insee_quartier
    AND kpi1.annee = kpi2.annee
LEFT JOIN fact_kpi_confort_quartier kpi3
    ON kpi1.code_insee_quartier = kpi3.code_insee_quartier
LEFT JOIN fact_kpi_surete_quartier kpi4
    ON kpi1.code_insee_quartier = kpi4.code_insee_quartier
    AND kpi1.annee = kpi4.annee
WHERE kpi1.annee = 2023 AND kpi1.code_insee_quartier = '7501101';
```

**Trouver tous les IRIS d'un quartier :**

```sql
SELECT code_iris, nom_iris FROM iris_to_quartier
WHERE code_insee_quartier = '7501101'
ORDER BY code_iris;
```

---

## 2. MongoDB (`urban_data`)

### 2.1 Collections GeoJSON

Chaque collection contient des **GeoJSON Features** avec géométries (points ou polygones).

#### `geo_iris`

Polygones des IRIS (subdivisions fines) avec centroïdes.

**Document exemple :**

```json
{
  "_id": ObjectId("..."),
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[2.348, 48.862], [2.347, 48.860], ...]]
  },
  "properties": {
    "INSEE_COM": "75101",
    "CODE_IRIS": "751010205",
    "NOM_IRIS": "Les Halles 5",
    "Geo Point": "48.862, 2.345"
  }
}
```

**Requête :**

```javascript
db.geo_iris.findOne({ "properties.CODE_IRIS": "751010205" });
```

#### `geo_quartiers`

Polygones ou points des quartiers Paris.

**Document exemple :**

```json
{
  "_id": ObjectId("..."),
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [2.336, 48.848]
  },
  "properties": {
    "code_insee_quartier": "7501101",
    "nom_quartier": "Odéon",
    "arrondissement": "06",
    "surface_quartier_m2": 716148
  }
}
```

**Requête :**

```javascript
db.geo_quartiers.findOne({ "properties.code_insee_quartier": "7501101" });
```

#### `geo_commissariats`, `geo_cameras`, `geo_gares`

Points (commissariats, caméras de surveillance, gares).

**Document exemple (commissariat) :**

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [2.345, 48.862]
  },
  "properties": {
    "nom": "Commissariat 1er arrondissement",
    "adresse": "...",
    "telephone": "..."
  }
}
```

**Requête (requête spatiale, ex: all within 1km of a point) :**

```javascript
db.geo_commissariats.find({
  geometry: {
    $near: {
      $geometry: { type: "Point", coordinates: [2.345, 48.862] },
      $maxDistance: 1000,
    },
  },
});
```

### 2.2 Index Géospatiaux

Chaque collection (sauf `geo_gares`, cf. section 2.3) a un index 2dsphere sur le champ `geometry` :

```javascript
db.geo_iris.createIndex({ geometry: "2dsphere" });
db.geo_quartiers.createIndex({ geometry: "2dsphere" });
// ... etc
```

Cet index permet les requêtes spatiales (`$near`, `$geoIntersects`, etc.).

### 2.3 ⚠️ Note sur `geo_gares`

Le fichier source `gares.geojson` contient des coordonnées en **Lambert93** (système projeté), pas en WGS84 (lat/lon standard).

- **Conséquence :** aucun index 2dsphere (MongoDB refuse)
- **Solution :** reprojeter les coordonnées ou charger sans index (pas de requêtes spatiales pour l'instant)

### 2.4 Requêtes courantes

**Récupérer une géométrie quartier :**

```javascript
db.geo_quartiers.findOne({ "properties.code_insee_quartier": "7501101" });
```

**Récupérer tous les IRIS d'un quartier :**

```javascript
db.geo_iris.find({
  "properties.INSEE_COM": "75101",
  "properties.CODE_IRIS": { $regex: "^7501101" },
});
```

**Requête spatiale : tous les commissariats à proximité d'un point :**

```javascript
db.geo_commissariats.find({
  geometry: {
    $near: {
      $geometry: { type: "Point", coordinates: [2.345, 48.862] },
      $maxDistance: 500, // 500 mètres
    },
  },
});
```

---

## 3. Jointure MySQL + MongoDB

Pour afficher un KPI avec sa géométrie, il faut joindre les deux bases.

### Exemple Python (FastAPI/API)

```python
from pymongo import MongoClient
import mysql.connector

# Récupérer les KPI depuis MySQL
mysql_conn = mysql.connector.connect(
    host='localhost', port=3306, user='root1', password='dbl2025', database='urban_data'
)
cursor = mysql_conn.cursor(dictionary=True)
cursor.execute(
    "SELECT * FROM fact_kpi_prix_m2_quartier_annuel WHERE code_insee_quartier = %s AND annee = %s",
    ('7501101', 2023)
)
kpi = cursor.fetchone()

# Récupérer la géométrie depuis MongoDB
mongo_client = MongoClient('mongodb://localhost:27017')
mongo_db = mongo_client['urban_data']
geo_doc = mongo_db.geo_quartiers.findOne({
    'properties.code_insee_quartier': kpi['code_insee_quartier']
})

# Fusionner
result = {
    'properties': kpi,  # KPI (MySQL)
    'geometry': geo_doc['geometry']  # Géométrie (MongoDB)
}
```

**Réponse JSON (exemple) :**

```json
{
  "properties": {
    "annee": 2023,
    "code_insee_quartier": "7501101",
    "prix_m2_median": 12500,
    "loyer_reference_median": 1200,
    "score_confort_urbain_100": 75,
    "score_surete_quartier_moyen_100": 60
  },
  "geometry": {
    "type": "Point",
    "coordinates": [2.336, 48.848]
  }
}
```

---

## 4. Setup Local (pour dev/test)

### MySQL

```bash
# Créer la base (si besoin)
mysql -u root1 -p -e "CREATE DATABASE urban_data;"

# Charger les KPI et mapping
cd src/pipeline/export
python.exe run_mysql_sql.py --host localhost --port 3306 --database urban_data --user root1 --password dbl2025 --all
python.exe load_kpi_csv_to_mysql.py --host localhost --port 3306 --database urban_data --user root1 --password dbl2025 --truncate
```

### MongoDB

```bash
# Démarrer le service
Start-Service MongoDB

# Charger les GeoJSON
cd src/pipeline/export
python.exe load_geojson_to_mongodb.py --uri "mongodb://localhost:27017" --db urban_data --drop
```

### Vérifier les données

```bash
# MySQL
mysql -u root1 -p -D urban_data -e "SHOW TABLES; SELECT COUNT(*) FROM fact_kpi_prix_m2_quartier_annuel;"

# MongoDB
mongosh --eval "use urban_data; show collections; db.geo_quartiers.countDocuments()"
```

---

## 5. Dépendances et Scripts

### `requirements-storage.txt`

```
pymongo>=4.8.0
psycopg[binary]>=3.2.0
mysql-connector-python>=9.0.0
```

### Scripts fournis

- `src/pipeline/export/run_mysql_sql.py` : exécute les SQL KPI
- `src/pipeline/export/load_kpi_csv_to_mysql.py` : charge CSV → MySQL
- `src/pipeline/export/load_geojson_to_mongodb.py` : charge GeoJSON → MongoDB
- `src/pipeline/export/build_iris_quartier_mapping.py` : génère la table de mapping

---

## 6. Points importants pour l'API

1. **Code quartier** : toujours en format 7 chiffres (ex: `7501101`)
2. **Code IRIS** : 9 chiffres (ex: `751010205`)
3. **Coordonnées** : WGS84 (lat/lon) sauf `geo_gares`
4. **Années disponibles** : variable selon KPI (2019-2023 généralement)
5. **Index MySQL** : sur `code_insee_quartier` pour requêtes rapides
6. **Index MongoDB** : 2dsphere sur `geometry` (sauf `geo_gares`)

---

## 7. Troubleshooting

**MySQL : erreur `LOAD DATA LOCAL INFILE`**

- Vérifier que `local_infile=1` est configuré côté serveur
- Ou utiliser le script Python fallback

**MongoDB : pas d'index 2dsphere sur `geo_gares`**

- Fichier source en Lambert93, pas WGS84
- Reprojection requise avant utilisation spatiale

**Données manquantes**

- Vérifier le `--drop` flag pour forcer le rechargement
- Contrôler les chemins CSV/GeoJSON

---

**Contact pour questions :** [à compléter avec le responsable stockage]
