import argparse
import json
import sys
from pathlib import Path
from typing import Any

from opack.core.errors import GateBlockedError
from opack.orchestrators.build_pipeline import BuildPipeline


def _load_answers_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    content = Path(path).read_text(encoding="utf-8-sig")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("Файл ответов должен содержать JSON-объект.")
    return parsed


def _collect_interactive_unknown_answers(
    pipeline: BuildPipeline,
    repo_path: Path,
    profile: str,
    existing_answers: dict[str, Any],
) -> tuple[dict[str, Any], Any]:
    fact_model = pipeline.scanner.scan(repo_path=repo_path, profile=profile)
    questions = pipeline.questionnaire.build_questions(fact_model=fact_model, profile=profile)

    merged_answers = dict(existing_answers)
    unknown_answers_raw = merged_answers.get("unknown_answers", {})
    unknown_answers = dict(unknown_answers_raw) if isinstance(unknown_answers_raw, dict) else {}
    hypothesis_answers_raw = merged_answers.get("hypothesis_answers", {})
    hypothesis_answers = dict(hypothesis_answers_raw) if isinstance(hypothesis_answers_raw, dict) else {}

    if questions:
        print("[ОПРОСНИК] Режим ввода ответов")
    for item in questions:
        question_type = str(item.get("question_type", "unknown"))

        if question_type == "hypothesis":
            hypothesis_id = str(item.get("target_id", "")).strip()
            if not hypothesis_id:
                continue
            if str(hypothesis_answers.get(hypothesis_id, "")).strip():
                continue

            print(f"\n[{item.get('impact_level', 'medium')}] {item.get('question', '')}")
            proposed = str(item.get("proposed_claim", "")).strip()
            if proposed:
                print(f"hypothesis: {proposed}")
            print(f"id: {hypothesis_id}")
            print("Формат ответа: confirm | edit:<new_text> | reject[:reason]")
            answer = input("> ").strip()
            if answer:
                hypothesis_answers[hypothesis_id] = answer
            continue

        unknown_id = str(item.get("unknown_id", "")).strip()
        if not unknown_id:
            continue
        if str(unknown_answers.get(unknown_id, "")).strip():
            continue

        print(f"\n[{item.get('impact_level', 'medium')}] {item.get('question', '')}")
        print(f"id: {unknown_id}")
        answer = input("> ").strip()
        if answer:
            unknown_answers[unknown_id] = answer

    merged_answers["unknown_answers"] = unknown_answers
    merged_answers["hypothesis_answers"] = hypothesis_answers
    return merged_answers, fact_model


def build_command(args: argparse.Namespace) -> int:
    pipeline = BuildPipeline()
    repo_path = Path(args.repo).resolve()
    output_path = Path(args.output).resolve()

    try:
        answers = _load_answers_file(args.answers_file)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"[ОШИБКА] Не удалось загрузить файл ответов: {exc}")
        return 1

    fact_model = None
    if args.interactive:
        answers, fact_model = _collect_interactive_unknown_answers(
            pipeline=pipeline,
            repo_path=repo_path,
            profile=args.profile,
            existing_answers=answers,
        )

    try:
        result = pipeline.run(
            repo_path=repo_path,
            output_path=output_path,
            profile=args.profile,
            answers=answers,
            fact_model=fact_model,
        )
    except GateBlockedError as exc:
        print(f"[ЗАБЛОКИРОВАНО] {exc}")
        return 2

    print("[УСПЕХ] Operating-pack сгенерирован")
    print(f"pack_id={result['pack_id']}")
    print(f"папка_результата={result['output_dir']}")
    print(f"оценка_качества={result['quality_score']}")
    print(f"количество_проблем={result['issues']}")
    return 0


def monitor_ui_command(_args: argparse.Namespace) -> int:
    from opack.monitor.ui import launch_monitor_ui

    launch_monitor_ui()
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="opack", description="CLI генератор operating-pack")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Собрать operating-pack из репозитория")
    b.add_argument("--repo", required=True, help="Путь к репозиторию")
    b.add_argument("--output", default="./out", help="Папка для результата")
    b.add_argument("--profile", choices=["quick", "balanced", "strict"], default="balanced")
    b.add_argument("--answers-file", help="Путь к JSON с ответами опросника")
    b.add_argument("--interactive", action="store_true", help="Задать неотвеченные вопросы в терминале")
    b.set_defaults(func=build_command)

    m = sub.add_parser("monitor-ui", help="Открыть личный монитор проверок")
    m.set_defaults(func=monitor_ui_command)
    return p


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = parser()
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
