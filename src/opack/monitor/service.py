from __future__ import annotations

import json
import re
import subprocess
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

from opack.core.errors import GateBlockedError
from opack.orchestrators.build_pipeline import BuildPipeline


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        raise ValueError("Answers file must contain a JSON object.")
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


def _summarize_git_error(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if any("Filename too long" in line for line in lines):
        return "Git checkout failed on Windows because file paths are too long (Filename too long)."
    if not lines:
        return "Git command failed without error output."
    return " | ".join(lines[-4:])


def clone_repo_to_run_workspace(repo_url: str, run_root: Path, git_ref: str = "HEAD") -> Path:
    repo_dir = run_root / "r"
    clone = _run_command(
        [
            "git",
            "-c",
            "core.longpaths=true",
            "clone",
            "--depth",
            "1",
            "--config",
            "core.longpaths=true",
            repo_url,
            str(repo_dir),
        ]
    )
    if clone.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {_summarize_git_error(clone)}")

    _run_command(["git", "config", "core.longpaths", "true"], cwd=repo_dir)

    ref = (git_ref or "HEAD").strip()
    if ref.upper() != "HEAD":
        checkout = _run_command(["git", "checkout", ref], cwd=repo_dir)
        if checkout.returncode != 0:
            raise RuntimeError(f"Failed to checkout ref '{ref}': {_summarize_git_error(checkout)}")
    return repo_dir


@dataclass
class MonitorStageEvent:
    run_id: str
    state: str
    stage_id: str
    message: str
    percent: int
    timestamp_utc: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MonitorSessionStart:
    run_id: str
    repo_url: str
    repo_path: str
    repo_head_sha: str
    profile: str
    run_root: str
    output_root: str
    questions: list[dict[str, Any]]
    unknown_questions: int
    hypothesis_questions: int
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


@dataclass
class _RunSession:
    run_id: str
    repo_url: str
    repo_path: Path
    repo_head_sha: str
    profile: str
    run_root: Path
    output_root: Path
    fact_model: Any
    questions: list[dict[str, Any]]
    state: str


ProgressCallback = Callable[[MonitorStageEvent], None]
_RUN_SESSIONS: dict[str, _RunSession] = {}
_RUN_SESSIONS_LOCK = threading.Lock()


def _emit_stage_event(
    callback: ProgressCallback | None,
    *,
    run_id: str,
    state: str,
    stage_id: str,
    message: str,
    percent: int,
) -> None:
    if callback is None:
        return
    event = MonitorStageEvent(
        run_id=run_id,
        state=state,
        stage_id=stage_id,
        message=message,
        percent=max(0, min(100, int(percent))),
    )
    # Callback errors must not break runtime flow.
    try:
        callback(event)
    except Exception:
        return


def _put_session(session: _RunSession) -> None:
    with _RUN_SESSIONS_LOCK:
        _RUN_SESSIONS[session.run_id] = session


def _get_session(run_id: str) -> _RunSession:
    with _RUN_SESSIONS_LOCK:
        session = _RUN_SESSIONS.get(run_id)
    if session is None:
        raise RuntimeError(f"Session not found: {run_id}")
    return session


def discard_session(run_id: str) -> bool:
    with _RUN_SESSIONS_LOCK:
        removed = _RUN_SESSIONS.pop(run_id, None)
    return removed is not None


def _question_counts(questions: list[dict[str, Any]]) -> tuple[int, int]:
    unknown_questions = 0
    hypothesis_questions = 0
    for item in questions:
        qtype = str(item.get("question_type", "unknown")).strip().lower()
        if qtype == "hypothesis":
            hypothesis_questions += 1
        else:
            unknown_questions += 1
    return unknown_questions, hypothesis_questions


def _session_to_start_payload(session: _RunSession) -> MonitorSessionStart:
    unknown_questions, hypothesis_questions = _question_counts(session.questions)
    return MonitorSessionStart(
        run_id=session.run_id,
        repo_url=session.repo_url,
        repo_path=str(session.repo_path),
        repo_head_sha=session.repo_head_sha,
        profile=session.profile,
        run_root=str(session.run_root),
        output_root=str(session.output_root),
        questions=session.questions,
        unknown_questions=unknown_questions,
        hypothesis_questions=hypothesis_questions,
        state=session.state,
    )


def get_session_snapshot(run_id: str) -> MonitorSessionStart | None:
    with _RUN_SESSIONS_LOCK:
        session = _RUN_SESSIONS.get(run_id)
    if session is None:
        return None
    return _session_to_start_payload(session)


def _latest_pack_dir(output_root: Path) -> Path:
    packs = sorted(output_root.glob("pack-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not packs:
        raise RuntimeError("Generated pack directory not found.")
    return packs[0]


def _build_check_result(
    *,
    run_id: str,
    repo_url: str,
    repo_path: Path,
    repo_head_sha: str,
    profile: str,
    output_root: Path,
    error_message: str,
) -> MonitorCheckResult:
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
        repo_head_sha=repo_head_sha,
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


def _start_session_for_repo(
    *,
    run_id: str,
    repo_url: str,
    repo_path: Path,
    run_root: Path,
    profile: str,
    progress_callback: ProgressCallback | None,
) -> MonitorSessionStart:
    output_root = run_root / "o"
    output_root.mkdir(parents=True, exist_ok=True)

    pipeline = BuildPipeline()
    _emit_stage_event(
        progress_callback,
        run_id=run_id,
        state="scanning",
        stage_id="scanning",
        message="Scanner started.",
        percent=35,
    )
    fact_model = pipeline.scanner.scan(repo_path=repo_path, profile=profile)
    questions = pipeline.questionnaire.build_questions(fact_model=fact_model, profile=profile)
    session = _RunSession(
        run_id=run_id,
        repo_url=repo_url,
        repo_path=repo_path,
        repo_head_sha=_git_head_sha(repo_path),
        profile=profile,
        run_root=run_root,
        output_root=output_root,
        fact_model=fact_model,
        questions=questions,
        state="awaiting_answers",
    )
    _put_session(session)
    _emit_stage_event(
        progress_callback,
        run_id=run_id,
        state="awaiting_answers",
        stage_id="awaiting_answers",
        message=f"Questionnaire ready: {len(questions)} items.",
        percent=60,
    )
    return _session_to_start_payload(session)


def start_local_repo_session(
    repo_path: Path,
    workspace_root: Path,
    profile: str = "balanced",
    repo_url: str = "",
    progress_callback: ProgressCallback | None = None,
) -> MonitorSessionStart:
    repo_path = repo_path.resolve()
    if not repo_path.exists():
        raise RuntimeError(f"Repository path not found: {repo_path}")

    stamp = _now_stamp()
    token = uuid4().hex[:8]
    run_id = f"{stamp}_{token}"
    run_root = workspace_root / "s" / f"{stamp}_{token}"
    run_root.mkdir(parents=True, exist_ok=True)
    return _start_session_for_repo(
        run_id=run_id,
        repo_url=repo_url,
        repo_path=repo_path,
        run_root=run_root,
        profile=profile,
        progress_callback=progress_callback,
    )


def start_remote_repo_session(
    repo_url: str,
    workspace_root: Path,
    profile: str = "balanced",
    git_ref: str = "HEAD",
    progress_callback: ProgressCallback | None = None,
) -> MonitorSessionStart:
    slug = repo_slug_from_url(repo_url)
    stamp = _now_stamp()
    token = uuid4().hex[:6]
    run_id = f"{stamp}_{slug}_{token}"
    run_root = workspace_root / "s" / f"{stamp}_{token}"
    run_root.mkdir(parents=True, exist_ok=True)

    _emit_stage_event(
        progress_callback,
        run_id=run_id,
        state="preparing_repo",
        stage_id="preparing_repo",
        message="Repository clone started.",
        percent=10,
    )
    try:
        repo_path = clone_repo_to_run_workspace(repo_url=repo_url, run_root=run_root, git_ref=git_ref)
    except Exception as exc:
        _emit_stage_event(
            progress_callback,
            run_id=run_id,
            state="failed",
            stage_id="preparing_repo",
            message=str(exc),
            percent=100,
        )
        raise

    _emit_stage_event(
        progress_callback,
        run_id=run_id,
        state="preparing_repo",
        stage_id="preparing_repo",
        message="Repository clone completed.",
        percent=25,
    )
    try:
        return _start_session_for_repo(
            run_id=run_id,
            repo_url=repo_url,
            repo_path=repo_path,
            run_root=run_root,
            profile=profile,
            progress_callback=progress_callback,
        )
    except Exception as exc:
        _emit_stage_event(
            progress_callback,
            run_id=run_id,
            state="failed",
            stage_id="scanning",
            message=str(exc),
            percent=100,
        )
        raise


def submit_session_answers(
    run_id: str,
    answers_payload: dict[str, Any] | None = None,
    progress_callback: ProgressCallback | None = None,
    close_session: bool = False,
) -> MonitorCheckResult:
    session = _get_session(run_id)
    session.state = "building_pack"
    _emit_stage_event(
        progress_callback,
        run_id=run_id,
        state="building_pack",
        stage_id="building_pack",
        message="Generate and validate started.",
        percent=75,
    )

    pipeline = BuildPipeline()
    error_message = ""
    try:
        pipeline.run(
            repo_path=session.repo_path,
            output_path=session.output_root,
            profile=session.profile,
            answers=answers_payload or {},
            fact_model=session.fact_model,
        )
    except GateBlockedError as exc:
        error_message = str(exc)
    except Exception as exc:
        session.state = "failed"
        _emit_stage_event(
            progress_callback,
            run_id=run_id,
            state="failed",
            stage_id="building_pack",
            message=str(exc),
            percent=100,
        )
        if close_session:
            discard_session(run_id)
        raise

    result = _build_check_result(
        run_id=session.run_id,
        repo_url=session.repo_url,
        repo_path=session.repo_path,
        repo_head_sha=session.repo_head_sha,
        profile=session.profile,
        output_root=session.output_root,
        error_message=error_message,
    )
    session.state = "completed_blocked" if result.blocking_status else "completed_success"
    _emit_stage_event(
        progress_callback,
        run_id=run_id,
        state=session.state,
        stage_id="completed",
        message="Build completed.",
        percent=100,
    )

    if close_session:
        discard_session(run_id)
    return result


def run_local_repo_check(
    repo_path: Path,
    workspace_root: Path,
    profile: str = "balanced",
    answers_payload: dict[str, Any] | None = None,
    repo_url: str = "",
) -> MonitorCheckResult:
    session = start_local_repo_session(
        repo_path=repo_path,
        workspace_root=workspace_root,
        profile=profile,
        repo_url=repo_url,
    )
    return submit_session_answers(
        run_id=session.run_id,
        answers_payload=answers_payload,
        close_session=True,
    )


def run_remote_repo_check(
    repo_url: str,
    workspace_root: Path,
    profile: str = "balanced",
    git_ref: str = "HEAD",
    answers_payload: dict[str, Any] | None = None,
) -> MonitorCheckResult:
    session = start_remote_repo_session(
        repo_url=repo_url,
        workspace_root=workspace_root,
        profile=profile,
        git_ref=git_ref,
    )
    return submit_session_answers(
        run_id=session.run_id,
        answers_payload=answers_payload,
        close_session=True,
    )
