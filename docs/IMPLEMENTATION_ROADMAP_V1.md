# IMPLEMENTATION_ROADMAP_V1

## Status snapshot (2026-03-17)
- V1 delivery phases (`2 -> 6`) are completed.
- Release baseline was published (commit `4c71788`, tag `v0.1.0`).
- Active improvement track moved to V1.1:
  - `docs/V1_1_OPERATIONAL_ACCURACY_PLAN.md`
  - `docs/V1_1_GAP_REGISTER.md`

## Historical V1 phase map

### Phase 2 - Scanner Baseline
- File tree scan.
- Stack/environment/entrypoint/command extraction.
- Unknown + confidence model.

### Phase 3 - Questionnaire Engine
- Unknown-driven question list.
- Question budget by profile (`quick/balanced/strict`).
- Policy model generation from answers.

### Phase 4 - Generator Engine
- Fact + Policy to operating-pack artifacts.
- Manifest generation.
- Deterministic section structure.

### Phase 5 - Validator Engine
- Completeness checks.
- Consistency checks.
- Operational applicability checks.
- Severity-ranked report with blocking on critical issues.

### Phase 6 - Pilot + Release
- Full pilot matrix execution.
- Release hardening.
- Baseline publish.

## Next track
- Continue with V1.1 operational accuracy cycle.
- Keep V2/V3 scope excluded until V1.1 acceptance is complete.
