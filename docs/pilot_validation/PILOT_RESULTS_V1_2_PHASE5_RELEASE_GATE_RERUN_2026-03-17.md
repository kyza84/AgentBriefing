# PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_RERUN_2026-03-17

## Scope
Re-run of V1.2 `B5` release gate after stabilizing scanner guardrail behavior.

Applied stabilization before rerun:
1. Deterministic file walk order (sorted directories/files in scanner walk).
2. Time-budget grace window for guardrail boundary checks to reduce warning flaps near threshold.

Evidence:
- `pilot_runs/v12_b5_release_r2_20260317_210650_results.json`
- `pilot_runs/v12_b5_repeat_r2_20260317_210650.json`
- `pilot_runs/v12_b5_repeat_check_r2_20260317_210650.json`

## Acceptance summary (36 runs)
- `total_runs`: `36`
- `success_runs`: `36`
- `blocking_runs`: `0`
- `critical_runs`: `0`
- `warning_runs`: `11`
- `avg_quality`: `0.984`
- `median_quality`: `1.0`
- `min_quality`: `0.87`
- `total_issues`: `20` (`17` runs with issues)

### Runtime profile
- aggregate:
  - `median_time`: `0.095s`
  - `p95_time`: `32.912s`
- per profile:
  - `quick`: `min/median/p95/max = 0.015s / 0.128s / 5.297s / 5.697s`
  - `balanced`: `min/median/p95/max = 0.012s / 0.081s / 28.587s / 28.618s`
  - `strict`: `min/median/p95/max = 0.019s / 0.112s / 45.793s / 45.807s`

### Operational extraction delta
- dependency non-zero runs:
  - current rerun: `24/36` (`0.6667`)
  - previous B5 run: `21/36` (`0.5833`)

## Issue distribution (acceptance)
- `scanner_warnings_present`: `11`
- `test_command_gap_tracked_as_unknown`: `6`
- `entrypoint_fallback_with_open_test_gap`: `3`

Notes:
- `ci_pipeline_map_sampled_due_guardrail` did not appear in this rerun.
- All observed issue IDs are non-blocking under current policy.

## Repeatability summary
- Primary repeat run (`v12_b5_repeat_r2_20260317_210650`):
  - `stable_quality_runs`: `6/6`
  - `stable_issue_runs`: `6/6`
  - `stable_blocking_runs`: `6/6`
  - `stable_warning_runs`: `6/6`
- Control repeat run (`v12_b5_repeat_check_r2_20260317_210650`):
  - `stable_quality_runs`: `6/6`
  - `stable_issue_runs`: `6/6`
  - `stable_blocking_runs`: `6/6`
  - `stable_warning_runs`: `6/6`

ND-02 (`quick`/`balanced`) remained stable in both repeat runs (no warning or dependency-map drift versus release baseline of this rerun).

## Gate decision
- Hard release safety gates: `PASS`
  - `blocking_runs=0`
  - `critical_runs=0`
  - no runtime crash in matrix
- Strict repeatability target (`stable_* = 6/6`): `PASS`

Decision: `GO` for V1.2 release freeze from B5 perspective.

## Follow-up (non-blocking)
1. Keep monitoring guardrail warning distribution on larger repos.
2. Track whether additional deterministic ordering is needed in other scan stages.
