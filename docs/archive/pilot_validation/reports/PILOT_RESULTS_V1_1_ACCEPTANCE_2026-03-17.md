# PILOT_RESULTS_V1_1_ACCEPTANCE_2026-03-17

## Scope
V1.1 acceptance matrix after A1-A4 implementation:
- Matrix: `12 repositories x 3 profiles`
- Total runs: `36`
- Profiles: `quick`, `balanced`, `strict`
- Source aggregate: `pilot_runs/acceptance_v1_1_20260317_155513_results.json`
- Baseline for delta: `pilot_runs/release_phase6_20260317_141558_results.json`

## Aggregate summary

| Metric | Value |
|---|---|
| Total runs | 36 |
| Success runs | 36 |
| Blocking runs | 0 |
| Critical runs | 0 |
| Average quality score | 1.00 |
| Median quality score | 1.00 |
| Median run time (s) | 0.619 |
| Total issues | 0 |
| Total scanner warnings | 0 |

## Delta vs V1 release baseline

| Metric | V1 baseline | V1.1 acceptance | Delta |
|---|---:|---:|---:|
| Blocking runs | 0 | 0 | 0 |
| Critical runs | 0 | 0 | 0 |
| Average quality | 1.00 | 1.00 | 0.00 |
| Total issues | 0 | 0 | 0 |
| Total scanner warnings | 0 | 0 | 0 |
| Sum of unknowns (all runs) | 36 | 60 | +24 |
| Median run time (s) | 0.049 | 0.619 | +0.570 |

Notes:
- `unknowns +24` is expected: hypothesis-driven questioning intentionally exposes more explicit confirm/edit/reject items.
- Time increased mostly on first heavy `quick` runs over very large repos due deeper operational extraction (`tests/ci/critical/deps`).

## Operational fact coverage (run-level)

| Signal | Runs with signal | Coverage |
|---|---:|---:|
| `tests_map > 0` | 33 / 36 | 91.7% |
| `ci_pipeline_map > 0` | 30 / 36 | 83.3% |
| `critical_files_map > 0` | 36 / 36 | 100% |
| `module_dependency_map > 0` | 15 / 36 | 41.7% |
| `hypotheses > 0` | 36 / 36 | 100% |

## Profile latency snapshot

| Profile | Runs | Median time (s) | Average time (s) | Average quality |
|---|---:|---:|---:|---:|
| quick | 12 | 5.557 | 96.579 | 1.00 |
| balanced | 12 | 0.151 | 4.246 | 1.00 |
| strict | 12 | 0.135 | 3.822 | 1.00 |

## Repo snapshot (operational signals)

| Repo ID | Stack signal | Runs | Median time (s) | Max tests_map | Max ci_pipeline_map | Max module_dependency_map | Max unknowns |
|---|---|---:|---:|---:|---:|---:|---:|
| GO-01 | go | 3 | 0.044 | 10 | 4 | 0 | 2 |
| GO-02 | go | 3 | 0.020 | 10 | 2 | 0 | 3 |
| LD-01 | python | 3 | 0.013 | 0 | 0 | 0 | 2 |
| LD-02 | unknown | 3 | 0.023 | 1 | 1 | 0 | 3 |
| MX-01 | python,go | 3 | 12.076 | 10 | 0 | 21 | 2 |
| MX-02 | python,node,rust,jvm | 3 | 14.293 | 10 | 44 | 5 | 2 |
| ND-01 | node | 3 | 0.151 | 1 | 4 | 0 | 1 |
| ND-02 | node | 3 | 2.474 | 10 | 1 | 1 | 1 |
| ND-03 | node,rust | 3 | 21.052 | 10 | 33 | 9 | 1 |
| PY-01 | python | 3 | 0.089 | 3 | 5 | 0 | 1 |
| PY-02 | python | 3 | 0.677 | 8 | 19 | 3 | 1 |
| PY-03 | python | 3 | 0.041 | 1 | 6 | 0 | 2 |

## Gate decision
- Gate status: `PASS`.
- A5 acceptance criteria met:
  - `blocking=0`
  - `critical=0`
  - no regressions in quality/issues/warnings vs V1 release baseline
  - operational extraction signals present across the matrix
