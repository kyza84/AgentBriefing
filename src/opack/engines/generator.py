from opack.contracts.models import FactModel, OperatingPackManifest, PolicyModel


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
    """V1 generator hardening: richer, fact-driven operating-pack artifacts."""

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
            "HANDOFF_PROTOCOL.md": self._handoff_protocol(policy_model),
            "AGENT_BEHAVIOR_RULES.md": self._agent_behavior_rules(policy_model),
            "CONTEXT_UPDATE_POLICY.md": self._context_update_policy(policy_model),
            "TASK_TRACKING_PROTOCOL.md": self._task_tracking_protocol(policy_model),
            "VALIDATION_REPORT.json": "{}",
        }

        manifest = OperatingPackManifest(
            pack_id=pack_id,
            artifact_inventory=REQUIRED_ARTIFACTS,
            source_provenance={
                "PROJECT_ARCHITECTURE.md": "FactModel",
                "PROJECT_STATE.md": "FactModel",
                "FIRST_MESSAGE_INSTRUCTIONS.md": "PolicyModel",
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
                "generator_version": "0.2.0",
                "decision_profile": policy_model.decision_profile,
                "resolved_unknowns": len(policy_model.resolved_unknowns),
                "open_unknowns": len(policy_model.open_unknowns),
            },
        )
        return artifacts, manifest

    def _project_architecture(self, fact: FactModel, policy: PolicyModel) -> str:
        return (
            "# PROJECT_ARCHITECTURE\n\n"
            "## Обнаруженные стеки\n"
            f"{self._format_bullets(fact.detected_stacks, fallback='UNKNOWN: стек не определен')}\n\n"
            "## Модули\n"
            f"{self._format_bullets([f'{m.name} ({m.kind})' for m in fact.modules], fallback='UNKNOWN: модули не выделены')}\n\n"
            "## Точки входа\n"
            f"{self._format_bullets(fact.entry_points, fallback='UNKNOWN: точка входа не определена')}\n\n"
            "## Внешние интеграции\n"
            f"{self._format_bullets(fact.external_integrations, fallback='Нет явных интеграций')}\n\n"
            "## Архитектурные риски\n"
            f"{self._format_unknowns(policy.open_unknowns, prefix='Открытый unknown')}\n"
        )

    def _project_state(self, fact: FactModel, policy: PolicyModel) -> str:
        confidence_lines = [
            f"coverage={fact.confidence_breakdown.get('coverage_confidence', 0.0)}",
            f"signal={fact.confidence_breakdown.get('signal_confidence', 0.0)}",
            f"coherence={fact.confidence_breakdown.get('coherence_confidence', 0.0)}",
        ]
        return (
            "# PROJECT_STATE\n\n"
            f"- Репозиторий: {fact.repo_id}\n"
            f"- Профиль решений: {policy.decision_profile}\n"
            f"- Общая уверенность сканера: {fact.confidence_overall}\n"
            f"- Breakdown: {', '.join(confidence_lines)}\n"
            f"- Unknown (fact): {len(fact.unknowns)}\n"
            f"- Resolved unknown: {len(policy.resolved_unknowns)}\n"
            f"- Open unknown: {len(policy.open_unknowns)}\n\n"
            "## Предупреждения сканера\n"
            f"{self._format_bullets(fact.scanner_warnings, fallback='Предупреждений нет')}\n\n"
            "## Открытые unknown\n"
            f"{self._format_unknowns(policy.open_unknowns, prefix='UNKNOWN')}\n"
        )

    def _first_message_instructions(self, fact: FactModel, policy: PolicyModel) -> str:
        startup_steps = [
            "Сначала прочитай PROJECT_STATE.md и PROJECT_ARCHITECTURE.md.",
            "Проверь доступные команды запуска и тестов.",
            "Проверь открытые unknown перед изменениями.",
            "Перед правками дай краткий план: Completed / Not completed / Deviation / Next.",
        ]
        if fact.key_commands:
            startup_steps.append(f"Рекомендуемая команда проверки: {fact.key_commands[0]}")
        if fact.entry_points:
            startup_steps.append(f"Ключевая точка входа: {fact.entry_points[0]}")
        return (
            "# FIRST_MESSAGE_INSTRUCTIONS\n\n"
            "## Первый ответ агента\n"
            f"{self._format_numbered(startup_steps)}\n\n"
            "## Поведенческие ограничения\n"
            f"{self._format_bullets(policy.agent_behavior_rules, fallback='UNKNOWN: правила поведения не заданы')}\n"
        )

    def _handoff_protocol(self, policy: PolicyModel) -> str:
        return (
            "# HANDOFF_PROTOCOL\n\n"
            "## Что передать в следующую сессию\n"
            f"{self._format_bullets(policy.handoff_rules, fallback='UNKNOWN: правила handoff не заданы')}\n\n"
            "## Минимальный handoff-пакет\n"
            f"{self._format_numbered(['Текущий статус фазы', 'Что выполнено', 'Что не выполнено', 'Где лежат артефакты проверки', 'Следующее действие'])}\n"
        )

    def _agent_behavior_rules(self, policy: PolicyModel) -> str:
        conflicts = self._format_bullets(policy.conflict_log, fallback="Конфликты правил не обнаружены")
        return (
            "# AGENT_BEHAVIOR_RULES\n\n"
            "## Основные правила\n"
            f"{self._format_bullets(policy.agent_behavior_rules, fallback='UNKNOWN: правила поведения не заданы')}\n\n"
            "## Эскалация\n"
            f"{self._format_bullets(policy.escalation_rules, fallback='UNKNOWN: правила эскалации не заданы')}\n\n"
            "## Конфликты\n"
            f"{conflicts}\n"
        )

    def _context_update_policy(self, policy: PolicyModel) -> str:
        return (
            "# CONTEXT_UPDATE_POLICY\n\n"
            "## Когда обновлять контекст\n"
            f"{self._format_bullets(policy.context_update_rules, fallback='UNKNOWN: политика обновления контекста не задана')}\n\n"
            "## Минимум для material update\n"
            f"{self._format_numbered(['PROJECT_STATE', 'NEXT_CHAT_CONTEXT', 'MASTER_PLAN_TRACKER'])}\n"
        )

    def _task_tracking_protocol(self, policy: PolicyModel) -> str:
        return (
            "# TASK_TRACKING_PROTOCOL\n\n"
            "## Формат отчета по итерации\n"
            f"{self._format_numbered(['Completed', 'Not completed', 'Deviation', 'Next', 'Evidence paths'])}\n\n"
            "## Дополнительные правила\n"
            f"{self._format_bullets(policy.task_tracking_rules, fallback='UNKNOWN: правила трекинга задач не заданы')}\n"
        )

    def _format_bullets(self, items: list[str], fallback: str) -> str:
        cleaned = [str(i).strip() for i in items if str(i).strip()]
        if not cleaned:
            return f"- {fallback}"
        return "\n".join(f"- {item}" for item in cleaned)

    def _format_numbered(self, items: list[str]) -> str:
        cleaned = [str(i).strip() for i in items if str(i).strip()]
        return "\n".join(f"{idx}. {item}" for idx, item in enumerate(cleaned, start=1))

    def _format_unknowns(self, unknown_ids: list[str], prefix: str) -> str:
        if not unknown_ids:
            return "- Нет открытых unknown"
        return "\n".join(f"- {prefix}: {uid}" for uid in unknown_ids)
