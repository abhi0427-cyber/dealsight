#!/usr/bin/env python3
"""Data profiling: shape, dtypes, nulls, categoricals, and special_terms notes."""

from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

deals = pd.read_csv(DATA / "deals.csv")
lines = pd.read_csv(DATA / "deal_line_items.csv")

# ── Shape & dtypes ──────────────────────────────────────────────────────
for name, df in [("deals", deals), ("deal_line_items", lines)]:
    print(f"=== {name} ===")
    print(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n")
    print("Column               Dtype           Non-Null    Null")
    print("-" * 65)
    for col in df.columns:
        nn = df[col].notna().sum()
        na = df[col].isna().sum()
        print(f"{col:20s} {str(df[col].dtype):15s} {nn:>8d}  {na:>6d}")
    print()

# ── Categorical value counts ────────────────────────────────────────────
cat_cols = [
    "deal_type", "deal_owner", "region", "currency",
    "billing_frequency", "payment_terms", "po_required",
    "stage", "invoice_status",
]
print("=== Categorical value counts (deals) ===\n")
for col in cat_cols:
    print(f"--- {col} ---")
    print(deals[col].value_counts(dropna=False).to_string())
    print()

line_cats = ["product", "billing_type"]
print("=== Categorical value counts (deal_line_items) ===\n")
for col in line_cats:
    print(f"--- {col} ---")
    print(lines[col].value_counts(dropna=False).to_string())
    print()

# ── Non-null special_terms notes ────────────────────────────────────────
st = deals.loc[deals["special_terms"].notna() & (deals["special_terms"] != ""),
               ["deal_id", "special_terms"]]
print(f"=== Non-null special_terms ({len(st)} deals) ===\n")
for _, row in st.iterrows():
    print(f"  {row['deal_id']:8s}  {row['special_terms']}")
print()
