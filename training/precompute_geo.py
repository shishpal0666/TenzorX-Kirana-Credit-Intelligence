"""
TenzorX Geo Pre-Computation Script
Queries OpenStreetMap Overpass API to build geo_lookup.csv for a set of coordinates.

Run this BEFORE the hackathon on your laptop (not during demo).
Output: geo_lookup.csv → copy to backend/data/geo_lookup.csv

Install: pip install overpy pandas numpy
Usage  : python precompute_geo.py
"""

import time
import math
import pandas as pd
import numpy as np

try:
    import overpy
except ImportError:
    print("Install overpy: pip install overpy")
    raise

# ─────────────────────────────────────────────────────────────────────────────
# Locations to pre-compute
# Add any lat/lon you plan to demo with
# ─────────────────────────────────────────────────────────────────────────────
LOCATIONS = [
    # (lat, lon, city, state, city_tier)
    (19.0760, 72.8777, "Mumbai",       "Maharashtra",   1),
    (18.5204, 73.8567, "Pune",         "Maharashtra",   1),
    (28.6139, 77.2090, "Delhi",        "Delhi",         1),
    (12.9716, 77.5946, "Bangalore",    "Karnataka",     1),
    (13.0827, 80.2707, "Chennai",      "Tamil Nadu",    1),
    (22.5726, 88.3639, "Kolkata",      "West Bengal",   1),
    (17.3850, 78.4867, "Hyderabad",    "Telangana",     1),
    (23.0225, 72.5714, "Ahmedabad",    "Gujarat",       2),
    (21.1702, 72.8311, "Surat",        "Gujarat",       2),
    (26.9124, 75.7873, "Jaipur",       "Rajasthan",     2),
    (26.8467, 80.9462, "Lucknow",      "Uttar Pradesh", 2),
    (22.7196, 75.8577, "Indore",       "Madhya Pradesh",2),
    (30.9010, 75.8573, "Ludhiana",     "Punjab",        2),
    (21.1458, 79.0882, "Nagpur",       "Maharashtra",   2),
    (25.5941, 85.1376, "Patna",        "Bihar",         2),
    (24.5854, 73.7125, "Udaipur",      "Rajasthan",     3),
    (20.2961, 85.8245, "Bhubaneswar",  "Odisha",        3),
    (30.3165, 78.0322, "Dehradun",     "Uttarakhand",   3),
    (10.7867, 76.6548, "Thrissur",     "Kerala",        3),
    (15.8497, 74.4977, "Belgaum",      "Karnataka",     3),
]

RADIUS_M = 500  # 500-meter radius for competitor/POI count


def overpass_query(lat: float, lon: float, radius: int = RADIUS_M) -> dict:
    """
    Query OpenStreetMap Overpass API for nearby features.
    Returns counts of competitors and POIs (schools, transit, offices).
    """
    api = overpy.Overpass()

    query = f"""
    [out:json][timeout:30];
    (
      node["shop"="convenience"](around:{radius},{lat},{lon});
      node["shop"="supermarket"](around:{radius},{lat},{lon});
      node["shop"="grocery"](around:{radius},{lat},{lon});
      node["amenity"="school"](around:{radius},{lat},{lon});
      node["amenity"="college"](around:{radius},{lat},{lon});
      node["amenity"="bus_station"](around:{radius},{lat},{lon});
      node["highway"="bus_stop"](around:{radius},{lat},{lon});
      node["amenity"="office"](around:{radius},{lat},{lon});
      node["office"](around:{radius},{lat},{lon});
    );
    out count;
    """

    result = api.query(query)
    total = len(result.nodes) if result.nodes else 0

    # Separate queries for cleaner counts
    comp_query = f"""
    [out:json][timeout:20];
    (
      node["shop"="convenience"](around:{radius},{lat},{lon});
      node["shop"="supermarket"](around:{radius},{lat},{lon});
      node["shop"="grocery"](around:{radius},{lat},{lon});
    );
    out count;
    """
    poi_query = f"""
    [out:json][timeout:20];
    (
      node["amenity"="school"](around:{radius},{lat},{lon});
      node["amenity"="college"](around:{radius},{lat},{lon});
      node["amenity"="bus_station"](around:{radius},{lat},{lon});
      node["highway"="bus_stop"](around:{radius},{lat},{lon});
      node["amenity"="hospital"](around:{radius},{lat},{lon});
      node["office"](around:{radius},{lat},{lon});
    );
    out count;
    """

    comp_result = api.query(comp_query)
    poi_result  = api.query(poi_query)

    comp_count = len(comp_result.nodes)
    poi_count  = len(poi_result.nodes)

    return {"competition_count": comp_count, "poi_raw_count": poi_count}


def normalize_poi(poi_raw: int, city_tier: int) -> float:
    """Normalize POI count to 0-1 score based on city tier context."""
    max_pois = {1: 40, 2: 25, 3: 15, 4: 8}
    return round(min(poi_raw / max_pois.get(city_tier, 20), 1.0), 3)


def score_footfall(competition: int, poi_raw: int, city_tier: int) -> float:
    """
    Estimate footfall score from competition density and POI density.
    Moderate competition + high POIs = good footfall.
    """
    tier_base = {1: 0.70, 2: 0.52, 3: 0.34, 4: 0.20}[city_tier]
    poi_bonus = min(poi_raw / 30.0, 0.25)
    comp_bonus = min(competition / 15.0, 0.10) if competition < 15 else -0.05
    return round(min(1.0, tier_base + poi_bonus + comp_bonus), 3)


def estimate_population_density(city_tier: int, competition: int) -> float:
    """Estimate relative population density from tier + competition signal."""
    tier_base = {1: 0.82, 2: 0.60, 3: 0.38, 4: 0.22}[city_tier]
    comp_signal = min(competition / 15.0, 0.10)
    noise = np.random.normal(0, 0.03)
    return round(np.clip(tier_base + comp_signal + noise, 0.10, 1.0), 3)


# ─────────────────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────────────────
rows = []
print("\nTenzorX Geo Pre-Computation")
print(f"Querying {len(LOCATIONS)} locations (radius={RADIUS_M}m)...")
print("-" * 55)

for lat, lon, city, state, city_tier in LOCATIONS:
    print(f"  [{city}] ({lat}, {lon})... ", end="", flush=True)
    try:
        osm = overpass_query(lat, lon)
        competition = osm["competition_count"]
        poi_raw     = osm["poi_raw_count"]
    except Exception as e:
        print(f"⚠️  Overpass failed ({e}), using tier defaults.")
        tier_defaults = {1: (10, 20), 2: (6, 12), 3: (3, 6), 4: (2, 4)}
        competition, poi_raw = tier_defaults.get(city_tier, (5, 10))

    poi_score    = normalize_poi(poi_raw, city_tier)
    footfall     = score_footfall(competition, poi_raw, city_tier)
    pop_density  = estimate_population_density(city_tier, competition)

    row = {
        "lat_rounded"       : round(lat, 2),
        "lon_rounded"       : round(lon, 2),
        "city"              : city,
        "state"             : state,
        "city_tier"         : city_tier,
        "population_density": pop_density,
        "footfall_score"    : footfall,
        "competition_count" : competition,
        "poi_score"         : poi_score,
    }
    rows.append(row)
    print(f"✅  competition={competition}, poi_score={poi_score:.2f}")
    time.sleep(1.5)  # Be nice to Overpass API

# ─────────────────────────────────────────────────────────────────────────────
# Save CSV
# ─────────────────────────────────────────────────────────────────────────────
out_df = pd.DataFrame(rows)
output_path = "geo_lookup.csv"
out_df.to_csv(output_path, index=False)

print(f"\n✅  Saved {len(out_df)} rows → {output_path}")
print(f"   Copy to: code/backend/data/geo_lookup.csv")
print(out_df[["city", "city_tier", "competition_count", "footfall_score", "poi_score"]].to_string(index=False))
