# IMPLEMENTATION_ROADMAP_V1

## Цель
Практический план разработки рабочей программы после архитектурного каркаса.

## Phase 2 - Scanner Baseline
- Реализовать сбор структуры файлов.
- Добавить определение стеков по сигнатурам.
- Добавить модель unknown/confidence.
- Выдавать `FactModel` в JSON.

## Phase 3 - Questionnaire Engine
- Построить список вопросов из unknown.
- Добавить лимит вопросов по профилю (`quick/balanced/strict`).
- Собирать ответы в `PolicyModel`.

## Phase 4 - Generator Engine
- Сопоставить Fact+Policy в 9 обязательных артефактов.
- Записывать `OPERATING_PACK_MANIFEST`.
- Обеспечить deterministic section ordering.

## Phase 5 - Validator Engine
- Проверки полноты mandatory sections.
- Проверки consistency между артефактами.
- Блокировка run при критичных ошибках.

## Phase 6 - Pilot + Hardening
- Прогон на пилотных репозиториях.
- Измерение времени и полноты.
- Закрытие P0/P1 дефектов перед baseline release.
