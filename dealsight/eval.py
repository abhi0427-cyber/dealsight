"""Eval — score parsers against golden.json, merge corrections, write report."""

import json
import os
from pathlib import Path
from dealsight.parser.regex_parser import RegexParser
from dealsight.parser.base import ParseResult


GOLDEN_PATH = Path("golden/golden.json")
CORRECTIONS_PATH = Path("out/corrections.jsonl")
REPORT_PATH = Path("reports/eval_report.md")


def _load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        return []
    return json.loads(GOLDEN_PATH.read_text())


def _load_corrections() -> list[dict]:
    if not CORRECTIONS_PATH.exists():
        return []
    entries = []
    with open(CORRECTIONS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _field_exact(expected: dict, actual: ParseResult) -> dict:
    """Compare fields exactly, return {field: match}."""
    results = {}
    for key in ("type", "sub_id", "coterm_end", "prorate"):
        exp = expected.get(key)
        act = actual.get(key)
        if exp is not None:
            results[key] = exp == act
    # Ramp comparison
    if "ramp" in expected and expected["ramp"]:
        exp_ramp = expected["ramp"]
        act_ramp = actual.get("ramp", [])
        if len(exp_ramp) == len(act_ramp):
            ramp_match = all(
                e.get("year") == a.get("year") and abs(e.get("amount", 0) - a.get("amount", 0)) < 0.01
                for e, a in zip(exp_ramp, act_ramp)
            )
        else:
            ramp_match = False
        results["ramp"] = ramp_match
    return results


def run_eval():
    """Run eval, write report."""
    cases = _load_golden()
    corrections = _load_corrections()

    # Merge corrections as extra cases
    for corr in corrections:
        cases.append({
            "id": f"corr-{corr['deal_id']}",
            "origin": "correction",
            "text": corr.get("note", ""),
            "expected": {
                "type": corr.get("type", "none"),
                "coterm_end": corr.get("coterm_end"),
                "ramp": corr.get("ramp"),
            },
        })

    if not cases:
        print("No golden cases found.")
        return

    config = {}
    regex_parser = RegexParser(config)

    # LLM parser: check key availability
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    llm_parser = None
    if has_key:
        from dealsight.parser.llm_parser import LLMParser
        llm_parser = LLMParser(config)
    else:
        print("LLM: not run (no ANTHROPIC_API_KEY)")

    import pandas as pd
    from dealsight.parser.guard import reconcile

    results = []
    regex_correct = 0
    llm_correct = 0
    llm_errors = 0
    total = len(cases)
    guard_catches = 0

    for case in cases:
        text = case.get("text", "")
        expected = case.get("expected", {})
        deal = pd.Series({"deal_id": case["id"], "contract_value_usd": 0, "term_months": 12,
                          "term_start": "2025-07-01", "special_terms": text})

        # --- Regex ---
        regex_result = regex_parser.parse(text, deal)
        regex_fields = _field_exact(expected, regex_result)
        regex_all_match = all(regex_fields.values()) if regex_fields else True
        if regex_all_match:
            regex_correct += 1

        # --- LLM ---
        llm_result = None
        llm_all_match = False
        llm_status = "skip"  # skip | pass | FAIL | error
        if llm_parser:
            try:
                llm_result = llm_parser.parse(text, deal)
                llm_fields = _field_exact(expected, llm_result)
                llm_all_match = all(llm_fields.values()) if llm_fields else True
                if llm_all_match:
                    llm_correct += 1
                    llm_status = "pass"
                else:
                    llm_status = "FAIL"
            except Exception as exc:
                print(f"  LLM error on {case['id']}: {exc}")
                llm_errors += 1
                llm_status = "error"

        # --- Guard (on regex result) ---
        guard_result = reconcile(regex_result, deal, pd.DataFrame())
        caught = not guard_result.get("pass", True)
        if caught:
            guard_catches += 1

        results.append({
            "id": case["id"],
            "origin": case.get("origin", "unknown"),
            "expected_type": expected.get("type", "?"),
            "regex_type": regex_result.get("type", "?"),
            "regex_match": "pass" if regex_all_match else "FAIL",
            "llm_type": (llm_result or {}).get("type", "-") if llm_parser else "-",
            "llm_match": llm_status,
            "guard_caught": "caught" if caught else "-",
        })

    # --- Write report ---
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    llm_label = f"{llm_correct}/{total} ({llm_correct/total*100:.0f}%)" if has_key else "not run"

    lines = [
        "# DealSight Parser Evaluation Report\n",
        f"**Cases:** {total} | **Regex accuracy:** {regex_correct}/{total} ({regex_correct/total*100:.0f}%)"
        f" | **LLM accuracy:** {llm_label}",
        f"\n**Guard catches:** {guard_catches}\n",
        "\n## Per-case results\n",
        "| ID | Origin | Expected | Regex | Regex Match | LLM | LLM Match | Guard |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        lines.append(
            f"| {r['id']} | {r['origin']} | {r['expected_type']} "
            f"| {r['regex_type']} | {r['regex_match']} "
            f"| {r['llm_type']} | {r['llm_match']} | {r['guard_caught']} |"
        )

    report_text = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report_text)

    # --- Console summary ---
    print(f"Eval report written to {REPORT_PATH}")
    llm_console = f"{llm_correct}/{total}" if has_key else "not run (no ANTHROPIC_API_KEY)"
    print(f"Regex: {regex_correct}/{total} \u00b7 LLM: {llm_console} \u00b7 Guard catches: {guard_catches}")
