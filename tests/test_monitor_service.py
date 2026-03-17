import subprocess
import tempfile
import unittest
from pathlib import Path

from opack.monitor.service import load_pilot_repo_urls, repo_slug_from_url, run_local_repo_check


def _run(command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{result.stdout}\n{result.stderr}")


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

            result = run_local_repo_check(
                repo_path=repo,
                workspace_root=Path(ws_tmp),
                profile="balanced",
                answers_payload={"unknown_answers": {"u_workflow_001": "Always escalate on scope changes."}},
            )
            self.assertTrue(Path(result.pack_dir).exists())
            self.assertGreaterEqual(result.quality_score, 0.0)
            self.assertFalse(result.blocking_status)


if __name__ == "__main__":
    unittest.main()
