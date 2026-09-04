"""Stripe payload builder — ready deals only.

Builds real Stripe shapes: /v1/customers, /v1/subscriptions.
MockStripe writes JSON to out/stripe_requests/.
Idempotency: per-deal content hash in out/state.json; unchanged deals skip.
"""

import hashlib
import json
from pathlib import Path
import pandas as pd
from dealsight.rules.r14_billing_stripe import map_frequency, map_payment_terms


STATE_PATH = Path("out/state.json")
STRIPE_DIR = Path("out/stripe_requests")


def _content_hash(deal: pd.Series, lines: pd.DataFrame) -> str:
    """Deterministic hash of deal + line data."""
    data = {
        "deal_id": deal["deal_id"],
        "contract_value_usd": deal.get("contract_value_usd"),
        "customer_name": deal.get("customer_name"),
        "term_months": int(deal.get("term_months", 0)),
        "billing_frequency": deal.get("billing_frequency"),
        "payment_terms": deal.get("payment_terms"),
        "lines": [
            {
                "line_id": ln["line_id"],
                "product": ln.get("product"),
                "quantity": int(ln.get("quantity", 0)),
                "net_unit_price_usd": ln.get("net_unit_price_usd"),
                "line_total_usd": ln.get("line_total_usd"),
            }
            for _, ln in lines.iterrows()
        ],
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def build_payload(deal: pd.Series, lines: pd.DataFrame, bucket: str) -> dict | None:
    """Build Stripe payload for a ready deal. Returns None if non-ready or unchanged."""
    if bucket != "ready":
        raise ValueError(f"Refusing to build payload for non-ready deal {deal['deal_id']} (bucket={bucket})")

    deal_id = deal["deal_id"]
    content_hash = _content_hash(deal, lines)

    # Idempotency check
    state = _load_state()
    if state.get(deal_id) == content_hash:
        return None  # Unchanged

    freq_info = map_frequency(str(deal.get("billing_frequency", "annual")))
    days_due = map_payment_terms(str(deal.get("payment_terms", "net_30")))
    if days_due is None:
        days_due = 30
    if freq_info is None:
        freq_info = {"interval": "year", "interval_count": 1}

    # Build customer object
    customer = {
        "object": "customer",
        "name": deal.get("customer_name", ""),
        "email": deal.get("billing_contact_email", ""),
        "metadata": {
            "deal_id": deal_id,
            "customer_id": deal.get("customer_id", ""),
        },
    }

    # Build subscription with price_data items
    items = []
    for _, ln in lines.iterrows():
        items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {"name": ln.get("product", "Unknown")},
                "unit_amount": int(round(ln["net_unit_price_usd"] * 100)),
                "recurring": {
                    "interval": freq_info["interval"],
                    "interval_count": freq_info["interval_count"],
                },
            },
            "quantity": int(ln.get("quantity", 1)),
        })

    subscription = {
        "object": "subscription",
        "customer": f"{{customer_id}}",  # Placeholder
        "items": items,
        "collection_method": "send_invoice",
        "days_until_due": days_due,
        "metadata": {
            "deal_id": deal_id,
            "content_hash": content_hash,
        },
    }

    payload = {
        "customer": customer,
        "subscription": subscription,
    }

    # Write to mock stripe directory
    STRIPE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = STRIPE_DIR / f"{deal_id}.json"
    out_path.write_text(json.dumps(payload, indent=2))

    # Update state
    state[deal_id] = content_hash
    _save_state(state)

    return payload
