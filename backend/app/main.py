from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from app import optimizer_darkstores, data_osm, data_gen
from app.utils_graph import to_geojson
import pandas as pd
import numpy as np
import time
import logging
from sklearn.cluster import KMeans
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from concurrent.futures import ThreadPoolExecutor
import os
from sqlalchemy import text
from app.db import get_engine, get_postgres_engine

# ------------------------------------------------------------
# App Setup
# ------------------------------------------------------------
app = FastAPI(title="GeoOptima API", version="1.6.0")

# ✅ CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to known origins in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

executor = ThreadPoolExecutor(max_workers=2)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def summarize_plan(plan_df: pd.DataFrame):
    """Generate quick summary stats for visualization and monitoring."""
    if plan_df.empty:
        return {}

    open_stores = plan_df.query("open == True")
    closed_stores = plan_df.query("open == False")

    return {
        "total_candidates": len(plan_df),
        "open_stores": len(open_stores),
        "closed_stores": len(closed_stores),
        "open_pct": round(len(open_stores) / len(plan_df) * 100, 2),
        "avg_fixed_cost_open": float(open_stores["fixed_cost"].mean() or 0),
        "avg_fixed_cost_closed": float(closed_stores["fixed_cost"].mean() or 0),
        "geo_bounds": {
            "min_lat": float(plan_df["lat"].min()),
            "max_lat": float(plan_df["lat"].max()),
            "min_lon": float(plan_df["lon"].min()),
            "max_lon": float(plan_df["lon"].max()),
        },
    }


def compute_geographic_clusters(plan_df: pd.DataFrame, n_clusters: int = 5):
    """Cluster open stores geographically for macro-level analysis."""
    open_df = plan_df[plan_df["open"]]
    if open_df.empty:
        return []

    coords = open_df[["lat", "lon"]].to_numpy()
    n_clusters = min(n_clusters, len(coords))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    open_df["cluster"] = kmeans.fit_predict(coords)
    centroids = kmeans.cluster_centers_

    return [
        {
            "cluster_id": int(i),
            "count": len(open_df[open_df["cluster"] == i]),
            "center_lat": float(center[0]),
            "center_lon": float(center[1]),
            "avg_fixed_cost": float(open_df.loc[open_df["cluster"] == i, "fixed_cost"].mean()),
        }
        for i, center in enumerate(centroids)
    ]


def compute_coverage_stats():
    """Compute delivery time distribution from assignments."""
    assignments = optimizer_darkstores.STATE.get("assignments", [])
    if not assignments:
        return {}

    travel_times = np.array([a["travel_min"] for a in assignments])
    return {
        "avg_travel_min": float(np.mean(travel_times)),
        "p90_travel_min": float(np.percentile(travel_times, 90)),
        "max_travel_min": float(np.max(travel_times)),
    }

# ------------------------------------------------------------
# Request Model
# ------------------------------------------------------------
class PlanRequest(BaseModel):
    city: str = "delhi"
    max_time_min: int = 10
    store_capacity: int = 200
    store_fixed_cost: float = 1.0
    n_candidates: int = 20
    n_customers: int = 300
    use_postgis: bool = True

# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------

@app.get("/plan/cities")
def list_available_cities():
    """
    Dynamically list all city databases available in PostGIS (geodb_*).
    Example output: {"cities": ["delhi", "noida", "gurgaon", "faridabad", "ghaziabad"]}
    """
    engine = get_postgres_engine()

    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("SELECT datname FROM pg_database WHERE datname LIKE 'geodb_%';")
            ).fetchall()
            cities = [r[0].replace("geodb_", "") for r in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query cities: {e}")

    if not cities:
        cities = ["delhi"]

    logger.info(f"🏙️ Available cities: {', '.join(cities)}")
    return {"cities": sorted(cities)}


@app.post("/generate")
def generate(req: PlanRequest):
    """Generate synthetic customers and darkstore candidates."""
    candidates, customers = data_gen.generate_candidates_and_customers(
        n_candidates=req.n_candidates,
        n_customers=req.n_customers,
    )
    optimizer_darkstores.STATE.update({
        "candidates": candidates,
        "customers": customers,
    })
    return {
        "mode": "synthetic",
        "candidates": len(candidates),
        "customers": len(customers),
    }


@app.post("/plan/network")
def plan_network(req: PlanRequest):
    """
    Run optimization using PostGIS (real OSM) or synthetic fallback.
    """
    start_time = time.time()
    plan = None
    source = "synthetic"

    try:
        if req.use_postgis:
            stores_df, customers_df = data_osm.extract_osm_points(city=req.city)
            optimizer_darkstores.STATE.update({
                "candidates": stores_df.to_dict("records"),
                "customers": customers_df.to_dict("records"),
            })
            plan = optimizer_darkstores.solve_darkstores(
                stores_df, customers_df, req.city,
                req.max_time_min, req.store_capacity,
                req.store_fixed_cost, True
            )
            source = f"osm:{req.city}"
    except Exception as e:
        logger.warning(f"⚠️ PostGIS/OSM failed for {req.city}, using synthetic fallback: {e}")

    if plan is None:
        # fallback synthetic generation
        candidates, customers = data_gen.generate_candidates_and_customers(
            n_candidates=req.n_candidates,
            n_customers=req.n_customers,
        )
        optimizer_darkstores.STATE.update({
            "candidates": candidates,
            "customers": customers,
        })
        plan = optimizer_darkstores.solve_darkstores(
            None, None, req.city, req.max_time_min, req.store_capacity,
            req.store_fixed_cost, False
        )

    elapsed = round(time.time() - start_time, 2)
    plan_df = pd.DataFrame(plan["stores"])
    summary = summarize_plan(plan_df)
    geojson = to_geojson(plan["stores"])

    optimizer_darkstores.STATE.update({
        "plan_df": plan_df.to_dict("records"),
        "assignments": plan["assignments"],
    })

    return {
        "source": source,
        "city": req.city,
        "stats": {**plan["stats"], **summary, "execution_time_sec": elapsed},
        "geojson": geojson,
        "assignments": plan["assignments"],
    }


@app.post("/plan/darkstores")
def plan_darkstores(
    city: str = Query("delhi", description="City name (delhi, noida, gurgaon, faridabad, ghaziabad)"),
    max_time_min: int = 10,
    capacity: int = 200,
    fixed_cost: float = 1.0
):
    """Run direct optimization from PostGIS data for the selected city."""
    start_time = time.time()

    try:
        stores_df, customers_df = data_osm.extract_osm_points(city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PostGIS data unavailable for {city}: {e}")

    optimizer_darkstores.STATE.update({
        "candidates": stores_df.to_dict("records"),
        "customers": customers_df.to_dict("records"),
    })

    # Use async execution for CPU-bound optimization
    future = executor.submit(
        optimizer_darkstores.solve_darkstores,
        stores_df, customers_df, city, max_time_min, capacity, fixed_cost, True
    )
    result = future.result(timeout=120)

    plan_df = pd.DataFrame(result["stores"])
    summary = summarize_plan(plan_df)
    elapsed = round(time.time() - start_time, 2)

    optimizer_darkstores.STATE.update({
        "plan_df": plan_df.to_dict("records"),
        "assignments": result["assignments"],
    })

    result["stats"].update(summary)
    result["stats"]["execution_time_sec"] = elapsed
    result["stats"]["city"] = city

    logger.info(f"✅ Optimization complete for {city} ({elapsed}s)")
    return {
        "city": city,
        "geojson": to_geojson(result["stores"]),
        "stats": result["stats"],
    }


@app.get("/plan/insights")
def plan_insights():
    """Return post-optimization analytics: coverage, clusters, and cost patterns."""
    plan_data = optimizer_darkstores.STATE.get("plan_df")
    if not plan_data:
        raise HTTPException(status_code=404, detail="No plan found. Run /plan/darkstores first.")

    plan_df = pd.DataFrame(plan_data)
    insights = {
        "summary": summarize_plan(plan_df),
        "coverage": compute_coverage_stats(),
        "clusters": compute_geographic_clusters(plan_df),
    }
    return insights


@app.get("/state")
def get_state():
    """Inspect current optimizer memory state."""
    state = optimizer_darkstores.STATE
    return {
        "candidates": len(state.get("candidates", [])),
        "customers": len(state.get("customers", [])),
        "has_plan": "plan_df" in state,
    }
