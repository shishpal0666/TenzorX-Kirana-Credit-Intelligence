# TenzorX — Kirana Credit Intelligence

> **Problem Statement 4C** · TenzorX 2026 National AI Hackathon · Partner: Poonawalla Fincorp

**Remote cash flow underwriting for kirana stores using Vision & Geo Intelligence — no bank statements, no surveys.**

🌐 **Live Demo:** [https://tenzorx-dashboard.vercel.app/](https://tenzorx-dashboard.vercel.app/)

---

## What It Does

TenzorX estimates a kirana store's daily cash flow using **only 3–5 store images and GPS coordinates**. It produces **₹ ranges with uncertainty**, confidence scores, fraud risk flags, and a lending recommendation — all in under 8 seconds.

### The Four Engines

| Engine | Technology | Function |
|---|---|---|
| 👁️ **Vision** | Gemini 2.5 Flash | Zero-shot extraction of shelf density, SKU diversity, refill signals |
| 🗺️ **Geo-Spatial** | OpenStreetMap CSV | Footfall proxy, competition density, city-tier classification |
| 🛡️ **Fraud Defense** | EXIF + Logic Gates | Multi-layer fraud detection: coverage check, timestamps, cross-signals |
| 📊 **Economic Fusion** | Deterministic Formula Engine | NSSO-calibrated ₹ daily revenue ranges (p10/p50/p90) |

---

## Project Structure

```
TenzorX/
├── README.md
├── .gitignore
├── backend/                    ← Flask ML API (Python)
│   ├── app.py                 ← Main server (/api/underwrite)
│   ├── vision_engine.py       ← Gemini 2.5 Flash zero-shot extraction
│   ├── geo_engine.py          ← Pre-computed CSV geo lookup (stdlib)
│   ├── fraud_engine.py        ← EXIF + cross-signal checks
│   ├── fusion_engine.py       ← NSSO formula engine (p10/p50/p90)
│   ├── demo_responses.py      ← Pre-crafted DEMO_MODE responses
│   ├── requirements.txt       ← Pure-Python dependencies
│   ├── .env.example
│   └── data/
│       └── geo_lookup.csv     ← 20+ Indian cities pre-computed
├── training/
│   ├── train_model.py         ← Legacy XGBoost training (reference)
│   └── precompute_geo.py      ← Overpass API → geo_lookup.csv
├── frontend/                   ← Next.js React dashboard
│   ├── package.json
│   ├── .env.example           ← Backend URL config
│   ├── next.config.mjs
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.js
│   │   ├── page.js            ← Main underwriter dashboard
│   │   └── globals.css
│   └── components/
│       ├── UploadZone.js      ← Drag & drop image uploader
│       ├── OutputCard.js      ← Animated result display
│       ├── RiskBadge.js       ← Colored risk flag pills
│       └── ConfidenceGauge.js ← Animated radial gauge
├── presentation/
│   └── presentation.html      ← 8-slide pitch deck (self-contained)
└── docs/
    ├── Kirana_Underwriting_Detailed_Report.pdf
    ├── TenzorX_Hackathon_Report_md.md
    └── TenzorX_Presentation.md
```

---

## Prerequisites

- **Python 3.10+** — [python.org](https://python.org)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **Git**

---

## Quick Start

### 1. Get Your Gemini API Key (Free)

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Click **"Create API Key"**
3. Copy the key (starts with `AIza...`)

### 2. Set Up the Backend

```bash
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Copy the environment template
cp .env.example .env    # (Linux/Mac)
copy .env.example .env  # (Windows)
```

Edit `.env` and set your Gemini API key:

```env
GEMINI_API_KEY=AIzaSy...your_key_here
DEMO_MODE=true
USE_CLIP=false
PORT=5000
```

### 3. Test in Demo Mode

```bash
# Still in backend/
python app.py
```

You should see:
```
  TenzorX Kirana Underwriting API
  Mode      : 🎭 DEMO (pre-crafted responses)
  Gemini Key: ✅ Set
  Port      : 5000
```

Verify: open `http://localhost:5000/api/health` → `{ "status": "ok" }`

### 4. Switch to Live Mode

```env
# In backend/.env
DEMO_MODE=false
```

Restart the backend: `python app.py`

### 6. Set Up the Frontend

```bash
cd frontend

# Copy environment template
cp .env.example .env.local    # (Linux/Mac)
copy .env.example .env.local  # (Windows)

npm install
npm run dev
```

Open **http://localhost:3000** 🎉

---

## Usage

1. Go to `http://localhost:3000`
2. Upload 1–5 kirana store images (interior, counter, exterior)
3. Enter GPS coordinates (default: Mumbai 19.0760, 72.8777)
4. Click **"Run Underwriting Analysis"**
5. View: daily sales range, confidence gauge, risk flags, recommendation

---

## Architecture

```
[Browser: localhost:3000]
        ↓ POST /api/underwrite (images + GPS)
[Flask: localhost:5000]
        ├── vision_engine.py   → Gemini 1.5 Flash API
        ├── geo_engine.py      → data/geo_lookup.csv (instant)
        ├── fraud_engine.py    → EXIF + CLIP + logic gates
        └── fusion_engine.py   → models/xgb_p10/p50/p90.pkl
        ↓ JSON response
[Browser: OutputCard with ₹ ranges, gauges, risk flags]
```

---

## API Reference

### `POST /api/underwrite`

| Field | Required | Type | Description |
|---|---|---|---|
| `images` | ✅ | File(s) | 1–5 store images (jpg/png/webp) |
| `lat` | ✅ | float | GPS latitude |
| `lon` | ✅ | float | GPS longitude |
| `shop_size` | ⬜ | string | `small` / `medium` / `large` (override) |
| `rent` | ⬜ | number | Monthly rent in ₹ |
| `years_operation` | ⬜ | number | Years in business |
| `scenario` | ⬜ | int | Demo mode only (0/1/2) |

> **Note:** `rent` and `years_operation` are used for **contextual enrichment** — they adjust the confidence score (established stores get +3%, verified rent +2%). Video input support is planned for v2 (frame sampling + motion analysis).

### Response

```json
{
  "daily_sales_range": [6200, 9400],
  "daily_sales_median": 7800,
  "monthly_revenue_range": [161200, 244400],
  "monthly_income_range": [22568, 39104],
  "confidence_score": 0.74,
  "recommendation": "needs_verification",
  "risk_flags": ["inventory_footfall_mismatch"],
  "fraud_risk_level": "medium",
  "location": { "city": "Mumbai", "city_tier": 1 },
  "vision_summary": { "shelf_density_index": 0.78 }
}
```

---

## Demo Mode (For Live Pitch)

Set `DEMO_MODE=true` in `.env` and restart. Returns pre-crafted JSON instantly — no API calls, no latency, no risk of failure.

| Scenario | City | Revenue | Confidence | Decision |
|---|---|---|---|---|
| 0 | Mumbai | ₹6,200–₹9,400/day | 74% | Verify |
| 1 | Pune | ₹8,500–₹15,200/day | 82% | Approve |
| 2 | Delhi | ₹3,100–₹5,900/day | 38% | Reject |

---

## Presentation

Open `presentation/presentation.html` in Chrome/Edge.

**Navigation:** `←` `→` arrow keys · `1`–`8` number keys · touch swipe · click nav dots

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `GEMINI_API_KEY not set` | Check `.env` file exists with your key |
| `FileNotFoundError: xgb_p10.pkl` | Train models or use `DEMO_MODE=true` |
| `CORS error` in browser | Backend must be running on port 5000 |
| Frontend blank page | Run `npm install` in `frontend/` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 · React 18 · Tailwind CSS |
| Backend API | Flask · Python 3.10+ |
| Vision AI | Google Gemini 1.5 Flash (zero-shot JSON) |
| Fraud Detection | OpenAI CLIP · EXIF metadata · Logic gates |
| Geo Intelligence | OpenStreetMap Overpass API (pre-computed) |
| Economic Model | XGBoost Quantile Regressor (NSSO-calibrated) |

---

## Team

**TenzorX** · National AI Hackathon 2026

---

*Problem Statement 4C — Remote Cash Flow Underwriting via Multi-Modal AI*
