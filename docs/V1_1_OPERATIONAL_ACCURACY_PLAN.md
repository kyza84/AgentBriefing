# V1.1 Operational Accuracy Plan

## Status
- Date: 2026-03-17
- State: approved for execution
- Owner mode: "analyze first, then implement"

## Goal
Increase practical agent effectiveness by adding operational facts and hypothesis-driven unknown resolution.

## Why this cycle
- V1 baseline is stable and released.
- Current scan quality is strong on structure, but limited on operations.
- Next quality step is not more templates; it is better factual extraction for real workflows.

## Current gaps to close
- Missing `tests_map`: where tests are, how to run them, what is canonical check after change.
- Missing `ci_pipeline_map`: what exactly runs on push/PR and what can break deploy.
- Missing `critical_files_map`: high-risk or high-churn files.
- Missing `module_dependency_map`: impact of module-to-module dependencies.
- Unknowns are generated mainly from absence, not from hypotheses with confidence.

## Execution stages

### A0 - Baseline Gap Analysis
Goal:
- Build a single "Gap Register" with four classes:
  - determined correctly,
  - missed,
  - convenient but inaccurate,
  - validator should have warned but did not.
Output:
- `docs/V1_1_GAP_REGISTER.md`
Gate:
- Top-10 P0/P1 gaps agreed.

### A1 - FactModel v1.1 Contract
Goal:
- Extend data model with operational facts and hypothesis objects.
Output:
- contract addendum (fields and semantics) for:
  - `tests_map`,
  - `ci_pipeline_map`,
  - `critical_files_map`,
  - `module_dependency_map`,
  - `hypotheses[]` (claim + confidence + evidence).
Gate:
- Backward compatibility confirmed.

### A2 - Scanner v1.1
Goal:
- Extract operational facts, not only structure.
Output:
- scanner enhancements for tests, CI workflows, critical files, dependencies.
- confidence per operational section.
Gate:
- operational extraction works on pilot sample without blocking regressions.

### A3 - Questionnaire v1.1
Goal:
- Ask confirmation/correction questions on hypotheses instead of generic unknowns.
Output:
- confirm/edit/reject question flow.
- question budget prioritization by impact and confidence.
Gate:
- median unknowns reduced by >= 40% vs current baseline.

### A4 - Validator v1.1
Goal:
- Enforce quality of operational facts.
Output:
- new rules for missing or weak operational sections.
- explicit warnings for fallback-only conclusions (e.g., README entrypoint without confirmation).
Gate:
- "should-have-warned" test suite passes 100%.

### A5 - Acceptance Matrix v1.1
Goal:
- Validate improvements on real repositories.
Output:
- full matrix report with delta vs V1 baseline.
Gate:
- `blocking=0`, `critical=0`, operational quality improvements verified.

### A6 - Release v1.1
Goal:
- Freeze improved baseline and document known limits.
Output:
- release report and backlog handoff for next cycle.

## Metrics (must track)
- Unknown reduction rate.
- Hypothesis confirmation rate.
- False-confidence incidents.
- Validator recall for known silent-failure cases.
- Time-to-pack and blocking status stability.

## Scope control
- No V2 maintainer automation in this cycle.
- No governance/RBAC additions in this cycle.
- Focus only on V1.1 quality and operational accuracy.
