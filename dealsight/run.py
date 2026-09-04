"""Main pipeline — load data, run rules, triage, output."""

import traceback
from pathlib import Path
from datetime import datetime

import pandas as pd
import yaml

from dealsight.loader import load_deals, load_line_items
from dealsight.rules import get_all_rules
from dealsight.rules.r09_duplicate_deal import set_all_deals as set_dup_deals
from dealsight.rules.r10_fuzzy_customer import set_all_deals as set_fuzzy_deals
from dealsight.triage import triage_deal
from dealsight import ledger
from dealsight.stripe_payload import build_payload
from dealsight.chase import write_chase


def load_config() -> dict:
    cfg_path = Path(__file__).parent / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def run_pipeline(data_dir: Path = Path("data"), out_dir: Path = Path("out")) -> dict:
    """Run full pipeline. Returns summary dict."""
    config = load_config()

    # Load data
    deals = load_deals(data_dir / "deals.csv")
    line_items = load_line_items(data_dir / "deal_line_items.csv")

    # Set global state for cross-deal rules
    set_dup_deals(deals)
    set_fuzzy_deals(deals)

    # Get all rules
    rules = get_all_rules()

    # Process each deal
    results = []
    buckets = {"ready": 0, "needs_rep": 0, "needs_approval": 0,
               "do_not_auto_invoice": 0, "error": 0}

    for _, deal in deals.iterrows():
        deal_id = deal["deal_id"]
        deal_lines = line_items[line_items["deal_id"] == deal_id]

        try:
            # Run all rules
            all_findings = []
            for rule_code, check_fn in rules.items():
                try:
                    findings = check_fn(deal, deal_lines, config)
                    all_findings.extend(findings)
                except Exception as e:
                    all_findings.append(("rule_error", "block", {
                        "rule": rule_code,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    }))

            # Triage
            result = triage_deal(deal, all_findings, config)
            results.append(result)
            bucket = result["bucket"]
            buckets[bucket] = buckets.get(bucket, 0) + 1

            # Ledger
            ledger.append(deal_id, bucket, all_findings)

            # Post-triage actions
            if bucket == "ready":
                try:
                    build_payload(deal, deal_lines, bucket)
                except Exception:
                    pass  # Non-fatal

            elif bucket == "needs_rep":
                try:
                    write_chase(deal, all_findings)
                except Exception:
                    pass  # Non-fatal

        except Exception:
            buckets["error"] = buckets.get("error", 0) + 1
            tb = traceback.format_exc()
            ledger.append(deal_id, "error", [], extra={"traceback": tb})
            results.append({
                "deal_id": deal_id,
                "bucket": "error",
                "findings": [],
                "priority": 0,
                "contract_value": deal.get("contract_value_usd", 0),
                "customer_name": deal.get("customer_name", ""),
                "owner": deal.get("owner", ""),
                "close_date": None,
                "currency": deal.get("currency", "USD"),
            })

    # Sort by priority descending
    results.sort(key=lambda r: r.get("priority", 0), reverse=True)

    summary = {
        "total": len(deals),
        "buckets": buckets,
        "results": results,
    }

    # Run eval if golden.json exists
    try:
        from pathlib import Path as _P
        if _P("golden/golden.json").exists():
            from dealsight.eval import run_eval
            run_eval()
    except Exception:
        pass  # Non-fatal

    return summary


def print_summary(summary: dict) -> None:
    b = summary["buckets"]
    total = summary["total"]
    parts = [f"ready:{b.get('ready',0)}",
             f"needs_rep:{b.get('needs_rep',0)}",
             f"needs_approval:{b.get('needs_approval',0)}",
             f"do_not_auto_invoice:{b.get('do_not_auto_invoice',0)}"]
    if b.get("error", 0):
        parts.append(f"error:{b['error']}")
    counts = " ".join(parts)
    print(f"\u2713 {total} deals \u2192 {counts} \u00b7 out/queue.html \u00b7 reports/eval_report.md")
