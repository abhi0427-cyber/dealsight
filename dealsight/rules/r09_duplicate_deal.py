"""Rule 9: Duplicate-deal fingerprint (customer+value+term+start, close ≤7d)."""

import pandas as pd
from . import register

# This rule needs all deals, so we cache and compare.
# The check function receives one deal at a time, but we detect dupes
# by comparing against the full deals DataFrame stored in _all_deals.

_all_deals: pd.DataFrame | None = None


def set_all_deals(deals: pd.DataFrame) -> None:
    global _all_deals
    _all_deals = deals


@register("duplicate_deal")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["duplicate_deal"]
    window = cfg.get("close_date_window_days", 7)

    if _all_deals is None:
        return []

    matches = []
    for _, other in _all_deals.iterrows():
        if other["deal_id"] == deal["deal_id"]:
            continue
        # Same customer (by name, case-insensitive)
        if str(deal.get("customer_name", "")).strip().lower() != str(other.get("customer_name", "")).strip().lower():
            continue
        # Same contract value
        if deal.get("contract_value_usd") != other.get("contract_value_usd"):
            continue
        # Same term
        if deal.get("term_months") != other.get("term_months"):
            continue
        # Same start date
        if pd.notna(deal.get("term_start")) and pd.notna(other.get("term_start")):
            if deal["term_start"] != other["term_start"]:
                continue
        # Close dates within window
        if pd.notna(deal.get("close_date")) and pd.notna(other.get("close_date")):
            delta = abs((deal["close_date"] - other["close_date"]).days)
            if delta > window:
                continue
        else:
            continue
        matches.append(other["deal_id"])

    if matches:
        return [("duplicate_deal", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "duplicate_of": matches,
        })]
    return []
