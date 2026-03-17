# PERSONAL_MONITOR_QUICKSTART

## What this gives you
Personal one-click monitor window:
1. Paste/select repository URL.
2. Choose profile (`quick` / `balanced` / `strict`).
3. Click `Run Check`.
4. Get full validation summary and pack folder path.

## Start command

```powershell
cd D:\earnforme\AgentBriefing
$env:PYTHONPATH='src'
python -m opack.cli monitor-ui
```

## UI fields
- `Pilot repos`: dropdown from `PILOT_REPO_REGISTRY.md`.
- `Repo URL`: can be custom GitHub link.
- `Git ref`: default `HEAD`.
- `Profile`: check intensity.
- `Answers file`: JSON for questionnaire answers (default sample is auto-used when available).

## Output shown in the window
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
