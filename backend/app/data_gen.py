import random
import pandas as pd
from typing import Tuple, List, Dict

# -----------------------------------------------------------
# Predefined bounding boxes for NCR cities
# (Approximate geographic limits)
# -----------------------------------------------------------
CITY_BOUNDS = {
    "delhi": {"lon_min": 76.84, "lon_max": 77.38, "lat_min": 28.38, "lat_max": 28.88},
    "noida": {"lon_min": 77.28, "lon_max": 77.45, "lat_min": 28.45, "lat_max": 28.63},
    "gurgaon": {"lon_min": 76.92, "lon_max": 77.10, "lat_min": 28.36, "lat_max": 28.53},
    "faridabad": {"lon_min": 77.25, "lon_max": 77.45, "lat_min": 28.33, "lat_max": 28.52},
    "ghaziabad": {"lon_min": 77.35, "lon_max": 77.55, "lat_min": 28.60, "lat_max": 28.78},
}

# -----------------------------------------------------------
# Generate synthetic store and customer data
# -----------------------------------------------------------
def generate_candidates_and_customers(
    city: str = "delhi",
    n_candidates: int = 20,
    n_customers: int = 300
) -> Tuple[List[Dict], List[Dict]]:
    """
    Generate synthetic darkstore candidates & customers within city bounding box.

    Args:
        city (str): City name from CITY_BOUNDS.
        n_candidates (int): Number of darkstore candidates.
        n_customers (int): Number of customer points.

    Returns:
        (List[Dict], List[Dict]): (candidates, customers)
    """
    city = city.lower()
    if city not in CITY_BOUNDS:
        raise ValueError(f"Unsupported city '{city}'. Choose from {list(CITY_BOUNDS.keys())}")

    bounds = CITY_BOUNDS[city]
    random.seed(42)

    lon_min, lon_max = bounds["lon_min"], bounds["lon_max"]
    lat_min, lat_max = bounds["lat_min"], bounds["lat_max"]

    candidates = pd.DataFrame({
        "id": range(1, n_candidates + 1),
        "lon": [random.uniform(lon_min, lon_max) for _ in range(n_candidates)],
        "lat": [random.uniform(lat_min, lat_max) for _ in range(n_candidates)],
        "fixed_cost": [round(random.uniform(0.8, 1.2), 2) for _ in range(n_candidates)],
        "city": city,
    })

    customers = pd.DataFrame({
        "id": range(1, n_customers + 1),
        "lon": [random.uniform(lon_min, lon_max) for _ in range(n_customers)],
        "lat": [random.uniform(lat_min, lat_max) for _ in range(n_customers)],
        "demand": [random.randint(1, 5) for _ in range(n_customers)],
        "priority": [random.choice(["normal", "express"]) for _ in range(n_customers)],
        "city": city,
    })

    print(f"✅ Generated {len(candidates)} stores and {len(customers)} customers for '{city.title()}'.")
    return candidates.to_dict("records"), customers.to_dict("records")

# -----------------------------------------------------------
# Optional: standalone test mode
# -----------------------------------------------------------
if __name__ == "__main__":
    candidates, customers = generate_candidates_and_customers(city="noida", n_candidates=15, n_customers=100)
    print(candidates[:2])
    print(customers[:2])
