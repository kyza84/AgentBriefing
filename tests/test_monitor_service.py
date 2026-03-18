import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opack.monitor.service import (
    clone_repo_to_run_workspace,
    get_session_snapshot,
    load_pilot_repo_urls,
    repo_slug_from_url,
    run_local_repo_check,
    start_local_repo_session,
    submit_session_answers,
)


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")


def _init_local_repo(repo: Path) -> None:
    (repo / "pyproject.toml").write_text("[project]\nname='tmp'\n", encoding="utf-8")
    (repo / "main.py").write_text("print('hi')\n", encoding="utf-8")

    _run(["git", "init"], cwd=repo)
    _run(["git", "add", "."], cwd=repo)
    _run(
        [
            "git",
            "-c",
            "user.name=MonitorTest",
            "-c",
            "user.email=monitor@test.local",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
    )


class MonitorServiceTest(unittest.TestCase):
    def test_repo_slug_from_url(self) -> None:
        self.assertEqual(repo_slug_from_url("https://github.com/pallets/flask.git"), "flask")
        self.assertEqual(repo_slug_from_url("https://github.com/vercel/next.js"), "next.js")

    def test_load_pilot_repo_urls(self) -> None:
        registry = Path("docs/pilot_validation/PILOT_REPO_REGISTRY.md").resolve()
        urls = load_pilot_repo_urls(registry)
        self.assertGreaterEqual(len(urls), 10)
        self.assertTrue(any("github.com/pallets/flask" in url for url in urls))

    def test_run_local_repo_check_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as ws_tmp:
            repo = Path(repo_tmp)
            _init_local_repo(repo)

            result = run_local_repo_check(
                repo_path=repo,
                workspace_root=Path(ws_tmp),
                profile="balanced",
                answers_payload={"unknown_answers": {"u_workflow_001": "Always escalate on scope changes."}},
            )
            self.assertTrue(Path(result.pack_dir).exists())
            self.assertGreaterEqual(result.quality_score, 0.0)
            self.assertFalse(result.blocking_status)

    def test_staged_local_session_flow(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as ws_tmp:
            repo = Path(repo_tmp)
            _init_local_repo(repo)

            events: list[tuple[str, str, int]] = []

            def _on_event(event: object) -> None:
                state = str(getattr(event, "state", ""))
                stage_id = str(getattr(event, "stage_id", ""))
                percent = int(getattr(event, "percent", 0))
                events.append((state, stage_id, percent))

            started = start_local_repo_session(
                repo_path=repo,
                workspace_root=Path(ws_tmp),
                profile="balanced",
                progress_callback=_on_event,
            )
            self.assertEqual(started.state, "awaiting_answers")
            self.assertGreaterEqual(len(started.questions), 1)
            self.assertIn("\\s\\", started.run_root.replace("/", "\\"))
            self.assertIn("\\o", started.output_root.replace("/", "\\"))
            self.assertTrue(any(stage_id == "scanning" for _, stage_id, _ in events))
            self.assertTrue(any(state == "awaiting_answers" for state, _, _ in events))

            snapshot = get_session_snapshot(started.run_id)
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.run_id, started.run_id)

            result = submit_session_answers(
                run_id=started.run_id,
                answers_payload={"unknown_answers": {"u_workflow_001": "Escalate on scope change."}},
                progress_callback=_on_event,
                close_session=True,
            )
            self.assertTrue(Path(result.pack_dir).exists())
            self.assertTrue(any(stage_id == "building_pack" for _, stage_id, _ in events))
            self.assertTrue(any(stage_id == "completed" for _, stage_id, _ in events))
            self.assertIsNone(get_session_snapshot(started.run_id))

    def test_submit_session_answers_missing_session(self) -> None:
        with self.assertRaises(RuntimeError):
            submit_session_answers(run_id="missing-run-id", answers_payload={})

    def test_clone_repo_uses_longpaths_git_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_root = Path(tmp_dir)
            with patch("opack.monitor.service._run_command") as run_cmd:
                run_cmd.side_effect = [
                    subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
                    subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
                ]
                repo_dir = clone_repo_to_run_workspace(
                    repo_url="https://github.com/example/repo.git",
                    run_root=run_root,
                )
                self.assertEqual(repo_dir, run_root / "r")
                clone_command = run_cmd.call_args_list[0].args[0]
                self.assertIn("-c", clone_command)
                self.assertIn("core.longpaths=true", clone_command)
                self.assertIn("--config", clone_command)


if __name__ == "__main__":
    unittest.main()
