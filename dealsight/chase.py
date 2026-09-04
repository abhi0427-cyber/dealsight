"""Chase — draft Slack messages for needs_rep deals → out/outbox/*.txt."""

from pathlib import Path
from datetime import datetime
import pandas as pd

OUTBOX = Path("out/outbox")


def draft_chase(deal: pd.Series, findings: list[tuple[str, str, dict]]) -> str:
    """Draft a Slack message naming the exact missing items."""
    deal_id = deal["deal_id"]
    customer = deal.get("customer_name", "Unknown")
    owner = deal.get("owner", "Unknown")
    cv = deal.get("contract_value_usd", 0) or 0
    close_date = deal.get("close_date")

    if pd.notna(close_date):
        close_dt = close_date.to_pydatetime() if hasattr(close_date, 'to_pydatetime') else close_date
        if hasattr(close_dt, 'tzinfo') and close_dt.tzinfo:
            close_dt = close_dt.replace(tzinfo=None)
        days = (datetime.now() - close_dt).days
    else:
        days = 0

    missing_items = []
    for code, severity, evidence in findings:
        if code == "po_required":
            missing_items.append("PO number (required by customer)")
        elif code == "billing_contact":
            missing_items.append("billing contact email")
        elif code == "email_regex":
            email = evidence.get("email", "")
            missing_items.append(f"valid billing email (current: {email})")
        elif code == "date_sanity":
            missing_items.append(f"date fix: {evidence.get('issue', 'date issue')}")
        elif code == "billing_stripe":
            missing_items.append(f"billing config: {evidence.get('issue', 'billing issue')}")

    if not missing_items:
        return ""

    items_text = "\n".join(f"  - {item}" for item in missing_items)

    msg = (
        f"Hi {owner},\n\n"
        f"Deal {deal_id} for {customer} (${cv:,.2f}) closed {days} days ago "
        f"but can't be invoiced yet. Missing:\n"
        f"{items_text}\n\n"
        f"Can you update HubSpot so we can get this billed?\n\n"
        f"— DealSight"
    )
    return msg


def write_chase(deal: pd.Series, findings: list[tuple[str, str, dict]]) -> Path | None:
    """Write chase message to outbox, return path."""
    msg = draft_chase(deal, findings)
    if not msg:
        return None
    OUTBOX.mkdir(parents=True, exist_ok=True)
    path = OUTBOX / f"{deal['deal_id']}.txt"
    path.write_text(msg)
    return path
