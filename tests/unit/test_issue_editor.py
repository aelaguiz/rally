from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from rally.services.issue_editor import (
    IssueEditorResult,
    clean_issue_editor_text,
    edit_issue_file_in_editor,
    resolve_interactive_issue_editor,
)


class IssueEditorTests(unittest.TestCase):
    def test_resolve_interactive_issue_editor_prefers_visual(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_dir = Path(temp_dir).resolve()
            for name in ("nvim", "nano"):
                tool_path = bin_dir / name
                tool_path.write_text("#!/bin/sh\n", encoding="utf-8")
                tool_path.chmod(0o755)

            command = resolve_interactive_issue_editor(
                stdin=_TtyStream(),
                stdout=_TtyStream(),
                environ={
                    "VISUAL": "nvim -f",
                    "EDITOR": "nano",
                    "PATH": str(bin_dir),
                },
            )

        self.assertEqual(command, ("nvim", "-f"))

    def test_resolve_interactive_issue_editor_falls_back_to_vim_then_vi(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_dir = Path(temp_dir).resolve()
            vim_path = bin_dir / "vim"
            vim_path.write_text("#!/bin/sh\n", encoding="utf-8")
            vim_path.chmod(0o755)

            command = resolve_interactive_issue_editor(
                stdin=_TtyStream(),
                stdout=_TtyStream(),
                environ={"PATH": str(bin_dir)},
            )

        self.assertEqual(command, ("vim",))

    def test_edit_issue_file_in_editor_strips_prompt_block_before_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            issue_path = Path(temp_dir).resolve() / "issue.md"

            def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                temp_file = Path(command[-1])
                temp_file.write_text(
                    temp_file.read_text(encoding="utf-8") + "\n\nFix the pagination bug.\n",
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(args=command, returncode=0)

            result = edit_issue_file_in_editor(
                issue_path=issue_path,
                editor_command=("vim",),
                run=fake_run,
            )

            self.assertEqual(
                result,
                IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n", reason=None),
            )
            self.assertEqual(issue_path.read_text(encoding="utf-8"), "Fix the pagination bug.\n")

    def test_clean_issue_editor_text_leaves_user_text_alone_without_prompt_block(self) -> None:
        self.assertEqual(clean_issue_editor_text("Write a sonnet.\n"), "Write a sonnet.\n")


class _TtyStream:
    def isatty(self) -> bool:
        return True


if __name__ == "__main__":
    unittest.main()
