import random
from app.db import get_engine
import pandas as pd
import os

engine = get_engine()

def extract_osm_points():
    """Extract real customer & darkstore coordinates from PostGIS (OSM tables)."""
    print("📍 Extracting customers and stores from PostGIS...")

    with engine.begin() as conn:
        customers = pd.read_sql("""
            SELECT osm_id, ST_X(ST_Centroid(way)) AS lon, ST_Y(ST_Centroid(way)) AS lat
            FROM planet_osm_point
            WHERE "place" IN ('suburb', 'neighbourhood', 'residential')
            LIMIT 800
        """, conn)

        stores = pd.read_sql("""
            SELECT osm_id, ST_X(ST_Centroid(way)) AS lon, ST_Y(ST_Centroid(way)) AS lat
            FROM planet_osm_point
            WHERE "amenity" IN ('supermarket', 'convenience', 'marketplace')
               OR "shop" IN ('supermarket', 'department_store', 'grocery')
            LIMIT 200
        """, conn)

    if customers.empty or stores.empty:
        raise ValueError("No OSM data found — did you run osm2pgsql import?")

    rng = random.Random(42)
    customers["demand"] = [rng.randint(1, 5) for _ in range(len(customers))]
    stores["fixed_cost"] = [rng.uniform(1.0, 3.0) for _ in range(len(stores))]

    print(f"✅ Loaded {len(customers)} customers, {len(stores)} stores from OSM.")
    return stores[["osm_id", "lon", "lat", "fixed_cost"]], customers[["osm_id", "lon", "lat", "demand"]]
