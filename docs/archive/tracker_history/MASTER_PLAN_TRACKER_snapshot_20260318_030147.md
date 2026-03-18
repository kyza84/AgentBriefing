# MASTER_PLAN_TRACKER

## Purpose
Single source of truth for execution progress of Operating-Pack Platform V1.

After each material iteration record:
- what is completed,
- what is not completed,
- whether deviation happened,
- why deviation happened,
- evidence file paths.

## Mandatory workflow rule
1. Before work: identify active phase(s) from this file.
2. After each iteration: update phase status and log row.
3. In chat report: always include `Completed / Not completed / Deviation / Next`.
4. If deviation is needed: capture reason and risk before applying.
5. No phase is done without measurable acceptance criteria.

## Scope control rule (critical)
- V1 must not absorb V2/V3 scope.
- Any out-of-scope request is recorded into backlog, not executed inside V1 baseline.

## V1 implementation phase map

| Phase | Name | Status | Purpose | Exit Criteria |
|---|---|---|---|---|
| 0 | Architecture Foundation | in_progress | Freeze architecture contract and tech-debt policy | Core boundaries, data contracts, gates, and debt policy approved |
| 1 | Builder Contract Pack | pending | Define executable specs for scan/ask/generate/validate flow | V1 execution specs approved for implementation start |
| 2 | Scanner Baseline | completed | Build fact extraction baseline with unknown/confidence model | Fact model quality accepted on pilot sample repos |
| 3 | Adaptive Questionnaire | completed | Implement unknown-driven questioning with conflict checks | Questionnaire resolves critical unknowns with bounded question count |
| 4 | Pack Generator | completed | Build operating-pack generation from Fact+Policy models | 9 required artifacts generated with no mandatory gaps |
| 5 | Validator | completed | Add completeness/consistency/applicability checks | Validation report severity model accepted |
| 6 | Pilot + Release V1 | completed | Validate on pilot repos and ship V1 baseline | V1 target metrics achieved and release baseline published |

## V1.1 improvement cycle map

| Stage | Name | Status | Purpose | Exit Criteria |
|---|---|---|---|---|
| A0 | Gap Analysis | completed | Build concrete quality gap register from current baseline | Top-10 P0/P1 gaps agreed |
| A1 | FactModel v1.1 Contract | completed | Add operational fact sections and hypotheses contract | Backward-compatible contract approved |
| A2 | Scanner v1.1 | completed | Extract tests/CI/critical files/dependencies | Operational extraction stable on pilot sample |
| A3 | Questionnaire v1.1 | completed | Shift unknowns to confirm/edit/reject hypothesis flow | Unknown load reduced with same or better precision |
| A4 | Validator v1.1 | completed | Enforce operational fact quality and silent-failure checks | Should-have-warned suite passes |
| A5 | Acceptance Matrix v1.1 | completed | Validate improvements against V1 baseline | Blocking=0, critical=0, quality delta accepted |
| A6 | Release V1.1 | completed | Freeze improved baseline and document limits | Release report and backlog handoff published |

## V1.2 improvement cycle map

| Stage | Name | Status | Purpose | Exit Criteria |
|---|---|---|---|---|
| B0 | Baseline Freeze | completed | Freeze comparable baseline before new hardening | Baseline metrics/report fixed for delta checks |
| B1 | CI Parser Hardening | completed | Replace trigger heuristics with structured workflow parsing | CI events/filters/jobs extraction passes regression suite |
| B2 | Dependency Mapper Depth | completed | Improve cross-language dependency extraction precision | Dependency map coverage rises on pilot set |
| B3 | Quick Guardrails | completed | Add quick-profile runtime guardrails on huge repos | Runtime p95 and timeout risk reduced |
| B4 | Validator Recall Expansion | completed | Expand should-have-warned detection set | Negative suite recall improved without false block spikes |
| B5 | Acceptance + Release Gate | completed | Validate V1.2 with full acceptance/repeatability | Gate targets achieved and release docs published |

## UI V1 cycle map

| Stage | Name | Status | Purpose | Exit Criteria |
|---|---|---|---|---|
| UI-0 | UX Contract | completed | Fix UX flow, states, screen map, and data contracts for first full UI | `docs/UI_V1_SPEC.md` exists and covers flow/state/contracts/scope |
| UI-1 | Runtime Stage API | completed | Introduce stage-aware run API with progress events and questionnaire pause/resume | API supports `start -> progress -> questions -> submit -> result` |
| UI-2 | Launch + Progress UX | completed | Build launch screen and live progress/timeline UX in dark theme | User can run URL-based check and see stage-by-stage progress |
| UI-3 | Questionnaire UX | completed | Build in-UI question flow for unknown/hypothesis resolution | User can answer in UI and continue build without JSON file |
| UI-4 | Result + File Viewer | completed | Add result dashboard and generated-file viewer | User can inspect pack artifacts in-app |
| UI-5 | UX Hardening | completed | Stabilize negative paths and polish usability | Pilot subset passes with no critical UX blockers |

## Phase 0 - Architecture Foundation (detailed)

Status: `in_progress`

Goal:
- Build a complete architecture contract before implementation starts.
- Prevent scope drift and hidden technical debt.

Work packages:
1. Define core boundaries:
   - `Core Domain`, `Core Engines`, `Orchestrators`, `Adapters`.
2. Freeze data contracts:
   - `FactModel`, `PolicyModel`, `OperatingPackManifest`, `ValidationReport`.
3. Freeze V1 pipeline state machine:
   - build flow and stage-gate transitions.
4. Freeze tech-debt policy:
   - debt categories, severity, release thresholds.
5. Create architecture sign-off package for owner approval.

Expected artifacts:
- `docs/ARCHITECTURE.md` (full product architecture baseline).
- `V1_APPROVAL_PLAN.txt` (source of execution contract).
- `docs/MASTER_PLAN_TRACKER.md` (phase and debt tracking).

Exit criteria:
- Core/adapter boundary is explicit and approved.
- V1 data contracts are documented and versioned.
- Gate criteria are explicit for each phase transition.
- Debt policy exists with critical debt release block.

Main risks in phase:
- Mixing V2/V3 concerns into V1 architecture.
- Ambiguous ownership of core rules vs adapters.

## Phase 1 - Builder Contract Pack (detailed)

Status: `pending`

Goal:
- Produce implementation-ready specification set for V1 Builder.
- Ensure every V1 stage has measurable inputs/outputs/quality bars.

Work packages:
1. Scanner spec:
   - what is extracted, confidence model, unknown strategy.
2. Questionnaire spec:
   - adaptive branching logic, question budget, conflict handling.
3. Generator spec:
   - mapping from Fact+Policy models to 9 V1 artifacts.
4. Validator spec:
   - rules, severity levels, blocking criteria, remediation format.
5. End-to-end dry-run script (spec-level):
   - canonical run path with expected outputs per stage.

Expected artifacts:
- `docs/SCANNER_SPEC_V1.md` (to create).
- `docs/QUESTIONNAIRE_SPEC_V1.md` (to create).
- `docs/GENERATOR_SPEC_V1.md` (to create).
- `docs/VALIDATOR_SPEC_V1.md` (to create).
- `docs/V1_ACCEPTANCE_MATRIX.md` (to create).

Exit criteria:
- All 4 stage specs approved by owner.
- Acceptance matrix for V1 is finalized.
- No open critical ambiguity in V1 pipeline contracts.

Main risks in phase:
- Over-design that delays implementation start.
- Under-specified validator leading to weak quality bar.

## Active tasks

| ID | Task | Status | Owner | Evidence/Notes |
|---|---|---|---|---|
| V1-001 | Create baseline operating-layer docs for AgentBriefing | completed | Codex | `docs/*` initialization |
| V1-002 | Confirm V1 sign-off checklist and approval format | in_progress | Owner + Codex | Based on `V1_APPROVAL_PLAN.txt` |
| V1-003 | Confirm pilot repo set and acceptance metrics thresholds | pending | Owner | Needed for Phase 6 readiness |
| V1-004 | Hard-save repository boundary (`solana-alert-bot` blocked) | completed | Codex | Updated guardrails in core docs |
| V1-005 | Phase 0: finalize architecture boundaries and data contracts | in_progress | Codex | `docs/ARCHITECTURE.md`, tracker Phase 0 |
| V1-006 | Phase 1 prep: draft V1 stage specs and acceptance matrix | pending | Codex | `docs/*_SPEC_V1.md`, `docs/V1_ACCEPTANCE_MATRIX.md` |
| V1-007 | Initialize runnable project skeleton (CLI + engines + pipeline) | completed | Codex | `pyproject.toml`, `src/opack/*`, `tests/test_pipeline_smoke.py` |
| V1-008 | Define technical program architecture for implementation | completed | Codex | `docs/PROGRAM_ARCHITECTURE_V1.md`, `docs/IMPLEMENTATION_ROADMAP_V1.md` |
| V1-009 | Start Phase 2 scanner depth implementation | completed | Codex | `src/opack/engines/scanner.py`, scanner test coverage |
| V1-010 | Phase 2 acceptance on pilot repo sample | completed | Codex + Owner | Full 12x3 matrix passed, see `docs/pilot_validation/PILOT_RESULTS_FULL_2026-03-17.md` |
| V1-011 | Implement Phase 3 answer-driven questionnaire flow | completed | Codex | `src/opack/engines/questionnaire.py`, `src/opack/cli.py`, `src/opack/orchestrators/build_pipeline.py` |
| V1-012 | Phase 3 acceptance on pilot repo sample | completed | Codex + Owner | Full 12x3 matrix passed, see `docs/pilot_validation/PILOT_RESULTS_FULL_2026-03-17.md` |
| V1-013 | Build pilot repo registry (open-source, pinned SHA) | completed | Codex | `docs/pilot_validation/PILOT_REPO_REGISTRY.md` |
| V1-014 | Create pilot protocol and reporting templates | completed | Codex | `docs/pilot_validation/PILOT_TEST_PROTOCOL.md`, `docs/pilot_validation/PILOT_RESULTS_TEMPLATE.md` |
| V1-015 | Execute 36-run pilot matrix (12 repos x 3 profiles) | completed | Codex + Owner | `36/36` success in `pilot_runs/full_20260317_030825_results.json` |
| V1-016 | Implement personal one-click monitor UI for repo checks | completed | Codex | `src/opack/monitor/*`, `opack monitor-ui` |
| V1-017 | Verify monitor workflow docs and tests | completed | Codex | `tests/test_monitor_service.py`, `docs/pilot_validation/PERSONAL_MONITOR_QUICKSTART.md` |
| V1-018 | Run pilot batch #1 (3 repos x 3 profiles) and publish results | completed | Codex | `docs/pilot_validation/PILOT_RESULTS_BATCH1_2026-03-17.md`, `pilot_runs/batch_20260317_024740` |
| V1-019 | Implement Phase 4 generator hardening (fact-driven artifacts) | completed | Codex | `src/opack/engines/generator.py`, generator tests |
| V1-020 | Localize user-facing program stats to Russian | completed | Codex | `src/opack/cli.py`, `src/opack/monitor/ui.py`, `src/opack/monitor/service.py` |
| V1-021 | Phase 4 acceptance on pilot sample | completed | Codex + Owner | Accepted on full matrix, see `docs/pilot_validation/PILOT_RESULTS_FULL_2026-03-17.md` |
| V1-022 | Phase 5 start gate after validation review | completed | Owner + Codex | Start approved and executed in current iteration |
| V1-023 | Implement Phase 5 validator hardening ruleset | completed | Codex | `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py` |
| V1-024 | Validate Phase 5 on targeted external repos (9 runs) | completed | Codex | `pilot_runs/phase5_validation_20260317.json`, `docs/pilot_validation/PILOT_RESULTS_PHASE5_2026-03-17.md` |
| V1-025 | Release hardening: ignore service workdirs in scanner | completed | Codex | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py` |
| V1-026 | Execute final Phase 6 release matrix (12x3 pinned) | completed | Codex | `pilot_runs/release_phase6_20260317_141558_results.json`, `docs/pilot_validation/PILOT_RESULTS_RELEASE_PHASE6_2026-03-17.md` |
| V11-001 | Approve and freeze V1.1 Operational Accuracy plan | completed | Owner + Codex | `docs/V1_1_OPERATIONAL_ACCURACY_PLAN.md` |
| V11-002 | Build V1.1 Gap Register (4 classes of quality gaps) | completed | Codex + Owner | `docs/V1_1_GAP_REGISTER.md` |
| V11-003 | Implement FactModel v1.1 operational contract | completed | Codex | `src/opack/contracts/models.py` |
| V11-004 | Implement Scanner v1.1 operational extraction | completed | Codex | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py` |
| V11-005 | Implement Questionnaire v1.1 hypothesis flow | completed | Codex | `src/opack/engines/questionnaire.py`, `src/opack/cli.py`, `tests/test_pipeline_smoke.py` |
| V11-006 | Implement Validator v1.1 operational quality checks | completed | Codex | `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py` |
| V11-007 | Execute V1.1 acceptance matrix (12x3, delta vs V1) | completed | Codex | `pilot_runs/acceptance_v1_1_20260317_155513_results.json`, `docs/pilot_validation/PILOT_RESULTS_V1_1_ACCEPTANCE_2026-03-17.md` |
| V11-008 | Prepare V1.1 release package and known limits | completed | Codex + Owner | `docs/pilot_validation/PILOT_RESULTS_V1_1_PHASE6_RELEASE_2026-03-17.md`, `docs/V1_1_KNOWN_LIMITS.md`, `docs/V1_2_BACKLOG.md` |
| V11-009 | Open V1.2 execution cycle from prioritized backlog | completed | Owner + Codex | V1.2 cycle agreed; B1 started by owner request |
| V11-010 | Post-A6 quality hardening (blocking majors + scanner regressions) | completed | Codex | `src/opack/engines/validator.py`, `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/a6_negative_validator_20260317_165847.json` |
| V12-001 | Freeze V1.2 baseline metrics/evidence pack | completed | Codex | `pilot_runs/v12_baseline_freeze_20260317_185644.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_BASELINE_FREEZE_2026-03-17.md` |
| V12-002 | B1: CI parser hardening (events/filters/jobs critical steps) | completed | Codex | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase1_ci_parser_20260317_184826.json` |
| V12-003 | B2: Dependency mapper depth upgrade | completed | Codex | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase2_dependency_scan_20260317_191535.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE2_DEPENDENCY_MAPPER_2026-03-17.md` |
| V12-004 | B3: Quick-profile performance guardrails | completed | Codex | `src/opack/engines/scanner.py`, `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase3_quick_runtime_20260317_192720_results.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE3_QUICK_GUARDRAILS_2026-03-17.md` |
| V12-005 | B4: Validator recall expansion | completed | Codex | `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase4_validator_recall_20260317_200330.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE4_VALIDATOR_RECALL_2026-03-17.md` |
| V12-006 | B5: V1.2 acceptance and release gate | completed | Codex + Owner | Post-fix rerun stabilized repeatability (`6/6`), B5 gate `GO` |
| V12-007 | Post-B5 hot-fix cycle (P1/P2/P3 accuracy gaps) | completed | Codex + Owner | `docs/V1_2_HOT_FIX_PLAN.md`, scanner/validator fixes validated by `40/40` tests |
| UI-001 | UI-0: create UI V1 specification baseline | completed | Codex + Owner | `docs/UI_V1_SPEC.md` |
| UI-002 | UI-1: implement runtime stage API for progress/questionnaire boundary | completed | Codex | `src/opack/monitor/service.py`, `tests/test_monitor_service.py` |
| UI-003 | UI-2: implement dark launch/progress UX shell | completed | Codex | `src/opack/monitor/ui.py`, `pilot_runs/ui2_stage_smoke_20260318_002052.json` |
| UI-004 | UI-3: implement in-UI questionnaire step (no mandatory answers file) | completed | Codex | `src/opack/monitor/ui.py`, `tests/test_monitor_ui.py` |
| UI-005 | UI-4: implement result dashboard + file viewer in UI | completed | Codex | `src/opack/monitor/ui.py`, `pilot_runs/ui4_smoke_20260318_004810.json` |
| UI-006 | UI-5: harden questionnaire/file-viewer UX on negative cases | completed | Codex | `src/opack/monitor/ui.py`, `tests/test_monitor_ui.py` |
| RP-001 | Prepare and approve tomorrow Reference-Parity hot plan | completed | Owner + Codex | `docs/V1_3_REFERENCE_PARITY_HOT_PLAN.md` |
| RP-002 | RP-01..RP-06 execution (reference parity, questionnaire depth, validator strictness, pilot report) | pending | Codex + Owner | Execution date: `2026-03-19` |

## Iteration log

| Date | Iteration | Completed | Not completed | Deviation | Evidence |
|---|---|---|---|---|---|
| 2026-03-17 | Init operating layer | Created `MAIN_PLAN.txt`, `V1_APPROVAL_PLAN.txt`, and `docs/` baseline files | Sign-off checklist pending | None | `MAIN_PLAN.txt`, `V1_APPROVAL_PLAN.txt`, `docs/` |
| 2026-03-17 | Hard boundary lock | Added explicit permanent block for `D:\earnforme\solana-alert-bot` in operating-layer rules | Sign-off checklist still pending | None | `docs/CHAT_FIRST_MESSAGE.md`, `docs/OPERATOR_PATTERNS.md`, `docs/SAFE_TUNING_AGENT_PROTOCOL.md`, `docs/NEXT_CHAT_CONTEXT.md`, `docs/PROJECT_STATE.md` |
| 2026-03-17 | Phase-based execution split | Replaced letter phases with Phase 0-6 map and added detailed Phase 0/1 execution plan | Phase 1 spec files not created yet | None | `docs/MASTER_PLAN_TRACKER.md` |
| 2026-03-17 | Program bootstrap start | Rolled back prior iteration artifacts and started real program skeleton (CLI, pipeline, engines, tests, architecture docs) | Scanner depth, adaptive answers, stronger validator still pending | None | `pyproject.toml`, `src/opack/`, `tests/test_pipeline_smoke.py`, `docs/PROGRAM_ARCHITECTURE_V1.md`, `docs/IMPLEMENTATION_ROADMAP_V1.md` |
| 2026-03-17 | Phase 2 scanner implementation | Implemented deeper scanner (stacks, entry points, commands, environments, confidence/unknown model) and added dedicated scanner tests | Pilot acceptance on sample repos not completed yet | None | `src/opack/engines/scanner.py`, `src/opack/contracts/models.py`, `tests/test_pipeline_smoke.py` |
| 2026-03-17 | Phase 3 questionnaire implementation | Implemented answer-driven questionnaire with profile budget, unknown resolution, conflict checks, CLI answers-file/interactive mode, and validator fix for fully resolved unknowns | Phase 2 and Phase 3 pilot acceptance not completed yet | None | `src/opack/engines/questionnaire.py`, `src/opack/cli.py`, `src/opack/orchestrators/build_pipeline.py`, `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py` |
| 2026-03-17 | Pilot docs branch and OSS registry | Created dedicated `docs/pilot_validation/` branch with 12 pinned open-source repos, test protocol, and results template | Pilot matrix execution not started yet | None | `docs/pilot_validation/README.md`, `docs/pilot_validation/PILOT_REPO_REGISTRY.md`, `docs/pilot_validation/PILOT_TEST_PROTOCOL.md`, `docs/pilot_validation/PILOT_RESULTS_TEMPLATE.md` |
| 2026-03-17 | Personal monitor implementation | Added one-click monitor window (`monitor-ui`) to run repo checks from URL and show validation metrics in-app, with pilot repo dropdown and answers-file support | Full 36-run pilot matrix still pending | None | `src/opack/monitor/service.py`, `src/opack/monitor/ui.py`, `src/opack/cli.py`, `tests/test_monitor_service.py`, `docs/pilot_validation/PERSONAL_MONITOR_QUICKSTART.md` |
| 2026-03-17 | Pilot batch #1 execution | Executed 9 runs on pinned `PY-01`, `ND-01`, `GO-01` across `quick/balanced/strict`; all runs passed with blocking=false and quality=1.0 | Remaining 27 runs for full matrix | None | `docs/pilot_validation/PILOT_RESULTS_BATCH1_2026-03-17.md`, `pilot_runs/batch_20260317_024740` |
| 2026-03-17 | Phase 4 + RU localization | Hardened generator to produce richer fact-driven artifacts and switched user-facing stats/output labels to Russian; fixed UTF-8 console handling | Phase 4 acceptance still pending on pilot matrix | None | `src/opack/engines/generator.py`, `src/opack/cli.py`, `src/opack/monitor/ui.py`, `src/opack/monitor/service.py`, `tests/test_pipeline_smoke.py` |
| 2026-03-17 | Full pilot matrix acceptance | Executed full `12x3` matrix (`36/36` success, blocking=0, issues=0), closed acceptance for Phase 2/3/4 and moved release phase to in-progress | Phase 5 implementation still deferred by instruction | Minor: intermediate ND-03 long-path pressure on Windows in rerun; mitigated and final pinned rerun passed | `docs/pilot_validation/PILOT_RESULTS_FULL_2026-03-17.md`, `pilot_runs/full_20260317_030825_results.json`, `src/opack/engines/scanner.py` |
| 2026-03-17 | Phase 5 implementation + validation | Implemented Phase 5 validator hardening (completeness/consistency/applicability checks, severity-based recommendations) and passed validation (`9/9` external runs with blocking=0; local test suite later expanded to `12/12`) | Phase 6 release baseline checklist not finalized yet | None | `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/phase5_validation_20260317.json`, `docs/pilot_validation/PILOT_RESULTS_PHASE5_2026-03-17.md` |
| 2026-03-17 | Phase 6 release baseline completed | Added scanner release-hardening for service workdirs and executed final pinned `12x3` release matrix (`36/36` success, blocking=0, critical=0, warnings=0); marked V1 baseline ready | Phase 0/1 architecture-contract docs remain open as planning artifacts | Minor: non-blocking subprocess decode thread warning during long git output collection; acceptance artifacts were generated successfully | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/release_phase6_20260317_141558_results.json`, `docs/pilot_validation/PILOT_RESULTS_RELEASE_PHASE6_2026-03-17.md` |
| 2026-03-17 | V1.1 plan freeze + docs sync | Approved and fixed V1.1 Operational Accuracy plan, synchronized core context docs to avoid drift before execution start | V1.1 Gap Register content not filled yet (A0 in progress) | None | `docs/V1_1_OPERATIONAL_ACCURACY_PLAN.md`, `docs/PROJECT_STATE.md`, `docs/NEXT_CHAT_CONTEXT.md`, `docs/MASTER_PLAN_TRACKER.md` |
| 2026-03-17 | V1.1 A0 draft produced | Filled Gap Register with concrete evidence and 12 prioritized P0/P1 gaps across missed facts, inaccurate heuristics, and validator silent cases | Owner approval for P0/P1 ordering is pending before A1 | None | `docs/V1_1_GAP_REGISTER.md` |
| 2026-03-17 | V1.1 A1-A5 execution | Implemented FactModel/Scanner/Questionnaire/Validator v1.1 and executed full acceptance matrix (`36/36`, blocking=0, critical=0, quality=1.00) with delta report vs V1 baseline | A6 release packaging and known-limits handoff not completed yet | Runtime increase on heavy quick-profile runs due deeper operational extraction; quality gates remained stable | `src/opack/contracts/models.py`, `src/opack/engines/scanner.py`, `src/opack/engines/questionnaire.py`, `src/opack/engines/validator.py`, `pilot_runs/acceptance_v1_1_20260317_155513_results.json`, `docs/pilot_validation/PILOT_RESULTS_V1_1_ACCEPTANCE_2026-03-17.md` |
| 2026-03-17 | V1.1 A6 release gate | Executed anti-ideal validator audit (`5/5` expected failures detected), repeatability subset (`6/6` stable), and published release/limits/backlog docs; marked A6 completed | V1.2 execution not started yet | None | `pilot_runs/a6_negative_validator_20260317_165847.json`, `pilot_runs/a6_repeatability_20260317_163120.json`, `docs/pilot_validation/PILOT_RESULTS_V1_1_PHASE6_RELEASE_2026-03-17.md`, `docs/V1_1_KNOWN_LIMITS.md`, `docs/V1_2_BACKLOG.md` |
| 2026-03-17 | Post-A6 hardening before commit | Promoted critical operational major issues to blocking gate, hardened CI trigger parsing against nested `workflow_dispatch` noise, extended dependency-map coverage for `src/*` layouts, added regression tests, and revalidated full test suite | V1.2 backlog remains pending start | None | `src/opack/engines/validator.py`, `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/a6_negative_validator_20260317_165847.json` |
| 2026-03-17 | V1.2 B1 CI parser hardening | Implemented structured CI workflow parsing (`on` events + trigger filters + job-level critical step extraction), added CI parser regression suite (inline map, block filters, noisy nested inputs), and validated on local heavy repo sample | B0 baseline freeze and B2-B5 still pending | None | `src/opack/contracts/models.py`, `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase1_ci_parser_20260317_184826.json` |
| 2026-03-17 | V1.2 B0 baseline freeze | Frozen baseline metrics and release references for controlled V1.2 deltas (acceptance/negative/repeatability/CI snapshot) | B3-B5 still pending | None | `pilot_runs/v12_baseline_freeze_20260317_185644.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_BASELINE_FREEZE_2026-03-17.md` |
| 2026-03-17 | V1.2 B2 dependency depth | Upgraded dependency resolver for Python package roots, Go module paths, and TS aliases; added focused regression tests and executed 12x3 dependency scan delta (`24/36` vs baseline `15/36`, `+0.25`) | B3-B5 still pending | None | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase2_dependency_scan_20260317_191535.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE2_DEPENDENCY_MAPPER_2026-03-17.md` |
| 2026-03-17 | V1.2 B3 quick guardrails | Implemented quick-profile guardrails (time/file/bytes caps), added explicit guardrail unknown/hypothesis tracking, updated validator behavior for sampled CI mode, and validated quick runtime delta on 12 pilot repos (`p95 448.562s -> 13.767s`, blocking `0/12`) | B4-B5 still pending | None | `src/opack/engines/scanner.py`, `src/opack/contracts/models.py`, `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase3_quick_runtime_20260317_192720_results.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE3_QUICK_GUARDRAILS_2026-03-17.md` |
| 2026-03-17 | V1.2 B4 validator recall expansion | Expanded validator should-have-warned recall for CI detail gaps, tracked-but-unresolved test-command gaps, and fallback-entrypoint/test-gap combinations; added regression tests and revalidated unit suite (`33/33`) | B5 still pending | None | `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_phase4_validator_recall_20260317_200330.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE4_VALIDATOR_RECALL_2026-03-17.md` |
| 2026-03-17 | V1.2 B5 acceptance + release gate (attempt) | Executed full `12x3` acceptance matrix (`36/36` success, blocking=0, critical=0), plus repeatability subset and control rerun; published B5 report and evidence artifacts | Final freeze is not approved: repeatability drift remains (`stable_quality=5/6`, `stable_issue=5/6`) on `ND-02` guardrail boundary | Gate `NO-GO` until repeatability stabilization | `pilot_runs/v12_b5_release_20260317_201853_results.json`, `pilot_runs/v12_b5_repeat_20260317_201853.json`, `pilot_runs/v12_b5_repeat_check_20260317_202744.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_2026-03-17.md` |
| 2026-03-17 | V1.2 B5 repeatability stabilization rerun | Stabilized scanner guardrail boundary behavior (deterministic file walk + time-budget grace), re-ran full B5 acceptance and repeatability control; both repeat runs reached strict stability (`6/6`) and gate moved to `GO` | None | None | `src/opack/engines/scanner.py`, `tests/test_pipeline_smoke.py`, `pilot_runs/v12_b5_release_r2_20260317_210650_results.json`, `pilot_runs/v12_b5_repeat_r2_20260317_210650.json`, `pilot_runs/v12_b5_repeat_check_r2_20260317_210650.json`, `docs/pilot_validation/PILOT_RESULTS_V1_2_PHASE5_RELEASE_GATE_RERUN_2026-03-17.md` |
| 2026-03-17 | V1.2 hot-fix closure (P1/P2/P3) | Closed real gaps in dependency resolution, test-signal accuracy, validator unknown-visibility checks, and CI parser architecture risk; migrated CI parsing to internal YAML-AST with fallback, added regressions, and revalidated full suite (`40/40`) | Full YAML-spec parser compliance remains out of scope (tracked residual risk) | None | `docs/V1_2_HOT_FIX_PLAN.md`, `src/opack/engines/scanner.py`, `src/opack/engines/validator.py`, `tests/test_pipeline_smoke.py` |
| 2026-03-17 | UI cycle kickoff + UI-0 completion | Formalized first full UI implementation map (dark-only, URL->scan->questionnaire->pack->viewer), fixed state machine and screen/data contracts in dedicated spec, and aligned next step to runtime stage API | UI runtime API and frontend implementation are not started yet | None | `docs/UI_V1_SPEC.md`, `docs/MASTER_PLAN_TRACKER.md` |
| 2026-03-18 | UI-1 runtime stage API completed | Implemented staged runtime API (`start_local/start_remote`, `submit_session_answers`) with progress events and questionnaire pause/resume boundary; integrated stage-event logging into existing monitor worker; hardened Windows clone path handling (`core.longpaths=true` + shorter session paths) and added regressions (`43/43`) | UI-2 visual dark shell and questionnaire screen are not implemented yet | None | `src/opack/monitor/service.py`, `src/opack/monitor/ui.py`, `tests/test_monitor_service.py`, `docs/UI_V1_SPEC.md` |
| 2026-03-18 | UI-2 dark launch/progress shell completed | Reworked monitor UI into dark shell with structured launch panel, deterministic stage timeline chips, progress bar/status line bound to runtime events, and questionnaire counters; validated end-to-end stage visibility on `next.js` quick run | In-UI editable questionnaire form and file viewer screens are not implemented yet | None | `src/opack/monitor/ui.py`, `pilot_runs/ui2_stage_smoke_20260318_002052.json`, `docs/UI_V1_SPEC.md` |
| 2026-03-18 | UI-3 in-UI questionnaire step completed | Added one-by-one questionnaire dialog in monitor flow (per-question fields and navigation), integrated submit/cancel behavior in staged run, and added helper coverage for answer parsing; full suite revalidated (`47/47`) | UI-5 hardening scenarios are not implemented yet | None | `src/opack/monitor/ui.py`, `tests/test_monitor_ui.py`, `docs/UI_V1_SPEC.md` |
| 2026-03-18 | UI-4 result dashboard + file viewer completed | Added result tab with key quality metrics, generated pack tree, and inline file preview; validated runtime smoke artifact on `pallets/flask` quick profile | UI-5 hardening scenarios are not implemented yet | None | `src/opack/monitor/ui.py`, `pilot_runs/ui4_smoke_20260318_004810.json`, `docs/UI_V1_SPEC.md` |
| 2026-03-18 | UI-5 UX hardening completed | Connected launch URL validation, runtime remediation hints, blocked-result guidance, and safe binary/truncated file preview handling; expanded UI helper coverage and revalidated full suite (`51/51`) | None | None | `src/opack/monitor/ui.py`, `tests/test_monitor_ui.py`, `docs/UI_V1_SPEC.md` |
| 2026-03-18 | Reference-parity hot plan prepared for tomorrow | Fixed next-day execution plan with strict RP-01..RP-06 scope and measurable acceptance targets focused on quality parity | Execution itself is pending for 2026-03-19 | None | `docs/V1_3_REFERENCE_PARITY_HOT_PLAN.md`, `docs/MASTER_PLAN_TRACKER.md` |

## Archive rule
- Closed tasks remain in history.
- Move closed items to archive section if active list grows.
- Keep evidence references for every closed task.
