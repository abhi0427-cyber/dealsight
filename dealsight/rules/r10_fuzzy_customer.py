"""Rule 10: Fuzzy customer dedup — normalize names, difflib ratio."""

import re
import difflib
import pandas as pd
from . import register

_all_deals: pd.DataFrame | None = None


def set_all_deals(deals: pd.DataFrame) -> None:
    global _all_deals
    _all_deals = deals


def _normalize(name: str) -> str:
    """Lower, strip punctuation, remove Inc/LLC/Ltd/Corp suffixes."""
    name = str(name).lower().strip()
    name = re.sub(r"[,.\-']", " ", name)
    # Remove common suffixes
    for suffix in ("inc", "llc", "ltd", "corp", "corporation", "incorporated", "limited"):
        name = re.sub(rf"\b{suffix}\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


@register("fuzzy_customer")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["fuzzy_customer"]
    threshold = cfg.get("similarity_threshold", 0.85)

    if _all_deals is None:
        return []

    my_name = deal.get("customer_name", "")
    my_norm = _normalize(my_name)
    my_cid = deal.get("customer_id", "")

    matches = []
    seen_cids = set()
    for _, other in _all_deals.iterrows():
        other_cid = other.get("customer_id", "")
        if other_cid == my_cid or other_cid in seen_cids:
            continue
        other_name = other.get("customer_name", "")
        other_norm = _normalize(other_name)
        if my_norm == other_norm and my_cid != other_cid:
            matches.append({"customer_id": other_cid, "name": other_name, "similarity": 1.0})
            seen_cids.add(other_cid)
        elif my_norm != other_norm:
            ratio = difflib.SequenceMatcher(None, my_norm, other_norm).ratio()
            if ratio >= threshold and my_cid != other_cid:
                matches.append({"customer_id": other_cid, "name": other_name, "similarity": round(ratio, 3)})
                seen_cids.add(other_cid)

    if matches:
        return [("fuzzy_customer", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "customer_name": my_name,
            "customer_id": my_cid,
            "similar_customers": matches,
        })]
    return []
