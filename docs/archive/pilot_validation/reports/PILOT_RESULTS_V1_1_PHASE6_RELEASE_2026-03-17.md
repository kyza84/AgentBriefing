# PILOT_RESULTS_V1_1_PHASE6_RELEASE_2026-03-17

## Scope
Final release gate for V1.1 after A1-A5:
- Primary acceptance matrix: `pilot_runs/acceptance_v1_1_20260317_155513_results.json`
- Delta baseline: `pilot_runs/release_phase6_20260317_141558_results.json`
- Negative validator audit: `pilot_runs/a6_negative_validator_20260317_165847.json`
- Repeatability subset: `pilot_runs/a6_repeatability_20260317_163120.json`

## Gate checks

| Gate | Result | Evidence |
|---|---|---|
| Acceptance matrix (`12x3`) completed | PASS | `36/36` runs in `acceptance_v1_1_20260317_155513_results.json` |
| `blocking=0` | PASS | aggregate field `blocking_runs=0` |
| `critical=0` | PASS | aggregate field `critical_runs=0` |
| Quality regression vs V1 baseline | PASS | `avg_quality=1.00` unchanged |
| Issue regression vs V1 baseline | PASS | `total_issues=0`, delta `0` |
| Scanner warning regression | PASS | `total_scanner_warnings=0`, delta `0` |
| Negative scenarios detected by validator | PASS | `5/5` in `a6_negative_validator_20260317_165847.json` |
| Repeatability on subset | PASS | quality/issues/blocking/warnings stable `6/6` |

## Non-ideal validation (anti-perfect checks)
Purpose of this block: verify system is not silently over-optimistic.

Executed scenarios:
1. fallback/manual entrypoint without tracking -> expected `entrypoint_fallback_unconfirmed`.
2. CI signal without detailed map -> expected `ci_pipeline_map_missing`.
3. missing canonical test command without unknown -> expected `test_command_missing_without_unknown`.
4. overlap between resolved/open unknowns -> expected `unknown_resolution_overlap`.
5. healthy minimal case -> expected no forced major issue.

Result:
- `PASSED=5/5`.
- Validator emits expected issue IDs on broken cases and stays clean on healthy case.
- Operational major gaps are now blocking by policy (`blocking_status=true`) for cases 1-3.

## Repeatability snapshot
Subset rerun:
- `PY-01`: quick, balanced
- `ND-02`: quick, balanced
- `MX-02`: balanced, strict

Stability:
- quality stable `6/6`
- issues stable `6/6`
- blocking stable `6/6`
- warnings stable `6/6`

## Final release decision
- V1.1 release gate status: `PASS`.
- A6 outcome: improved baseline is frozen for use.
- Known limits and next backlog are documented:
  - `docs/V1_1_KNOWN_LIMITS.md`
  - `docs/V1_2_BACKLOG.md`
