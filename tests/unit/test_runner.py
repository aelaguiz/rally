from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rally.domain.run import ResumeRequest, RunRequest, RunStatus
from rally.errors import RallyConfigError, RallyUsageError
from rally.services.issue_editor import IssueEditorResult
from rally.services.run_store import archive_run, find_run_dir, load_run_state, write_run_state
from rally.services.runner import resume_run, run_flow


class RunnerTests(unittest.TestCase):
    def test_run_flow_creates_pending_run_until_issue_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun([])

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=None,
            ):
                with self.assertRaisesRegex(RallyUsageError, "waiting for `.*issue.md`"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo"),
                        subprocess_run=fake_run,
                    )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            state = load_run_state(run_dir=run_dir)
            run_yaml_text = (run_dir / "run.yaml").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(state.status, RunStatus.PENDING)
            self.assertEqual(state.turn_index, 0)
            self.assertFalse(fake_run.calls)
            self.assertFalse((run_dir / "home" / "issue.md").exists())
            self.assertNotIn("brief_file", run_yaml_text)
            self.assertIn("Prepared run home shell", rendered_text)
            self.assertIn("waiting for `home/issue.md`", rendered_text)

    def test_resume_run_after_issue_exists_hands_off_and_records_logs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "stdout_lines": [
                            {"type": "thread.started", "thread_id": "session-1"},
                            {"type": "assistant.message.delta", "delta": "Investigating the bug\n"},
                            {"type": "reasoning.delta", "delta": "Tracing the pagination path\n"},
                            {"type": "tool.call.started", "tool_name": "shell", "command": 'rg -n "page" src'},
                            {"type": "tool.call.completed", "tool_name": "shell", "message": "12 matches"},
                            {
                                "type": "turn.completed",
                                "usage": {
                                    "input_tokens": 1,
                                    "cached_input_tokens": 0,
                                    "output_tokens": 1,
                                },
                            },
                        ],
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            session_text = (run_dir / "home" / "sessions" / "scope_lead" / "session.yaml").read_text(
                encoding="utf-8"
            )
            events_text = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            agent_log_text = (run_dir / "logs" / "agents" / "scope_lead.jsonl").read_text(encoding="utf-8")
            launch_record = json.loads(
                (run_dir / "logs" / "adapter_launch" / "turn-001-scope_lead.json").read_text(encoding="utf-8")
            )

            self.assertEqual(result.run_id, "DMO-1")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertIsNone(state.current_agent_key)
            self.assertEqual(state.turn_index, 2)
            self.assertFalse((run_dir / "home" / "operator_brief.md").exists())
            self.assertIn("Fix the pagination bug.", issue_text)
            self.assertIn("Rally Run Started", issue_text)
            self.assertIn("Rally Turn Result", issue_text)
            self.assertIn("Rally Done", issue_text)
            self.assertIn("session-1", session_text)
            self.assertIn('"code": "RUN"', events_text)
            self.assertIn('"code": "SESSION"', agent_log_text)
            self.assertIn("Investigating the bug", rendered_text)
            self.assertIn("Tracing the pagination path", rendered_text)
            self.assertIn('rg -n "page" src', rendered_text)
            self.assertIn("Handed off", rendered_text)
            self.assertIn("is done: verified", rendered_text)
            self.assertEqual(launch_record["env"]["RALLY_AGENT_SLUG"], "scope_lead")
            self.assertIn("--output-schema", fake_run.calls[0]["command"])
            self.assertIn("-C", fake_run.calls[0]["command"])
            self.assertIn(
                "--dangerously-bypass-approvals-and-sandbox",
                fake_run.calls[0]["command"],
            )

    def test_poem_loop_prompt_includes_kernel_skill_and_writer_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_poem_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-poem-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "poem_critic",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-poem-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "accepted",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Write a sonnet about the moon.\n", encoding="utf-8")
                return IssueEditorResult(
                    status="saved",
                    cleaned_text="Write a sonnet about the moon.\n",
                )

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="poem_loop"),
                    subprocess_run=fake_run,
                )

            run_dir = find_run_dir(repo_root=repo_root, run_id="POM-1")
            prompt_text = fake_run.calls[0]["kwargs"]["input"]

            self.assertEqual(result.run_id, "POM-1")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertIn("## Skills", prompt_text)
            self.assertIn("### rally-kernel", prompt_text)
            self.assertIn("Use the shared `rally-kernel` skill for that note.", prompt_text)
            self.assertIn('Append With: `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"`', prompt_text)
            self.assertIn("Artistic Rationale", prompt_text)

    def test_resume_run_uses_saved_session_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "scope_lead",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(state.status, RunStatus.DONE)
            self.assertEqual(len(fake_run.calls), 3)
            self.assertIn("resume", fake_run.calls[2]["command"])
            self.assertIn("session-1", fake_run.calls[2]["command"])

    def test_resume_run_blocks_sleep_turn_result_and_records_why(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "sleep",
                            "next_owner": None,
                            "summary": None,
                            "reason": "wait for CI",
                            "sleep_duration_seconds": 60,
                        },
                    }
                ]
            )

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.BLOCKED)
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertEqual(state.last_turn_kind, "sleep")
            self.assertIn("Sleep turn results are not supported", state.blocker_reason or "")
            self.assertIn("Rally Turn Result", issue_text)
            self.assertIn("Rally Blocked", issue_text)
            self.assertNotIn("Rally Sleeping", issue_text)
            self.assertIn("SLEEP", rendered_text)
            self.assertIn("BLOCKED", rendered_text)

    def test_resume_run_rejects_blank_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="   \n")

            with self.assertRaisesRegex(RallyUsageError, "non-empty issue"):
                resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=_FakeCodexRun([]),
                )

            state = load_run_state(run_dir=run_dir)
            self.assertEqual(state.status, RunStatus.PENDING)

    def test_resume_run_rejects_archived_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            archive_run(repo_root=repo_root, run_id="DMO-1")

            with self.assertRaisesRegex(RallyUsageError, "archived and cannot be resumed"):
                resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=_FakeCodexRun([]),
                )

    def test_resume_run_with_edit_updates_existing_issue_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "updated",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Old issue.\n")

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("New issue text.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="New issue text.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=fake_run,
                )

            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertTrue(issue_text.startswith("New issue text.\n"))
            self.assertIn("## user edited issue.md", issue_text)
            self.assertIn("```diff\n--- before/issue.md\n+++ after/issue.md\n", issue_text)
            self.assertIn("-Old issue.\n+New issue text.\n", issue_text)
            self.assertIn("Rally Run Started", issue_text)
            self.assertTrue(fake_run.calls)
            self.assertIn("Opening editor for `home/issue.md`", rendered_text)
            self.assertIn("Saved issue from editor", rendered_text)

    def test_resume_run_with_edit_retries_blocked_run_after_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "approved",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Write about space whales.\n")
            blocked_state = replace(
                load_run_state(run_dir=run_dir),
                status=RunStatus.BLOCKED,
                blocker_reason="Need the poem type.",
            )
            write_run_state(run_dir=run_dir, state=blocked_state)

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Write a sonnet about space whales.\n", encoding="utf-8")
                return IssueEditorResult(
                    status="saved",
                    cleaned_text="Write a sonnet about space whales.\n",
                )

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=fake_run,
                )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertEqual(state.status, RunStatus.DONE)
            self.assertIsNone(state.blocker_reason)
            self.assertTrue(issue_text.startswith("Write a sonnet about space whales.\n"))
            self.assertIn("## user edited issue.md", issue_text)
            self.assertIn("-Write about space whales.\n+Write a sonnet about space whales.\n", issue_text)
            self.assertTrue(fake_run.calls)
            self.assertIn("Opening editor for `home/issue.md`", rendered_text)
            self.assertIn("Saved issue from editor", rendered_text)

    def test_resume_run_with_edit_waits_when_issue_is_left_blank(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Write a sonnet.\n")
            fake_run = _FakeCodexRun([])

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("   \n", encoding="utf-8")
                return IssueEditorResult(status="cancelled", reason="blank_issue")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                with self.assertRaisesRegex(RallyUsageError, "non-empty issue"):
                    resume_run(
                        repo_root=repo_root,
                        request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                        subprocess_run=fake_run,
                    )

            state = load_run_state(run_dir=run_dir)
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(state.status, RunStatus.PENDING)
            self.assertFalse(fake_run.calls)
            self.assertNotIn("## user edited issue.md", (run_dir / "home" / "issue.md").read_text(encoding="utf-8"))
            self.assertIn("Editor closed without a non-empty issue", rendered_text)
            self.assertIn("WAITING", rendered_text)

    def test_resume_run_with_edit_still_refuses_done_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            done_state = replace(
                load_run_state(run_dir=run_dir),
                status=RunStatus.DONE,
                current_agent_key=None,
                current_agent_slug=None,
                done_summary="all set",
            )
            write_run_state(run_dir=run_dir, state=done_state)

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
            ) as resolve_editor_mock:
                with self.assertRaisesRegex(RallyUsageError, "already done"):
                    resume_run(
                        repo_root=repo_root,
                        request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                        subprocess_run=_FakeCodexRun([]),
                    )

            resolve_editor_mock.assert_not_called()

    def test_resume_run_with_edit_skips_diff_note_for_noop_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "kept",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Keep this issue.\n")

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Keep this issue.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Keep this issue.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=fake_run,
                )

            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertNotIn("## user edited issue.md", issue_text)

    def test_resume_run_with_edit_records_diff_when_issue_file_was_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "started",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )
            run_dir = self._create_pending_run(repo_root=repo_root)

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Start from scratch.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Start from scratch.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=fake_run,
                )

            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue(issue_text.startswith("Start from scratch.\n"))
            self.assertIn("## user edited issue.md", issue_text)
            self.assertIn("@@ -0,0 +1 @@", issue_text)
            self.assertIn("+Start from scratch.\n", issue_text)

    def test_run_flow_opens_editor_for_missing_issue_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "editor flow done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug from the editor.\n", encoding="utf-8")
                return IssueEditorResult(
                    status="saved",
                    cleaned_text="Fix the pagination bug from the editor.\n",
                )

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo"),
                    subprocess_run=fake_run,
                )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertTrue(issue_text.startswith("Fix the pagination bug from the editor.\n"))
            self.assertNotIn("RALLY_ISSUE_PROMPT_START", issue_text)
            self.assertIn("Rally Run Started", issue_text)
            self.assertTrue(fake_run.calls)
            self.assertIn("Opening editor for `home/issue.md`", rendered_text)
            self.assertIn("Saved issue from editor", rendered_text)

    def test_resume_run_opens_editor_for_blank_issue_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "resume editor done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="   \n")

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug after resume.\n", encoding="utf-8")
                return IssueEditorResult(
                    status="saved",
                    cleaned_text="Fix the pagination bug after resume.\n",
                )

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=fake_run,
                )

            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertTrue(issue_text.startswith("Fix the pagination bug after resume.\n"))
            self.assertIn("Rally Run Started", issue_text)
            self.assertTrue(fake_run.calls)
            self.assertIn("Opening editor for `home/issue.md`", rendered_text)
            self.assertIn("Saved issue from editor", rendered_text)

    def test_run_flow_waits_when_editor_does_not_save_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun([])

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                return_value=IssueEditorResult(status="cancelled", reason="blank_issue"),
            ):
                with self.assertRaisesRegex(RallyUsageError, "waiting for `.*issue.md`"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo"),
                        subprocess_run=fake_run,
                    )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            state = load_run_state(run_dir=run_dir)
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(state.status, RunStatus.PENDING)
            self.assertFalse(fake_run.calls)
            self.assertIn("Opening editor for `home/issue.md`", rendered_text)
            self.assertIn("Editor closed without a non-empty issue", rendered_text)
            self.assertIn("WAITING", rendered_text)

    def test_run_flow_new_archives_active_run_and_starts_fresh_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            old_run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=old_run_dir, body="Fix the old issue.\n")
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "thread_id": "session-3",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "fresh run done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Start the new issue.\n", encoding="utf-8")
                return IssueEditorResult(
                    status="saved",
                    cleaned_text="Start the new issue.\n",
                )

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=True,
            ), patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", start_new=True),
                    subprocess_run=fake_run,
                )

            archived_dir = repo_root / "runs" / "archive" / "DMO-1"
            new_run_dir = repo_root / "runs" / "active" / "DMO-2"
            archived_issue = (archived_dir / "home" / "issue.md").read_text(encoding="utf-8")
            archived_rendered = (archived_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            new_issue = (new_run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.run_id, "DMO-2")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertFalse((repo_root / "runs" / "active" / "DMO-1").exists())
            self.assertTrue(archived_dir.is_dir())
            self.assertTrue(new_run_dir.is_dir())
            self.assertIn("Fix the old issue.", archived_issue)
            self.assertIn("Rally Archived", archived_issue)
            self.assertIn("Starting a fresh `demo` run", archived_issue)
            self.assertIn("ARCHIVE", archived_rendered)
            self.assertTrue(new_issue.startswith("Start the new issue.\n"))
            self.assertTrue(fake_run.calls)

    def test_run_flow_new_cancels_when_replacement_not_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._create_pending_run(repo_root=repo_root)
            fake_run = _FakeCodexRun([])

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=False,
            ):
                with self.assertRaisesRegex(RallyUsageError, "Cancelled starting a new `demo` run"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo", start_new=True),
                        subprocess_run=fake_run,
                    )

            self.assertTrue((repo_root / "runs" / "active" / "DMO-1").is_dir())
            self.assertFalse((repo_root / "runs" / "active" / "DMO-2").exists())
            self.assertFalse((repo_root / "runs" / "archive" / "DMO-1").exists())
            self.assertFalse(fake_run.calls)

    def test_run_flow_new_requires_interactive_tty_to_confirm_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._create_pending_run(repo_root=repo_root)

            with patch("sys.stdin", io.StringIO("y\n")), patch("sys.stdout", io.StringIO()):
                with self.assertRaisesRegex(RallyUsageError, "needs an interactive TTY to confirm archiving"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo", start_new=True),
                        subprocess_run=_FakeCodexRun([]),
                    )

    def test_run_flow_does_not_run_setup_before_issue_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, with_setup_script=True)
            run_dir = self._create_pending_run(repo_root=repo_root)

            self.assertFalse((run_dir / "home" / "setup-ok.txt").exists())

            self._write_issue(run_dir=run_dir)
            resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=_FakeCodexRun(
                    [
                        {
                            "thread_id": "session-1",
                            "last_message": {
                                "kind": "done",
                                "next_owner": None,
                                "summary": "verified",
                                "reason": None,
                                "sleep_duration_seconds": None,
                            },
                        }
                    ]
                ),
            )

            self.assertTrue((run_dir / "home" / "setup-ok.txt").is_file())

    def test_run_flow_rejects_skill_without_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            (repo_root / "skills" / "repo-search" / "SKILL.md").write_text(
                "# Repo Search\n",
                encoding="utf-8",
            )

            with self.assertRaises(RallyConfigError):
                resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=_FakeCodexRun([]),
                )

    def test_run_flow_blocks_when_codex_times_out_mid_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=_FakeCodexRun(
                    [
                        {
                            "thread_id": "session-1",
                            "last_message": {
                                "kind": "handoff",
                                "next_owner": "change_engineer",
                                "summary": None,
                                "reason": None,
                                "sleep_duration_seconds": None,
                            },
                        },
                        {
                            "thread_id": "session-timeout",
                            "timeout": True,
                            "stderr": "partial stderr",
                        },
                    ]
                ),
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.BLOCKED)
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertEqual(state.current_agent_key, "02_change_engineer")
            self.assertEqual(state.turn_index, 2)
            self.assertIn("timed out", state.blocker_reason or "")
            self.assertIn("Rally Blocked", issue_text)
            self.assertIn("Handed off", rendered_text)
            self.assertIn("session-timeout", rendered_text)
            self.assertIn("BLOCKED", rendered_text)

    def test_run_flow_blocks_when_max_command_turns_is_hit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, max_command_turns=1)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.BLOCKED)
            self.assertEqual(result.current_agent_key, "02_change_engineer")
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertEqual(state.current_agent_key, "02_change_engineer")
            self.assertEqual(state.turn_index, 1)
            self.assertEqual(len(fake_run.calls), 1)
            self.assertIn("max_command_turns=1", state.blocker_reason or "")
            self.assertIn("Rally Blocked", issue_text)
            self.assertIn("Handed off", rendered_text)
            self.assertIn("max_command_turns=1", rendered_text)
            self.assertFalse((run_dir / "logs" / "adapter_launch" / "turn-002-change_engineer.json").exists())

    def _create_pending_run(self, *, repo_root: Path) -> Path:
        with patch(
            "rally.services.home_materializer.resolve_interactive_issue_editor",
            return_value=None,
        ):
            with self.assertRaises(RallyUsageError):
                run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo"),
                    subprocess_run=_FakeCodexRun([]),
                )
        return find_run_dir(repo_root=repo_root, run_id="DMO-1")

    def _write_issue(self, *, run_dir: Path, body: str = "Fix the pagination bug.\n") -> None:
        (run_dir / "home" / "issue.md").write_text(body, encoding="utf-8")

    def _write_demo_repo(
        self,
        *,
        repo_root: Path,
        with_setup_script: bool = False,
        max_command_turns: int = 8,
    ) -> None:
        (repo_root / "skills" / "repo-search").mkdir(parents=True)
        (repo_root / "skills" / "repo-search" / "SKILL.md").write_text(
            textwrap.dedent(
                """\
                ---
                name: repo-search
                description: "Use `rg` to find the exact files and tests for the current task."
                ---

                # Repo Search
                """
            ),
            encoding="utf-8",
        )
        (repo_root / "skills" / "rally-kernel").mkdir(parents=True)
        (repo_root / "skills" / "rally-kernel" / "SKILL.md").write_text(
            textwrap.dedent(
                """\
                ---
                name: rally-kernel
                description: "Leave Rally notes and end the turn with valid final JSON."
                ---

                # Rally Kernel
                """
            ),
            encoding="utf-8",
        )
        (repo_root / "stdlib" / "rally" / "schemas").mkdir(parents=True)
        (repo_root / "stdlib" / "rally" / "examples").mkdir(parents=True)
        (repo_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json").write_text(
            textwrap.dedent(
                """\
                {
                  "type": "object",
                  "required": ["kind", "next_owner", "summary", "reason", "sleep_duration_seconds"],
                  "properties": {
                    "kind": { "type": "string", "enum": ["handoff", "done", "blocker", "sleep"] },
                    "next_owner": { "type": ["string", "null"] },
                    "summary": { "type": ["string", "null"] },
                    "reason": { "type": ["string", "null"] },
                    "sleep_duration_seconds": { "type": ["integer", "null"] }
                  }
                }
                """
            ),
            encoding="utf-8",
        )
        (repo_root / "stdlib" / "rally" / "examples" / "rally_turn_result.example.json").write_text(
            '{"kind":"done","next_owner":null,"summary":"ok","reason":null,"sleep_duration_seconds":null}\n',
            encoding="utf-8",
        )

        flow_root = repo_root / "flows" / "demo"
        (flow_root / "prompts").mkdir(parents=True)
        (flow_root / "build" / "agents" / "scope_lead").mkdir(parents=True)
        (flow_root / "build" / "agents" / "change_engineer").mkdir(parents=True)
        (flow_root / "prompts" / "AGENTS.prompt").write_text("agent Demo:\n", encoding="utf-8")
        if with_setup_script:
            (flow_root / "setup").mkdir(parents=True)
            (flow_root / "setup" / "prepare_home.sh").write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'ok\\n' > \"$RALLY_RUN_HOME/setup-ok.txt\"\n",
                encoding="utf-8",
            )

        setup_home_line = "setup_home_script: setup/prepare_home.sh\n" if with_setup_script else ""
        (flow_root / "flow.yaml").write_text(
            (
                "name: demo\n"
                "code: DMO\n"
                "start_agent: 01_scope_lead\n"
                f"{setup_home_line}"
                "agents:\n"
                "  01_scope_lead:\n"
                "    timeout_sec: 60\n"
                "    allowed_skills: [repo-search]\n"
                "    allowed_mcps: []\n"
                "  02_change_engineer:\n"
                "    timeout_sec: 60\n"
                "    allowed_skills: [repo-search]\n"
                "    allowed_mcps: []\n"
                "runtime:\n"
                "  adapter: codex\n"
                f"  max_command_turns: {max_command_turns}\n"
                "  adapter_args:\n"
                "    model: gpt-5.4\n"
                "    reasoning_effort: medium\n"
                "    project_doc_max_bytes: 0\n"
            ),
            encoding="utf-8",
        )
        self._write_compiled_agent(repo_root=repo_root, flow_root=flow_root, slug="scope_lead", name="ScopeLead")
        self._write_compiled_agent(
            repo_root=repo_root,
            flow_root=flow_root,
            slug="change_engineer",
            name="ChangeEngineer",
        )

    def _write_poem_repo(self, *, repo_root: Path) -> None:
        source_root = Path(__file__).resolve().parents[2]
        shutil.copytree(source_root / "flows" / "poem_loop", repo_root / "flows" / "poem_loop")
        shutil.copytree(source_root / "skills" / "rally-kernel", repo_root / "skills" / "rally-kernel")
        shutil.copytree(source_root / "stdlib" / "rally", repo_root / "stdlib" / "rally")

    def _write_compiled_agent(
        self,
        *,
        repo_root: Path,
        flow_root: Path,
        slug: str,
        name: str,
    ) -> None:
        agent_dir = flow_root / "build" / "agents" / slug
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "AGENTS.md").write_text(f"# {name}\n", encoding="utf-8")
        (agent_dir / "AGENTS.contract.json").write_text(
            json.dumps(
                {
                    "contract_version": 1,
                    "agent": {
                        "name": name,
                        "slug": slug,
                        "entrypoint": "flows/demo/prompts/AGENTS.prompt",
                    },
                    "final_output": {
                        "exists": True,
                        "declaration_key": "DemoTurnResult",
                        "declaration_name": "DemoTurnResult",
                        "format_mode": "json_schema",
                        "schema_profile": "OpenAIStructuredOutput",
                        "schema_file": "stdlib/rally/schemas/rally_turn_result.schema.json",
                        "example_file": "stdlib/rally/examples/rally_turn_result.example.json",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


class _FakeCodexRun:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        response = self._responses[len(self.calls)]
        self.calls.append({"command": command, "kwargs": kwargs})

        if bool(response.get("timeout")):
            raise subprocess.TimeoutExpired(
                cmd=command,
                timeout=float(kwargs["timeout"]),
                output=f'{{"type":"thread.started","thread_id":"{response["thread_id"]}"}}\n',
                stderr=str(response.get("stderr", "partial stderr")),
            )

        output_path = Path(command[command.index("-o") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(response["last_message"]) + "\n", encoding="utf-8")

        stdout_lines = response.get("stdout_lines")
        if isinstance(stdout_lines, list):
            stdout = "".join(json.dumps(line) + "\n" for line in stdout_lines)
        else:
            stdout = (
                f'{{"type":"thread.started","thread_id":"{response["thread_id"]}"}}\n'
                '{"type":"turn.completed","usage":{"input_tokens":1,"cached_input_tokens":0,"output_tokens":1}}\n'
            )
        return subprocess.CompletedProcess(
            args=command,
            returncode=int(response.get("returncode", 0)),
            stdout=stdout,
            stderr=str(response.get("stderr", "")),
        )


if __name__ == "__main__":
    unittest.main()
