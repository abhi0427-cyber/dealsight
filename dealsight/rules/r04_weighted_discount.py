"""Rule 4: Recomputed dollar-weighted discount vs 25% policy + approval."""

import pandas as pd
from . import register


@register("weighted_discount")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["weighted_discount"]
    max_pct = cfg.get("max_discount_pct", 25.0)

    if len(lines) == 0:
        return []

    total_list = (lines["list_unit_price_usd"] * lines["quantity"] * lines["term_months"] / 12).sum()
    total_net = (lines["net_unit_price_usd"] * lines["quantity"] * lines["term_months"] / 12).sum()

    if total_list == 0:
        return []

    weighted_disc = (1 - total_net / total_list) * 100
    reported = deal.get("blended_discount_pct", 0) or 0

    if weighted_disc > max_pct:
        has_approval = pd.notna(deal.get("discount_approval")) and str(deal.get("discount_approval", "")).strip() != ""
        if not has_approval:
            return [("weighted_discount", cfg["severity"], {
                "recomputed_discount_pct": round(weighted_disc, 2),
                "reported_discount_pct": round(reported, 2),
                "threshold_pct": max_pct,
                "approval": None,
            })]
    return []
