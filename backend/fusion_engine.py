"""
TenzorX Economic Fusion Engine
Loads pre-trained XGBoost Quantile Regression models (p10/p50/p90)
and converts vision + geo features into calibrated ₹ cash flow ranges.

Feature vector (15 features — must match training order):
  [sdi, sku_div, inv_val, refill_val, size_val,
   cleanliness, fmcg, premium, perishable, daily_customers,
   pop_density, footfall, comp_norm, poi, city_tier_val]
"""

import os
import pickle
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Model paths
# ─────────────────────────────────────────────────────────────────────────────
_MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
_MODEL_PATHS = {
    "p10": os.path.join(_MODEL_DIR, "xgb_p10.pkl"),
    "p50": os.path.join(_MODEL_DIR, "xgb_p50.pkl"),
    "p90": os.path.join(_MODEL_DIR, "xgb_p90.pkl"),
}

_models = {}


def _load_models():
    """Lazy-load all three quantile models once."""
    global _models
    if _models:
        return _models

    missing = [k for k, p in _MODEL_PATHS.items() if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(
            f"Missing model files: {missing}. "
            "Run training/train_model.py on Colab and place .pkl files in backend/models/"
        )

    for key, path in _MODEL_PATHS.items():
        with open(path, "rb") as f:
            _models[key] = pickle.load(f)
        print(f"[FusionEngine] Loaded {key} model.")

    return _models


# ─────────────────────────────────────────────────────────────────────────────
# Feature encoding (must match training script exactly)
# ─────────────────────────────────────────────────────────────────────────────
def _encode_features(vision: dict, geo: dict) -> np.ndarray:
    """
    Convert vision + geo feature dicts into a 15-element float numpy array.
    All values normalized to [0, 1] range.
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

    return np.array([
        sdi, sku_div, inv_val, refill_val, size_val,
        cleanliness, fmcg, premium, perishable, cust_val,
        pop_density, footfall, competition, poi, city_tier_val
    ], dtype=float).reshape(1, -1)


# ─────────────────────────────────────────────────────────────────────────────
# Main prediction function
# ─────────────────────────────────────────────────────────────────────────────
def predict_cash_flow(vision: dict, geo: dict, fraud_flags: list, optional_context: dict = None) -> dict:
    """
    Run the economic fusion engine to produce calibrated ₹ cash flow ranges.

    Args:
        vision: Output dict from vision_engine
        geo: Output dict from geo_engine
        fraud_flags: List of active risk flag strings
        optional_context: Optional dict with 'rent' and 'years_operation'

    Returns:
        dict with daily/monthly ranges, confidence score, recommendation
    """
    models = _load_models()
    X = _encode_features(vision, geo)

    raw_p10 = float(models["p10"].predict(X)[0])
    raw_p50 = float(models["p50"].predict(X)[0])
    raw_p90 = float(models["p90"].predict(X)[0])

    # Enforce monotonicity: p10 ≤ p50 ≤ p90
    daily_p10 = max(500.0, raw_p10)
    daily_p50 = max(daily_p10 * 1.10, raw_p50)
    daily_p90 = max(daily_p50 * 1.15, raw_p90)

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

    return {
        "daily_sales_range": [round(daily_p10, -2), round(daily_p90, -2)],
        "daily_sales_median": round(daily_p50, -2),
        "monthly_revenue_range": [round(monthly_p10, -2), round(monthly_p90, -2)],
        "monthly_revenue_median": round(monthly_p50, -2),
        "monthly_income_range": [round(income_p10, -2), round(income_p90, -2)],
        "confidence_score": confidence,
        "recommendation": recommendation,
        "model_version": "xgb_quantile_nsso_v1",
    }
