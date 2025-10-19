import random
import pandas as pd
from typing import Tuple, List, Dict

def generate_candidates_and_customers(
    n_candidates: int = 20, 
    n_customers: int = 300,
    bounds: Dict[str, float] = {"lon_min": 77.10, "lon_max": 77.30, "lat_min": 28.55, "lat_max": 28.70}
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate synthetic darkstore candidates & customers
    around central Delhi (default bounding box).
    """
    random.seed(42)

    lon_min, lon_max = bounds["lon_min"], bounds["lon_max"]
    lat_min, lat_max = bounds["lat_min"], bounds["lat_max"]

    candidates = pd.DataFrame({
        "id": range(1, n_candidates + 1),
        "lon": [random.uniform(lon_min, lon_max) for _ in range(n_candidates)],
        "lat": [random.uniform(lat_min, lat_max) for _ in range(n_candidates)],
        "fixed_cost": [round(random.uniform(0.8, 1.2), 2) for _ in range(n_candidates)],
    })

    customers = pd.DataFrame({
        "id": range(1, n_customers + 1),
        "lon": [random.uniform(lon_min, lon_max) for _ in range(n_customers)],
        "lat": [random.uniform(lat_min, lat_max) for _ in range(n_customers)],
        "demand": [random.randint(1, 5) for _ in range(n_customers)],
        "priority": [random.choice(["normal", "express"]) for _ in range(n_customers)],
    })

    print(f"✅ Generated {len(candidates)} stores and {len(customers)} customers (synthetic Delhi)")
    return candidates.to_dict("records"), customers.to_dict("records")
