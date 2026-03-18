# PILOT_RESULTS_FULL_2026-03-17

## Scope
Full V1 pilot matrix for acceptance:
- Repos: `12` (from `PILOT_REPO_REGISTRY.md`)
- Profiles: `quick`, `balanced`, `strict`
- Total runs: `36`
- Run folder: `pilot_runs/full_20260317_030825`
- Run source file: `pilot_runs/full_20260317_030825_results.json`

## Aggregate summary

| Metric | Value |
|---|---|
| Total runs | 36 |
| Success runs | 36 |
| Blocking runs | 0 |
| Average quality score | 1.00 |
| Median time_to_pack_seconds | 0.414 |
| Min run time (s) | 0.236 |
| Max run time (s) | 6.610 |
| Total issues | 0 |
| Total warnings | 0 |
| Average unknowns | 1.083 |
| Average resolved unknowns | 1.083 |

## Repo-level summary

| Repo ID | Stack signal | Runs | Blocking | Issues | Median time (s) |
|---|---|---:|---:|---:|---:|
| GO-01 | go | 3 | 0 | 0 | 0.282 |
| GO-02 | go | 3 | 0 | 0 | 0.413 |
| LD-01 | python | 3 | 0 | 0 | 0.396 |
| LD-02 | unknown | 3 | 0 | 0 | 0.348 |
| MX-01 | python,go | 3 | 0 | 0 | 6.610 |
| MX-02 | python,node,rust,jvm | 3 | 0 | 0 | 5.125 |
| ND-01 | node | 3 | 0 | 0 | 0.367 |
| ND-02 | node | 3 | 0 | 0 | 0.480 |
| ND-03 | node,rust | 3 | 0 | 0 | 3.653 |
| PY-01 | python | 3 | 0 | 0 | 0.661 |
| PY-02 | python | 3 | 0 | 0 | 0.709 |
| PY-03 | python | 3 | 0 | 0 | 0.290 |

## Profile latency snapshot

| Profile | Runs | Median time (s) |
|---|---:|---:|
| quick | 12 | 0.446 |
| balanced | 12 | 0.390 |
| strict | 12 | 0.405 |

## Interpretation
- Acceptance result: full matrix passed (`36/36`, zero blocking, zero issues).
- Phase gate impact: scanner (Phase 2), questionnaire (Phase 3), and generator acceptance (Phase 4) are validated on the full pilot set.
- Technical note: in an intermediate ND-03 rerun, Windows long-path pressure was observed; final matrix run passed after scanner traversal hardening and long-path-safe run setup.
- Decision per current instruction: Phase 5 remains deferred and will start only after explicit validation sign-off.
