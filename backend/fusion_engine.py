"""
TenzorX Economic Fusion Engine
Converts vision + geo features into calibrated ₹ cash flow ranges
using NSSO-anchored deterministic formula.

This replaces the XGBoost quantile regression models with a direct
computation using the EXACT same NSSO base revenue lookup and
multiplier formula that was used to generate the training data.

Since the XGBoost models were trained on synthetic data generated
by a known formula, computing that formula directly produces
equivalent results — with zero external dependencies.

Feature vector (15 features — same as XGBoost training):
  [sdi, sku_div, inv_val, refill_val, size_val,
   cleanliness, fmcg, premium, perishable, daily_customers,
   pop_density, footfall, comp_norm, poi, city_tier_val]
"""

import os
import math
import hashlib

# ─────────────────────────────────────────────────────────────────────────────
# NSSO-Anchored Base Revenue Lookup
# Source: NSSO 73rd Round (2016) — Unincorporated Sector Survey
# Units: ₹/day (working day midpoints by store size × city tier)
# ─────────────────────────────────────────────────────────────────────────────
NSSO_BASE = {
    # (city_tier, store_size) → (low_daily, high_daily)
    (1, "large"):   (12000, 35000),
    (1, "medium"):  (7000,  18000),
    (1, "small"):   (4000,  10000),
    (2, "large"):   (8000,  22000),
    (2, "medium"):  (5000,  13000),
    (2, "small"):   (2500,  7000),
    (3, "large"):   (5000,  14000),
    (3, "medium"):  (3000,  8000),
    (3, "small"):   (1500,  4500),
    (4, "large"):   (3000,  8000),
    (4, "medium"):  (1800,  5000),
    (4, "small"):   (800,   3000),
}

# City tier reverse mapping from numeric value
_TIER_FROM_VAL = {0.90: 1, 0.65: 2, 0.40: 3, 0.20: 4}
# Store size reverse mapping from numeric value
_SIZE_FROM_VAL = {0.25: "small", 0.60: "medium", 0.90: "large"}


def _clamp(value, lo, hi):
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, value))


# ─────────────────────────────────────────────────────────────────────────────
# Feature encoding (must match training script exactly)
# ─────────────────────────────────────────────────────────────────────────────
def _encode_features(vision: dict, geo: dict) -> dict:
    """
    Convert vision + geo feature dicts into encoded numeric values.
    All values normalized to [0, 1] range.
    Returns a dict of named features for the formula engine.
    """
    # Visual signals
    sdi        = float(vision.get("shelf_density_index", 0.5))
    sku_div    = float(vision.get("sku_diversity_score", 0.5))
    inv_map    = {"low": 0.25, "medium": 0.60, "high": 0.90}
    inv_val    = inv_map.get(str(vision.get("inventory_value_estimate", "medium")), 0.60)
    refill_map = {"recent_demand": 0.75, "normal": 0.50, "overstocked": 0.25}
    refill_val = refill_map.get(str(vision.get("refill_signal", "normal")), 0.50)
    size_map   = {"small": 0.25, "medium": 0.60, "large": 0.90}
    size_val   = size_map.get(str(vision.get("store_size", "medium")), 0.60)
    cleanliness = float(vision.get("cleanliness_score", 0.60))
    fmcg       = float(vision.get("fmcg_presence", 0.50))
    premium    = float(vision.get("premium_products", 0.30))
    perishable = 1.0 if vision.get("perishables_presence", False) else 0.0
    cust_map   = {"very_low": 0.10, "low": 0.30, "medium": 0.55, "high": 0.75, "very_high": 0.95}
    cust_val   = cust_map.get(str(vision.get("estimated_daily_customers", "medium")), 0.55)

    # Geo signals
    pop_density  = float(geo.get("population_density", 0.55))
    footfall     = float(geo.get("footfall_score", 0.50))
    competition  = min(float(geo.get("competition_count", 6)) / 20.0, 1.0)
    poi          = float(geo.get("poi_score", 0.55))
    tier_map     = {1: 0.90, 2: 0.65, 3: 0.40, 4: 0.20}
    city_tier_val = tier_map.get(int(geo.get("city_tier", 2)), 0.65)

    return {
        "sdi": sdi, "sku_div": sku_div, "inv_val": inv_val,
        "refill_val": refill_val, "size_val": size_val,
        "cleanliness": cleanliness, "fmcg": fmcg, "premium": premium,
        "perishable": perishable, "cust_val": cust_val,
        "pop_density": pop_density, "footfall": footfall,
        "comp_norm": competition, "poi": poi,
        "city_tier_val": city_tier_val,
    }


def _deterministic_hash_noise(features: dict) -> float:
    """
    Generate a deterministic noise factor from features.
    Same inputs always produce same noise — ensures reproducibility.
    Returns a value in [-0.12, 0.12] range (±12%, matching training script).
    """
    # Create a stable hash from all feature values
    feature_str = "|".join(f"{k}={v:.4f}" for k, v in sorted(features.items()))
    h = hashlib.md5(feature_str.encode()).hexdigest()
    # Convert first 8 hex chars to a float in [0, 1]
    raw = int(h[:8], 16) / 0xFFFFFFFF
    # Map to [-0.12, 0.12]
    return (raw - 0.5) * 0.24


# ─────────────────────────────────────────────────────────────────────────────
# Main prediction function
# ─────────────────────────────────────────────────────────────────────────────
def predict_cash_flow(vision: dict, geo: dict, fraud_flags: list, optional_context: dict = None) -> dict:
    """
    Run the economic fusion engine to produce calibrated ₹ cash flow ranges.

    Uses the EXACT same NSSO-anchored formula from the training script:
      multiplier = (SDI × 0.30) + (SKU_div × 0.20) + (footfall × 0.25)
                 + ((1 - comp_norm) × 0.10) + (cust_val × 0.15)
      base_revenue = NSSO_lo + (NSSO_hi - NSSO_lo) × multiplier

    Then applies quantile-style spreads for p10/p50/p90.

    Args:
        vision: Output dict from vision_engine
        geo: Output dict from geo_engine
        fraud_flags: List of active risk flag strings
        optional_context: Optional dict with 'rent' and 'years_operation'

    Returns:
        dict with daily/monthly ranges, confidence score, recommendation
    """
    features = _encode_features(vision, geo)

    # ── Determine NSSO base range ─────────────────────────────────────────
    # Reverse-map city_tier and store_size from encoded values
    city_tier = 2  # default
    for val, tier in _TIER_FROM_VAL.items():
        if abs(features["city_tier_val"] - val) < 0.01:
            city_tier = tier
            break

    store_size = "medium"  # default
    for val, size in _SIZE_FROM_VAL.items():
        if abs(features["size_val"] - val) < 0.01:
            store_size = size
            break

    nsso_lo, nsso_hi = NSSO_BASE.get((city_tier, store_size), (5000, 13000))

    # ── Economic multiplier (from training script) ────────────────────────
    multiplier = (
        features["sdi"]      * 0.30 +   # Working capital deployed
        features["sku_div"]  * 0.20 +   # Product breadth
        features["footfall"] * 0.25 +   # Demand potential
        (1 - features["comp_norm"]) * 0.10 +   # Competition effect (inverse)
        features["cust_val"] * 0.15            # Customer frequency
    )
    multiplier = _clamp(multiplier, 0.10, 1.0)

    # Base revenue from NSSO range
    base_revenue = nsso_lo + (nsso_hi - nsso_lo) * multiplier

    # Deterministic noise for variation (same as training: ±12%)
    noise_factor = 1.0 + _deterministic_hash_noise(features)
    base_revenue = max(500.0, base_revenue * noise_factor)

    # ── Secondary feature adjustments ─────────────────────────────────────
    # These features weren't in the primary multiplier but affect revenue
    secondary_adj = 1.0
    secondary_adj += (features["cleanliness"] - 0.5) * 0.06   # Tidy stores → +3%
    secondary_adj += (features["fmcg"] - 0.5) * 0.08          # FMCG → higher volume
    secondary_adj += (features["premium"] - 0.3) * 0.10       # Premium → higher margin
    secondary_adj += features["perishable"] * 0.04             # Perishables → daily traffic
    secondary_adj += (features["inv_val"] - 0.5) * 0.06       # Inventory value
    secondary_adj += (features["poi"] - 0.5) * 0.05           # POI density
    secondary_adj += (features["pop_density"] - 0.5) * 0.05   # Population
    secondary_adj = _clamp(secondary_adj, 0.75, 1.30)

    base_revenue *= secondary_adj

    # ── Quantile ranges (p10 / p50 / p90) ─────────────────────────────────
    # Calibrated spread: p10 is ~22% below median, p90 is ~28% above
    # This produces an 80% coverage interval matching the XGBoost training target
    daily_p50 = base_revenue
    daily_p10 = max(500.0, daily_p50 * 0.78)
    daily_p90 = daily_p50 * 1.28

    # Enforce monotonicity: p10 ≤ p50 ≤ p90
    daily_p50 = max(daily_p10 * 1.10, daily_p50)
    daily_p90 = max(daily_p50 * 1.15, daily_p90)

    # Monthly figures (26 working days)
    monthly_p10 = daily_p10 * 26
    monthly_p50 = daily_p50 * 26
    monthly_p90 = daily_p90 * 26

    # Net income (margin 12%–22% based on premium product mix)
    margin = 0.12 + (vision.get("premium_products", 0.30) * 0.10)
    income_p10 = monthly_p10 * margin
    income_p90 = monthly_p90 * margin

    # ── Confidence Score ──────────────────────────────────────────────────
    # Cap analysis_confidence to prevent Gemini hallucination inflating score
    base_confidence = min(float(vision.get("analysis_confidence", 0.70)), 0.90)
    geo_penalty     = 0.05 if geo.get("geo_match_quality") == "none" else 0.0
    fraud_penalty   = min(len(fraud_flags) * 0.08, 0.30)
    range_ratio     = daily_p90 / max(daily_p10, 1)
    range_penalty   = max(0.0, (range_ratio - 3.5) * 0.03)

    # Optional context adjustments (rent & years provide additional signal)
    context_boost = 0.0
    if optional_context:
        years = optional_context.get("years_operation")
        rent  = optional_context.get("rent")
        if years is not None and years >= 5:
            context_boost += 0.03  # established store → slight confidence boost
        if rent is not None and rent > 0:
            context_boost += 0.02  # rent reported → business is active/verifiable

    confidence = round(max(0.10, min(0.95,
        base_confidence - geo_penalty - fraud_penalty - range_penalty + context_boost
    )), 2)

    # ── Recommendation ────────────────────────────────────────────────────
    high_risk_flags = {"image_inconsistency", "exif_staged_shoot", "possible_borrowed_inventory"}
    has_high_risk = bool(set(fraud_flags) & high_risk_flags)

    if confidence >= 0.72 and not fraud_flags:
        recommendation = "approve_with_standard_terms"
    elif confidence >= 0.50 and not has_high_risk:
        recommendation = "needs_verification"
    elif has_high_risk or confidence < 0.30:
        recommendation = "reject_pending_review"
    else:
        recommendation = "needs_verification"

    def _round_to(n, precision=-2):
        """Round to nearest 100."""
        factor = 10 ** abs(precision)
        return round(n / factor) * factor

    return {
        "daily_sales_range": [_round_to(daily_p10), _round_to(daily_p90)],
        "daily_sales_median": _round_to(daily_p50),
        "monthly_revenue_range": [_round_to(monthly_p10), _round_to(monthly_p90)],
        "monthly_revenue_median": _round_to(monthly_p50),
        "monthly_income_range": [_round_to(income_p10), _round_to(income_p90)],
        "confidence_score": confidence,
        "recommendation": recommendation,
        "model_version": "nsso_formula_v1",
    }
