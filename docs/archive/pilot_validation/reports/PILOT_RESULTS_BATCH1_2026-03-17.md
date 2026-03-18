# PILOT_RESULTS_BATCH1_2026-03-17

## Scope
First pilot batch for V1 acceptance:
- Repos: `PY-01`, `ND-01`, `GO-01`
- Profiles: `quick`, `balanced`, `strict`
- Total runs: `9`
- Batch folder: `pilot_runs/batch_20260317_024740`

## Run-level results

| Date | Repo ID | Profile | SHA | Time (s) | Blocking | Quality Score | Issues | Unknowns | Resolved Unknowns | Stacks | Entry Points | Key Commands | Notes |
|---|---|---|---|---:|---|---:|---:|---:|---:|---|---:|---:|---|
| 2026-03-17 | PY-01 | quick | 4cae5d8e411b1e69949d8fae669afeacbd3e5908 | 0.933 | false | 1.00 | 0 | 1 | 1 | python | 5 | 2 | ok |
| 2026-03-17 | PY-01 | balanced | 4cae5d8e411b1e69949d8fae669afeacbd3e5908 | 1.105 | false | 1.00 | 0 | 1 | 1 | python | 5 | 2 | ok |
| 2026-03-17 | PY-01 | strict | 4cae5d8e411b1e69949d8fae669afeacbd3e5908 | 0.886 | false | 1.00 | 0 | 1 | 1 | python | 5 | 2 | ok |
| 2026-03-17 | ND-01 | quick | 6c4249feec8ab40631817c8e7001baf2ed022224 | 1.173 | false | 1.00 | 0 | 1 | 1 | node | 30 | 6 | ok |
| 2026-03-17 | ND-01 | balanced | 6c4249feec8ab40631817c8e7001baf2ed022224 | 1.305 | false | 1.00 | 0 | 1 | 1 | node | 30 | 6 | ok |
| 2026-03-17 | ND-01 | strict | 6c4249feec8ab40631817c8e7001baf2ed022224 | 1.275 | false | 1.00 | 0 | 1 | 1 | node | 30 | 6 | ok |
| 2026-03-17 | GO-01 | quick | d3ffc9985281dcf4d3bef604cce4e662b1a327a6 | 1.365 | false | 1.00 | 0 | 1 | 1 | go | 1 | 11 | ok |
| 2026-03-17 | GO-01 | balanced | d3ffc9985281dcf4d3bef604cce4e662b1a327a6 | 1.158 | false | 1.00 | 0 | 1 | 1 | go | 1 | 11 | ok |
| 2026-03-17 | GO-01 | strict | d3ffc9985281dcf4d3bef604cce4e662b1a327a6 | 0.847 | false | 1.00 | 0 | 1 | 1 | go | 1 | 11 | ok |

## Summary

| Metric | Value |
|---|---|
| Total runs | 9 |
| Success runs | 9 |
| Blocking runs | 0 |
| Median quality score | 1.00 |
| Median time_to_pack_seconds | 1.158 |
| Critical failures | 0 |
| Most frequent issue | none |

## Interpretation
- Primary bottleneck: not observed in this batch (all checks passed).
- Secondary bottleneck: scanner currently returns one workflow unknown by design for all runs.
- Next action: run Batch #2 on `MX-*` and `LD-*` repos to pressure-test edge cases.
