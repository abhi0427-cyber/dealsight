"""Rule 14: billing_frequency + payment_terms mappable to Stripe interval / days_until_due."""

import pandas as pd
from . import register

# Map billing_frequency (case-insensitive) → Stripe recurring interval
STRIPE_INTERVAL_MAP = {
    "monthly": {"interval": "month", "interval_count": 1},
    "quarterly": {"interval": "month", "interval_count": 3},
    "annual": {"interval": "year", "interval_count": 1},
    "annual upfront": {"interval": "year", "interval_count": 1},
    "yearly": {"interval": "year", "interval_count": 1},
}

# Map payment_terms (case-insensitive) → days_until_due
DAYS_DUE_MAP = {
    "net_15": 15, "net 15": 15,
    "net_30": 30, "net 30": 30,
    "net_45": 45, "net 45": 45,
    "net_60": 60, "net 60": 60,
    "net_90": 90, "net 90": 90,
    "due_on_receipt": 0, "due on receipt": 0,
}


def map_frequency(freq: str) -> dict | None:
    freq = str(freq).strip().lower()
    return STRIPE_INTERVAL_MAP.get(freq)


def map_payment_terms(terms: str) -> int | None:
    terms = str(terms).strip().lower()
    return DAYS_DUE_MAP.get(terms)


@register("billing_stripe")
def check(deal: pd.Series, lines: pd.DataFrame, config: dict) -> list[tuple[str, str, dict]]:
    cfg = config["rules"]["billing_stripe"]
    findings = []

    freq = deal.get("billing_frequency", "")
    if pd.isna(freq) or map_frequency(str(freq)) is None:
        findings.append(("billing_stripe", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "issue": f"billing_frequency '{freq}' not mappable to Stripe interval",
        }))

    terms = deal.get("payment_terms", "")
    if pd.isna(terms) or map_payment_terms(str(terms)) is None:
        findings.append(("billing_stripe", cfg["severity"], {
            "deal_id": deal["deal_id"],
            "issue": f"payment_terms '{terms}' not mappable to Stripe days_until_due",
        }))

    return findings
