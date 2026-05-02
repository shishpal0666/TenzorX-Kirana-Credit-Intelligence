"""
TenzorX Fraud Defense Engine
Four-layer fraud detection:
  1. Image Coverage Check — flag limited view coverage (<3 images)
  2. EXIF Timestamp Clustering — all images within 45s = staged shoot
  3. CLIP Embedding Consistency — (requires torch, skipped when USE_CLIP=false)
  4. Cross-Signal Logic Gates — economic inconsistency detection

Uses only pure Python + exifread — no numpy/PIL/torch required.
"""

import io

# ─────────────────────────────────────────────────────────────────────────────
# Check 1: EXIF Timestamp Clustering
# ─────────────────────────────────────────────────────────────────────────────
def check_exif_timestamps(image_bytes_list: list) -> dict:
    """
    Check EXIF DateTimeOriginal across images.
    If all images taken within 45 seconds → flag staged shoot.
    """
    import exifread
    from datetime import datetime

    timestamps = []
    for img_bytes in image_bytes_list:
        try:
            tags = exifread.process_file(
                io.BytesIO(img_bytes),
                stop_tag="EXIF DateTimeOriginal",
                details=False
            )
            if "EXIF DateTimeOriginal" in tags:
                dt_str = str(tags["EXIF DateTimeOriginal"])
                dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                timestamps.append(dt)
        except Exception:
            pass

    if len(timestamps) < 2:
        return {
            "staged_shoot": False,
            "time_span_seconds": None,
            "timestamps_found": len(timestamps),
            "flags": []
        }

    time_span = (max(timestamps) - min(timestamps)).total_seconds()
    flags = ["exif_staged_shoot"] if time_span < 45 else []

    return {
        "staged_shoot": time_span < 45,
        "time_span_seconds": round(time_span, 1),
        "timestamps_found": len(timestamps),
        "flags": flags
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check 2: Cross-Signal Logic Gates
# ─────────────────────────────────────────────────────────────────────────────
def check_cross_signals(vision_features: dict, geo_features: dict) -> dict:
    """
    Detect economic inconsistencies between vision and geo signals.
    Pure Python — no numpy needed.
    """
    flags = []

    sdi = vision_features.get("shelf_density_index", 0.5)
    footfall = geo_features.get("footfall_score", 0.5)
    competition = geo_features.get("competition_count", 5)
    refill = vision_features.get("refill_signal", "normal")
    cleanliness = vision_features.get("cleanliness_score", 0.5)
    visibility = vision_features.get("visibility_concerns", [])
    fmcg = vision_features.get("fmcg_presence", 0.5)
    city_tier = geo_features.get("city_tier", 2)

    # Gate 1: High inventory in very low-footfall area
    if sdi > 0.88 and footfall < 0.30:
        flags.append("inventory_footfall_mismatch")

    # Gate 2: Overstocked in near-zero competition zone
    if refill == "overstocked" and competition <= 2:
        flags.append("overstock_anomaly")

    # Gate 3: Staging suspected — perfect store with visibility concerns
    if cleanliness > 0.92 and "staging_suspected" in visibility:
        flags.append("staging_suspected")

    # Gate 4: Premium FMCG heavy mix in Tier 3/4 city
    if fmcg > 0.80 and city_tier >= 3:
        flags.append("product_mix_city_mismatch")

    return {"flags": flags}


# ─────────────────────────────────────────────────────────────────────────────
# Master Fraud Runner
# ─────────────────────────────────────────────────────────────────────────────
def run_fraud_checks(
    image_bytes_list: list,
    vision_features: dict,
    geo_features: dict,
    use_clip: bool = False
) -> dict:
    """
    Run all fraud detection layers and return consolidated risk flags.

    Args:
        image_bytes_list: Raw image bytes (no mime type needed here)
        vision_features: Output from vision_engine
        geo_features: Output from geo_engine
        use_clip: Enable CLIP consistency check (requires torch — disabled by default)

    Returns:
        dict with risk_flags, fraud_risk_level, and per-check details
    """
    all_flags = []
    details = {}

    # Layer 0: Image coverage check
    num_images = len(image_bytes_list)
    coverage_flags = []
    if num_images < 3:
        coverage_flags.append("limited_view_coverage")
    # Also check if vision engine flagged single_angle_only
    visibility = vision_features.get("visibility_concerns", [])
    if "single_angle_only" in visibility and "limited_view_coverage" not in coverage_flags:
        coverage_flags.append("limited_view_coverage")
    all_flags.extend(coverage_flags)
    details["coverage_check"] = {
        "images_provided": num_images,
        "sufficient_coverage": num_images >= 3,
        "flags": coverage_flags
    }

    # Layer 1: EXIF timestamp clustering
    exif_result = check_exif_timestamps(image_bytes_list)
    all_flags.extend(exif_result["flags"])
    details["exif_check"] = exif_result

    # Layer 2: CLIP consistency (skipped — requires torch/transformers)
    if use_clip and len(image_bytes_list) >= 2:
        # CLIP requires torch + transformers + PIL — not available on Python 3.14
        # In production, this would use CLIP embeddings for cross-image verification
        details["clip_check"] = {
            "skipped": True,
            "reason": "CLIP requires torch — not available in current environment",
            "flags": []
        }
    else:
        details["clip_check"] = {"skipped": True, "reason": "USE_CLIP=false"}

    # Layer 3: Cross-signal logic gates
    cross_result = check_cross_signals(vision_features, geo_features)
    all_flags.extend(cross_result["flags"])
    details["cross_signal_check"] = cross_result

    # Deduplicate (preserves order)
    seen = set()
    unique_flags = []
    for f in all_flags:
        if f not in seen:
            seen.add(f)
            unique_flags.append(f)
    all_flags = unique_flags

    # Risk level
    if len(all_flags) >= 3:
        risk_level = "high"
    elif len(all_flags) >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_flags": all_flags,
        "fraud_risk_level": risk_level,
        "details": details
    }
