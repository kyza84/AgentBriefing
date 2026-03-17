# PILOT_RESULTS_V1_2_BASELINE_FREEZE_2026-03-17

## Scope
Execution report for V1.2 `B0` (baseline freeze).

Purpose:
1. Freeze objective baseline before V1.2 deep improvements.
2. Lock acceptance, negative, and repeatability reference metrics.
3. Define comparison targets for B2/B3/B4/B5.

## Baseline sources
- `pilot_runs/acceptance_v1_1_20260317_155513_results.json`
- `pilot_runs/a6_negative_validator_20260317_165847.json`
- `pilot_runs/a6_repeatability_20260317_163120.json`
- `pilot_runs/v12_phase1_ci_parser_20260317_184826.json`
- Snapshot artifact: `pilot_runs/v12_baseline_freeze_20260317_185644.json`

## Frozen acceptance baseline (`36` runs)
- success: `36/36`
- blocking: `0`
- critical: `0`
- avg quality: `1.00`
- median quality: `1.00`
- total issues: `0`
- scanner warnings: `0`
- dependency coverage (non-zero runs): `15/36` (`0.4167`)

## Frozen runtime baseline (from acceptance set)
- quick:
  - min `0.104s`
  - median `4.433s`
  - p95 `448.562s`
  - max `511.561s`
- balanced:
  - min `0.013s`
  - median `0.119s`
  - p95 `17.335s`
  - max `21.052s`
- strict:
  - min `0.013s`
  - median `0.112s`
  - p95 `16.327s`
  - max `19.571s`

## Frozen negative baseline
- scenarios: `5`
- passed: `5/5`
- critical operational major blocking checks: `3/3` (`entrypoint`, `ci map`, `test command`)

## Frozen repeatability baseline
- subset size: `6`
- stable quality: `6/6`
- stable issues: `6/6`
- stable blocking: `6/6`
- stable warnings: `6/6`

## Freeze targets for V1.2 phases
- `acceptance_blocking_runs = 0`
- `acceptance_critical_runs = 0`
- `acceptance_avg_quality >= 0.95`
- `negative_pass_rate = 1.0`
- `repeatability_stable_ratio = 1.0`

## Phase decision
- B0 status: `completed`.
- Baseline is frozen and can be used for controlled delta checks in B2-B5.
