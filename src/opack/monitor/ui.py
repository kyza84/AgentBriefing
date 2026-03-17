from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from opack.monitor.service import (
    MonitorCheckResult,
    load_answers_payload,
    load_pilot_repo_urls,
    run_remote_repo_check,
)


class PersonalMonitorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Личный монитор Operating-Pack")
        self.root.geometry("980x700")

        self.repo_var = tk.StringVar()
        self.ref_var = tk.StringVar(value="HEAD")
        self.profile_var = tk.StringVar(value="balanced")
        self.answers_var = tk.StringVar()
        self.last_pack_dir: str = ""

        default_answers = Path.cwd() / "examples" / "answers.sample.json"
        if default_answers.exists():
            self.answers_var.set(str(default_answers))

        self._build_layout()
        self._load_pilot_list()

    def _build_layout(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Пилотные репозитории:").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.pilot_combo = ttk.Combobox(frame, state="readonly")
        self.pilot_combo.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 6))
        self.pilot_combo.bind("<<ComboboxSelected>>", self._on_pilot_select)

        ttk.Label(frame, text="Ссылка на репозиторий:").grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(frame, textvariable=self.repo_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=(0, 6))

        ttk.Label(frame, text="Git ref:").grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(frame, textvariable=self.ref_var, width=20).grid(row=2, column=1, sticky="w", pady=(0, 6))

        ttk.Label(frame, text="Профиль:").grid(row=2, column=2, sticky="e", pady=(0, 6))
        ttk.Combobox(
            frame,
            state="readonly",
            textvariable=self.profile_var,
            values=["quick", "balanced", "strict"],
            width=12,
        ).grid(row=2, column=3, sticky="w", pady=(0, 6))

        ttk.Label(frame, text="Файл ответов:").grid(row=3, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(frame, textvariable=self.answers_var).grid(row=3, column=1, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Button(frame, text="Выбрать", command=self._browse_answers_file).grid(row=3, column=3, sticky="w", pady=(0, 6))

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(8, 10))

        self.run_button = ttk.Button(button_row, text="Запустить проверку", command=self._start_run)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(button_row, text="Открыть папку pack", command=self._open_pack_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="Очистить вывод", command=self._clear_output).pack(side=tk.LEFT, padx=(8, 0))

        self.output = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=28)
        self.output.grid(row=5, column=0, columnspan=4, sticky="nsew")

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(5, weight=1)

    def _load_pilot_list(self) -> None:
        registry = Path.cwd() / "docs" / "pilot_validation" / "PILOT_REPO_REGISTRY.md"
        repos = load_pilot_repo_urls(registry)
        self.pilot_combo["values"] = repos
        if repos:
            self.pilot_combo.current(0)
            self.repo_var.set(repos[0])

    def _on_pilot_select(self, _event: object) -> None:
        value = self.pilot_combo.get().strip()
        if value:
            self.repo_var.set(value)

    def _browse_answers_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Выбор JSON с ответами",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
        )
        if path:
            self.answers_var.set(path)

    def _clear_output(self) -> None:
        self.output.delete("1.0", tk.END)

    def _open_pack_folder(self) -> None:
        if not self.last_pack_dir:
            messagebox.showinfo("Монитор", "Папка с pack пока не создана.")
            return
        pack = Path(self.last_pack_dir)
        if not pack.exists():
            messagebox.showerror("Монитор", f"Папка pack не найдена:\n{pack}")
            return
        os.startfile(str(pack))

    def _append(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)

    def _start_run(self) -> None:
        repo_url = self.repo_var.get().strip()
        if not repo_url:
            messagebox.showerror("Монитор", "Нужно указать ссылку на репозиторий.")
            return

        answers_path = self.answers_var.get().strip()
        answers_payload = {}
        if answers_path:
            try:
                answers_payload = load_answers_payload(Path(answers_path))
            except Exception as exc:
                messagebox.showerror("Монитор", f"Не удалось загрузить файл ответов:\n{exc}")
                return

        self.run_button.config(state=tk.DISABLED)
        self._append("\n=== СТАРТ ПРОГОНА ===\n")
        self._append(f"repo={repo_url}\n")
        self._append(f"profile={self.profile_var.get()}\n")

        thread = threading.Thread(
            target=self._run_worker,
            args=(repo_url, self.ref_var.get().strip(), self.profile_var.get(), answers_payload),
            daemon=True,
        )
        thread.start()

    def _run_worker(self, repo_url: str, git_ref: str, profile: str, answers_payload: dict) -> None:
        try:
            result = run_remote_repo_check(
                repo_url=repo_url,
                workspace_root=Path.cwd() / ".monitor",
                profile=profile,
                git_ref=git_ref or "HEAD",
                answers_payload=answers_payload,
            )
            self.root.after(0, lambda: self._on_run_success(result))
        except Exception as exc:
            self.root.after(0, lambda: self._on_run_error(exc))

    def _on_run_success(self, result: MonitorCheckResult) -> None:
        self.last_pack_dir = result.pack_dir
        self._append(self._render_result(result))
        self._append("=== КОНЕЦ ПРОГОНА ===\n")
        self.run_button.config(state=tk.NORMAL)

    def _on_run_error(self, exc: Exception) -> None:
        self._append(f"[ОШИБКА] {exc}\n")
        self._append("=== КОНЕЦ ПРОГОНА ===\n")
        self.run_button.config(state=tk.NORMAL)

    def _render_result(self, result: MonitorCheckResult) -> str:
        lines = [
            f"run_id={result.run_id}",
            f"repo_head_sha={result.repo_head_sha}",
            f"папка_pack={result.pack_dir}",
            f"блокирующий_статус={result.blocking_status}",
            f"оценка_качества={result.quality_score}",
            f"количество_проблем={result.issues_count}",
            f"критичных_проблем={result.critical_issues}",
            f"unknown_всего={result.unknown_count}",
            f"unknown_resolved={result.resolved_unknown_count}",
            f"unknown_open={result.open_unknown_count}",
            f"обнаруженные_стеки={', '.join(result.detected_stacks)}",
            f"количество_entry_points={result.entry_points_count}",
            f"количество_key_commands={result.key_commands_count}",
            f"окружения={', '.join(result.environments)}",
            f"внешние_интеграции={', '.join(result.external_integrations)}",
        ]
        if result.error_message:
            lines.append(f"сообщение_pipeline={result.error_message}")
        return "\n".join(lines) + "\n"


def launch_monitor_ui() -> None:
    root = tk.Tk()
    PersonalMonitorApp(root)
    root.mainloop()
