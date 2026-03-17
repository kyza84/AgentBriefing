import tempfile
import unittest
import json
from pathlib import Path

from opack.contracts.models import FactModel, PolicyModel, UnknownItem
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
            self.assertIn("## Точки входа", architecture)
            self.assertIn("## Открытые unknown", state)
            self.assertIn("## Первый ответ агента", first_message)

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
            artifacts={
                "PROJECT_ARCHITECTURE.md": "# A\n\n## S1\n- python\n\n## S2\n- module\n\n## S3\n- main.py\n\n## S4\n- ext\n\n## S5\n- u_workflow_001\n",
                "PROJECT_STATE.md": "# S\n\n## S1\n- u_workflow_001\n\n## S2\n- ok\n",
                "FIRST_MESSAGE_INSTRUCTIONS.md": "# F\n\n## S1\n1. main.py\n\n## S2\n- python -m unittest discover -s tests -v\n",
                "HANDOFF_PROTOCOL.md": "# H\n\n## S1\n- a\n\n## S2\n- b\n",
                "AGENT_BEHAVIOR_RULES.md": "# B\n\n## S1\n- a\n\n## S2\n- b\n\n## S3\n- c\n",
                "CONTEXT_UPDATE_POLICY.md": "# C\n\n## S1\n- a\n\n## S2\n- b\n",
                "TASK_TRACKING_PROTOCOL.md": "# T\n\n## S1\n1. a\n\n## S2\n- b\n",
                "VALIDATION_REPORT.json": "{}",
            },
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("unknown_resolution_overlap", issue_ids)

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
            artifacts={
                "PROJECT_ARCHITECTURE.md": "# A\n\n## S1\n- UNKNOWN\n\n## S2\n- module\n\n## S3\n- none\n\n## S4\n- ext\n\n## S5\n- u_workflow_001\n",
                "PROJECT_STATE.md": "# S\n\n## S1\n- u_workflow_001\n\n## S2\n- ok\n",
                "FIRST_MESSAGE_INSTRUCTIONS.md": "# F\n\n## S1\n1. start\n\n## S2\n- boundaries\n",
                "HANDOFF_PROTOCOL.md": "# H\n\n## S1\n- a\n\n## S2\n- b\n",
                "AGENT_BEHAVIOR_RULES.md": "# B\n\n## S1\n- a\n\n## S2\n- b\n\n## S3\n- c\n",
                "CONTEXT_UPDATE_POLICY.md": "# C\n\n## S1\n- a\n\n## S2\n- b\n",
                "TASK_TRACKING_PROTOCOL.md": "# T\n\n## S1\n1. a\n\n## S2\n- b\n",
                "VALIDATION_REPORT.json": "{}",
            },
            fact_model=fact_model,
            policy_model=policy_model,
        )
        issue_ids = {issue.issue_id for issue in report.issues}
        self.assertIn("operability_entrypoint_missing_without_unknown", issue_ids)
        self.assertIn("operability_commands_missing_without_unknown", issue_ids)


if __name__ == "__main__":
    unittest.main()
