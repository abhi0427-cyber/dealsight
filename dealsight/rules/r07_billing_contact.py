"""Rule 7: Billing contact email missing."""

import pandas as pd
from . import register


@register("billing_contact")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["billing_contact"]
    email = deal.get("billing_contact_email")
    if pd.isna(email) or str(email).strip() == "":
        return [("billing_contact", cfg["severity"], {
            "customer": deal.get("customer_name", ""),
            "deal_id": deal["deal_id"],
        })]
    return []
