# PILOT_RESULTS_V1_2_PHASE4_VALIDATOR_RECALL_2026-03-17

## Scope
Execution report for V1.2 `B4` (validator recall expansion).

Goals:
1. Increase should-have-warned recall for CI/test/fallback-entrypoint risk combinations.
2. Keep new recall checks non-blocking by default to avoid false blocking spikes.
3. Preserve baseline unit-suite stability.

## Implemented validator additions
- New CI detail quality warnings:
  - `ci_pipeline_map_triggers_missing`
  - `ci_pipeline_map_jobs_missing`
- New tracked-gap warning for tests:
  - `test_command_gap_tracked_as_unknown`
- New combination warning:
  - `entrypoint_fallback_with_open_test_gap`

## Blocking policy impact
- Existing blocking-major set is intentionally unchanged:
  - `entrypoint_fallback_unconfirmed`
  - `ci_pipeline_map_missing`
  - `test_command_missing_without_unknown`
  - `operability_entrypoint_missing_without_unknown`
  - `operability_commands_missing_without_unknown`
- New B4 issue ids are non-blocking by design.

## Regression coverage added
In `tests/test_pipeline_smoke.py`:
1. `test_validator_phase4_warns_when_ci_pipeline_map_lacks_detail`
2. `test_validator_phase4_warns_when_test_gap_is_only_tracked_unknown`
3. `test_validator_phase4_warns_on_fallback_entrypoint_plus_open_test_gap`

## Validation results
- Unit tests:
  - command: `PYTHONPATH=src python -m unittest discover -s tests -v`
  - result: `33/33` passed
- Stage evidence:
  - `pilot_runs/v12_phase4_validator_recall_20260317_200330.json`

## Phase decision
- B4 status: `completed`.
- Ready to proceed to B5 (acceptance + release gate).
