# PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_2026-03-17

> Historical snapshot: this report captured the first B5 run (`NO-GO` state).
> Updated post-fix rerun with final gate status is documented in
> `PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_RERUN_2026-03-17.md`.

## Scope
Execution report for V1.2 `B5` (acceptance + release gate) after B1-B4.

Runs executed:
1. Full acceptance matrix (`12 repos x 3 profiles = 36 runs`)
2. Repeatability subset run (`6 runs`)
3. Repeatability control rerun (`6 runs`)

Evidence:
- `pilot_runs/v12_b5_release_20260317_201853_results.json`
- `pilot_runs/v12_b5_repeat_20260317_201853.json`
- `pilot_runs/v12_b5_repeat_check_20260317_202744.json`

## Acceptance summary (36 runs)
- `total_runs`: `36`
- `success_runs`: `36`
- `blocking_runs`: `0`
- `critical_runs`: `0`
- `warning_runs`: `12`
- `avg_quality`: `0.982`
- `median_quality`: `0.995`
- `min_quality`: `0.87`
- `total_issues`: `23` (`18` runs with issues)

### Runtime profile (current vs B0 baseline)
- `quick`:
  - current median/p95/max: `3.831s / 40.92s / 59.92s`
  - B0 median/p95/max: `4.433s / 448.562s / 511.561s`
- `balanced`:
  - current median/p95/max: `0.087s / 28.032s / 28.059s`
  - B0 median/p95/max: `0.119s / 17.335s / 21.052s`
- `strict`:
  - current median/p95/max: `0.091s / 45.035s / 45.055s`
  - B0 median/p95/max: `0.112s / 16.327s / 19.571s`

### Operational extraction delta
- dependency non-zero runs:
  - current: `21/36` (`0.5833`)
  - B0: `15/36` (`0.4167`)

## Issue distribution (acceptance)
- `scanner_warnings_present`: `12`
- `test_command_gap_tracked_as_unknown`: `6`
- `entrypoint_fallback_with_open_test_gap`: `3`
- `ci_pipeline_map_sampled_due_guardrail`: `2`

Notes:
- All observed issue IDs are non-blocking in current policy.
- No new critical issue class was introduced by B5.

## Repeatability summary
- Primary repeat run (`v12_b5_repeat_20260317_201853`):
  - `stable_quality_runs`: `5/6`
  - `stable_issue_runs`: `5/6`
  - `stable_blocking_runs`: `6/6`
  - `stable_warning_runs`: `3/6`
- Control repeat run (`v12_b5_repeat_check_20260317_202744`):
  - `stable_quality_runs`: `5/6`
  - `stable_issue_runs`: `5/6`
  - `stable_blocking_runs`: `6/6`
  - `stable_warning_runs`: `4/6`

Observed drift is concentrated on `ND-02` (`quick/balanced`) where dependency scan guardrail time-budget warnings can appear/disappear between runs.

## Gate decision
- Hard release safety gates: `PASS`
  - `blocking_runs=0`
  - `critical_runs=0`
  - no runtime crash in matrix
- Strict repeatability target from baseline freeze (`stable_* = 6/6`): `NOT MET`

Decision: `NO-GO` for final V1.2 release freeze until repeatability drift is stabilized.

## Required follow-up before release
1. Stabilize scanner warning determinism for guardrail boundary cases (`ND-02` profile drift).
2. Re-run B5 acceptance + repeatability after fix.
3. Re-evaluate release gate with same artifacts schema.
