from __future__ import annotations
 
import json
import sys
from pathlib import Path
 
import pandas as pd
 
 
# Determine project root robustly by searching for a containing `src` directory.
candidate = Path(__file__).resolve()
project_root = None
for _ in range(8):
    candidate = candidate.parent
    if (candidate / "src").exists():
        project_root = candidate
        break
 
if project_root is None:
    # Fallback to original heuristic
    project_root = Path(__file__).resolve().parents[3]
 
ROOT_PATH = project_root
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))
 
print(f"[build_storage_exports] Using ROOT_PATH={ROOT_PATH}")
 
from src.utils.config import GOLD_DIR, SILVER_DIR
 
 
EXPORT_DIR = ROOT_PATH / "data" / "exports"
RELATIONAL_DIR = EXPORT_DIR / "relational"
NOSQL_DIR = EXPORT_DIR / "nosql"
SQL_DIR = ROOT_PATH / "sql"
 
 
RELATIONAL_SOURCES = [
    ("fact_kpi_prix_m2_quartier_annuel", GOLD_DIR / "kpi_prix_m2_quartier_annuel.csv"),
    ("fact_kpi_comparaison_achat_location_arrondissement", GOLD_DIR / "kpi_comparaison_achat_location_arrondissement.csv"),
    ("fact_kpi_comparaison_achat_location_quartier", GOLD_DIR / "kpi_comparaison_achat_location_quartier_estime.csv"),
    ("fact_kpi_loyers_quartier", GOLD_DIR / "kpi_loyers_quartier.csv"),
    ("fact_kpi_repartition_logements_sociaux", GOLD_DIR / "kpi_repartition_logements_sociaux.csv"),
    ("fact_kpi_confort_quartier", GOLD_DIR / "gold_kpi_confort_urbain.csv"),
    ("fact_kpi_surete_quartier", GOLD_DIR / "kpi_score_surete_quartier_estime_depuis_iris.csv"),
]
 
 
GEOJSON_SOURCES = [
    ("quartiers", SILVER_DIR / "commun" / "quartiers_clean.csv", "polygon"),
    ("arrondissements", SILVER_DIR / "commun" / "arrondissements_clean.csv", "polygon"),
    ("iris", SILVER_DIR / "commun" / "iris_clean.csv", "polygon"),
    ("commissariats", SILVER_DIR / "surete" / "commissariats_clean.csv", "point"),
    ("cameras", SILVER_DIR / "surete" / "cameras_clean.csv", "point"),
    ("gares", SILVER_DIR / "confort" / "gares_clean.csv", "point"),
]
 
 
def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, low_memory=False)
 
 
def jsonable(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
 
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
 
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
 
    return value
 
 
def parse_point_from_row(row: pd.Series) -> tuple[float, float] | None:
    coordinate_pairs = [
        ("longitude", "latitude", "lon_lat"),
        ("lon", "lat", "lon_lat"),
        ("x", "y", "xy"),
        ("lat", "lon", "lat_lon"),
        ("latitude", "longitude", "lat_lon"),
    ]
    for first_col, second_col, mode in coordinate_pairs:
        if first_col in row and second_col in row:
            first_value = row[first_col]
            second_value = row[second_col]
            if pd.notna(first_value) and pd.notna(second_value):
                try:
                    first_float = float(first_value)
                    second_float = float(second_value)
                except (TypeError, ValueError):
                    continue
                if mode == "lon_lat":
                    return first_float, second_float
                return second_float, first_float
 
    geometry_columns = ["geometry_xy", "Geo Point", "geo_point_2d", "geo_point", "geometry", "geo_shape"]
    for geometry_column in geometry_columns:
        if geometry_column not in row or pd.isna(row[geometry_column]):
            continue
 
        text = str(row[geometry_column]).strip()
        if not text or text.lower() in {"none", "nan", "nat"}:
            continue
 
        if text.startswith("{"):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                coordinates = payload.get("coordinates")
                if isinstance(coordinates, list) and len(coordinates) >= 2:
                    try:
                        return float(coordinates[0]), float(coordinates[1])
                    except (TypeError, ValueError):
                        continue
 
        if "," in text:
            parts = [part.strip() for part in text.split(",", 1)]
            if len(parts) == 2:
                try:
                    first_value = float(parts[0])
                    second_value = float(parts[1])
                except (TypeError, ValueError):
                    continue
                if geometry_column in {"x", "geometry", "geo_shape"}:
                    return first_value, second_value
                return second_value, first_value
 
    return None
 
 
def parse_geometry_from_row(row: pd.Series) -> dict | None:
    geometry_candidates = ["Geo Shape", "geo_shape", "geometry", "geometry_xy"]
    for geometry_column in geometry_candidates:
        if geometry_column not in row or pd.isna(row[geometry_column]):
            continue
 
        text = str(row[geometry_column]).strip()
        if not text or text.lower() in {"none", "nan", "nat"}:
            continue
 
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
 
        if isinstance(payload, dict) and payload.get("type") in {"Polygon", "MultiPolygon"}:
            return payload
 
    return None
 
 
def dataframe_to_geojson(df: pd.DataFrame, collection_name: str, geometry_mode: str = "point") -> dict:
    features = []
    geometry_columns = {"latitude", "longitude", "lat", "lon", "x", "y", "geometry_xy", "Geo Point", "geo_point_2d", "geo_point", "geometry", "geo_shape", "Geo Shape"}
 
    for _, row in df.iterrows():
        properties = {
            column: jsonable(value)
            for column, value in row.items()
            if column not in geometry_columns
        }
 
        if geometry_mode == "polygon":
            geometry = parse_geometry_from_row(row)
            if geometry is None:
                point = parse_point_from_row(row)
                if point is None:
                    continue
                lon, lat = point
                geometry = {
                    "type": "Point",
                    "coordinates": [lon, lat],
                }
        else:
            point = parse_point_from_row(row)
            if point is None:
                continue
 
            lon, lat = point
            geometry = {
                "type": "Point",
                "coordinates": [lon, lat],
            }
 
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )
 
    return {
        "type": "FeatureCollection",
        "name": collection_name,
        "features": features,
    }
 
 
def build_relational_loader() -> list[str]:
    statements = ["BEGIN;"]
    for table_name, csv_path in RELATIONAL_SOURCES:
        if not csv_path.exists():
            continue
        statements.append(f"TRUNCATE TABLE {table_name} CASCADE;")
        statements.append(
            f"\\copy {table_name} FROM '{csv_path.as_posix()}' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8');"
        )
    statements.append("COMMIT;")
    return statements
 
 
def export_relational_loader() -> Path:
    RELATIONAL_DIR.mkdir(parents=True, exist_ok=True)
    SQL_DIR.mkdir(parents=True, exist_ok=True)
 
    loader_path = SQL_DIR / "load_gold_kpis.psql"
    loader_path.write_text("\n".join(build_relational_loader()) + "\n", encoding="utf-8")
 
    manifest = []
    for table_name, csv_path in RELATIONAL_SOURCES:
        if csv_path.exists():
            manifest.append({"table": table_name, "source": csv_path.as_posix()})
 
    manifest_path = RELATIONAL_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return loader_path
 
 
def export_geojson_documents() -> list[Path]:
    NOSQL_DIR.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
 
    for collection_name, csv_path, geometry_mode in GEOJSON_SOURCES:
        df = read_csv_if_exists(csv_path)
        if df is None or df.empty:
            continue
 
        geojson = dataframe_to_geojson(df, collection_name, geometry_mode=geometry_mode)
        output_path = NOSQL_DIR / f"{collection_name}.geojson"
        output_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_paths.append(output_path)
 
    return output_paths
 
 
def main() -> None:
    loader_path = export_relational_loader()
    geojson_paths = export_geojson_documents()
 
    print(f"Loader relationnel généré: {loader_path}")
    if geojson_paths:
        print("GeoJSON générés:")
        for path in geojson_paths:
            print(f"- {path}")
    else:
        print("Aucun GeoJSON généré.")
 
 
if __name__ == "__main__":
    main()
 