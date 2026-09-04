"""CLI entry point: python -m dealsight <cmd>."""

import argparse
import json
import sys
import time
import os
from datetime import datetime, timezone
from pathlib import Path

from dealsight.run import run_pipeline, print_summary, load_config
from dealsight.report import generate_report
from dealsight.loader import validate as validate_schema
from dealsight import ledger


def cmd_validate(args):
    """Validate CSV schemas and exit."""
    validate_schema()
    print("Schema OK — all required columns present.")


def cmd_run(args):
    """Run full pipeline."""
    validate_schema()
    if args.validate_only:
        print("Schema OK — all required columns present.")
        return
    summary = run_pipeline()
    generate_report(summary)
    print_summary(summary)

    if args.watch:
        deals_path = Path("data/deals.csv")
        items_path = Path("data/deal_line_items.csv")
        prev_mtime = (deals_path.stat().st_mtime, items_path.stat().st_mtime)
        interval = 5
        print(f"Watching for changes every {interval}s... (Ctrl+C to stop)")
        try:
            while True:
                time.sleep(interval)
                cur_mtime = (deals_path.stat().st_mtime, items_path.stat().st_mtime)
                if cur_mtime != prev_mtime:
                    print(f"\nChanges detected at {datetime.now().strftime('%H:%M:%S')}, re-running...")
                    summary = run_pipeline()
                    generate_report(summary)
                    print_summary(summary)
                    prev_mtime = cur_mtime
        except KeyboardInterrupt:
            print("\nStopped watching.")


def cmd_approve(args):
    """Human override → ready."""
    config = load_config()
    deal_id = args.deal_id
    ledger.append(deal_id, "ready", [], actor="human",
                  extra={"action": "approve"})
    # Re-run to regenerate payload + HTML
    summary = run_pipeline()
    generate_report(summary)
    print(f"Approved {deal_id} → ready. Payload regenerated.")


def cmd_dismiss(args):
    """Dismiss a finding."""
    deal_id = args.deal_id
    reason = args.reason or "dismissed"
    ledger.append(deal_id, "dismissed", [], actor="human",
                  extra={"action": "dismiss", "reason": reason})
    print(f"Dismissed {deal_id}: {reason}")


def cmd_correct(args):
    """Append correction to corrections.jsonl."""
    deal_id = args.deal_id
    correction = {"deal_id": deal_id, "ts": datetime.now(timezone.utc).isoformat()}
    if args.coterm_end:
        correction["coterm_end"] = args.coterm_end
    if args.ramp:
        correction["ramp"] = args.ramp
    if args.note:
        correction["note"] = args.note

    corr_path = Path("out/corrections.jsonl")
    corr_path.parent.mkdir(parents=True, exist_ok=True)
    with open(corr_path, "a") as f:
        f.write(json.dumps(correction) + "\n")

    ledger.append(deal_id, "corrected", [], actor="human",
                  extra={"action": "correct", "correction": correction})
    print(f"Correction recorded for {deal_id}")


def cmd_eval(args):
    """Run eval against golden.json."""
    from dealsight.eval import run_eval
    run_eval()


def cmd_stats(args):
    """Aggregate ledger: per-rule fire/dismiss counts."""
    entries = ledger.read_all()
    rule_fires: dict[str, int] = {}
    rule_dismissals: dict[str, int] = {}

    for entry in entries:
        if entry.get("actor") == "engine":
            for code in entry.get("codes", []):
                rule_fires[code] = rule_fires.get(code, 0) + 1
        elif entry.get("action") == "dismiss":
            for code in entry.get("codes", []):
                rule_dismissals[code] = rule_dismissals.get(code, 0) + 1

    print("Rule fire counts (precision signal):")
    print(f"{'Rule':<25} {'Fires':>8} {'Dismissals':>12} {'Precision':>10}")
    print("-" * 58)
    all_codes = sorted(set(list(rule_fires.keys()) + list(rule_dismissals.keys())))
    for code in all_codes:
        fires = rule_fires.get(code, 0)
        dismissals = rule_dismissals.get(code, 0)
        precision = f"{(fires - dismissals) / fires * 100:.0f}%" if fires > 0 else "N/A"
        print(f"{code:<25} {fires:>8} {dismissals:>12} {precision:>10}")


def _load_dotenv():
    """Read .env file and set missing env vars. No external dependency."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def main():
    _load_dotenv()
    parser = argparse.ArgumentParser(prog="dealsight", description="DealSight — deal gating pipeline")
    sub = parser.add_subparsers(dest="command")

    # validate
    p_validate = sub.add_parser("validate", help="Check CSV schemas and exit")
    p_validate.set_defaults(func=cmd_validate)

    # run
    p_run = sub.add_parser("run", help="Run full pipeline")
    p_run.add_argument("--watch", action="store_true", help="Poll CSV mtime every 5s")
    p_run.add_argument("--validate-only", action="store_true",
                       help="Check CSV schemas and exit without processing")
    p_run.set_defaults(func=cmd_run)

    # approve
    p_approve = sub.add_parser("approve", help="Human override → ready")
    p_approve.add_argument("deal_id", help="Deal ID to approve")
    p_approve.set_defaults(func=cmd_approve)

    # dismiss
    p_dismiss = sub.add_parser("dismiss", help="Dismiss a finding")
    p_dismiss.add_argument("deal_id", help="Deal ID")
    p_dismiss.add_argument("--reason", help="Reason for dismissal")
    p_dismiss.set_defaults(func=cmd_dismiss)

    # correct
    p_correct = sub.add_parser("correct", help="Record a correction")
    p_correct.add_argument("deal_id", help="Deal ID")
    p_correct.add_argument("--coterm-end", help="Corrected coterm end date")
    p_correct.add_argument("--ramp", help="Corrected ramp JSON")
    p_correct.add_argument("--note", help="Free-text note")
    p_correct.set_defaults(func=cmd_correct)

    # eval
    p_eval = sub.add_parser("eval", help="Run eval against golden.json")
    p_eval.set_defaults(func=cmd_eval)

    # stats
    p_stats = sub.add_parser("stats", help="Aggregate ledger stats")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
