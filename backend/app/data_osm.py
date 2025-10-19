import random
import pandas as pd
from sqlalchemy import text
from app.db import get_engine

engine = get_engine()

def extract_osm_points(limit_customers: int = 800, limit_stores: int = 200):
    """Extract customers and darkstore candidates from PostGIS OSM import."""
    print("📍 Extracting customers and stores from PostGIS...")

    with engine.begin() as conn:
        # Use SQLAlchemy text() with proper parameter binding
        customers_query = text("""
            SELECT osm_id, ST_X(ST_Centroid(way)) AS lon, ST_Y(ST_Centroid(way)) AS lat, name, place
            FROM planet_osm_point
            WHERE "place" IN ('suburb', 'neighbourhood', 'residential')
            LIMIT :limit_customers
        """)
        stores_query = text("""
            SELECT osm_id, ST_X(ST_Centroid(way)) AS lon, ST_Y(ST_Centroid(way)) AS lat, name, shop, amenity
            FROM planet_osm_point
            WHERE "amenity" IN ('supermarket', 'convenience', 'marketplace')
               OR "shop" IN ('supermarket', 'department_store', 'grocery')
            LIMIT :limit_stores
        """)

        customers = pd.read_sql(customers_query, conn, params={"limit_customers": limit_customers})
        stores = pd.read_sql(stores_query, conn, params={"limit_stores": limit_stores})

    if customers.empty or stores.empty:
        raise ValueError("No OSM data found — did you run osm2pgsql import?")

    rng = random.Random(42)
    customers["demand"] = [rng.randint(1, 5) for _ in range(len(customers))]
    stores["fixed_cost"] = [rng.uniform(1.0, 3.0) for _ in range(len(stores))]

    print(f"✅ Loaded {len(customers)} customers, {len(stores)} stores from PostGIS.")
    return (
        stores[["osm_id", "lon", "lat", "fixed_cost"]],
        customers[["osm_id", "lon", "lat", "demand"]],
    )
