"""Tests for loader schema validation."""

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import patch

from dealsight.loader import (
    load_deals, load_line_items, validate, SchemaError,
    REQUIRED_DEAL_COLS, REQUIRED_LINE_ITEM_COLS,
)


def _write_csv(tmp_path: Path, name: str, columns: list[str]) -> Path:
    path = tmp_path / name
    pd.DataFrame(columns=columns).to_csv(path, index=False)
    return path


def test_load_deals_missing_columns(tmp_path):
    """load_deals exits with a message naming the missing columns."""
    present = {"deal_id", "customer_name"}
    path = _write_csv(tmp_path, "deals.csv", list(present))
    with pytest.raises(SchemaError, match="missing required columns"):
        load_deals(path)


def test_load_line_items_missing_columns(tmp_path):
    """load_line_items exits with a message naming the missing columns."""
    present = {"line_id", "deal_id"}
    path = _write_csv(tmp_path, "items.csv", list(present))
    with pytest.raises(SchemaError, match="missing required columns"):
        load_line_items(path)


def test_schema_error_names_file_and_columns(tmp_path):
    """The error message includes the file path and the exact missing columns."""
    present = sorted(REQUIRED_DEAL_COLS - {"po_required", "close_date"})
    path = _write_csv(tmp_path, "deals.csv", present)
    with pytest.raises(SchemaError, match="close_date") as exc_info:
        load_deals(path)
    msg = str(exc_info.value)
    assert "po_required" in msg
    assert str(path) in msg


def test_validate_ok(tmp_path):
    """validate() passes when both CSVs have all required columns."""
    _write_csv(tmp_path, "deals.csv", list(REQUIRED_DEAL_COLS))
    _write_csv(tmp_path, "deal_line_items.csv", list(REQUIRED_LINE_ITEM_COLS))
    validate(data_dir=tmp_path)  # should not raise


def test_validate_catches_bad_line_items(tmp_path):
    """validate() catches missing columns in line items CSV."""
    _write_csv(tmp_path, "deals.csv", list(REQUIRED_DEAL_COLS))
    _write_csv(tmp_path, "deal_line_items.csv", ["line_id", "deal_id"])
    with pytest.raises(SchemaError, match="deal_line_items.csv"):
        validate(data_dir=tmp_path)
