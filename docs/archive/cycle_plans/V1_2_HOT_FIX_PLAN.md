# V1.2 Hot Fix Plan (Post B5)

Updated: 2026-03-17

## Status
1. H1 (P1): completed
2. H2 (P1): completed
3. H3 (P2): completed
4. H4 (P3): completed

## Goal
Close real accuracy/validation gaps discovered after V1.2 B5 release-gate rerun, without widening scope to V2/V3.

## Scope
In scope:
1. Dependency-map accuracy for Python relative imports in `src/*` package layouts.
2. False-positive test readiness when repository has no real test evidence.
3. Validator visibility check for all open unknown IDs (not only the first one).

Out of scope:
1. Full YAML specification compliance (anchors/aliases/tags/custom types) beyond CI extraction needs.

## Prioritized tasks

### H1 (P1): Python relative import dependency resolution
- Status: completed (`2026-03-17`)
- Problem: relative imports like `from .core.utils import ...` can map to structural root (`src`) instead of target module (`core`).
- Target files:
  - `src/opack/engines/scanner.py`
  - `tests/test_pipeline_smoke.py`
- Acceptance:
  1. Relative import case in package-root layout resolves to `core`.
  2. No regression for existing absolute import cases.

### H2 (P1): False-positive test signal without file evidence
- Status: completed (`2026-03-17`)
- Problem: scanner can infer test operability from synthetic defaults even when no tests exist in repo.
- Target files:
  - `src/opack/engines/scanner.py`
  - `tests/test_pipeline_smoke.py`
- Acceptance:
  1. Repo with `pyproject.toml` + app code but no test files does not produce fake `tests_map`.
  2. Validator/reporting exposes test gap via unknown/warning path (non-silent).

### H3 (P2): Validate all `open_unknowns` visibility
- Status: completed (`2026-03-17`)
- Problem: validator currently checks only the first open unknown ID for artifact visibility.
- Target files:
  - `src/opack/engines/validator.py`
  - `tests/test_pipeline_smoke.py`
- Acceptance:
  1. Missing second/third open unknown in artifacts is detected.
  2. Existing passing scenarios with complete unknown visibility remain green.

### H4 (P3): CI parser architecture risk follow-up
- Status: completed (`2026-03-17`)
- Problem: parser was heuristic line-based, not YAML AST.
- Action completed:
  - Added internal YAML AST parser for CI workflows (`on` / `jobs` / `steps`) with safe fallback to legacy parser.
  - Added AST-focused regression tests (block-scalar `run`, inline comments in trigger filters).
  - Verified on complex pilot repo (`MX-02`) with full CI map extraction coverage.
- Acceptance:
  1. AST parser path is active for valid workflow files.
  2. Legacy fallback preserves behavior if AST parse fails.

## Execution order
1. H1 implementation + tests
2. H2 implementation + tests
3. H3 implementation + tests
4. Full regression run (`python -m unittest discover -s tests -q`)
5. Docs/state refresh and report

## Execution result
1. Regression run: `40/40` tests passed (`python -m unittest discover -s tests -q`).
2. Pilot spot-check: `MX-02` balanced profile:
   - `ci_pipeline_count=44`
   - `pipelines_with_triggers=44`
   - `pipelines_with_jobs=44`
3. Evidence:
   - `src/opack/engines/scanner.py`
   - `src/opack/engines/validator.py`
   - `tests/test_pipeline_smoke.py`
