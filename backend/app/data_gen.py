import random
import pandas as pd

def generate_candidates_and_customers(n_candidates: int = 20, n_customers: int = 300):
    """
    Generate synthetic dark store candidates & customer points
    roughly around central Delhi.
    """
    random.seed(42)
    lon_min, lon_max = 77.10, 77.30
    lat_min, lat_max = 28.55, 28.70

    candidates = [
        {
            "id": i + 1,
            "lon": random.uniform(lon_min, lon_max),
            "lat": random.uniform(lat_min, lat_max),
            "fixed_cost": round(random.uniform(0.8, 1.2), 2),
        }
        for i in range(n_candidates)
    ]

    customers = [
        {
            "id": j + 1,
            "lon": random.uniform(lon_min, lon_max),
            "lat": random.uniform(lat_min, lat_max),
            "demand": random.randint(1, 5),
            "priority": random.choice(["normal", "express"]),
        }
        for j in range(n_customers)
    ]

    print(f"✅ Generated {len(candidates)} stores and {len(customers)} customers (synthetic Delhi)")
    return candidates, customers
