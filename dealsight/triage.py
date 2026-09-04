"""Triage — bucket deals based on rule findings.

Buckets: ready / needs_rep / needs_approval / do_not_auto_invoice / error
Worst finding wins. Priority = contract_value × days_since_close.
"""

from datetime import datetime
import pandas as pd


BUCKET_PRIORITY = ["do_not_auto_invoice", "needs_approval", "needs_rep", "ready"]


def bucket_for_findings(findings: list[tuple[str, str, dict]], config: dict) -> str:
    """Determine bucket from list of (code, severity, evidence) findings."""
    if not findings:
        return "ready"

    bucket_map = config.get("bucket_map", {})
    worst = "ready"
    worst_idx = len(BUCKET_PRIORITY) - 1

    for code, severity, _ in findings:
        if severity == "warn":
            continue  # Warnings don't affect bucket
        bucket = bucket_map.get(code, "do_not_auto_invoice")
        try:
            idx = BUCKET_PRIORITY.index(bucket)
        except ValueError:
            idx = 0  # Unknown → worst
        if idx < worst_idx:
            worst_idx = idx
            worst = bucket

    return worst


def compute_priority(deal: pd.Series, now: datetime | None = None) -> float:
    """Priority = contract_value × days_since_close."""
    now = now or datetime.now()
    cv = deal.get("contract_value_usd", 0) or 0
    close = deal.get("close_date")
    if pd.isna(close):
        days = 0
    else:
        close_dt = close.to_pydatetime() if hasattr(close, 'to_pydatetime') else close
        if hasattr(close_dt, 'tzinfo') and close_dt.tzinfo:
            close_dt = close_dt.replace(tzinfo=None)
        days = max((now - close_dt).days, 0)
    return cv * days


def triage_deal(deal: pd.Series, findings: list[tuple[str, str, dict]], config: dict) -> dict:
    """Return triage result for a deal."""
    bucket = bucket_for_findings(findings, config)
    priority = compute_priority(deal)
    return {
        "deal_id": deal["deal_id"],
        "bucket": bucket,
        "findings": findings,
        "priority": priority,
        "contract_value": deal.get("contract_value_usd", 0) or 0,
        "customer_name": deal.get("customer_name", ""),
        "owner": deal.get("owner", ""),
        "close_date": str(deal["close_date"].date()) if pd.notna(deal.get("close_date")) else None,
        "currency": deal.get("currency", "USD"),
    }
