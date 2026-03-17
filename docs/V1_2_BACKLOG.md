# V1.2 Backlog (Post V1.1 Release)

## Priority P0
1. CI workflow parser hardening.
- Replace line-heuristics with structured YAML traversal.
- Goal: remove noisy trigger tokens and improve trigger/job confidence.
- Success metric: reduce false trigger tokens to near-zero on MX/enterprise repos.

2. Dependency extraction depth.
- Improve language-specific import resolution (Go module paths, Python package roots, TS alias handling).
- Goal: raise dependency-map coverage above current `41.7%` run-level.

3. Quick-profile performance guardrails.
- Add file-count/time budget with progressive deep-scan fallback.
- Goal: cap extreme quick-profile runtime spikes on large monorepos.

## Priority P1
4. Stack detection expansion.
- Add fallback signals beyond root manifests (workspace manifests, lockfile context, language markers).
- Goal: reduce unknown stack cases (`LD-02`-like) in pilot matrix.

5. Hypothesis quality scoring calibration.
- Refine confidence model using validator/confirmation outcomes.
- Goal: reduce unnecessary unknown inflation while preserving safety.

6. Validator operational recall growth.
- Add more should-have-warned scenarios for CI, tests, and fallback entrypoint combinations.
- Goal: keep recall growth measurable without quality-score inflation.

## Priority P2
7. Acceptance automation packaging.
- Convert phase scripts into reusable command entry points for repeatable audits.
- Goal: one-command rerun for acceptance + negative + repeatability bundles.

8. Report usability improvements.
- Add compact per-repo delta dashboards and top-risk summaries in markdown output.

## Exit target for V1.2
- Keep `blocking=0` and `critical=0` on full matrix.
- Improve dependency-map and CI-parsing accuracy.
- Improve quick-profile runtime distribution on largest repos.
