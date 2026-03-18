# V1.1 Known Limits

## Purpose
Honest list of current V1.1 limits to avoid false confidence during rollout.

## Confirmed limits

1. Quick-profile runtime can spike on very large monorepos.
- Evidence: `MX-01/quick=511.561s`, `ND-03/quick=397.018s`, `MX-02/quick=189.067s` in `pilot_runs/acceptance_v1_1_20260317_155513_results.json`.
- Impact: first-run UX latency is high.
- Current mitigation: use `balanced`/`strict` for routine checks on huge repos.

2. Dependency map coverage is partial.
- Evidence: `module_dependency_map > 0` only in `15/36` runs.
- Repos with zero dependency map include `GO-01`, `GO-02`, `LD-01`, `LD-02`, `ND-01`, `PY-01`, `PY-03`.
- Impact: change blast-radius visibility is incomplete for some stacks/repo styles.

3. Stack detection can be unknown on repos without strong manifest signals.
- Evidence: `LD-02` appears with empty stack signal in acceptance matrix.
- Impact: downstream recommendations can be less specific.

4. CI trigger parsing is still heuristic (partial hardening applied).
- Current status: nested `workflow_dispatch.inputs.*` noise is filtered (covered by `tests/test_pipeline_smoke.py::test_scanner_ci_triggers_ignore_nested_workflow_dispatch_fields`).
- Remaining limitation: parser is line-based, not full YAML AST traversal; complex inline/map forms may still be incomplete.

5. Unknown count increased versus V1 baseline.
- Evidence: sum of unknowns changed from `36` to `60` across full matrix (`+24`).
- Rationale: intentional hypothesis-driven confirm/edit/reject flow.
- Impact: higher question volume in exchange for lower silent assumptions.

## Limits not observed in this cycle
- No blocking regressions in acceptance matrix (`blocking=0`).
- No critical issues in acceptance matrix (`critical=0`).
- No scanner warning regressions in acceptance matrix (`warnings delta=0`).
- Negative major scenarios now correctly block release (`pilot_runs/a6_negative_validator_20260317_165847.json`).
