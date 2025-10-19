from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from app import optimizer_darkstores, data_osm, data_gen
from app.utils_graph import to_geojson
import pandas as pd
import numpy as np
import time
import logging
from sklearn.cluster import KMeans
from fastapi.middleware.cors import CORSMiddleware

# ------------------------------------------------------------
# App Setup
# ------------------------------------------------------------
app = FastAPI(title="Geo Darkstore Optimizer API", version="1.3.0")

# CORS setup (allow frontend on localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def summarize_plan(plan_df):
    """Generate insight stats for visualization and monitoring."""
    open_stores = plan_df[plan_df["open"]]
    closed_stores = plan_df[~plan_df["open"]]
    
    return {
        "total_candidates": len(plan_df),
        "open_stores": len(open_stores),
        "closed_stores": len(closed_stores),
        "open_pct": round(len(open_stores) / len(plan_df) * 100, 2) if len(plan_df) else 0,
        "avg_fixed_cost_open": float(open_stores["fixed_cost"].mean()) if not open_stores.empty else 0,
        "avg_fixed_cost_closed": float(closed_stores["fixed_cost"].mean()) if not closed_stores.empty else 0,
        "geo_bounds": {
            "min_lat": float(plan_df["lat"].min()) if not plan_df.empty else None,
            "max_lat": float(plan_df["lat"].max()) if not plan_df.empty else None,
            "min_lon": float(plan_df["lon"].min()) if not plan_df.empty else None,
            "max_lon": float(plan_df["lon"].max()) if not plan_df.empty else None,
        },
    }


def compute_geographic_clusters(plan_df: pd.DataFrame, n_clusters: int = 5):
    """Cluster open stores into regions for higher-level insights."""
    open_df = plan_df[plan_df["open"]]
    if open_df.empty:
        return []

    coords = open_df[["lat", "lon"]].to_numpy()
    n_clusters = min(n_clusters, len(coords))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    open_df["cluster"] = kmeans.fit_predict(coords)
    centroids = kmeans.cluster_centers_

    clusters = []
    for i, center in enumerate(centroids):
        group = open_df[open_df["cluster"] == i]
        clusters.append({
            "cluster_id": int(i),
            "count": len(group),
            "center_lat": float(center[0]),
            "center_lon": float(center[1]),
            "avg_fixed_cost": float(group["fixed_cost"].mean()),
        })

    return clusters


def compute_coverage_stats(plan_df: pd.DataFrame):
    """Compute delivery time distribution for customers."""
    assignments = optimizer_darkstores.STATE.get("assignments", [])
    if not assignments:
        return {}

    travel_times = [a["travel_min"] for a in assignments]
    return {
        "avg_travel_min": float(np.mean(travel_times)),
        "p90_travel_min": float(np.percentile(travel_times, 90)),
        "max_travel_min": float(np.max(travel_times)),
    }

# ------------------------------------------------------------
# Request Model
# ------------------------------------------------------------

class PlanRequest(BaseModel):
    """Request schema for network optimization or data generation."""
    max_time_min: int = 10
    store_capacity: int = 200
    store_fixed_cost: float = 1.0
    n_candidates: int = 20
    n_customers: int = 300
    use_postgis: bool = True


# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------

@app.post("/generate")
def generate(req: PlanRequest):
    """Generate synthetic customers and dark store candidates."""
    candidates, customers = data_gen.generate_candidates_and_customers(
        n_candidates=req.n_candidates,
        n_customers=req.n_customers,
    )
    optimizer_darkstores.STATE["candidates"] = candidates
    optimizer_darkstores.STATE["customers"] = customers
    return {"mode": "synthetic", "candidates": len(candidates), "customers": len(customers)}


@app.post("/plan/network")
def plan_network(req: PlanRequest):
    """
    Optimize darkstore placement & assignment.
    Uses PostGIS data if available; otherwise falls back to synthetic data.
    """
    source = "synthetic"
    plan = None
    start_time = time.time()

    # Try PostGIS first
    if req.use_postgis:
        try:
            stores_df, customers_df = data_osm.extract_osm_points()
            optimizer_darkstores.STATE["candidates"] = stores_df.to_dict(orient="records")
            optimizer_darkstores.STATE["customers"] = customers_df.to_dict(orient="records")

            plan = optimizer_darkstores.solve_darkstores(
                candidates_df=stores_df,
                customers_df=customers_df,
                max_time_min=req.max_time_min,
                store_capacity=req.store_capacity,
                store_fixed_cost=req.store_fixed_cost,
                use_postgis=True,
            )
            source = "osm"
        except Exception as e:
            logger.warning(f"⚠️ PostGIS/OSM failed, falling back to synthetic: {e}")

    # Fallback: synthetic mode
    if plan is None:
        candidates, customers = data_gen.generate_candidates_and_customers(
            n_candidates=req.n_candidates,
            n_customers=req.n_customers,
        )
        optimizer_darkstores.STATE["candidates"] = candidates
        optimizer_darkstores.STATE["customers"] = customers

        plan = optimizer_darkstores.solve_darkstores(
            candidates_df=None,
            customers_df=None,
            max_time_min=req.max_time_min,
            store_capacity=req.store_capacity,
            store_fixed_cost=req.store_fixed_cost,
            use_postgis=False,
        )

    elapsed_sec = round(time.time() - start_time, 2)

    # Convert results
    plan_df = pd.DataFrame(plan["stores"])
    summary = summarize_plan(plan_df)
    geojson = to_geojson(plan["stores"])

    # Persist for insights
    optimizer_darkstores.STATE["plan_df"] = plan_df.to_dict(orient="records")
    optimizer_darkstores.STATE["assignments"] = plan["assignments"]

    return {
        "source": source,
        "stats": {**plan["stats"], **summary, "execution_time_sec": elapsed_sec},
        "geojson": geojson,
        "assignments": plan["assignments"],
    }


@app.post("/plan/darkstores")
def plan_darkstores(max_time_min: int = 10, capacity: int = 200, fixed_cost: float = 1.0):
    """Quick endpoint for direct PostGIS optimization (used by frontend)."""
    start_time = time.time()

    stores_df, customers_df = data_osm.extract_osm_points()
    optimizer_darkstores.STATE["candidates"] = stores_df.to_dict(orient="records")
    optimizer_darkstores.STATE["customers"] = customers_df.to_dict(orient="records")

    result = optimizer_darkstores.solve_darkstores(
        candidates_df=stores_df,
        customers_df=customers_df,
        max_time_min=max_time_min,
        store_capacity=capacity,
        store_fixed_cost=fixed_cost,
        use_postgis=True,
    )

    elapsed_sec = round(time.time() - start_time, 2)
    plan_df = pd.DataFrame(result["stores"])
    summary = summarize_plan(plan_df)

    optimizer_darkstores.STATE["plan_df"] = plan_df.to_dict(orient="records")
    optimizer_darkstores.STATE["assignments"] = result["assignments"]

    result["stats"]["execution_time_sec"] = elapsed_sec
    result["stats"].update(summary)

    return {"geojson": to_geojson(result["stores"]), "stats": result["stats"]}


@app.get("/plan/insights")
def plan_insights():
    """
    Post-optimization analytics:
      - coverage stats (avg / p90 delivery time)
      - geographic clusters (KMeans)
      - fixed cost insights
    """
    if "plan_df" not in optimizer_darkstores.STATE:
        raise HTTPException(status_code=404, detail="No optimization plan found. Run /plan/darkstores first.")

    plan_df = pd.DataFrame(optimizer_darkstores.STATE["plan_df"])

    insights = {
        "summary": summarize_plan(plan_df),
        "coverage": compute_coverage_stats(plan_df),
        "clusters": compute_geographic_clusters(plan_df),
    }
    return insights


@app.get("/state")
def get_state():
    """Inspect currently loaded in-memory candidate and customer data."""
    return {
        "candidates": len(optimizer_darkstores.STATE.get("candidates", [])),
        "customers": len(optimizer_darkstores.STATE.get("customers", [])),
        "has_plan": "plan_df" in optimizer_darkstores.STATE,
    }
