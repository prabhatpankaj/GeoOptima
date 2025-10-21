import random
import pandas as pd
from sqlalchemy import text
from app.db import get_engine

def extract_osm_points(city: str = "delhi", limit_customers: int = 800, limit_stores: int = 200):
    """Extract customers & store candidates from a city-specific PostGIS DB."""
    print(f"📍 Extracting OSM data from PostGIS ({city}) ...")
    engine = get_engine(city)

    with engine.begin() as conn:
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
        raise ValueError(f"No OSM data found for {city}. Run osm2pgsql import first.")

    rng = random.Random(42)
    customers["demand"] = [rng.randint(1, 5) for _ in range(len(customers))]
    stores["fixed_cost"] = [rng.uniform(1.0, 3.0) for _ in range(len(stores))]

    print(f"✅ Loaded {len(customers)} customers, {len(stores)} stores from {city}.")
    return (
        stores[["osm_id", "lon", "lat", "fixed_cost"]],
        customers[["osm_id", "lon", "lat", "demand"]],
    )
