# PILOT_RESULTS_V1_2_PHASE2_DEPENDENCY_MAPPER_2026-03-17

## Scope
Execution report for V1.2 `B2` (dependency mapper depth upgrade).

Goals:
1. Increase dependency-map coverage across pilot repos.
2. Improve import resolution for Python package roots, TS aliases, and Go module paths.
3. Keep scanner stability and tests green.

## Implemented changes
- Scanner dependency context added:
  - python package roots discovery (`__init__.py`-based)
  - go module path discovery (`go.mod`)
  - ts/js path aliases discovery (`tsconfig.json` / `jsconfig.json`)
- Source module normalization improved:
  - skip root file pseudo-modules (e.g. `manage.py`)
  - better module extraction for `src/<package>/<submodule>` layout
- Target import resolution improved:
  - Python: package-root aware + relative import handling
  - TS/JS: alias-aware resolution + fallback logic
  - Go: module-path aware internal package resolution
- Go import extraction precision improved:
  - parse `import "..."` and `import (...)` blocks only

## Regression coverage added
In `tests/test_pipeline_smoke.py`:
1. `test_scanner_dependency_map_python_package_root_submodules`
2. `test_scanner_dependency_map_ts_alias_paths`
3. `test_scanner_dependency_map_go_module_path_imports`

## Validation execution
- Unit tests:
  - command: `PYTHONPATH=src python -m unittest discover -s tests -v`
  - result: `27/27` passed
- Pilot dependency scan (same 12 repos x 3 profiles, local workspace snapshot):
  - evidence: `pilot_runs/v12_phase2_dependency_scan_20260317_191535.json`
  - total runs: `36`
  - non-zero dependency runs: `24`
  - coverage ratio: `0.6667`
  - baseline coverage ratio (B0): `0.4167`
  - delta: `+0.25` (`+9` non-zero runs)

## Notable improvements from pilot delta
- New non-zero coverage introduced on previously zero repos:
  - `GO-01`
  - `ND-01`
  - `PY-01`
- Edge volume increased on high-complexity repos (`MX-*`, `ND-*`, `PY-02`) while preserving run stability.
- Remaining zero-coverage repos:
  - `GO-02`, `LD-01`, `LD-02`, `PY-03` (expected candidates for next iteration tuning).

## Phase decision
- B2 status: `completed`.
- Next phase should proceed to B3 (quick-profile runtime guardrails) with B0 baseline as comparison anchor.
