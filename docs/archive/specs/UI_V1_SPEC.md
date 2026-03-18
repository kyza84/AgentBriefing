# UI_V1_SPEC

Updated: 2026-03-18
Status: UI-0, UI-1, UI-2, UI-3, UI-4, UI-5 completed (spec baseline + staged runtime API + dark launch/progress shell + in-UI questionnaire + result/file viewer + UX hardening)

## 1. Purpose
Define the first full user interface for Operating-Pack Builder with a clear path:

1. paste repository URL
2. run scan with visible progress
3. complete adaptive questionnaire in UI
4. generate operating-pack
5. inspect generated files in built-in viewer

The spec is intentionally V1-focused and excludes V2/V3 SaaS/governance scope.

## 2. Product goals for UI V1

1. Remove mandatory terminal usage for the core build flow.
2. Keep user in one continuous UX session from URL input to artifact inspection.
3. Expose stage progress and failures transparently.
4. Keep all user-facing copy in Russian for this cycle.
5. Enforce dark theme only.

## 3. Scope and boundaries

In scope:
1. Local UI for one operator.
2. Single repository run per session.
3. Stage progress visualization.
4. Built-in questionnaire editor (unknown + hypothesis answers).
5. Built-in generated-pack file explorer and preview.

Out of scope:
1. Multi-user accounts and permissions.
2. Cloud queueing and remote workers.
3. Auto-maintenance cron/webhook flows.
4. Cross-run diff analytics and dashboards.

## 4. User flow (target)

1. User opens UI and lands on "Запуск".
2. User enters `repo_url`, optional `git_ref`, selects profile.
3. User starts run and sees stage progress (`clone`, `scan`).
4. When scanner/questionnaire data is ready, user gets interactive questions:
   - unknown answers (free text)
   - hypothesis decisions (`confirm | edit | reject`)
5. User submits questionnaire and starts build continuation.
6. UI executes `generate` and `validate` with progress updates.
7. User gets result summary with quality/blocking/issues and opens generated files in viewer.

## 5. UX state model (UI-0 contract)

Canonical run states:
1. `idle` - form ready, no active run.
2. `preparing_repo` - clone/checkout stage.
3. `scanning` - scanner stage in progress.
4. `awaiting_answers` - questionnaire is displayed and must be completed.
5. `building_pack` - generate + validate in progress.
6. `completed_success` - no blocking status.
7. `completed_blocked` - build produced blocking validation issues.
8. `failed` - technical failure (clone/parse/io/system).

Hard rules:
1. Progress UI must always show current stage and previous completed stages.
2. Transition to `awaiting_answers` must freeze stage execution until submit.
3. Any failure must show failed stage id and remediation hint.

## 6. Screen map (UI-0 contract)

### Screen A: Launch
Goal:
1. Start a run quickly and correctly.

Required controls:
1. `repo_url` input
2. `git_ref` input (default `HEAD`)
3. `profile` selector (`quick`, `balanced`, `strict`)
4. `start` button
5. pilot repo quick-select dropdown

Validation:
1. Empty URL blocks submit.
2. URL format check for `https://github.com/<org>/<repo>`.

### Screen B: Progress
Goal:
1. Provide transparent stage tracking during processing.

Required controls:
1. global progress bar
2. stage timeline with statuses (`pending`, `running`, `done`, `failed`)
3. live log panel
4. cancel button (soft cancel for current session)

### Screen C: Questionnaire
Goal:
1. Resolve unknowns/hypotheses inside UI without external JSON file dependency.

Required controls:
1. question cards ordered by impact and profile budget
2. hypothesis answer widget (`confirm/edit/reject`)
3. unknown answer text widget
4. counters: `answered`, `remaining`, `confidence impact`
5. submit answers button

### Screen D: Result + Files
Goal:
1. Let operator validate output quality and inspect artifacts immediately.

Required controls:
1. quality summary tiles (`quality_score`, `blocking_status`, issue counters)
2. generated pack path
3. tree view of files in generated pack
4. file preview pane (read-only)
5. open-in-folder button
6. rerun button

## 7. Data contract between UI and runtime

UI request payload:
1. `repo_url: str`
2. `git_ref: str`
3. `profile: quick|balanced|strict`
4. `answers_payload: {unknown_answers, hypothesis_answers}`

Progress event contract:
1. `run_id`
2. `state`
3. `stage_id`
4. `message`
5. `percent`
6. `timestamp`

Questionnaire payload contract:
1. `questions[]` from `QuestionnaireEngine.build_questions`
2. per-item stable ids:
   - `question_id`
   - `question_type`
   - `target_id` / `unknown_id`

Result contract:
1. top summary from `VALIDATION_REPORT.json`
2. paths from generated `pack-*` directory
3. file list from pack root

## 8. Visual direction (dark-only)

Mandatory:
1. Dark theme only for V1 UI cycle.
2. High-contrast readability for long logs and JSON previews.
3. Clear stage colors:
   - running: blue
   - done: green
   - failed: red
   - blocked result: amber/red accent

## 9. Error model and UX behavior

Primary error classes:
1. Clone/checkout failure.
2. Scanner stage failure.
3. Questionnaire validation failure.
4. Generator/validator failure.
5. File preview/read error.

Error UX rules:
1. Always show failed stage and short technical reason.
2. Provide one concrete next step in each error card.
3. Keep completed stage outputs inspectable even after blocked result.

## 10. Acceptance criteria by UI phase

### UI-0 (this phase)
1. UX flow, states, screen contracts, and payload contracts documented.
2. Dark-theme-only direction fixed.
3. In/out of scope fixed to avoid V2/V3 scope drift.

### UI-1
1. Runtime stage API and progress events implemented.
2. Questionnaire pause/resume boundary supported by API.
3. Implemented artifacts:
   - `start_remote_repo_session(...)`
   - `start_local_repo_session(...)`
   - `submit_session_answers(...)`
   - progress event contract via `MonitorStageEvent`
4. Evidence:
   - `src/opack/monitor/service.py`
   - `src/opack/monitor/ui.py`
   - `tests/test_monitor_service.py`

### UI-2
1. Launch + progress screens are functional.
2. Stage progress is visible end-to-end for at least one pilot repo.
3. Implemented artifacts:
   - dark visual shell in `monitor-ui` (input panel, progress bar, stage chips, status line, output log)
   - stage-state rendering mapped to runtime events (`preparing_repo`, `scanning`, `awaiting_answers`, `building_pack`, `completed`)
4. Evidence:
   - `src/opack/monitor/ui.py`
   - `pilot_runs/ui2_stage_smoke_20260318_002052.json`

### UI-3
1. Questionnaire screen supports unknown + hypothesis flows.
2. Submit resumes pipeline and reaches result screen.
3. Implemented artifacts:
   - in-UI questionnaire dialog with one-by-one navigation (`Назад` / `Далее`)
   - per-question answer fields (`unknown` text, `hypothesis` decision + detail text)
   - submit/cancel behavior integrated into staged runtime flow
4. Evidence:
   - `src/opack/monitor/ui.py`
   - `tests/test_monitor_ui.py`

### UI-4
1. Result summary and file viewer work for generated pack artifacts.
2. User can inspect docs/json without leaving UI.
3. Implemented artifacts:
   - result tab with quality/blocking/issues summary
   - generated pack tree view and inline file preview pane
4. Evidence:
   - `src/opack/monitor/ui.py`
   - `pilot_runs/ui4_smoke_20260318_004810.json`

### UI-5
1. Negative UX cases covered (bad URL, clone fail, blocked validation, preview read errors).
2. Stability pass completed on pilot repo subset.
3. Implemented artifacts:
   - launch validation for GitHub URL format before run start
   - runtime error hints for common failures (`Filename too long`, clone/auth, stale session, JSON input errors)
   - safe preview renderer for binary and oversized files (`[BINARY FILE]`, `[TRUNCATED]`)
   - explicit blocked-result status and remediation hint in run output
4. Evidence:
   - `src/opack/monitor/ui.py`
   - `tests/test_monitor_ui.py`

## 11. Traceability to existing code

Current baseline references:
1. `src/opack/monitor/ui.py` (legacy Tk monitor)
2. `src/opack/monitor/service.py` (run orchestration for remote/local checks)
3. `src/opack/orchestrators/build_pipeline.py` (scan -> ask -> generate -> validate pipeline)
4. `src/opack/engines/questionnaire.py` (question contract and answer semantics)

This spec does not rewrite core pipeline contracts. It defines the new UI layer around existing runtime.
