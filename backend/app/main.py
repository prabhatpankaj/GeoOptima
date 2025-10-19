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
from fastapi.middleware.gzip import GZipMiddleware
from concurrent.futures import ThreadPoolExecutor

# ------------------------------------------------------------
# App Setup
# ------------------------------------------------------------
app = FastAPI(title="GeoOptima API", version="1.4.0")

# CORS setup (allow frontend on localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to ["http://localhost:3000"] for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Add GZip compression after CORS
app.add_middleware(GZipMiddleware, minimum_size=1000)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Thread pool for heavy background tasks
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
    Run optimization using either PostGIS (real) or synthetic data.
    Automatically falls back if PostGIS tables are missing.
    """
    start_time = time.time()
    source = "synthetic"
    plan = None

    try:
        if req.use_postgis:
            stores_df, customers_df = data_osm.extract_osm_points()
            optimizer_darkstores.STATE.update({
                "candidates": stores_df.to_dict("records"),
                "customers": customers_df.to_dict("records"),
            })
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
        logger.warning(f"⚠️ PostGIS/OSM failed, using synthetic: {e}")

    if plan is None:
        candidates, customers = data_gen.generate_candidates_and_customers(
            n_candidates=req.n_candidates,
            n_customers=req.n_customers,
        )
        optimizer_darkstores.STATE.update({
            "candidates": candidates,
            "customers": customers,
        })
        plan = optimizer_darkstores.solve_darkstores(
            candidates_df=None,
            customers_df=None,
            max_time_min=req.max_time_min,
            store_capacity=req.store_capacity,
            store_fixed_cost=req.store_fixed_cost,
            use_postgis=False,
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
        "stats": {**plan["stats"], **summary, "execution_time_sec": elapsed},
        "geojson": geojson,
        "assignments": plan["assignments"],
    }


@app.post("/plan/darkstores")
def plan_darkstores(max_time_min: int = 10, capacity: int = 200, fixed_cost: float = 1.0):
    """Direct PostGIS optimization (primary frontend endpoint)."""
    start_time = time.time()
    try:
        stores_df, customers_df = data_osm.extract_osm_points()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PostGIS data unavailable: {e}")

    optimizer_darkstores.STATE.update({
        "candidates": stores_df.to_dict("records"),
        "customers": customers_df.to_dict("records"),
    })

    # Run in background thread for better performance responsiveness
    future = executor.submit(
        optimizer_darkstores.solve_darkstores,
        stores_df, customers_df, max_time_min, capacity, fixed_cost, True
    )
    result = future.result(timeout=40)

    plan_df = pd.DataFrame(result["stores"])
    summary = summarize_plan(plan_df)
    elapsed = round(time.time() - start_time, 2)

    optimizer_darkstores.STATE.update({
        "plan_df": plan_df.to_dict("records"),
        "assignments": result["assignments"],
    })

    result["stats"].update(summary)
    result["stats"]["execution_time_sec"] = elapsed

    return {"geojson": to_geojson(result["stores"]), "stats": result["stats"]}


@app.get("/plan/insights")
def plan_insights():
    """Post-optimization analytics: coverage, clusters, and cost patterns."""
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
    """Inspect the currently loaded dataset in memory."""
    state = optimizer_darkstores.STATE
    return {
        "candidates": len(state.get("candidates", [])),
        "customers": len(state.get("customers", [])),
        "has_plan": "plan_df" in state,
    }
