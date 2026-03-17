import json
import os
from pathlib import Path

from opack.contracts.models import FactModel, ModuleFact, UnknownItem

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
}


class ScannerEngine:
    """V1 scanner baseline: real file scan with stack/entry/env/command inference."""

    def scan(self, repo_path: Path, profile: str = "balanced") -> FactModel:
        repo = repo_path.resolve()
        files, walk_warnings = self._collect_files(repo)
        file_names = {p.name.lower() for p in files}
        rel_files = [p.relative_to(repo).as_posix() for p in files]
        warnings: list[str] = list(walk_warnings)

        detected_stacks = self._detect_stacks(file_names)
        modules = self._collect_modules(repo, files)
        entry_points = self._detect_entry_points(repo, rel_files, file_names)
        environments = self._detect_environments(file_names, rel_files)
        key_commands, command_warnings = self._detect_commands(repo, file_names)
        warnings.extend(command_warnings)
        external_integrations = self._detect_external_integrations(file_names, rel_files)
        unknowns = self._build_unknowns(entry_points=entry_points, key_commands=key_commands)

        confidence_breakdown = self._confidence(
            file_count=len(files),
            stacks=detected_stacks,
            entry_points=entry_points,
            key_commands=key_commands,
            warnings=warnings,
        )
        confidence_overall = (
            0.4 * confidence_breakdown["coverage_confidence"]
            + 0.4 * confidence_breakdown["signal_confidence"]
            + 0.2 * confidence_breakdown["coherence_confidence"]
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
            unknowns=unknowns,
            confidence_overall=round(confidence_overall, 3),
            confidence_breakdown=confidence_breakdown,
            scanner_warnings=warnings,
        )

    def _collect_files(self, repo: Path) -> tuple[list[Path], list[str]]:
        files: list[Path] = []
        warnings: list[str] = []

        def _onerror(exc: OSError) -> None:
            warnings.append(f"Walk warning: {exc}")

        for root, dirs, filenames in os.walk(repo, topdown=True, onerror=_onerror):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIR_NAMES]
            for name in filenames:
                path = Path(root) / name
                if any(part in IGNORE_DIR_NAMES for part in path.parts):
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

        return sorted(set(commands)), warnings

    def _detect_external_integrations(self, file_names: set[str], rel_files: list[str]) -> list[str]:
        integrations = []
        if "dockerfile" in file_names:
            integrations.append("docker")
        if "terraform.tf" in file_names or "main.tf" in file_names:
            integrations.append("terraform")
        if any(path.startswith(".github/workflows/") for path in rel_files):
            integrations.append("github-actions")
        return sorted(set(integrations))

    def _build_unknowns(self, entry_points: list[str], key_commands: list[str]) -> list[UnknownItem]:
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
        return unknowns

    def _confidence(
        self,
        file_count: int,
        stacks: list[str],
        entry_points: list[str],
        key_commands: list[str],
        warnings: list[str],
    ) -> dict[str, float]:
        coverage = min(1.0, file_count / 120.0) if file_count else 0.0
        signal_parts = [1.0 if stacks else 0.0, 1.0 if entry_points else 0.0, 1.0 if key_commands else 0.0]
        signal = sum(signal_parts) / len(signal_parts)
        coherence = 0.85 - min(0.35, 0.05 * len(warnings))
        return {
            "coverage_confidence": round(coverage, 3),
            "signal_confidence": round(signal, 3),
            "coherence_confidence": round(max(0.0, coherence), 3),
        }
