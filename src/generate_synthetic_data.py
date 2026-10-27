"""
Synthetic Demonstration Data Generator
======================================
PURPOSE:
Generate privacy-safe, synthetic inventory datasets to demonstrate and test
the local MLflow experiment tracking and data drift detection pipeline without
using or exposing any real, private business data.

OUTPUTS:
- data/synthetic_demo_reference.csv: Baseline inventory stock distribution
- data/synthetic_demo_current.csv: Operational inventory stock distribution (with simulated drift)
"""

import os
import sys
from pathlib import Path

# ==============================================================================
# Auto-Bootstrap: Bridge to project .venv if invoked with system Python
# ==============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_VENV_SITE = PROJECT_ROOT / ".venv" / "Lib" / "site-packages"
if LOCAL_VENV_SITE.exists() and str(LOCAL_VENV_SITE) not in sys.path:
    sys.path.insert(0, str(LOCAL_VENV_SITE))

import numpy as np
import pandas as pd

def generate_synthetic_inventory_data(n_samples=500, seed=42):
    """Generate baseline and drifted synthetic inventory datasets."""
    rng = np.random.default_rng(seed)
    os.makedirs("data", exist_ok=True)

    categories = ["Electronics", "Apparel", "Home & Kitchen", "Automotive", "Office Supplies"]

    # --- 1. Baseline Reference Dataset (Historical stable period) ---
    ref_skus = [f"SKU-DEMO-{1000 + i}" for i in range(n_samples)]
    ref_categories = rng.choice(categories, size=n_samples)
    ref_stock = rng.normal(loc=250.0, scale=45.0, size=n_samples).clip(min=10).round()
    ref_reorder = rng.normal(loc=80.0, scale=15.0, size=n_samples).clip(min=5).round()
    ref_unit_cost = rng.uniform(low=12.0, high=120.0, size=n_samples).round(2)
    ref_unit_price = (ref_unit_cost * rng.uniform(low=1.3, high=1.8, size=n_samples)).round(2)
    ref_monthly_demand = rng.normal(loc=110.0, scale=25.0, size=n_samples).clip(min=5).round()
    ref_lead_time_days = rng.integers(low=3, high=21, size=n_samples)

    df_reference = pd.DataFrame({
        "sku_id": ref_skus,
        "category": ref_categories,
        "current_stock": ref_stock,
        "reorder_point": ref_reorder,
        "unit_cost": ref_unit_cost,
        "unit_price": ref_unit_price,
        "monthly_demand": ref_monthly_demand,
        "lead_time_days": ref_lead_time_days,
    })

    # --- 2. Current Dataset (Simulated supply chain shock / drift) ---
    cur_stock = rng.normal(loc=165.0, scale=40.0, size=n_samples).clip(min=5).round()
    cur_reorder = rng.normal(loc=81.0, scale=14.5, size=n_samples).clip(min=5).round()
    cur_unit_cost = rng.uniform(low=12.0, high=120.0, size=n_samples).round(2)
    cur_unit_price = (cur_unit_cost * rng.uniform(low=1.3, high=1.8, size=n_samples)).round(2)
    cur_monthly_demand = rng.normal(loc=145.0, scale=30.0, size=n_samples).clip(min=10).round()
    cur_lead_time_days = rng.integers(low=7, high=28, size=n_samples)

    df_current = pd.DataFrame({
        "sku_id": ref_skus,
        "category": ref_categories,
        "current_stock": cur_stock,
        "reorder_point": cur_reorder,
        "unit_cost": cur_unit_cost,
        "unit_price": cur_unit_price,
        "monthly_demand": cur_monthly_demand,
        "lead_time_days": cur_lead_time_days,
    })

    ref_path = os.path.join("data", "synthetic_demo_reference.csv")
    cur_path = os.path.join("data", "synthetic_demo_current.csv")

    df_reference.to_csv(ref_path, index=False)
    df_current.to_csv(cur_path, index=False)

    print("Synthetic Demonstration Datasets Generated Successfully:")
    print(f"  Reference Demo: {ref_path} ({len(df_reference)} records)")
    print(f"  Current Demo:   {cur_path} ({len(df_current)} records)")
    print("\nNote: These datasets are purely synthetic and safe for public demonstration.")

if __name__ == "__main__":
    generate_synthetic_inventory_data()
