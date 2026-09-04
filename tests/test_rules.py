"""Tests for all 15 rules — happy path + violation for each."""

import pandas as pd
import pytest
import yaml
from pathlib import Path

# Load config
with open(Path(__file__).parent.parent / "dealsight" / "config.yaml") as f:
    CONFIG = yaml.safe_load(f)


def _deal(**kwargs):
    defaults = {
        "deal_id": "DD-TEST", "customer_id": "CUST-999", "customer_name": "Test Co",
        "owner": "Tester", "stage": "Closed Won", "contract_value_usd": 10000,
        "currency": "USD", "term_months": 12, "term_start": pd.Timestamp("2025-07-01"),
        "close_date": pd.Timestamp("2025-06-20"), "billing_frequency": "monthly",
        "payment_terms": "net_30", "po_required": False, "po_number": "",
        "billing_contact_email": "test@example.com", "blended_discount_pct": 10.0,
        "discount_approval": "", "special_terms": "",
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def _lines(deal_id="DD-TEST", items=None):
    if items is None:
        items = [{"line_id": "LI-T1", "deal_id": deal_id, "product": "License",
                  "quantity": 1, "list_unit_price_usd": 11111.11,
                  "discount_pct": 10.0, "net_unit_price_usd": 10000.0,
                  "term_months": 12, "line_total_usd": 10000.0}]
    return pd.DataFrame(items)


# ── Rule 1: CV vs lines ──────────────────────────────────────────────────

def test_r01_pass():
    from dealsight.rules.r01_cv_vs_lines import check
    deal = _deal(contract_value_usd=10000)
    lines = _lines()
    assert check(deal, lines, CONFIG) == []


def test_r01_fail():
    from dealsight.rules.r01_cv_vs_lines import check
    deal = _deal(contract_value_usd=12000)
    lines = _lines()
    result = check(deal, lines, CONFIG)
    assert len(result) == 1
    assert result[0][0] == "cv_vs_lines"
    assert result[0][1] == "block"


# ── Rule 2: Line math ────────────────────────────────────────────────────

def test_r02_pass():
    from dealsight.rules.r02_line_math import check
    deal = _deal()
    lines = _lines()
    assert check(deal, lines, CONFIG) == []


def test_r02_fail():
    from dealsight.rules.r02_line_math import check
    deal = _deal()
    bad_lines = _lines(items=[{
        "line_id": "LI-BAD", "deal_id": "DD-TEST", "product": "License",
        "quantity": 1, "list_unit_price_usd": 100.0,
        "discount_pct": 10.0, "net_unit_price_usd": 95.0,  # Wrong: should be 90
        "term_months": 12, "line_total_usd": 95.0,
    }])
    result = check(deal, bad_lines, CONFIG)
    assert len(result) == 1
    assert result[0][0] == "line_math"


# ── Rule 3: Line term ────────────────────────────────────────────────────

def test_r03_pass():
    from dealsight.rules.r03_line_term import check
    deal = _deal(term_months=12)
    lines = _lines()
    assert check(deal, lines, CONFIG) == []


def test_r03_fail():
    from dealsight.rules.r03_line_term import check
    deal = _deal(term_months=24)
    lines = _lines()  # line term_months=12
    result = check(deal, lines, CONFIG)
    assert len(result) == 1
    assert result[0][0] == "line_term"


# ── Rule 4: Weighted discount ────────────────────────────────────────────

def test_r04_pass():
    from dealsight.rules.r04_weighted_discount import check
    deal = _deal(blended_discount_pct=10.0)
    lines = _lines()
    assert check(deal, lines, CONFIG) == []


def test_r04_fail():
    from dealsight.rules.r04_weighted_discount import check
    deal = _deal(blended_discount_pct=30.0, discount_approval="")
    high_disc_lines = _lines(items=[{
        "line_id": "LI-HD", "deal_id": "DD-TEST", "product": "License",
        "quantity": 1, "list_unit_price_usd": 10000.0,
        "discount_pct": 30.0, "net_unit_price_usd": 7000.0,
        "term_months": 12, "line_total_usd": 7000.0,
    }])
    result = check(deal, high_disc_lines, CONFIG)
    assert len(result) == 1
    assert result[0][0] == "weighted_discount"


# ── Rule 5: Max line discount ────────────────────────────────────────────

def test_r05_pass():
    from dealsight.rules.r05_max_line_discount import check
    deal = _deal()
    lines = _lines()
    assert check(deal, lines, CONFIG) == []


def test_r05_fail():
    from dealsight.rules.r05_max_line_discount import check
    deal = _deal(discount_approval="")
    high_disc_lines = _lines(items=[{
        "line_id": "LI-HD", "deal_id": "DD-TEST", "product": "License",
        "quantity": 1, "list_unit_price_usd": 10000.0,
        "discount_pct": 30.0, "net_unit_price_usd": 7000.0,
        "term_months": 12, "line_total_usd": 7000.0,
    }])
    result = check(deal, high_disc_lines, CONFIG)
    assert len(result) == 1
    assert result[0][0] == "max_line_discount"


# ── Rule 6: PO required ──────────────────────────────────────────────────

def test_r06_pass():
    from dealsight.rules.r06_po_required import check
    deal = _deal(po_required=True, po_number="PO-123")
    assert check(deal, _lines(), CONFIG) == []


def test_r06_fail():
    from dealsight.rules.r06_po_required import check
    deal = _deal(po_required=True, po_number="")
    result = check(deal, _lines(), CONFIG)
    assert len(result) == 1
    assert result[0][0] == "po_required"


# ── Rule 7: Billing contact ──────────────────────────────────────────────

def test_r07_pass():
    from dealsight.rules.r07_billing_contact import check
    deal = _deal(billing_contact_email="ap@test.com")
    assert check(deal, _lines(), CONFIG) == []


def test_r07_fail():
    from dealsight.rules.r07_billing_contact import check
    deal = _deal(billing_contact_email="")
    result = check(deal, _lines(), CONFIG)
    assert len(result) == 1
    assert result[0][0] == "billing_contact"


# ── Rule 8: Email regex ──────────────────────────────────────────────────

def test_r08_pass():
    from dealsight.rules.r08_email_regex import check
    deal = _deal(billing_contact_email="valid@example.com")
    assert check(deal, _lines(), CONFIG) == []


def test_r08_fail():
    from dealsight.rules.r08_email_regex import check
    deal = _deal(billing_contact_email="bad@domain..com")
    result = check(deal, _lines(), CONFIG)
    assert len(result) == 1
    assert result[0][0] == "email_regex"


# ── Rule 9: Duplicate deal ───────────────────────────────────────────────

def test_r09_pass():
    from dealsight.rules.r09_duplicate_deal import check, set_all_deals
    all_deals = pd.DataFrame([
        {"deal_id": "DD-A", "customer_name": "Foo", "contract_value_usd": 1000,
         "term_months": 12, "term_start": pd.Timestamp("2025-07-01"),
         "close_date": pd.Timestamp("2025-06-20")},
        {"deal_id": "DD-B", "customer_name": "Bar", "contract_value_usd": 2000,
         "term_months": 12, "term_start": pd.Timestamp("2025-07-01"),
         "close_date": pd.Timestamp("2025-06-20")},
    ])
    set_all_deals(all_deals)
    deal = all_deals.iloc[0]
    assert check(deal, _lines(), CONFIG) == []


def test_r09_fail():
    from dealsight.rules.r09_duplicate_deal import check, set_all_deals
    all_deals = pd.DataFrame([
        {"deal_id": "DD-A", "customer_name": "Same Corp", "contract_value_usd": 5000,
         "term_months": 12, "term_start": pd.Timestamp("2025-07-01"),
         "close_date": pd.Timestamp("2025-06-20")},
        {"deal_id": "DD-B", "customer_name": "Same Corp", "contract_value_usd": 5000,
         "term_months": 12, "term_start": pd.Timestamp("2025-07-01"),
         "close_date": pd.Timestamp("2025-06-22")},
    ])
    set_all_deals(all_deals)
    deal = all_deals.iloc[0]
    result = check(deal, _lines(), CONFIG)
    assert len(result) == 1
    assert result[0][0] == "duplicate_deal"


# ── Rule 10: Fuzzy customer ──────────────────────────────────────────────

def test_r10_pass():
    from dealsight.rules.r10_fuzzy_customer import check, set_all_deals
    all_deals = pd.DataFrame([
        {"deal_id": "DD-A", "customer_id": "C-1", "customer_name": "Alpha"},
        {"deal_id": "DD-B", "customer_id": "C-2", "customer_name": "Zebra"},
    ])
    set_all_deals(all_deals)
    deal = all_deals.iloc[0]
    assert check(deal, _lines(), CONFIG) == []


def test_r10_fail():
    from dealsight.rules.r10_fuzzy_customer import check, set_all_deals
    all_deals = pd.DataFrame([
        {"deal_id": "DD-A", "customer_id": "C-1", "customer_name": "Northwind Labs"},
        {"deal_id": "DD-B", "customer_id": "C-2", "customer_name": "Northwind Labs Inc"},
    ])
    set_all_deals(all_deals)
    deal = all_deals.iloc[0]
    result = check(deal, _lines(), CONFIG)
    assert len(result) == 1
    assert result[0][0] == "fuzzy_customer"


# ── Rule 11: Empty deal ──────────────────────────────────────────────────

def test_r11_pass():
    from dealsight.rules.r11_empty_deal import check
    deal = _deal(contract_value_usd=10000)
    assert check(deal, _lines(), CONFIG) == []


def test_r11_fail():
    from dealsight.rules.r11_empty_deal import check
    deal = _deal(contract_value_usd=0)
    result = check(deal, pd.DataFrame(columns=["line_total_usd"]), CONFIG)
    assert len(result) == 1
    assert result[0][0] == "empty_deal"


# ── Rule 12: Currency mismatch ───────────────────────────────────────────

def test_r12_pass():
    from dealsight.rules.r12_currency_mismatch import check
    deal = _deal(currency="USD")
    assert check(deal, _lines(), CONFIG) == []


def test_r12_fail():
    from dealsight.rules.r12_currency_mismatch import check
    deal = _deal(currency="EUR", contract_value_usd=10000)
    lines = _lines()  # line_total_usd sums to 10000
    result = check(deal, lines, CONFIG)
    assert len(result) == 1
    assert result[0][0] == "currency_mismatch"


# ── Rule 13: Date sanity ─────────────────────────────────────────────────

def test_r13_pass():
    from dealsight.rules.r13_date_sanity import check
    deal = _deal(close_date=pd.Timestamp("2025-06-20"),
                 term_start=pd.Timestamp("2025-07-01"))
    assert check(deal, _lines(), CONFIG) == []


def test_r13_fail():
    from dealsight.rules.r13_date_sanity import check
    deal = _deal(close_date=pd.Timestamp("2025-07-15"),
                 term_start=pd.Timestamp("2025-07-01"))  # start before close
    result = check(deal, _lines(), CONFIG)
    assert len(result) >= 1
    assert any(r[0] == "date_sanity" for r in result)


# ── Rule 14: Billing Stripe ──────────────────────────────────────────────

def test_r14_pass():
    from dealsight.rules.r14_billing_stripe import check
    deal = _deal(billing_frequency="monthly", payment_terms="net_30")
    assert check(deal, _lines(), CONFIG) == []


def test_r14_fail():
    from dealsight.rules.r14_billing_stripe import check
    deal = _deal(billing_frequency="biweekly", payment_terms="net_30")
    result = check(deal, _lines(), CONFIG)
    assert len(result) >= 1
    assert any(r[0] == "billing_stripe" for r in result)


# ── Rule 15: Special terms ───────────────────────────────────────────────

def test_r15_pass():
    from dealsight.rules.r15_special_terms import check
    deal = _deal(special_terms="")
    assert check(deal, _lines(), CONFIG) == []


def test_r15_coterm():
    from dealsight.rules.r15_special_terms import check
    deal = _deal(special_terms="Co-terminate with SUB-00100 ending 2026-01-01",
                 term_start=pd.Timestamp("2025-07-01"), contract_value_usd=10000)
    result = check(deal, _lines(), CONFIG)
    assert len(result) >= 1
    assert any(r[0] == "special_terms" for r in result)
