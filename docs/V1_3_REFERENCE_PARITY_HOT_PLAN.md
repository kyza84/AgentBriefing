# V1.3 Reference-Parity Hot Plan (Tomorrow)

Updated: 2026-03-18  
Execution date: 2026-03-19

## Progress
1. RP-01: completed (`docs/REFERENCE_PARITY_CONTRACT_V1.md`)
2. RP-02: completed (`src/opack/engines/generator.py`, `tests/test_pipeline_smoke.py`)
3. RP-03: completed (`src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py`)
4. RP-04: completed (`src/opack/engines/questionnaire.py`, `tests/test_pipeline_smoke.py`)
5. RP-05: completed (`src/opack/monitor/ui.py`)
6. RP-06: completed (`docs/archive/pilot_validation/reports/PILOT_RESULTS_REFERENCE_PARITY_2026-03-19.md`)

## Why this plan exists
Current V1.2 + UI baseline is functional, but output quality is below target reference operating-layer quality.  
Tomorrow focus is not "new features", but parity growth for generated operating-pack usefulness.

## Goal for 2026-03-19
Raise generated operating-pack from "working baseline" to "reference-parity direction" on three critical axes:
1. operational doc quality and structure,
2. questionnaire depth and signal quality,
3. validator strictness against missing operational content.

## Hard scope (tomorrow only)
In scope:
1. Reference-parity contract freeze for V1 artifacts (required sections + cross-file links).
2. Generator template upgrade for core operating-layer files.
3. Validator rules for section completeness and silent-failure detection.
4. Questionnaire depth fix (too few questions problem).
5. One focused UI usability pass for questionnaire readability and clarity.
6. Targeted pilot rerun + explicit gap report.

Out of scope:
1. V2 SaaS maintenance automation.
2. V3 governance workflows.
3. Full visual redesign of monitor UI from scratch.

## Acceptance targets (tomorrow EOD)
1. Generated pack includes required operational sections with no mandatory section omissions on pilot subset.
2. Questionnaire asks more than one question on complex repos (profile-dependent floor is enforced).
3. Validator explicitly reports missing critical operational sections (no silent pass).
4. Gap report is published with 4 required blocks:
   - what was correct,
   - what was missed,
   - where output looked convenient but was inaccurate,
   - where validator should have warned but was silent.

## Work packages

### RP-01 (P0): Reference contract freeze
- Problem: no explicit parity contract vs target operating-layer shape.
- Deliverable:
  1. `docs/REFERENCE_PARITY_CONTRACT_V1.md` with required files/sections/checks.
  2. machine-checkable checklist for validator mapping.
- Done when:
  1. all required sections for core files are explicitly listed,
  2. each section has source-of-truth class (`scanner_fact` or `questionnaire_policy`).

### RP-02 (P0): Generator parity upgrade
- Problem: generated docs are structurally useful but operationally shallow.
- Deliverable:
  1. update generator mappings for core operational files:
     - architecture view,
     - project state,
     - first-message instructions,
     - handoff instructions,
     - behavior rules,
     - context update rules,
     - stale-context detection notes.
- Done when:
  1. each required section from RP-01 is present in generated output,
  2. unresolved unknowns are surfaced as explicit "open decisions" blocks.

### RP-03 (P0): Validator parity guardrails
- Problem: validator may pass packs that look complete but miss critical operational sections.
- Deliverable:
  1. new validator rules bound to RP-01 checklist,
  2. explicit issue IDs for missing/weak operational sections.
- Done when:
  1. removing mandatory section triggers validator issue,
  2. severity reflects impact (major/critical where needed),
  3. no silent success on known-bad synthetic fixtures.

### RP-04 (P1): Questionnaire depth fix
- Problem: complex repos sometimes produce only 1 question.
- Deliverable:
  1. profile-specific minimum question floor:
     - `quick >= 3`
     - `balanced >= 5`
     - `strict >= 7`
  2. priority ordering by impact + confidence gap.
- Done when:
  1. on complex pilot repos questionnaire exceeds floor,
  2. questions remain actionable (confirm/edit/reject + concrete hypothesis text).

### RP-05 (P1): UI questionnaire usability pass
- Problem: UI feels functional but visually and cognitively weak.
- Deliverable:
  1. cleaner question card hierarchy (type/impact/reason clearly visible),
  2. stronger input affordance and answer status visibility,
  3. small copy/spacing polish in dark theme only.
- Done when:
  1. operator can answer full questionnaire without ambiguity,
  2. no low-contrast or clipped critical controls on standard desktop window.

### RP-06 (P1): Pilot rerun + parity report
- Deliverable:
  1. run on at least 3 mixed/complex repositories,
  2. publish `docs/archive/pilot_validation/reports/PILOT_RESULTS_REFERENCE_PARITY_2026-03-19.md`.
- Done when report contains:
  1. delta vs current baseline,
  2. the 4 mandatory quality blocks,
  3. next risk-ranked fixes.

## Execution order (strict)
1. RP-01 contract freeze
2. RP-02 generator upgrade
3. RP-03 validator guardrails
4. RP-04 questionnaire depth
5. RP-05 UI usability pass
6. RP-06 pilot rerun and report

## Risks tomorrow
1. Scope blow-up from UI redesign requests.
2. Overfitting generator to one reference format.
3. Validator false positives after strict parity checks.

## Guardrails tomorrow
1. Keep work only in `D:\\earnforme\\AgentBriefing`.
2. Do not touch `D:\\earnforme\\solana-alert-bot`.
3. Prioritize parity quality over new feature breadth.
