# PILOT_RESULTS_RELEASE_PHASE6_2026-03-17

## Scope
Final Phase 6 release acceptance run:
- Matrix: `12 repositories x 3 profiles`
- Total runs: `36`
- Profiles: `quick`, `balanced`, `strict`
- Source aggregate: `pilot_runs/release_phase6_20260317_141558_results.json`

## Aggregate summary

| Metric | Value |
|---|---|
| Total runs | 36 |
| Success runs | 36 |
| Blocking runs | 0 |
| Critical runs | 0 |
| Average quality score | 1.00 |
| Median run time (s) | 0.049 |
| Total issues | 0 |
| Total scanner warnings | 0 |

## Repo-level snapshot

| Repo ID | Stack signal | Runs | Blocking | Median time (s) |
|---|---|---:|---:|---:|
| GO-01 | go | 3 | 0 | 0.039 |
| GO-02 | go | 3 | 0 | 0.017 |
| LD-01 | python | 3 | 0 | 0.019 |
| LD-02 | unknown | 3 | 0 | 0.009 |
| MX-01 | python,go | 3 | 0 | 4.179 |
| MX-02 | python,node,rust,jvm | 3 | 0 | 2.390 |
| ND-01 | node | 3 | 0 | 0.053 |
| ND-02 | node | 3 | 0 | 0.493 |
| ND-03 | node,rust | 3 | 0 | 4.635 |
| PY-01 | python | 3 | 0 | 0.272 |
| PY-02 | python | 3 | 0 | 0.337 |
| PY-03 | python | 3 | 0 | 0.049 |

## Profile latency snapshot

| Profile | Runs | Median time (s) |
|---|---:|---:|
| quick | 12 | 0.162 |
| balanced | 12 | 0.028 |
| strict | 12 | 0.028 |

## Release decision
- Gate status: `PASS`.
- Phase 6 acceptance criteria achieved:
  - `blocking_status=false` in all runs.
  - no critical issues.
  - no scanner warnings in release run matrix.
- V1 builder baseline is ready for release packaging.
