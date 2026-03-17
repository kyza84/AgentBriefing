# V1.2 Backlog (Post V1.1 Release)

## Priority P0
1. CI workflow parser hardening.
- Status: completed in V1.2 B1 (`2026-03-17`).
- Result: structured event/filter/job parsing shipped with regression coverage.
- Evidence:
  - `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE1_CI_PARSER_2026-03-17.md`
  - `pilot_runs/v12_phase1_ci_parser_20260317_184826.json`

2. Dependency extraction depth.
- Status: completed in V1.2 B2 (`2026-03-17`).
- Result: dependency resolver upgraded for Go module paths, Python package roots, and TS aliases.
- Evidence:
  - `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE2_DEPENDENCY_MAPPER_2026-03-17.md`
  - `pilot_runs/v12_phase2_dependency_scan_20260317_191535.json`

3. Quick-profile performance guardrails.
- Status: completed in V1.2 B3 (`2026-03-17`).
- Result: quick profile now enforces scan guardrails (time budget + CI/dependency caps + oversized file skips) with explicit unknown/hypothesis tracking.
- Evidence:
  - `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE3_QUICK_GUARDRAILS_2026-03-17.md`
  - `pilot_runs/v12_phase3_quick_runtime_20260317_192720_results.json`

## Priority P1
4. Stack detection expansion.
- Add fallback signals beyond root manifests (workspace manifests, lockfile context, language markers).
- Goal: reduce unknown stack cases (`LD-02`-like) in pilot matrix.

5. Hypothesis quality scoring calibration.
- Refine confidence model using validator/confirmation outcomes.
- Goal: reduce unnecessary unknown inflation while preserving safety.

6. Validator operational recall growth.
- Status: completed in V1.2 B4 (`2026-03-17`).
- Result: validator now flags low-detail CI maps, tracked-but-unresolved canonical test-command gaps, and fallback-entrypoint + open test-gap combinations.
- Evidence:
  - `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE4_VALIDATOR_RECALL_2026-03-17.md`
  - `pilot_runs/v12_phase4_validator_recall_20260317_200330.json`

## Priority P2
7. Acceptance automation packaging.
- Convert phase scripts into reusable command entry points for repeatable audits.
- Goal: one-command rerun for acceptance + negative + repeatability bundles.

8. Report usability improvements.
- Add compact per-repo delta dashboards and top-risk summaries in markdown output.

## Exit target for V1.2
- Keep `blocking=0` and `critical=0` on full matrix.
- Improve dependency-map and CI-parsing accuracy.
- Improve quick-profile runtime distribution on largest repos.

## B5 release gate status
- Status: completed in V1.2 B5 (`2026-03-17`) after post-fix rerun.
- Result: full acceptance matrix passed hard safety gates (`blocking=0`, `critical=0`) and strict repeatability target is met (`6/6` on repeat + control).
- Current decision: `GO` for V1.2 release freeze from B5 gate perspective.
- Evidence:
  - `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_2026-03-17.md` (initial NO-GO snapshot)
  - `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_RERUN_2026-03-17.md` (post-fix GO snapshot)
  - `pilot_runs/v12_b5_release_r2_20260317_210650_results.json`
  - `pilot_runs/v12_b5_repeat_r2_20260317_210650.json`
  - `pilot_runs/v12_b5_repeat_check_r2_20260317_210650.json`
