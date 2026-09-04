"""Generate out/queue.html — ONE static self-contained file, zero external requests."""

import json
from pathlib import Path
from datetime import datetime


def _special_terms_row_label(evidence: dict) -> str:
    """Compute a specific row label for special-terms findings."""
    parse_r = evidence.get("parse_result", {})
    details = evidence.get("guard_result", {}).get("details", {})
    if parse_r.get("type") == "coterm":
        cv = details.get("cv", 0)
        prorated = details.get("expected_prorated", 0)
        if cv and prorated:
            delta = cv - prorated
            return f"Would overbill ${delta:,.0f} &mdash; needs proration"
        return "Co-term &mdash; needs proration"
    elif parse_r.get("type") == "ramp":
        return "Ramp schedule in notes"
    return "Special terms require manual review"


def generate_report(summary: dict) -> Path:
    """Generate the HTML report and return its path."""
    results = summary["results"]
    buckets = summary["buckets"]
    total = summary["total"]

    # Compute stats
    ready_val = sum(r["contract_value"] for r in results if r["bucket"] == "ready")
    blocked_val = sum(r["contract_value"] for r in results if r["bucket"] != "ready")
    total_val = ready_val + blocked_val

    ages = []
    now = datetime.now()
    for r in results:
        if r.get("close_date"):
            try:
                cd = datetime.strptime(r["close_date"], "%Y-%m-%d")
                ages.append((now - cd).days)
            except (ValueError, TypeError):
                pass
    median_age = sorted(ages)[len(ages) // 2] if ages else 0

    queue_deals = [r for r in results if r["bucket"] not in ("ready", "error")]
    ready_deals = [r for r in results if r["bucket"] == "ready"]

    # Build defect summary for upstream tab
    defect_codes: dict[str, dict] = {}
    for r in results:
        for code, severity, evidence in r.get("findings", []):
            if code not in defect_codes:
                defect_codes[code] = {"count": 0, "deals": set(), "total_value": 0}
            defect_codes[code]["count"] += 1
            defect_codes[code]["deals"].add(r["deal_id"])
            defect_codes[code]["total_value"] += r["contract_value"]
    # Sort by total value blocked
    sorted_defects = sorted(defect_codes.items(), key=lambda x: x[1]["total_value"], reverse=True)

    hubspot_fixes = {
        "cv_vs_lines": "Recalculate contract value to match line items",
        "line_math": "Fix line item pricing (check list price, discount, and quantity)",
        "line_term": "Align line item term with deal term",
        "weighted_discount": "Add discount approval or reduce discount below 25%",
        "max_line_discount": "Add discount approval or reduce line discount below 25%",
        "po_required": "Add PO number to deal record",
        "billing_contact": "Add billing contact email to deal",
        "email_regex": "Fix billing contact email format",
        "duplicate_deal": "Close the duplicate deal",
        "fuzzy_customer": "Merge duplicate customer records",
        "empty_deal": "Add line items or close the $0 deal",
        "currency_mismatch": "Set correct currency or convert contract value",
        "date_sanity": "Fix deal dates (term_start should be on or after close_date)",
        "billing_stripe": "Set valid billing frequency and payment terms",
        "special_terms": "Review special terms — may need manual invoicing",
    }

    problem_colors = {
        "cv_vs_lines": "#dc3545", "line_math": "#dc3545", "line_term": "#dc3545",
        "currency_mismatch": "#dc3545", "empty_deal": "#dc3545",
        "po_required": "#f59e0b", "billing_contact": "#f59e0b", "email_regex": "#f59e0b",
        "date_sanity": "#f59e0b", "billing_stripe": "#f59e0b",
        "weighted_discount": "#7F77DD", "max_line_discount": "#7F77DD",
        "duplicate_deal": "#dc3545", "fuzzy_customer": "#f59e0b",
        "special_terms": "#dc3545",
    }

    problem_labels = {
        "cv_vs_lines": "Contract value doesn't match line items",
        "line_math": "Line item math error",
        "line_term": "Line term doesn't match deal term",
        "weighted_discount": "Discount exceeds 25% — needs approval",
        "max_line_discount": "Line discount exceeds 25% — needs approval",
        "po_required": "PO number required but missing",
        "billing_contact": "Billing contact email missing",
        "email_regex": "Billing email format invalid",
        "duplicate_deal": "Possible duplicate deal",
        "fuzzy_customer": "Similar customer name found under different ID",
        "empty_deal": "Empty deal ($0 or no line items)",
        "currency_mismatch": "Currency mismatch — likely missing FX conversion",
        "date_sanity": "Date issue detected",
        "billing_stripe": "Billing config not Stripe-compatible",
        "special_terms": "Special terms require manual review",
    }

    def deal_row_html(r: dict, expanded_content: str = "") -> str:
        deal_id = r["deal_id"]
        customer = r["customer_name"]
        owner = r["owner"]
        cv = r["contract_value"]
        age = ""
        if r.get("close_date"):
            try:
                cd = datetime.strptime(r["close_date"], "%Y-%m-%d")
                age = f"{(now - cd).days}d"
            except (ValueError, TypeError):
                pass

        problems_html = ""
        for code, severity, evidence in r.get("findings", []):
            if severity == "warn":
                continue
            color = problem_colors.get(code, "#6b7280")
            if code == "special_terms":
                label = _special_terms_row_label(evidence)
            else:
                label = problem_labels.get(code, code)
            problems_html += f'<span style="color:{color};font-size:13px">{label}</span><br>'

        if not problems_html and r["bucket"] == "ready":
            problems_html = '<span style="color:#10b981;font-size:13px">Ready for invoicing</span>'

        evidence_html = _evidence_card(r) if expanded_content == "" else expanded_content

        return f'''
        <div class="deal-row" onclick="this.querySelector('.evidence').classList.toggle('show')">
          <div style="display:grid;grid-template-columns:1fr 2fr auto 30px;align-items:center;padding:16px 20px;cursor:pointer">
            <div>
              <div style="font-weight:600;font-size:15px">{customer}</div>
              <div style="color:#6b7280;font-size:13px">{deal_id} &middot; {owner} &middot; {age}</div>
            </div>
            <div>{problems_html}</div>
            <div style="font-family:'SF Mono',ui-monospace,monospace;font-size:15px;font-variant-numeric:tabular-nums;text-align:right;font-weight:500">${cv:,.2f}</div>
            <div style="text-align:center;color:#9ca3af;font-size:18px">&rsaquo;</div>
          </div>
          <div class="evidence">{evidence_html}</div>
        </div>'''

    def _evidence_card(r: dict) -> str:
        parts = []
        for code, severity, evidence in r.get("findings", []):
            if code == "currency_mismatch":
                parts.append(f'<p><strong>Currency:</strong> Deal is {evidence.get("currency","?")} but contract value ({evidence.get("contract_value","?")}) exactly equals USD line sum — likely missing FX conversion.</p>')
            elif code == "special_terms":
                parse_r = evidence.get("parse_result", {})
                guard_r = evidence.get("guard_result", {})
                details = guard_r.get("details", {})
                raw = evidence.get("raw_text", "")
                if parse_r.get("type") == "coterm":
                    cv = details.get("cv", 0)
                    prorated = details.get("expected_prorated", 0)
                    days = details.get("days", 0)
                    months = days / 30.4375 if days else 0
                    coterm_end = parse_r.get("coterm_end", "?")
                    delta = cv - prorated
                    parts.append(
                        f'<div style="margin-bottom:6px">'
                        f'<strong>Co-term:</strong> {parse_r.get("sub_id", "")} &rarr; {coterm_end}'
                        f'</div>'
                        f'<div style="margin-bottom:4px">'
                        f'<s style="color:#9ca3af">Recorded: ${cv:,.2f}</s>'
                        f'</div>'
                        f'<div style="margin-bottom:4px">'
                        f'<span style="color:#10b981;font-weight:500">Computed prorated: ${prorated:,.2f}</span>'
                        f' <span style="color:#6b7280;font-size:13px">({months:.1f} months to {coterm_end})</span>'
                        f'</div>'
                        f'<div style="margin-bottom:8px;color:#dc3545;font-weight:500">'
                        f'Would overbill by ${delta:,.0f} if invoiced as recorded'
                        f'</div>'
                    )
                    parts.append(f'<blockquote style="border-left:3px solid #d1d5db;margin:8px 0;padding:4px 12px;color:#6b7280;font-size:13px">{raw}</blockquote>')
                elif parse_r.get("type") == "ramp":
                    ramp = parse_r.get("ramp", [])
                    ramp_sum = details.get("ramp_sum", sum(y.get("amount", 0) for y in ramp))
                    cv = details.get("cv", 0)
                    ramp_lines = ''.join(
                        f'<div style="margin-left:16px;margin-bottom:2px;font-size:14px">'
                        f'Year {y["year"]}: <span style="font-weight:500">${y["amount"]:,.2f}</span></div>'
                        for y in ramp
                    )
                    match_color = "#10b981" if abs(ramp_sum - cv) < 0.01 else "#dc3545"
                    parts.append(
                        f'<div style="margin-bottom:6px"><strong>Ramp schedule:</strong></div>'
                        f'{ramp_lines}'
                        f'<div style="margin-top:6px;font-weight:500">'
                        f'Sum: ${ramp_sum:,.2f} vs Contract value: '
                        f'<span style="color:{match_color}">${cv:,.2f}</span></div>'
                    )
                    parts.append(f'<blockquote style="border-left:3px solid #d1d5db;margin:8px 0;padding:4px 12px;color:#6b7280;font-size:13px">{raw}</blockquote>')
                if not guard_r.get("pass"):
                    parts.append(f'<p style="color:#dc3545">Guard: {guard_r.get("reason","")}</p>')
            elif code == "weighted_discount":
                parts.append(f'<p><strong>Discount:</strong> Field shows {evidence.get("reported_discount_pct",0):.1f}% but dollar-weighted recomputation = {evidence.get("recomputed_discount_pct",0):.1f}% (threshold: {evidence.get("threshold_pct",25)}%)</p>')
            elif code == "cv_vs_lines":
                parts.append(f'<p><strong>Contract value mismatch:</strong> CV ${evidence.get("contract_value",0):,.2f} vs line sum ${evidence.get("line_sum",0):,.2f} (diff: ${evidence.get("difference",0):,.2f})</p>')
            elif code == "duplicate_deal":
                parts.append(f'<p><strong>Duplicate:</strong> Matches {evidence.get("duplicate_of",[])}</p>')
            elif code == "empty_deal":
                parts.append(f'<p><strong>Empty deal:</strong> CV=${evidence.get("contract_value",0):,.2f}, {evidence.get("line_count",0)} line items</p>')
            elif code in ("po_required", "billing_contact", "email_regex"):
                parts.append(f'<p>{problem_labels.get(code, code)}</p>')

        if r["bucket"] == "ready":
            # Show payload JSON
            stripe_path = Path(f"out/stripe_requests/{r['deal_id']}.json")
            if stripe_path.exists():
                payload = stripe_path.read_text()
                parts.append(f'<p><strong>Stripe Payload:</strong></p><pre style="background:#f3f4f6;padding:12px;border-radius:6px;font-size:12px;overflow-x:auto">{payload}</pre>')
                parts.append('<p style="color:#10b981;font-weight:500">Create in Stripe</p>')

        # Add chase text for needs_rep
        if r["bucket"] == "needs_rep":
            chase_path = Path(f"out/outbox/{r['deal_id']}.txt")
            if chase_path.exists():
                chase_text = chase_path.read_text().replace("<", "&lt;").replace(">", "&gt;")
                parts.append(f'<p><strong>Drafted chase message:</strong></p><pre style="background:#fefce8;padding:12px;border-radius:6px;font-size:12px">{chase_text}</pre>')

        return '<div style="background:#fafafa;border-radius:10px;padding:16px 20px;margin:0 20px 16px">' + ''.join(parts) + '</div>' if parts else ''

    # Build upstream defect rows
    upstream_html = ""
    if sorted_defects:
        max_val = sorted_defects[0][1]["total_value"] if sorted_defects else 1
        for code, info in sorted_defects:
            bar_w = max(int(info["total_value"] / max_val * 100), 2) if max_val > 0 else 2
            fix = hubspot_fixes.get(code, "Review and fix in CRM")
            upstream_html += f'''
            <div style="padding:12px 20px;border-bottom:1px solid #f3f4f6">
              <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span style="font-weight:500;font-size:14px">{code}</span>
                <span style="color:#6b7280;font-size:13px">{len(info["deals"])} deals &middot; ${info["total_value"]:,.0f} blocked</span>
              </div>
              <div style="background:#f3f4f6;border-radius:4px;height:6px;margin-bottom:6px">
                <div style="background:{problem_colors.get(code,"#6b7280")};border-radius:4px;height:6px;width:{bar_w}%"></div>
              </div>
              <div style="color:#6b7280;font-size:12px">{fix}</div>
            </div>'''

    queue_count = len(queue_deals)
    ready_count = len(ready_deals)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DealSight</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,Inter,system-ui,sans-serif; background:#fff; color:#111827; line-height:1.5; }}
  .header {{ padding:20px 32px; border-bottom:1px solid #e5e7eb; display:flex; align-items:center; gap:12px; }}
  .mark {{ width:16px; height:16px; border-radius:3px; display:flex; flex-direction:column; overflow:hidden; }}
  .mark div {{ flex:1; }}
  .hero {{ padding:40px 32px 32px; }}
  .hero h1 {{ font-size:28px; font-weight:700; color:#111827; margin-bottom:4px; }}
  .hero .subtitle {{ font-size:15px; color:#6b7280; }}
  .stats {{ display:flex; gap:32px; margin-top:20px; }}
  .stat-val {{ font-size:22px; font-weight:600; font-variant-numeric:tabular-nums; }}
  .stat-label {{ font-size:13px; color:#6b7280; }}
  .tabs {{ display:flex; gap:0; padding:0 32px; border-bottom:1px solid #e5e7eb; }}
  .tab {{ padding:12px 20px; font-size:14px; font-weight:500; color:#6b7280; cursor:pointer; border-bottom:2px solid transparent; }}
  .tab.active {{ color:#111827; border-bottom-color:#111827; }}
  .tab-content {{ display:none; }}
  .tab-content.active {{ display:block; }}
  .deal-row {{ border-bottom:1px solid #f3f4f6; }}
  .deal-row:hover {{ background:#fafafa; }}
  .evidence {{ display:none; }}
  .evidence.show {{ display:block; }}
</style>
</head>
<body>
<div class="header">
  <div class="mark">
    <div style="background:#7F77DD"></div>
    <div style="background:#5DCAA5"></div>
    <div style="background:#EF9F27"></div>
  </div>
  <span style="font-weight:600;font-size:16px">DealSight</span>
</div>

<div class="hero">
  <h1>Waiting to be invoiced</h1>
  <div class="subtitle">{total} deals processed &middot; {datetime.now().strftime("%b %d, %Y %H:%M")}</div>
  <div class="stats">
    <div><div class="stat-val">${total_val:,.0f}</div><div class="stat-label">Total pipeline</div></div>
    <div><div class="stat-val" style="color:#10b981">${ready_val:,.0f}</div><div class="stat-label">Ready to invoice</div></div>
    <div><div class="stat-val" style="color:#dc3545">${blocked_val:,.0f}</div><div class="stat-label">Blocked</div></div>
    <div><div class="stat-val">{median_age}d</div><div class="stat-label">Median age</div></div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('queue')">Queue &middot; {queue_count}</div>
  <div class="tab" onclick="switchTab('ready')">Ready &middot; {ready_count}</div>
  <div class="tab" onclick="switchTab('upstream')">Upstream</div>
</div>

<div id="tab-queue" class="tab-content active">
  {''.join(deal_row_html(r) for r in queue_deals)}
</div>

<div id="tab-ready" class="tab-content">
  {''.join(deal_row_html(r) for r in ready_deals)}
</div>

<div id="tab-upstream" class="tab-content">
  {upstream_html}
</div>

<script>
function switchTab(name) {{
  document.querySelectorAll('.tab').forEach((t, i) => {{
    const tabs = ['queue','ready','upstream'];
    t.classList.toggle('active', tabs[i] === name);
  }});
  document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
}}
</script>
</body>
</html>'''

    out_path = Path("out/queue.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path
