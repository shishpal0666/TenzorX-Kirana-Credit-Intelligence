"""
TenzorX Demo Response Library
Pre-crafted, realistic demo responses for DEMO_MODE=true
These are served instantly without any API calls — essential for live pitch.
"""

import random

# ─────────────────────────────────────────────────────────────────────────────
# Pre-crafted demo scenarios
# ─────────────────────────────────────────────────────────────────────────────
_DEMO_SCENARIOS = [
    {
        # Scenario A: Healthy Mumbai store — approvable
        "daily_sales_range": [6200, 9400],
        "daily_sales_median": 7800,
        "monthly_revenue_range": [161200, 244400],
        "monthly_revenue_median": 202800,
        "monthly_income_range": [22568, 39104],
        "confidence_score": 0.74,
        "recommendation": "needs_verification",
        "risk_flags": ["inventory_footfall_mismatch"],
        "fraud_risk_level": "medium",
        "location": {
            "city": "Mumbai",
            "state": "Maharashtra",
            "city_tier": 1,
            "population_density": 0.92,
            "footfall_score": 0.85,
            "competition_count": 12,
            "poi_score": 0.88,
            "geo_match_quality": "exact",
        },
        "vision_summary": {
            "shelf_density_index": 0.78,
            "sku_diversity_score": 0.65,
            "store_size": "medium",
            "refill_signal": "recent_demand",
        },
        "model_version": "xgb_quantile_nsso_v1",
    },
    {
        # Scenario B: Thriving Pune store — strong approve
        "daily_sales_range": [8500, 15200],
        "daily_sales_median": 11800,
        "monthly_revenue_range": [221000, 395200],
        "monthly_revenue_median": 306800,
        "monthly_income_range": [30940, 63232],
        "confidence_score": 0.82,
        "recommendation": "approve_with_standard_terms",
        "risk_flags": [],
        "fraud_risk_level": "low",
        "location": {
            "city": "Pune",
            "state": "Maharashtra",
            "city_tier": 1,
            "population_density": 0.80,
            "footfall_score": 0.75,
            "competition_count": 8,
            "poi_score": 0.78,
            "geo_match_quality": "exact",
        },
        "vision_summary": {
            "shelf_density_index": 0.87,
            "sku_diversity_score": 0.82,
            "store_size": "large",
            "refill_signal": "normal",
        },
        "model_version": "xgb_quantile_nsso_v1",
    },
    {
        # Scenario C: Suspicious store — reject
        "daily_sales_range": [3100, 5900],
        "daily_sales_median": 4200,
        "monthly_revenue_range": [80600, 153400],
        "monthly_revenue_median": 109200,
        "monthly_income_range": [9672, 24544],
        "confidence_score": 0.38,
        "recommendation": "reject_pending_review",
        "risk_flags": ["exif_staged_shoot", "image_inconsistency", "inventory_footfall_mismatch"],
        "fraud_risk_level": "high",
        "location": {
            "city": "Delhi",
            "state": "Delhi",
            "city_tier": 1,
            "population_density": 0.88,
            "footfall_score": 0.82,
            "competition_count": 14,
            "poi_score": 0.86,
            "geo_match_quality": "approximate",
        },
        "vision_summary": {
            "shelf_density_index": 0.95,
            "sku_diversity_score": 0.40,
            "store_size": "small",
            "refill_signal": "overstocked",
        },
        "model_version": "xgb_quantile_nsso_v1",
    },
]


def get_demo_response(scenario_index: int = None) -> dict:
    """
    Return a pre-crafted demo response.

    Args:
        scenario_index: 0, 1, or 2 for specific scenario. None = random.

    Returns:
        Complete underwriting response dict
    """
    if scenario_index is not None and 0 <= scenario_index < len(_DEMO_SCENARIOS):
        return _DEMO_SCENARIOS[scenario_index]
    return random.choice(_DEMO_SCENARIOS)
