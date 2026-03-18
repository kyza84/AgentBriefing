# REFERENCE_PARITY_CONTRACT_V1

Updated: 2026-03-18
Status: Active (V1.3 RP-01 baseline)

## 1. Purpose
This contract fixes minimum parity requirements for generated operating-pack so output is operationally useful, not just structurally complete.

## 2. Scope
Contract applies to V1 Builder generated artifacts:
1. `PROJECT_ARCHITECTURE.md`
2. `PROJECT_STATE.md`
3. `FIRST_MESSAGE_INSTRUCTIONS.md`
4. `HANDOFF_PROTOCOL.md`
5. `AGENT_BEHAVIOR_RULES.md`
6. `CONTEXT_UPDATE_POLICY.md`
7. `TASK_TRACKING_PROTOCOL.md`
8. `OPERATING_PACK_MANIFEST.json`
9. `VALIDATION_REPORT.json`

## 3. Source-of-truth classes
Each section must explicitly map to one source class:
1. `scanner_fact` - extracted from repository scan (`FactModel`).
2. `questionnaire_policy` - derived from user answers (`PolicyModel`).
3. `derived_runtime` - deterministic synthesis from facts/policy (counts, summary, linkage).

## 4. Required section matrix

## PROJECT_ARCHITECTURE.md
1. `## Обнаруженные стеки` (`scanner_fact`)
2. `## Модули и границы` (`scanner_fact`)
3. `## Точки входа и команды запуска` (`scanner_fact`)
4. `## Внешние интеграции и CI/CD` (`scanner_fact`)
5. `## Зависимости между модулями` (`scanner_fact`)
6. `## Критичные файлы` (`scanner_fact`)
7. `## Открытые решения` (`questionnaire_policy`)

## PROJECT_STATE.md
1. `## Снимок прогона` (`derived_runtime`)
2. `## Операционная готовность` (`scanner_fact`)
3. `## Неопределенности и риски` (`questionnaire_policy`)
4. `## Предупреждения сканера` (`scanner_fact`)

## FIRST_MESSAGE_INSTRUCTIONS.md
1. `## Порядок чтения контекста` (`questionnaire_policy`)
2. `## Чеклист первого сообщения` (`derived_runtime`)
3. `## Что проверить после изменений` (`scanner_fact`)
4. `## Открытые решения перед рисковыми правками` (`questionnaire_policy`)

## HANDOFF_PROTOCOL.md
1. `## Что передать в следующий чат` (`questionnaire_policy`)
2. `## Обязательный шаблон handoff` (`questionnaire_policy`)
3. `## Что осталось открытым` (`questionnaire_policy`)

## AGENT_BEHAVIOR_RULES.md
1. `## Базовые правила` (`questionnaire_policy`)
2. `## Эскалация` (`questionnaire_policy`)
3. `## Конфликты и ограничения` (`questionnaire_policy`)
4. `## Открытые решения` (`questionnaire_policy`)

## CONTEXT_UPDATE_POLICY.md
1. `## Когда обновлять контекст` (`questionnaire_policy`)
2. `## Обязательные файлы` (`questionnaire_policy`)
3. `## Порядок обновления` (`questionnaire_policy`)
4. `## Проверка перед push` (`questionnaire_policy`)

## TASK_TRACKING_PROTOCOL.md
1. `## Лимит и статусы активных задач` (`questionnaire_policy`)
2. `## Формат отчета по итерации` (`questionnaire_policy`)
3. `## Правила архивации` (`questionnaire_policy`)

## 5. Open decisions requirement
For parity, open unknowns must be visible in artifacts, not hidden only in JSON:
1. `PROJECT_STATE.md` must list all `open_unknowns`.
2. `PROJECT_ARCHITECTURE.md` must include architecture-relevant open unknowns/risk notes.
3. `FIRST_MESSAGE_INSTRUCTIONS.md` must include explicit caution block if open unknowns exist.
4. `AGENT_BEHAVIOR_RULES.md` must expose unresolved behavioral constraints.
5. `HANDOFF_PROTOCOL.md` must include unresolved decisions transfer block.

## 6. Validator mapping (for RP-03)
Validator must check:
1. mandatory section presence by title (not only H2 count),
2. open unknown visibility in required artifacts,
3. consistency between `FactModel` signals and architecture/state/first-message sections,
4. no silent pass when operational sections are missing.

## 7. Change policy
1. Contract changes require explicit owner approval.
2. Any contract change must update:
   - `docs/MASTER_PLAN_TRACKER.md`
   - `docs/PROJECT_STATE.md`
   - `docs/NEXT_CHAT_CONTEXT.md`
