"""Rule 13: Date sanity — parseable, term_start not before close_date."""

import pandas as pd
from . import register


@register("date_sanity")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["date_sanity"]
    findings = []

    close = deal.get("close_date")
    start = deal.get("term_start")

    if pd.isna(close):
        findings.append(("date_sanity", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "issue": "close_date is missing or unparseable",
        }))
    if pd.isna(start):
        findings.append(("date_sanity", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "issue": "term_start is missing or unparseable",
        }))

    if pd.notna(close) and pd.notna(start):
        if start < close:
            findings.append(("date_sanity", cfg["severity"], {
                "deal_id": deal["deal_id"],
                "issue": "term_start is before close_date",
                "term_start": str(start.date()),
                "close_date": str(close.date()),
            }))

    return findings
