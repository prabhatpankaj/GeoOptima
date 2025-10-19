# Placeholder for map visualization helpers

def to_geojson(points, key_lon="lon", key_lat="lat"):
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [p[key_lon], p[key_lat]]}, "properties": p}
            for p in points
        ],
    }
