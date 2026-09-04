"""Load deal and line-item CSVs into DataFrames."""

import sys
from pathlib import Path
import pandas as pd

# Canonical column names the rules expect → possible source names
_DEAL_RENAMES = {
    "deal_owner": "owner",
    "term_start_date": "term_start",
    "contract_value": "contract_value_usd",
}

# Required columns checked *before* renames (i.e. as they appear in the CSV)
REQUIRED_DEAL_COLS = frozenset({
    "deal_id", "customer_name", "customer_id", "deal_owner", "close_date",
    "term_start_date", "term_months", "currency", "contract_value",
    "blended_discount_pct", "billing_frequency", "payment_terms",
    "po_required", "po_number", "billing_contact_email",
})

REQUIRED_LINE_ITEM_COLS = frozenset({
    "line_id", "deal_id", "product", "quantity", "list_unit_price_usd",
    "discount_pct", "net_unit_price_usd", "term_months", "line_total_usd",
})


class SchemaError(SystemExit):
    """Raised when a CSV is missing required columns."""


def _check_columns(df: pd.DataFrame, required: frozenset, file_path: Path) -> None:
    """Exit with a clear message if *required* columns are missing from *df*."""
    missing = required - set(df.columns)
    if missing:
        raise SchemaError(
            f"{file_path}: missing required columns: {', '.join(sorted(missing))}"
        )


def validate(data_dir: Path = Path("data")) -> None:
    """Load both CSVs and validate schemas. Raises SchemaError on failure."""
    deals_path = data_dir / "deals.csv"
    items_path = data_dir / "deal_line_items.csv"
    deals_df = pd.read_csv(deals_path, nrows=0)
    items_df = pd.read_csv(items_path, nrows=0)
    _check_columns(deals_df, REQUIRED_DEAL_COLS, deals_path)
    _check_columns(items_df, REQUIRED_LINE_ITEM_COLS, items_path)


def load_deals(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"deal_id": str, "customer_id": str, "po_number": str})
    _check_columns(df, REQUIRED_DEAL_COLS, path)
    # Rename columns to canonical names
    rename = {src: dst for src, dst in _DEAL_RENAMES.items() if src in df.columns}
    df = df.rename(columns=rename)
    # Normalise boolean column
    if "po_required" in df.columns:
        df["po_required"] = df["po_required"].map(
            lambda v: str(v).strip().lower() in ("true", "1", "yes") if pd.notna(v) else False
        )
    # Parse dates
    for col in ("term_start", "close_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    # Ensure numeric
    for col in ("contract_value_usd", "blended_discount_pct", "term_months"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_line_items(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"line_id": str, "deal_id": str})
    _check_columns(df, REQUIRED_LINE_ITEM_COLS, path)
    for col in ("quantity", "list_unit_price_usd", "discount_pct",
                "net_unit_price_usd", "term_months", "line_total_usd"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
