# V1.1 Gap Register

## Status
- Date: 2026-03-17
- Stage: A0 (draft completed, pending owner approval)
- Purpose: capture concrete quality gaps before implementation

## Classification model
1. Determined correctly
2. Missed
3. Convenient but inaccurate
4. Validator should have warned but was silent

## Evidence baseline
- Local run:
  - `out/pack-1b796b3e20/FACT_MODEL.json`
  - `out/pack-1b796b3e20/VALIDATION_REPORT.json`
- Pilot release matrix samples:
  - `pilot_runs/release_phase6_20260317_141558/LD-02/quick/pack-a61c002686/*`
  - `pilot_runs/release_phase6_20260317_141558/ND-03/quick/pack-4bf8367c66/*`
  - `pilot_runs/release_phase6_20260317_141558/PY-01/quick/pack-0b877fc012/*`

## Determined correctly (baseline strengths)

| ID | Area | Observation | Evidence |
|---|---|---|---|
| C-001 | Stack detection | Main stacks are detected correctly on pilot samples (`python`, `node`, `go`, `rust`, `jvm`). | `release_phase6_*/*/FACT_MODEL.json` |
| C-002 | Environment signal | Presence of CI/docker-level environment markers is detected (`github-actions`, `docker`, etc.). | `release_phase6_*/*/FACT_MODEL.json` |
| C-003 | Unknown fallback | If commands are not detected, scanner can emit command unknown (`u_commands_001`) and keep flow unblocked. | `LD-02/quick/FACT_MODEL.json` |
| C-004 | Stability after hardening | Final release matrix has zero scanner warnings and zero blocking runs. | `release_phase6_20260317_141558_results.json` |

## Priority gaps (P0/P1)

| ID | Class | Area | Observation | Impact | Priority | Candidate fix |
|---|---|---|---|---|---|---|
| G-101 | missed | `tests_map` | Fact model has no explicit test inventory (locations, framework, canonical post-change run). | Agent may finish without real regression check. | P0 | Add `tests_map` section: discovered test roots, framework hints, command candidates, confidence. |
| G-102 | missed | `ci_pipeline_map` | Only `github-actions` presence is captured, no trigger/job/step model. | Agent can break CI/deploy constraints unknowingly. | P0 | Parse workflows into trigger->jobs->critical steps model with confidence. |
| G-103 | missed | `module_dependency_map` | No dependency/impact graph between modules. | Change blast radius is hidden; risky edits increase. | P0 | Build lightweight import/reference dependency graph per supported stack. |
| G-104 | missed | `critical_files_map` | No hot/stable/risky file map from repo patterns/history. | High-risk files are modified without guardrails. | P1 | Add risk map from naming patterns + optional git-history weighting. |
| G-105 | convenient but inaccurate | Entrypoint fallback | `README.md (manual entrypoint reference)` is accepted as entrypoint (LD-02). | First-message instructions can direct agent to non-executable flow. | P0 | Mark fallback entrypoints as hypothesis, not confirmed fact. |
| G-106 | convenient but inaccurate | Entrypoint ranking | In monorepo, entrypoints can be `.github/actions/*` or examples (ND-03), not product runtime entry. | Agent starts in maintenance scripts instead of core app. | P0 | Rank entrypoints by operational relevance (runtime > tests/examples > tooling). |
| G-107 | convenient but inaccurate | Command ranking | First command may be benchmark/lint (`npm run bench:render-pipeline`) and is used as recommended verification command. | Agent validates with non-regression command. | P0 | Score commands by "verification value" and surface canonical test/build checks first. |
| G-108 | missed | Unknown strategy | Unknowns are mostly absence-based; no confirm/edit/reject hypothesis questions. | Too few precise questions, hidden assumptions stay unchallenged. | P0 | Add `hypotheses[]` with confidence and ask targeted confirmation questions. |
| G-109 | convenient but inaccurate | Confidence model | High confidence can coexist with poor operational precision (e.g., noisy entrypoint lists). | False certainty reduces corrective questioning. | P1 | Split confidence into structural vs operational confidence and gate questions by each. |
| G-110 | validator silent | Entrypoint quality | Validator does not warn when entrypoint is fallback/manual or low-relevance path. | Pack passes with misleading startup instructions. | P0 | Add validator rule: fallback/manual entrypoint requires warning or user confirmation. |
| G-111 | validator silent | CI operational completeness | Validator does not warn when CI is detected but pipeline map is absent. | Pack appears complete while CI risk remains opaque. | P0 | Add rule: CI detected + missing `ci_pipeline_map` -> major issue. |
| G-112 | validator silent | Test operability | Validator does not warn when no concrete canonical test command is established for repo. | Pack can pass without executable post-change verification path. | P0 | Add rule: missing verified test command -> major issue unless explicit justified exception. |

## Initial seed topics (approved scope)
- tests layout + canonical post-change command
- ci pipeline map (trigger -> jobs -> critical steps)
- critical file map (risk/hot paths)
- module dependency map
- hypothesis-based unknown flow (confirm/edit/reject)

## Acceptance rule for A0
- At least top-10 P0/P1 gaps recorded with owner-approved priorities.

## A0 result
- Draft produced with 12 prioritized gaps (`P0/P1`).
- Next action: owner approves priorities and lock scope for A1 contract design.
