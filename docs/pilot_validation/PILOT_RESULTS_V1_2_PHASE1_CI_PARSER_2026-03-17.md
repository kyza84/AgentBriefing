# PILOT_RESULTS_V1_2_PHASE1_CI_PARSER_2026-03-17

## Scope
Execution report for V1.2 `B1` (CI parser hardening).

Goals of this phase:
1. Replace trigger extraction heuristics with structured parsing for `on` block.
2. Extract event-level trigger filters (`branches`, `paths`, `types`, etc.).
3. Improve job extraction and pipeline critical step detection.

## Implemented changes
- Added `trigger_filters` to `CiPipelineFact` contract.
- Reworked scanner CI parsing flow in `ScannerEngine`:
  - structured parse of `on` for:
    - scalar form (`on: push`)
    - list form (`on: [push, pull_request]`)
    - inline map form (`on: {push: {...}, pull_request: {...}}`)
    - block form with nested filters and lists
  - separation of:
    - event names (`triggers`)
    - event filter constraints (`trigger_filters`)
  - structured `jobs` extraction via `jobs:` root block
  - job-level critical step extraction (`run:`/`uses:` with deploy/release hints)

## Regression coverage added
In `tests/test_pipeline_smoke.py`:
1. `test_scanner_ci_triggers_ignore_nested_workflow_dispatch_fields`
2. `test_scanner_ci_parses_inline_map_events_and_filters`
3. `test_scanner_ci_parses_block_filters_and_critical_job_steps`

## Validation results
- Unit test suite:
  - command: `PYTHONPATH=src python -m unittest discover -s tests -v`
  - result: `24/24` passed
- Heavy repo spot-check:
  - repo: `repos_lab/complex_awx`
  - evidence: `pilot_runs/v12_phase1_ci_parser_20260317_184826.json`
  - key check: `.github/workflows/promote.yml`
    - triggers extracted: `release`, `workflow_dispatch`
    - filter extracted: `release -> types=published`
    - noisy pseudo-triggers (`description`, `required`, `tag_name`) absent

## Phase decision
- B1 status: `completed`.
- Ready to proceed to B2 (dependency mapper depth) after B0 baseline freeze decision.
