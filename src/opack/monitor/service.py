from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from opack.core.errors import GateBlockedError
from opack.orchestrators.build_pipeline import BuildPipeline


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def repo_slug_from_url(repo_url: str) -> str:
    parsed = urlparse(repo_url.strip())
    raw = parsed.path.rstrip("/").split("/")[-1] if parsed.path else "repo"
    if raw.endswith(".git"):
        raw = raw[:-4]
    raw = raw or "repo"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", raw)
    return slug.strip("-") or "repo"


def load_answers_payload(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    content = path.read_text(encoding="utf-8-sig")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Файл ответов должен содержать JSON-объект.")
    return parsed


def load_pilot_repo_urls(registry_path: Path) -> list[str]:
    if not registry_path.exists():
        return []
    urls: list[str] = []
    pattern = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if match:
            urls.append(match.group(0))
    deduped: list[str] = []
    seen = set()
    for url in urls:
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(url)
    return deduped


def _run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def _git_head_sha(repo_path: Path) -> str:
    result = _run_command(["git", "rev-parse", "HEAD"], cwd=repo_path)
    if result.returncode != 0:
        return "N/A"
    return result.stdout.strip() or "N/A"


def clone_repo_to_run_workspace(repo_url: str, run_root: Path, git_ref: str = "HEAD") -> Path:
    repo_dir = run_root / "repo"
    clone = _run_command(["git", "clone", "--depth", "1", repo_url, str(repo_dir)])
    if clone.returncode != 0:
        stderr = clone.stderr.strip() or clone.stdout.strip()
        raise RuntimeError(f"Не удалось клонировать репозиторий: {stderr}")

    ref = (git_ref or "HEAD").strip()
    if ref.upper() != "HEAD":
        checkout = _run_command(["git", "checkout", ref], cwd=repo_dir)
        if checkout.returncode != 0:
            stderr = checkout.stderr.strip() or checkout.stdout.strip()
            raise RuntimeError(f"Не удалось переключиться на ref '{ref}': {stderr}")
    return repo_dir


@dataclass
class MonitorCheckResult:
    run_id: str
    repo_url: str
    repo_path: str
    repo_head_sha: str
    profile: str
    pack_dir: str
    blocking_status: bool
    quality_score: float
    issues_count: int
    critical_issues: int
    unknown_count: int
    resolved_unknown_count: int
    open_unknown_count: int
    detected_stacks: list[str]
    entry_points_count: int
    key_commands_count: int
    environments: list[str]
    external_integrations: list[str]
    error_message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _latest_pack_dir(output_root: Path) -> Path:
    packs = sorted(output_root.glob("pack-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not packs:
        raise RuntimeError("Не найден сгенерированный каталог pack.")
    return packs[0]


def run_local_repo_check(
    repo_path: Path,
    workspace_root: Path,
    profile: str = "balanced",
    answers_payload: dict[str, Any] | None = None,
    repo_url: str = "",
) -> MonitorCheckResult:
    run_id = f"{_now_stamp()}_{uuid4().hex[:8]}"
    run_root = workspace_root / "runs" / run_id
    output_root = run_root / "output"
    output_root.mkdir(parents=True, exist_ok=True)

    pipeline = BuildPipeline()
    error_message = ""
    try:
        pipeline.run(
            repo_path=repo_path,
            output_path=output_root,
            profile=profile,
            answers=answers_payload or {},
        )
    except GateBlockedError as exc:
        error_message = str(exc)

    pack_dir = _latest_pack_dir(output_root)
    fact_model = json.loads((pack_dir / "FACT_MODEL.json").read_text(encoding="utf-8"))
    policy_model = json.loads((pack_dir / "POLICY_MODEL.json").read_text(encoding="utf-8"))
    validation = json.loads((pack_dir / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))

    issues = validation.get("issues", [])
    critical_issues = sum(1 for issue in issues if str(issue.get("severity", "")).lower().endswith("critical"))

    return MonitorCheckResult(
        run_id=run_id,
        repo_url=repo_url,
        repo_path=str(repo_path),
        repo_head_sha=_git_head_sha(repo_path),
        profile=profile,
        pack_dir=str(pack_dir),
        blocking_status=bool(validation.get("blocking_status", False)),
        quality_score=float(validation.get("quality_score", 0.0)),
        issues_count=len(issues),
        critical_issues=critical_issues,
        unknown_count=len(fact_model.get("unknowns", [])),
        resolved_unknown_count=len(policy_model.get("resolved_unknowns", [])),
        open_unknown_count=len(policy_model.get("open_unknowns", [])),
        detected_stacks=list(fact_model.get("detected_stacks", [])),
        entry_points_count=len(fact_model.get("entry_points", [])),
        key_commands_count=len(fact_model.get("key_commands", [])),
        environments=list(fact_model.get("environments", [])),
        external_integrations=list(fact_model.get("external_integrations", [])),
        error_message=error_message,
    )


def run_remote_repo_check(
    repo_url: str,
    workspace_root: Path,
    profile: str = "balanced",
    git_ref: str = "HEAD",
    answers_payload: dict[str, Any] | None = None,
) -> MonitorCheckResult:
    slug = repo_slug_from_url(repo_url)
    run_id = f"{_now_stamp()}_{slug}_{uuid4().hex[:6]}"
    run_root = workspace_root / "remote_runs" / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    repo_path = clone_repo_to_run_workspace(repo_url=repo_url, run_root=run_root, git_ref=git_ref)
    return run_local_repo_check(
        repo_path=repo_path,
        workspace_root=workspace_root,
        profile=profile,
        answers_payload=answers_payload,
        repo_url=repo_url,
    )
