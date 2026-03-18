# PILOT_TEST_PROTOCOL

## Purpose
Standard protocol for running V1 builder against pinned pilot repositories and collecting comparable metrics.

## Preconditions
1. Run from `D:\earnforme\AgentBriefing`.
2. Set Python path for local package:
   - `$env:PYTHONPATH='src'`
3. Use pinned SHA from `PILOT_REPO_REGISTRY.md`.

## Run matrix
For each pilot repo run 3 profiles:
- `quick`
- `balanced`
- `strict`

Total runs for 12 repos:
- `12 * 3 = 36` runs

## Output structure
Recommended layout:

```text
pilot_runs/
  <repo_id>/
    quick/
    balanced/
    strict/
```

Each run should keep:
- generated pack path
- `FACT_MODEL.json`
- `POLICY_MODEL.json`
- `OPERATING_PACK_MANIFEST.json`
- `VALIDATION_REPORT.json`

## Execution command template

```powershell
python -m opack.cli build --repo <pilot-repo-path> --output .\pilot_runs\<repo_id>\<profile> --profile <profile> --answers-file .\examples\answers.sample.json
```

## Metrics to collect (mandatory)
- `time_to_pack_seconds`
- `blocking_status`
- `quality_score`
- `issues_count`
- `unknown_count` (from `FACT_MODEL`)
- `resolved_unknown_count` (from `POLICY_MODEL`)
- `detected_stacks`
- `entry_points_count`
- `key_commands_count`

## Pass criteria for V1 pilot gate
Recommended baseline:
1. `blocking_status=false` for >= 90% runs.
2. `quality_score >= 0.85` median across runs.
3. `issues_count (critical)` = 0 for all runs.
4. No hard crash in scanner/questionnaire/validator.

## Failure triage
- If scanner weak:
  - inspect `FACT_MODEL.json` coverage and warnings.
- If questionnaire weak:
  - inspect `open_unknowns` and `conflict_log`.
- If validator weak:
  - inspect issue distribution by severity.

## Reporting
Use `PILOT_RESULTS_TEMPLATE.md` and keep one row per run.
