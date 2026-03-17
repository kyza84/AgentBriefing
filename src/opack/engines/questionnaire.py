from typing import Any

from opack.contracts.models import FactModel, HypothesisItem, PolicyModel, UnknownItem


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

HYPOTHESIS_AREA_IMPACT = {
    "workflow": "high",
    "delivery": "high",
    "architecture": "medium",
    "testing": "high",
}


class QuestionnaireEngine:
    """V1.1 adaptive questionnaire with hypothesis confirmation flow."""

    def build_questions(self, fact_model: FactModel, profile: str = "balanced") -> list[dict[str, Any]]:
        unknowns = self._prioritize_unknowns(fact_model.unknowns)
        hypotheses = self._prioritize_hypotheses(fact_model.hypotheses)
        budget = PROFILE_BUDGET.get(profile, PROFILE_BUDGET["balanced"])

        hypothesis_unknown_map = self._map_hypothesis_unknowns(fact_model)
        covered_unknown_ids = set(hypothesis_unknown_map.keys())

        candidates: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []

        for hypothesis in hypotheses:
            impact = HYPOTHESIS_AREA_IMPACT.get(hypothesis.area, "medium")
            priority = (
                IMPACT_ORDER.get(impact, 99),
                0,  # hypothesis questions first within same impact
                int(max(0.0, min(1.0, hypothesis.confidence)) * 100),  # lower confidence first
                hypothesis.hypothesis_id,
            )
            question = {
                "question_id": f"h::{hypothesis.hypothesis_id}",
                "question_type": "hypothesis",
                "target_id": hypothesis.hypothesis_id,
                "area": hypothesis.area,
                "impact_level": impact,
                "confidence": round(hypothesis.confidence, 3),
                "question": hypothesis.suggested_question or f"Подтвердите или скорректируйте: {hypothesis.claim}",
                "proposed_claim": hypothesis.claim,
                "response_format": "confirm | edit:<new_text> | reject[:reason]",
            }
            candidates.append((priority, question))

        for unknown in unknowns:
            if unknown.unknown_id in covered_unknown_ids:
                continue
            priority = (
                IMPACT_ORDER.get(unknown.impact_level, 99),
                1,  # generic unknowns second
                0,
                unknown.unknown_id,
            )
            question = {
                "question_id": f"u::{unknown.unknown_id}",
                "question_type": "unknown",
                "unknown_id": unknown.unknown_id,
                "target_id": unknown.unknown_id,
                "area": unknown.area,
                "impact_level": unknown.impact_level,
                "question": unknown.suggested_question,
            }
            candidates.append((priority, question))

        selected = sorted(candidates, key=lambda item: item[0])[:budget]
        return [question for _, question in selected]

    def build_policy_model(
        self,
        fact_model: FactModel,
        profile: str = "balanced",
        answers: dict[str, Any] | None = None,
    ) -> PolicyModel:
        payload = answers or {}
        question_set = self.build_questions(fact_model=fact_model, profile=profile)
        unknown_answers = self._normalize_unknown_answers(payload.get("unknown_answers", {}))
        hypothesis_answers = self._normalize_hypothesis_answers(payload.get("hypothesis_answers", {}))
        answered_unknowns = set()
        open_unknowns: list[str] = []

        asked_unknown_ids = {
            str(q.get("unknown_id", ""))
            for q in question_set
            if q.get("question_type") in {None, "unknown"} and str(q.get("unknown_id", "")).strip()
        }
        asked_hypothesis_ids = {
            str(q.get("target_id", ""))
            for q in question_set
            if q.get("question_type") == "hypothesis" and str(q.get("target_id", "")).strip()
        }
        hypothesis_unknown_map = self._map_hypothesis_unknowns(fact_model)

        for unknown in self._prioritize_unknowns(fact_model.unknowns):
            mapped_hypothesis_id = hypothesis_unknown_map.get(unknown.unknown_id, "")
            hypothesis_is_asked = mapped_hypothesis_id in asked_hypothesis_ids

            if unknown.unknown_id not in asked_unknown_ids and not hypothesis_is_asked:
                open_unknowns.append(unknown.unknown_id)
                continue

            answer = unknown_answers.get(unknown.unknown_id, "").strip()
            hypothesis_decision = hypothesis_answers.get(mapped_hypothesis_id, {}).get("decision", "")
            if answer:
                answered_unknowns.add(unknown.unknown_id)
            elif hypothesis_decision in {"confirm", "edit", "reject"}:
                answered_unknowns.add(unknown.unknown_id)
            else:
                open_unknowns.append(unknown.unknown_id)

        resolved_unknowns = sorted(answered_unknowns)
        resolved_hypotheses = {
            hypothesis_id
            for hypothesis_id in asked_hypothesis_ids
            if hypothesis_answers.get(hypothesis_id, {}).get("decision", "") in {"confirm", "edit", "reject"}
        }

        question_count = max(1, len(asked_unknown_ids) + len(asked_hypothesis_ids))
        answered_count = len(resolved_unknowns) + len(resolved_hypotheses)
        answer_confidence = answered_count / question_count

        fact_hypothesis_map = {item.hypothesis_id: item for item in fact_model.hypotheses}
        entrypoint_rule = self._rule_from_hypothesis_answer(
            hypothesis=fact_hypothesis_map.get("h_entrypoint_001"),
            answer=hypothesis_answers.get("h_entrypoint_001"),
            label="Canonical project entrypoint",
        )
        command_rule = self._rule_from_hypothesis_answer(
            hypothesis=fact_hypothesis_map.get("h_command_001"),
            answer=hypothesis_answers.get("h_command_001"),
            label="Canonical run/test commands",
        )
        tests_rule = self._rule_from_hypothesis_answer(
            hypothesis=fact_hypothesis_map.get("h_tests_001"),
            answer=hypothesis_answers.get("h_tests_001"),
            label="Primary test scope",
        )
        ci_rule = self._rule_from_hypothesis_answer(
            hypothesis=fact_hypothesis_map.get("h_ci_001"),
            answer=hypothesis_answers.get("h_ci_001"),
            label="CI/CD workflow boundary",
        )

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
            entrypoint_rule,
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
            ci_rule,
        )
        task_tracking_rules = self._merge_rules(
            [
                "Track active tasks and evidence paths in MASTER_PLAN_TRACKER.",
            ],
            payload.get("task_tracking_rules"),
            self._rule_from_unknown_answer(unknown_answers, "u_commands_001", "Canonical run/test commands"),
            command_rule,
            tests_rule,
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

    def _prioritize_hypotheses(self, hypotheses: list[HypothesisItem]) -> list[HypothesisItem]:
        pending = [item for item in hypotheses if item.requires_confirmation]
        return sorted(
            pending,
            key=lambda item: (
                IMPACT_ORDER.get(HYPOTHESIS_AREA_IMPACT.get(item.area, "medium"), 99),
                item.confidence,
                item.hypothesis_id,
            ),
        )

    def _map_hypothesis_unknowns(self, fact_model: FactModel) -> dict[str, str]:
        mapping: dict[str, str] = {}
        pending = self._prioritize_hypotheses(fact_model.hypotheses)
        for idx, hypothesis in enumerate(pending, start=1):
            mapping[f"u_hypothesis_{idx:03d}"] = hypothesis.hypothesis_id
        return mapping

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

    def _normalize_hypothesis_answers(self, value: Any) -> dict[str, dict[str, str]]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, dict[str, str]] = {}
        for key, raw in value.items():
            hypothesis_id = str(key).strip()
            if not hypothesis_id:
                continue

            decision = ""
            content = ""
            if isinstance(raw, dict):
                decision = str(raw.get("decision", "")).strip().lower()
                content = str(raw.get("value", "")).strip()
            else:
                text = str(raw).strip()
                lower = text.lower()
                if lower == "confirm":
                    decision = "confirm"
                elif lower.startswith("edit:"):
                    decision = "edit"
                    content = text.split(":", 1)[1].strip()
                elif lower.startswith("reject"):
                    decision = "reject"
                    content = text.split(":", 1)[1].strip() if ":" in text else ""
                elif text:
                    # Compatibility fallback: plain text means edited claim.
                    decision = "edit"
                    content = text

            if decision not in {"confirm", "edit", "reject"}:
                continue
            normalized[hypothesis_id] = {
                "decision": decision,
                "value": content,
            }
        return normalized

    def _merge_rules(self, base: list[str], extras: Any, *derived_rules: str | None) -> list[str]:
        merged = list(base)
        if isinstance(extras, list):
            for item in extras:
                text = str(item).strip()
                if text:
                    merged.append(text)
        for derived in derived_rules:
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

    def _rule_from_hypothesis_answer(
        self,
        hypothesis: HypothesisItem | None,
        answer: dict[str, str] | None,
        label: str,
    ) -> str | None:
        if hypothesis is None or not answer:
            return None

        decision = str(answer.get("decision", "")).strip().lower()
        value = str(answer.get("value", "")).strip()
        if decision == "confirm":
            return f"{label}: {hypothesis.claim}"
        if decision == "edit":
            return f"{label}: {value or hypothesis.claim}"
        if decision == "reject":
            note = value or "hypothesis rejected, requires explicit manual answer"
            return f"{label}: {note}"
        return None

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
