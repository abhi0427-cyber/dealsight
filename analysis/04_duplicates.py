#!/usr/bin/env python3
"""Duplicate detection: fuzzy customer names and deal fingerprints."""

import re
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

deals = pd.read_csv(DATA / "deals.csv")

# ── Customer name normalization ─────────────────────────────────────────
STOP_WORDS = {"inc", "llc", "ltd", "corp", "co", "company", "corporation",
              "limited", "group", "holdings", "partners", "services"}


def normalize_name(name):
    s = str(name).lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)          # drop punctuation
    tokens = [t for t in s.split() if t not in STOP_WORDS]
    return " ".join(tokens)


deals["norm_name"] = deals["customer_name"].map(normalize_name)

unique_names = deals[["customer_name", "norm_name"]].drop_duplicates()
print(f"=== Customer name normalization ===\n")
print(f"Raw unique names:        {deals['customer_name'].nunique()}")
print(f"After normalization:     {unique_names['norm_name'].nunique()}")
print()

# ── Fuzzy similarity pairs (ratio ≥ 0.85) ──────────────────────────────
THRESHOLD = 0.85
norms = unique_names["norm_name"].unique()
pairs = []
for i in range(len(norms)):
    for j in range(i + 1, len(norms)):
        ratio = SequenceMatcher(None, norms[i], norms[j]).ratio()
        if ratio >= THRESHOLD:
            pairs.append((norms[i], norms[j], round(ratio, 3)))

print(f"=== Fuzzy pairs (ratio ≥ {THRESHOLD}) — {len(pairs)} found ===\n")
for a, b, r in sorted(pairs, key=lambda x: -x[2]):
    raw_a = unique_names.loc[unique_names["norm_name"] == a, "customer_name"].iloc[0]
    raw_b = unique_names.loc[unique_names["norm_name"] == b, "customer_name"].iloc[0]
    print(f"  {r:.3f}  {raw_a!r:35s} ↔ {raw_b!r}")
print()

# ── Deal fingerprint duplicates ─────────────────────────────────────────
# Fingerprint: (norm_name, contract_value, term_months, term_start_date)
deals["fingerprint"] = (deals["norm_name"] + "|"
                        + deals["contract_value"].astype(str) + "|"
                        + deals["term_months"].astype(str) + "|"
                        + deals["term_start_date"].astype(str))

dup_fp = deals[deals.duplicated("fingerprint", keep=False)].sort_values("fingerprint")
print(f"=== Fingerprint duplicates ({len(dup_fp)} rows) ===\n")
if len(dup_fp):
    cols = ["deal_id", "customer_name", "contract_value", "term_months",
            "term_start_date", "close_date"]
    print(dup_fp[cols].to_string(index=False))
else:
    print("  (none)")
print()
