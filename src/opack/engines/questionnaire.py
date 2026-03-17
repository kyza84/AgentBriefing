from typing import Any

from opack.contracts.models import FactModel, PolicyModel, UnknownItem


PROFILE_BUDGET = {
    "quick": 10,
    "balanced": 20,
    "strict": 30,
}

IMPACT_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


class QuestionnaireEngine:
    """V1 adaptive questionnaire with unknown-driven answering and conflict checks."""

    def build_questions(self, fact_model: FactModel, profile: str = "balanced") -> list[dict[str, str]]:
        unknowns = self._prioritize_unknowns(fact_model.unknowns)
        budget = PROFILE_BUDGET.get(profile, PROFILE_BUDGET["balanced"])
        questions: list[dict[str, str]] = []
        for unknown in unknowns[:budget]:
            questions.append(
                {
                    "unknown_id": unknown.unknown_id,
                    "area": unknown.area,
                    "impact_level": unknown.impact_level,
                    "question": unknown.suggested_question,
                }
            )
        return questions

    def build_policy_model(
        self,
        fact_model: FactModel,
        profile: str = "balanced",
        answers: dict[str, Any] | None = None,
    ) -> PolicyModel:
        payload = answers or {}
        question_set = self.build_questions(fact_model=fact_model, profile=profile)
        unknown_answers = self._normalize_unknown_answers(payload.get("unknown_answers", {}))
        answered_unknowns = set()
        open_unknowns: list[str] = []

        asked_unknown_ids = {q["unknown_id"] for q in question_set}
        for unknown in self._prioritize_unknowns(fact_model.unknowns):
            if unknown.unknown_id not in asked_unknown_ids:
                open_unknowns.append(unknown.unknown_id)
                continue
            answer = unknown_answers.get(unknown.unknown_id, "").strip()
            if answer:
                answered_unknowns.add(unknown.unknown_id)
            else:
                open_unknowns.append(unknown.unknown_id)

        resolved_unknowns = sorted(answered_unknowns)
        question_count = max(1, len(question_set))
        answer_confidence = len(resolved_unknowns) / question_count

        agent_behavior_rules = self._merge_rules(
            [
                "Follow repository scope and do not perform destructive operations.",
                "Prefer deterministic and traceable outputs.",
            ],
            payload.get("agent_behavior_rules"),
            self._rule_from_unknown_answer(unknown_answers, "u_workflow_001", "Workflow boundary"),
        )
        handoff_rules = self._merge_rules(
            [
                "Update NEXT_CHAT_CONTEXT after material changes.",
                "Record completed/not completed/deviation/next.",
            ],
            payload.get("handoff_rules"),
            self._rule_from_unknown_answer(unknown_answers, "u_entrypoint_001", "Canonical project entrypoint"),
        )
        context_update_rules = self._merge_rules(
            [
                "Update PROJECT_STATE and MASTER_PLAN_TRACKER on material planning changes.",
            ],
            payload.get("context_update_rules"),
        )
        escalation_rules = self._merge_rules(
            [
                "Escalate when scope change impacts V1 boundaries.",
            ],
            payload.get("escalation_rules"),
        )
        task_tracking_rules = self._merge_rules(
            [
                "Track active tasks and evidence paths in MASTER_PLAN_TRACKER.",
            ],
            payload.get("task_tracking_rules"),
            self._rule_from_unknown_answer(unknown_answers, "u_commands_001", "Canonical run/test commands"),
        )

        conflict_log = self._detect_conflicts(
            agent_behavior_rules=agent_behavior_rules,
            escalation_rules=escalation_rules,
        )
        if conflict_log:
            answer_confidence = max(0.0, answer_confidence - 0.2)

        return PolicyModel(
            decision_profile=profile,
            agent_behavior_rules=agent_behavior_rules,
            handoff_rules=handoff_rules,
            context_update_rules=context_update_rules,
            escalation_rules=escalation_rules,
            task_tracking_rules=task_tracking_rules,
            resolved_unknowns=resolved_unknowns,
            open_unknowns=open_unknowns,
            answer_confidence=round(answer_confidence, 3),
            conflict_log=conflict_log,
        )

    def _prioritize_unknowns(self, unknowns: list[UnknownItem]) -> list[UnknownItem]:
        return sorted(
            unknowns,
            key=lambda item: (IMPACT_ORDER.get(item.impact_level, 99), item.unknown_id),
        )

    def _normalize_unknown_answers(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, str] = {}
        for key, raw in value.items():
            if raw is None:
                continue
            text = str(raw).strip()
            if text:
                normalized[str(key)] = text
        return normalized

    def _merge_rules(self, base: list[str], extras: Any, derived: str | None = None) -> list[str]:
        merged = list(base)
        if isinstance(extras, list):
            for item in extras:
                text = str(item).strip()
                if text:
                    merged.append(text)
        if derived:
            merged.append(derived)

        deduped: list[str] = []
        seen = set()
        for rule in merged:
            token = rule.strip().lower()
            if token in seen:
                continue
            seen.add(token)
            deduped.append(rule.strip())
        return deduped

    def _rule_from_unknown_answer(
        self,
        unknown_answers: dict[str, str],
        unknown_id: str,
        label: str,
    ) -> str | None:
        answer = unknown_answers.get(unknown_id, "").strip()
        if not answer:
            return None
        return f"{label}: {answer}"

    def _detect_conflicts(self, agent_behavior_rules: list[str], escalation_rules: list[str]) -> list[str]:
        conflicts: list[str] = []
        normalized_behavior = " | ".join(agent_behavior_rules).lower()
        normalized_escalation = " | ".join(escalation_rules).lower()

        has_read_only = "do not change anything" in normalized_behavior
        has_execute_full = "execute end-to-end" in normalized_behavior
        if has_read_only and has_execute_full:
            conflicts.append("Conflict: read-only and execute end-to-end rules are both present.")

        has_escalate = "escalate" in normalized_escalation
        has_never_escalate = "never escalate" in normalized_escalation
        if has_escalate and has_never_escalate:
            conflicts.append("Conflict: escalation rules contain both escalate and never escalate.")

        return conflicts
