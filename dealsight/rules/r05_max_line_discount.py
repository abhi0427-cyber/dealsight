"""Rule 5: Max per-line discount vs 25% policy + approval."""

import pandas as pd
from . import register


@register("max_line_discount")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["max_line_discount"]
    max_pct = cfg.get("max_discount_pct", 25.0)

    if len(lines) == 0:
        return []

    violations = []
    for _, ln in lines.iterrows():
        disc = ln.get("discount_pct", 0) or 0
        if disc > max_pct:
            violations.append({"line_id": ln["line_id"], "discount_pct": disc})

    if violations:
        has_approval = pd.notna(deal.get("discount_approval")) and str(deal.get("discount_approval", "")).strip() != ""
        if not has_approval:
            return [("max_line_discount", cfg["severity"], {
                "lines_over_threshold": violations,
                "threshold_pct": max_pct,
                "approval": None,
            })]
    return []
