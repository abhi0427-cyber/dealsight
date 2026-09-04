#!/usr/bin/env python3
"""Reconciliation: contract_value vs line-item sums, and line math verification."""

from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

deals = pd.read_csv(DATA / "deals.csv")
lines = pd.read_csv(DATA / "deal_line_items.csv")

# ── Contract value vs line-item sum per deal ────────────────────────────
line_sums = lines.groupby("deal_id")["line_total_usd"].sum().rename("line_sum")
merged = deals[["deal_id", "contract_value"]].merge(line_sums, on="deal_id", how="left")
merged["line_sum"] = merged["line_sum"].fillna(0)
merged["delta"] = merged["contract_value"] - merged["line_sum"]
merged["pct_diff"] = (merged["delta"] / merged["line_sum"].replace(0, float("nan")) * 100).round(2)

mismatches = merged[merged["delta"].abs() > 0.01].copy()

print("=== Contract value vs line-item sum ===\n")
print(f"Total deals:       {len(merged)}")
print(f"Exact matches:     {len(merged) - len(mismatches)}")
print(f"Mismatches (|Δ|>$0.01): {len(mismatches)}\n")

if len(mismatches):
    print(f"{'deal_id':10s} {'contract_value':>16s} {'line_sum':>12s} {'delta':>10s} {'pct_diff':>10s}")
    print("-" * 62)
    for _, r in mismatches.sort_values("delta", key=abs, ascending=False).iterrows():
        print(f"{r['deal_id']:10s} {r['contract_value']:16,.2f} {r['line_sum']:12,.2f} "
              f"{r['delta']:+10,.2f} {r['pct_diff']:+10.2f}%")
    print()

# ── Line math: line_total_usd = quantity × net_unit_price_usd × term_months/12
print(f"=== Line math verification ({len(lines)} rows) ===\n")

lines["expected_total"] = (lines["quantity"] * lines["net_unit_price_usd"]
                           * lines["term_months"] / 12).round(2)
lines["math_delta"] = (lines["line_total_usd"] - lines["expected_total"]).round(2)

tol = 0.01
ok = lines["math_delta"].abs() <= tol
print(f"Rows passing (|Δ| ≤ ${tol}):  {ok.sum()} / {len(lines)}")
print(f"Rows failing:              {(~ok).sum()}")

if (~ok).any():
    print("\nFailing rows:")
    bad = lines[~ok][["line_id", "deal_id", "quantity", "net_unit_price_usd",
                       "term_months", "line_total_usd", "expected_total", "math_delta"]]
    print(bad.to_string(index=False))
print()
