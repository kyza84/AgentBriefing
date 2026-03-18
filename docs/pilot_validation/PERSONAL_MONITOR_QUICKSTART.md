# PERSONAL_MONITOR_QUICKSTART

## What this gives you
Personal one-click monitor window:
1. Paste/select repository URL.
2. Choose profile (`quick` / `balanced` / `strict`).
3. Click `Run Check`.
4. Watch dark progress shell with stage timeline.
5. Get validation summary and generated pack path.

## Start command

```powershell
cd D:\earnforme\AgentBriefing
$env:PYTHONPATH='src'
python -m opack.cli monitor-ui
```

## UI fields
- `Pilot repos`: dropdown from `PILOT_REPO_REGISTRY.md`.
- `Repo URL`: custom GitHub link.
- `Git ref`: default `HEAD`.
- `Profile`: check intensity.
- `Answers file`: optional JSON prefill for questionnaire.
- Stage chips + progress bar: live runtime state (`clone -> scan -> questionnaire -> build -> complete`).
- Launch validation: run start is blocked for invalid URL format (`https://github.com/<owner>/<repo>`).

## Questionnaire step
- After scan, monitor opens in-UI questionnaire dialog before build stage.
- Questions are shown one-by-one with dedicated input fields.
- For hypothesis questions use `confirm / edit / reject` plus optional detail text.
- `answers file` is optional and only used as prefill.

## Result + files
- `Результат` tab shows quality/blocking/issues summary.
- Generated pack files are shown in a tree.
- Selecting a file opens inline preview inside the app.
- Binary files are shown as `[BINARY FILE]`.
- Large files are truncated and marked as `[TRUNCATED]`.

## Output shown in the window
- stage events (`preparing_repo`, `scanning`, `awaiting_answers`, `building_pack`, `completed`)
- questionnaire counters (`questionnaire_total`, `unknown`, `hypothesis`)
- run id
- repo commit SHA
- generated pack directory
- blocking status
- quality score
- issue counts
- unknown/resolved unknown counts
- stack/entry/command/environment signals

## Notes
- Monitor creates run data under `.monitor/`.
- Generated packs remain available for manual inspection.
- Common runtime failures show remediation hints directly in the log output.
