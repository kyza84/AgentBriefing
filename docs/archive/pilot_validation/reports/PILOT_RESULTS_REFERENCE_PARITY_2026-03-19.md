# PILOT_RESULTS_REFERENCE_PARITY_2026-03-19

Updated: 2026-03-18  
Profile: `strict`  
Runner: `opack.monitor.service.run_remote_repo_check`

## Scope
Pilot rerun executed on 3 repositories:
1. `https://github.com/pallets/flask`
2. `https://github.com/fastapi/fastapi`
3. `https://github.com/nestjs/nest`

Artifacts:
1. Raw run summary: `repos_lab/rp06_runs/rp06_results_20260318_135938.json`
2. Pack roots:
   - `repos_lab/rp06_runs/s/20260318_135830_d3bde7/o/pack-5dfa5d5925`
   - `repos_lab/rp06_runs/s/20260318_135834_5b216f/o/pack-0f4396add0`
   - `repos_lab/rp06_runs/s/20260318_135901_40dc11/o/pack-98fc0543d5`

## Snapshot
| Repo | blocking | quality | issues | unknown/open | entry_points | key_commands | tests_map | ci_map | deps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| flask | false | 1.0 | 0 | 2 / 1 | 5 | 2 | 3 | 5 | 3 |
| fastapi | false | 1.0 | 0 | 1 / 0 | 21 | 1 | 8 | 19 | 5 |
| nest | false | 1.0 | 0 | 1 / 0 | 143 | 35 | 10 | 1 | 39 |

## Что определено правильно
1. Стабильно извлекаются структурные факты: стеки, модули, CI сигналы, тестовые контуры, критичные файлы, dependency edges.
2. Generator после RP-02/RP-03 выдает parity-секции по контракту, и validator корректно пропускает валидные секции.
3. Open unknowns (если есть) отображаются в ключевых артефактах и не теряются между `FACT_MODEL` и `POLICY_MODEL`.

## Что пропущено
1. Нет детектора «слишком много entry points / нет канонического entrypoint» (особенно видно на `nestjs/nest`: `entry_points=143`).
2. Нет детектора «слишком много key commands / нет канонической post-change проверки» (`nestjs/nest`: `key_commands=35`).
3. Нет проверки, что выбранный primary CI workflow действительно основной для merge/release (пример: `fastapi` выбрался `Add to Project`).

## Где картина удобная, но неточная
1. `fastapi`: гипотеза canonical entrypoint указывает на `docs_src/.../main.py`, что удобно для заполнения шаблона, но не отражает рабочий runtime entrypoint продукта.
2. `nestjs`: гипотеза canonical entrypoint указывает на `packages/core/index.ts`, хотя в репо много `sample/*/main.ts`; итоговый «канон» вероятно упрощен.
3. `PROJECT_STATE` и `VALIDATION_REPORT` показывают `quality=1.0` даже в случаях высокой неоднозначности выбора entrypoint/command.

## Где validator должен был ругнуться, но промолчал
1. Не ругается на чрезмерную множественность entry points (ambiguous canonical entrypoint risk).
2. Не ругается на чрезмерную множественность команд тестирования/запуска без подтвержденного canonical command.
3. Не ругается на «канонический» entrypoint/command, если он выбран из docs/sample/demo контуров.
4. Не ругается на потенциально неверный primary CI workflow при большом числе workflow-файлов.

## Delta vs baseline
1. Плюс: parity-структура в документах и section-level validator guardrails работают стабильно.
2. Минус: semantic quality-validator пока слабо оценивает неоднозначность extracted operational facts.

## Приоритетные фиксы после пилота
1. Добавить validator-правило `entrypoint_ambiguity_high` (threshold по количеству и типам entrypoint paths).
2. Добавить validator-правило `test_command_ambiguity_high` (много command candidates без подтвержденного canonical).
3. Добавить scanner/questionnaire фильтр-кандидатов для `docs/`, `samples/`, `examples/`, `tests/` как non-primary по умолчанию.
4. Добавить validator-правило `ci_primary_workflow_low_confidence` при большом числе CI workflow и слабом сигнале приоритета.
