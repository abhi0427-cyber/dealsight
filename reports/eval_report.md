# DealSight Parser Evaluation Report

**Cases:** 29 | **Regex accuracy:** 14/29 (48%) | **LLM accuracy:** not run

**Guard catches:** 5


## Per-case results

| ID | Origin | Expected | Regex | Regex Match | LLM | LLM Match | Guard |
|---|---|---|---|---|---|---|---|
| G-001 | real | coterm | coterm | pass | - | skip | - |
| G-002 | real | coterm | coterm | pass | - | skip | - |
| G-003 | real | coterm | coterm | pass | - | skip | - |
| G-004 | real | ramp | ramp | pass | - | skip | - |
| G-005 | real | ramp | ramp | pass | - | skip | - |
| G-006 | real | coterm | coterm | pass | - | skip | caught |
| G-007 | real | ramp | ramp | pass | - | skip | - |
| G-008 | real | none | none | pass | - | skip | - |
| G-009 | real | none | none | pass | - | skip | - |
| G-010 | synthetic | coterm | none | FAIL | - | skip | - |
| G-011 | synthetic | coterm | none | FAIL | - | skip | - |
| G-012 | synthetic | coterm | none | FAIL | - | skip | - |
| G-013 | synthetic | coterm | none | FAIL | - | skip | - |
| G-014 | synthetic | coterm | none | FAIL | - | skip | - |
| G-015 | synthetic | coterm | none | FAIL | - | skip | - |
| G-016 | synthetic | coterm | none | FAIL | - | skip | - |
| G-017 | synthetic | ramp | none | FAIL | - | skip | - |
| G-018 | synthetic | ramp | none | FAIL | - | skip | - |
| G-019 | synthetic | ramp | none | FAIL | - | skip | caught |
| G-020 | synthetic | ramp | none | FAIL | - | skip | caught |
| G-021 | synthetic | ramp | none | FAIL | - | skip | - |
| G-022 | synthetic | ramp | none | FAIL | - | skip | caught |
| G-023 | synthetic | ramp | none | FAIL | - | skip | caught |
| G-024 | synthetic | ramp | none | FAIL | - | skip | - |
| G-025 | negative | none | none | pass | - | skip | - |
| G-026 | negative | none | none | pass | - | skip | - |
| G-027 | negative | none | none | pass | - | skip | - |
| G-028 | negative | none | none | pass | - | skip | - |
| G-029 | negative | none | none | pass | - | skip | - |
