# DealSight — Iru Operations Engineer Work Sample

Abhishek Adavi

Parts 1, 2 and 4 below. Part 3 is the code in this repo — see `README.md` for how to run it.

---

## Part 1 — Diagnosis

### How I got there

I loaded both CSVs in pandas and worked from the data rather than the narrative. The steps, in order:

1. Reconciled every line item to its parent deal (`quantity × net_unit_price_usd × term_months/12`) and compared the sum to `contract_value`.
2. Recomputed every derived field on the deal rather than trusting it — blended discount, line totals, net unit prices.
3. Profiled the categorical fields (deal type, currency, billing frequency, payment terms) and the null pattern across `po_number`, `billing_contact_email`, `discount_approval`.
4. Read all nine `special_terms` notes individually and checked whether the instruction in each one agreed with the structured fields on the same deal.
5. Grouped customers by normalised name to look for the same company under different IDs, and fingerprinted deals on (customer, value, term, start date) to look for repeats.
6. Aged every deal from `close_date` and compared `term_start_date` to today.

The scripts that produce all of this are in `analysis/`.

### What the data says

**41 of 65 deals carry at least one defect. Only 24 could be invoiced today.** That is $1.95M of $5.88M moving cleanly, and $3.9M held up.

**Median age since close is 69 days** (P90 116, max 126). 36 deals are over 60 days old, holding $3.37M. Every deal in the file has a `term_start_date` in the past, so in every case the customer is already being served and the invoice hasn't gone out. The delay isn't a scheduling problem, it's pure DSO on revenue already earned.

### Frequent versus expensive

These are different problems and they need different treatments.

**Frequent and cheap — the chase loop.** 10 of the 23 PO-required deals have no PO number ($641K blocked). 5 deals have no billing contact. 3 more have a contact address with a typo'd domain (`ap@bluewatermarin.com` — one missing letter, and the invoice bounces silently). Individually each is a two-minute fix. Collectively they're the reason the queue never clears, because each one costs a Slack message and an unbounded wait.

**Rare and expensive — the ones that bill wrong.** Four deals carry co-termination instructions in `special_terms` — mid-term upgrades that should prorate to an existing subscription's period end rather than start a fresh 12-month term. Invoiced as recorded, they overbill by roughly $103K in total. DD-1004 is the clearest: $38,400 on the deal record, ~$13,457 once prorated to the period ending 2026-10-06.

Three deals are denominated EUR or GBP while `contract_value` equals the USD line-item sum to the cent — the currency label was changed and the numbers weren't. DD-1051 is "€375,400" against $375,400 of line items.

DD-1099 is an exact duplicate of DD-1023 — same customer, value, term, dates and owner. Invoice both and the customer is billed twice.

Northwind Labs appears under three customer IDs ("Northwind Labs Inc", "Northwind Labs, Inc.", "northwind labs") and Kestrel under two. Each variant becomes a separate Stripe customer with its own billing relationship.

Seven deals have a contract value that doesn't match their line items, from −12% to +15%, with nothing in the notes explaining why.

The pattern: the frequent defects delay revenue, the rare ones misbill it. The frequent ones are visible from the CSV headers. The rare ones only surface if you read the notes field against the structured fields, which is exactly what nobody has time to do at the invoicing step.

### The problem created furthest upstream

`blended_discount_pct` on the deal record is an unweighted mean of the line-item discounts. I verified this against all 64 deals that have line items — it matches the simple average, not the dollar-weighted one, in every case.

That field ignores line size. A large line at 40% off averaged with a small line at 0% reads as 20%, which is under the policy threshold. So the approval gate — "anything above 25% requires approval" — is reading a number that systematically understates the real discount.

The result: six deals carry line discounts up to 40% with no `discount_approval` on file, $567K in total. Three of them (DD-1003, DD-1026, DD-1055) show 25% or less in the field the policy is enforced against, while their true dollar-weighted discount is 29–32%.

This is the answer to "which problems are created upstream of the step where they surface." Nobody at the invoicing step did anything wrong. The violation was created by a rollup formula in the CRM at the moment the deal was built, passed a gate that was reading the wrong number, and will surface months later as a finance dispute or a revenue-recognition problem.

### What the data can't tell me

The files show that deals age 65 days, but not where the time goes inside those 65 days. There are no timestamps for when Operations picked a deal up, when a question went to the field, or when the answer came back. So "the rep round-trip is the largest single time sink" is a reasonable inference from the volume of missing-field defects, but it is an inference, not a measurement.

I've treated that as a finding rather than a gap to hand-wave: capturing those timestamps is part of what the build does, and it's what makes Part 4 answerable in ninety days.

---

## Part 2 — Proposal

### What I'd build first

**A validation gate that runs when the deal hits Closed Won, not when someone picks it up to invoice.**

Everything downstream of that moment is cleanup of defects that already exist. Moving the check to the moment of creation is the only intervention that shortens the queue and stops it refilling.

### What I considered instead, and why not

**A chaser bot for missing fields.** It's the most visible pain and the easiest build. But it only addresses the frequent-and-cheap category, and it makes the queue faster at doing work that shouldn't exist. The $103K overbilling exposure and the $567K discount-compliance problem would be completely untouched.

**A full HubSpot → Stripe automation.** Automating end to end would industrialise a process that produces a wrong or incomplete result 63% of the time. Automation before validation just misbills faster.

**A conversational interface over the deal data.** An operator clearing a queue doesn't want to interrogate deals; they want the answer already on screen. Anything a chat interface would be asked, the tool should have computed.

**Fixing HubSpot first.** Correct in the long run, and it's where the upstream report points. But it needs field changes, formula changes and a rollout with the sales org — weeks of change management. The gate delivers value immediately and produces the evidence that makes the HubSpot argument concrete rather than anecdotal.

### The design

```
HubSpot (Closed Won)
        │
        ▼
┌─────────────────────────────┐
│  15 deterministic rules     │  math integrity · discount policy (recomputed)
│  + special-terms parser     │  required fields · duplicates · currency
│  + reconciliation guard     │  parser output must tie to contract value
└─────────────────────────────┘
        │
        ▼
     triage
        │
   ┌────┴────┬──────────────┬──────────────────┐
   ▼         ▼              ▼                  ▼
 ready    needs rep    needs approval   do-not-auto-invoice
   │         │              │                  │
 Stripe   drafted       recomputed        evidence card
 payload   chase        discount +        (recorded vs
 built    message       approver          computed), human
   │                    request           decides
   ▼
 invoice
        │
        ▼
  append-only ledger  ──▶  upstream report (defects ranked by $ blocked)
```

Each bucket gets the work done for it, not just a label:

- **Ready** — subscription and invoice payloads generated, correct intervals and due dates, idempotent on re-run.
- **Needs rep** — a message drafted naming the exact missing item, the deal, the amount and the age.
- **Needs approval** — the real dollar-weighted discount computed and attached to an approval request.
- **Do-not-auto-invoice** — recorded amount and computed amount side by side, with the raw note quoted, for a human to approve.

The queue is sorted by dollars blocked × days aged, so the work order matches the money.

### What I would deliberately not automate

**Sending invoices for co-terms, ramps and currency conflicts.** The tool computes the prorated amount to the cent and still stops. The input is a parsed free-text note, and an invoice can't be un-sent. Automate the evidence, not the trigger.

**Merging duplicate customers.** Detection is automatic; the merge isn't. A wrong merge cross-bills two companies and corrupts records in both the CRM and the billing system — one of the few genuinely irreversible actions in this process.

**Granting discount approvals.** The tool computes the correct number and routes the request. Approving is an authority, not an arithmetic result.

**Acting on a low-confidence parse.** If the reconciliation guard can't tie the extracted amounts back to the contract value, the deal goes to a human with both readings shown. A model that guesses about money is worse than no model.

**Writing corrections back into the CRM.** The tool reports what's broken and what field or formula would prevent it. Silently patching source records would hide the cause and make the defect permanent.

The principle, in one line: **automate detection, computation and preparation; never automate irreversible actions, authority, or guesses.**

### Where the model is, and how I'd know it was wrong

Most `special_terms` notes are structured enough for a deterministic parser. Some are not. So there are two parsers behind one interface — regex by default, an LLM when it's available — and a reconciliation guard that both must pass: extracted co-term prorations and ramp schedules have to tie back to the deal's contract value within tolerance, or the parse is discarded and the deal is routed to a human.

That gives two independent signals on model correctness. Before deployment, both parsers are scored against a hand-labelled golden set of 29 cases — the 9 real notes, 15 adversarial paraphrases written to be hard for a pattern matcher but unambiguous to a person, and 5 notes with no billing meaning at all, to test that neither parser invents structure where there is none.

The results, field-exact (`reports/eval_report.md`):

| Parser | Score | Where it fails |
|---|---|---|
| Regex | 14/29 | Every adversarial case. It returns `none` rather than a wrong answer, so a note it can't read routes to a human instead of misbilling. |
| LLM | 19/29 | Recovers 7 of the 15 adversarial cases — all of them ramps. It gets the co-term *type* right every time but the fields wrong, which matters because co-terms are the category that overbills. |
| Guard | 5 catches | Including one live deal where the model produced a plausible parse that arithmetic rejected. |

Neither number is the one I'd manage to. The metric that matters is how often a wrong parse reaches a customer, and that is zero by construction: co-terms and ramps never auto-invoice, so a parser miss means a human reviews a deal a human was already going to review. Parser accuracy changes how much preparation work gets done, not whether anything breaks.

At runtime, the guard catches misparses the eval set didn't anticipate, because it checks against arithmetic rather than against expected text.

The system also runs offline with no model at all. The LLM improves coverage on awkward phrasing; it is never load-bearing.

---

## Part 4 — Measurement

### What I'd need to capture beforehand

Nothing in the current data makes the ninety-day question answerable, so the instrumentation is part of the build rather than something added afterwards. Every deal gets timestamps written to an append-only ledger:

- `closed_at` → `validated_at` (how fast the gate sees it)
- `validated_at` → `chased_at` (how fast a question reaches the field)
- `chased_at` → `resolved_at` (how long the field takes — the number nobody has today)
- `resolved_at` → `invoiced_at` (how fast a cleared deal converts)

Plus, per deal: which rules fired, which bucket it landed in, whether a human overrode the machine and why, and whether the invoice was later corrected or credited.

The pre-ship baseline has to be captured before the gate changes behaviour: current straight-through rate (24/65 = 37%), current median age (65 days), the current defect mix by dollars, and — from finance rather than the CRM — the count of credit memos and disputed invoices in the prior quarter.

### What I'd look at after ninety days

| Metric | Baseline | Target | Why it's falsifiable |
|---|---|---|---|
| Straight-through rate | 37% | 60%+ | Direct count, no interpretation |
| Median close → invoice, clean deals | 65 days | under 10 | Timestamped, not estimated |
| Median chase → resolution | unmeasured | establish, then reduce | The number the process has never had |
| Overbilled co-terms | ~$103K exposed | 0 | Any occurrence is a hard failure |
| Deals invoiced against unapproved discounts | 6 ($567K) | 0 | Binary |
| Top defect by dollars blocked | PO missing, $641K | different defect at the top | If the same defect leads after a CRM fix, the fix didn't work |
| Credit memos / disputes | from finance | down | Independent of the tool's own reporting |

### What would tell me it didn't work

I'd rather name the failure conditions than only the success ones:

- **Straight-through rate hasn't moved.** The gate is in the wrong place, or the defects are being created faster than they're being fixed upstream.
- **The upstream report's top defect is unchanged.** The evidence isn't translating into CRM changes, which means the reporting loop is decorative.
- **Human override rate on a rule is high.** That rule is wrong, not the deals — check the ledger's fire-versus-dismiss counts and retune or remove it.
- **Median age drops but credit memos rise.** The worst outcome: faster wrong invoices. This is why the do-not-auto-invoice bucket exists and why it must never be automated for speed.
- **Ready-bucket deals get corrected downstream.** The rules are passing things they shouldn't, and each case is a missing rule.

### One thing that isn't a metric

"Hours saved" isn't in the table. It isn't measurable here — the work was never time-tracked — and it's the kind of number that gets estimated into whatever shape the argument needs. Cycle time and defect counts are recorded facts; hours saved would be a story about them.

---

## AI usage

I used Claude for the data profiling in Part 1, for generating the DealSight codebase via Claude Code, and as a thinking partner on scope — including talking me out of things (a login screen, a chat interface, a knowledge graph) that would have added surface area without addressing the diagnosis.

Where I had to correct it:

**The golden dataset was circular.** The first version of the parser evaluation had the regex parser scoring 29 out of 29. That looked like a result until I realised the same session had written both the regex patterns and the synthetic test cases, so it was scoring itself against test data shaped to its own assumptions. I had the synthetic cases rewritten to be genuinely adversarial for a pattern matcher — paraphrased prorations with no keyword, spelled-out dates, ramp years split across clauses and out of order, amounts written as "$62.4k", subscription IDs without the expected prefix — with an explicit instruction not to modify the regex to pass them. The honest score matters more than the flattering one, and a benchmark that can't fail isn't a benchmark.

**The LLM call was sending the whole deal record.** The first implementation passed the full row to the model when only the free-text note was needed for the task. I changed it to send `special_terms` and nothing else — no customer names, no contact emails, no amounts, no identifiers — with the reconciliation against contract value happening locally. I work on clinical systems at a medical device company, where data minimisation on any external call is a habit rather than a preference, and the same reasoning applies to customer commercial data.

**The model asserted something the text didn't say, and my guard couldn't catch it.** On a real note reading only "Co-terminate with SUB-00287 ending 2025-12-31", the LLM returned `prorate: true`. That's a reasonable business convention, but the note never states it, and the difference changes the invoice. The reconciliation guard was blind to it: the guard validates amounts against contract value, and an unwarranted prorate flag still produces a plausible amount. So I tightened the extraction prompt to forbid inference and return null for anything the text doesn't address, and extended the guard to treat a null in any payload-critical field as a routing condition. The model now abstains on that case and the deal goes to a human. The score didn't improve — the failure mode changed from silent to visible, which was the point. A guard catches arithmetic errors; it does not catch inferential ones, and I'd rather know that about my own design than discover it in production.

**It scaffolded the project into my home directory.** Minor, but it's the class of thing that quietly breaks a submission: the repo root ended up as `~`, which meant relative paths worked by accident and the project couldn't be version-controlled cleanly. Caught it when the data files wouldn't land where the loader expected them.

**On the diagnosis itself.** I ran the profiling and reconciled the output against a second independent pass before trusting any of it — the defect counts in Part 1 were confirmed twice, from separate analyses, down to the deal IDs. The finding that mattered most (the unweighted discount rollup) came out of checking a derived field against its own inputs rather than out of a prompt, and it's the one thing here that a narrative reading of the brief would never have surfaced.

Where the design came from my own work: keeping the decision logic deterministic and letting the model only extract, guarding model output with arithmetic that can veto it, and keeping a human in front of anything irreversible — that's the pattern I've shipped on clinical document processing at Penumbra, where an approval decision has to be explainable to a governance committee. It transfers to billing more or less unchanged.

---

## Assumptions

The brief said ambiguity could be resolved by asking or by assuming and writing it down. I assumed, and recorded each one:

- **"Today" is the latest close date in the dataset.** Ages are computed from that, so the numbers are reproducible on any machine and don't drift.
- **Line-item unit prices are annual.** `quantity × net_unit_price × term_months/12` reconciles to `line_total_usd` on all 142 rows, so I treated it as the schema's intent rather than a coincidence.
- **The discount policy applies to the real dollar-weighted discount, not the stored field.** The stored field is the mechanism that's failing; enforcing against it would reproduce the bug.
- **Non-USD deals whose contract value exactly equals the USD line sum are mislabelled, not genuinely foreign-denominated.** An exact match to the cent is not a plausible exchange rate.
- **Duplicate deals mean one sale entered twice, not two real sales.** Flagged for a human either way — the tool never deletes.
- **Invoices are sent, not charged.** `collection_method: send_invoice` with due dates from payment terms, which matches B2B net-30 terms in the data rather than card-on-file billing.
