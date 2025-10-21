import math
import pandas as pd
from typing import Optional, Dict, Any
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value, PULP_CBC_CMD
from sqlalchemy import text
from app.db import get_engine
import logging

logger = logging.getLogger(__name__)
STATE: Dict[str, Any] = {}

def _haversine_minutes(lon1, lat1, lon2, lat2, speed_kmph=30.0):
    dx = (lon1 - lon2) * 111
    dy = (lat1 - lat2) * 111
    return (math.hypot(dx, dy) / speed_kmph) * 60

def _build_travel_matrix(cands, custs, city: str, use_postgis=True, speed_kmph=30.0):
    travel = {}
    engine = get_engine(city)

    if not use_postgis:
        logger.info("🧮 Using Haversine fallback.")
        for i, ci in cands.iterrows():
            for j, cu in custs.iterrows():
                travel[(i, j)] = _haversine_minutes(ci.lon, ci.lat, cu.lon, cu.lat, speed_kmph)
        return travel

    try:
        with engine.begin() as conn:
            query = text("""
                SELECT ST_DistanceSphere(
                    ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326),
                    ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326)
                ) / 1000 AS dist_km
            """)
            for i, ci in cands.iterrows():
                for j, cu in custs.iterrows():
                    dist_km = conn.execute(query, {
                        "lon1": float(ci.lon), "lat1": float(ci.lat),
                        "lon2": float(cu.lon), "lat2": float(cu.lat)
                    }).scalar() or 0
                    travel[(i, j)] = (dist_km / speed_kmph) * 60
        return travel
    except Exception as e:
        logger.warning(f"⚠️ PostGIS travel matrix failed ({e}), fallback to Haversine.")
        return _build_travel_matrix(cands, custs, city, use_postgis=False, speed_kmph=speed_kmph)

def solve_darkstores(
    candidates_df=None,
    customers_df=None,
    city: str = "delhi",
    max_time_min=10,
    store_capacity=200,
    store_fixed_cost=1.0,
    travel_speed_kmph=30.0,
    use_postgis=True,
    solver_time_limit=20
):
    if candidates_df is None or customers_df is None:
        if not STATE.get("candidates") or not STATE.get("customers"):
            raise ValueError("No data provided or available in STATE.")
        candidates_df = pd.DataFrame(STATE["candidates"])
        customers_df = pd.DataFrame(STATE["customers"])

    c, u = candidates_df.reset_index(drop=True), customers_df.reset_index(drop=True)
    c.rename(columns={"osm_id": "id"}, inplace=True, errors="ignore")
    u.rename(columns={"osm_id": "id"}, inplace=True, errors="ignore")

    u["demand"] = u.get("demand", pd.Series(1, index=u.index))
    c["fixed_cost"] = c.get("fixed_cost", pd.Series(store_fixed_cost, index=c.index))

    travel = _build_travel_matrix(c, u, city, use_postgis, travel_speed_kmph)
    coverable = {(i, j): int(travel[(i, j)] <= max_time_min) for i in range(len(c)) for j in range(len(u))}

    prob = LpProblem("DarkstoreOptimization", LpMinimize)
    y = {i: LpVariable(f"y_{i}", cat=LpBinary) for i in range(len(c))}
    x = {(i, j): LpVariable(f"x_{i}_{j}", cat=LpBinary) for i in range(len(c)) for j in range(len(u))}

    prob += lpSum(c.fixed_cost[i] * y[i] for i in range(len(c))) + lpSum(
        0.01 * travel[(i, j)] * x[(i, j)] for i in range(len(c)) for j in range(len(u))
    )

    for j in range(len(u)):
        prob += lpSum(x[(i, j)] for i in range(len(c))) == 1

    for i in range(len(c)):
        for j in range(len(u)):
            if not coverable[(i, j)]:
                prob += x[(i, j)] == 0
            prob += x[(i, j)] <= y[i]
        prob += lpSum(u.demand[j] * x[(i, j)] for j in range(len(u))) <= store_capacity * y[i]

    solver = PULP_CBC_CMD(msg=False, timeLimit=solver_time_limit)
    logger.info(f"🚀 Running solver for {city} ...")
    prob.solve(solver)

    opened = [i for i in range(len(c)) if value(y[i]) > 0.5]
    assignments = [
        {
            "customer_id": int(u.id[j]),
            "store_id": int(c.id[i]),
            "travel_min": float(travel[(i, j)]),
            "lon": float(u.lon[j]),
            "lat": float(u.lat[j])
        }
        for i in range(len(c)) for j in range(len(u)) if value(x[(i, j)]) > 0.5
    ]

    avg_t = sum(a["travel_min"] for a in assignments) / max(1, len(assignments))
    STATE["assignments"] = assignments

    return {
        "stores": [
            {"id": int(c.id[i]), "lon": float(c.lon[i]), "lat": float(c.lat[i]),
             "open": i in opened, "fixed_cost": float(c.fixed_cost[i])}
            for i in range(len(c))
        ],
        "assignments": assignments,
        "stats": {"stores_open": len(opened), "avg_travel_min": avg_t, "total_customers": len(u)},
    }
