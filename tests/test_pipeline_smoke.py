import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from opack.contracts.models import CiJobFact, CiPipelineFact, FactModel, HypothesisItem, PolicyModel, UnknownItem
from opack.engines.questionnaire import QuestionnaireEngine
from opack.engines.scanner import ScannerEngine
from opack.engines.validator import ValidatorEngine
from opack.orchestrators.build_pipeline import BuildPipeline


class PipelineSmokeTest(unittest.TestCase):
    def test_build_pipeline_generates_output(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as out_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "README.md").write_text("# sample\n", encoding="utf-8")
            (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (repo / "tests").mkdir(parents=True, exist_ok=True)
            (repo / "tests" / "test_sample.py").write_text(
                "def test_ok():\n    assert True\n",
                encoding="utf-8",
            )
            (repo / "Makefile").write_text("test:\n\tpython -m unittest discover -s tests -v\n", encoding="utf-8")

            pipeline = BuildPipeline()
            result = pipeline.run(repo_path=repo, output_path=Path(out_tmp), profile="balanced")

            output_dir = Path(result["output_dir"])
            self.assertTrue(output_dir.exists())
            self.assertTrue((output_dir / "OPERATING_PACK_MANIFEST.json").exists())
            self.assertTrue((output_dir / "VALIDATION_REPORT.json").exists())
            validation = json.loads((output_dir / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))
            self.assertFalse(validation["blocking_status"])
            self.assertEqual(len(validation["issues"]), 0)

    def test_generator_phase4_rich_russian_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as out_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")

            pipeline = BuildPipeline()
            result = pipeline.run(
                repo_path=repo,
                output_path=Path(out_tmp),
                profile="balanced",
                answers={"unknown_answers": {"u_workflow_001": "Не менять scope без эскалации."}},
            )

            pack_dir = Path(result["output_dir"])
            architecture = (pack_dir / "PROJECT_ARCHITECTURE.md").read_text(encoding="utf-8")
            state = (pack_dir / "PROJECT_STATE.md").read_text(encoding="utf-8")
            first_message = (pack_dir / "FIRST_MESSAGE_INSTRUCTIONS.md").read_text(encoding="utf-8")

            self.assertIn("## Обнаруженные стеки", architecture)
            self.assertIn("## Точки входа и команды запуска", architecture)
            self.assertIn("## Открытые решения", architecture)
            self.assertIn("## Неопределенности и риски", state)
            self.assertIn("## Чеклист первого сообщения", first_message)

    def test_generator_phase2_parity_contract_sections_present(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp, tempfile.TemporaryDirectory() as out_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (repo / "tests").mkdir(parents=True, exist_ok=True)
            (repo / "tests" / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (repo / "Makefile").write_text("test:\n\tpython -m unittest discover -s tests -v\n", encoding="utf-8")

            pipeline = BuildPipeline()
            result = pipeline.run(
                repo_path=repo,
                output_path=Path(out_tmp),
                profile="balanced",
                answers={"unknown_answers": {"u_workflow_001": "Scope changes only after escalation."}},
            )
            pack_dir = Path(result["output_dir"])

            architecture = (pack_dir / "PROJECT_ARCHITECTURE.md").read_text(encoding="utf-8")
            state = (pack_dir / "PROJECT_STATE.md").read_text(encoding="utf-8")
            first_message = (pack_dir / "FIRST_MESSAGE_INSTRUCTIONS.md").read_text(encoding="utf-8")
            handoff = (pack_dir / "HANDOFF_PROTOCOL.md").read_text(encoding="utf-8")
            behavior = (pack_dir / "AGENT_BEHAVIOR_RULES.md").read_text(encoding="utf-8")
            context_policy = (pack_dir / "CONTEXT_UPDATE_POLICY.md").read_text(encoding="utf-8")
            tracking = (pack_dir / "TASK_TRACKING_PROTOCOL.md").read_text(encoding="utf-8")

            self.assertIn("## Модули и границы", architecture)
            self.assertIn("## Внешние интеграции и CI/CD", architecture)
            self.assertIn("## Зависимости между модулями", architecture)
            self.assertIn("## Критичные файлы", architecture)
            self.assertIn("## Открытые решения", architecture)

            self.assertIn("## Снимок прогона", state)
            self.assertIn("## Операционная готовность", state)
            self.assertIn("## Предупреждения сканера", state)

            self.assertIn("## Порядок чтения контекста", first_message)
            self.assertIn("## Что проверить после изменений", first_message)
            self.assertIn("## Открытые решения перед рисковыми правками", first_message)

            self.assertIn("## Обязательный шаблон handoff", handoff)
            self.assertIn("## Что осталось открытым", handoff)

            self.assertIn("## Конфликты и ограничения", behavior)
            self.assertIn("## Открытые решения", behavior)

            self.assertIn("## Обязательные файлы", context_policy)
            self.assertIn("## Проверка перед push", context_policy)

            self.assertIn("## Лимит и статусы активных задач", tracking)
            self.assertIn("## Правила архивации", tracking)

    def test_scanner_phase2_baseline_extracts_core_signals(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text(
                "[project]\nname='sample'\n[project.scripts]\nopack='opack.cli:main'\n",
                encoding="utf-8",
            )
            (repo / "Makefile").write_text("test:\n\tpython -m unittest\n", encoding="utf-8")
            (repo / "Dockerfile").write_text("FROM python:3.11\n", encoding="utf-8")
            (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertIn("python", fact.detected_stacks)
            self.assertTrue(any("main.py" in p for p in fact.entry_points))
            self.assertIn("docker", fact.environments)
            self.assertTrue(any("make test" == c for c in fact.key_commands))
            self.assertGreater(fact.confidence_overall, 0.0)
            self.assertTrue(any(u.unknown_id == "u_workflow_001" for u in fact.unknowns))

    def test_scanner_ranking_demotes_docs_and_tests_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "src").mkdir(parents=True, exist_ok=True)
            (repo / "docs_src").mkdir(parents=True, exist_ok=True)
            (repo / "tests").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "main.py").write_text("print('src')\n", encoding="utf-8")
            (repo / "docs_src" / "main.py").write_text("print('docs')\n", encoding="utf-8")
            (repo / "tests" / "main.py").write_text("print('tests')\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertGreaterEqual(len(fact.entry_points), 3)
            self.assertEqual(fact.entry_points[0], "src/main.py")
            self.assertIn("docs_src/main.py", fact.entry_points)
            self.assertIn("tests/main.py", fact.entry_points)

    def test_scanner_rank_key_commands_demotes_release_like_commands(self) -> None:
        scanner = ScannerEngine()
        ranked = scanner._rank_key_commands(
            [
                "npm run publish:test",
                "npm run test",
                "npm run test:cov",
                "npm run deploy",
                "npm run docs",
            ]
        )
        self.assertEqual(ranked[0], "npm run test")
        self.assertGreater(ranked.index("npm run publish:test"), ranked.index("npm run test"))

    def test_scanner_ignores_service_workdirs_in_release_mode(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")

            monitor_dir = repo / ".monitor"
            monitor_dir.mkdir(parents=True, exist_ok=True)
            (monitor_dir / "package.json").write_text('{"name":"noise","scripts":{"test":"jest"}}', encoding="utf-8")
            (monitor_dir / "index.js").write_text("console.log('noise')\n", encoding="utf-8")

            pilot_dir = repo / "pilot_runs"
            pilot_dir.mkdir(parents=True, exist_ok=True)
            (pilot_dir / "go.mod").write_text("module noise\n\ngo 1.21\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(fact.detected_stacks, ["python"])
            self.assertFalse(any("index.js" in entry for entry in fact.entry_points))
            self.assertTrue(all(module.name not in {".monitor", "pilot_runs"} for module in fact.modules))

    def test_scanner_does_not_ignore_repo_when_parent_folder_matches_service_name(self) -> None:
        with tempfile.TemporaryDirectory() as root_tmp:
            repo = Path(root_tmp) / "pilot_workspace" / "real_repo"
            repo.mkdir(parents=True, exist_ok=True)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "main.py").write_text("print('ok')\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertIn("python", fact.detected_stacks)
            self.assertTrue(any("main.py" in entry for entry in fact.entry_points))
            self.assertFalse(any(w == "No files found during scan." for w in fact.scanner_warnings))

    def test_scanner_extracts_operational_facts_for_tests_ci_and_critical_files(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "app").mkdir(parents=True, exist_ok=True)
            (repo / "app" / "main.py").write_text("print('run')\n", encoding="utf-8")
            (repo / "tests").mkdir(parents=True, exist_ok=True)
            (repo / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "name: CI\n"
                "on: [push, pull_request]\n"
                "jobs:\n"
                "  build:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: python -m unittest discover -s tests -v\n"
                "  deploy:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: docker push sample:latest\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertTrue(fact.tests_map)
            self.assertTrue(any(item.path == "tests" for item in fact.tests_map))
            self.assertTrue(fact.ci_pipeline_map)
            self.assertTrue(any("push" in pipeline.triggers for pipeline in fact.ci_pipeline_map))
            self.assertTrue(any(item.path == ".github/workflows/ci.yml" for item in fact.critical_files_map))
            self.assertTrue(any(item.path == "pyproject.toml" for item in fact.critical_files_map))
            hypothesis_ids = {item.hypothesis_id for item in fact.hypotheses}
            self.assertIn("h_entrypoint_001", hypothesis_ids)
            self.assertIn("h_command_001", hypothesis_ids)
            self.assertIn("h_tests_001", hypothesis_ids)
            self.assertIn("h_ci_001", hypothesis_ids)
            self.assertIn("operational_confidence", fact.confidence_breakdown)

    def test_scanner_ci_keeps_prioritized_workflow_order_for_primary_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "add-to-project.yml").write_text(
                "name: Add to Project\n"
                "on: [issues]\n"
                "jobs:\n"
                "  triage:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: echo triage\n",
                encoding="utf-8",
            )
            (repo / ".github" / "workflows" / "test.yml").write_text(
                "name: Test\n"
                "on: [push, pull_request]\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: python -m unittest discover -s tests -v\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertGreaterEqual(len(fact.ci_pipeline_map), 2)
            self.assertEqual(fact.ci_pipeline_map[0].file, ".github/workflows/test.yml")
            self.assertEqual(fact.ci_pipeline_map[1].file, ".github/workflows/add-to-project.yml")

    def test_scanner_ci_triggers_ignore_nested_workflow_dispatch_fields(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "name: CI\n"
                "on:\n"
                "  workflow_dispatch:\n"
                "    inputs:\n"
                "      environment:\n"
                "        description: Target env\n"
                "        required: true\n"
                "  push:\n"
                "    branches: [main]\n"
                "jobs:\n"
                "  build:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: python -m unittest discover -s tests -v\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(len(fact.ci_pipeline_map), 1)
            triggers = set(fact.ci_pipeline_map[0].triggers)
            self.assertEqual(triggers, {"workflow_dispatch", "push"})
            self.assertFalse({"inputs", "description", "required", "branches"} & triggers)
            self.assertIn("branches=main", fact.ci_pipeline_map[0].trigger_filters.get("push", []))

    def test_scanner_ci_parses_inline_map_events_and_filters(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "name: Inline CI\n"
                "on: {push: {branches: [main, release/*]}, pull_request: {types: [opened, synchronize]}, workflow_dispatch: {}}\n"
                "jobs:\n"
                "  build:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: python -m unittest discover -s tests -v\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(len(fact.ci_pipeline_map), 1)
            pipeline = fact.ci_pipeline_map[0]
            self.assertEqual(set(pipeline.triggers), {"push", "pull_request", "workflow_dispatch"})
            self.assertIn("branches=main", pipeline.trigger_filters.get("push", []))
            self.assertIn("branches=release/*", pipeline.trigger_filters.get("push", []))
            self.assertIn("types=opened", pipeline.trigger_filters.get("pull_request", []))
            self.assertIn("types=synchronize", pipeline.trigger_filters.get("pull_request", []))

    def test_scanner_ci_parses_block_filters_and_critical_job_steps(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "name: Deploy CI\n"
                "on:\n"
                "  push:\n"
                "    branches:\n"
                "      - main\n"
                "    paths:\n"
                "      - src/**\n"
                "  schedule:\n"
                "    - cron: \"0 3 * * *\"\n"
                "jobs:\n"
                "  deploy_prod:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: ./deploy.sh\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(len(fact.ci_pipeline_map), 1)
            pipeline = fact.ci_pipeline_map[0]
            self.assertEqual(set(pipeline.triggers), {"push", "schedule"})
            self.assertIn("branches=main", pipeline.trigger_filters.get("push", []))
            self.assertIn("paths=src/**", pipeline.trigger_filters.get("push", []))
            self.assertTrue(any(job.job_id == "deploy_prod" for job in pipeline.jobs))
            deploy_job = next(job for job in pipeline.jobs if job.job_id == "deploy_prod")
            self.assertTrue(any("run: ./deploy.sh" == step for step in deploy_job.critical_steps))
            self.assertTrue(any("run: ./deploy.sh" == step for step in pipeline.critical_steps))

    def test_scanner_ci_ast_parses_block_scalar_run_command(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "release.yml").write_text(
                "name: Release Workflow\n"
                "on:\n"
                "  push:\n"
                "    branches: [main]\n"
                "jobs:\n"
                "  deploy_prod:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - run: |\n"
                "          echo preparing release\n"
                "          ./deploy.sh\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(len(fact.ci_pipeline_map), 1)
            pipeline = fact.ci_pipeline_map[0]
            self.assertEqual(set(pipeline.triggers), {"push"})
            self.assertTrue(any(job.job_id == "deploy_prod" for job in pipeline.jobs))
            deploy_job = next(job for job in pipeline.jobs if job.job_id == "deploy_prod")
            self.assertTrue(any("deploy.sh" in step for step in deploy_job.critical_steps))
            self.assertTrue(any("deploy.sh" in step for step in pipeline.critical_steps))

    def test_scanner_ci_ast_parses_filters_with_inline_comments(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (repo / ".github" / "workflows" / "ci.yml").write_text(
                "name: Commented CI\n"
                "on:\n"
                "  pull_request:\n"
                "    types: [opened, synchronize] # PR event types\n"
                "  push:\n"
                "    branches: [main] # protected branch\n"
                "jobs:\n"
                "  build:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: python -m unittest discover -s tests -v\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(len(fact.ci_pipeline_map), 1)
            pipeline = fact.ci_pipeline_map[0]
            self.assertEqual(set(pipeline.triggers), {"pull_request", "push"})
            self.assertIn("types=opened", pipeline.trigger_filters.get("pull_request", []))
            self.assertIn("types=synchronize", pipeline.trigger_filters.get("pull_request", []))
            self.assertIn("branches=main", pipeline.trigger_filters.get("push", []))

    def test_scanner_extracts_module_dependency_map(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "core").mkdir(parents=True, exist_ok=True)
            (repo / "services").mkdir(parents=True, exist_ok=True)
            (repo / "api").mkdir(parents=True, exist_ok=True)
            (repo / "core" / "utils.py").write_text("def ping():\n    return 'pong'\n", encoding="utf-8")
            (repo / "services" / "runner.py").write_text("from core.utils import ping\n", encoding="utf-8")
            (repo / "api" / "handler.py").write_text("from services.runner import ping\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            edge_pairs = {(edge.source_module, edge.target_module) for edge in fact.module_dependency_map}
            self.assertIn(("services", "core"), edge_pairs)
            self.assertIn(("api", "services"), edge_pairs)

    def test_scanner_extracts_module_dependency_map_for_src_layout(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "src" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "services").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "api").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "core" / "utils.py").write_text("def ping():\n    return 'pong'\n", encoding="utf-8")
            (repo / "src" / "services" / "runner.py").write_text("from core.utils import ping\n", encoding="utf-8")
            (repo / "src" / "api" / "handler.py").write_text("from services.runner import ping\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            edge_pairs = {(edge.source_module, edge.target_module) for edge in fact.module_dependency_map}
            self.assertIn(("services", "core"), edge_pairs)
            self.assertIn(("api", "services"), edge_pairs)

    def test_scanner_dependency_map_python_package_root_submodules(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "src" / "myapp" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "myapp" / "services").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "myapp" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "src" / "myapp" / "core" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "src" / "myapp" / "services" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "src" / "myapp" / "core" / "utils.py").write_text("def ping():\n    return 'pong'\n", encoding="utf-8")
            (repo / "src" / "myapp" / "services" / "runner.py").write_text(
                "from myapp.core.utils import ping\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            edge_pairs = {(edge.source_module, edge.target_module) for edge in fact.module_dependency_map}
            self.assertIn(("services", "core"), edge_pairs)
            self.assertFalse(any(source.endswith(".py") for source, _ in edge_pairs))

    def test_scanner_dependency_map_python_relative_import_prefers_module_tail(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "src" / "myapp" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "myapp" / "services").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "myapp" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "src" / "myapp" / "core" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "src" / "myapp" / "services" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "src" / "myapp" / "core" / "utils.py").write_text("def ping():\n    return 'pong'\n", encoding="utf-8")
            (repo / "src" / "myapp" / "services" / "runner.py").write_text(
                "from ..core.utils import ping\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            edge_pairs = {(edge.source_module, edge.target_module) for edge in fact.module_dependency_map}
            self.assertIn(("services", "core"), edge_pairs)
            self.assertNotIn(("services", "src"), edge_pairs)

    def test_scanner_does_not_infer_tests_map_without_test_files(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "main.py").write_text("print('hello')\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            self.assertEqual(fact.tests_map, [])
            self.assertFalse(any(cmd == "python -m unittest discover -s tests -v" for cmd in fact.key_commands))
            unknown_ids = {item.unknown_id for item in fact.unknowns}
            self.assertIn("u_tests_001", unknown_ids)

    def test_scanner_dependency_map_ts_alias_paths(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "package.json").write_text('{"name":"sample","scripts":{"test":"npm run test"}}\n', encoding="utf-8")
            (repo / "tsconfig.json").write_text(
                "{\n"
                "  \"compilerOptions\": {\n"
                "    \"baseUrl\": \".\",\n"
                "    \"paths\": {\n"
                "      \"@app/*\": [\"src/app/*\"],\n"
                "      \"@core\": [\"src/core/index.ts\"]\n"
                "    }\n"
                "  }\n"
                "}\n",
                encoding="utf-8",
            )
            (repo / "src" / "app").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "app" / "runner.ts").write_text("import { ping } from '@core';\n", encoding="utf-8")
            (repo / "src" / "core" / "index.ts").write_text("export const ping = () => 'ok';\n", encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            edge_pairs = {(edge.source_module, edge.target_module) for edge in fact.module_dependency_map}
            self.assertIn(("app", "core"), edge_pairs)

    def test_scanner_dependency_map_go_module_path_imports(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "go.mod").write_text("module github.com/acme/sample\n\ngo 1.21\n", encoding="utf-8")
            (repo / "cmd").mkdir(parents=True, exist_ok=True)
            (repo / "internal" / "service").mkdir(parents=True, exist_ok=True)
            (repo / "internal" / "service" / "service.go").write_text(
                "package service\n\nfunc Ping() string { return \"ok\" }\n",
                encoding="utf-8",
            )
            (repo / "cmd" / "main.go").write_text(
                "package main\n\nimport \"github.com/acme/sample/internal/service\"\n\nfunc main() { _ = service.Ping() }\n",
                encoding="utf-8",
            )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="balanced")

            edge_pairs = {(edge.source_module, edge.target_module) for edge in fact.module_dependency_map}
            self.assertIn(("cmd", "internal"), edge_pairs)

    def test_scanner_quick_guardrails_activate_on_ci_workflow_cap(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            workflows = repo / ".github" / "workflows"
            workflows.mkdir(parents=True, exist_ok=True)

            for idx in range(45):
                (workflows / f"ci_{idx:03d}.yml").write_text(
                    "name: CI\n"
                    "on: [push]\n"
                    "jobs:\n"
                    "  build:\n"
                    "    runs-on: ubuntu-latest\n"
                    "    steps:\n"
                    "      - run: python -m unittest discover -s tests -v\n",
                    encoding="utf-8",
                )

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="quick")

            self.assertTrue(fact.scan_guardrails.get("activated"))
            self.assertIn("ci_workflow_cap", fact.scan_guardrails.get("reasons", []))
            self.assertLessEqual(len(fact.ci_pipeline_map), 35)
            self.assertTrue(any(item.unknown_id == "u_scan_budget_001" for item in fact.unknowns))
            self.assertTrue(any(item.hypothesis_id == "h_scan_budget_001" for item in fact.hypotheses))
            self.assertTrue(any("Guardrail" in warning for warning in fact.scanner_warnings))

    def test_scanner_quick_guardrails_skip_oversized_dependency_files(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "src" / "app").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "core").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "app" / "main.py").write_text("from core.big import payload\n", encoding="utf-8")
            big_payload = "x = 'a'\\n" * 50000
            (repo / "src" / "core" / "big.py").write_text(big_payload, encoding="utf-8")

            scanner = ScannerEngine()
            fact = scanner.scan(repo_path=repo, profile="quick")

            self.assertTrue(fact.scan_guardrails.get("activated"))
            self.assertIn("dependency_large_file_skip", fact.scan_guardrails.get("reasons", []))
            self.assertTrue(any("oversized source file" in warning for warning in fact.scanner_warnings))
            self.assertTrue(any(item.unknown_id == "u_scan_budget_001" for item in fact.unknowns))

    def test_scanner_guardrail_time_budget_uses_stabilization_grace(self) -> None:
        scanner = ScannerEngine()
        guardrail_state = {
            "time_budget_sec": 10.0,
            "time_budget_grace_sec": 0.4,
        }

        with patch("opack.engines.scanner.time.perf_counter", return_value=10.39):
            self.assertFalse(scanner._time_budget_exceeded(guardrail_state=guardrail_state, scan_started_at=0.0))
        with patch("opack.engines.scanner.time.perf_counter", return_value=10.41):
            self.assertTrue(scanner._time_budget_exceeded(guardrail_state=guardrail_state, scan_started_at=0.0))

    def test_scanner_collect_files_is_sorted_for_repeatability(self) -> None:
        with tempfile.TemporaryDirectory() as repo_tmp:
            repo = Path(repo_tmp)
            (repo / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (repo / "src").mkdir(parents=True, exist_ok=True)
            (repo / "src" / "B.py").write_text("print('b')\n", encoding="utf-8")
            (repo / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
            (repo / "alpha.txt").write_text("alpha\n", encoding="utf-8")

            scanner = ScannerEngine()
            files, _warnings = scanner._collect_files(repo=repo)
            rel_paths = [path.relative_to(repo).as_posix() for path in files]

            self.assertEqual(rel_paths, sorted(rel_paths, key=str.lower))

    def test_questionnaire_resolves_unknowns_from_answers(self) -> None:
        engine = QuestionnaireEngine()
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow unknown",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                ),
                UnknownItem(
                    unknown_id="u_commands_001",
                    area="workflow",
                    description="Command unknown",
                    impact_level="high",
                    suggested_question="Canonical commands?",
                ),
            ],
        )

        answers = {
            "unknown_answers": {
                "u_workflow_001": "Always ask approval before destructive changes.",
            }
        }
        policy = engine.build_policy_model(fact_model=fact_model, profile="balanced", answers=answers)

        self.assertIn("u_workflow_001", policy.resolved_unknowns)
        self.assertIn("u_commands_001", policy.open_unknowns)
        self.assertGreater(policy.answer_confidence, 0.0)
        self.assertTrue(any("Workflow boundary:" in rule for rule in policy.agent_behavior_rules))

    def test_questionnaire_respects_question_budget_for_quick_profile(self) -> None:
        engine = QuestionnaireEngine()
        unknowns = [
            UnknownItem(
                unknown_id=f"u_{idx:03d}",
                area="workflow",
                description=f"Unknown {idx}",
                impact_level="medium",
                suggested_question=f"Question {idx}?",
            )
            for idx in range(15)
        ]
        fact_model = FactModel(repo_id="repo", unknowns=unknowns)

        questions = engine.build_questions(fact_model=fact_model, profile="quick")
        self.assertEqual(len(questions), 10)

    def test_questionnaire_enforces_profile_minimum_question_floor(self) -> None:
        engine = QuestionnaireEngine()
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow unknown",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                )
            ],
            entry_points=["main.py"],
            key_commands=["python -m app"],
        )

        quick_questions = engine.build_questions(fact_model=fact_model, profile="quick")
        balanced_questions = engine.build_questions(fact_model=fact_model, profile="balanced")
        strict_questions = engine.build_questions(fact_model=fact_model, profile="strict")

        self.assertGreaterEqual(len(quick_questions), 3)
        self.assertGreaterEqual(len(balanced_questions), 5)
        self.assertGreaterEqual(len(strict_questions), 7)

        self.assertTrue(any(item.get("question_type") == "hypothesis" for item in quick_questions))
        self.assertTrue(any(str(item.get("target_id", "")).startswith("h_floor_") for item in strict_questions))

    def test_questionnaire_prioritizes_hypothesis_questions_and_hides_duplicate_unknown(self) -> None:
        engine = QuestionnaireEngine()
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_hypothesis_001",
                    area="delivery",
                    description="Need confirm CI hypothesis",
                    impact_level="high",
                    suggested_question="Confirm CI hypothesis?",
                ),
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow boundary",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                ),
            ],
            hypotheses=[
                HypothesisItem(
                    hypothesis_id="h_ci_001",
                    area="delivery",
                    claim="Main CI workflow is .github/workflows/ci.yml",
                    confidence=0.31,
                    evidence=["workflow file detected"],
                    requires_confirmation=True,
                    suggested_question="CI workflow is .github/workflows/ci.yml, correct?",
                )
            ],
        )

        questions = engine.build_questions(fact_model=fact_model, profile="quick")
        self.assertEqual(questions[0]["question_type"], "hypothesis")
        self.assertEqual(questions[0]["target_id"], "h_ci_001")
        self.assertFalse(any(item.get("unknown_id") == "u_hypothesis_001" for item in questions))

    def test_questionnaire_resolves_hypothesis_unknown_from_confirm_edit_reject_answers(self) -> None:
        engine = QuestionnaireEngine()
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_hypothesis_001",
                    area="architecture",
                    description="Entrypoint hypothesis confirmation required",
                    impact_level="medium",
                    suggested_question="Is manage.py canonical entrypoint?",
                )
            ],
            hypotheses=[
                HypothesisItem(
                    hypothesis_id="h_entrypoint_001",
                    area="architecture",
                    claim="Canonical entrypoint: manage.py",
                    confidence=0.55,
                    evidence=["manage.py detected"],
                    requires_confirmation=True,
                    suggested_question="Confirm canonical entrypoint manage.py?",
                )
            ],
        )

        policy = engine.build_policy_model(
            fact_model=fact_model,
            profile="balanced",
            answers={"hypothesis_answers": {"h_entrypoint_001": "edit:Canonical entrypoint: app/main.py"}},
        )

        self.assertIn("u_hypothesis_001", policy.resolved_unknowns)
        self.assertNotIn("u_hypothesis_001", policy.open_unknowns)
        self.assertTrue(any("Canonical project entrypoint:" in rule for rule in policy.handoff_rules))
        self.assertGreater(policy.answer_confidence, 0.0)

    def _validator_ready_artifacts(self) -> dict[str, str]:
        return {
            "PROJECT_ARCHITECTURE.md": (
                "# PROJECT_ARCHITECTURE\n\n"
                "## Обнаруженные стеки\n"
                "- python\n\n"
                "## Модули и границы\n"
                "- module\n\n"
                "## Точки входа и команды запуска\n"
                "- entry: main.py\n"
                "- cmd: python -m unittest discover -s tests -v\n\n"
                "## Внешние интеграции и CI/CD\n"
                "- ext\n\n"
                "## Зависимости между модулями\n"
                "- module -> core\n\n"
                "## Критичные файлы\n"
                "- pyproject.toml\n\n"
                "## Открытые решения\n"
                "- u_workflow_001: open\n"
            ),
            "PROJECT_STATE.md": (
                "# PROJECT_STATE\n\n"
                "## Снимок прогона\n"
                "- repo_id=repo\n\n"
                "## Операционная готовность\n"
                "- entry_points=1\n"
                "- key_commands=1\n\n"
                "## Неопределенности и риски\n"
                "- u_workflow_001: open\n\n"
                "## Предупреждения сканера\n"
                "- none\n"
            ),
            "FIRST_MESSAGE_INSTRUCTIONS.md": (
                "# FIRST_MESSAGE_INSTRUCTIONS\n\n"
                "## Порядок чтения контекста\n"
                "1. PROJECT_STATE.md\n\n"
                "## Чеклист первого сообщения\n"
                "1. main.py\n\n"
                "## Что проверить после изменений\n"
                "- python -m unittest discover -s tests -v\n\n"
                "## Открытые решения перед рисковыми правками\n"
                "- u_workflow_001: open\n"
            ),
            "HANDOFF_PROTOCOL.md": (
                "# HANDOFF_PROTOCOL\n\n"
                "## Что передать в следующий чат\n"
                "- Rule B\n\n"
                "## Обязательный шаблон handoff\n"
                "1. next\n\n"
                "## Что осталось открытым\n"
                "- u_workflow_001: open\n"
            ),
            "AGENT_BEHAVIOR_RULES.md": (
                "# AGENT_BEHAVIOR_RULES\n\n"
                "## Базовые правила\n"
                "- Rule A\n\n"
                "## Эскалация\n"
                "- Rule D\n\n"
                "## Конфликты и ограничения\n"
                "- none\n\n"
                "## Открытые решения\n"
                "- u_workflow_001: open\n"
            ),
            "CONTEXT_UPDATE_POLICY.md": (
                "# CONTEXT_UPDATE_POLICY\n\n"
                "## Когда обновлять контекст\n"
                "- Rule C\n\n"
                "## Обязательные файлы\n"
                "1. docs/PROJECT_STATE.md\n\n"
                "## Порядок обновления\n"
                "1. sync\n\n"
                "## Проверка перед push\n"
                "1. done\n"
            ),
            "TASK_TRACKING_PROTOCOL.md": (
                "# TASK_TRACKING_PROTOCOL\n\n"
                "## Лимит и статусы активных задач\n"
                "- <= 12\n\n"
                "## Формат отчета по итерации\n"
                "1. Completed\n\n"
                "## Правила архивации\n"
                "- archive\n"
            ),
            "VALIDATION_REPORT.json": "{}",
        }

    def _validator_ready_policy(self, **overrides: object) -> PolicyModel:
        payload: dict[str, object] = {
            "decision_profile": "balanced",
            "agent_behavior_rules": ["Rule A"],
            "handoff_rules": ["Rule B"],
            "context_update_rules": ["Rule C"],
            "escalation_rules": ["Rule D"],
            "task_tracking_rules": ["Rule E"],
            "answer_confidence": 1.0,
        }
        payload.update(overrides)
        return PolicyModel(**payload)

    def test_validator_allows_fully_resolved_unknowns(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow unknown",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                )
            ],
        )
        questionnaire = QuestionnaireEngine()
        policy_model = questionnaire.build_policy_model(
            fact_model=fact_model,
            answers={"unknown_answers": {"u_workflow_001": "Never change production without approval."}},
        )
        validator = ValidatorEngine()
        report = validator.validate(
            artifacts={
                "PROJECT_ARCHITECTURE.md": "ok",
                "PROJECT_STATE.md": "ok",
                "FIRST_MESSAGE_INSTRUCTIONS.md": "ok",
                "HANDOFF_PROTOCOL.md": "ok",
                "AGENT_BEHAVIOR_RULES.md": "ok",
                "CONTEXT_UPDATE_POLICY.md": "ok",
                "TASK_TRACKING_PROTOCOL.md": "ok",
                "VALIDATION_REPORT.json": "{}",
            },
            fact_model=fact_model,
            policy_model=policy_model,
        )
        self.assertFalse(any(issue.issue_id == "unknown_mismatch" for issue in report.issues))

    def test_validator_phase5_detects_unknown_resolution_overlap(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow unknown",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                )
            ],
        )
        policy_model = PolicyModel(
            decision_profile="balanced",
            agent_behavior_rules=["Rule A"],
            handoff_rules=["Rule B"],
            context_update_rules=["Rule C"],
            escalation_rules=["Rule D"],
            task_tracking_rules=["Rule E"],
            resolved_unknowns=["u_workflow_001"],
            open_unknowns=["u_workflow_001"],
            answer_confidence=1.0,
        )
        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("unknown_resolution_overlap", issue_ids)

    def test_validator_phase5_checks_visibility_for_all_open_unknowns(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["python -m unittest discover -s tests -v"],
            confidence_overall=0.9,
            unknowns=[
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow unknown",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                ),
                UnknownItem(
                    unknown_id="u_tests_001",
                    area="testing",
                    description="Tests unknown",
                    impact_level="high",
                    suggested_question="Where are tests?",
                ),
            ],
        )
        policy_model = self._validator_ready_policy(open_unknowns=["u_workflow_001", "u_tests_001"])

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("project_state_unknown_visibility_gap", issue_ids)
        self.assertIn("architecture_unknown_visibility_gap", issue_ids)
        self.assertIn("first_message_unknown_visibility_gap", issue_ids)
        self.assertIn("handoff_unknown_visibility_gap", issue_ids)
        self.assertIn("behavior_unknown_visibility_gap", issue_ids)

    def test_validator_phase5_detects_operability_gaps_without_unknowns(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            unknowns=[
                UnknownItem(
                    unknown_id="u_workflow_001",
                    area="workflow",
                    description="Workflow unknown",
                    impact_level="high",
                    suggested_question="Workflow boundary?",
                )
            ],
            confidence_overall=0.8,
        )
        policy_model = PolicyModel(
            decision_profile="balanced",
            agent_behavior_rules=["Rule A"],
            handoff_rules=["Rule B"],
            context_update_rules=["Rule C"],
            escalation_rules=["Rule D"],
            task_tracking_rules=["Rule E"],
            open_unknowns=["u_workflow_001"],
            answer_confidence=0.5,
        )
        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("operability_entrypoint_missing_without_unknown", issue_ids)
        self.assertIn("operability_commands_missing_without_unknown", issue_ids)
        self.assertTrue(report.blocking_status)

    def test_validator_phase4_detects_unconfirmed_fallback_entrypoint_without_tracking(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["README.md (manual entrypoint reference)"],
            hypotheses=[
                HypothesisItem(
                    hypothesis_id="h_entrypoint_001",
                    area="architecture",
                    claim="Canonical entrypoint: README.md (manual entrypoint reference)",
                    confidence=0.55,
                    requires_confirmation=True,
                    suggested_question="Confirm canonical entrypoint?",
                )
            ],
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("entrypoint_fallback_unconfirmed", issue_ids)
        self.assertTrue(report.blocking_status)

    def test_validator_phase4_detects_ci_signal_without_pipeline_map(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            environments=["github-actions"],
            external_integrations=["github-actions"],
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("ci_pipeline_map_missing", issue_ids)
        self.assertTrue(report.blocking_status)

    def test_validator_phase4_allows_ci_missing_map_when_guardrail_unknown_is_tracked(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["python -m unittest discover -s tests -v"],
            environments=["github-actions"],
            external_integrations=["github-actions"],
            scan_guardrails={"activated": True, "reasons": ["time_budget_exceeded_before_ci_scan"]},
            unknowns=[
                UnknownItem(
                    unknown_id="u_scan_budget_001",
                    area="scanner",
                    description="Guardrail active",
                    impact_level="medium",
                    suggested_question="Run balanced?",
                )
            ],
        )
        policy_model = self._validator_ready_policy(open_unknowns=["u_scan_budget_001"])

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertNotIn("ci_pipeline_map_missing", issue_ids)
        self.assertIn("ci_pipeline_map_sampled_due_guardrail", issue_ids)
        self.assertFalse(report.blocking_status)

    def test_validator_phase4_detects_missing_test_command_without_unknown(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["make build"],
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("test_command_missing_without_unknown", issue_ids)
        self.assertTrue(report.blocking_status)

    def test_validator_phase4_warns_when_ci_pipeline_map_lacks_detail(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["python -m unittest discover -s tests -v"],
            environments=["github-actions"],
            external_integrations=["github-actions"],
            ci_pipeline_map=[
                CiPipelineFact(
                    provider="github-actions",
                    file=".github/workflows/ci.yml",
                    name="CI",
                )
            ],
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("ci_pipeline_map_triggers_missing", issue_ids)
        self.assertIn("ci_pipeline_map_jobs_missing", issue_ids)
        self.assertFalse(report.blocking_status)

    def test_validator_phase4_warns_when_test_gap_is_only_tracked_unknown(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["make build"],
            unknowns=[
                UnknownItem(
                    unknown_id="u_tests_001",
                    area="testing",
                    description="No canonical test command yet",
                    impact_level="high",
                    suggested_question="What test command should run?",
                )
            ],
        )
        policy_model = self._validator_ready_policy(open_unknowns=["u_tests_001"])

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("test_command_gap_tracked_as_unknown", issue_ids)
        self.assertNotIn("test_command_missing_without_unknown", issue_ids)
        self.assertFalse(report.blocking_status)

    def test_validator_phase4_warns_on_fallback_entrypoint_plus_open_test_gap(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["README.md (manual entrypoint reference)"],
            key_commands=["make build"],
            hypotheses=[
                HypothesisItem(
                    hypothesis_id="h_entrypoint_001",
                    area="architecture",
                    claim="Canonical entrypoint: README.md (manual entrypoint reference)",
                    confidence=0.55,
                    requires_confirmation=True,
                    suggested_question="Confirm canonical entrypoint?",
                )
            ],
            unknowns=[
                UnknownItem(
                    unknown_id="u_hypothesis_001",
                    area="architecture",
                    description="Entrypoint hypothesis is unresolved",
                    impact_level="medium",
                    suggested_question="Confirm entrypoint",
                ),
                UnknownItem(
                    unknown_id="u_tests_001",
                    area="testing",
                    description="No canonical test command yet",
                    impact_level="high",
                    suggested_question="What test command should run?",
                ),
            ],
        )
        policy_model = self._validator_ready_policy(open_unknowns=["u_hypothesis_001", "u_tests_001"])
        artifacts = {
            "PROJECT_ARCHITECTURE.md": (
                "# PROJECT_ARCHITECTURE\n\n"
                "## Обнаруженные стеки\n"
                "- python\n\n"
                "## Модули и границы\n"
                "- module\n\n"
                "## Точки входа и команды запуска\n"
                "- entry: README.md (manual entrypoint reference)\n"
                "- cmd: make build\n\n"
                "## Внешние интеграции и CI/CD\n"
                "- ext\n\n"
                "## Зависимости между модулями\n"
                "- module -> core\n\n"
                "## Критичные файлы\n"
                "- pyproject.toml\n\n"
                "## Открытые решения\n"
                "- u_hypothesis_001: open\n"
                "- u_tests_001: open\n"
            ),
            "PROJECT_STATE.md": (
                "# PROJECT_STATE\n\n"
                "## Снимок прогона\n"
                "- repo_id=repo\n\n"
                "## Операционная готовность\n"
                "- entry_points=1\n"
                "- key_commands=1\n\n"
                "## Неопределенности и риски\n"
                "- u_hypothesis_001: open\n"
                "- u_tests_001: open\n\n"
                "## Предупреждения сканера\n"
                "- none\n"
            ),
            "FIRST_MESSAGE_INSTRUCTIONS.md": (
                "# FIRST_MESSAGE_INSTRUCTIONS\n\n"
                "## Порядок чтения контекста\n"
                "1. PROJECT_STATE.md\n\n"
                "## Чеклист первого сообщения\n"
                "1. README.md (manual entrypoint reference)\n\n"
                "## Что проверить после изменений\n"
                "- make build\n\n"
                "## Открытые решения перед рисковыми правками\n"
                "- u_hypothesis_001: open\n"
                "- u_tests_001: open\n"
            ),
            "HANDOFF_PROTOCOL.md": (
                "# HANDOFF_PROTOCOL\n\n"
                "## Что передать в следующий чат\n"
                "- Rule B\n\n"
                "## Обязательный шаблон handoff\n"
                "1. next\n\n"
                "## Что осталось открытым\n"
                "- u_hypothesis_001: open\n"
                "- u_tests_001: open\n"
            ),
            "AGENT_BEHAVIOR_RULES.md": (
                "# AGENT_BEHAVIOR_RULES\n\n"
                "## Базовые правила\n"
                "- Rule A\n\n"
                "## Эскалация\n"
                "- Rule D\n\n"
                "## Конфликты и ограничения\n"
                "- none\n\n"
                "## Открытые решения\n"
                "- u_hypothesis_001: open\n"
                "- u_tests_001: open\n"
            ),
            "CONTEXT_UPDATE_POLICY.md": (
                "# CONTEXT_UPDATE_POLICY\n\n"
                "## Когда обновлять контекст\n"
                "- Rule C\n\n"
                "## Обязательные файлы\n"
                "1. docs/PROJECT_STATE.md\n\n"
                "## Порядок обновления\n"
                "1. sync\n\n"
                "## Проверка перед push\n"
                "1. done\n"
            ),
            "TASK_TRACKING_PROTOCOL.md": (
                "# TASK_TRACKING_PROTOCOL\n\n"
                "## Лимит и статусы активных задач\n"
                "- <= 12\n\n"
                "## Формат отчета по итерации\n"
                "1. Completed\n\n"
                "## Правила архивации\n"
                "- archive\n"
            ),
            "VALIDATION_REPORT.json": "{}",
        }

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=artifacts,
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("entrypoint_fallback_with_open_test_gap", issue_ids)
        self.assertNotIn("entrypoint_fallback_unconfirmed", issue_ids)
        self.assertNotIn("test_command_missing_without_unknown", issue_ids)
        self.assertFalse(report.blocking_status)

    def test_validator_phase3_detects_missing_parity_section_title(self) -> None:
        artifacts = self._validator_ready_artifacts()
        artifacts["PROJECT_STATE.md"] = artifacts["PROJECT_STATE.md"].replace(
            "## Операционная готовность",
            "## Операционная готовность (legacy)",
        )
        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=artifacts,
            fact_model=FactModel(repo_id="repo"),
            policy_model=self._validator_ready_policy(),
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("parity_section_missing_project_state_02", issue_ids)

    def test_validator_phase3_blocks_on_missing_critical_parity_section(self) -> None:
        artifacts = self._validator_ready_artifacts()
        artifacts["FIRST_MESSAGE_INSTRUCTIONS.md"] = artifacts["FIRST_MESSAGE_INSTRUCTIONS.md"].replace(
            "## Порядок чтения контекста",
            "## Порядок чтения",
        )
        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=artifacts,
            fact_model=FactModel(repo_id="repo"),
            policy_model=self._validator_ready_policy(),
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("parity_section_missing_first_message_instructions_01", issue_ids)
        self.assertTrue(report.blocking_status)

    def test_validator_phase7_detects_entrypoint_ambiguity_without_tracking(self) -> None:
        entrypoints = [f"sample/{idx:02d}/main.py" for idx in range(14)]
        fact_model = FactModel(
            repo_id="repo",
            entry_points=entrypoints,
            key_commands=["python -m unittest discover -s tests -v"],
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("entrypoint_ambiguity_high", issue_ids)
        self.assertIn("entrypoint_primary_non_primary_path", issue_ids)

    def test_validator_phase7_detects_command_ambiguity_without_tracking(self) -> None:
        commands = [f"npm run test:unit:{idx:02d}" for idx in range(14)]
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=commands,
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("command_ambiguity_high", issue_ids)
        self.assertIn("test_command_ambiguity_high", issue_ids)

    def test_validator_phase7_skips_ambiguity_when_tracked_unknowns_exist(self) -> None:
        entrypoints = [f"sample/{idx:02d}/main.py" for idx in range(14)]
        commands = [f"npm run test:unit:{idx:02d}" for idx in range(14)]
        fact_model = FactModel(
            repo_id="repo",
            entry_points=entrypoints,
            key_commands=commands,
            unknowns=[
                UnknownItem(
                    unknown_id="u_entrypoint_001",
                    area="architecture",
                    description="Entrypoint ambiguity is tracked",
                    impact_level="high",
                    suggested_question="Confirm canonical entrypoint?",
                ),
                UnknownItem(
                    unknown_id="u_commands_001",
                    area="workflow",
                    description="Command ambiguity is tracked",
                    impact_level="high",
                    suggested_question="Confirm canonical run/test command?",
                ),
            ],
        )
        policy_model = self._validator_ready_policy(open_unknowns=["u_entrypoint_001", "u_commands_001"])

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertNotIn("entrypoint_ambiguity_high", issue_ids)
        self.assertNotIn("entrypoint_primary_non_primary_path", issue_ids)
        self.assertNotIn("command_ambiguity_high", issue_ids)
        self.assertNotIn("test_command_ambiguity_high", issue_ids)

    def test_validator_phase7_detects_ci_primary_workflow_low_confidence(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["python -m unittest discover -s tests -v"],
            environments=["github-actions"],
            external_integrations=["github-actions"],
            ci_pipeline_map=[
                CiPipelineFact(
                    provider="github-actions",
                    file=".github/workflows/add-to-project.yml",
                    name="Add to Project",
                    triggers=["issues"],
                    jobs=[CiJobFact(job_id="triage", name="triage")],
                ),
                CiPipelineFact(
                    provider="github-actions",
                    file=".github/workflows/test.yml",
                    name="Test",
                    triggers=["push", "pull_request"],
                    jobs=[CiJobFact(job_id="test", name="test")],
                ),
            ],
        )
        policy_model = self._validator_ready_policy()

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("ci_primary_workflow_low_confidence", issue_ids)

    def test_validator_phase7_skips_ci_primary_confidence_when_hypothesis_unknown_tracked(self) -> None:
        fact_model = FactModel(
            repo_id="repo",
            entry_points=["main.py"],
            key_commands=["python -m unittest discover -s tests -v"],
            environments=["github-actions"],
            external_integrations=["github-actions"],
            unknowns=[
                UnknownItem(
                    unknown_id="u_hypothesis_001",
                    area="delivery",
                    description="Primary CI workflow is not confirmed",
                    impact_level="high",
                    suggested_question="Confirm primary CI workflow?",
                )
            ],
            ci_pipeline_map=[
                CiPipelineFact(
                    provider="github-actions",
                    file=".github/workflows/add-to-project.yml",
                    name="Add to Project",
                    triggers=["issues"],
                    jobs=[CiJobFact(job_id="triage", name="triage")],
                ),
                CiPipelineFact(
                    provider="github-actions",
                    file=".github/workflows/test.yml",
                    name="Test",
                    triggers=["push", "pull_request"],
                    jobs=[CiJobFact(job_id="test", name="test")],
                ),
            ],
        )
        policy_model = self._validator_ready_policy(open_unknowns=["u_hypothesis_001"])

        validator = ValidatorEngine()
        report = validator.validate(
            artifacts=self._validator_ready_artifacts(),
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertNotIn("ci_primary_workflow_low_confidence", issue_ids)


if __name__ == "__main__":
    unittest.main()
