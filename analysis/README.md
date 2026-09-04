# analysis/

Exploratory scripts that produced the Part 1 diagnosis numbers. Each is standalone, uses only pandas, and prints its findings to stdout. Read-only on `data/`; no imports from `dealsight/`.

| Script | What it checks |
|--------|---------------|
| `01_profile.py` | Shape, dtypes, null counts, categorical value counts, special_terms notes |
| `02_reconcile.py` | Contract value vs line-item sums; line math verification (qty × price × term/12) |
| `03_discount.py` | Unweighted vs dollar-weighted discount; deals hiding >25% true discount |
| `04_duplicates.py` | Fuzzy customer name pairs; deal fingerprint duplicates |
| `05_aging.py` | Days-since-close distribution; stale deals >60 days; past-due term starts |

Example:

```bash
python analysis/03_discount.py
```
