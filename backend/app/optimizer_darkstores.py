import math
import pandas as pd
from typing import Optional, Dict, Any
from pulp import (
    LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value, PULP_CBC_CMD
)
from sqlalchemy import text
from app.db import get_engine
import logging

# ---------------------------------------
# Global setup
# ---------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

engine = get_engine()
STATE: Dict[str, Any] = {}


# ---------------------------------------
# Helper functions
# ---------------------------------------

def _haversine_minutes(lon1, lat1, lon2, lat2, speed_kmph=30.0):
    """Approximate travel time between coordinates in minutes."""
    dx = (lon1 - lon2) * 111
    dy = (lat1 - lat2) * 111
    return (math.hypot(dx, dy) / speed_kmph) * 60


def _build_travel_matrix(cands, custs, speed_kmph=30.0, use_postgis=True):
    """Build travel time matrix using PostGIS or fallback to Haversine."""
    if not use_postgis:
        logger.info("🧮 Using Haversine-based travel times (no PostGIS)")
        return {
            (i, j): _haversine_minutes(float(ci.lon), float(ci.lat), float(cu.lon), float(cu.lat), speed_kmph)
            for i, ci in cands.iterrows() for j, cu in custs.iterrows()
        }

    try:
        travel = {}
        with engine.begin() as conn:
            for i, ci in cands.iterrows():
                lon1, lat1 = float(ci.lon), float(ci.lat)
                for j, cu in custs.iterrows():
                    lon2, lat2 = float(cu.lon), float(cu.lat)

                    # Always cast to Python float to avoid np.float64 schema issues
                    q = text("""
                        SELECT ST_DistanceSphere(
                            ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326),
                            ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)
                        ) / 1000 AS dist_km
                    """)

                    res = conn.execute(q, {
                        "lon1": float(lon1),
                        "lat1": float(lat1),
                        "lon2": float(lon2),
                        "lat2": float(lat2)
                    }).scalar()

                    dist_km = float(res or 0.0)
                    travel[(i, j)] = (dist_km / speed_kmph) * 60.0

        logger.info(f"✅ Built PostGIS travel matrix ({len(travel)} entries)")
        return travel

    except Exception as e:
        logger.warning(f"⚠️ PostGIS travel matrix failed ({e}), falling back to Haversine.")
        return {
            (i, j): _haversine_minutes(float(ci.lon), float(ci.lat), float(cu.lon), float(cu.lat), speed_kmph)
            for i, ci in cands.iterrows() for j, cu in custs.iterrows()
        }


# ---------------------------------------
# Main optimization routine
# ---------------------------------------

def solve_darkstores(
    candidates_df: Optional[pd.DataFrame] = None,
    customers_df: Optional[pd.DataFrame] = None,
    max_time_min: int = 10,
    store_capacity: int = 200,
    store_fixed_cost: float = 1.0,
    travel_speed_kmph: float = 30.0,
    use_postgis: bool = True,
    solver_time_limit: int = 30
) -> Dict[str, Any]:
    """
    Solves the darkstore facility-location problem:
      - Select stores to open (binary variable y_i)
      - Assign customers to stores (binary variable x_ij)
      - Respect max delivery time, capacity, and cost

    Automatically falls back to STATE data if inputs are None.
    """
    # -----------------------------------
    # Handle missing input DataFrames
    # -----------------------------------
    if candidates_df is None or customers_df is None:
        if "candidates" in STATE and "customers" in STATE:
            logger.info("🔁 Using in-memory STATE data for optimization.")
            candidates_df = pd.DataFrame(STATE["candidates"])
            customers_df = pd.DataFrame(STATE["customers"])
        else:
            raise ValueError("❌ No data provided or available in STATE.")

    if candidates_df.empty or customers_df.empty:
        raise ValueError("❌ Candidate or customer dataset is empty.")

    # -----------------------------------
    # Normalize column names
    # -----------------------------------
    c = candidates_df.reset_index(drop=True).copy()
    u = customers_df.reset_index(drop=True).copy()

    if "osm_id" in c.columns:
        c.rename(columns={"osm_id": "id"}, inplace=True)
    if "osm_id" in u.columns:
        u.rename(columns={"osm_id": "id"}, inplace=True)

    if "demand" not in u:
        u["demand"] = 1
    if "fixed_cost" not in c:
        c["fixed_cost"] = store_fixed_cost

    # Ensure all coordinates are plain Python floats
    c["lon"] = c["lon"].astype(float)
    c["lat"] = c["lat"].astype(float)
    u["lon"] = u["lon"].astype(float)
    u["lat"] = u["lat"].astype(float)

    logger.info(f"📊 Solving for {len(c)} stores, {len(u)} customers")

    # -----------------------------------
    # Build travel matrix & coverage mask
    # -----------------------------------
    travel = _build_travel_matrix(c, u, travel_speed_kmph, use_postgis)
    coverable = {
        (i, j): int(travel[(i, j)] <= max_time_min)
        for i in range(len(c)) for j in range(len(u))
    }

    # -----------------------------------
    # Define MILP model
    # -----------------------------------
    prob = LpProblem("DarkstoreOptimization", LpMinimize)

    y = {i: LpVariable(f"y_{i}", cat=LpBinary) for i in range(len(c))}
    x = {(i, j): LpVariable(f"x_{i}_{j}", cat=LpBinary)
         for i in range(len(c)) for j in range(len(u))}

    # Objective: open store costs + weighted travel time
    prob += lpSum(
        c.fixed_cost[i] * y[i] for i in range(len(c))
    ) + lpSum(
        0.01 * travel[(i, j)] * x[(i, j)] for i in range(len(c)) for j in range(len(u))
    )

    # Each customer assigned to exactly one store
    for j in range(len(u)):
        prob += lpSum(x[(i, j)] for i in range(len(c))) == 1

    # Assign only to open stores & within coverage
    for i in range(len(c)):
        for j in range(len(u)):
            if not coverable[(i, j)]:
                prob += x[(i, j)] == 0
            prob += x[(i, j)] <= y[i]

    # Capacity constraint
    for i in range(len(c)):
        prob += lpSum(u.demand[j] * x[(i, j)] for j in range(len(u))) <= store_capacity * y[i]

    # -----------------------------------
    # Solve MILP
    # -----------------------------------
    solver = PULP_CBC_CMD(msg=False, timeLimit=solver_time_limit)
    logger.info(f"🚀 Starting solver (limit={solver_time_limit}s)...")
    prob.solve(solver)

    opened = [i for i in range(len(c)) if value(y[i]) > 0.5]

    # -----------------------------------
    # Build solution output
    # -----------------------------------
    assignments = []
    for j in range(len(u)):
        for i in range(len(c)):
            if value(x[(i, j)]) > 0.5:
                assignments.append({
                    "customer_id": int(u.id[j]),
                    "store_id": int(c.id[i]),
                    "travel_min": float(travel[(i, j)]),
                    "lon": float(u.lon[j]),
                    "lat": float(u.lat[j])
                })
                break

    avg_t = sum(a["travel_min"] for a in assignments) / max(1, len(assignments))

    return {
        "stores": [
            {
                "id": int(c.id[i]),
                "lon": float(c.lon[i]),
                "lat": float(c.lat[i]),
                "open": i in opened,
                "fixed_cost": float(c.fixed_cost[i]),
            }
            for i in range(len(c))
        ],
        "assignments": assignments,
        "stats": {
            "stores_open": len(opened),
            "avg_travel_min": avg_t,
            "total_customers": len(u),
        },
    }
