"""
TenzorX Kirana Underwriting API
Main Flask server — single /api/underwrite endpoint orchestrates
all four engines: Vision → Geo → Fraud → Economic Fusion.
"""

import os
import json
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ─── Environment Flags ────────────────────────────────────────────────────────
DEMO_MODE       = os.getenv("DEMO_MODE", "true").lower() == "true"
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
USE_CLIP        = os.getenv("USE_CLIP", "false").lower() == "true"

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _normalize_mime(filename: str) -> str:
    ext = filename.rsplit(".", 1)[1].lower()
    return "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    """Quick health check — use this to verify backend is running."""
    return jsonify({
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "clip_enabled": USE_CLIP,
        "gemini_key_set": bool(GEMINI_API_KEY),
        "version": "1.0.0",
    })


# ─── Main Underwriting Endpoint ───────────────────────────────────────────────
@app.route("/api/underwrite", methods=["POST"])
def underwrite():
    """
    POST /api/underwrite
    Form data:
      - images: 1-5 image files (jpg/png/webp)
      - lat: float (GPS latitude)
      - lon: float (GPS longitude)
      - shop_size: "small"|"medium"|"large" (optional override)
      - rent: monthly rent in ₹ (optional context)
      - years_operation: years in business (optional context)
      - scenario: 0|1|2 (demo mode only — pick specific scenario)

    Returns:
      JSON with cash flow ranges, confidence, risk flags, recommendation
    """

    # ── DEMO MODE: Return pre-crafted response instantly ──────────────────────
    if DEMO_MODE:
        from demo_responses import get_demo_response
        scenario = request.form.get("scenario")
        idx = int(scenario) if scenario and scenario.isdigit() else None
        response = get_demo_response(idx).copy()  # copy to avoid mutating original
        response["demo_mode"] = True
        return jsonify(response)

    # ── LIVE MODE ─────────────────────────────────────────────────────────────
    try:
        if not GEMINI_API_KEY:
            return jsonify({"error": "GEMINI_API_KEY not set in .env"}), 500

        # 1. Parse form inputs
        lat = float(request.form.get("lat", 19.07))
        lon = float(request.form.get("lon", 72.87))
        shop_size_override = request.form.get("shop_size")
        rent = request.form.get("rent")
        years_operation = request.form.get("years_operation")

        # 2. Read uploaded images
        uploaded_files = request.files.getlist("images")
        if not uploaded_files:
            return jsonify({"error": "Upload at least 1 image of the store."}), 400

        image_data = []  # list of (bytes, mime_type)
        for f in uploaded_files:
            if f and _allowed_file(f.filename):
                img_bytes = f.read()
                mime_type = _normalize_mime(f.filename)
                image_data.append((img_bytes, mime_type))

        if not image_data:
            return jsonify({"error": "No valid images found. Use jpg/png/webp."}), 400

        # 3. Engine 1 — Vision Extraction
        print(f"[API] Running Vision Engine on {len(image_data)} image(s)...")
        from vision_engine import extract_vision_features_bytes
        vision = extract_vision_features_bytes(image_data, GEMINI_API_KEY)

        # Apply user override for store size
        if shop_size_override:
            vision["store_size"] = shop_size_override

        # 4. Engine 2 — Geo Features
        print(f"[API] Looking up geo features for ({lat}, {lon})...")
        from geo_engine import get_geo_features
        geo = get_geo_features(lat, lon)

        # 5. Engine 3 — Fraud Detection
        print("[API] Running fraud checks...")
        from fraud_engine import run_fraud_checks
        image_bytes_only = [b for b, _ in image_data]
        fraud = run_fraud_checks(image_bytes_only, vision, geo, use_clip=USE_CLIP)

        # 6. Engine 4 — Economic Fusion
        print("[API] Running economic fusion model...")
        from fusion_engine import predict_cash_flow
        optional_context = {
            "rent": float(rent) if rent else None,
            "years_operation": int(years_operation) if years_operation else None,
        }
        prediction = predict_cash_flow(vision, geo, fraud["risk_flags"], optional_context)

        # 7. Build final response
        response = {
            **prediction,
            "risk_flags": fraud["risk_flags"],
            "fraud_risk_level": fraud["fraud_risk_level"],
            "location": geo,
            "vision_summary": {
                "shelf_density_index": vision.get("shelf_density_index"),
                "sku_diversity_score": vision.get("sku_diversity_score"),
                "store_size": vision.get("store_size"),
                "refill_signal": vision.get("refill_signal"),
                "analysis_confidence": vision.get("analysis_confidence"),
            },
            "demo_mode": False,
        }

        if rent or years_operation:
            response["user_context"] = {
                "monthly_rent": float(rent) if rent else None,
                "years_operation": int(years_operation) if years_operation else None,
            }

        print("[API] ✅ Underwriting complete.")
        return jsonify(response)

    except FileNotFoundError as e:
        # Model files missing
        return jsonify({
            "error": str(e),
            "fix": "Run training/train_model.py on Colab and place .pkl files in backend/models/"
        }), 503

    except json.JSONDecodeError as e:
        return jsonify({
            "error": f"Vision engine returned invalid JSON: {str(e)}",
            "fix": "Check your GEMINI_API_KEY and retry."
        }), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print("=" * 60)
    print("  TenzorX Kirana Underwriting API")
    print("=" * 60)
    print(f"  Mode      : {'🎭 DEMO (pre-crafted responses)' if DEMO_MODE else '🧠 LIVE (real AI pipeline)'}")
    print(f"  Gemini Key: {'✅ Set' if GEMINI_API_KEY else '❌ MISSING — set in .env'}")
    print(f"  CLIP      : {'✅ Enabled' if USE_CLIP else '⚪ Disabled'}")
    print(f"  Port      : {port}")
    print(f"  Health    : http://localhost:{port}/api/health")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
