# PILOT_RESULTS_V1_2_PHASE3_QUICK_GUARDRAILS_2026-03-17

## Scope
Execution report for V1.2 `B3` (quick-profile runtime guardrails).

Goals:
1. Cap quick-profile runtime spikes on large repos.
2. Keep output operationally safe when deep scan is sampled.
3. Preserve non-blocking behavior under controlled guardrail mode.

## Implemented guardrails
- Profile-level quick limits:
  - scan time budget
  - CI workflow cap
  - dependency source-file cap
  - per-file and total byte limits for dependency parsing
- Guardrail telemetry in `FactModel`:
  - `scan_guardrails.activated`
  - `scan_guardrails.reasons`
  - `scan_guardrails.skipped`
- Explicit uncertainty tracking when guardrails are active:
  - hypothesis: `h_scan_budget_001`
  - unknown: `u_scan_budget_001`
- Validator compatibility in guardrail mode:
  - CI map missing under tracked guardrail unknown no longer escalates to blocking major.

## Regression coverage added
In `tests/test_pipeline_smoke.py`:
1. `test_scanner_quick_guardrails_activate_on_ci_workflow_cap`
2. `test_scanner_quick_guardrails_skip_oversized_dependency_files`
3. `test_validator_phase4_allows_ci_missing_map_when_guardrail_unknown_is_tracked`

## Validation results
- Unit tests:
  - command: `PYTHONPATH=src python -m unittest discover -s tests -v`
  - result: `30/30` passed
- Quick runtime matrix on pilot workspace (`12` repos):
  - evidence: `pilot_runs/v12_phase3_quick_runtime_20260317_192720_results.json`
  - successful runs: `12/12`
  - blocking runs: `0`
  - guardrail-activated runs: `5/12`

## Runtime delta vs frozen baseline (B0)
- quick median:
  - baseline: `4.433s`
  - after B3: `0.513s`
- quick p95:
  - baseline: `448.562s`
  - after B3: `13.767s`
- quick max:
  - baseline: `511.561s`
  - after B3: `15.96s`

## Heavy-repo examples
- `MX-01`:
  - baseline quick: `511.561s`
  - after B3: `15.96s`
  - guardrail reasons: `repo_file_soft_limit_exceeded`, `dependency_file_cap`, `time_budget_exceeded_dependency_scan`
- `ND-03`:
  - baseline quick: `397.018s`
  - after B3: `11.972s`
  - guardrail reasons include CI time-budget cutoff + dependency caps
  - blocking remained `false` due tracked guardrail uncertainty

## Phase decision
- B3 status: `completed`.
- Ready to proceed to B4 (validator recall expansion) with B0/B3 runtime baseline locked.
