# PROGRAM_ARCHITECTURE_V1

## 1. Назначение
Техническая архитектура первой рабочей версии программы `Operating-Pack Builder`.

Цель:
- из репозитория и ответов пользователя собирать operating-pack,
- выдавать валидированный результат, пригодный для первого чата агента.

## 2. Технический формат V1
- Тип: CLI-first приложение.
- Режим: локальный запуск на одном репозитории.
- Выход: набор файлов operating-pack + manifest + validation report.

## 3. Слои системы

### 3.1 Core Domain (`src/opack/contracts`, `src/opack/core`)
Содержит:
- модели данных,
- статусы,
- ошибки домена.

Правила:
- без I/O,
- без зависимости от конкретного провайдера AI.

### 3.2 Engines (`src/opack/engines`)
Содержит движки стадий V1:
- scanner,
- questionnaire,
- generator,
- validator.

Правила:
- принимают/возвращают строго контрактные модели.

### 3.3 Orchestrator (`src/opack/orchestrators`)
Содержит:
- общий pipeline `scan -> ask -> generate -> validate`,
- управление переходами стадий,
- сбор финального результата.

### 3.4 Adapters (`src/opack/adapters`)
Содержит:
- файловый адаптер (чтение репозитория, запись результатов),
- точки расширения под будущие интеграции.

### 3.5 CLI (`src/opack/cli.py`)
Содержит:
- команды запуска,
- аргументы профиля,
- указание входного репозитория и выходной директории.

## 4. Контракты данных (V1)
- `FactModel`: факты репозитория + unknown + confidence.
- `PolicyModel`: ответы пользователя + правила поведения.
- `OperatingPackManifest`: состав output + provenance.
- `ValidationReport`: найденные проблемы и блокирующий статус.

## 5. Основной pipeline
1. Scanner извлекает структуру репозитория и формирует `FactModel`.
2. Questionnaire формирует первичный `PolicyModel` (пока базовый stub + future answers).
3. Generator выпускает артефакты operating-pack и `OperatingPackManifest`.
4. Validator проверяет полноту и consistency.
5. Orchestrator пишет результат в output-директорию.

## 6. Разделение ответственности
- Ядро отвечает за корректность контрактов.
- Engines отвечают за бизнес-логику стадий.
- Orchestrator отвечает за последовательность стадий и общую транзакцию запуска.
- Adapters отвечают только за внешние I/O операции.
- CLI отвечает только за пользовательский вход в систему.

## 7. Технический долг (policy)
- Любое временное решение фиксируется в tracker как debt item.
- Критичный долг по core contracts и validator блокирует переход к release.
- Долг по адаптерам допустим, если не ломает контракты ядра.

## 8. Этапы реализации после каркаса
1. Реализовать Scanner Baseline (Phase 2).
2. Реализовать adaptive questionnaire logic (Phase 3).
3. Реализовать generator templates (Phase 4).
4. Реализовать validator ruleset (Phase 5).
5. Пилот и стабилизация (Phase 6).
