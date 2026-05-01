"""
TenzorX Vision Engine
Extracts structured financial proxy features from kirana store images
using Gemini 1.5 Flash with strict JSON schema enforcement.
"""

import os
import json
import base64
from pathlib import Path
import google.generativeai as genai

# ─────────────────────────────────────────────────────────────────────────────
# MASTER VISION PROMPT — Schema Enforced, Zero-Shot, Expert Role
# ─────────────────────────────────────────────────────────────────────────────
VISION_PROMPT = """
You are a senior financial analyst specializing in kirana (Indian grocery) store
credit underwriting for Non-Banking Financial Companies (NBFCs).

Your task: Analyze the provided store image(s) and extract structured financial
proxy features. These features will be used to estimate the store's daily cash flow
for a micro-lending decision.

Analyze all images carefully, considering:
- Store interior (shelves, inventory density)
- Counter area (product mix, branding, POS setup)
- Store exterior (size, signage, street activity)

Return ONLY a valid JSON object with EXACTLY these fields — no other text:

{
  "shelf_density_index": <float 0.0-1.0, proportion of visible shelf space occupied>,
  "sku_diversity_score": <float 0.0-1.0, breadth of product categories visible>,
  "inventory_value_estimate": <"low" | "medium" | "high">,
  "refill_signal": <"recent_demand" | "overstocked" | "normal">,
  "store_size": <"small" | "medium" | "large">,
  "cleanliness_score": <float 0.0-1.0, overall tidiness and organization>,
  "fmcg_presence": <float 0.0-1.0, proportion of FMCG branded goods>,
  "premium_products": <float 0.0-1.0, proportion of high-margin or premium items>,
  "perishables_presence": <true | false, whether fresh or perishable goods are visible>,
  "estimated_daily_customers": <"very_low" | "low" | "medium" | "high" | "very_high">,
  "visibility_concerns": <list of strings from: ["low_light", "partial_view", "blurry", "staging_suspected", "single_angle_only"]>,
  "analysis_confidence": <float 0.0-1.0, your confidence given image quality and coverage>
}

Scoring guidance:
- shelf_density_index: 0.9+ = fully packed, 0.5 = half full, 0.2 = sparse
- sku_diversity: 0.9 = staples+FMCG+dairy+snacks+beverages+household, 0.3 = only a few categories
- refill_signal: "recent_demand" if shelves show empty spots/gaps mid-shelf; "overstocked" if every shelf is perfectly full (inspection-day stocking); "normal" otherwise
- Be conservative. Reduce analysis_confidence if you see only 1 image, poor lighting, or partial views.

Return ONLY the JSON. No markdown, no explanation, no code fences.
""".strip()


def _encode_image(path: str) -> tuple:
    """Read an image file and return (base64_string, mime_type)."""
    ext = Path(path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime_type = mime_map.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8"), mime_type


def _parse_gemini_response(text: str) -> dict:
    """Robustly parse JSON from Gemini response, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()
    return json.loads(text)


def extract_vision_features(image_paths: list, api_key: str) -> dict:
    """
    Extract financial proxy features from kirana store images (file paths).

    Args:
        image_paths: List of paths to store images
        api_key: Google Gemini API key

    Returns:
        dict with structured feature extraction
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    content = []
    for path in image_paths:
        img_b64, mime_type = _encode_image(path)
        content.append({
            "inline_data": {"mime_type": mime_type, "data": img_b64}
        })
    content.append({"text": VISION_PROMPT})

    response = model.generate_content(content)
    return _parse_gemini_response(response.text)


def extract_vision_features_bytes(image_bytes_list: list, api_key: str) -> dict:
    """
    Extract features from image bytes (Flask file uploads).

    Args:
        image_bytes_list: List of (bytes, mime_type) tuples
        api_key: Google Gemini API key

    Returns:
        dict with structured feature extraction
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    content = []
    for img_bytes, mime_type in image_bytes_list:
        # Normalize mime type
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "inline_data": {"mime_type": mime_type, "data": img_b64}
        })
    content.append({"text": VISION_PROMPT})

    response = model.generate_content(content)
    return _parse_gemini_response(response.text)
