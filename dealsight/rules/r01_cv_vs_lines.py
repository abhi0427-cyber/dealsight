"""Rule 1: Contract value vs line-item sum ±$1."""

import pandas as pd
from . import register


@register("cv_vs_lines")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["cv_vs_lines"]
    cv = deal.get("contract_value_usd", 0) or 0
    line_sum = lines["line_total_usd"].sum() if len(lines) > 0 else 0
    tolerance = cfg.get("tolerance_usd", 1.0)
    diff = cv - line_sum
    if abs(diff) > tolerance:
        return [("cv_vs_lines", cfg["severity"], {
            "contract_value": cv,
            "line_sum": round(line_sum, 2),
            "difference": round(diff, 2),
        })]
    return []
