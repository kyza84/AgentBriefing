from opack.contracts.models import FactModel, PolicyModel, ValidationIssue, ValidationReport
from opack.core.enums import Severity


class ValidatorEngine:
    """V1 Phase 5 validator: completeness, consistency, and operational applicability."""

    _MANDATORY_ARTIFACTS = [
        "PROJECT_ARCHITECTURE.md",
        "PROJECT_STATE.md",
        "FIRST_MESSAGE_INSTRUCTIONS.md",
        "HANDOFF_PROTOCOL.md",
        "AGENT_BEHAVIOR_RULES.md",
        "CONTEXT_UPDATE_POLICY.md",
        "TASK_TRACKING_PROTOCOL.md",
        "VALIDATION_REPORT.json",
    ]

    _MANDATORY_MARKDOWN_H2_COUNTS = {
        "PROJECT_ARCHITECTURE.md": 5,
        "PROJECT_STATE.md": 2,
        "FIRST_MESSAGE_INSTRUCTIONS.md": 2,
        "HANDOFF_PROTOCOL.md": 2,
        "AGENT_BEHAVIOR_RULES.md": 3,
        "CONTEXT_UPDATE_POLICY.md": 2,
        "TASK_TRACKING_PROTOCOL.md": 2,
    }

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
            "markdown_structure",
            "unknown_consistency",
            "policy_rule_presence",
            "fact_policy_consistency",
            "operational_applicability",
            "scanner_signal_health",
        ]

        for name in self._MANDATORY_ARTIFACTS:
            if name not in artifacts:
                self._append_issue(
                    issues=issues,
                    issue_id=f"missing_{name}",
                    severity=Severity.CRITICAL,
                    artifact=name,
                    description=f"Missing mandatory artifact: {name}",
                    remediation="Ensure generator creates all mandatory artifacts.",
                )

        for name, content in artifacts.items():
            if not content.strip():
                self._append_issue(
                    issues=issues,
                    issue_id=f"empty_{name}",
                    severity=Severity.MAJOR,
                    artifact=name,
                    description=f"Artifact is empty: {name}",
                    remediation="Populate artifact with actionable content.",
                )
            if name.endswith(".md") and content.strip():
                if not content.lstrip().startswith("# "):
                    self._append_issue(
                        issues=issues,
                        issue_id=f"markdown_title_missing_{name}",
                        severity=Severity.MINOR,
                        artifact=name,
                        description=f"Markdown artifact does not start with H1 title: {name}",
                        remediation="Start markdown artifacts with a single H1 section title.",
                    )

                expected_h2 = self._MANDATORY_MARKDOWN_H2_COUNTS.get(name)
                if expected_h2 is not None:
                    h2_count = self._h2_count(content)
                    if h2_count < expected_h2:
                        self._append_issue(
                            issues=issues,
                            issue_id=f"markdown_sections_insufficient_{name}",
                            severity=Severity.MAJOR,
                            artifact=name,
                            description=f"{name} has {h2_count} H2 sections, expected at least {expected_h2}.",
                            remediation="Regenerate artifact with all mandatory operational sections.",
                        )

        fact_unknown_ids = {u.unknown_id for u in fact_model.unknowns}
        resolved_unknown_ids = set(policy_model.resolved_unknowns)
        unresolved_unknown_ids = fact_unknown_ids - resolved_unknown_ids
        declared_open_unknown_ids = set(policy_model.open_unknowns)

        if unresolved_unknown_ids and not declared_open_unknown_ids:
            self._append_issue(
                issues=issues,
                issue_id="unknown_mismatch",
                severity=Severity.MAJOR,
                artifact="POLICY_MODEL",
                description="FactModel has unresolved unknowns but PolicyModel open_unknowns is empty.",
                remediation="Carry unresolved unknowns into policy model and final manifest.",
            )

        missing_open_unknown_ids = unresolved_unknown_ids - declared_open_unknown_ids
        if missing_open_unknown_ids:
            self._append_issue(
                issues=issues,
                issue_id="unknown_open_missing",
                severity=Severity.MAJOR,
                artifact="POLICY_MODEL",
                description="Some unresolved FactModel unknowns are not listed in PolicyModel open_unknowns.",
                remediation="Synchronize open_unknowns to include all unresolved unknown ids.",
            )

        overlap_unknown_ids = resolved_unknown_ids & declared_open_unknown_ids
        if overlap_unknown_ids:
            self._append_issue(
                issues=issues,
                issue_id="unknown_resolution_overlap",
                severity=Severity.MAJOR,
                artifact="POLICY_MODEL",
                description="Same unknown ids appear in both resolved_unknowns and open_unknowns.",
                remediation="Keep unknown ids in exactly one bucket: resolved or open.",
            )

        unknown_id_drift = declared_open_unknown_ids - fact_unknown_ids
        if unknown_id_drift:
            self._append_issue(
                issues=issues,
                issue_id="unknown_id_drift",
                severity=Severity.MINOR,
                artifact="POLICY_MODEL",
                description="PolicyModel open_unknowns contains ids absent in FactModel.",
                remediation="Synchronize open_unknowns with current FactModel unknown ids.",
            )

        resolved_id_drift = resolved_unknown_ids - fact_unknown_ids
        if resolved_id_drift:
            self._append_issue(
                issues=issues,
                issue_id="resolved_unknown_id_drift",
                severity=Severity.MINOR,
                artifact="POLICY_MODEL",
                description="PolicyModel resolved_unknowns contains ids absent in FactModel.",
                remediation="Remove stale unknown ids or refresh FactModel before regeneration.",
            )

        self._validate_policy_rules(issues=issues, policy_model=policy_model)
        self._validate_artifact_consistency(
            issues=issues,
            artifacts=artifacts,
            fact_model=fact_model,
            policy_model=policy_model,
        )
        self._validate_operational_applicability(
            issues=issues,
            fact_model=fact_model,
            policy_model=policy_model,
        )
        self._validate_scanner_signals(issues=issues, fact_model=fact_model)

        has_critical = any(i.severity == Severity.CRITICAL for i in issues)
        quality_score = self._quality_score(issues)

        return ValidationReport(
            checks_run=checks_run,
            issues=issues,
            blocking_status=has_critical,
            quality_score=round(quality_score, 3),
            recommended_actions=self._recommended_actions(issues),
        )

    def _validate_policy_rules(self, issues: list[ValidationIssue], policy_model: PolicyModel) -> None:
        policy_rules = [
            ("agent_behavior_rules", policy_model.agent_behavior_rules),
            ("handoff_rules", policy_model.handoff_rules),
            ("context_update_rules", policy_model.context_update_rules),
            ("escalation_rules", policy_model.escalation_rules),
            ("task_tracking_rules", policy_model.task_tracking_rules),
        ]
        for field_name, rules in policy_rules:
            if rules:
                continue
            self._append_issue(
                issues=issues,
                issue_id=f"policy_rules_missing_{field_name}",
                severity=Severity.MAJOR,
                artifact="POLICY_MODEL",
                description=f"PolicyModel {field_name} is empty.",
                remediation=f"Provide at least one actionable rule in {field_name}.",
            )

        if policy_model.conflict_log:
            self._append_issue(
                issues=issues,
                issue_id="policy_conflicts_present",
                severity=Severity.MAJOR,
                artifact="POLICY_MODEL",
                description="PolicyModel conflict_log is not empty.",
                remediation="Resolve conflicting policy answers before pack finalization.",
            )

    def _validate_artifact_consistency(
        self,
        issues: list[ValidationIssue],
        artifacts: dict[str, str],
        fact_model: FactModel,
        policy_model: PolicyModel,
    ) -> None:
        architecture = artifacts.get("PROJECT_ARCHITECTURE.md", "")
        project_state = artifacts.get("PROJECT_STATE.md", "")
        first_message = artifacts.get("FIRST_MESSAGE_INSTRUCTIONS.md", "")
        behavior_rules = artifacts.get("AGENT_BEHAVIOR_RULES.md", "")

        if fact_model.detected_stacks and not all(stack in architecture for stack in fact_model.detected_stacks):
            self._append_issue(
                issues=issues,
                issue_id="architecture_stack_signal_mismatch",
                severity=Severity.MAJOR,
                artifact="PROJECT_ARCHITECTURE.md",
                description="Not all detected stacks are reflected in PROJECT_ARCHITECTURE.md.",
                remediation="Propagate detected stack signals into architecture artifact sections.",
            )

        if fact_model.entry_points and fact_model.entry_points[0] not in first_message:
            self._append_issue(
                issues=issues,
                issue_id="first_message_entrypoint_mismatch",
                severity=Severity.MINOR,
                artifact="FIRST_MESSAGE_INSTRUCTIONS.md",
                description="Primary entry point is missing in first-message instructions.",
                remediation="Include canonical entry point in FIRST_MESSAGE_INSTRUCTIONS.md.",
            )

        if fact_model.key_commands and fact_model.key_commands[0] not in first_message:
            self._append_issue(
                issues=issues,
                issue_id="first_message_command_mismatch",
                severity=Severity.MAJOR,
                artifact="FIRST_MESSAGE_INSTRUCTIONS.md",
                description="Primary key command is missing in first-message instructions.",
                remediation="Include a canonical verification command in FIRST_MESSAGE_INSTRUCTIONS.md.",
            )

        if policy_model.open_unknowns:
            primary_open_unknown = policy_model.open_unknowns[0]
            if primary_open_unknown not in project_state:
                self._append_issue(
                    issues=issues,
                    issue_id="project_state_unknown_visibility_gap",
                    severity=Severity.MAJOR,
                    artifact="PROJECT_STATE.md",
                    description="Open unknowns are not visible in PROJECT_STATE.md.",
                    remediation="Expose all open unknown ids in PROJECT_STATE.md.",
                )
            if primary_open_unknown not in architecture:
                self._append_issue(
                    issues=issues,
                    issue_id="architecture_unknown_visibility_gap",
                    severity=Severity.MINOR,
                    artifact="PROJECT_ARCHITECTURE.md",
                    description="Open unknowns are not visible in PROJECT_ARCHITECTURE.md.",
                    remediation="Expose unknown-driven architecture risks in PROJECT_ARCHITECTURE.md.",
                )

        if policy_model.conflict_log and policy_model.conflict_log[0] not in behavior_rules:
            self._append_issue(
                issues=issues,
                issue_id="behavior_conflict_log_visibility_gap",
                severity=Severity.MINOR,
                artifact="AGENT_BEHAVIOR_RULES.md",
                description="Policy conflict log is not reflected in AGENT_BEHAVIOR_RULES.md.",
                remediation="Surface policy conflicts directly in behavior rules artifact.",
            )

    def _validate_operational_applicability(
        self,
        issues: list[ValidationIssue],
        fact_model: FactModel,
        policy_model: PolicyModel,
    ) -> None:
        resolved_and_open = set(policy_model.resolved_unknowns) | set(policy_model.open_unknowns)

        if not fact_model.entry_points and "u_entrypoint_001" not in resolved_and_open:
            self._append_issue(
                issues=issues,
                issue_id="operability_entrypoint_missing_without_unknown",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description="No entry point found and no tracked unknown for entry point resolution.",
                remediation="Add canonical entry point or track u_entrypoint_001 in questionnaire output.",
            )

        if not fact_model.key_commands and "u_commands_001" not in resolved_and_open:
            self._append_issue(
                issues=issues,
                issue_id="operability_commands_missing_without_unknown",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description="No key commands found and no tracked unknown for command resolution.",
                remediation="Add canonical run/test commands or track u_commands_001 in questionnaire output.",
            )

    def _validate_scanner_signals(self, issues: list[ValidationIssue], fact_model: FactModel) -> None:
        if fact_model.confidence_overall < 0.25:
            self._append_issue(
                issues=issues,
                issue_id="scanner_confidence_low",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description=f"Scanner confidence is too low: {fact_model.confidence_overall}.",
                remediation="Improve scanner coverage or provide more policy answers before release.",
            )
        if fact_model.scanner_warnings:
            self._append_issue(
                issues=issues,
                issue_id="scanner_warnings_present",
                severity=Severity.INFO,
                artifact="FACT_MODEL",
                description=f"Scanner produced {len(fact_model.scanner_warnings)} warning(s).",
                remediation="Review scanner warnings and ensure they do not hide critical project facts.",
            )

    def _append_issue(
        self,
        issues: list[ValidationIssue],
        issue_id: str,
        severity: Severity,
        artifact: str,
        description: str,
        remediation: str,
    ) -> None:
        issues.append(
            ValidationIssue(
                issue_id=issue_id,
                severity=severity,
                artifact=artifact,
                description=description,
                remediation=remediation,
            )
        )

    def _h2_count(self, content: str) -> int:
        return sum(1 for line in content.splitlines() if line.strip().startswith("## "))

    def _quality_score(self, issues: list[ValidationIssue]) -> float:
        penalties = {
            Severity.CRITICAL: 0.30,
            Severity.MAJOR: 0.10,
            Severity.MINOR: 0.03,
            Severity.INFO: 0.01,
        }
        score = 1.0
        for issue in issues:
            score -= penalties.get(issue.severity, 0.0)
        return max(0.0, score)

    def _recommended_actions(self, issues: list[ValidationIssue]) -> list[str]:
        ordered_severity = [Severity.CRITICAL, Severity.MAJOR, Severity.MINOR, Severity.INFO]
        remediations: list[str] = []
        seen = set()
        for severity in ordered_severity:
            for issue in issues:
                if issue.severity != severity:
                    continue
                action = issue.remediation.strip()
                if not action:
                    continue
                token = action.lower()
                if token in seen:
                    continue
                seen.add(token)
                remediations.append(action)
        if any(issue.severity == Severity.CRITICAL for issue in issues):
            prefix = "Resolve critical issues before marking the pack as completed."
            if prefix.lower() not in seen:
                remediations.insert(0, prefix)
        return remediations[:8]
