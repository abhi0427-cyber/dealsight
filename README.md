# DealSight

Gate Closed Won deals before they become Stripe invoices. Deterministic rules engine that catches contract-value mismatches, missing fields, discount policy violations, duplicate deals, and billing edge cases — then triages each deal into an actionable queue.

## Quickstart

```bash
git clone <repo>
cd dealsight-project
./run.sh
```

No API key or internet connection is required — the pipeline runs fully offline with bundled data.

Expected output:

```
✓ 65 deals → ready:24 needs_rep:15 needs_approval:6 do_not_auto_invoice:20 · out/queue.html · reports/eval_report.md
```

### Manual setup (alternative)

If you prefer to manage the virtual environment yourself:

```bash
# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m dealsight run

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m dealsight run
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `python -m dealsight run` | Full pipeline — rules, triage, payloads, chase, report |
| `python -m dealsight run --watch` | Re-run on CSV change (polls every 5s) |
| `python -m dealsight approve DD-1048` | Human override → ready, regenerate payload |
| `python -m dealsight dismiss DD-1048 --reason "..."` | Dismiss a finding |
| `python -m dealsight correct DD-1058 --coterm-end 2025-10-01` | Record correction |
| `python -m dealsight eval` | Score parsers against golden.json |
| `python -m dealsight stats` | Per-rule fire/dismiss counts (precision signal) |

## Optional: LLM Parser

Set `ANTHROPIC_API_KEY` to enable the Claude-backed special-terms parser. Without it, the regex parser handles all parsing offline.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m dealsight run
```

The LLM parser uses raw HTTPS (`urllib`) to call the Anthropic Messages API — no SDK dependency. Both parsers are scored against `golden/golden.json` during eval.

## Mock Boundaries

This tool runs fully offline with mock integrations:

| Real System | Mock |
|-------------|------|
| Stripe API | `MockStripe` → writes JSON to `out/stripe_requests/` |
| Slack | Chase messages → `out/outbox/*.txt` |
| State DB | `out/state.json` (content-hash idempotency) |
| Audit log | `out/ledger.jsonl` (append-only) |

**To go live:** swap `MockStripe` for the `stripe` SDK; replace outbox writes with a Slack webhook POST.

## Repo Map

```
dealsight/
  __main__.py          # CLI entry point
  run.py               # Main pipeline
  loader.py            # CSV loading
  triage.py            # Bucket assignment
  stripe_payload.py    # Stripe payload builder + MockStripe
  chase.py             # Draft Slack messages for needs_rep
  ledger.py            # Append-only audit ledger
  report.py            # HTML report generator
  eval.py              # Parser evaluation against golden.json
  config.yaml          # All thresholds and severities
  rules/
    __init__.py         # Auto-discovery registry
    r01_cv_vs_lines.py  # Contract value vs line-item sum
    r02_line_math.py    # Per-line price × qty × term math
    r03_line_term.py    # Line term = deal term
    r04_weighted_discount.py  # Dollar-weighted discount >25%
    r05_max_line_discount.py  # Any line discount >25%
    r06_po_required.py  # PO required but missing
    r07_billing_contact.py    # Billing email missing
    r08_email_regex.py  # Email format validation
    r09_duplicate_deal.py     # Fingerprint dedup (customer+value+term+start)
    r10_fuzzy_customer.py     # Fuzzy name matching (difflib ≥0.85)
    r11_empty_deal.py   # $0 or no lines
    r12_currency_mismatch.py  # Non-USD with CV = USD line sum
    r13_date_sanity.py  # Date validation
    r14_billing_stripe.py     # Billing freq/terms → Stripe mapping
    r15_special_terms.py      # Co-term/ramp reconciliation
  parser/
    __init__.py         # Parser factory (regex or LLM)
    base.py             # BaseParser interface
    regex_parser.py     # Regex-based parser (default)
    llm_parser.py       # LLM parser (optional, needs API key)
    guard.py            # Reconciliation guard (runs on every parse)
data/
  deals.csv             # 65 Closed Won deals
  deal_line_items.csv   # 142 line items
golden/
  golden.json           # 29 eval cases (9 real + 15 synthetic + 5 negative)
tests/
  test_rules.py         # Every rule: happy + violation
  test_guard.py         # Guard accept/reject
  test_triage.py        # Bucket precedence
  test_idempotent.py    # Idempotent re-run
  test_smoke.py         # Full-run bucket count assertion
analysis/               # Placeholder for diagnosis scripts
```

## config.yaml

All rule severities (`block` or `warn`) and thresholds live in `config.yaml`, not code:

- `rules.<name>.severity` — `block` prevents invoicing; `warn` is informational
- `rules.weighted_discount.max_discount_pct` — discount threshold (default 25%)
- `rules.fuzzy_customer.similarity_threshold` — difflib ratio (default 0.85)
- `rules.duplicate_deal.close_date_window_days` — duplicate window (default 7)
- `rules.cv_vs_lines.tolerance_usd` — CV match tolerance (default $1)
- `bucket_map.<rule>` — which bucket a block-severity rule maps to

## Adding Rule 16

1. Create `dealsight/rules/r16_my_rule.py`
2. Import and use the `@register("my_rule")` decorator
3. Add config entry in `config.yaml` under `rules:` and `bucket_map:`
4. The registry auto-discovers it — no other wiring needed

## Triage Buckets

| Bucket | Meaning | Trigger Rules |
|--------|---------|---------------|
| `ready` | Zero block findings → generate Stripe payload | — |
| `needs_rep` | Missing PO, contact, or bad email | r06, r07, r08 |
| `needs_approval` | Discount >25% without approval | r04, r05 |
| `do_not_auto_invoice` | Structural issues requiring manual handling | r01, r02, r03, r09, r11, r12, r15 |
| `error` | Deal crashed during processing | Exception |

Priority within each bucket: `contract_value × days_since_close` (descending).
