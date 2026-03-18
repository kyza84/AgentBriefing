import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opack.monitor.ui import (
    build_questionnaire_seed_payload,
    build_runtime_error_hint,
    parse_hypothesis_answer,
    render_preview_content,
    validate_repo_url,
)


class MonitorUiHelpersTest(unittest.TestCase):
    def test_build_questionnaire_seed_payload_adds_missing_question_keys(self) -> None:
        questions = [
            {"question_type": "unknown", "unknown_id": "u_entry"},
            {"question_type": "hypothesis", "target_id": "h_entry"},
        ]
        payload = build_questionnaire_seed_payload(questions=questions, seed_answers={})
        self.assertIn("u_entry", payload["unknown_answers"])
        self.assertEqual(payload["hypothesis_answers"].get("h_entry"), "confirm")

    def test_build_questionnaire_seed_payload_keeps_existing_answers(self) -> None:
        questions = [
            {"question_type": "unknown", "unknown_id": "u_entry"},
            {"question_type": "hypothesis", "target_id": "h_entry"},
        ]
        seed = {
            "unknown_answers": {"u_entry": "main.py"},
            "hypothesis_answers": {"h_entry": "edit:src/main.py"},
        }
        payload = build_questionnaire_seed_payload(questions=questions, seed_answers=seed)
        self.assertEqual(payload["unknown_answers"].get("u_entry"), "main.py")
        self.assertEqual(payload["hypothesis_answers"].get("h_entry"), "edit:src/main.py")

    def test_parse_hypothesis_answer_string_variants(self) -> None:
        self.assertEqual(
            parse_hypothesis_answer("confirm"),
            {"decision": "confirm", "value": ""},
        )
        self.assertEqual(
            parse_hypothesis_answer("edit:main.py"),
            {"decision": "edit", "value": "main.py"},
        )
        self.assertEqual(
            parse_hypothesis_answer("reject:not canonical"),
            {"decision": "reject", "value": "not canonical"},
        )

    def test_parse_hypothesis_answer_dict_variant(self) -> None:
        self.assertEqual(
            parse_hypothesis_answer({"decision": "edit", "value": "src/main.py"}),
            {"decision": "edit", "value": "src/main.py"},
        )

    def test_validate_repo_url_accepts_valid_github_urls(self) -> None:
        ok1, _ = validate_repo_url("https://github.com/pallets/flask")
        ok2, _ = validate_repo_url("https://github.com/pallets/flask.git")
        ok3, _ = validate_repo_url("https://github.com/vercel/next.js/")
        self.assertTrue(ok1)
        self.assertTrue(ok2)
        self.assertTrue(ok3)

    def test_validate_repo_url_rejects_invalid_urls(self) -> None:
        invalid_samples = [
            "",
            "github.com/pallets/flask",
            "http://github.com/pallets/flask",
            "https://github.com/pallets",
            "https://gitlab.com/pallets/flask",
        ]
        for sample in invalid_samples:
            with self.subTest(sample=sample):
                ok, message = validate_repo_url(sample)
                self.assertFalse(ok)
                self.assertTrue(message)

    def test_build_runtime_error_hint_known_patterns(self) -> None:
        self.assertIn("long paths", build_runtime_error_hint("fatal: Filename too long"))
        self.assertIn(
            "проверь URL",
            build_runtime_error_hint("Failed to clone repository: auth failed"),
        )
        self.assertIn(
            "сессия устарела",
            build_runtime_error_hint("Session not found: test"),
        )
        self.assertIn(
            "формата ответа",
            build_runtime_error_hint("JSON decode error"),
        )

    def test_render_preview_content_binary_and_truncated(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            binary_file = base / "bin.dat"
            binary_file.write_bytes(b"\x00\x01\x02\x03")
            text_file = base / "large.txt"
            text_file.write_text("a" * 128, encoding="utf-8")

            binary_preview = render_preview_content(binary_file)
            text_preview = render_preview_content(text_file, max_bytes=32)

            self.assertIn("[BINARY FILE]", binary_preview)
            self.assertIn("[TRUNCATED]", text_preview)


if __name__ == "__main__":
    unittest.main()
