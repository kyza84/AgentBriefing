# PILOT_RESULTS_PHASE5_2026-03-17

## Scope
Targeted Phase 5 validator acceptance run:
- Repositories: `PY-03 (requests)`, `GO-02 (cobra)`, `LD-02 (inih)`
- Profiles: `quick`, `balanced`, `strict`
- Total runs: `9`
- Source aggregate: `pilot_runs/phase5_validation_20260317.json`

## Run-level results

| Date | Repo ID | Profile | SHA | Blocking | Quality | Issues | Critical | Notes |
|---|---|---|---|---|---:|---:|---:|---|
| 2026-03-17 | PY-03 | quick | `0e4ae38f0c93d4f92a96c774bd52c069d12a4798` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | PY-03 | balanced | `0e4ae38f0c93d4f92a96c774bd52c069d12a4798` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | PY-03 | strict | `0e4ae38f0c93d4f92a96c774bd52c069d12a4798` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | GO-02 | quick | `61968e893eee2f27696c2fbc8e34fa5c4afaf7c4` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | GO-02 | balanced | `61968e893eee2f27696c2fbc8e34fa5c4afaf7c4` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | GO-02 | strict | `61968e893eee2f27696c2fbc8e34fa5c4afaf7c4` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | LD-02 | quick | `577ae2dee1f0d9c2d11c7f10375c1715f3d6940c` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | LD-02 | balanced | `577ae2dee1f0d9c2d11c7f10375c1715f3d6940c` | false | 1.00 | 0 | 0 | ok |
| 2026-03-17 | LD-02 | strict | `577ae2dee1f0d9c2d11c7f10375c1715f3d6940c` | false | 1.00 | 0 | 0 | ok |

## Summary

| Metric | Value |
|---|---|
| Total runs | 9 |
| Blocking runs | 0 |
| Average quality score | 1.00 |
| Total issues | 0 |
| Total critical issues | 0 |

## Interpretation
- Phase 5 validator hardening is accepted on targeted external repos and all three decision profiles.
- No blocking regressions after introducing completeness/consistency/applicability rules.
- Remaining note: local repo runs may show info-level `scanner_warnings_present` because historical pilot workspaces are inside the scan root; this is non-blocking and expected.
