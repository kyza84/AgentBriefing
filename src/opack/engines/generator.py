from opack.contracts.models import (
    CiPipelineFact,
    FactModel,
    ModuleDependencyFact,
    OperatingPackManifest,
    PolicyModel,
    UnknownItem,
)


REQUIRED_ARTIFACTS = [
    "PROJECT_ARCHITECTURE.md",
    "PROJECT_STATE.md",
    "FIRST_MESSAGE_INSTRUCTIONS.md",
    "HANDOFF_PROTOCOL.md",
    "AGENT_BEHAVIOR_RULES.md",
    "CONTEXT_UPDATE_POLICY.md",
    "TASK_TRACKING_PROTOCOL.md",
    "OPERATING_PACK_MANIFEST.json",
    "VALIDATION_REPORT.json",
]


class GeneratorEngine:
    """V1.3 parity-driven generator for richer operating-pack artifacts."""

    def generate(
        self,
        fact_model: FactModel,
        policy_model: PolicyModel,
        pack_id: str,
    ) -> tuple[dict[str, str], OperatingPackManifest]:
        artifacts: dict[str, str] = {
            "PROJECT_ARCHITECTURE.md": self._project_architecture(fact_model, policy_model),
            "PROJECT_STATE.md": self._project_state(fact_model, policy_model),
            "FIRST_MESSAGE_INSTRUCTIONS.md": self._first_message_instructions(fact_model, policy_model),
            "HANDOFF_PROTOCOL.md": self._handoff_protocol(fact_model, policy_model),
            "AGENT_BEHAVIOR_RULES.md": self._agent_behavior_rules(fact_model, policy_model),
            "CONTEXT_UPDATE_POLICY.md": self._context_update_policy(policy_model),
            "TASK_TRACKING_PROTOCOL.md": self._task_tracking_protocol(policy_model),
            "VALIDATION_REPORT.json": "{}",
        }

        manifest = OperatingPackManifest(
            pack_id=pack_id,
            artifact_inventory=REQUIRED_ARTIFACTS,
            source_provenance={
                "PROJECT_ARCHITECTURE.md": "FactModel+PolicyModel",
                "PROJECT_STATE.md": "FactModel+PolicyModel",
                "FIRST_MESSAGE_INSTRUCTIONS.md": "FactModel+PolicyModel",
                "HANDOFF_PROTOCOL.md": "PolicyModel",
                "AGENT_BEHAVIOR_RULES.md": "PolicyModel",
                "CONTEXT_UPDATE_POLICY.md": "PolicyModel",
                "TASK_TRACKING_PROTOCOL.md": "PolicyModel",
                "OPERATING_PACK_MANIFEST.json": "FactModel+PolicyModel",
                "VALIDATION_REPORT.json": "Validator",
            },
            open_unknowns=policy_model.open_unknowns,
            quality_summary={"status": "generated"},
            build_run_metadata={
                "generator_version": "0.3.0",
                "decision_profile": policy_model.decision_profile,
                "resolved_unknowns": len(policy_model.resolved_unknowns),
                "open_unknowns": len(policy_model.open_unknowns),
                "tests_map_count": len(fact_model.tests_map),
                "ci_pipeline_count": len(fact_model.ci_pipeline_map),
                "critical_file_count": len(fact_model.critical_files_map),
            },
        )
        return artifacts, manifest

    def _project_architecture(self, fact: FactModel, policy: PolicyModel) -> str:
        module_lines = [f"{module.name} | {module.kind} | {module.path}" for module in fact.modules]
        entrypoint_lines = [f"entry: {value}" for value in fact.entry_points]
        command_lines = [f"cmd: {value}" for value in fact.key_commands]

        return (
            "# PROJECT_ARCHITECTURE\n\n"
            "## Обнаруженные стеки\n"
            f"{self._format_bullets(fact.detected_stacks, fallback='UNKNOWN: stack not detected')}\n\n"
            "## Модули и границы\n"
            f"{self._format_bullets(module_lines, fallback='UNKNOWN: modules not extracted')}\n\n"
            "## Точки входа и команды запуска\n"
            f"{self._format_bullets(entrypoint_lines + command_lines, fallback='UNKNOWN: entrypoint/commands are not established')}\n\n"
            "## Внешние интеграции и CI/CD\n"
            f"{self._format_bullets(self._integration_and_ci_lines(fact), fallback='No explicit integrations or CI/CD map')}\n\n"
            "## Зависимости между модулями\n"
            f"{self._format_bullets(self._dependency_lines(fact.module_dependency_map), fallback='No module dependency edges extracted')}\n\n"
            "## Критичные файлы\n"
            f"{self._format_bullets(self._critical_file_lines(fact), fallback='Critical files are not identified')}\n\n"
            "## Открытые решения\n"
            f"{self._format_open_decisions(fact, policy)}\n"
        )

    def _project_state(self, fact: FactModel, policy: PolicyModel) -> str:
        confidence_lines = [
            f"overall={fact.confidence_overall}",
            f"coverage={fact.confidence_breakdown.get('coverage_confidence', 0.0)}",
            f"signal={fact.confidence_breakdown.get('signal_confidence', 0.0)}",
            f"coherence={fact.confidence_breakdown.get('coherence_confidence', 0.0)}",
            f"operational={fact.confidence_breakdown.get('operational_confidence', 0.0)}",
        ]
        readiness_lines = [
            f"entry_points={len(fact.entry_points)}",
            f"key_commands={len(fact.key_commands)}",
            f"tests_map={len(fact.tests_map)}",
            f"ci_pipeline_map={len(fact.ci_pipeline_map)}",
            f"critical_files_map={len(fact.critical_files_map)}",
            f"module_dependency_map={len(fact.module_dependency_map)}",
            f"environments={', '.join(fact.environments) if fact.environments else 'none'}",
        ]

        return (
            "# PROJECT_STATE\n\n"
            "## Снимок прогона\n"
            f"{self._format_bullets([f'repo_id={fact.repo_id}', f'decision_profile={policy.decision_profile}'] + confidence_lines, fallback='Run snapshot is unavailable')}\n\n"
            "## Операционная готовность\n"
            f"{self._format_bullets(readiness_lines, fallback='Operational readiness is unknown')}\n\n"
            "## Неопределенности и риски\n"
            f"{self._format_open_decisions(fact, policy)}\n\n"
            "## Предупреждения сканера\n"
            f"{self._format_bullets(fact.scanner_warnings, fallback='Scanner warnings are absent')}\n"
        )

    def _first_message_instructions(self, fact: FactModel, policy: PolicyModel) -> str:
        checklist = [
            "Подтверди цель текущей итерации и границы scope.",
            "Укажи, что именно будет изменено до начала правок.",
            "После правок дай отчет: Completed / Not completed / Deviation / Next.",
        ]
        if fact.entry_points:
            checklist.append(f"Проверь точку входа: {fact.entry_points[0]}")
        if fact.key_commands:
            checklist.append(f"Запусти проверку после изменений: {fact.key_commands[0]}")

        verify_steps = self._verification_steps(fact)
        if not verify_steps:
            verify_steps = ["Нет явной команды проверки, зафиксируй это как риск и уточни у пользователя."]

        return (
            "# FIRST_MESSAGE_INSTRUCTIONS\n\n"
            "## Порядок чтения контекста\n"
            f"{self._format_numbered(['PROJECT_STATE.md', 'PROJECT_ARCHITECTURE.md', 'AGENT_BEHAVIOR_RULES.md', 'CONTEXT_UPDATE_POLICY.md', 'TASK_TRACKING_PROTOCOL.md', 'HANDOFF_PROTOCOL.md'])}\n\n"
            "## Чеклист первого сообщения\n"
            f"{self._format_numbered(checklist)}\n\n"
            "## Что проверить после изменений\n"
            f"{self._format_bullets(verify_steps, fallback='Verification steps are not defined')}\n\n"
            "## Открытые решения перед рисковыми правками\n"
            f"{self._format_open_decisions(fact, policy)}\n"
        )

    def _handoff_protocol(self, fact: FactModel, policy: PolicyModel) -> str:
        transfer_rules = policy.handoff_rules or ["Handoff rules are not defined yet."]
        return (
            "# HANDOFF_PROTOCOL\n\n"
            "## Что передать в следующий чат\n"
            f"{self._format_bullets(transfer_rules, fallback='Handoff rules are missing')}\n\n"
            "## Обязательный шаблон handoff\n"
            f"{self._format_numbered(['Текущая фаза и цель', 'Что выполнено', 'Что не выполнено', 'Отклонения и риски', 'Следующий шаг'])}\n\n"
            "## Что осталось открытым\n"
            f"{self._format_open_decisions(fact, policy)}\n"
        )

    def _agent_behavior_rules(self, fact: FactModel, policy: PolicyModel) -> str:
        conflicts = self._format_bullets(policy.conflict_log, fallback="Конфликты правил не обнаружены")
        return (
            "# AGENT_BEHAVIOR_RULES\n\n"
            "## Базовые правила\n"
            f"{self._format_bullets(policy.agent_behavior_rules, fallback='Behavior rules are missing')}\n\n"
            "## Эскалация\n"
            f"{self._format_bullets(policy.escalation_rules, fallback='Escalation rules are missing')}\n\n"
            "## Конфликты и ограничения\n"
            f"{conflicts}\n\n"
            "## Открытые решения\n"
            f"{self._format_open_decisions(fact, policy)}\n"
        )

    def _context_update_policy(self, policy: PolicyModel) -> str:
        return (
            "# CONTEXT_UPDATE_POLICY\n\n"
            "## Когда обновлять контекст\n"
            f"{self._format_bullets(policy.context_update_rules, fallback='Context update policy is missing')}\n\n"
            "## Обязательные файлы\n"
            f"{self._format_numbered(['docs/PROJECT_STATE.md', 'docs/NEXT_CHAT_CONTEXT.md', 'docs/MASTER_PLAN_TRACKER.md', 'docs/REFERENCE_PARITY_CONTRACT_V1.md'])}\n\n"
            "## Порядок обновления\n"
            f"{self._format_numbered(['Обновить PROJECT_STATE', 'Обновить MASTER_PLAN_TRACKER', 'Обновить NEXT_CHAT_CONTEXT', 'Проверить, что активных задач <= 12'])}\n\n"
            "## Проверка перед push\n"
            f"{self._format_numbered(['Ядро документации синхронизировано', 'Закрытые задачи перенесены в архив', 'Критические решения зафиксированы в файлах, а не только в чате'])}\n"
        )

    def _task_tracking_protocol(self, policy: PolicyModel) -> str:
        return (
            "# TASK_TRACKING_PROTOCOL\n\n"
            "## Лимит и статусы активных задач\n"
            f"{self._format_bullets(['Активных задач не больше 12', 'Статусы: pending / in_progress / completed'], fallback='Task tracking baseline is missing')}\n\n"
            "## Формат отчета по итерации\n"
            f"{self._format_numbered(['Completed', 'Not completed', 'Deviation', 'Next', 'Files updated'])}\n\n"
            "## Правила архивации\n"
            f"{self._format_bullets(['Закрытые задачи переносятся в docs/archive/tracker_history/', 'Старые цикловые планы и отчеты хранятся только в docs/archive/'], fallback='Archive rules are missing')}\n\n"
            "## Дополнительные правила\n"
            f"{self._format_bullets(policy.task_tracking_rules, fallback='Additional tracking rules are not defined')}\n"
        )

    def _integration_and_ci_lines(self, fact: FactModel) -> list[str]:
        lines = list(fact.external_integrations)
        for pipeline in fact.ci_pipeline_map:
            lines.append(self._pipeline_line(pipeline))
        return lines

    def _pipeline_line(self, pipeline: CiPipelineFact) -> str:
        trigger_text = ", ".join(pipeline.triggers) if pipeline.triggers else "no triggers"
        return (
            f"{pipeline.provider} | {pipeline.file} | {pipeline.name} | "
            f"triggers={trigger_text} | jobs={len(pipeline.jobs)}"
        )

    def _dependency_lines(self, dependencies: list[ModuleDependencyFact]) -> list[str]:
        lines: list[str] = []
        for edge in dependencies:
            lines.append(
                f"{edge.source_module} -> {edge.target_module} "
                f"(signals={edge.signal_count}, confidence={round(edge.confidence, 3)})"
            )
        return lines

    def _critical_file_lines(self, fact: FactModel) -> list[str]:
        lines: list[str] = []
        for item in fact.critical_files_map:
            lines.append(
                f"{item.path} | reason={item.reason} | risk={item.risk_level} "
                f"| confidence={round(item.confidence, 3)}"
            )
        return lines

    def _verification_steps(self, fact: FactModel) -> list[str]:
        steps: list[str] = []
        seen: set[str] = set()
        for suite in fact.tests_map:
            if suite.command_candidates:
                command = suite.command_candidates[0].strip()
                if command and command not in seen:
                    seen.add(command)
                    steps.append(f"[tests:{suite.suite_id}] {command}")
        for command in fact.key_commands:
            text = command.strip()
            if not text or text in seen:
                continue
            if self._is_test_like_command(text):
                seen.add(text)
                steps.append(text)
        return steps

    def _is_test_like_command(self, command: str) -> bool:
        lower = command.strip().lower()
        return any(token in lower for token in ("test", "pytest", "unittest", "go test", "cargo test", "vitest", "jest"))

    def _format_open_decisions(self, fact: FactModel, policy: PolicyModel) -> str:
        if not policy.open_unknowns:
            return "- Нет открытых решений."
        unknown_lookup = {item.unknown_id: item for item in fact.unknowns}
        lines: list[str] = []
        for unknown_id in policy.open_unknowns:
            info = unknown_lookup.get(unknown_id)
            if isinstance(info, UnknownItem):
                lines.append(
                    f"- {unknown_id} | area={info.area} | impact={info.impact_level} | "
                    f"question={info.suggested_question}"
                )
            else:
                lines.append(f"- {unknown_id} | details=not found in FactModel")
        return "\n".join(lines)

    def _format_bullets(self, items: list[str], fallback: str) -> str:
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        if not cleaned:
            return f"- {fallback}"
        return "\n".join(f"- {item}" for item in cleaned)

    def _format_numbered(self, items: list[str]) -> str:
        cleaned = [str(item).strip() for item in items if str(item).strip()]
        if not cleaned:
            return "1. N/A"
        return "\n".join(f"{idx}. {item}" for idx, item in enumerate(cleaned, start=1))
