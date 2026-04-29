#!/usr/bin/env python3
"""Load GeoJSON exports into MongoDB collections.

Usage example:
python src/pipeline/export/load_geojson_to_mongodb.py \
  --uri "mongodb://localhost:27017" \
  --db urban_data \
  --drop
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.errors import OperationFailure


DEFAULT_MAPPING = {
    "iris.geojson": "geo_iris",
    "quartiers.geojson": "geo_quartiers",
    "commissariats.geojson": "geo_commissariats",
    "cameras.geojson": "geo_cameras",
    "gares.geojson": "geo_gares",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load GeoJSON files into MongoDB.")
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27017",
        help="MongoDB connection URI.",
    )

    parser.add_argument(
        "--db",
        default="urban_data",
        help="MongoDB database name.",
    )
    parser.add_argument(
        "--geojson-dir",
        default="data/exports/nosql",
        help="Directory that contains GeoJSON files.",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop target collections before insert.",
    )
    return parser.parse_args()


def load_features(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        features = payload.get("features", [])
    elif isinstance(payload, list):
        features = payload
    else:
        raise ValueError(f"Unsupported GeoJSON structure in {path}")

    if not isinstance(features, list):
        raise ValueError(f"Invalid features array in {path}")

    return features


def import_geojson_file(db, geojson_path: Path, collection_name: str, drop: bool) -> int:
    collection = db[collection_name]
    if drop:
        collection.drop()

    features = load_features(geojson_path)
    if not features:
        return 0

    collection.insert_many(features, ordered=False)
    try:
        collection.create_index([("geometry", "2dsphere")])
    except OperationFailure as e:
        print(
            f"[WARN] Could not create 2dsphere index on {collection_name}: {str(e)[:120]}... "
            "(coordinates may be in a projected CRS, not WGS84)"
        )
    return len(features)


def main() -> None:
    args = parse_args()

    geojson_dir = Path(args.geojson_dir)
    if not geojson_dir.exists():
        raise FileNotFoundError(f"GeoJSON directory not found: {geojson_dir}")

    client = MongoClient(args.uri)
    db = client[args.db]

    total = 0
    for geojson_name, collection_name in DEFAULT_MAPPING.items():
        geojson_path = geojson_dir / geojson_name
        if not geojson_path.exists():
            print(f"[SKIP] Missing file: {geojson_path}")
            continue

        inserted = import_geojson_file(db, geojson_path, collection_name, args.drop)
        total += inserted
        print(
            f"[OK] {geojson_name} -> {collection_name}: {inserted} document(s)"
        )

    print(f"Done. Inserted {total} document(s) into database '{args.db}'.")


if __name__ == "__main__":
    main()
