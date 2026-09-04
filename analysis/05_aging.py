#!/usr/bin/env python3
"""Aging analysis: days since close, stale dollars, and past-due term starts."""

from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

deals = pd.read_csv(DATA / "deals.csv")
today = pd.Timestamp.today().normalize()

deals["close_date"] = pd.to_datetime(deals["close_date"], errors="coerce")
deals["term_start_date"] = pd.to_datetime(deals["term_start_date"], errors="coerce")

# ── Days since close ────────────────────────────────────────────────────
deals["days_since_close"] = (today - deals["close_date"]).dt.days

valid = deals["days_since_close"].dropna()
print(f"=== Days since close (reference: {today.date()}) ===\n")
print(f"  Count:   {len(valid)}")
print(f"  Median:  {valid.median():.0f}")
print(f"  P90:     {valid.quantile(0.9):.0f}")
print(f"  Max:     {valid.max():.0f}")
print()

# ── Deals over 60 days since close ──────────────────────────────────────
stale = deals[deals["days_since_close"] > 60].copy()
stale_dollars = stale["contract_value"].sum()

print(f"=== Deals > 60 days since close ===\n")
print(f"  Count:   {len(stale)}")
print(f"  Dollars: ${stale_dollars:,.2f}")
if len(stale):
    print()
    cols = ["deal_id", "customer_name", "contract_value", "close_date", "days_since_close"]
    print(stale.sort_values("days_since_close", ascending=False)[cols].to_string(index=False))
print()

# ── Term start already in the past ──────────────────────────────────────
past_start = deals[deals["term_start_date"] < today].copy()
print(f"=== Deals with term_start_date already in the past ===\n")
print(f"  Count:   {len(past_start)}")
if len(past_start):
    past_start["days_past"] = (today - past_start["term_start_date"]).dt.days
    cols = ["deal_id", "customer_name", "term_start_date", "days_past", "invoice_status"]
    print()
    print(past_start.sort_values("days_past", ascending=False)[cols].to_string(index=False))
print()
