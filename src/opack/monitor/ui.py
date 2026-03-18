from __future__ import annotations

import os
import re
import threading
import tkinter as tk
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Any

from opack.monitor.service import (
    MonitorCheckResult,
    MonitorStageEvent,
    discard_session,
    load_answers_payload,
    load_pilot_repo_urls,
    start_remote_repo_session,
    submit_session_answers,
)


def build_questionnaire_seed_payload(
    questions: list[dict[str, Any]],
    seed_answers: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = deepcopy(seed_answers) if isinstance(seed_answers, dict) else {}

    unknown_answers = payload.get("unknown_answers", {})
    if not isinstance(unknown_answers, dict):
        unknown_answers = {}
    hypothesis_answers = payload.get("hypothesis_answers", {})
    if not isinstance(hypothesis_answers, dict):
        hypothesis_answers = {}

    for item in questions:
        qtype = str(item.get("question_type", "unknown"))
        if qtype == "hypothesis":
            hypothesis_id = str(item.get("target_id", "")).strip()
            if hypothesis_id and hypothesis_id not in hypothesis_answers:
                hypothesis_answers[hypothesis_id] = "confirm"
        else:
            unknown_id = str(item.get("unknown_id", "")).strip()
            if unknown_id and unknown_id not in unknown_answers:
                unknown_answers[unknown_id] = ""

    payload["unknown_answers"] = unknown_answers
    payload["hypothesis_answers"] = hypothesis_answers
    return payload


def parse_hypothesis_answer(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        decision = str(value.get("decision", "")).strip().lower()
        text = str(value.get("value", "")).strip()
        if decision in {"confirm", "edit", "reject"}:
            return {"decision": decision, "value": text}

    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if lowered == "confirm":
            return {"decision": "confirm", "value": ""}
        if lowered.startswith("edit:"):
            return {"decision": "edit", "value": text.split(":", 1)[1].strip()}
        if lowered.startswith("reject"):
            reason = text.split(":", 1)[1].strip() if ":" in text else ""
            return {"decision": "reject", "value": reason}
        if text:
            return {"decision": "edit", "value": text}

    return {"decision": "confirm", "value": ""}


def validate_repo_url(repo_url: str) -> tuple[bool, str]:
    value = str(repo_url or "").strip()
    if not value:
        return False, "Ссылка на репозиторий пустая."
    pattern = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/?(?:\.git)?$")
    if not pattern.match(value):
        return False, "Нужен формат: https://github.com/<owner>/<repo>"
    return True, ""


def build_runtime_error_hint(error_text: str) -> str:
    lower = str(error_text or "").lower()
    if "filename too long" in lower:
        return "Подсказка: включи long paths в Windows/Git или используй более короткий workspace path."
    if "failed to clone repository" in lower:
        return "Подсказка: проверь URL, доступ к репозиторию и сетевое подключение."
    if "session not found" in lower:
        return "Подсказка: сессия устарела, запусти проверку заново."
    if "json" in lower:
        return "Подсказка: проверь корректность формата ответа в опроснике."
    return ""


def render_preview_content(path: Path, max_bytes: int = 300_000) -> str:
    data = path.read_bytes()
    if b"\x00" in data[:2048]:
        return "[BINARY FILE] Предпросмотр недоступен для бинарных файлов."

    truncated = False
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True

    text = data.decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n[TRUNCATED]"
    return text


class QuestionnaireDialog:
    def __init__(
        self,
        parent: tk.Tk,
        questions: list[dict[str, Any]],
        seed_answers: dict[str, Any] | None,
        colors: dict[str, str],
    ) -> None:
        self.questions = questions
        self.colors = colors
        self.result: dict[str, Any] | None = None
        self.index = 0

        seed = build_questionnaire_seed_payload(questions=questions, seed_answers=seed_answers)
        seed_unknown = seed.get("unknown_answers", {})
        seed_hypothesis = seed.get("hypothesis_answers", {})

        self.asked_unknown_ids: list[str] = []
        self.asked_hypothesis_ids: list[str] = []
        for item in questions:
            qtype = str(item.get("question_type", "unknown"))
            if qtype == "hypothesis":
                hid = str(item.get("target_id", "")).strip()
                if hid:
                    self.asked_hypothesis_ids.append(hid)
            else:
                uid = str(item.get("unknown_id", "")).strip()
                if uid:
                    self.asked_unknown_ids.append(uid)

        self.extra_unknown_answers: dict[str, Any] = {}
        self.extra_hypothesis_answers: dict[str, Any] = {}
        if isinstance(seed_unknown, dict):
            self.extra_unknown_answers = {
                str(k): v
                for k, v in seed_unknown.items()
                if str(k) not in set(self.asked_unknown_ids)
            }
        if isinstance(seed_hypothesis, dict):
            self.extra_hypothesis_answers = {
                str(k): v
                for k, v in seed_hypothesis.items()
                if str(k) not in set(self.asked_hypothesis_ids)
            }

        self.unknown_state: dict[str, str] = {}
        for uid in self.asked_unknown_ids:
            raw = seed_unknown.get(uid, "") if isinstance(seed_unknown, dict) else ""
            self.unknown_state[uid] = str(raw)

        self.hypothesis_state: dict[str, dict[str, str]] = {}
        for hid in self.asked_hypothesis_ids:
            raw = seed_hypothesis.get(hid, "confirm") if isinstance(seed_hypothesis, dict) else "confirm"
            self.hypothesis_state[hid] = parse_hypothesis_answer(raw)

        self.counter_var = tk.StringVar(value="")
        self.meta_var = tk.StringVar(value="")
        self.question_var = tk.StringVar(value="")
        self.id_var = tk.StringVar(value="")
        self.proposed_var = tk.StringVar(value="")
        self.answer_state_var = tk.StringVar(value="")
        self.format_var = tk.StringVar(value="")
        self.local_progress_var = tk.IntVar(value=0)

        self.unknown_answer_var = tk.StringVar(value="")
        self.h_decision_var = tk.StringVar(value="confirm")
        self.h_text_var = tk.StringVar(value="")

        self.window = tk.Toplevel(parent)
        self.window.title("Опросник")
        self.window.configure(bg=self.colors["app_bg"])
        self.window.geometry("980x620")
        self.window.minsize(840, 540)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.bind("<Alt-Left>", lambda _event: self._on_prev())
        self.window.bind("<Alt-Right>", lambda _event: self._on_next())
        self.window.bind("<Control-Return>", lambda _event: self._on_submit())

        self._build_layout()
        self._render_current_question()

    def _build_layout(self) -> None:
        root = tk.Frame(self.window, bg=self.colors["app_bg"])
        root.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        tk.Label(
            root,
            text="Опросник",
            bg=self.colors["app_bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            root,
            text="Вопросы показываются по одному. Заполни ответ и продолжай.",
            bg=self.colors["app_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(2, 10))

        status_row = tk.Frame(root, bg=self.colors["app_bg"])
        status_row.pack(fill=tk.X, pady=(0, 10))
        tk.Label(
            status_row,
            textvariable=self.answer_state_var,
            bg=self.colors["app_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        self.local_progress = ttk.Progressbar(
            status_row,
            orient="horizontal",
            mode="determinate",
            maximum=max(1, len(self.questions)),
            variable=self.local_progress_var,
        )
        self.local_progress.pack(fill=tk.X, pady=(4, 0))

        self.card = tk.Frame(
            root,
            bg=self.colors["panel_bg"],
            highlightbackground=self.colors["panel_border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        self.card.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            self.card,
            textvariable=self.counter_var,
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        ).pack(fill=tk.X)

        tk.Label(
            self.card,
            textvariable=self.meta_var,
            bg=self.colors["panel_bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill=tk.X, pady=(2, 0))

        tk.Label(
            self.card,
            textvariable=self.id_var,
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Consolas", 9),
            anchor="w",
            justify="left",
        ).pack(fill=tk.X, pady=(1, 0))

        tk.Label(
            self.card,
            textvariable=self.question_var,
            bg=self.colors["panel_bg"],
            fg=self.colors["text"],
            font=("Segoe UI", 11),
            wraplength=900,
            anchor="w",
            justify="left",
        ).pack(fill=tk.X, pady=(8, 8))

        tk.Label(
            self.card,
            textvariable=self.format_var,
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Consolas", 9),
            wraplength=900,
            anchor="w",
            justify="left",
        ).pack(fill=tk.X, pady=(0, 8))

        self.proposed_label = tk.Label(
            self.card,
            textvariable=self.proposed_var,
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            wraplength=900,
            anchor="w",
            justify="left",
        )

        self.unknown_frame = tk.Frame(self.card, bg=self.colors["panel_bg"])
        tk.Label(
            self.unknown_frame,
            text="Ответ:",
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        ).pack(fill=tk.X)
        self.unknown_entry = tk.Entry(
            self.unknown_frame,
            textvariable=self.unknown_answer_var,
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["panel_border"],
            highlightcolor=self.colors["progress_fill"],
            font=("Consolas", 11),
        )
        self.unknown_entry.pack(fill=tk.X)

        self.hypothesis_frame = tk.Frame(self.card, bg=self.colors["panel_bg"])
        top = tk.Frame(self.hypothesis_frame, bg=self.colors["panel_bg"])
        top.pack(fill=tk.X)
        tk.Label(
            top,
            text="Решение:",
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        ).pack(side=tk.LEFT)
        self.decision_combo = ttk.Combobox(
            top,
            state="readonly",
            values=["confirm", "edit", "reject"],
            width=14,
            textvariable=self.h_decision_var,
        )
        self.decision_combo.pack(side=tk.LEFT, padx=(8, 0))

        tk.Label(
            self.hypothesis_frame,
            text="Текст (для edit/reject):",
            bg=self.colors["panel_bg"],
            fg=self.colors["muted"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
        ).pack(fill=tk.X, pady=(6, 0))
        self.h_text_entry = tk.Entry(
            self.hypothesis_frame,
            textvariable=self.h_text_var,
            bg=self.colors["input_bg"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.colors["panel_border"],
            highlightcolor=self.colors["progress_fill"],
            font=("Consolas", 11),
        )
        self.h_text_entry.pack(fill=tk.X)

        actions = tk.Frame(root, bg=self.colors["app_bg"])
        actions.pack(fill=tk.X, pady=(10, 0))
        self.prev_button = ttk.Button(actions, text="Назад", style="Accent.TButton", command=self._on_prev)
        self.prev_button.pack(side=tk.LEFT)
        self.next_button = ttk.Button(actions, text="Далее", style="Accent.TButton", command=self._on_next)
        self.next_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Отмена", style="Accent.TButton", command=self._on_cancel).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Завершить опросник", style="Accent.TButton", command=self._on_submit).pack(side=tk.RIGHT, padx=(0, 8))

    def _question_is_answered(self, question: dict[str, Any]) -> bool:
        qtype = str(question.get("question_type", "unknown")).strip().lower()
        if qtype == "hypothesis":
            hid = str(question.get("target_id", "")).strip()
            if not hid:
                return False
            state = self.hypothesis_state.get(hid, {})
            decision = str(state.get("decision", "")).strip().lower()
            if decision not in {"confirm", "edit", "reject"}:
                return False
            if decision == "confirm":
                return True
            return bool(str(state.get("value", "")).strip())
        uid = str(question.get("unknown_id", "")).strip()
        if not uid:
            return False
        return bool(str(self.unknown_state.get(uid, "")).strip())

    def _refresh_answer_progress(self) -> None:
        total = len(self.questions)
        if total <= 0:
            self.local_progress_var.set(0)
            self.answer_state_var.set("Ответы: 0/0")
            return
        answered = sum(1 for question in self.questions if self._question_is_answered(question))
        self.local_progress_var.set(answered)
        self.answer_state_var.set(f"Ответы: {answered}/{total}")

    def _current_question(self) -> dict[str, Any]:
        if not self.questions:
            return {}
        return self.questions[self.index]

    def _save_current_answer(self) -> None:
        question = self._current_question()
        if not question:
            return

        qtype = str(question.get("question_type", "unknown"))
        if qtype == "hypothesis":
            hid = str(question.get("target_id", "")).strip()
            if not hid:
                return
            decision = self.h_decision_var.get().strip().lower()
            if decision not in {"confirm", "edit", "reject"}:
                decision = "confirm"
            self.hypothesis_state[hid] = {
                "decision": decision,
                "value": self.h_text_var.get().strip(),
            }
        else:
            uid = str(question.get("unknown_id", "")).strip()
            if not uid:
                return
            self.unknown_state[uid] = self.unknown_answer_var.get().strip()
        self._refresh_answer_progress()

    def _render_current_question(self) -> None:
        total = len(self.questions)
        if total == 0:
            self.counter_var.set("Вопросов нет")
            self.meta_var.set("")
            self.id_var.set("")
            self.question_var.set("")
            self.proposed_var.set("")
            self.format_var.set("")
            self.unknown_frame.pack_forget()
            self.hypothesis_frame.pack_forget()
            self.proposed_label.pack_forget()
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            self._refresh_answer_progress()
            return

        question = self._current_question()
        qtype = str(question.get("question_type", "unknown"))
        area = str(question.get("area", "-"))
        impact = str(question.get("impact_level", "-"))
        self.counter_var.set(f"Вопрос {self.index + 1} из {total}")
        qtype_ru = "Гипотеза" if qtype == "hypothesis" else "Unknown"
        self.meta_var.set(f"Тип: {qtype_ru} | Area: {area} | Impact: {impact}")

        if qtype == "hypothesis":
            hid = str(question.get("target_id", "")).strip()
            self.id_var.set(f"id: {hid}")
            self.question_var.set(str(question.get("question", "")).strip())
            claim = str(question.get("proposed_claim", "")).strip()
            self.proposed_var.set(f"Предложение сканера: {claim}" if claim else "")
            state = self.hypothesis_state.get(hid, {"decision": "confirm", "value": ""})
            self.h_decision_var.set(state.get("decision", "confirm"))
            self.h_text_var.set(state.get("value", ""))
            self.format_var.set(
                "Формат ответа: "
                + str(question.get("response_format", "confirm | edit:<new_text> | reject[:reason]"))
            )

            self.unknown_frame.pack_forget()
            self.proposed_label.pack(fill=tk.X, pady=(0, 6))
            self.hypothesis_frame.pack(fill=tk.X)
            self.decision_combo.focus_set()
        else:
            uid = str(question.get("unknown_id", "")).strip()
            self.id_var.set(f"id: {uid}")
            self.question_var.set(str(question.get("question", "")).strip())
            self.unknown_answer_var.set(self.unknown_state.get(uid, ""))
            self.format_var.set("Формат ответа: свободный текст")

            self.proposed_var.set("")
            self.proposed_label.pack_forget()
            self.hypothesis_frame.pack_forget()
            self.unknown_frame.pack(fill=tk.X)
            self.unknown_entry.focus_set()

        self.prev_button.config(state=tk.NORMAL if self.index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.index < total - 1 else tk.DISABLED)
        self._refresh_answer_progress()

    def _on_prev(self) -> None:
        if self.index <= 0:
            return
        self._save_current_answer()
        self.index -= 1
        self._render_current_question()

    def _on_next(self) -> None:
        if self.index >= len(self.questions) - 1:
            return
        self._save_current_answer()
        self.index += 1
        self._render_current_question()

    def _on_submit(self) -> None:
        self._save_current_answer()

        unknown_answers = dict(self.extra_unknown_answers)
        for uid, value in self.unknown_state.items():
            text = str(value).strip()
            if text:
                unknown_answers[uid] = text
            elif uid in unknown_answers:
                unknown_answers.pop(uid, None)

        hypothesis_answers: dict[str, Any] = dict(self.extra_hypothesis_answers)
        for hid, state in self.hypothesis_state.items():
            decision = str(state.get("decision", "confirm")).strip().lower()
            if decision not in {"confirm", "edit", "reject"}:
                decision = "confirm"
            hypothesis_answers[hid] = {
                "decision": decision,
                "value": str(state.get("value", "")).strip(),
            }

        self.result = {
            "unknown_answers": unknown_answers,
            "hypothesis_answers": hypothesis_answers,
        }
        self.window.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.window.destroy()


class PersonalMonitorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Operating-Pack Monitor")
        self.root.geometry("1260x820")
        self.root.minsize(1100, 700)

        self.repo_var = tk.StringVar()
        self.ref_var = tk.StringVar(value="HEAD")
        self.profile_var = tk.StringVar(value="balanced")
        self.answers_var = tk.StringVar()
        self.run_status_var = tk.StringVar(value="Готов к запуску")
        self.questionnaire_var = tk.StringVar(value="Опросник: -")
        self.progress_var = tk.IntVar(value=0)
        self.last_pack_dir: str = ""
        self.tree_paths: dict[str, Path] = {}

        self.summary_vars = {
            "run_id": tk.StringVar(value="-"),
            "quality_score": tk.StringVar(value="-"),
            "blocking_status": tk.StringVar(value="-"),
            "issues_count": tk.StringVar(value="-"),
            "critical_issues": tk.StringVar(value="-"),
            "unknown_open": tk.StringVar(value="-"),
        }

        self.stage_order = ["preparing_repo", "scanning", "awaiting_answers", "building_pack", "completed"]
        self.stage_titles = {
            "preparing_repo": "Клон",
            "scanning": "Скан",
            "awaiting_answers": "Опросник",
            "building_pack": "Сборка",
            "completed": "Итог",
        }
        self.stage_state: dict[str, str] = {stage: "pending" for stage in self.stage_order}
        self.stage_labels: dict[str, tk.Label] = {}

        self.colors = {
            "app_bg": "#0b1220",
            "panel_bg": "#111a2b",
            "panel_border": "#1a2740",
            "text": "#e6edf3",
            "muted": "#9ba9bc",
            "input_bg": "#0f1727",
            "button_bg": "#1b2a44",
            "button_fg": "#dce9ff",
            "progress_trough": "#1a2233",
            "progress_fill": "#2f81f7",
            "chip_pending_bg": "#182238",
            "chip_pending_fg": "#9ba9bc",
            "chip_running_bg": "#143a66",
            "chip_running_fg": "#d6ebff",
            "chip_done_bg": "#1f5a36",
            "chip_done_fg": "#d4ffe7",
            "chip_failed_bg": "#6a1d2a",
            "chip_failed_fg": "#ffd8dd",
            "chip_blocked_bg": "#5f4317",
            "chip_blocked_fg": "#ffe7bf",
            "log_bg": "#0a101c",
            "log_fg": "#d3deee",
        }

        default_answers = Path.cwd() / "examples" / "answers.sample.json"
        if default_answers.exists():
            self.answers_var.set(str(default_answers))

        self._configure_theme()
        self._build_layout()
        self._bind_clipboard_shortcuts()
        self._load_pilot_list()
        self._reset_progress_ui()

    def _bind_clipboard_shortcuts(self) -> None:
        # Explicit clipboard shortcuts improve reliability across keyboard layouts on Windows.
        for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>", "<Control-Insert>"):
            self.root.bind_all(sequence, self._on_paste_shortcut, add="+")
        self.root.bind_all("<Control-KeyPress>", self._on_control_keypress, add="+")

    def _on_control_keypress(self, event: tk.Event) -> str | None:
        # VK_V keycode fallback for non-Latin layouts where <Control-v> may not fire.
        if int(getattr(event, "keycode", 0)) == 86:
            return self._on_paste_shortcut(event)
        return None

    def _resolve_input_widget(self, event: tk.Event | None = None) -> Any:
        widget = getattr(event, "widget", None) if event is not None else None
        if widget is None:
            widget = self.root.focus_get()
        if widget is None:
            return None
        return widget

    def _insert_clipboard_text(self, widget: Any) -> bool:
        if widget is None:
            return False
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return False
        if not text:
            return False

        if isinstance(widget, ttk.Combobox):
            state = str(widget.cget("state")).strip().lower()
            if state == "readonly":
                return False

        if isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
            try:
                if widget.selection_present():
                    widget.delete("sel.first", "sel.last")
            except Exception:
                pass
            widget.insert(tk.INSERT, text)
            return True

        if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
            try:
                widget.delete("sel.first", "sel.last")
            except Exception:
                pass
            widget.insert(tk.INSERT, text)
            return True

        return False

    def _on_paste_shortcut(self, event: tk.Event | None = None) -> str | None:
        widget = self._resolve_input_widget(event)
        if self._insert_clipboard_text(widget):
            return "break"
        return None

    def _paste_repo_from_clipboard(self) -> None:
        if self._insert_clipboard_text(getattr(self, "repo_entry", None)):
            self.repo_entry.focus_set()

    def _configure_theme(self) -> None:
        self.root.configure(bg=self.colors["app_bg"])
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("App.TFrame", background=self.colors["app_bg"])
        style.configure("Panel.TFrame", background=self.colors["panel_bg"], borderwidth=1, relief="solid")
        style.configure("Title.TLabel", background=self.colors["app_bg"], foreground=self.colors["text"], font=("Segoe UI", 18, "bold"))
        style.configure("SubTitle.TLabel", background=self.colors["app_bg"], foreground=self.colors["muted"], font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=self.colors["panel_bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("PanelMuted.TLabel", background=self.colors["panel_bg"], foreground=self.colors["muted"], font=("Segoe UI", 9))
        style.configure("Accent.TButton", background=self.colors["button_bg"], foreground=self.colors["button_fg"], borderwidth=1, focusthickness=0, focuscolor=self.colors["button_bg"], padding=(10, 6))
        style.map("Accent.TButton", background=[("active", "#27406b"), ("disabled", "#1a2438")], foreground=[("disabled", "#7586a1")])
        style.configure("Dark.Horizontal.TProgressbar", troughcolor=self.colors["progress_trough"], bordercolor=self.colors["progress_trough"], lightcolor=self.colors["progress_fill"], darkcolor=self.colors["progress_fill"], background=self.colors["progress_fill"])
        style.configure("TEntry", fieldbackground=self.colors["input_bg"], foreground=self.colors["text"], bordercolor=self.colors["panel_border"], lightcolor=self.colors["panel_border"], darkcolor=self.colors["panel_border"], insertcolor=self.colors["text"])
        style.configure("TCombobox", fieldbackground=self.colors["input_bg"], background=self.colors["input_bg"], foreground=self.colors["text"], bordercolor=self.colors["panel_border"], arrowsize=13)
        style.map("TCombobox", fieldbackground=[("readonly", self.colors["input_bg"])], foreground=[("readonly", self.colors["text"])], selectbackground=[("readonly", "#2a3b5a")], selectforeground=[("readonly", self.colors["text"])])

    def _build_layout(self) -> None:
        app = ttk.Frame(self.root, style="App.TFrame", padding=14)
        app.pack(fill=tk.BOTH, expand=True)

        ttk.Label(app, text="Operating-Pack Monitor", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(app, text="Темный режим | URL -> скан -> опросник -> сборка -> результат", style="SubTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(2, 12))

        form = ttk.Frame(app, style="Panel.TFrame", padding=12)
        form.grid(row=2, column=0, sticky="ew")

        ttk.Label(form, text="Пилотные репозитории", style="Panel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.pilot_combo = ttk.Combobox(form, state="readonly")
        self.pilot_combo.grid(row=0, column=1, columnspan=5, sticky="ew", pady=(0, 6))
        self.pilot_combo.bind("<<ComboboxSelected>>", self._on_pilot_select)

        ttk.Label(form, text="Ссылка на репозиторий", style="Panel.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.repo_entry = ttk.Entry(form, textvariable=self.repo_var)
        self.repo_entry.grid(row=1, column=1, columnspan=4, sticky="ew", pady=(0, 6))
        ttk.Button(form, text="Вставить", style="Accent.TButton", command=self._paste_repo_from_clipboard).grid(
            row=1, column=5, sticky="w", pady=(0, 6), padx=(6, 0)
        )

        ttk.Label(form, text="Git ref", style="Panel.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=self.ref_var, width=20).grid(row=2, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Профиль", style="Panel.TLabel").grid(row=2, column=2, sticky="e", pady=(0, 6))
        ttk.Combobox(form, state="readonly", textvariable=self.profile_var, values=["quick", "balanced", "strict"], width=12).grid(row=2, column=3, sticky="w", pady=(0, 6), padx=(6, 0))

        ttk.Label(form, text="Файл ответов", style="Panel.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=self.answers_var).grid(row=3, column=1, columnspan=4, sticky="ew", pady=(0, 6))
        ttk.Button(form, text="Выбрать", style="Accent.TButton", command=self._browse_answers_file).grid(row=3, column=5, sticky="w", pady=(0, 6), padx=(6, 0))

        button_row = ttk.Frame(form, style="Panel.TFrame")
        button_row.grid(row=4, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        self.run_button = ttk.Button(button_row, text="Запустить проверку", style="Accent.TButton", command=self._start_run)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(button_row, text="Открыть папку pack", style="Accent.TButton", command=self._open_pack_folder).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_row, text="Очистить вывод", style="Accent.TButton", command=self._clear_output).pack(side=tk.LEFT, padx=(8, 0))

        progress_panel = ttk.Frame(app, style="Panel.TFrame", padding=12)
        progress_panel.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(progress_panel, textvariable=self.run_status_var, style="Panel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(progress_panel, textvariable=self.questionnaire_var, style="PanelMuted.TLabel").grid(row=0, column=1, sticky="e")
        self.progress = ttk.Progressbar(progress_panel, orient="horizontal", mode="determinate", maximum=100, variable=self.progress_var, style="Dark.Horizontal.TProgressbar")
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 10))

        chip_host = tk.Frame(progress_panel, bg=self.colors["panel_bg"])
        chip_host.grid(row=2, column=0, columnspan=2, sticky="ew")
        for idx, stage_id in enumerate(self.stage_order):
            label = tk.Label(chip_host, text="", bg=self.colors["chip_pending_bg"], fg=self.colors["chip_pending_fg"], font=("Segoe UI", 9, "bold"), padx=10, pady=6, bd=0)
            label.grid(row=0, column=idx, padx=(0 if idx == 0 else 8, 0), sticky="ew")
            self.stage_labels[stage_id] = label
            chip_host.grid_columnconfigure(idx, weight=1)

        self.tabs = ttk.Notebook(app)
        self.tabs.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

        self.log_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.result_tab = ttk.Frame(self.tabs, style="Panel.TFrame")
        self.tabs.add(self.log_tab, text="Лог")
        self.tabs.add(self.result_tab, text="Результат")

        self.output = scrolledtext.ScrolledText(self.log_tab, wrap=tk.WORD, height=22, bg=self.colors["log_bg"], fg=self.colors["log_fg"], insertbackground=self.colors["log_fg"], relief=tk.FLAT, borderwidth=0, padx=8, pady=8, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        summary = ttk.Frame(self.result_tab, style="Panel.TFrame", padding=10)
        summary.pack(fill=tk.X)
        fields = [
            ("Run ID", "run_id"),
            ("Quality", "quality_score"),
            ("Blocking", "blocking_status"),
            ("Issues", "issues_count"),
            ("Critical", "critical_issues"),
            ("Unknown Open", "unknown_open"),
        ]
        for idx, (label_text, key) in enumerate(fields):
            row = idx // 3
            col = (idx % 3) * 2
            ttk.Label(summary, text=label_text, style="PanelMuted.TLabel").grid(row=row, column=col, sticky="w", padx=(0, 6), pady=(0, 4))
            ttk.Label(summary, textvariable=self.summary_vars[key], style="Panel.TLabel").grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=(0, 4))
        for c in range(6):
            summary.columnconfigure(c, weight=1 if c % 2 == 1 else 0)

        viewer_host = ttk.Frame(self.result_tab, style="Panel.TFrame", padding=(10, 0, 10, 10))
        viewer_host.pack(fill=tk.BOTH, expand=True)

        viewer_split = ttk.Panedwindow(viewer_host, orient=tk.HORIZONTAL)
        viewer_split.pack(fill=tk.BOTH, expand=True)

        tree_frame = ttk.Frame(viewer_split, style="Panel.TFrame")
        preview_frame = ttk.Frame(viewer_split, style="Panel.TFrame")
        viewer_split.add(tree_frame, weight=1)
        viewer_split.add(preview_frame, weight=3)

        self.pack_tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse")
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.pack_tree.yview)
        self.pack_tree.configure(yscrollcommand=tree_scroll.set)
        self.pack_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.pack_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        self.file_preview = scrolledtext.ScrolledText(preview_frame, wrap=tk.NONE, bg=self.colors["log_bg"], fg=self.colors["text"], insertbackground=self.colors["text"], relief=tk.FLAT, borderwidth=0, padx=8, pady=8, font=("Consolas", 10))
        self.file_preview.pack(fill=tk.BOTH, expand=True)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=0)
        form.columnconfigure(3, weight=0)
        form.columnconfigure(4, weight=1)
        form.columnconfigure(5, weight=0)
        progress_panel.columnconfigure(0, weight=1)
        progress_panel.columnconfigure(1, weight=1)
        app.columnconfigure(0, weight=1)
        app.rowconfigure(4, weight=1)
        self.log_tab.columnconfigure(0, weight=1)
        self.log_tab.rowconfigure(0, weight=1)
        self.result_tab.columnconfigure(0, weight=1)
        self.result_tab.rowconfigure(1, weight=1)

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
        path = filedialog.askopenfilename(title="Выбор JSON с ответами", filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")])
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

    def _stage_palette(self, status: str) -> tuple[str, str]:
        if status == "running":
            return self.colors["chip_running_bg"], self.colors["chip_running_fg"]
        if status == "done":
            return self.colors["chip_done_bg"], self.colors["chip_done_fg"]
        if status == "failed":
            return self.colors["chip_failed_bg"], self.colors["chip_failed_fg"]
        if status == "blocked":
            return self.colors["chip_blocked_bg"], self.colors["chip_blocked_fg"]
        return self.colors["chip_pending_bg"], self.colors["chip_pending_fg"]

    def _stage_suffix(self, status: str) -> str:
        return {
            "pending": "ожидает",
            "running": "в процессе",
            "done": "готово",
            "failed": "ошибка",
            "blocked": "блок",
        }.get(status, status)

    def _render_stage_chip(self, stage_id: str) -> None:
        status = self.stage_state.get(stage_id, "pending")
        bg, fg = self._stage_palette(status)
        self.stage_labels[stage_id].configure(text=f"{self.stage_titles.get(stage_id, stage_id)}: {self._stage_suffix(status)}", bg=bg, fg=fg)

    def _set_stage_state(self, stage_id: str, status: str) -> None:
        if stage_id in self.stage_state:
            self.stage_state[stage_id] = status
            self._render_stage_chip(stage_id)

    def _mark_previous_done(self, stage_id: str) -> None:
        if stage_id in self.stage_order:
            target_index = self.stage_order.index(stage_id)
            for idx in range(target_index):
                item = self.stage_order[idx]
                if self.stage_state[item] in {"pending", "running"}:
                    self._set_stage_state(item, "done")

    def _reset_progress_ui(self) -> None:
        self.progress_var.set(0)
        self.run_status_var.set("Готов к запуску")
        self.questionnaire_var.set("Опросник: -")
        for stage_id in self.stage_order:
            self._set_stage_state(stage_id, "pending")

    def _apply_stage_event(self, event: MonitorStageEvent) -> None:
        self.progress_var.set(max(0, min(100, int(event.percent))))
        self.run_status_var.set(f"[{event.stage_id}] {event.message}")

        stage_id = str(event.stage_id)
        state = str(event.state)
        msg = str(event.message).lower()

        if stage_id in self.stage_order:
            self._mark_previous_done(stage_id)
            if state == "failed":
                self._set_stage_state(stage_id, "failed")
            elif stage_id == "completed":
                self._set_stage_state(stage_id, "blocked" if state == "completed_blocked" else "done")
            elif stage_id == "preparing_repo" and "completed" in msg:
                self._set_stage_state(stage_id, "done")
            else:
                self._set_stage_state(stage_id, "running")

        self._append(f"[stage={event.stage_id}] state={event.state} progress={event.percent}% message={event.message}\n")

    def _clear_result_panel(self) -> None:
        for value in self.summary_vars.values():
            value.set("-")
        self.pack_tree.delete(*self.pack_tree.get_children())
        self.file_preview.delete("1.0", tk.END)
        self.tree_paths.clear()

    def _set_result_summary(self, result: MonitorCheckResult) -> None:
        self.summary_vars["run_id"].set(result.run_id)
        self.summary_vars["quality_score"].set(f"{result.quality_score:.3f}")
        self.summary_vars["blocking_status"].set("yes" if result.blocking_status else "no")
        self.summary_vars["issues_count"].set(str(result.issues_count))
        self.summary_vars["critical_issues"].set(str(result.critical_issues))
        self.summary_vars["unknown_open"].set(str(result.open_unknown_count))

    def _load_pack_tree(self, pack_dir: Path) -> None:
        self.pack_tree.delete(*self.pack_tree.get_children())
        self.tree_paths.clear()

        if not pack_dir.exists():
            return

        root_id = self.pack_tree.insert("", "end", text=pack_dir.name, open=True)
        self.tree_paths[root_id] = pack_dir

        def add_children(parent_id: str, directory: Path) -> None:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            for entry in entries:
                child_id = self.pack_tree.insert(parent_id, "end", text=entry.name, open=False)
                self.tree_paths[child_id] = entry
                if entry.is_dir():
                    add_children(child_id, entry)

        add_children(root_id, pack_dir)

    def _on_tree_select(self, _event: object) -> None:
        selected = self.pack_tree.selection()
        if not selected:
            return
        path = self.tree_paths.get(selected[0])
        if path is None or path.is_dir():
            return

        try:
            content = render_preview_content(path)
        except Exception as exc:
            content = f"[ОШИБКА ЧТЕНИЯ] {exc}"

        self.file_preview.delete("1.0", tk.END)
        self.file_preview.insert("1.0", content)
        self.tabs.select(self.result_tab)

    def _start_run(self) -> None:
        repo_url = self.repo_var.get().strip()
        is_valid_repo_url, repo_error = validate_repo_url(repo_url)
        if not is_valid_repo_url:
            messagebox.showerror("Монитор", repo_error)
            return

        answers_path = self.answers_var.get().strip()
        answers_payload: dict[str, Any] = {}
        if answers_path:
            try:
                answers_payload = load_answers_payload(Path(answers_path))
            except Exception as exc:
                messagebox.showerror("Монитор", f"Не удалось загрузить файл ответов:\n{exc}")
                return

        self.run_button.config(state=tk.DISABLED)
        self._reset_progress_ui()
        self._clear_result_panel()
        self._append("\n=== СТАРТ ПРОГОНА ===\n")
        self._append(f"repo={repo_url}\n")
        self._append(f"profile={self.profile_var.get()}\n")

        thread = threading.Thread(
            target=self._run_worker,
            args=(repo_url, self.ref_var.get().strip(), self.profile_var.get(), answers_payload),
            daemon=True,
        )
        thread.start()

    def _request_questionnaire_answers(
        self,
        questions: list[dict[str, Any]],
        seed_answers: dict[str, Any],
    ) -> dict[str, Any] | None:
        wait_event = threading.Event()
        holder: dict[str, Any] = {"answers": None}

        def _open_dialog() -> None:
            try:
                self.run_status_var.set("Ожидание ответов в окне опросника")
                dialog = QuestionnaireDialog(
                    parent=self.root,
                    questions=questions,
                    seed_answers=seed_answers,
                    colors=self.colors,
                )
                self.root.wait_window(dialog.window)
                holder["answers"] = dialog.result
            finally:
                wait_event.set()

        self.root.after(0, _open_dialog)
        wait_event.wait()

        answers = holder.get("answers")
        if isinstance(answers, dict):
            return answers
        return None

    def _run_worker(self, repo_url: str, git_ref: str, profile: str, answers_payload: dict[str, Any]) -> None:
        def _progress(event: MonitorStageEvent) -> None:
            self.root.after(0, lambda e=event: self._apply_stage_event(e))

        try:
            session = start_remote_repo_session(
                repo_url=repo_url,
                workspace_root=Path.cwd() / ".monitor",
                profile=profile,
                git_ref=git_ref or "HEAD",
                progress_callback=_progress,
            )
            self.root.after(
                0,
                lambda s=session: self.questionnaire_var.set(
                    f"Опросник: всего {len(s.questions)} | unknown {s.unknown_questions} | hypothesis {s.hypothesis_questions}"
                ),
            )

            final_answers = deepcopy(answers_payload) if isinstance(answers_payload, dict) else {}
            if session.questions:
                self.root.after(0, lambda: self._append("[опросник] Открылось окно вопросов (по одному).\n"))
                collected = self._request_questionnaire_answers(session.questions, final_answers)
                if collected is None:
                    discard_session(session.run_id)
                    self.root.after(0, lambda run_id=session.run_id: self._on_run_cancelled(run_id))
                    return
                final_answers = collected
            else:
                self.root.after(0, lambda: self.questionnaire_var.set("Опросник: вопросов нет"))

            result = submit_session_answers(
                run_id=session.run_id,
                answers_payload=final_answers,
                progress_callback=_progress,
                close_session=True,
            )
            self.root.after(0, lambda r=result: self._on_run_success(r))
        except Exception as exc:
            self.root.after(0, lambda: self._on_run_error(exc))

    def _on_run_success(self, result: MonitorCheckResult) -> None:
        self.last_pack_dir = result.pack_dir
        self._set_stage_state("completed", "blocked" if result.blocking_status else "done")
        self.run_status_var.set(
            "Прогон завершен с блокирующими замечаниями"
            if result.blocking_status
            else "Прогон успешно завершен"
        )
        self._set_result_summary(result)
        self._load_pack_tree(Path(result.pack_dir))
        self.tabs.select(self.result_tab)
        self._append(self._render_result(result))
        if result.blocking_status:
            self._append("[ПОДСКАЗКА] Есть блокирующие замечания: открой VALIDATION_REPORT.json в дереве результатов.\n")
        self._append("=== КОНЕЦ ПРОГОНА ===\n")
        self.run_button.config(state=tk.NORMAL)

    def _on_run_cancelled(self, run_id: str) -> None:
        self._set_stage_state("awaiting_answers", "failed")
        self.progress_var.set(max(self.progress_var.get(), 60))
        self.run_status_var.set("Прогон отменен на этапе опросника")
        self._append(f"[INFO] Прогон {run_id} отменен пользователем.\n")
        self._append("=== КОНЕЦ ПРОГОНА ===\n")
        self.run_button.config(state=tk.NORMAL)

    def _on_run_error(self, exc: Exception) -> None:
        self._append(f"[ОШИБКА] {exc}\n")
        hint = build_runtime_error_hint(str(exc))
        if hint:
            self._append(f"[ПОДСКАЗКА] {hint}\n")
        self._set_stage_state("completed", "failed")
        self.progress_var.set(100)
        self.run_status_var.set("Прогон завершился с ошибкой")
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
