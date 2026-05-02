"""
TenzorX Geo-Spatial Engine
Looks up pre-computed geographic features from a CSV for given GPS coordinates.
Fast, zero-latency, zero network dependency during demo.

Uses only Python stdlib (csv, math) — no pandas/numpy required.
"""

import os
import csv
import math

_GEO_DATA = None
_GEO_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "geo_lookup.csv")


def _load_geo_data() -> list:
    """Load and cache geo lookup CSV as a list of dicts."""
    global _GEO_DATA
    if _GEO_DATA is None:
        _GEO_DATA = []
        with open(_GEO_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                row["lat_rounded"] = float(row["lat_rounded"])
                row["lon_rounded"] = float(row["lon_rounded"])
                row["city_tier"] = int(row["city_tier"])
                row["population_density"] = float(row["population_density"])
                row["footfall_score"] = float(row["footfall_score"])
                row["competition_count"] = int(row["competition_count"])
                row["poi_score"] = float(row["poi_score"])
                _GEO_DATA.append(row)
    return _GEO_DATA


def _tier_defaults(city_tier: int) -> dict:
    """Fallback defaults based on city tier when no CSV match found."""
    defaults = {
        1: {"population_density": 0.82, "footfall_score": 0.78, "competition_count": 11, "poi_score": 0.80},
        2: {"population_density": 0.60, "footfall_score": 0.56, "competition_count": 6,  "poi_score": 0.58},
        3: {"population_density": 0.38, "footfall_score": 0.34, "competition_count": 3,  "poi_score": 0.36},
        4: {"population_density": 0.22, "footfall_score": 0.20, "competition_count": 2,  "poi_score": 0.22},
    }
    return defaults.get(city_tier, defaults[2])


def get_geo_features(lat: float, lon: float) -> dict:
    """
    Lookup pre-computed geo features for the given GPS coordinates.

    Matching strategy:
    1. Try exact match at 2 decimal places (~1.1km grid)
    2. Try nearest within 0.05 degrees (~5km radius)
    3. Fall back to Tier 2 city defaults

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        dict with geo features and match quality indicator
    """
    data = _load_geo_data()

    # Strategy 1: exact 2-decimal match
    lat_r = round(lat, 2)
    lon_r = round(lon, 2)

    exact_matches = [
        row for row in data
        if row["lat_rounded"] == lat_r and row["lon_rounded"] == lon_r
    ]

    if exact_matches:
        row = exact_matches[0]
        return {
            "city": str(row.get("city", "Unknown")),
            "state": str(row.get("state", "Unknown")),
            "city_tier": int(row.get("city_tier", 2)),
            "population_density": float(row.get("population_density", 0.6)),
            "footfall_score": float(row.get("footfall_score", 0.5)),
            "competition_count": int(row.get("competition_count", 6)),
            "poi_score": float(row.get("poi_score", 0.55)),
            "geo_match_quality": "exact",
        }

    # Strategy 2: nearest city within ~50km
    best_row = None
    best_dist = float("inf")
    for row in data:
        dist = math.sqrt(
            (row["lat_rounded"] - lat) ** 2 + (row["lon_rounded"] - lon) ** 2
        )
        if dist < 0.50 and dist < best_dist:
            best_dist = dist
            best_row = row

    if best_row:
        return {
            "city": str(best_row.get("city", "Unknown")),
            "state": str(best_row.get("state", "Unknown")),
            "city_tier": int(best_row.get("city_tier", 2)),
            "population_density": float(best_row.get("population_density", 0.6)),
            "footfall_score": float(best_row.get("footfall_score", 0.5)),
            "competition_count": int(best_row.get("competition_count", 6)),
            "poi_score": float(best_row.get("poi_score", 0.55)),
            "geo_match_quality": "approximate",
        }

    # Strategy 3: total fallback
    return {
        "city": "Unknown",
        "state": "Unknown",
        "city_tier": 2,
        "geo_match_quality": "none",
        **_tier_defaults(2)
    }
