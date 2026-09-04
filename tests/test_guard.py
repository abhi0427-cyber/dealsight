"""Tests for parser guard — accept and reject cases."""

import pandas as pd
import pytest
from dealsight.parser.guard import reconcile


def _deal(**kwargs):
    defaults = {
        "deal_id": "DD-TEST", "contract_value_usd": 100000,
        "term_months": 12, "term_start": pd.Timestamp("2025-07-01"),
        "special_terms": "",
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def test_guard_coterm_accept():
    parsed = {"type": "coterm", "sub_id": "SUB-001", "coterm_end": "2026-01-01", "prorate": True}
    deal = _deal(term_start=pd.Timestamp("2025-07-01"), contract_value_usd=50000)
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is True


def test_guard_coterm_reject_end_before_start():
    parsed = {"type": "coterm", "sub_id": "SUB-001", "coterm_end": "2025-06-15", "prorate": False}
    deal = _deal(term_start=pd.Timestamp("2025-07-01"))
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is False


def test_guard_coterm_reject_no_end_date():
    parsed = {"type": "coterm", "sub_id": "SUB-001", "coterm_end": None}
    deal = _deal()
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is False


def test_guard_ramp_accept():
    parsed = {"type": "ramp", "ramp": [
        {"year": 1, "amount": 30000},
        {"year": 2, "amount": 35000},
        {"year": 3, "amount": 35000},
    ]}
    deal = _deal(contract_value_usd=100000)
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is True


def test_guard_ramp_reject_sum_mismatch():
    parsed = {"type": "ramp", "ramp": [
        {"year": 1, "amount": 30000},
        {"year": 2, "amount": 35000},
        {"year": 3, "amount": 40000},
    ]}
    deal = _deal(contract_value_usd=95000)  # ramp sum = 105000, >1% diff
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is False


def test_guard_none_with_dollars_suspicious():
    parsed = {"type": "none"}
    deal = _deal(special_terms="Credit of $5,000 applied")
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is False


def test_guard_none_clean():
    parsed = {"type": "none"}
    deal = _deal(special_terms="Standard terms")
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is True


def test_guard_coterm_null_prorate_routes_to_human():
    """Coterm parse with prorate=null should fail the guard (route to do_not_auto_invoice)."""
    parsed = {"type": "coterm", "sub_id": "SUB-001", "coterm_end": "2026-01-01", "prorate": None}
    deal = _deal(term_start=pd.Timestamp("2025-07-01"), contract_value_usd=50000)
    result = reconcile(parsed, deal, pd.DataFrame())
    assert result["pass"] is False
    assert "prorate" in result["reason"]
