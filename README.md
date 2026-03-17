# AgentBriefing (Operating-Pack Platform)

CLI-first инструмент для генерации operating-pack, чтобы AI-агент мог корректно работать с репозиторием с первого сообщения.

## Что делает проект

- Сканирует репозиторий и извлекает факты о структуре проекта.
- Запускает адаптивный опросник для закрытия неизвестных зон.
- Генерирует operating-pack с артефактами для работы агента.
- Выполняет валидацию полноты и согласованности.
- Даёт простой UI-монитор: вставить ссылку на repo -> запустить проверку -> получить метрики.

## Текущий объём (V1 Builder)

- `opack build` (CLI pipeline): scanner -> questionnaire -> generator -> validator.
- Профили запуска: `quick`, `balanced`, `strict`.
- Поддержка `--answers-file` и `--interactive` режима.
- Генерация ключевых артефактов:
  - `PROJECT_ARCHITECTURE.md`
  - `PROJECT_STATE.md`
  - `FIRST_MESSAGE_INSTRUCTIONS.md`
  - `HANDOFF_PROTOCOL.md`
  - `AGENT_BEHAVIOR_RULES.md`
  - `CONTEXT_UPDATE_POLICY.md`
  - `TASK_TRACKING_PROTOCOL.md`
  - `OPERATING_PACK_MANIFEST.json`
  - `VALIDATION_REPORT.json`
  - `FACT_MODEL.json`
  - `POLICY_MODEL.json`

## Требования

- Python `>=3.11`
- Git (для удалённых репозиториев и monitor UI)

## Быстрый старт

```bash
pip install -e .
```

### 1) Сборка operating-pack через CLI

```bash
opack build --repo . --output ./out --profile balanced
```

С готовыми ответами опросника:

```bash
opack build --repo . --output ./out --profile strict --answers-file ./examples/answers.sample.json
```

Интерактивный режим для unknown-вопросов:

```bash
opack build --repo . --output ./out --profile balanced --interactive
```

### 2) Личный монитор (GUI)

```bash
opack monitor-ui
```

В окне можно:
- выбрать пилотный репозиторий из списка,
- вставить свою ссылку на GitHub репозиторий,
- указать профиль и ответы,
- получить результат проверки и путь к собранному pack.

## Тесты

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Структура проекта

- `src/opack/` - код платформы (engines, orchestrators, monitor, CLI)
- `tests/` - smoke и monitor-тесты
- `examples/` - пример JSON-ответов для опросника
- `docs/` - публичная техническая документация по продукту и пилотной валидации

## Примечание по документации

В репозитории намеренно исключены внутренние prompt/context документы для агентного операционного слоя. Публикуется только программная и продуктовая документация, относящаяся к работе платформы.
