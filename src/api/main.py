"""
Urban Data API Backend — FastAPI server serving MongoDB + MySQL data to React frontend.

Endpoints:
- GET /api/quartiers/geojson
- GET /api/quartiers/lookup?lat=...&lon=...
- GET /api/search/address?q=...
- GET /api/quartiers/{codeInsee}/addresses
- GET /api/kpi/quartier/{codeInsee}?categories=...&annee=...
- GET /api/ranking/arrondissement/{arrNum}?categories=...
- GET /api/quartiers/choropleth?category=...
"""

from contextlib import asynccontextmanager
from typing import Any, Optional
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import mysql.connector
from pymongo import MongoClient
from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv()


# ─── Configuration ────────────────────────────────────────────────────────────

API_KEY = os.getenv("API_KEY", "")
FRONT_URL = os.getenv("FRONT_URL", "http://localhost:5173/").rstrip("/")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "urban_data")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("MYSQL_DATABASE", "urban_data")
MYSQL_USER = os.getenv("MYSQL_USER", "root1")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "dbl2025")


# ─── Global connections ────────────────────────────────────────────────────────

mongo_client: Optional[MongoClient] = None
mongo_db = None
mysql_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global mongo_client, mongo_db, mysql_pool
    
    # Startup
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        mongo_db = mongo_client[MONGODB_DB]
        print("[OK] Connected to MongoDB")
    except Exception as e:
        print(f"[FAIL] MongoDB connection failed: {e}")
    
    try:
        mysql_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="urban_pool",
            pool_size=5,
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            database=MYSQL_DB,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
        )
        conn = mysql_pool.get_connection()
        conn.close()
        print("[OK] Connected to MySQL")
    except Exception as e:
        print(f"[FAIL] MySQL connection failed: {e}")
    
    yield
    
    # Shutdown
    if mongo_client is not None:
        mongo_client.close()
        print("[OK] MongoDB connection closed")
    if mysql_pool is not None:
        print("[OK] MySQL pool closed")


app = FastAPI(
    title="Urban Paris Data API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Skip preflight requests — CORS middleware handles them
    if request.url.path.startswith("/api/") and request.method != "OPTIONS":
        if not API_KEY:
            return JSONResponse(status_code=500, content={"detail": "API key not configured on server"})
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class QuartierProperties(BaseModel):
    """Properties of a quartier GeoJSON feature."""
    arrondissement: int
    code_quartier_id: int
    code_insee_quartier: int
    nom_quartier: str
    surface_quartier_m2: float


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature structure."""
    type: str = "Feature"
    geometry: dict
    properties: QuartierProperties


class QuartiersGeoJSON(BaseModel):
    """GeoJSON FeatureCollection."""
    type: str = "FeatureCollection"
    features: list[GeoJSONFeature]


class GeoJSONFeatureCollection(BaseModel):
    """Generic GeoJSON FeatureCollection."""
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]


class Quartier(BaseModel):
    """Domain model for a quartier."""
    code_insee: str
    nom_quartier: str
    arrondissement: int
    code_quartier: str
    surface: float
    perimetre: float
    lat: float
    lon: float


class Address(BaseModel):
    """Domain model for an address."""
    numero: str
    rue: str
    code_postal: str
    lat: float
    lon: float
    full: str
    type: Optional[str] = None
    statut: Optional[str] = None


class KPIConfort(BaseModel):
    arrondissement: int
    code_insee_quartier: int
    nom_quartier: str
    surface_quartier_m2: float
    part_surface: float
    incidents_estime: float
    travaux_estime: float
    gares_estime: float
    risque_incidents_100: float
    score_confort_urbain_100: float


class KPISurete(BaseModel):
    annee: int
    arrondissement: int
    code_insee_quartier: int
    score_surete_quartier_moyen_100: float
    score_risque_quartier_moyen_100: float
    score_surete_iris_min_100: float
    score_surete_iris_max_100: float
    score_surete_iris_std_100: float
    score_risque_iris_min_100: float
    score_risque_iris_max_100: float
    score_risque_iris_std_100: float
    nb_iris_rattaches: int
    codes_iris_rattaches: str
    noms_iris_rattaches: str
    dist_commissariat_km_moyenne: float
    nb_cameras_arrondissement: int


class KPIPrixM2(BaseModel):
    annee: int
    arrondissement: int
    code_insee_quartier: int
    prix_m2_median: float
    prix_m2_moyen: float
    nb_ventes: int
    nb_ventes_estime: int
    surface_quartier_m2: float
    part_surface: float


class KPILoyers(BaseModel):
    annee: int
    arrondissement: int
    code_insee_quartier: int
    loyer_reference_median: float
    loyer_reference_moyen: float
    nb_observations: int
    loyer_reference_majore_median: float
    loyer_reference_minore_median: float
    nombre_pieces_median: float
    nom_quartier: str
    type_location_mode: str
    epoque_construction_mode: str


class KPILogementsSociaux(BaseModel):
    arrondissement: int
    annee: int
    code_insee_quartier: int
    nom_quartier: str
    logements_finances_total: int
    logements_finances_moyen: float
    nb_programmes: int
    nb_bailleurs: int
    nb_pla_i_total: int
    nb_plus_total: int
    nb_plus_cd_total: int
    nb_pls_total: int
    latitude_moyenne: float
    longitude_moyenne: float


ADDRESS_COLLECTIONS = ("geo_addresses", "addresses", "geo_adresses", "adresses")


def geojson_collection_to_feature_collection(collection_name: str) -> dict[str, Any]:
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB not available")

    collection = mongo_db[collection_name]
    features: list[dict[str, Any]] = []

    for doc in collection.find({}):
        if "_id" in doc:
            del doc["_id"]
        features.append({
            "type": "Feature",
            "geometry": doc.get("geometry", {"type": "Point", "coordinates": [0, 0]}),
            "properties": doc.get("properties", {}),
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def read_address_value(source: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return default


def document_to_address(doc: dict[str, Any]) -> dict[str, Any]:
    properties = doc.get("properties", {}) if isinstance(doc.get("properties", {}), dict) else {}
    geometry = doc.get("geometry", {}) if isinstance(doc.get("geometry", {}), dict) else {}
    coordinates = geometry.get("coordinates", [0, 0]) if isinstance(geometry.get("coordinates", [0, 0]), list) else [0, 0]
    lon = coordinates[0] if len(coordinates) > 0 and isinstance(coordinates[0], (int, float)) else read_address_value(doc, ["lon", "longitude", "x"], 0)
    lat = coordinates[1] if len(coordinates) > 1 and isinstance(coordinates[1], (int, float)) else read_address_value(doc, ["lat", "latitude", "y"], 0)

    numero = str(read_address_value(properties, ["numero", "adresse_numero", "house_number"], read_address_value(doc, ["numero", "adresse_numero"], "")))
    rue = str(read_address_value(properties, ["rue", "adresse_nom_voie", "nom_voie", "voie"], read_address_value(doc, ["rue", "adresse_nom_voie", "nom_voie", "voie"], "")))
    code_postal = str(read_address_value(properties, ["code_postal", "postal_code"], read_address_value(doc, ["code_postal", "postal_code"], "")))
    full = str(read_address_value(properties, ["full", "adresse_complete"], read_address_value(doc, ["full", "adresse_complete"], f"{numero} {rue}, {code_postal} Paris".strip())))

    address_type = read_address_value(properties, ["type"], read_address_value(doc, ["type"], "Adresse"))
    statut = read_address_value(properties, ["statut"], read_address_value(doc, ["statut"], None))

    return {
        "numero": numero,
        "rue": rue,
        "code_postal": code_postal,
        "lat": float(lat) if isinstance(lat, (int, float)) else 0,
        "lon": float(lon) if isinstance(lon, (int, float)) else 0,
        "full": full,
        "type": address_type,
        "statut": statut,
    }


def query_address_collections(query: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB not available")

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, float, float]] = set()

    for collection_name in ADDRESS_COLLECTIONS:
        collection = mongo_db[collection_name]
        for doc in collection.find(query).limit(limit):
            address = document_to_address(doc)
            dedupe_key = (
                address["numero"],
                address["rue"],
                address["code_postal"],
                address["lat"],
                address["lon"],
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            results.append(address)
            if len(results) >= limit:
                return results

    return results


class KPIComparaison(BaseModel):
    annee: int
    arrondissement: int
    code_insee_quartier: int
    prix_m2_median: float
    prix_m2_moyen: float
    nb_transactions: int
    loyer_reference_median: float
    loyer_reference_moyen: float
    nb_observations: int
    kpi_comparaison_achat_location: float
    surface_quartier_m2: float
    part_surface: float
    nb_transactions_estime: int
    nb_observations_estime: int


class QuartierKPIResponse(BaseModel):
    quartier: Optional[Quartier]
    kpis: dict[str, Any]
    categories_requested: list[str]


class RankedQuartier(BaseModel):
    code_insee: str
    nom_quartier: str
    arrondissement: int
    scores: dict[str, Optional[float]]
    composite_score: float
    rank: int


class RankingResponse(BaseModel):
    arrondissement: int
    categories: list[str]
    ranking: list[RankedQuartier]


# ─── Utility Functions ────────────────────────────────────────────────────────

def get_mysql_connection():
    """Get a MySQL connection from the pool."""
    if not mysql_pool:
        raise HTTPException(status_code=503, detail="MySQL not available")
    return mysql_pool.get_connection()


def quartier_from_geojson(feature: dict) -> Quartier:
    """Convert a GeoJSON feature to a Quartier domain model."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [0, 0])
    
    return Quartier(
        code_insee=str(props.get("code_insee_quartier", "")),
        nom_quartier=str(props.get("nom_quartier", "")),
        arrondissement=int(props.get("arrondissement", 0)),
        code_quartier=str(props.get("code_quartier_id", "")),
        surface=float(props.get("surface_quartier_m2", 0)),
        perimetre=0,  # Not available in local GeoJSON
        lat=coords[1] if len(coords) > 1 else 0,
        lon=coords[0] if len(coords) > 0 else 0,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/quartiers/geojson", response_model=QuartiersGeoJSON)
async def get_quartiers_geojson():
    """Return all quartiers as GeoJSON FeatureCollection."""
    try:
        return geojson_collection_to_feature_collection("geo_quartiers")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")


@app.get("/api/arrondissements/geojson", response_model=GeoJSONFeatureCollection)
async def get_arrondissements_geojson():
    """Return all arrondissements as GeoJSON FeatureCollection."""
    try:
        return geojson_collection_to_feature_collection("geo_arrondissements")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")


@app.get("/api/quartiers/lookup")
async def lookup_quartier(lat: float, lon: float):
    """Return the quartier containing a point (lat, lon)."""
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB not available")
    
    try:
        collection = mongo_db["geo_quartiers"]
        # MongoDB 2dsphere index allows $near queries
        feature = collection.find_one({
            "geometry": {
                "$geoIntersects": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    }
                }
            }
        })
        
        if not feature:
            # Fallback: try simple point-in-polygon (less efficient but works)
            features = list(collection.find({}))
            for doc in features:
                geom = doc.get("geometry", {})
                if geom.get("type") == "Polygon":
                    # Simple bounding box check (not perfect but good enough)
                    coords = geom.get("coordinates", [[]])[0]
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    if min(lons) <= lon <= max(lons) and min(lats) <= lat <= max(lats):
                        feature = doc
                        break
        
        if not feature:
            raise HTTPException(status_code=404, detail="Quartier not found")
        
        return quartier_from_geojson(feature)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")


@app.get("/api/search/address")
async def search_address(q: str):
    """Search for addresses by name or quartier."""
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB not available")
    
    try:
        address_query = {
            "$or": [
                {"properties.numero": {"$regex": q, "$options": "i"}},
                {"properties.rue": {"$regex": q, "$options": "i"}},
                {"properties.full": {"$regex": q, "$options": "i"}},
                {"properties.adresse_numero": {"$regex": q, "$options": "i"}},
                {"properties.adresse_nom_voie": {"$regex": q, "$options": "i"}},
                {"properties.code_postal": {"$regex": q, "$options": "i"}},
                {"numero": {"$regex": q, "$options": "i"}},
                {"rue": {"$regex": q, "$options": "i"}},
                {"full": {"$regex": q, "$options": "i"}},
                {"adresse_numero": {"$regex": q, "$options": "i"}},
                {"adresse_nom_voie": {"$regex": q, "$options": "i"}},
                {"code_postal": {"$regex": q, "$options": "i"}},
            ]
        }
        results = query_address_collections(address_query)

        if results:
            return results

        quartier_query = {"properties.nom_quartier": {"$regex": q, "$options": "i"}}
        quartier_results = []
        for doc in mongo_db["geo_quartiers"].find(quartier_query):
            props = doc.get("properties", {})
            geom = doc.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])

            quartier_results.append({
                "numero": "",
                "rue": props.get("nom_quartier", ""),
                "code_postal": f"75{str(props.get('arrondissement', 0)).zfill(2)}",
                "lat": coords[1] if len(coords) > 1 else 0,
                "lon": coords[0] if len(coords) > 0 else 0,
                "full": f"{props.get('nom_quartier', '')}, Paris",
                "type": "Quartier",
            })

        return quartier_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")


@app.get("/api/quartiers/{codeInsee}/addresses")
async def get_quartier_addresses(codeInsee: str):
    """Return addresses for a specific quartier."""
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="MongoDB not available")
    
    try:
        collection = mongo_db["geo_quartiers"]
        quartier = collection.find_one({
            "properties.code_insee_quartier": int(codeInsee)
        })
        
        if not quartier:
            return []  # Return empty list if quartier not found
        
        props = quartier.get("properties", {})
        arr = props.get("arrondissement", 0)
        postal_prefix = f"75{str(arr).zfill(2)}"

        address_query = {
            "$or": [
                {"properties.code_postal": {"$regex": f"^{postal_prefix}"}},
                {"code_postal": {"$regex": f"^{postal_prefix}"}},
                {"properties.arrondissement": arr},
                {"arrondissement": arr},
            ]
        }

        return query_address_collections(address_query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB error: {str(e)}")


@app.get("/api/kpi/quartier/{codeInsee}")
async def get_quartier_kpis(codeInsee: str, categories: str = "", annee: int = 2023):
    """Return KPI data for a quartier."""
    if mysql_pool is None:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        code_insee_int = int(codeInsee)
        categories_list = [c.strip() for c in categories.split(",") if c.strip()]
        
        kpis = {}
        
        # Confort
        if "confort" in categories_list:
            cursor.execute(
                "SELECT * FROM fact_kpi_confort_quartier WHERE code_insee_quartier = %s LIMIT 1",
                (code_insee_int,)
            )
            row = cursor.fetchone()
            if row:
                kpis["confort"] = dict(row)
        
        # Surete
        if "surete" in categories_list:
            cursor.execute(
                "SELECT * FROM fact_kpi_surete_quartier WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1",
                (code_insee_int,)
            )
            row = cursor.fetchone()
            if row:
                kpis["surete"] = dict(row)
        
        # Prix M2
        if "prix_m2" in categories_list:
            cursor.execute(
                "SELECT * FROM fact_kpi_prix_m2_quartier_annuel WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1",
                (code_insee_int,)
            )
            row = cursor.fetchone()
            if row:
                kpis["prix_m2"] = dict(row)
        
        # Loyers
        if "loyers" in categories_list:
            cursor.execute(
                "SELECT * FROM fact_kpi_loyers_quartier WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1",
                (code_insee_int,)
            )
            row = cursor.fetchone()
            if row:
                kpis["loyers"] = dict(row)
        
        # Logements Sociaux
        if "logements_sociaux" in categories_list:
            cursor.execute(
                "SELECT * FROM fact_kpi_repartition_logements_sociaux WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1",
                (code_insee_int,)
            )
            row = cursor.fetchone()
            if row:
                kpis["logements_sociaux"] = dict(row)
        
        # Comparaison
        if "comparaison" in categories_list:
            cursor.execute(
                "SELECT * FROM fact_kpi_comparaison_achat_location_quartier WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1",
                (code_insee_int,)
            )
            row = cursor.fetchone()
            if row:
                kpis["comparaison"] = dict(row)
        
        cursor.close()
        conn.close()
        
        return {
            "quartier": None,  # Could fetch from MongoDB
            "kpis": kpis,
            "categories_requested": categories_list,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MySQL error: {str(e)}")


@app.get("/api/ranking/arrondissement/{arrNum}")
async def get_arrondissement_ranking(arrNum: int, categories: str = ""):
    """Return ranking of quartiers in an arrondissement."""
    if mysql_pool is None:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        categories_list = [c.strip() for c in categories.split(",") if c.strip()]
        
        # Fetch all quartiers in this arrondissement
        cursor.execute(
            "SELECT DISTINCT code_insee_quartier, nom_quartier FROM fact_kpi_confort_quartier WHERE arrondissement = %s",
            (arrNum,)
        )
        quartiers = cursor.fetchall()
        
        raw_ranking = []
        for idx, q in enumerate(quartiers, 1):
            code_insee = q.get("code_insee_quartier")
            nom = q.get("nom_quartier")
            scores = {}
            
            # Fetch scores for each category
            if "confort" in categories_list:
                cursor.execute(
                    "SELECT score_confort_urbain_100 FROM fact_kpi_confort_quartier WHERE code_insee_quartier = %s LIMIT 1",
                    (code_insee,)
                )
                row = cursor.fetchone()
                scores["confort"] = row.get("score_confort_urbain_100") if row else None
            
            if "surete" in categories_list:
                cursor.execute(
                    "SELECT score_surete_quartier_moyen_100 FROM fact_kpi_surete_quartier WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1",
                    (code_insee,)
                )
                row = cursor.fetchone()
                scores["surete"] = row.get("score_surete_quartier_moyen_100") if row else None
            
            if "prix_m2" in categories_list:
                cursor.execute("SELECT prix_m2_median FROM fact_kpi_prix_m2_quartier_annuel WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1", (code_insee,))
                row = cursor.fetchone()
                scores["prix_m2"] = row.get("prix_m2_median") if row else None

            if "loyers" in categories_list:
                cursor.execute("SELECT loyer_reference_median FROM fact_kpi_loyers_quartier WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1", (code_insee,))
                row = cursor.fetchone()
                scores["loyers"] = row.get("loyer_reference_median") if row else None
            
            if "logements_sociaux" in categories_list:
                cursor.execute("SELECT logements_finances_moyen FROM fact_kpi_repartition_logements_sociaux WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1", (code_insee,))
                row = cursor.fetchone()
                scores["logements_sociaux"] = row.get("logements_finances_moyen") if row else None
            
            if "comparaison" in categories_list:
                cursor.execute("SELECT kpi_comparaison_achat_location FROM fact_kpi_comparaison_achat_location_quartier WHERE code_insee_quartier = %s ORDER BY annee DESC LIMIT 1", (code_insee,))
                row = cursor.fetchone()
                scores["comparaison"] = row.get("kpi_comparaison_achat_location") if row else None
            
            raw_ranking.append({
                "code_insee": str(code_insee),
                "nom_quartier": nom,
                "arrondissement": arrNum,
                "scores": scores
            })

        # Calculate min-max for normalization
        min_max = {}
        for cat in categories_list:
            if cat in ("confort", "surete"):
                continue
            valid_scores = [r["scores"][cat] for r in raw_ranking if r["scores"].get(cat) is not None]
            if valid_scores:
                min_max[cat] = {"min": float(min(valid_scores)), "max": float(max(valid_scores))}
            else:
                min_max[cat] = {"min": 0.0, "max": 0.0}

        ranking = []
        for r in raw_ranking:
            norm_scores = {}
            for cat, val in r["scores"].items():
                if val is None:
                    continue
                if cat in ("confort", "surete"):
                    norm_scores[cat] = float(val)
                else:
                    c_min = min_max[cat]["min"]
                    c_max = min_max[cat]["max"]
                    if c_min == c_max:
                        norm_scores[cat] = 100.0
                    else:
                        if cat in ("prix_m2", "loyers"):
                            # Inverse: lowest price = 100 score
                            norm_scores[cat] = 100.0 - ((float(val) - c_min) / (c_max - c_min) * 100.0)
                        else:
                            # Higher is better
                            norm_scores[cat] = ((float(val) - c_min) / (c_max - c_min) * 100.0)

            composite = sum(norm_scores.values()) / len(norm_scores) if norm_scores else 0
            r["composite_score"] = composite
            ranking.append(r)

        # Sort the ranking by composite_score DESC
        ranking.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Add rank index based on sorted position
        for idx, r in enumerate(ranking, 1):
            r["rank"] = idx
        
        cursor.close()
        conn.close()
        
        return {
            "arrondissement": arrNum,
            "categories": categories_list,
            "ranking": ranking,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MySQL error: {str(e)}")


@app.get("/api/quartiers/choropleth")
async def get_choropleth_scores(category: str = "confort"):
    """Return choropleth scores (code_insee -> score) for a category."""
    if mysql_pool is None:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        scores = {}
        
        if category == "confort":
            cursor.execute(
                "SELECT code_insee_quartier, score_confort_urbain_100 FROM fact_kpi_confort_quartier"
            )
        elif category == "surete":
            cursor.execute(
                "SELECT code_insee_quartier, score_surete_quartier_moyen_100 FROM fact_kpi_surete_quartier ORDER BY annee DESC"
            )
        elif category == "prix_m2":
            cursor.execute(
                "SELECT code_insee_quartier, prix_m2_median FROM fact_kpi_prix_m2_quartier_annuel ORDER BY annee DESC"
            )
        elif category == "loyers":
            cursor.execute("SELECT code_insee_quartier, loyer_reference_median FROM fact_kpi_loyers_quartier ORDER BY annee DESC")
        elif category == "logements_sociaux":
            cursor.execute("SELECT code_insee_quartier, logements_finances_moyen FROM fact_kpi_repartition_logements_sociaux ORDER BY annee DESC")
        elif category == "comparaison":
            cursor.execute("SELECT code_insee_quartier, kpi_comparaison_achat_location FROM fact_kpi_comparaison_achat_location_quartier ORDER BY annee DESC")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
        
        rows = cursor.fetchall()
        for row in rows:
            code_insee = str(row.get("code_insee_quartier", 0))
            if category == "confort":
                score = row.get("score_confort_urbain_100", 0)
            elif category == "surete":
                score = row.get("score_surete_quartier_moyen_100", 0)
            elif category == "prix_m2":
                score = row.get("prix_m2_median", 0)
            elif category == "loyers":
                score = row.get("loyer_reference_median", 0)
            elif category == "logements_sociaux":
                score = row.get("logements_finances_moyen", 0)
            elif category == "comparaison":
                score = row.get("kpi_comparaison_achat_location", 0)
            else:
                score = 0
            
            if code_insee not in scores:  # Keep first (most recent) value
                scores[code_insee] = score
        
        cursor.close()
        conn.close()
        
        return scores
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MySQL error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "mongodb": "connected" if mongo_db is not None else "disconnected",
        "mysql": "connected" if mysql_pool is not None else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
