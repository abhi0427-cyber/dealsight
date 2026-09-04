# DealSight Parser Evaluation Report

**Cases:** 29 | **Regex accuracy:** 14/29 (48%) | **LLM accuracy:** 19/29 (66%)

**Guard catches:** 5


## Per-case results

| ID | Origin | Expected | Regex | Regex Match | LLM | LLM Match | Guard |
|---|---|---|---|---|---|---|---|
| G-001 | real | coterm | coterm | pass | coterm | pass | - |
| G-002 | real | coterm | coterm | pass | coterm | FAIL | - |
| G-003 | real | coterm | coterm | pass | coterm | pass | - |
| G-004 | real | ramp | ramp | pass | ramp | pass | - |
| G-005 | real | ramp | ramp | pass | ramp | pass | - |
| G-006 | real | coterm | coterm | pass | coterm | FAIL | caught |
| G-007 | real | ramp | ramp | pass | ramp | pass | - |
| G-008 | real | none | none | pass | none | pass | - |
| G-009 | real | none | none | pass | none | pass | - |
| G-010 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-011 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-012 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-013 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-014 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-015 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-016 | synthetic | coterm | none | FAIL | coterm | FAIL | - |
| G-017 | synthetic | ramp | none | FAIL | ramp | pass | - |
| G-018 | synthetic | ramp | none | FAIL | ramp | pass | - |
| G-019 | synthetic | ramp | none | FAIL | ramp | FAIL | caught |
| G-020 | synthetic | ramp | none | FAIL | ramp | pass | caught |
| G-021 | synthetic | ramp | none | FAIL | ramp | pass | - |
| G-022 | synthetic | ramp | none | FAIL | ramp | pass | caught |
| G-023 | synthetic | ramp | none | FAIL | ramp | pass | caught |
| G-024 | synthetic | ramp | none | FAIL | ramp | pass | - |
| G-025 | negative | none | none | pass | none | pass | - |
| G-026 | negative | none | none | pass | none | pass | - |
| G-027 | negative | none | none | pass | none | pass | - |
| G-028 | negative | none | none | pass | none | pass | - |
| G-029 | negative | none | none | pass | none | pass | - |
