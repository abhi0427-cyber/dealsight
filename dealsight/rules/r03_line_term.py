"""Rule 3: Line term_months must equal deal term_months."""

import pandas as pd
from . import register


@register("line_term")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["line_term"]
    deal_term = deal.get("term_months")
    if pd.isna(deal_term):
        return []
    findings = []
    for _, ln in lines.iterrows():
        if ln["term_months"] != deal_term:
            findings.append(("line_term", cfg["severity"], {
                "line_id": ln["line_id"],
                "deal_term_months": int(deal_term),
                "line_term_months": int(ln["term_months"]),
            }))
    return findings
