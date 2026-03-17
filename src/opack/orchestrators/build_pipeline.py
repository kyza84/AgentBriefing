from pathlib import Path
from typing import Any
from uuid import uuid4

from opack.adapters.filesystem import FilesystemAdapter
from opack.contracts.models import FactModel
from opack.core.errors import GateBlockedError
from opack.engines.generator import GeneratorEngine
from opack.engines.questionnaire import QuestionnaireEngine
from opack.engines.scanner import ScannerEngine
from opack.engines.validator import ValidatorEngine


class BuildPipeline:
    """End-to-end V1 builder orchestration."""

    def __init__(self) -> None:
        self.scanner = ScannerEngine()
        self.questionnaire = QuestionnaireEngine()
        self.generator = GeneratorEngine()
        self.validator = ValidatorEngine()
        self.fs = FilesystemAdapter()

    def run(
        self,
        repo_path: Path,
        output_path: Path,
        profile: str = "balanced",
        answers: dict[str, Any] | None = None,
        fact_model: FactModel | None = None,
    ) -> dict[str, str]:
        current_fact_model = fact_model or self.scanner.scan(repo_path=repo_path, profile=profile)
        policy_model = self.questionnaire.build_policy_model(
            fact_model=current_fact_model,
            profile=profile,
            answers=answers,
        )

        pack_id = f"pack-{uuid4().hex[:10]}"
        artifacts, manifest = self.generator.generate(
            fact_model=current_fact_model,
            policy_model=policy_model,
            pack_id=pack_id,
        )
        validation = self.validator.validate(
            artifacts=artifacts,
            fact_model=current_fact_model,
            policy_model=policy_model,
        )

        manifest.quality_summary = {
            "quality_score": validation.quality_score,
            "blocking_status": validation.blocking_status,
            "issue_count": len(validation.issues),
        }

        pack_dir = output_path / pack_id
        self.fs.ensure_dir(pack_dir)
        for name, content in artifacts.items():
            if name.endswith(".json"):
                continue
            self.fs.write_text(pack_dir / name, content)

        self.fs.write_json(pack_dir / "OPERATING_PACK_MANIFEST.json", manifest.to_dict())
        self.fs.write_json(pack_dir / "VALIDATION_REPORT.json", validation.to_dict())
        self.fs.write_json(pack_dir / "FACT_MODEL.json", current_fact_model.to_dict())
        self.fs.write_json(pack_dir / "POLICY_MODEL.json", policy_model.to_dict())

        if validation.blocking_status:
            raise GateBlockedError("Build completed with blocking validation issues.")

        return {
            "pack_id": pack_id,
            "output_dir": str(pack_dir),
            "quality_score": str(validation.quality_score),
            "issues": str(len(validation.issues)),
        }
