#!/usr/bin/env python3
"""Discount analysis: unweighted vs dollar-weighted blended discount."""

from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

deals = pd.read_csv(DATA / "deals.csv")
lines = pd.read_csv(DATA / "deal_line_items.csv")

# Only deals that have line items
deals_with_lines = deals[deals["deal_id"].isin(lines["deal_id"])].copy()
n = len(deals_with_lines)
print(f"=== Discount analysis ({n} deals with line items) ===\n")

# ── Prove blended_discount_pct = unweighted mean of line discounts ──────
unweighted = (lines.groupby("deal_id")["discount_pct"]
              .mean().round(1).rename("unweighted_mean"))
merged = deals_with_lines[["deal_id", "blended_discount_pct"]].merge(
    unweighted, on="deal_id")
merged["match"] = (merged["blended_discount_pct"] - merged["unweighted_mean"]).abs() <= 0.05

match_count = merged["match"].sum()
print(f"blended_discount_pct == unweighted mean of line discounts: "
      f"{match_count} / {n}")
if match_count < n:
    print("\nMismatches:")
    mis = merged[~merged["match"]]
    print(mis.to_string(index=False))
print()

# ── Compute dollar-weighted discount per deal ───────────────────────────
lines_ext = lines.copy()
lines_ext["gross_total"] = (lines_ext["quantity"]
                            * lines_ext["list_unit_price_usd"]
                            * lines_ext["term_months"] / 12)
lines_ext["discount_dollars"] = lines_ext["gross_total"] * lines_ext["discount_pct"] / 100

deal_agg = lines_ext.groupby("deal_id").agg(
    gross_total=("gross_total", "sum"),
    discount_dollars=("discount_dollars", "sum"),
).reset_index()
deal_agg["weighted_discount_pct"] = (
    deal_agg["discount_dollars"] / deal_agg["gross_total"] * 100
).round(2)

compare = deals_with_lines[["deal_id", "blended_discount_pct"]].merge(
    deal_agg[["deal_id", "weighted_discount_pct"]], on="deal_id")
compare["delta"] = (compare["weighted_discount_pct"]
                    - compare["blended_discount_pct"]).round(2)

print("=== Dollar-weighted discount vs stored blended_discount_pct ===\n")
print(f"{'deal_id':10s} {'stored':>8s} {'weighted':>10s} {'delta':>8s}")
print("-" * 40)
for _, r in compare.iterrows():
    print(f"{r['deal_id']:10s} {r['blended_discount_pct']:8.1f} "
          f"{r['weighted_discount_pct']:10.2f} {r['delta']:+8.2f}")
print()

# ── Key finding: stored ≤25% but true weighted discount >25% ───────────
hidden = compare[(compare["blended_discount_pct"] <= 25)
                 & (compare["weighted_discount_pct"] > 25)]
print(f"=== Deals where stored ≤ 25% but weighted > 25% ({len(hidden)} found) ===\n")
if len(hidden):
    print(f"{'deal_id':10s} {'stored':>8s} {'weighted':>10s}")
    print("-" * 30)
    for _, r in hidden.iterrows():
        print(f"{r['deal_id']:10s} {r['blended_discount_pct']:8.1f} "
              f"{r['weighted_discount_pct']:10.2f}")
else:
    print("  (none)")
print()
