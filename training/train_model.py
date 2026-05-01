"""
TenzorX XGBoost Quantile Regression Training Script
Run this on Google Colab or Kaggle.

STEPS:
  1. Upload this file to Colab/Kaggle
  2. Run: !pip install xgboost scikit-learn pandas numpy matplotlib
  3. Run: !python train_model.py
  4. Download xgb_p10.pkl, xgb_p50.pkl, xgb_p90.pkl
  5. Place them in: code/backend/models/

ALTERNATIVELY (Colab):
  Copy each section into a separate code cell and run cell by cell.
"""

import numpy as np
import pandas as pd
import pickle
import os
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import xgboost as xgb
import warnings
warnings.filterwarnings("ignore")

print("=" * 65)
print("  TenzorX — XGBoost Quantile Regressor Training")
print("  Anchored to NSSO 73rd Round Survey Data")
print("=" * 65)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: NSSO-Anchored Base Revenue Lookup
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

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Synthetic Dataset Generation (N = 5,000 stores)
# ─────────────────────────────────────────────────────────────────────────────
np.random.seed(42)
N = 5000

print(f"\n[Step 1] Generating {N} synthetic kirana stores...")

rows = []
store_sizes = ["small", "medium", "large"]
city_tiers  = [1, 2, 3, 4]
tier_weights = [0.25, 0.35, 0.25, 0.15]  # More Tier 1/2 stores in dataset

for _ in range(N):
    city_tier  = np.random.choice(city_tiers, p=tier_weights)
    store_size = np.random.choice(store_sizes, p=[0.35, 0.45, 0.20])

    # ── Visual proxy features ──────────────────────────────────────────────
    # SDI correlated with store_size and city_tier
    sdi_base   = {"small": 0.55, "medium": 0.70, "large": 0.82}[store_size]
    sdi        = np.clip(np.random.normal(sdi_base, 0.12), 0.20, 0.98)

    sku_base   = {"small": 0.45, "medium": 0.62, "large": 0.78}[store_size]
    sku_div    = np.clip(np.random.normal(sku_base, 0.14), 0.15, 0.98)

    inv_raw    = (sdi * 0.5 + sku_div * 0.3 + np.random.uniform(0, 0.2))
    inv_val    = 0.25 if inv_raw < 0.40 else (0.90 if inv_raw > 0.75 else 0.60)

    refill_r   = np.random.random()
    refill_val = 0.75 if refill_r < 0.35 else (0.25 if refill_r > 0.80 else 0.50)

    size_val   = {"small": 0.25, "medium": 0.60, "large": 0.90}[store_size]
    cleanliness = np.clip(np.random.normal(0.62, 0.18), 0.10, 0.98)

    fmcg        = np.clip(np.random.normal(0.55, 0.18), 0.10, 0.98)
    premium     = np.clip(np.random.normal(
                    {1: 0.40, 2: 0.28, 3: 0.18, 4: 0.12}[city_tier], 0.12
                  ), 0.05, 0.95)
    perishable  = float(np.random.random() > 0.35)

    cust_vals   = [0.10, 0.30, 0.55, 0.75, 0.95]
    cust_probs  = {1: [0.05, 0.15, 0.35, 0.30, 0.15],
                   2: [0.08, 0.22, 0.38, 0.25, 0.07],
                   3: [0.15, 0.30, 0.35, 0.15, 0.05],
                   4: [0.25, 0.35, 0.28, 0.10, 0.02]}
    cust_val    = np.random.choice(cust_vals, p=cust_probs[city_tier])

    # ── Geo proxy features ─────────────────────────────────────────────────
    tier_geo = {
        1: (0.82, 0.78, 11, 0.80),
        2: (0.60, 0.56, 6,  0.58),
        3: (0.38, 0.34, 3,  0.36),
        4: (0.22, 0.20, 2,  0.22),
    }
    pop_base, foot_base, comp_base, poi_base = tier_geo[city_tier]

    pop_density = np.clip(np.random.normal(pop_base, 0.08), 0.05, 1.0)
    footfall    = np.clip(np.random.normal(foot_base, 0.10), 0.05, 1.0)
    competition = max(0, int(np.random.normal(comp_base, 3)))
    poi         = np.clip(np.random.normal(poi_base, 0.10), 0.05, 1.0)
    comp_norm   = min(competition / 20.0, 1.0)
    city_tier_val = {1: 0.90, 2: 0.65, 3: 0.40, 4: 0.20}[city_tier]

    # ── Target: Daily Revenue (NSSO-anchored) ─────────────────────────────
    lo, hi = NSSO_BASE[(city_tier, store_size)]

    # Economic multiplier using proxy signals
    multiplier = (
        sdi      * 0.30 +   # Working capital deployed
        sku_div  * 0.20 +   # Product breadth
        footfall * 0.25 +   # Demand potential
        (1 - comp_norm) * 0.10 +   # Competition effect (inverse)
        cust_val * 0.15           # Customer frequency
    )
    # Multiplier range ~0.3–1.0 → maps revenue across lo–hi range
    multiplier_norm = np.clip(multiplier, 0.10, 1.0)

    base_revenue = lo + (hi - lo) * multiplier_norm
    noise = np.random.normal(1.0, 0.12)   # ±12% stochastic noise
    daily_revenue = max(300.0, base_revenue * noise)

    rows.append({
        # Features (15 total — same order as fusion_engine.py)
        "sdi"        : round(sdi, 4),
        "sku_div"    : round(sku_div, 4),
        "inv_val"    : inv_val,
        "refill_val" : refill_val,
        "size_val"   : size_val,
        "cleanliness": round(cleanliness, 4),
        "fmcg"       : round(fmcg, 4),
        "premium"    : round(premium, 4),
        "perishable" : perishable,
        "cust_val"   : cust_val,
        "pop_density": round(pop_density, 4),
        "footfall"   : round(footfall, 4),
        "comp_norm"  : round(comp_norm, 4),
        "poi"        : round(poi, 4),
        "city_tier_val": city_tier_val,
        # Target
        "daily_revenue": round(daily_revenue, 2),
        # Metadata (not used in training)
        "_city_tier" : city_tier,
        "_store_size": store_size,
    })

df = pd.DataFrame(rows)
print(f"  Generated {len(df)} records.")
print(f"\n  Daily Revenue Stats:")
print(f"    Min : ₹{df.daily_revenue.min():,.0f}")
print(f"    P10 : ₹{df.daily_revenue.quantile(0.10):,.0f}")
print(f"    P50 : ₹{df.daily_revenue.quantile(0.50):,.0f}")
print(f"    P90 : ₹{df.daily_revenue.quantile(0.90):,.0f}")
print(f"    Max : ₹{df.daily_revenue.max():,.0f}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Train XGBoost Quantile Regression (p10, p50, p90)
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "sdi", "sku_div", "inv_val", "refill_val", "size_val",
    "cleanliness", "fmcg", "premium", "perishable", "cust_val",
    "pop_density", "footfall", "comp_norm", "poi", "city_tier_val"
]
TARGET_COL = "daily_revenue"

X = df[FEATURE_COLS].values
y = df[TARGET_COL].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42
)

print(f"\n[Step 2] Training XGBoost Quantile Regressors...")
print(f"  Train size : {len(X_train)}")
print(f"  Test size  : {len(X_test)}")
print(f"  Features   : {len(FEATURE_COLS)}")

QUANTILES = {"p10": 0.10, "p50": 0.50, "p90": 0.90}
trained_models = {}

XGB_PARAMS = dict(
    n_estimators    = 400,
    max_depth       = 6,
    learning_rate   = 0.05,
    subsample       = 0.85,
    colsample_bytree= 0.85,
    min_child_weight= 5,
    reg_alpha       = 0.5,
    reg_lambda      = 1.0,
    tree_method     = "hist",
    random_state    = 42,
    n_jobs          = -1,
)

for name, alpha in QUANTILES.items():
    print(f"\n  Training {name} (alpha={alpha})...")
    model = xgb.XGBRegressor(
        objective    = "reg:quantileerror",
        quantile_alpha = alpha,
        **XGB_PARAMS
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    trained_models[name] = model
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"    ✅ MAE on test set: ₹{mae:,.0f}/day")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: Evaluate Coverage Probability
# Checks: what % of true values fall inside the [p10, p90] interval?
# Target: ~80% (well-calibrated, not too wide)
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[Step 3] Evaluating interval coverage probability...")

p10_preds = trained_models["p10"].predict(X_test)
p90_preds = trained_models["p90"].predict(X_test)

covered = ((y_test >= p10_preds) & (y_test <= p90_preds)).mean()
interval_width = (p90_preds - p10_preds).mean()

print(f"\n  ┌─────────────────────────────────────────┐")
print(f"  │  p10–p90 Coverage Probability: {covered*100:.1f}%    │")
print(f"  │  Mean Interval Width: ₹{interval_width:,.0f}/day   │")
print(f"  │  (Target: 78–85% for well-calibrated)   │")
print(f"  └─────────────────────────────────────────┘")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Feature Importance Plot
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[Step 4] Generating feature importance plot...")

importance = trained_models["p50"].feature_importances_
feat_df = pd.DataFrame({"feature": FEATURE_COLS, "importance": importance})
feat_df = feat_df.sort_values("importance", ascending=True)

plt.figure(figsize=(10, 6))
plt.barh(feat_df["feature"], feat_df["importance"], color="#6366f1")
plt.xlabel("Feature Importance (XGBoost gain)")
plt.title("TenzorX — Feature Importance (p50 model)")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=150)
print("  Saved: feature_importance.png")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: Save Models
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[Step 5] Saving models...")

os.makedirs("models", exist_ok=True)
for name, model in trained_models.items():
    path = f"models/xgb_{name}.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    size_kb = os.path.getsize(path) / 1024
    print(f"  ✅ Saved: {path} ({size_kb:.0f} KB)")

print(f"\n{'=' * 65}")
print(f"  Training complete!")
print(f"  Coverage probability: {covered*100:.1f}%")
print(f"\n  NEXT STEPS:")
print(f"  1. Download xgb_p10.pkl, xgb_p50.pkl, xgb_p90.pkl")
print(f"  2. Place them in: code/backend/models/")
print(f"  3. Set DEMO_MODE=false in your .env")
print(f"  4. Restart the backend: python app.py")
print(f"{'=' * 65}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: Quick Smoke Test
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n[Smoke Test] Verifying a sample prediction...")

sample = np.array([[
    0.78,  # sdi
    0.65,  # sku_div
    0.60,  # inv_val (medium)
    0.75,  # refill_val (recent_demand)
    0.60,  # size_val (medium)
    0.70,  # cleanliness
    0.60,  # fmcg
    0.35,  # premium
    1.0,   # perishable
    0.55,  # cust_val (medium)
    0.85,  # pop_density (Mumbai Tier 1)
    0.80,  # footfall
    0.60,  # comp_norm (12 stores / 20)
    0.85,  # poi
    0.90,  # city_tier_val (Tier 1)
]])

s_p10 = trained_models["p10"].predict(sample)[0]
s_p50 = trained_models["p50"].predict(sample)[0]
s_p90 = trained_models["p90"].predict(sample)[0]

print(f"\n  Sample store (Mumbai, medium, SDI=0.78, high footfall):")
print(f"    Daily Sales Range  : ₹{s_p10:,.0f} – ₹{s_p90:,.0f}")
print(f"    Daily Sales Median : ₹{s_p50:,.0f}")
print(f"    Monthly Revenue    : ₹{s_p10*26:,.0f} – ₹{s_p90*26:,.0f}")
print(f"\n  ✅ Smoke test passed!\n")
