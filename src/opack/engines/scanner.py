import json
import os
import posixpath
import re
import time
from pathlib import Path

from opack.contracts.models import (
    CiJobFact,
    CiPipelineFact,
    CriticalFileFact,
    FactModel,
    HypothesisItem,
    ModuleDependencyFact,
    ModuleFact,
    TestSuiteFact,
    UnknownItem,
)

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


IGNORE_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "out",
    ".monitor",
    "pilot_workspace",
    "pilot_runs",
}

CI_EVENT_IGNORE_KEYS = {
    "inputs",
    "outputs",
}

CI_TRIGGER_FILTER_KEYS = {
    "branches",
    "branches-ignore",
    "paths",
    "paths-ignore",
    "tags",
    "tags-ignore",
    "types",
}

CI_CRITICAL_KEYWORDS = (
    "deploy",
    "release",
    "publish",
    "docker push",
    "terraform apply",
)

CI_RELEASE_JOB_HINTS = (
    "deploy",
    "release",
    "publish",
    "production",
    "prod",
)

CRITICAL_FILE_RULES = [
    (".github/workflows/", "ci-pipeline", "high"),
    ("dockerfile", "runtime-environment", "high"),
    ("docker-compose.yml", "runtime-orchestration", "high"),
    ("docker-compose.yaml", "runtime-orchestration", "high"),
    ("compose.yml", "runtime-orchestration", "high"),
    ("compose.yaml", "runtime-orchestration", "high"),
    ("pyproject.toml", "python-dependencies", "high"),
    ("requirements.txt", "python-dependencies", "high"),
    ("package.json", "node-dependencies", "high"),
    ("go.mod", "go-dependencies", "high"),
    ("cargo.toml", "rust-dependencies", "high"),
    ("pom.xml", "jvm-dependencies", "high"),
    ("build.gradle", "jvm-dependencies", "high"),
    ("build.gradle.kts", "jvm-dependencies", "high"),
    (".env", "runtime-configuration", "high"),
    (".env.example", "runtime-configuration", "medium"),
]

LOW_RELEVANCE_ENTRYPOINT_PREFIXES = (
    ".github/",
    "examples/",
    "example/",
    "test/",
    "tests/",
    "bench/",
)

LOW_RELEVANCE_COMMAND_MARKERS = (
    "bench",
    "benchmark",
)

DEPENDENCY_FILE_LIMIT_BY_PROFILE = {
    "quick": 1200,
    "balanced": 12000,
    "strict": 20000,
}

PROFILE_SCAN_GUARDRAILS: dict[str, dict[str, float | int]] = {
    "quick": {
        "time_budget_sec": 8.0,
        "repo_file_soft_limit": 15000,
        "max_ci_workflows": 35,
        "max_dependency_total_bytes": 25_000_000,
        "max_dependency_file_bytes": 350_000,
    },
    "balanced": {
        "time_budget_sec": 28.0,
        "repo_file_soft_limit": 60000,
        "max_ci_workflows": 120,
        "max_dependency_total_bytes": 120_000_000,
        "max_dependency_file_bytes": 800_000,
    },
    "strict": {
        "time_budget_sec": 45.0,
        "repo_file_soft_limit": 120000,
        "max_ci_workflows": 220,
        "max_dependency_total_bytes": 260_000_000,
        "max_dependency_file_bytes": 1_500_000,
    },
}

TIME_BUDGET_GRACE_RATIO = 0.02
TIME_BUDGET_GRACE_MIN_SEC = 0.2
TIME_BUDGET_GRACE_MAX_SEC = 0.75


class ScannerEngine:
    """V1.1 scanner: structural and operational fact extraction."""

    def scan(self, repo_path: Path, profile: str = "balanced") -> FactModel:
        scan_started_at = time.perf_counter()
        repo = repo_path.resolve()
        files, walk_warnings = self._collect_files(repo)
        file_names = {p.name.lower() for p in files}
        rel_files = [p.relative_to(repo).as_posix() for p in files]
        warnings: list[str] = list(walk_warnings)
        guardrail_state = self._init_guardrail_state(profile=profile, file_count=len(files))
        if guardrail_state["activated"]:
            warnings.append(
                "Guardrail: repository file count exceeds profile soft limit; deep scan stages may run in sampled mode."
            )

        detected_stacks = self._detect_stacks(file_names)
        modules = self._collect_modules(repo, files)
        entry_points = self._rank_entry_points(self._detect_entry_points(repo, rel_files, file_names))
        environments = self._detect_environments(file_names, rel_files)
        key_commands, command_warnings = self._detect_commands(repo, file_names)
        key_commands = self._rank_key_commands(key_commands)
        warnings.extend(command_warnings)
        external_integrations = self._detect_external_integrations(file_names, rel_files)
        tests_map = self._detect_tests(
            rel_files=rel_files,
            detected_stacks=detected_stacks,
            key_commands=key_commands,
        )
        ci_pipeline_map = self._detect_ci_pipelines(
            repo=repo,
            rel_files=rel_files,
            profile=profile,
            guardrail_state=guardrail_state,
            scan_started_at=scan_started_at,
            warnings=warnings,
        )
        critical_files_map = self._detect_critical_files(rel_files=rel_files)
        module_dependency_map = self._detect_module_dependencies(
            repo=repo,
            files=files,
            modules=modules,
            profile=profile,
            guardrail_state=guardrail_state,
            scan_started_at=scan_started_at,
            warnings=warnings,
        )
        hypotheses = self._build_hypotheses(
            entry_points=entry_points,
            key_commands=key_commands,
            tests_map=tests_map,
            ci_pipeline_map=ci_pipeline_map,
        )
        unknowns = self._build_unknowns(
            entry_points=entry_points,
            key_commands=key_commands,
            tests_map=tests_map,
            hypotheses=hypotheses,
        )
        self._apply_guardrail_unknowns(hypotheses=hypotheses, unknowns=unknowns, guardrail_state=guardrail_state)

        confidence_breakdown = self._confidence(
            file_count=len(files),
            stacks=detected_stacks,
            entry_points=entry_points,
            key_commands=key_commands,
            tests_map=tests_map,
            ci_pipeline_map=ci_pipeline_map,
            warnings=warnings,
        )
        operational_confidence = self._operational_confidence(
            tests_map=tests_map,
            ci_pipeline_map=ci_pipeline_map,
            critical_files_map=critical_files_map,
            module_dependency_map=module_dependency_map,
            hypotheses=hypotheses,
        )
        confidence_breakdown["operational_confidence"] = operational_confidence.get("overall", 0.0)
        confidence_overall = (
            0.3 * confidence_breakdown["coverage_confidence"]
            + 0.3 * confidence_breakdown["signal_confidence"]
            + 0.2 * confidence_breakdown["coherence_confidence"]
            + 0.2 * confidence_breakdown["operational_confidence"]
        )

        if not files:
            warnings.append("No files found during scan.")

        return FactModel(
            repo_id=str(repo),
            detected_stacks=detected_stacks,
            modules=modules,
            entry_points=entry_points,
            environments=environments,
            key_commands=key_commands,
            external_integrations=external_integrations,
            tests_map=tests_map,
            ci_pipeline_map=ci_pipeline_map,
            critical_files_map=critical_files_map,
            module_dependency_map=module_dependency_map,
            hypotheses=hypotheses,
            unknowns=unknowns,
            confidence_overall=round(confidence_overall, 3),
            confidence_breakdown=confidence_breakdown,
            operational_confidence=operational_confidence,
            scan_guardrails=self._public_guardrail_state(guardrail_state),
            scanner_warnings=warnings,
        )

    def _collect_files(self, repo: Path) -> tuple[list[Path], list[str]]:
        files: list[Path] = []
        warnings: list[str] = []
        ignored_lower = {name.lower() for name in IGNORE_DIR_NAMES}

        def _onerror(exc: OSError) -> None:
            warnings.append(f"Walk warning: {exc}")

        for root, dirs, filenames in os.walk(repo, topdown=True, onerror=_onerror):
            dirs[:] = sorted((d for d in dirs if d.lower() not in ignored_lower), key=str.lower)
            for name in sorted(filenames, key=str.lower):
                path = Path(root) / name
                # Apply ignore rules only to the path inside the scanned repository.
                rel_parts = path.relative_to(repo).parts
                if any(part.lower() in ignored_lower for part in rel_parts):
                    continue
                files.append(path)
        return files, warnings

    def _init_guardrail_state(self, profile: str, file_count: int) -> dict[str, object]:
        defaults = PROFILE_SCAN_GUARDRAILS["balanced"]
        config = PROFILE_SCAN_GUARDRAILS.get(profile, defaults)
        time_budget_sec = float(config.get("time_budget_sec", defaults["time_budget_sec"]))
        time_budget_grace_sec = min(
            TIME_BUDGET_GRACE_MAX_SEC,
            max(TIME_BUDGET_GRACE_MIN_SEC, time_budget_sec * TIME_BUDGET_GRACE_RATIO),
        )
        state: dict[str, object] = {
            "profile": profile,
            "time_budget_sec": time_budget_sec,
            "time_budget_grace_sec": round(time_budget_grace_sec, 3),
            "repo_file_soft_limit": int(config.get("repo_file_soft_limit", defaults["repo_file_soft_limit"])),
            "max_ci_workflows": int(config.get("max_ci_workflows", defaults["max_ci_workflows"])),
            "max_dependency_total_bytes": int(
                config.get("max_dependency_total_bytes", defaults["max_dependency_total_bytes"])
            ),
            "max_dependency_file_bytes": int(
                config.get("max_dependency_file_bytes", defaults["max_dependency_file_bytes"])
            ),
            "activated": False,
            "reasons": [],
            "skipped": [],
            "repo_file_count": file_count,
        }
        soft_limit = int(state["repo_file_soft_limit"])
        if file_count > soft_limit:
            self._activate_guardrail(
                guardrail_state=state,
                reason="repo_file_soft_limit_exceeded",
                skipped_marker=f"repo_files:{file_count - soft_limit}",
            )
        return state

    def _activate_guardrail(
        self,
        guardrail_state: dict[str, object],
        reason: str,
        skipped_marker: str = "",
    ) -> None:
        guardrail_state["activated"] = True
        reasons = guardrail_state.setdefault("reasons", [])
        if isinstance(reasons, list) and reason and reason not in reasons:
            reasons.append(reason)
        skipped = guardrail_state.setdefault("skipped", [])
        if isinstance(skipped, list) and skipped_marker:
            skipped.append(skipped_marker)

    def _time_budget_exceeded(self, guardrail_state: dict[str, object], scan_started_at: float) -> bool:
        budget = float(guardrail_state.get("time_budget_sec", 0.0))
        if budget <= 0:
            return False
        grace_sec = max(0.0, float(guardrail_state.get("time_budget_grace_sec", 0.0)))
        elapsed = time.perf_counter() - scan_started_at
        return elapsed >= (budget + grace_sec)

    def _public_guardrail_state(self, guardrail_state: dict[str, object]) -> dict[str, object]:
        return {
            "profile": guardrail_state.get("profile", "unknown"),
            "activated": bool(guardrail_state.get("activated", False)),
            "time_budget_sec": float(guardrail_state.get("time_budget_sec", 0.0)),
            "time_budget_grace_sec": float(guardrail_state.get("time_budget_grace_sec", 0.0)),
            "repo_file_count": int(guardrail_state.get("repo_file_count", 0)),
            "repo_file_soft_limit": int(guardrail_state.get("repo_file_soft_limit", 0)),
            "max_ci_workflows": int(guardrail_state.get("max_ci_workflows", 0)),
            "max_dependency_total_bytes": int(guardrail_state.get("max_dependency_total_bytes", 0)),
            "max_dependency_file_bytes": int(guardrail_state.get("max_dependency_file_bytes", 0)),
            "reasons": list(guardrail_state.get("reasons", [])),
            "skipped": list(guardrail_state.get("skipped", [])),
        }

    def _apply_guardrail_unknowns(
        self,
        hypotheses: list[HypothesisItem],
        unknowns: list[UnknownItem],
        guardrail_state: dict[str, object],
    ) -> None:
        if not guardrail_state.get("activated"):
            return

        if not any(item.hypothesis_id == "h_scan_budget_001" for item in hypotheses):
            hypotheses.append(
                HypothesisItem(
                    hypothesis_id="h_scan_budget_001",
                    area="scanner",
                    claim=(
                        "Profile scan guardrails limited deep extraction "
                        "(CI detail and/or dependency depth may be sampled)."
                    ),
                    confidence=0.58,
                    evidence=[
                        f"guardrail_reasons={','.join(str(x) for x in guardrail_state.get('reasons', []))}",
                    ],
                    requires_confirmation=True,
                    suggested_question=(
                        "Подтвердите, что для этой репы достаточно sampled-режима; "
                        "или запустить `balanced/strict` для полного скана?"
                    ),
                )
            )

        if not any(item.unknown_id == "u_scan_budget_001" for item in unknowns):
            unknowns.append(
                UnknownItem(
                    unknown_id="u_scan_budget_001",
                    area="scanner",
                    description=(
                        "Scan guardrails were activated, so deep operational facts may be incomplete "
                        "for this run profile."
                    ),
                    impact_level="medium",
                    suggested_question=(
                        "Нужен ли полный перескан (`balanced/strict`) перед критичными изменениями?"
                    ),
                )
            )

    def _prioritize_workflow_files(self, workflow_files: list[str]) -> list[str]:
        def score(path: str) -> tuple[int, int, str]:
            lower = path.lower()
            priority = 0
            if any(token in lower for token in ("ci", "build", "test")):
                priority += 2
            if any(token in lower for token in ("deploy", "release", "publish", "prod")):
                priority += 3
            if "lint" in lower:
                priority += 1
            return (-priority, len(path), path)

        return sorted(set(workflow_files), key=score)

    def _collect_modules(self, repo: Path, files: list[Path]) -> list[ModuleFact]:
        top_level_dirs = sorted({p.parent.relative_to(repo).parts[0] for p in files if p.parent != repo})
        return [ModuleFact(name=d, path=str(repo / d), kind="directory") for d in top_level_dirs]

    def _detect_stacks(self, file_names: set[str]) -> list[str]:
        stacks: list[str] = []
        if {"pyproject.toml", "requirements.txt", "setup.py"} & file_names:
            stacks.append("python")
        if {"package.json", "pnpm-lock.yaml", "yarn.lock"} & file_names:
            stacks.append("node")
        if "go.mod" in file_names:
            stacks.append("go")
        if "cargo.toml" in file_names:
            stacks.append("rust")
        if {"pom.xml", "build.gradle", "build.gradle.kts"} & file_names:
            stacks.append("jvm")
        return stacks

    def _detect_entry_points(self, repo: Path, rel_files: list[str], file_names: set[str]) -> list[str]:
        candidates = []
        for rel in rel_files:
            lower = rel.lower()
            if lower.endswith(("main.py", "app.py", "server.py", "manage.py", "main.ts", "main.js", "index.ts", "index.js")):
                candidates.append(rel)
            if lower.startswith("cmd/") and lower.endswith(".go"):
                candidates.append(rel)

        # Read python console script entry points from pyproject if available.
        pyproject = repo / "pyproject.toml"
        if pyproject.exists() and tomllib is not None:
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                scripts = data.get("project", {}).get("scripts", {})
                for name in scripts.keys():
                    candidates.append(f"pyproject:script:{name}")
            except Exception:
                pass

        # Read node "main" and "bin" entry hints from package.json.
        package_json = repo / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                if isinstance(data.get("main"), str):
                    candidates.append(f"package.json:main:{data['main']}")
                if isinstance(data.get("bin"), dict):
                    for name, target in data["bin"].items():
                        candidates.append(f"package.json:bin:{name}->{target}")
            except Exception:
                pass

        if not candidates and "readme.md" in file_names:
            candidates.append("README.md (manual entrypoint reference)")
        return sorted(set(candidates))

    def _rank_entry_points(self, entry_points: list[str]) -> list[str]:
        def score(value: str) -> int:
            lower = value.lower()
            base = Path(lower.split(":", 1)[-1]).name
            total = 0
            if "manual entrypoint reference" in lower:
                total -= 5
            if base in {"main.py", "app.py", "server.py", "manage.py", "main.ts", "main.js", "index.ts", "index.js"}:
                total += 5
            if lower.startswith(("src/", "app/", "cmd/")):
                total += 2
            if any(lower.startswith(prefix) for prefix in LOW_RELEVANCE_ENTRYPOINT_PREFIXES):
                total -= 3
            if "/test" in f"/{lower}" or "/bench" in f"/{lower}":
                total -= 2
            if "pyproject:script:" in lower or "package.json:bin:" in lower:
                total += 1
            return total

        unique = sorted(set(entry_points))
        return sorted(unique, key=lambda item: (-score(item), len(item), item))

    def _detect_environments(self, file_names: set[str], rel_files: list[str]) -> list[str]:
        env = []
        if "dockerfile" in file_names:
            env.append("docker")
        if {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"} & file_names:
            env.append("docker-compose")
        if ".env" in file_names or ".env.example" in file_names:
            env.append("dotenv")
        if ".tool-versions" in file_names:
            env.append("asdf")
        if ".nvmrc" in file_names:
            env.append("nvm")
        if ".python-version" in file_names:
            env.append("pyenv")
        if any(path.startswith(".github/workflows/") for path in rel_files):
            env.append("github-actions")
        return sorted(set(env))

    def _detect_commands(self, repo: Path, file_names: set[str]) -> tuple[list[str], list[str]]:
        commands: list[str] = []
        warnings: list[str] = []

        makefile = repo / "Makefile"
        if makefile.exists():
            try:
                for line in makefile.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and ":" in line and not line.startswith(("#", ".", "\t")):
                        target = line.split(":", 1)[0].strip()
                        if target and " " not in target:
                            commands.append(f"make {target}")
            except Exception as exc:
                warnings.append(f"Failed to parse Makefile: {exc}")

        package_json = repo / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                if isinstance(scripts, dict):
                    for name in scripts.keys():
                        commands.append(f"npm run {name}")
            except Exception as exc:
                warnings.append(f"Failed to parse package.json scripts: {exc}")

        pyproject = repo / "pyproject.toml"
        if pyproject.exists() and tomllib is not None:
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                scripts = data.get("project", {}).get("scripts", {})
                if isinstance(scripts, dict):
                    for name in scripts.keys():
                        commands.append(name)
            except Exception as exc:
                warnings.append(f"Failed to parse pyproject scripts: {exc}")

        if "requirements.txt" in file_names:
            commands.append("pip install -r requirements.txt")
        if "pyproject.toml" in file_names:
            commands.append("python -m unittest discover -s tests -v")
        if "go.mod" in file_names:
            commands.append("go test ./...")
        if "cargo.toml" in file_names:
            commands.append("cargo test")
        if "package.json" in file_names and not any("npm run test" in c for c in commands):
            commands.append("npm run test")

        return sorted(set(commands)), warnings

    def _rank_key_commands(self, commands: list[str]) -> list[str]:
        def score(cmd: str) -> int:
            lower = cmd.lower()
            total = 0
            if self._is_test_command(lower):
                total += 6
            if "build" in lower:
                total += 2
            if "lint" in lower:
                total += 1
            if any(marker in lower for marker in LOW_RELEVANCE_COMMAND_MARKERS):
                total -= 3
            if any(token in lower for token in ("dev", "start", "serve")):
                total -= 1
            return total

        unique = sorted(set(commands))
        return sorted(unique, key=lambda value: (-score(value), len(value), value))

    def _is_test_command(self, command: str) -> bool:
        lower = command.lower()
        return any(token in lower for token in ("test", "pytest", "unittest", "go test", "cargo test"))

    def _detect_external_integrations(self, file_names: set[str], rel_files: list[str]) -> list[str]:
        integrations = []
        if "dockerfile" in file_names:
            integrations.append("docker")
        if "terraform.tf" in file_names or "main.tf" in file_names:
            integrations.append("terraform")
        if any(path.startswith(".github/workflows/") for path in rel_files):
            integrations.append("github-actions")
        return sorted(set(integrations))

    def _detect_tests(self, rel_files: list[str], detected_stacks: list[str], key_commands: list[str]) -> list[TestSuiteFact]:
        test_roots: set[str] = set()
        frameworks: set[str] = set()
        inferred_roots: set[str] = set()

        for rel in rel_files:
            lower = rel.lower()
            if self._is_test_file(lower):
                test_roots.add(self._test_root(rel))

            if lower.endswith(("pytest.ini", "tox.ini")) or lower.endswith("/conftest.py"):
                frameworks.add("pytest")
            if "jest.config" in lower:
                frameworks.add("jest")
            if "vitest.config" in lower:
                frameworks.add("vitest")
            if lower.endswith("_test.go"):
                frameworks.add("go-test")

        for command in key_commands:
            lower = command.lower()
            if "pytest" in lower:
                frameworks.add("pytest")
            elif "unittest" in lower:
                frameworks.add("unittest")
            elif "npm run test" in lower or "jest" in lower:
                frameworks.add("jest")
            elif "go test" in lower:
                frameworks.add("go-test")
            elif "cargo test" in lower:
                frameworks.add("rust-test")

        if "python" in detected_stacks and test_roots and not frameworks:
            frameworks.add("python-test")
        if "node" in detected_stacks and test_roots and not frameworks:
            frameworks.add("node-test")

        if not test_roots and not frameworks:
            return []

        if not test_roots:
            test_roots.add("tests")
            inferred_roots.add("tests")
        if not frameworks:
            frameworks.add("unknown-test")

        command_candidates = [cmd for cmd in key_commands if self._is_test_command(cmd)]
        if not command_candidates:
            defaults: list[str] = []
            if any(name in frameworks for name in {"pytest", "unittest", "python-test"}):
                defaults.append("python -m unittest discover -s tests -v")
            if any(name in frameworks for name in {"jest", "vitest", "node-test"}):
                defaults.append("npm run test")
            if "go-test" in frameworks:
                defaults.append("go test ./...")
            if "rust-test" in frameworks:
                defaults.append("cargo test")
            command_candidates = defaults

        primary_framework = "mixed" if len(frameworks) > 1 else sorted(frameworks)[0]
        suites: list[TestSuiteFact] = []
        for idx, path in enumerate(sorted(test_roots)[:10], start=1):
            confidence = 0.85 if "test" in path.lower() else 0.65
            if path in inferred_roots:
                confidence = min(confidence, 0.55)
            suites.append(
                TestSuiteFact(
                    suite_id=f"t_{idx:03d}",
                    path=path,
                    framework=primary_framework,
                    command_candidates=command_candidates[:5],
                    confidence=round(confidence, 3),
                )
            )
        return suites

    def _is_test_file(self, lower_rel_path: str) -> bool:
        parts = lower_rel_path.split("/")
        name = parts[-1]
        if any(part in {"test", "tests", "__tests__"} for part in parts):
            return True
        if name.startswith("test_") and name.endswith(".py"):
            return True
        if name.endswith("_test.py") or name.endswith("_test.go"):
            return True
        if name.endswith((".spec.js", ".spec.ts", ".test.js", ".test.ts", ".test.tsx", ".spec.tsx")):
            return True
        return False

    def _test_root(self, rel_path: str) -> str:
        parts = Path(rel_path).parts
        for idx, part in enumerate(parts):
            if part.lower() in {"test", "tests", "__tests__"}:
                return "/".join(parts[: idx + 1])
        parent = Path(rel_path).parent.as_posix()
        return parent if parent != "." else rel_path

    def _detect_ci_pipelines(
        self,
        repo: Path,
        rel_files: list[str],
        profile: str,
        guardrail_state: dict[str, object],
        scan_started_at: float,
        warnings: list[str],
    ) -> list[CiPipelineFact]:
        workflow_files = [
            rel
            for rel in rel_files
            if rel.lower().startswith(".github/workflows/") and rel.lower().endswith((".yml", ".yaml"))
        ]
        workflow_files = self._prioritize_workflow_files(workflow_files)

        max_ci_workflows = int(guardrail_state.get("max_ci_workflows", len(workflow_files)))
        if len(workflow_files) > max_ci_workflows:
            skipped_count = len(workflow_files) - max_ci_workflows
            workflow_files = workflow_files[:max_ci_workflows]
            self._activate_guardrail(
                guardrail_state=guardrail_state,
                reason="ci_workflow_cap",
                skipped_marker=f"ci_workflows:{skipped_count}",
            )
            warnings.append(
                f"Guardrail: CI workflow scan capped to {max_ci_workflows} files for profile `{profile}`; "
                f"skipped {skipped_count} workflow file(s)."
            )

        pipelines: list[CiPipelineFact] = []
        for rel in sorted(workflow_files):
            if self._time_budget_exceeded(guardrail_state=guardrail_state, scan_started_at=scan_started_at):
                self._activate_guardrail(
                    guardrail_state=guardrail_state,
                    reason="time_budget_exceeded_before_ci_scan",
                    skipped_marker="ci_workflows:time_budget",
                )
                warnings.append("Guardrail: CI workflow scan stopped due to time budget.")
                break

            file_path = repo / rel
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = content.splitlines()
            name = self._extract_workflow_name(lines) or Path(rel).stem
            triggers, trigger_filters = self._extract_workflow_events(lines)
            jobs = self._extract_workflow_jobs(lines)
            critical_steps = self._extract_ci_critical_steps(lines=lines, jobs=jobs)
            confidence = 0.5
            if triggers:
                confidence += 0.15
            if trigger_filters:
                confidence += 0.05
            if jobs:
                confidence += 0.15
            if critical_steps:
                confidence += 0.10
            pipelines.append(
                CiPipelineFact(
                    provider="github-actions",
                    file=rel,
                    name=name,
                    triggers=triggers,
                    trigger_filters=trigger_filters,
                    jobs=jobs,
                    critical_steps=critical_steps[:12],
                    confidence=round(min(0.95, confidence), 3),
                )
            )
        return pipelines

    def _extract_workflow_name(self, lines: list[str]) -> str:
        for line in lines[:80]:
            match = re.match(r"^\s*name:\s*(.+?)\s*$", line)
            if match:
                return match.group(1).strip("'\"")
        return ""

    def _extract_workflow_events(self, lines: list[str]) -> tuple[list[str], dict[str, list[str]]]:
        root_on = self._extract_root_key_data(lines=lines, key="on")
        if root_on is None:
            return [], {}
        inline_value, block_lines = root_on

        triggers: set[str] = set()
        trigger_filters: dict[str, list[str]] = {}

        inline_triggers, inline_filters = self._parse_on_inline(inline_value)
        triggers.update(inline_triggers)
        self._merge_trigger_filters(trigger_filters, inline_filters)

        block_triggers, block_filters = self._parse_on_block(block_lines)
        triggers.update(block_triggers)
        self._merge_trigger_filters(trigger_filters, block_filters)

        normalized_filters = {
            key: sorted(set(values))
            for key, values in trigger_filters.items()
            if values
        }
        return sorted(triggers), normalized_filters

    def _extract_workflow_jobs(self, lines: list[str]) -> list[CiJobFact]:
        root_jobs = self._extract_root_key_data(lines=lines, key="jobs")
        if root_jobs is None:
            return []
        inline_value, block_lines = root_jobs

        jobs: list[CiJobFact] = []
        seen_job_ids: set[str] = set()

        cleaned_inline = inline_value.strip()
        if cleaned_inline.startswith("{") and cleaned_inline.endswith("}"):
            entries = self._split_top_level(cleaned_inline[1:-1], ",")
            for entry in entries:
                pair = self._split_key_value_top_level(entry)
                if pair is None:
                    continue
                job_id = self._normalize_ci_token(pair[0])
                if not job_id or not re.match(r"^[a-z0-9_-]+$", job_id):
                    continue
                if job_id in seen_job_ids:
                    continue
                seen_job_ids.add(job_id)
                jobs.append(CiJobFact(job_id=job_id, name=job_id))

        content_indent = self._first_content_indent(block_lines)
        if content_indent is None:
            return jobs

        idx = 0
        while idx < len(block_lines):
            line = block_lines[idx]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                idx += 1
                continue

            indent = len(line) - len(line.lstrip(" "))
            if indent != content_indent:
                idx += 1
                continue

            pair = self._split_key_value_top_level(stripped)
            if pair is None:
                idx += 1
                continue

            job_id = self._normalize_ci_token(pair[0])
            if not job_id or not re.match(r"^[a-z0-9_-]+$", job_id):
                idx += 1
                continue

            idx += 1
            job_block: list[str] = []
            while idx < len(block_lines):
                nested = block_lines[idx]
                nested_stripped = nested.strip()
                if nested_stripped and not nested_stripped.startswith("#"):
                    nested_indent = len(nested) - len(nested.lstrip(" "))
                    if nested_indent <= content_indent:
                        break
                job_block.append(nested)
                idx += 1

            if job_id in seen_job_ids:
                continue

            seen_job_ids.add(job_id)
            critical_steps = self._extract_job_critical_steps(job_id=job_id, job_block=job_block)
            jobs.append(
                CiJobFact(
                    job_id=job_id,
                    name=job_id,
                    critical_steps=critical_steps[:8],
                )
            )

        return jobs

    def _extract_ci_critical_steps(self, lines: list[str], jobs: list[CiJobFact]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for job in jobs:
            for step in job.critical_steps:
                cleaned = step.strip()
                if not cleaned or cleaned in seen:
                    continue
                seen.add(cleaned)
                result.append(cleaned[:180])

        for line in lines:
            cleaned = line.strip()
            lowered = cleaned.lower()
            if not cleaned or cleaned in seen:
                continue
            if not any(keyword in lowered for keyword in CI_CRITICAL_KEYWORDS):
                continue
            if not re.match(r"^(?:-\s*)?(?:run|uses):\s+", cleaned):
                continue
            seen.add(cleaned)
            result.append(cleaned[:180])
        return result

    def _extract_root_key_data(self, lines: list[str], key: str) -> tuple[str, list[str]] | None:
        pattern = re.compile(rf"^\s*['\"]?{re.escape(key)}['\"]?\s*:(.*)$", flags=re.IGNORECASE)
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))
            if indent != 0:
                continue

            match = pattern.match(line)
            if not match:
                continue

            inline_value = match.group(1).strip()
            nested_block = self._collect_indented_block(lines=lines, start_idx=idx, base_indent=indent)
            return inline_value, nested_block
        return None

    def _collect_indented_block(self, lines: list[str], start_idx: int, base_indent: int) -> list[str]:
        block: list[str] = []
        for raw in lines[start_idx + 1 :]:
            stripped = raw.strip()
            current_indent = len(raw) - len(raw.lstrip(" "))
            if stripped and current_indent <= base_indent:
                break
            block.append(raw)
        return block

    def _first_content_indent(self, lines: list[str]) -> int | None:
        content_indents = [
            len(line) - len(line.lstrip(" "))
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        if not content_indents:
            return None
        return min(content_indents)

    def _parse_on_inline(self, inline_value: str) -> tuple[set[str], dict[str, list[str]]]:
        triggers: set[str] = set()
        trigger_filters: dict[str, list[str]] = {}
        cleaned = inline_value.strip()
        if not cleaned:
            return triggers, trigger_filters

        if cleaned.startswith("[") and cleaned.endswith("]"):
            for item in self._parse_yaml_list_literal(cleaned):
                event_name = self._normalize_ci_token(item)
                if self._is_ci_event_token(event_name):
                    triggers.add(event_name)
            return triggers, trigger_filters

        if cleaned.startswith("{") and cleaned.endswith("}"):
            entries = self._split_top_level(cleaned[1:-1], ",")
            for entry in entries:
                pair = self._split_key_value_top_level(entry)
                if pair is None:
                    continue
                event_name = self._normalize_ci_token(pair[0])
                if not self._is_ci_event_token(event_name):
                    continue
                triggers.add(event_name)
                event_filters = self._parse_event_inline_filters(pair[1])
                if event_filters:
                    trigger_filters[event_name] = sorted(set(event_filters))
            return triggers, trigger_filters

        event_name = self._normalize_ci_token(cleaned)
        if self._is_ci_event_token(event_name):
            triggers.add(event_name)
        return triggers, trigger_filters

    def _parse_on_block(self, block_lines: list[str]) -> tuple[set[str], dict[str, list[str]]]:
        triggers: set[str] = set()
        trigger_filters: dict[str, list[str]] = {}

        content_indent = self._first_content_indent(block_lines)
        if content_indent is None:
            return triggers, trigger_filters

        idx = 0
        while idx < len(block_lines):
            line = block_lines[idx]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                idx += 1
                continue

            indent = len(line) - len(line.lstrip(" "))
            if indent != content_indent:
                idx += 1
                continue

            event_name = ""
            inline_value = ""

            if stripped.startswith("-"):
                candidate = stripped.lstrip("-").strip()
                candidate = candidate.split(":", 1)[0].strip()
                event_name = self._normalize_ci_token(candidate)
            else:
                pair = self._split_key_value_top_level(stripped)
                if pair is not None:
                    event_name = self._normalize_ci_token(pair[0])
                    inline_value = pair[1].strip()

            if not self._is_ci_event_token(event_name):
                idx += 1
                continue

            triggers.add(event_name)
            idx += 1

            event_block: list[str] = []
            while idx < len(block_lines):
                nested = block_lines[idx]
                nested_stripped = nested.strip()
                if nested_stripped and not nested_stripped.startswith("#"):
                    nested_indent = len(nested) - len(nested.lstrip(" "))
                    if nested_indent <= content_indent:
                        break
                event_block.append(nested)
                idx += 1

            filters: list[str] = []
            filters.extend(self._parse_event_inline_filters(inline_value))
            filters.extend(self._parse_event_block_filters(event_block))
            if filters:
                trigger_filters[event_name] = sorted(set(filters))

        return triggers, trigger_filters

    def _parse_event_inline_filters(self, inline_value: str) -> list[str]:
        cleaned = inline_value.strip()
        if not cleaned or cleaned in {"{}", "null", "~"}:
            return []
        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            return []

        filters: list[str] = []
        entries = self._split_top_level(cleaned[1:-1], ",")
        for entry in entries:
            pair = self._split_key_value_top_level(entry)
            if pair is None:
                continue
            filter_key = self._normalize_ci_token(pair[0])
            if filter_key not in CI_TRIGGER_FILTER_KEYS:
                continue

            values: list[str] = []
            raw_value = pair[1].strip()
            if raw_value.startswith("[") and raw_value.endswith("]"):
                values.extend(self._parse_yaml_list_literal(raw_value))
            else:
                scalar = self._parse_yaml_scalar(raw_value)
                if scalar:
                    values.append(scalar)

            for value in values:
                filters.append(f"{filter_key}={value}")
        return sorted(set(filters))

    def _parse_event_block_filters(self, event_block: list[str]) -> list[str]:
        filters: list[str] = []
        content_indent = self._first_content_indent(event_block)
        if content_indent is None:
            return filters

        idx = 0
        while idx < len(event_block):
            line = event_block[idx]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                idx += 1
                continue

            indent = len(line) - len(line.lstrip(" "))
            if indent != content_indent:
                idx += 1
                continue

            pair = self._split_key_value_top_level(stripped)
            if pair is None:
                idx += 1
                continue

            filter_key = self._normalize_ci_token(pair[0])
            inline_value = pair[1].strip()
            idx += 1

            nested_block: list[str] = []
            while idx < len(event_block):
                nested = event_block[idx]
                nested_stripped = nested.strip()
                if nested_stripped and not nested_stripped.startswith("#"):
                    nested_indent = len(nested) - len(nested.lstrip(" "))
                    if nested_indent <= content_indent:
                        break
                nested_block.append(nested)
                idx += 1

            if filter_key in CI_EVENT_IGNORE_KEYS:
                continue
            if filter_key not in CI_TRIGGER_FILTER_KEYS:
                continue

            values: list[str] = []
            if inline_value.startswith("[") and inline_value.endswith("]"):
                values.extend(self._parse_yaml_list_literal(inline_value))
            elif inline_value and not inline_value.startswith("{"):
                scalar = self._parse_yaml_scalar(inline_value)
                if scalar:
                    values.append(scalar)

            if not values and nested_block:
                nested_indent = self._first_content_indent(nested_block)
                if nested_indent is not None:
                    for nested_line in nested_block:
                        nested_stripped = nested_line.strip()
                        if not nested_stripped or nested_stripped.startswith("#"):
                            continue
                        current_indent = len(nested_line) - len(nested_line.lstrip(" "))
                        if current_indent != nested_indent:
                            continue
                        if nested_stripped.startswith("-"):
                            scalar = self._parse_yaml_scalar(nested_stripped.lstrip("-").strip())
                            if scalar:
                                values.append(scalar)
                            continue
                        nested_pair = self._split_key_value_top_level(nested_stripped)
                        if nested_pair is not None:
                            scalar = self._parse_yaml_scalar(nested_pair[1])
                            if scalar:
                                values.append(scalar)

            for value in values:
                filters.append(f"{filter_key}={value}")

        return sorted(set(filters))

    def _parse_yaml_list_literal(self, value: str) -> list[str]:
        cleaned = value.strip()
        if not (cleaned.startswith("[") and cleaned.endswith("]")):
            return []
        body = cleaned[1:-1].strip()
        if not body:
            return []
        result: list[str] = []
        for part in self._split_top_level(body, ","):
            scalar = self._parse_yaml_scalar(part)
            if scalar:
                result.append(scalar)
        return result

    def _parse_yaml_scalar(self, value: str) -> str:
        token = value.strip()
        if not token:
            return ""
        if token in {"null", "~", "{}", "[]"}:
            return ""
        if token[:1] in {"'", '"'} and token[-1:] == token[:1] and len(token) >= 2:
            token = token[1:-1]
        return token.strip()

    def _merge_trigger_filters(self, target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
        for event_name, values in source.items():
            if not values:
                continue
            if event_name not in target:
                target[event_name] = []
            target[event_name].extend(values)
            target[event_name] = sorted(set(target[event_name]))

    def _normalize_ci_token(self, value: str) -> str:
        token = self._parse_yaml_scalar(value).lower()
        if token.endswith(":"):
            token = token[:-1]
        return token.strip()

    def _is_ci_event_token(self, value: str) -> bool:
        if not value:
            return False
        if value in CI_EVENT_IGNORE_KEYS:
            return False
        if value in CI_TRIGGER_FILTER_KEYS:
            return False
        return bool(re.match(r"^[a-z0-9_-]+$", value))

    def _split_top_level(self, value: str, delimiter: str) -> list[str]:
        parts: list[str] = []
        buffer: list[str] = []
        quote: str | None = None
        escaped = False
        depth_curly = 0
        depth_square = 0
        depth_round = 0

        for char in value:
            if quote:
                buffer.append(char)
                if char == "\\" and not escaped:
                    escaped = True
                    continue
                if char == quote and not escaped:
                    quote = None
                escaped = False
                continue

            if char in {"'", '"'}:
                quote = char
                buffer.append(char)
                continue

            if char == "{":
                depth_curly += 1
            elif char == "}":
                depth_curly = max(0, depth_curly - 1)
            elif char == "[":
                depth_square += 1
            elif char == "]":
                depth_square = max(0, depth_square - 1)
            elif char == "(":
                depth_round += 1
            elif char == ")":
                depth_round = max(0, depth_round - 1)

            if (
                char == delimiter
                and depth_curly == 0
                and depth_square == 0
                and depth_round == 0
            ):
                candidate = "".join(buffer).strip()
                if candidate:
                    parts.append(candidate)
                buffer = []
                continue

            buffer.append(char)

        candidate = "".join(buffer).strip()
        if candidate:
            parts.append(candidate)
        return parts

    def _split_key_value_top_level(self, value: str) -> tuple[str, str] | None:
        quote: str | None = None
        escaped = False
        depth_curly = 0
        depth_square = 0
        depth_round = 0

        for idx, char in enumerate(value):
            if quote:
                if char == "\\" and not escaped:
                    escaped = True
                    continue
                if char == quote and not escaped:
                    quote = None
                escaped = False
                continue

            if char in {"'", '"'}:
                quote = char
                continue

            if char == "{":
                depth_curly += 1
                continue
            if char == "}":
                depth_curly = max(0, depth_curly - 1)
                continue
            if char == "[":
                depth_square += 1
                continue
            if char == "]":
                depth_square = max(0, depth_square - 1)
                continue
            if char == "(":
                depth_round += 1
                continue
            if char == ")":
                depth_round = max(0, depth_round - 1)
                continue

            if (
                char == ":"
                and depth_curly == 0
                and depth_square == 0
                and depth_round == 0
            ):
                left = value[:idx].strip()
                right = value[idx + 1 :].strip()
                if not left:
                    return None
                return left, right
        return None

    def _extract_job_critical_steps(self, job_id: str, job_block: list[str]) -> list[str]:
        run_or_use_steps: list[str] = []
        critical_steps: list[str] = []
        seen: set[str] = set()
        job_hint = any(marker in job_id.lower() for marker in CI_RELEASE_JOB_HINTS)

        for raw_line in job_block:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            match_run = re.match(r"^(?:-\s*)?run:\s*(.+)$", stripped)
            match_uses = re.match(r"^(?:-\s*)?uses:\s*(.+)$", stripped)
            if match_run:
                candidate = f"run: {match_run.group(1).strip()}"
            elif match_uses:
                candidate = f"uses: {match_uses.group(1).strip()}"
            else:
                continue

            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            run_or_use_steps.append(candidate)

            lowered = candidate.lower()
            if any(keyword in lowered for keyword in CI_CRITICAL_KEYWORDS):
                critical_steps.append(candidate)
                continue
            if job_hint and "run:" in lowered and any(word in lowered for word in ("deploy", "release", "publish")):
                critical_steps.append(candidate)

        if job_hint and not critical_steps:
            critical_steps.extend(run_or_use_steps[:2])

        dedup: list[str] = []
        dedup_seen: set[str] = set()
        for step in critical_steps:
            if step in dedup_seen:
                continue
            dedup_seen.add(step)
            dedup.append(step)
        return dedup

    def _detect_critical_files(self, rel_files: list[str]) -> list[CriticalFileFact]:
        findings: list[CriticalFileFact] = []
        for rel in sorted(set(rel_files)):
            lower = rel.lower()
            for marker, reason, risk_level in CRITICAL_FILE_RULES:
                marker_lower = marker.lower()
                matched = lower.startswith(marker_lower) if marker_lower.endswith("/") else lower.endswith(marker_lower)
                if not matched and marker_lower in lower and "/" in marker_lower:
                    matched = True
                if not matched:
                    continue
                base_confidence = 0.9 if matched and lower.endswith(marker_lower.strip("/")) else 0.75
                if risk_level == "medium":
                    base_confidence -= 0.1
                findings.append(
                    CriticalFileFact(
                        path=rel,
                        reason=reason,
                        risk_level=risk_level,
                        confidence=round(max(0.4, min(0.95, base_confidence)), 3),
                    )
                )
                break
        return findings

    def _detect_module_dependencies(
        self,
        repo: Path,
        files: list[Path],
        modules: list[ModuleFact],
        profile: str,
        guardrail_state: dict[str, object],
        scan_started_at: float,
        warnings: list[str],
    ) -> list[ModuleDependencyFact]:
        code_files = [path for path in files if path.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs"}]
        file_limit = DEPENDENCY_FILE_LIMIT_BY_PROFILE.get(profile, DEPENDENCY_FILE_LIMIT_BY_PROFILE["balanced"])
        if len(code_files) > file_limit:
            skipped_count = len(code_files) - file_limit
            code_files = code_files[:file_limit]
            self._activate_guardrail(
                guardrail_state=guardrail_state,
                reason="dependency_file_cap",
                skipped_marker=f"dependency_files:{skipped_count}",
            )
            warnings.append(
                f"Guardrail: dependency scan capped to {file_limit} code files for profile `{profile}`; "
                f"skipped {skipped_count} file(s)."
            )

        dependency_context = self._build_dependency_context(repo=repo, files=files)
        module_names = {m.name for m in modules if m.name and not m.name.startswith(".")}
        edges: dict[tuple[str, str], int] = {}
        file_records: list[tuple[Path, str, str, str]] = []
        for file_path in code_files:
            try:
                rel_path = file_path.relative_to(repo).as_posix()
            except ValueError:
                continue

            parts = Path(rel_path).parts
            source_module = self._source_module_name(parts=parts, dependency_context=dependency_context)
            if not source_module:
                continue
            module_names.add(source_module)
            file_records.append((file_path, rel_path, source_module, file_path.suffix.lower()))

        if not file_records:
            return []

        max_file_bytes = int(guardrail_state.get("max_dependency_file_bytes", 0))
        max_total_bytes = int(guardrail_state.get("max_dependency_total_bytes", 0))
        total_read_bytes = 0
        skipped_large_files = 0
        skipped_time_budget = False
        skipped_total_budget = False

        for file_path, rel_path, source_module, suffix in file_records:
            if source_module not in module_names:
                continue

            if self._time_budget_exceeded(guardrail_state=guardrail_state, scan_started_at=scan_started_at):
                skipped_time_budget = True
                self._activate_guardrail(
                    guardrail_state=guardrail_state,
                    reason="time_budget_exceeded_dependency_scan",
                    skipped_marker="dependency_files:time_budget",
                )
                break

            try:
                file_size = file_path.stat().st_size
            except OSError:
                file_size = 0

            if max_file_bytes and file_size > max_file_bytes:
                skipped_large_files += 1
                continue
            if max_total_bytes and total_read_bytes + max(0, file_size) > max_total_bytes:
                skipped_total_budget = True
                self._activate_guardrail(
                    guardrail_state=guardrail_state,
                    reason="dependency_total_bytes_cap",
                    skipped_marker="dependency_files:total_bytes_budget",
                )
                break

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            total_read_bytes += max(0, file_size)

            for import_ref in self._extract_import_references(content, suffix):
                target_module = self._resolve_import_target(
                    import_ref=import_ref,
                    source_rel_path=rel_path,
                    suffix=suffix,
                    module_names=module_names,
                    dependency_context=dependency_context,
                )
                if not target_module or target_module == source_module:
                    continue
                edge = (source_module, target_module)
                edges[edge] = edges.get(edge, 0) + 1

        if skipped_large_files:
            self._activate_guardrail(
                guardrail_state=guardrail_state,
                reason="dependency_large_file_skip",
                skipped_marker=f"dependency_large_files:{skipped_large_files}",
            )
            warnings.append(
                f"Guardrail: dependency scan skipped {skipped_large_files} oversized source file(s) "
                f"(>{max_file_bytes} bytes)."
            )
        if skipped_total_budget:
            warnings.append("Guardrail: dependency scan stopped after total byte budget was reached.")
        if skipped_time_budget:
            warnings.append("Guardrail: dependency scan stopped due to time budget.")

        dependencies = [
            ModuleDependencyFact(
                source_module=source,
                target_module=target,
                signal_count=count,
                confidence=round(min(0.95, 0.45 + min(0.45, count * 0.08)), 3),
            )
            for (source, target), count in edges.items()
        ]
        return sorted(
            dependencies,
            key=lambda item: (-item.signal_count, item.source_module, item.target_module),
        )[:80]

    def _build_dependency_context(self, repo: Path, files: list[Path]) -> dict[str, object]:
        return {
            "python_package_roots": self._detect_python_package_roots(repo=repo, files=files),
            "go_module_path": self._detect_go_module_path(repo=repo),
            "ts_path_aliases": self._detect_ts_path_aliases(repo=repo),
        }

    def _detect_python_package_roots(self, repo: Path, files: list[Path]) -> set[str]:
        package_roots: set[str] = set()
        for file_path in files:
            try:
                rel_path = file_path.relative_to(repo).as_posix()
            except ValueError:
                continue
            if not rel_path.endswith("__init__.py"):
                continue
            parts = Path(rel_path).parts
            if not parts:
                continue
            if parts[0].lower() in {"src", "lib", "app", "apps", "pkg", "packages"} and len(parts) >= 2:
                package_roots.add(parts[1])
            else:
                package_roots.add(parts[0])
        return {item for item in package_roots if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", item)}

    def _detect_go_module_path(self, repo: Path) -> str:
        go_mod = repo / "go.mod"
        if not go_mod.exists():
            return ""
        try:
            for line in go_mod.read_text(encoding="utf-8", errors="replace").splitlines():
                stripped = line.strip()
                if not stripped.startswith("module "):
                    continue
                module_path = stripped.split("module", 1)[1].strip()
                return module_path
        except OSError:
            return ""
        return ""

    def _detect_ts_path_aliases(self, repo: Path) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for config_name in ("tsconfig.json", "jsconfig.json"):
            config_path = repo / config_name
            if not config_path.exists():
                continue
            try:
                data = json.loads(config_path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError):
                continue

            compiler_options = data.get("compilerOptions", {})
            paths = compiler_options.get("paths", {})
            if not isinstance(paths, dict):
                continue

            for raw_alias, raw_targets in paths.items():
                if not isinstance(raw_alias, str):
                    continue
                alias_key = raw_alias.rstrip("*").rstrip("/")
                if not alias_key:
                    continue

                targets: list[str] = []
                if isinstance(raw_targets, list):
                    targets.extend(str(item) for item in raw_targets if isinstance(item, str))
                elif isinstance(raw_targets, str):
                    targets.append(raw_targets)

                for target in targets:
                    normalized = target.replace("\\", "/").lstrip("./")
                    parts = [part for part in normalized.split("/") if part and part not in {"*", "."}]
                    if not parts:
                        continue
                    candidate = self._module_candidate_from_path_parts(tuple(parts), python_package_roots=set())
                    if not candidate:
                        continue
                    aliases[alias_key] = candidate
                    break
        return aliases

    def _source_module_name(self, parts: tuple[str, ...], dependency_context: dict[str, object]) -> str:
        if not parts:
            return ""
        if len(parts) == 1:
            return ""

        python_package_roots = set(dependency_context.get("python_package_roots", set()))
        module_name = self._module_candidate_from_path_parts(parts=parts, python_package_roots=python_package_roots)
        if not module_name.startswith(".") and re.match(r"^[A-Za-z0-9_-]+$", module_name):
            return module_name
        return ""

    def _module_candidate_from_path_parts(self, parts: tuple[str, ...], python_package_roots: set[str]) -> str:
        if not parts:
            return ""
        root = parts[0]
        lower = root.lower()
        if lower in {"src", "lib", "app", "apps", "pkg", "packages"} and len(parts) >= 2:
            if parts[1] in python_package_roots and len(parts) >= 3:
                return parts[2]
            return parts[1]
        if lower.startswith("."):
            return ""
        return root

    def _extract_import_references(self, content: str, suffix: str) -> list[str]:
        refs: set[str] = set()
        if suffix == ".py":
            for match in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z0-9_\.]+)", content, flags=re.MULTILINE):
                refs.add(match.group(1))
        elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
            for match in re.finditer(r"from\s+['\"]([^'\"]+)['\"]", content):
                refs.add(match.group(1))
            for match in re.finditer(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
                refs.add(match.group(1))
            for match in re.finditer(r"import\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
                refs.add(match.group(1))
        elif suffix == ".go":
            for match in re.finditer(r"^\s*import\s+\"([^\"]+)\"", content, flags=re.MULTILINE):
                refs.add(match.group(1))
            for block in re.finditer(r"^\s*import\s*\((.*?)\)", content, flags=re.MULTILINE | re.DOTALL):
                for quoted in re.finditer(r"\"([^\"]+)\"", block.group(1)):
                    refs.add(quoted.group(1))
        elif suffix == ".rs":
            for match in re.finditer(r"^\s*use\s+([A-Za-z0-9_:]+)", content, flags=re.MULTILINE):
                refs.add(match.group(1))
        return sorted(refs)

    def _resolve_import_target(
        self,
        import_ref: str,
        source_rel_path: str,
        suffix: str,
        module_names: set[str],
        dependency_context: dict[str, object],
    ) -> str | None:
        raw_ref = import_ref.strip()
        if not raw_ref:
            return None

        if suffix == ".py":
            return self._resolve_python_import_target(
                raw_ref=raw_ref,
                source_rel_path=source_rel_path,
                module_names=module_names,
                dependency_context=dependency_context,
            )
        if suffix in {".js", ".jsx", ".ts", ".tsx"}:
            return self._resolve_js_ts_import_target(
                raw_ref=raw_ref,
                source_rel_path=source_rel_path,
                module_names=module_names,
                dependency_context=dependency_context,
            )
        if suffix == ".go":
            return self._resolve_go_import_target(
                raw_ref=raw_ref,
                module_names=module_names,
                dependency_context=dependency_context,
            )

        ref = raw_ref.replace("::", "/")
        token = ref.split("/", 1)[0].split(".", 1)[0]
        if token in module_names:
            return token
        if "/" in ref:
            tail = ref.split("/")[-1].split(".", 1)[0]
            if tail in module_names:
                return tail
        return None

    def _resolve_python_import_target(
        self,
        raw_ref: str,
        source_rel_path: str,
        module_names: set[str],
        dependency_context: dict[str, object],
    ) -> str | None:
        python_package_roots = set(dependency_context.get("python_package_roots", set()))

        if raw_ref.startswith("."):
            dot_count = len(raw_ref) - len(raw_ref.lstrip("."))
            tail = raw_ref[dot_count:]

            module_path_parts = [part for part in Path(source_rel_path).with_suffix("").parts if part]
            if not module_path_parts:
                return None
            package_parts = module_path_parts[:-1]

            ascend = max(0, dot_count - 1)
            if ascend:
                package_parts = package_parts[:-ascend] if ascend <= len(package_parts) else []

            tail_parts = [part for part in tail.split(".") if part]
            candidate_parts = package_parts + tail_parts
            for candidate in self._candidate_tokens_from_import_parts(
                import_parts=candidate_parts,
                python_package_roots=python_package_roots,
            ):
                if candidate in module_names:
                    return candidate
            return None

        import_parts = [part for part in raw_ref.split(".") if part]
        for candidate in self._candidate_tokens_from_import_parts(
            import_parts=import_parts,
            python_package_roots=python_package_roots,
        ):
            if candidate in module_names:
                return candidate
        return None

    def _resolve_js_ts_import_target(
        self,
        raw_ref: str,
        source_rel_path: str,
        module_names: set[str],
        dependency_context: dict[str, object],
    ) -> str | None:
        ts_aliases = dict(dependency_context.get("ts_path_aliases", {}))

        for alias, target in ts_aliases.items():
            if raw_ref == alias or raw_ref.startswith(alias + "/"):
                if target in module_names:
                    return target

        if raw_ref.startswith("@") and "/" in raw_ref:
            scoped = raw_ref.split("/", 1)[1]
            scoped_token = scoped.split("/", 1)[0].split(".", 1)[0]
            if scoped_token in module_names:
                return scoped_token

        ref = raw_ref.lstrip("@")
        if not ref:
            return None

        if ref.startswith("./") or ref.startswith("../"):
            source_dir = posixpath.dirname(source_rel_path)
            normalized = posixpath.normpath(posixpath.join(source_dir, ref))
            parts = tuple(part for part in normalized.split("/") if part and part != ".")
            candidate = self._module_candidate_from_path_parts(parts=parts, python_package_roots=set())
            if candidate in module_names:
                return candidate

        token = ref.split("/", 1)[0].split(".", 1)[0]
        if token in module_names:
            return token

        if "/" in ref:
            tail = ref.split("/")[-1].split(".", 1)[0]
            if tail in module_names:
                return tail
        return None

    def _resolve_go_import_target(
        self,
        raw_ref: str,
        module_names: set[str],
        dependency_context: dict[str, object],
    ) -> str | None:
        go_module_path = str(dependency_context.get("go_module_path", "")).strip()
        if go_module_path:
            if raw_ref == go_module_path:
                return None
            if raw_ref.startswith(go_module_path + "/"):
                rel = raw_ref[len(go_module_path) + 1 :]
                rel_token = rel.split("/", 1)[0]
                if rel_token in module_names:
                    return rel_token

        token = raw_ref.split("/", 1)[0].split(".", 1)[0]
        if token in module_names:
            return token

        if "/" in raw_ref:
            tail = raw_ref.split("/")[-1].split(".", 1)[0]
            if tail in module_names:
                return tail
        return None

    def _candidate_tokens_from_import_parts(self, import_parts: list[str], python_package_roots: set[str]) -> list[str]:
        if not import_parts:
            return []
        tokens: list[str] = []
        if import_parts[0] in python_package_roots and len(import_parts) > 1:
            tokens.extend(import_parts[1:])
        tokens.extend(import_parts)
        dedup: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            cleaned = token.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            dedup.append(cleaned)
        return dedup

    def _build_hypotheses(
        self,
        entry_points: list[str],
        key_commands: list[str],
        tests_map: list[TestSuiteFact],
        ci_pipeline_map: list[CiPipelineFact],
    ) -> list[HypothesisItem]:
        hypotheses: list[HypothesisItem] = []

        if entry_points:
            primary_entry = entry_points[0]
            entry_confidence = 0.9 if not self._is_low_relevance_entrypoint(primary_entry) else 0.62
            hypotheses.append(
                HypothesisItem(
                    hypothesis_id="h_entrypoint_001",
                    area="architecture",
                    claim=f"Каноническая точка входа: {primary_entry}",
                    confidence=round(entry_confidence, 3),
                    evidence=[f"entry_points[0]={primary_entry}"],
                    requires_confirmation=entry_confidence < 0.8,
                    suggested_question=f"Подтвердите, что `{primary_entry}` — главный entrypoint проекта.",
                )
            )

        if key_commands:
            primary_command = key_commands[0]
            command_confidence = 0.86
            if self._is_low_relevance_command(primary_command):
                command_confidence = 0.64
            elif self._is_test_command(primary_command):
                command_confidence = 0.9
            hypotheses.append(
                HypothesisItem(
                    hypothesis_id="h_command_001",
                    area="workflow",
                    claim=f"Базовая верификация выполняется через `{primary_command}`",
                    confidence=round(command_confidence, 3),
                    evidence=[f"key_commands[0]={primary_command}"],
                    requires_confirmation=command_confidence < 0.8,
                    suggested_question=(
                        f"Подтвердите или скорректируйте ключевую команду проверки: `{primary_command}`."
                    ),
                )
            )

        if tests_map:
            primary_suite = tests_map[0]
            question = f"Это основной тестовый контур (`{primary_suite.path}`)?"
            if primary_suite.command_candidates:
                question = (
                    f"Подтвердите основной тестовый контур `{primary_suite.path}` "
                    f"и команду `{primary_suite.command_candidates[0]}`."
                )
            hypotheses.append(
                HypothesisItem(
                    hypothesis_id="h_tests_001",
                    area="testing",
                    claim=(
                        f"Основной тестовый контур: {primary_suite.path} "
                        f"(framework={primary_suite.framework})"
                    ),
                    confidence=round(primary_suite.confidence, 3),
                    evidence=[f"tests_map[0]={primary_suite.path}:{primary_suite.framework}"],
                    requires_confirmation=primary_suite.confidence < 0.8,
                    suggested_question=question,
                )
            )

        if ci_pipeline_map:
            primary_ci = ci_pipeline_map[0]
            ci_confidence = primary_ci.confidence
            trigger_label = ", ".join(primary_ci.triggers[:4]) if primary_ci.triggers else "unknown triggers"
            hypotheses.append(
                HypothesisItem(
                    hypothesis_id="h_ci_001",
                    area="delivery",
                    claim=f"Основной CI pipeline: {primary_ci.name} ({trigger_label})",
                    confidence=round(ci_confidence, 3),
                    evidence=[f"ci_pipeline_map[0]={primary_ci.file}"],
                    requires_confirmation=ci_confidence < 0.82,
                    suggested_question=(
                        f"Подтвердите, что `{primary_ci.file}` является критичным CI/CD workflow "
                        "для merge/push."
                    ),
                )
            )

        return hypotheses

    def _build_unknowns(
        self,
        entry_points: list[str],
        key_commands: list[str],
        tests_map: list[TestSuiteFact],
        hypotheses: list[HypothesisItem],
    ) -> list[UnknownItem]:
        unknowns = [
            UnknownItem(
                unknown_id="u_workflow_001",
                area="workflow",
                description="Project-specific agent workflow boundaries are not inferred from files.",
                impact_level="high",
                suggested_question="What are non-negotiable behavior boundaries for the agent?",
            )
        ]

        if not entry_points:
            unknowns.append(
                UnknownItem(
                    unknown_id="u_entrypoint_001",
                    area="architecture",
                    description="No explicit executable entry point was confidently inferred.",
                    impact_level="medium",
                    suggested_question="Which command or file is the canonical entry point for this project?",
                )
            )
        if not key_commands:
            unknowns.append(
                UnknownItem(
                    unknown_id="u_commands_001",
                    area="workflow",
                    description="No canonical run/test commands were inferred.",
                    impact_level="high",
                    suggested_question="What are the mandatory run and test commands for this repository?",
                )
            )
        if not tests_map:
            unknowns.append(
                UnknownItem(
                    unknown_id="u_tests_001",
                    area="testing",
                    description="No reliable test suite signal was inferred from repository scan.",
                    impact_level="high",
                    suggested_question="Where are tests located and what exact command must run after changes?",
                )
            )

        for idx, hypothesis in enumerate([h for h in hypotheses if h.requires_confirmation], start=1):
            impact = "medium"
            if hypothesis.area in {"workflow", "delivery"}:
                impact = "high"
            unknowns.append(
                UnknownItem(
                    unknown_id=f"u_hypothesis_{idx:03d}",
                    area=hypothesis.area,
                    description=f"Scanner hypothesis requires confirmation: {hypothesis.claim}",
                    impact_level=impact,
                    suggested_question=hypothesis.suggested_question,
                )
            )
        return unknowns

    def _confidence(
        self,
        file_count: int,
        stacks: list[str],
        entry_points: list[str],
        key_commands: list[str],
        tests_map: list[TestSuiteFact],
        ci_pipeline_map: list[CiPipelineFact],
        warnings: list[str],
    ) -> dict[str, float]:
        coverage = min(1.0, file_count / 120.0) if file_count else 0.0
        signal_parts = [
            1.0 if stacks else 0.0,
            1.0 if entry_points else 0.0,
            1.0 if key_commands else 0.0,
            1.0 if tests_map else 0.0,
            1.0 if ci_pipeline_map else 0.0,
        ]
        signal = sum(signal_parts) / len(signal_parts)
        coherence = 0.85 - min(0.35, 0.05 * len(warnings))
        return {
            "coverage_confidence": round(coverage, 3),
            "signal_confidence": round(signal, 3),
            "coherence_confidence": round(max(0.0, coherence), 3),
        }

    def _operational_confidence(
        self,
        tests_map: list[TestSuiteFact],
        ci_pipeline_map: list[CiPipelineFact],
        critical_files_map: list[CriticalFileFact],
        module_dependency_map: list[ModuleDependencyFact],
        hypotheses: list[HypothesisItem],
    ) -> dict[str, float]:
        tests = round(
            sum(item.confidence for item in tests_map) / len(tests_map),
            3,
        ) if tests_map else 0.0
        ci = round(
            sum(item.confidence for item in ci_pipeline_map) / len(ci_pipeline_map),
            3,
        ) if ci_pipeline_map else 0.0
        critical_files = round(
            sum(item.confidence for item in critical_files_map) / len(critical_files_map),
            3,
        ) if critical_files_map else 0.0
        dependencies = round(
            sum(item.confidence for item in module_dependency_map[:20]) / min(20, len(module_dependency_map)),
            3,
        ) if module_dependency_map else 0.0

        if hypotheses:
            confirm_ratio = sum(1 for h in hypotheses if h.requires_confirmation) / len(hypotheses)
            hypotheses_score = round(max(0.0, 1.0 - confirm_ratio), 3)
        else:
            hypotheses_score = 0.0

        weighted = (
            0.35 * tests
            + 0.30 * ci
            + 0.15 * critical_files
            + 0.10 * dependencies
            + 0.10 * hypotheses_score
        )
        return {
            "tests_confidence": tests,
            "ci_confidence": ci,
            "critical_files_confidence": critical_files,
            "dependency_confidence": dependencies,
            "hypotheses_confidence": hypotheses_score,
            "overall": round(weighted, 3),
        }

    def _is_low_relevance_entrypoint(self, entry_point: str) -> bool:
        lower = entry_point.lower()
        if "manual entrypoint reference" in lower:
            return True
        return any(lower.startswith(prefix) for prefix in LOW_RELEVANCE_ENTRYPOINT_PREFIXES)

    def _is_low_relevance_command(self, command: str) -> bool:
        lower = command.lower()
        return any(marker in lower for marker in LOW_RELEVANCE_COMMAND_MARKERS)
