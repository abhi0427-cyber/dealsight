"""Test that re-running the pipeline is idempotent."""

import json
import pytest
from pathlib import Path
from dealsight.run import run_pipeline


def test_idempotent_rerun(tmp_path):
    """Second run should produce same buckets; unchanged payloads should be skipped."""
    # First run
    summary1 = run_pipeline()
    state1 = json.loads(Path("out/state.json").read_text())

    # Count stripe request files
    stripe_files_1 = set(p.name for p in Path("out/stripe_requests").glob("*.json"))

    # Second run
    summary2 = run_pipeline()
    state2 = json.loads(Path("out/state.json").read_text())

    # Same buckets
    assert summary1["buckets"] == summary2["buckets"]

    # Same state (content hashes)
    assert state1 == state2

    # Same stripe request files
    stripe_files_2 = set(p.name for p in Path("out/stripe_requests").glob("*.json"))
    assert stripe_files_1 == stripe_files_2
