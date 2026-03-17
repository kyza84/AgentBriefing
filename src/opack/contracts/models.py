from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from opack.core.enums import Severity


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UnknownItem:
    unknown_id: str
    area: str
    description: str
    impact_level: str
    suggested_question: str


@dataclass
class ModuleFact:
    name: str
    path: str
    kind: str


@dataclass
class TestSuiteFact:
    suite_id: str
    path: str
    framework: str
    command_candidates: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class CiJobFact:
    job_id: str
    name: str
    critical_steps: list[str] = field(default_factory=list)


@dataclass
class CiPipelineFact:
    provider: str
    file: str
    name: str
    triggers: list[str] = field(default_factory=list)
    jobs: list[CiJobFact] = field(default_factory=list)
    critical_steps: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class CriticalFileFact:
    path: str
    reason: str
    risk_level: str
    confidence: float = 0.0


@dataclass
class ModuleDependencyFact:
    source_module: str
    target_module: str
    signal_count: int = 0
    confidence: float = 0.0


@dataclass
class HypothesisItem:
    hypothesis_id: str
    area: str
    claim: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    suggested_question: str = ""


@dataclass
class FactModel:
    schema_version: str = "fact.v1.1"
    repo_id: str = ""
    scan_timestamp_utc: str = field(default_factory=utc_now)
    detected_stacks: list[str] = field(default_factory=list)
    modules: list[ModuleFact] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    environments: list[str] = field(default_factory=list)
    key_commands: list[str] = field(default_factory=list)
    external_integrations: list[str] = field(default_factory=list)
    tests_map: list[TestSuiteFact] = field(default_factory=list)
    ci_pipeline_map: list[CiPipelineFact] = field(default_factory=list)
    critical_files_map: list[CriticalFileFact] = field(default_factory=list)
    module_dependency_map: list[ModuleDependencyFact] = field(default_factory=list)
    hypotheses: list[HypothesisItem] = field(default_factory=list)
    unknowns: list[UnknownItem] = field(default_factory=list)
    confidence_overall: float = 0.0
    confidence_breakdown: dict[str, float] = field(default_factory=dict)
    operational_confidence: dict[str, float] = field(default_factory=dict)
    scanner_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyModel:
    schema_version: str = "policy.v1"
    policy_timestamp_utc: str = field(default_factory=utc_now)
    decision_profile: str = "balanced"
    agent_behavior_rules: list[str] = field(default_factory=list)
    handoff_rules: list[str] = field(default_factory=list)
    context_update_rules: list[str] = field(default_factory=list)
    escalation_rules: list[str] = field(default_factory=list)
    task_tracking_rules: list[str] = field(default_factory=list)
    resolved_unknowns: list[str] = field(default_factory=list)
    open_unknowns: list[str] = field(default_factory=list)
    answer_confidence: float = 0.0
    conflict_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    issue_id: str
    severity: Severity
    artifact: str
    description: str
    remediation: str


@dataclass
class ValidationReport:
    schema_version: str = "validation.v1"
    validated_at_utc: str = field(default_factory=utc_now)
    checks_run: list[str] = field(default_factory=list)
    issues: list[ValidationIssue] = field(default_factory=list)
    blocking_status: bool = False
    quality_score: float = 0.0
    recommended_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperatingPackManifest:
    schema_version: str = "manifest.v1"
    pack_id: str = ""
    generated_at_utc: str = field(default_factory=utc_now)
    artifact_inventory: list[str] = field(default_factory=list)
    source_provenance: dict[str, str] = field(default_factory=dict)
    open_unknowns: list[str] = field(default_factory=list)
    quality_summary: dict[str, Any] = field(default_factory=dict)
    build_run_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
