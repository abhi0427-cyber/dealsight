"""Rule 2: Per-line math — list×(1−disc) vs net, qty×net×term/12 vs line_total."""

import pandas as pd
from . import register


@register("line_math")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["line_math"]
    tol = cfg.get("tolerance_usd", 0.01)
    findings = []
    for _, ln in lines.iterrows():
        errors = []
        # Check net = list * (1 - disc/100)
        expected_net = ln["list_unit_price_usd"] * (1 - ln["discount_pct"] / 100)
        if abs(ln["net_unit_price_usd"] - expected_net) > tol:
            errors.append(f"net_unit_price {ln['net_unit_price_usd']} != expected {expected_net:.2f}")
        # Check line_total = qty * net * term/12
        expected_total = ln["quantity"] * ln["net_unit_price_usd"] * ln["term_months"] / 12
        if abs(ln["line_total_usd"] - expected_total) > tol:
            errors.append(f"line_total {ln['line_total_usd']} != expected {expected_total:.2f}")
        if errors:
            findings.append(("line_math", cfg["severity"], {
                "line_id": ln["line_id"],
                "errors": errors,
            }))
    return findings
