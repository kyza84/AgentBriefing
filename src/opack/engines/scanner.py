import json
import os
import posixpath
import re
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

CI_TRIGGER_IGNORE_KEYS = {
    "branches",
    "branches-ignore",
    "paths",
    "paths-ignore",
    "tags",
    "tags-ignore",
    "types",
    "inputs",
    "outputs",
}

CI_CRITICAL_KEYWORDS = (
    "deploy",
    "release",
    "publish",
    "docker push",
    "terraform apply",
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
    "quick": 3500,
    "balanced": 12000,
    "strict": 20000,
}


class ScannerEngine:
    """V1.1 scanner: structural and operational fact extraction."""

    def scan(self, repo_path: Path, profile: str = "balanced") -> FactModel:
        repo = repo_path.resolve()
        files, walk_warnings = self._collect_files(repo)
        file_names = {p.name.lower() for p in files}
        rel_files = [p.relative_to(repo).as_posix() for p in files]
        warnings: list[str] = list(walk_warnings)

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
        ci_pipeline_map = self._detect_ci_pipelines(repo=repo, rel_files=rel_files)
        critical_files_map = self._detect_critical_files(rel_files=rel_files)
        module_dependency_map = self._detect_module_dependencies(
            repo=repo,
            files=files,
            modules=modules,
            profile=profile,
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
            scanner_warnings=warnings,
        )

    def _collect_files(self, repo: Path) -> tuple[list[Path], list[str]]:
        files: list[Path] = []
        warnings: list[str] = []
        ignored_lower = {name.lower() for name in IGNORE_DIR_NAMES}

        def _onerror(exc: OSError) -> None:
            warnings.append(f"Walk warning: {exc}")

        for root, dirs, filenames in os.walk(repo, topdown=True, onerror=_onerror):
            dirs[:] = [d for d in dirs if d.lower() not in ignored_lower]
            for name in filenames:
                path = Path(root) / name
                # Apply ignore rules only to the path inside the scanned repository.
                rel_parts = path.relative_to(repo).parts
                if any(part.lower() in ignored_lower for part in rel_parts):
                    continue
                files.append(path)
        return files, warnings

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

    def _detect_ci_pipelines(self, repo: Path, rel_files: list[str]) -> list[CiPipelineFact]:
        workflow_files = [
            rel
            for rel in rel_files
            if rel.lower().startswith(".github/workflows/") and rel.lower().endswith((".yml", ".yaml"))
        ]
        pipelines: list[CiPipelineFact] = []
        for rel in sorted(workflow_files):
            file_path = repo / rel
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lines = content.splitlines()
            name = self._extract_workflow_name(lines) or Path(rel).stem
            triggers = self._extract_workflow_triggers(lines)
            jobs = self._extract_workflow_jobs(lines)
            critical_steps = self._extract_ci_critical_steps(lines)
            confidence = 0.55
            if triggers:
                confidence += 0.15
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

    def _extract_workflow_triggers(self, lines: list[str]) -> list[str]:
        triggers: set[str] = set()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith("on:"):
                continue

            base_indent = len(line) - len(line.lstrip(" "))
            inline = stripped[len("on:") :].strip()
            if inline.startswith("[") and inline.endswith("]"):
                parts = [p.strip().strip("'\"") for p in inline.strip("[]").split(",")]
                triggers.update(part for part in parts if part)
                continue
            if inline and not inline.startswith("{"):
                triggers.add(inline.strip("'\""))
                continue

            for nested in lines[idx + 1 :]:
                nested_stripped = nested.strip()
                if not nested_stripped or nested_stripped.startswith("#"):
                    continue

                nested_indent = len(nested) - len(nested.lstrip(" "))
                if nested_indent <= base_indent:
                    break

                # Read only first-level keys directly under `on:`.
                if nested_indent != base_indent + 2:
                    continue

                key = ""
                if nested_stripped.startswith("-"):
                    key = nested_stripped.lstrip("-").strip().strip("'\"")
                    key = key.split(":", 1)[0].strip()
                else:
                    key = nested_stripped.split(":", 1)[0].strip().strip("'\"")

                if not key or not re.match(r"^[A-Za-z0-9_-]+$", key):
                    continue
                if key not in CI_TRIGGER_IGNORE_KEYS:
                    triggers.add(key)
            break
        return sorted(triggers)

    def _extract_workflow_jobs(self, lines: list[str]) -> list[CiJobFact]:
        in_jobs = False
        jobs: list[CiJobFact] = []
        for line in lines:
            if line.strip() == "jobs:":
                in_jobs = True
                continue
            if not in_jobs:
                continue
            if line and not line.startswith(" "):
                break
            match = re.match(r"^\s{2}([A-Za-z0-9_-]+):\s*$", line)
            if match:
                job_id = match.group(1)
                jobs.append(CiJobFact(job_id=job_id, name=job_id))
        return jobs

    def _extract_ci_critical_steps(self, lines: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for line in lines:
            lowered = line.lower()
            if not any(keyword in lowered for keyword in CI_CRITICAL_KEYWORDS):
                continue
            cleaned = line.strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            result.append(cleaned[:180])
        return result

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
    ) -> list[ModuleDependencyFact]:
        code_files = [path for path in files if path.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs"}]
        file_limit = DEPENDENCY_FILE_LIMIT_BY_PROFILE.get(profile, DEPENDENCY_FILE_LIMIT_BY_PROFILE["balanced"])
        if len(code_files) > file_limit:
            code_files = code_files[:file_limit]

        module_names = {m.name for m in modules if m.name and not m.name.startswith(".")}
        edges: dict[tuple[str, str], int] = {}
        file_records: list[tuple[Path, str, str, str]] = []
        for file_path in code_files:
            try:
                rel_path = file_path.relative_to(repo).as_posix()
            except ValueError:
                continue

            parts = Path(rel_path).parts
            source_module = self._canonical_module_name(parts)
            if not source_module:
                continue
            module_names.add(source_module)
            file_records.append((file_path, rel_path, source_module, file_path.suffix.lower()))

        if not file_records:
            return []

        for file_path, rel_path, source_module, suffix in file_records:
            if source_module not in module_names:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for import_ref in self._extract_import_references(content, suffix):
                target_module = self._resolve_import_target(
                    import_ref=import_ref,
                    source_rel_path=rel_path,
                    module_names=module_names,
                )
                if not target_module or target_module == source_module:
                    continue
                edge = (source_module, target_module)
                edges[edge] = edges.get(edge, 0) + 1

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

    def _canonical_module_name(self, parts: tuple[str, ...]) -> str:
        if not parts:
            return ""
        root = parts[0]
        lower = root.lower()
        if lower in {"src", "lib", "app", "apps", "pkg", "packages"} and len(parts) >= 2:
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
            for match in re.finditer(r"^\s*\"([^\"]+)\"", content, flags=re.MULTILINE):
                refs.add(match.group(1))
        elif suffix == ".rs":
            for match in re.finditer(r"^\s*use\s+([A-Za-z0-9_:]+)", content, flags=re.MULTILINE):
                refs.add(match.group(1))
        return sorted(refs)

    def _resolve_import_target(
        self,
        import_ref: str,
        source_rel_path: str,
        module_names: set[str],
    ) -> str | None:
        raw_ref = import_ref.strip()
        if not raw_ref:
            return None

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
            candidate = self._canonical_module_name(tuple(part for part in normalized.split("/") if part and part != "."))
            if candidate in module_names:
                return candidate

        token = ref.replace("::", "/").split("/", 1)[0].split(".", 1)[0]
        if token in module_names:
            return token

        if "/" in ref:
            tail = ref.split("/")[-1].split(".", 1)[0]
            if tail in module_names:
                return tail
        return None

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
