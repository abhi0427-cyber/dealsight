"""Tests for triage — bucket precedence and priority."""

import pandas as pd
import pytest
from dealsight.triage import bucket_for_findings, compute_priority, BUCKET_PRIORITY
import yaml
from pathlib import Path

with open(Path(__file__).parent.parent / "dealsight" / "config.yaml") as f:
    CONFIG = yaml.safe_load(f)


def test_no_findings_is_ready():
    assert bucket_for_findings([], CONFIG) == "ready"


def test_warn_only_is_ready():
    findings = [("fuzzy_customer", "warn", {})]
    assert bucket_for_findings(findings, CONFIG) == "ready"


def test_needs_rep_bucket():
    findings = [("po_required", "block", {})]
    assert bucket_for_findings(findings, CONFIG) == "needs_rep"


def test_needs_approval_bucket():
    findings = [("weighted_discount", "block", {})]
    assert bucket_for_findings(findings, CONFIG) == "needs_approval"


def test_do_not_auto_invoice_bucket():
    findings = [("cv_vs_lines", "block", {})]
    assert bucket_for_findings(findings, CONFIG) == "do_not_auto_invoice"


def test_worst_finding_wins():
    """DNAI > needs_approval > needs_rep."""
    findings = [
        ("po_required", "block", {}),           # needs_rep
        ("weighted_discount", "block", {}),      # needs_approval
        ("cv_vs_lines", "block", {}),            # do_not_auto_invoice
    ]
    assert bucket_for_findings(findings, CONFIG) == "do_not_auto_invoice"


def test_needs_approval_beats_needs_rep():
    findings = [
        ("po_required", "block", {}),
        ("weighted_discount", "block", {}),
    ]
    assert bucket_for_findings(findings, CONFIG) == "needs_approval"


def test_priority_calculation():
    deal = pd.Series({
        "contract_value_usd": 50000,
        "close_date": pd.Timestamp("2025-06-01"),
    })
    from datetime import datetime
    now = datetime(2025, 7, 1)
    priority = compute_priority(deal, now=now)
    assert priority == 50000 * 30
