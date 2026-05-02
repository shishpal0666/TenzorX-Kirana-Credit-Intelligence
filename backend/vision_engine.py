"""
TenzorX Vision Engine
Extracts structured financial proxy features from kirana store images
using Gemini 1.5 Flash REST API with strict JSON schema enforcement.

Uses direct HTTP requests instead of google-generativeai SDK
to avoid heavy dependency chain on Python 3.14.
"""

import json
import base64
import time
from pathlib import Path
import requests

# ─────────────────────────────────────────────────────────────────────────────
# Gemini REST API endpoint
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

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


def _call_gemini_api(content_parts: list, api_key: str) -> str:
    """
    Call Gemini REST API directly with content parts.
    Returns the text response from Gemini.
    """
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": content_parts}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        }
    }

    url = f"{GEMINI_API_URL}?key={api_key}"

    # Retry with exponential backoff for rate limits (429)
    max_retries = 3
    backoff_schedule = [5, 15, 30]  # seconds — free tier needs longer waits
    for attempt in range(max_retries + 1):
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code == 429 and attempt < max_retries:
            wait = backoff_schedule[attempt]
            print(f"[Vision] Rate limited (429). Waiting {wait}s before retry... ({attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue
        response.raise_for_status()
        break

    result = response.json()

    # Extract text from Gemini response
    candidates = result.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini returned no candidates: {result}")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError(f"Gemini returned no content parts: {result}")

    return parts[0].get("text", "")


def extract_vision_features(image_paths: list, api_key: str) -> dict:
    """
    Extract financial proxy features from kirana store images (file paths).

    Args:
        image_paths: List of paths to store images
        api_key: Google Gemini API key

    Returns:
        dict with structured feature extraction
    """
    content = []
    for path in image_paths:
        img_b64, mime_type = _encode_image(path)
        content.append({
            "inline_data": {"mime_type": mime_type, "data": img_b64}
        })
    content.append({"text": VISION_PROMPT})

    text = _call_gemini_api(content, api_key)
    return _parse_gemini_response(text)


def extract_vision_features_bytes(image_bytes_list: list, api_key: str) -> dict:
    """
    Extract features from image bytes (Flask file uploads).
    Automatically limits payload size to avoid Gemini rate limits.

    Args:
        image_bytes_list: List of (bytes, mime_type) tuples
        api_key: Google Gemini API key

    Returns:
        dict with structured feature extraction
    """
    MAX_IMAGE_SIZE = 800_000  # 800KB per image max
    MAX_IMAGES = 3            # Send at most 3 images to Gemini

    # Sort by size (smallest first) and take at most MAX_IMAGES
    sized = [(img_bytes, mime_type, len(img_bytes)) for img_bytes, mime_type in image_bytes_list]
    sized.sort(key=lambda x: x[2])
    selected = sized[:MAX_IMAGES]

    content = []
    total_bytes = 0
    for img_bytes, mime_type, size in selected:
        # Skip images that are too large
        if size > MAX_IMAGE_SIZE:
            print(f"[Vision] Skipping {size // 1024}KB image (max {MAX_IMAGE_SIZE // 1024}KB)")
            continue
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "inline_data": {"mime_type": mime_type, "data": img_b64}
        })
        total_bytes += size

    if not content:
        # All images were too large — send just the smallest one anyway
        img_bytes, mime_type, size = sized[0]
        if mime_type == "image/jpg":
            mime_type = "image/jpeg"
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        content.append({
            "inline_data": {"mime_type": mime_type, "data": img_b64}
        })
        total_bytes = size
        print(f"[Vision] All images over limit. Sending smallest ({size // 1024}KB)")

    print(f"[Vision] Sending {len(content)} image(s), total ~{total_bytes // 1024}KB")
    content.append({"text": VISION_PROMPT})

    text = _call_gemini_api(content, api_key)
    return _parse_gemini_response(text)

