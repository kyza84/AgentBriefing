from opack.contracts.models import FactModel, PolicyModel, ValidationIssue, ValidationReport
from opack.core.enums import Severity


class ValidatorEngine:
    """V1 validator baseline: mandatory artifact and minimal consistency checks."""

    def validate(
        self,
        artifacts: dict[str, str],
        fact_model: FactModel,
        policy_model: PolicyModel,
    ) -> ValidationReport:
        issues: list[ValidationIssue] = []
        checks_run = [
            "mandatory_artifacts_present",
            "artifact_non_empty",
            "unknowns_visible",
        ]

        mandatory = [
            "PROJECT_ARCHITECTURE.md",
            "PROJECT_STATE.md",
            "FIRST_MESSAGE_INSTRUCTIONS.md",
            "HANDOFF_PROTOCOL.md",
            "AGENT_BEHAVIOR_RULES.md",
            "CONTEXT_UPDATE_POLICY.md",
            "TASK_TRACKING_PROTOCOL.md",
            "VALIDATION_REPORT.json",
        ]
        for name in mandatory:
            if name not in artifacts:
                issues.append(
                    ValidationIssue(
                        issue_id=f"missing_{name}",
                        severity=Severity.CRITICAL,
                        artifact=name,
                        description=f"Missing mandatory artifact: {name}",
                        remediation="Ensure generator creates all mandatory artifacts.",
                    )
                )

        for name, content in artifacts.items():
            if not content.strip():
                issues.append(
                    ValidationIssue(
                        issue_id=f"empty_{name}",
                        severity=Severity.MAJOR,
                        artifact=name,
                        description=f"Artifact is empty: {name}",
                        remediation="Populate artifact with actionable content.",
                    )
                )

        fact_unknown_ids = {u.unknown_id for u in fact_model.unknowns}
        resolved_unknown_ids = set(policy_model.resolved_unknowns)
        unresolved_unknown_ids = fact_unknown_ids - resolved_unknown_ids
        declared_open_unknown_ids = set(policy_model.open_unknowns)

        if unresolved_unknown_ids and not declared_open_unknown_ids:
            issues.append(
                ValidationIssue(
                    issue_id="unknown_mismatch",
                    severity=Severity.MAJOR,
                    artifact="POLICY_MODEL",
                    description="FactModel has unresolved unknowns but PolicyModel open_unknowns is empty.",
                    remediation="Carry unresolved unknowns into policy model and final manifest.",
                )
            )
        unknown_id_drift = declared_open_unknown_ids - fact_unknown_ids
        if unknown_id_drift:
            issues.append(
                ValidationIssue(
                    issue_id="unknown_id_drift",
                    severity=Severity.MINOR,
                    artifact="POLICY_MODEL",
                    description="PolicyModel open_unknowns contains ids absent in FactModel.",
                    remediation="Synchronize open_unknowns with current FactModel unknown ids.",
                )
            )

        has_critical = any(i.severity == Severity.CRITICAL for i in issues)
        quality_score = max(0.0, 1.0 - (0.25 * sum(1 for i in issues if i.severity == Severity.CRITICAL)
                                        + 0.10 * sum(1 for i in issues if i.severity == Severity.MAJOR)
                                        + 0.03 * sum(1 for i in issues if i.severity == Severity.MINOR)))

        return ValidationReport(
            checks_run=checks_run,
            issues=issues,
            blocking_status=has_critical,
            quality_score=round(quality_score, 3),
            recommended_actions=[
                "Resolve critical issues before marking the pack as completed."
            ] if has_critical else [],
        )
