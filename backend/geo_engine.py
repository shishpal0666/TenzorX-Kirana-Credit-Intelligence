"""
TenzorX Geo-Spatial Engine
Looks up pre-computed geographic features from a CSV for given GPS coordinates.
Fast, zero-latency, zero network dependency during demo.
"""

import os
import pandas as pd
import numpy as np

_GEO_DATA = None
_GEO_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "geo_lookup.csv")


def _load_geo_data() -> pd.DataFrame:
    """Load and cache geo lookup CSV."""
    global _GEO_DATA
    if _GEO_DATA is None:
        _GEO_DATA = pd.read_csv(_GEO_CSV_PATH)
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
    df = _load_geo_data()

    # Strategy 1: exact 2-decimal match
    lat_r = round(lat, 2)
    lon_r = round(lon, 2)
    match = df[(df["lat_rounded"] == lat_r) & (df["lon_rounded"] == lon_r)]

    match_quality = "exact"

    if len(match) == 0:
        # Strategy 2: nearest within ~5km
        df["_dist"] = np.sqrt((df["lat_rounded"] - lat) ** 2 + (df["lon_rounded"] - lon) ** 2)
        closest = df[df["_dist"] < 0.05].sort_values("_dist")
        if len(closest) > 0:
            match = closest.iloc[[0]]
            match_quality = "approximate"

    if len(match) == 0:
        # Strategy 3: total fallback
        return {
            "city": "Unknown",
            "state": "Unknown",
            "city_tier": 2,
            "geo_match_quality": "none",
            **_tier_defaults(2)
        }

    row = match.iloc[0]
    city_tier = int(row.get("city_tier", 2))

    return {
        "city": str(row.get("city", "Unknown")),
        "state": str(row.get("state", "Unknown")),
        "city_tier": city_tier,
        "population_density": float(row.get("population_density", 0.6)),
        "footfall_score": float(row.get("footfall_score", 0.5)),
        "competition_count": int(row.get("competition_count", 6)),
        "poi_score": float(row.get("poi_score", 0.55)),
        "geo_match_quality": match_quality,
    }
