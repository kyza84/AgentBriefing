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

    _PARITY_SECTION_TITLES = {
        "PROJECT_ARCHITECTURE.md": [
            "Обнаруженные стеки",
            "Модули и границы",
            "Точки входа и команды запуска",
            "Внешние интеграции и CI/CD",
            "Зависимости между модулями",
            "Критичные файлы",
            "Открытые решения",
        ],
        "PROJECT_STATE.md": [
            "Снимок прогона",
            "Операционная готовность",
            "Неопределенности и риски",
            "Предупреждения сканера",
        ],
        "FIRST_MESSAGE_INSTRUCTIONS.md": [
            "Порядок чтения контекста",
            "Чеклист первого сообщения",
            "Что проверить после изменений",
            "Открытые решения перед рисковыми правками",
        ],
        "HANDOFF_PROTOCOL.md": [
            "Что передать в следующий чат",
            "Обязательный шаблон handoff",
            "Что осталось открытым",
        ],
        "AGENT_BEHAVIOR_RULES.md": [
            "Базовые правила",
            "Эскалация",
            "Конфликты и ограничения",
            "Открытые решения",
        ],
        "CONTEXT_UPDATE_POLICY.md": [
            "Когда обновлять контекст",
            "Обязательные файлы",
            "Порядок обновления",
            "Проверка перед push",
        ],
        "TASK_TRACKING_PROTOCOL.md": [
            "Лимит и статусы активных задач",
            "Формат отчета по итерации",
            "Правила архивации",
        ],
    }

    _MANDATORY_MARKDOWN_H2_COUNTS = {
        name: len(sections)
        for name, sections in _PARITY_SECTION_TITLES.items()
    }

    _PARITY_SECTION_SEVERITY = {
        "PROJECT_ARCHITECTURE.md": Severity.MAJOR,
        "PROJECT_STATE.md": Severity.MAJOR,
        "FIRST_MESSAGE_INSTRUCTIONS.md": Severity.CRITICAL,
        "HANDOFF_PROTOCOL.md": Severity.MAJOR,
        "AGENT_BEHAVIOR_RULES.md": Severity.MAJOR,
        "CONTEXT_UPDATE_POLICY.md": Severity.CRITICAL,
        "TASK_TRACKING_PROTOCOL.md": Severity.MAJOR,
    }

    _PARITY_ARTIFACT_SLUG = {
        "PROJECT_ARCHITECTURE.md": "project_architecture",
        "PROJECT_STATE.md": "project_state",
        "FIRST_MESSAGE_INSTRUCTIONS.md": "first_message_instructions",
        "HANDOFF_PROTOCOL.md": "handoff_protocol",
        "AGENT_BEHAVIOR_RULES.md": "agent_behavior_rules",
        "CONTEXT_UPDATE_POLICY.md": "context_update_policy",
        "TASK_TRACKING_PROTOCOL.md": "task_tracking_protocol",
    }

    _BLOCKING_MAJOR_ISSUES = {
        "entrypoint_fallback_unconfirmed",
        "ci_pipeline_map_missing",
        "test_command_missing_without_unknown",
        "operability_entrypoint_missing_without_unknown",
        "operability_commands_missing_without_unknown",
    }

    _ENTRYPOINT_AMBIGUITY_THRESHOLD = 12
    _COMMAND_AMBIGUITY_THRESHOLD = 12
    _TEST_COMMAND_AMBIGUITY_THRESHOLD = 5
    _CI_PRIMARY_CONFIDENCE_GAP_THRESHOLD = 3
    _NON_PRIMARY_ENTRYPOINT_PREFIXES = (
        "docs/",
        "docs_src/",
        "sample/",
        "samples/",
        "examples/",
        "example/",
        "tests/",
        "test/",
        "bench/",
        ".github/",
    )

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
            "operational_fact_quality",
            "operational_ambiguity",
            "ci_primary_confidence",
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
                    self._validate_parity_sections(
                        issues=issues,
                        artifact_name=name,
                        content=content,
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
        self._validate_operational_fact_quality(
            issues=issues,
            fact_model=fact_model,
            policy_model=policy_model,
        )
        self._validate_operational_ambiguity(
            issues=issues,
            fact_model=fact_model,
            policy_model=policy_model,
        )
        self._validate_ci_primary_confidence(
            issues=issues,
            fact_model=fact_model,
            policy_model=policy_model,
        )
        self._validate_scanner_signals(issues=issues, fact_model=fact_model)

        has_critical = any(i.severity == Severity.CRITICAL for i in issues)
        has_blocking_major = any(
            i.severity == Severity.MAJOR and i.issue_id in self._BLOCKING_MAJOR_ISSUES
            for i in issues
        )
        quality_score = self._quality_score(issues)

        return ValidationReport(
            checks_run=checks_run,
            issues=issues,
            blocking_status=has_critical or has_blocking_major,
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
            missing_in_project_state = [uid for uid in policy_model.open_unknowns if uid not in project_state]
            if missing_in_project_state:
                sample = ", ".join(missing_in_project_state[:3])
                self._append_issue(
                    issues=issues,
                    issue_id="project_state_unknown_visibility_gap",
                    severity=Severity.MAJOR,
                    artifact="PROJECT_STATE.md",
                    description=(
                        "Some open unknowns are not visible in PROJECT_STATE.md: "
                        f"{sample}"
                    ),
                    remediation="Expose all open unknown ids in PROJECT_STATE.md.",
                )

            missing_in_architecture = [uid for uid in policy_model.open_unknowns if uid not in architecture]
            if missing_in_architecture:
                sample = ", ".join(missing_in_architecture[:3])
                self._append_issue(
                    issues=issues,
                    issue_id="architecture_unknown_visibility_gap",
                    severity=Severity.MINOR,
                    artifact="PROJECT_ARCHITECTURE.md",
                    description=(
                        "Some open unknowns are not visible in PROJECT_ARCHITECTURE.md: "
                        f"{sample}"
                    ),
                    remediation="Expose unknown-driven architecture risks in PROJECT_ARCHITECTURE.md.",
                )

            missing_in_first_message = [uid for uid in policy_model.open_unknowns if uid not in first_message]
            if missing_in_first_message:
                sample = ", ".join(missing_in_first_message[:3])
                self._append_issue(
                    issues=issues,
                    issue_id="first_message_unknown_visibility_gap",
                    severity=Severity.MAJOR,
                    artifact="FIRST_MESSAGE_INSTRUCTIONS.md",
                    description=(
                        "Some open unknowns are not visible in FIRST_MESSAGE_INSTRUCTIONS.md: "
                        f"{sample}"
                    ),
                    remediation=(
                        "Expose all open unknown ids in FIRST_MESSAGE_INSTRUCTIONS.md "
                        "under the risk/open-decisions section."
                    ),
                )

            handoff = artifacts.get("HANDOFF_PROTOCOL.md", "")
            missing_in_handoff = [uid for uid in policy_model.open_unknowns if uid not in handoff]
            if missing_in_handoff:
                sample = ", ".join(missing_in_handoff[:3])
                self._append_issue(
                    issues=issues,
                    issue_id="handoff_unknown_visibility_gap",
                    severity=Severity.MAJOR,
                    artifact="HANDOFF_PROTOCOL.md",
                    description=(
                        "Some open unknowns are not visible in HANDOFF_PROTOCOL.md: "
                        f"{sample}"
                    ),
                    remediation="Expose unresolved unknown ids in handoff transfer/open sections.",
                )

            missing_in_behavior = [uid for uid in policy_model.open_unknowns if uid not in behavior_rules]
            if missing_in_behavior:
                sample = ", ".join(missing_in_behavior[:3])
                self._append_issue(
                    issues=issues,
                    issue_id="behavior_unknown_visibility_gap",
                    severity=Severity.MAJOR,
                    artifact="AGENT_BEHAVIOR_RULES.md",
                    description=(
                        "Some open unknowns are not visible in AGENT_BEHAVIOR_RULES.md: "
                        f"{sample}"
                    ),
                    remediation=(
                        "Expose unresolved behavior constraints by unknown id in "
                        "AGENT_BEHAVIOR_RULES.md."
                    ),
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

    def _validate_operational_fact_quality(
        self,
        issues: list[ValidationIssue],
        fact_model: FactModel,
        policy_model: PolicyModel,
    ) -> None:
        resolved_and_open = set(policy_model.resolved_unknowns) | set(policy_model.open_unknowns)
        canonical_test_command = self._canonical_test_command(fact_model)
        has_test_unknown = "u_tests_001" in resolved_and_open or "u_commands_001" in resolved_and_open

        fallback_entrypoint_tracked_unresolved = False

        if fact_model.entry_points:
            primary_entry = str(fact_model.entry_points[0]).strip().lower()
            if self._is_fallback_entrypoint(primary_entry):
                hypothesis_unknown_map = self._hypothesis_unknown_map(fact_model)
                entrypoint_unknown = hypothesis_unknown_map.get("h_entrypoint_001", "")
                is_confirmed = (
                    "u_entrypoint_001" in policy_model.resolved_unknowns
                    or (entrypoint_unknown and entrypoint_unknown in policy_model.resolved_unknowns)
                )
                is_tracked = (
                    "u_entrypoint_001" in resolved_and_open
                    or (entrypoint_unknown and entrypoint_unknown in resolved_and_open)
                )
                fallback_entrypoint_tracked_unresolved = bool(is_tracked and not is_confirmed)
                if not is_confirmed and not is_tracked:
                    self._append_issue(
                        issues=issues,
                        issue_id="entrypoint_fallback_unconfirmed",
                        severity=Severity.MAJOR,
                        artifact="FACT_MODEL",
                        description="Primary entrypoint is fallback/manual but confirmation tracking is missing.",
                        remediation=(
                            "Track fallback entrypoint as unknown/hypothesis or provide explicit confirmed entrypoint."
                        ),
                    )

        if fallback_entrypoint_tracked_unresolved and not canonical_test_command and has_test_unknown:
            self._append_issue(
                issues=issues,
                issue_id="entrypoint_fallback_with_open_test_gap",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description=(
                    "Fallback entrypoint is still unresolved and canonical test command is also unresolved "
                    "(tracked only via unknowns)."
                ),
                remediation=(
                    "Confirm canonical entrypoint and test command together before relying on this operating-pack."
                ),
            )

        ci_signaled = "github-actions" in fact_model.environments or "github-actions" in fact_model.external_integrations
        ci_guardrail_mode = bool(fact_model.scan_guardrails.get("activated")) or "u_scan_budget_001" in resolved_and_open
        if ci_signaled and not fact_model.ci_pipeline_map:
            if ci_guardrail_mode:
                self._append_issue(
                    issues=issues,
                    issue_id="ci_pipeline_map_sampled_due_guardrail",
                    severity=Severity.MINOR,
                    artifact="FACT_MODEL",
                    description="CI map is empty because scan guardrails were activated for this profile.",
                    remediation="Re-run with balanced/strict profile for complete CI pipeline extraction if release-critical.",
                )
            else:
                self._append_issue(
                    issues=issues,
                    issue_id="ci_pipeline_map_missing",
                    severity=Severity.MAJOR,
                    artifact="FACT_MODEL",
                    description="CI signal detected but ci_pipeline_map is empty.",
                    remediation="Extract workflow triggers/jobs into ci_pipeline_map before release.",
                )

        if fact_model.ci_pipeline_map:
            has_trigger_detail = any(bool(pipeline.triggers) for pipeline in fact_model.ci_pipeline_map)
            has_job_detail = any(bool(pipeline.jobs) for pipeline in fact_model.ci_pipeline_map)
            if not has_trigger_detail:
                self._append_issue(
                    issues=issues,
                    issue_id="ci_pipeline_map_triggers_missing",
                    severity=Severity.MAJOR,
                    artifact="FACT_MODEL",
                    description="CI pipeline map exists but contains no trigger details.",
                    remediation="Improve workflow trigger extraction or confirm CI trigger scope manually.",
                )
            if not has_job_detail:
                self._append_issue(
                    issues=issues,
                    issue_id="ci_pipeline_map_jobs_missing",
                    severity=Severity.MAJOR,
                    artifact="FACT_MODEL",
                    description="CI pipeline map exists but contains no job-level detail.",
                    remediation="Extract CI jobs/critical steps or provide explicit manual CI mapping.",
                )

        if not canonical_test_command:
            if has_test_unknown:
                self._append_issue(
                    issues=issues,
                    issue_id="test_command_gap_tracked_as_unknown",
                    severity=Severity.MINOR,
                    artifact="FACT_MODEL",
                    description=(
                        "Canonical test command is still unresolved and tracked only as an open/resolved unknown."
                    ),
                    remediation="Confirm one executable post-change test command before release-critical edits.",
                )
            else:
                self._append_issue(
                    issues=issues,
                    issue_id="test_command_missing_without_unknown",
                    severity=Severity.MAJOR,
                    artifact="FACT_MODEL",
                    description="No canonical test command is established and no unknown tracks this gap.",
                    remediation="Define canonical test command in scanner/questionnaire or track explicit unknown.",
                )

    def _is_fallback_entrypoint(self, entrypoint: str) -> bool:
        if "manual entrypoint reference" in entrypoint:
            return True
        return entrypoint.startswith(("readme.md", ".github/", "examples/", "example/", "tests/", "test/", "bench/"))

    def _hypothesis_unknown_map(self, fact_model: FactModel) -> dict[str, str]:
        mapping: dict[str, str] = {}
        pending = [item for item in fact_model.hypotheses if item.requires_confirmation]
        for idx, item in enumerate(pending, start=1):
            mapping[item.hypothesis_id] = f"u_hypothesis_{idx:03d}"
        return mapping

    def _canonical_test_command(self, fact_model: FactModel) -> str:
        for suite in fact_model.tests_map:
            for command in suite.command_candidates:
                if self._is_test_command(command):
                    return command
        for command in fact_model.key_commands:
            if self._is_test_command(command):
                return command
        return ""

    def _is_test_command(self, command: str) -> bool:
        lower = command.strip().lower()
        return any(token in lower for token in ("test", "pytest", "unittest", "go test", "cargo test", "vitest", "jest"))

    def _unique_command_candidates(self, fact_model: FactModel) -> list[str]:
        ordered: list[str] = []
        seen = set()
        for command in fact_model.key_commands:
            text = str(command).strip()
            if not text:
                continue
            token = text.lower()
            if token in seen:
                continue
            seen.add(token)
            ordered.append(text)
        for suite in fact_model.tests_map:
            for command in suite.command_candidates:
                text = str(command).strip()
                if not text:
                    continue
                token = text.lower()
                if token in seen:
                    continue
                seen.add(token)
                ordered.append(text)
        return ordered

    def _validate_operational_ambiguity(
        self,
        issues: list[ValidationIssue],
        fact_model: FactModel,
        policy_model: PolicyModel,
    ) -> None:
        resolved_and_open = set(policy_model.resolved_unknowns) | set(policy_model.open_unknowns)
        entrypoint_tracking = {"u_entrypoint_001", "u_hypothesis_001"} & resolved_and_open
        command_tracking = {"u_commands_001", "u_tests_001", "u_hypothesis_001"} & resolved_and_open

        entrypoints = [str(item).strip() for item in fact_model.entry_points if str(item).strip()]
        if len(entrypoints) >= self._ENTRYPOINT_AMBIGUITY_THRESHOLD and not entrypoint_tracking:
            sample = ", ".join(entrypoints[:3])
            self._append_issue(
                issues=issues,
                issue_id="entrypoint_ambiguity_high",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description=(
                    f"Too many entrypoint candidates ({len(entrypoints)}), canonical choice is ambiguous: {sample}"
                ),
                remediation=(
                    "Track entrypoint ambiguity (u_entrypoint_001) or confirm one canonical entrypoint via questionnaire."
                ),
            )

        if entrypoints and len(entrypoints) > 1 and not entrypoint_tracking:
            primary_entry = entrypoints[0].lower().replace("\\", "/")
            if primary_entry.startswith(self._NON_PRIMARY_ENTRYPOINT_PREFIXES):
                self._append_issue(
                    issues=issues,
                    issue_id="entrypoint_primary_non_primary_path",
                    severity=Severity.MAJOR,
                    artifact="FACT_MODEL",
                    description=(
                        "Primary entrypoint candidate points to docs/sample/tests-like path while alternatives exist: "
                        f"{entrypoints[0]}"
                    ),
                    remediation=(
                        "Demote non-primary folders (docs/sample/tests) or confirm canonical runtime entrypoint manually."
                    ),
                )

        unique_commands = self._unique_command_candidates(fact_model)
        if len(unique_commands) >= self._COMMAND_AMBIGUITY_THRESHOLD and not command_tracking:
            sample = ", ".join(unique_commands[:3])
            self._append_issue(
                issues=issues,
                issue_id="command_ambiguity_high",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description=f"Too many command candidates ({len(unique_commands)}), canonical command is ambiguous: {sample}",
                remediation="Track command ambiguity (u_commands_001) or confirm one canonical run/test command.",
            )

        test_commands = [command for command in unique_commands if self._is_test_command(command)]
        if len(test_commands) >= self._TEST_COMMAND_AMBIGUITY_THRESHOLD and not command_tracking:
            sample = ", ".join(test_commands[:3])
            self._append_issue(
                issues=issues,
                issue_id="test_command_ambiguity_high",
                severity=Severity.MAJOR,
                artifact="FACT_MODEL",
                description=(
                    f"Multiple test command variants detected ({len(test_commands)}), "
                    f"canonical post-change check is ambiguous: {sample}"
                ),
                remediation="Select and confirm one canonical post-change test command in questionnaire output.",
            )

    def _validate_ci_primary_confidence(
        self,
        issues: list[ValidationIssue],
        fact_model: FactModel,
        policy_model: PolicyModel,
    ) -> None:
        pipelines = list(fact_model.ci_pipeline_map)
        if len(pipelines) < 2:
            return

        resolved_and_open = set(policy_model.resolved_unknowns) | set(policy_model.open_unknowns)
        if "u_scan_budget_001" in resolved_and_open or bool(fact_model.scan_guardrails.get("activated")):
            return
        if "u_hypothesis_001" in resolved_and_open:
            return

        scored = [
            (idx, pipeline, self._ci_pipeline_priority_score(pipeline))
            for idx, pipeline in enumerate(pipelines)
        ]
        primary_idx, primary_pipeline, primary_score = scored[0]
        best_idx, best_pipeline, best_score = max(scored, key=lambda item: item[2])

        if best_idx == primary_idx:
            return
        if (best_score - primary_score) < self._CI_PRIMARY_CONFIDENCE_GAP_THRESHOLD:
            return

        self._append_issue(
            issues=issues,
            issue_id="ci_primary_workflow_low_confidence",
            severity=Severity.MAJOR,
            artifact="FACT_MODEL",
            description=(
                "Primary CI workflow selection appears low-confidence: "
                f"selected `{primary_pipeline.file}` but stronger candidate is `{best_pipeline.file}`."
            ),
            remediation=(
                "Confirm canonical CI workflow explicitly via questionnaire/policy "
                "or improve scanner ranking heuristics for workflow priority."
            ),
        )

    def _ci_pipeline_priority_score(self, pipeline: object) -> int:
        file_path = str(getattr(pipeline, "file", "")).lower()
        name = str(getattr(pipeline, "name", "")).lower()
        text = f"{file_path} {name}"
        score = 0
        if any(token in text for token in ("ci", "build", "test")):
            score += 3
        if any(token in text for token in ("deploy", "release", "publish", "prod", "production")):
            score += 3

        triggers = {str(item).lower() for item in getattr(pipeline, "triggers", [])}
        if {"push", "pull_request"} & triggers:
            score += 2
        if {"workflow_run", "release", "schedule"} & triggers:
            score += 1

        jobs = list(getattr(pipeline, "jobs", []))
        if jobs:
            score += 1
            for job in jobs:
                job_text = f"{getattr(job, 'job_id', '')} {getattr(job, 'name', '')}".lower()
                if any(token in job_text for token in ("deploy", "release", "publish", "prod", "build", "test")):
                    score += 1
                    break

        if getattr(pipeline, "critical_steps", []):
            score += 1
        return score

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

    def _h2_titles(self, content: str) -> list[str]:
        titles: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                titles.append(stripped[3:].strip())
        return titles

    def _validate_parity_sections(
        self,
        issues: list[ValidationIssue],
        artifact_name: str,
        content: str,
    ) -> None:
        expected_titles = self._PARITY_SECTION_TITLES.get(artifact_name, [])
        if not expected_titles:
            return
        existing_titles = set(self._h2_titles(content))
        artifact_slug = self._PARITY_ARTIFACT_SLUG.get(artifact_name, artifact_name.lower().replace(".md", ""))
        severity = self._PARITY_SECTION_SEVERITY.get(artifact_name, Severity.MAJOR)
        for index, title in enumerate(expected_titles, start=1):
            if title in existing_titles:
                continue
            self._append_issue(
                issues=issues,
                issue_id=f"parity_section_missing_{artifact_slug}_{index:02d}",
                severity=severity,
                artifact=artifact_name,
                description=f"Missing required parity section title: ## {title}",
                remediation="Regenerate artifact and restore all mandatory parity section titles.",
            )

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
