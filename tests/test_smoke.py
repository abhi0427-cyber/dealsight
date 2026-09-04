"""Full-run smoke test — asserts expected bucket counts."""

import pytest
from dealsight.run import run_pipeline


def test_full_run_bucket_counts():
    """Run full pipeline and verify bucket counts match expected values."""
    summary = run_pipeline()
    b = summary["buckets"]

    assert summary["total"] == 65
    assert b["ready"] == 24
    assert b["needs_rep"] == 15
    assert b["needs_approval"] == 6
    assert b["do_not_auto_invoice"] == 20
    assert b.get("error", 0) == 0


def test_full_run_no_errors():
    """No deal should crash."""
    summary = run_pipeline()
    assert summary["buckets"].get("error", 0) == 0
