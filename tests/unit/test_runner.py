from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rally.domain.run import ResumeRequest, RunRequest, RunStatus
from rally.errors import RallyConfigError, RallyUsageError
from rally.services.flow_build import ensure_flow_assets_built as build_flow_assets
from rally.services.bundled_assets import ensure_workspace_builtins_synced
from rally.services.issue_editor import IssueEditorResult
from rally.services.issue_ledger import ORIGINAL_ISSUE_END_MARKER
from rally.services.run_store import archive_run, find_run_dir, load_run_state, write_run_state
from rally.services.runner import resume_run, run_flow
from rally.terminal.display import AgentDisplayIdentity, DisplayContext, build_terminal_display


class RunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self._build_patcher = patch("rally.services.runner.ensure_flow_assets_built", autospec=True)
        self.ensure_flow_assets_built = self._build_patcher.start()
        self.addCleanup(self._build_patcher.stop)

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
            self.assertIn("Next: `rally resume DMO-1 --restart`", result.message)
            self.assertFalse((run_dir / "home" / "operator_brief.md").exists())
            self.assertIn("Fix the pagination bug.", issue_text)
            self.assertIn("Rally Run Started", issue_text)
            self.assertIn("Rally Turn Result", issue_text)
            self.assertIn("Rally Done", issue_text)
            self.assertIn("## Rally Run Started\n- Run ID: `DMO-1`\n- Time:", issue_text)
            self.assertIn("## Rally Turn Result\n- Run ID: `DMO-1`\n- Turn: `1`", issue_text)
            self.assertIn("## Rally Done\n- Run ID: `DMO-1`\n- Turn: `2`", issue_text)
            self.assertIn("\n---\n\n## Rally Turn Result", issue_text)
            self.assertIn("```json\n{\n  \"kind\": \"handoff\"", issue_text)
            self.assertIn('"next_owner": "change_engineer"', issue_text)
            self.assertIn('"summary": "verified"', issue_text)
            self.assertIn("session-1", session_text)
            self.assertIn('"code": "RUN"', events_text)
            self.assertIn('"code": "SESSION"', agent_log_text)
            self.assertIn("Investigating the bug", rendered_text)
            self.assertIn("Tracing the pagination path", rendered_text)
            self.assertIn('rg -n "page" src', rendered_text)
            self.assertIn("Handed off", rendered_text)
            self.assertIn("is done: verified", rendered_text)
            self.assertEqual(launch_record["env"]["RALLY_AGENT_SLUG"], "scope_lead")
            self.assertEqual(launch_record["env"]["RALLY_TURN_NUMBER"], "1")
            self.assertEqual(
                json.loads(
                    (run_dir / "logs" / "adapter_launch" / "turn-002-change_engineer.json").read_text(
                        encoding="utf-8"
                    )
                )["env"]["RALLY_TURN_NUMBER"],
                "2",
            )
            self.assertIn("--output-schema", fake_run.calls[0]["command"])
            self.assertIn("-C", fake_run.calls[0]["command"])
            self.assertIn(
                "--dangerously-bypass-approvals-and-sandbox",
                fake_run.calls[0]["command"],
            )

    def test_run_flow_step_pauses_after_one_turn(self) -> None:
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
                    }
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", step=True),
                    subprocess_run=fake_run,
                )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.PAUSED)
            self.assertEqual(result.current_agent_key, "02_change_engineer")
            self.assertEqual(state.status, RunStatus.PAUSED)
            self.assertEqual(state.current_agent_key, "02_change_engineer")
            self.assertEqual(state.turn_index, 1)
            self.assertIsNone(state.blocker_reason)
            self.assertEqual(len(fake_run.calls), 1)
            self.assertIn("Next: `rally resume DMO-1` or `rally resume DMO-1 --step`", result.message)
            self.assertIn("Rally Paused", issue_text)
            self.assertNotIn("Rally Blocked", issue_text)
            self.assertIn("paused after one step", rendered_text)
            self.assertFalse((run_dir / "logs" / "adapter_launch" / "turn-002-change_engineer.json").exists())

    def test_resume_run_step_pauses_after_one_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
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
                request=ResumeRequest(run_id="DMO-1", step=True),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.PAUSED)
            self.assertEqual(result.current_agent_key, "02_change_engineer")
            self.assertEqual(state.status, RunStatus.PAUSED)
            self.assertEqual(state.current_agent_key, "02_change_engineer")
            self.assertEqual(state.turn_index, 1)
            self.assertEqual(len(fake_run.calls), 1)
            self.assertIn("Next: `rally resume DMO-1` or `rally resume DMO-1 --step`", result.message)
            self.assertIn("Rally Paused", issue_text)
            self.assertNotIn("Rally Blocked", issue_text)
            self.assertIn("paused after one step", rendered_text)
            self.assertFalse((run_dir / "logs" / "adapter_launch" / "turn-002-change_engineer.json").exists())

    def test_run_flow_from_file_seeds_issue_without_opening_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            seed_path = repo_root / "seed-issue.md"
            seed_path.write_text("Seeded issue text.\n", encoding="utf-8")
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "seeded run done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=AssertionError("editor should not open for `--from-file`"),
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", issue_seed_path=seed_path),
                    subprocess_run=fake_run,
                )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            self.assertEqual(result.run_id, "DMO-1")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(len(fake_run.calls), 1)
            self.assertIn(f"Seeded `home/issue.md` from `{seed_path}`.", result.message)
            self.assertTrue(issue_text.startswith("Seeded issue text.\n"))
            self.assertIn("## Rally Run Started", issue_text)
            self.assertIn(f"- Issue Seed: `{seed_path}`", issue_text)
            self.assertNotIn("Opening editor for `home/issue.md`", rendered_text)

    def test_run_flow_from_file_works_with_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            seed_path = repo_root / "seed-issue.md"
            seed_path.write_text("Seeded issue text.\n", encoding="utf-8")
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

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=AssertionError("editor should not open for `--from-file`"),
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", step=True, issue_seed_path=seed_path),
                    subprocess_run=fake_run,
                )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.PAUSED)
            self.assertEqual(state.status, RunStatus.PAUSED)
            self.assertEqual(state.turn_index, 1)
            self.assertEqual(len(fake_run.calls), 1)
            self.assertIn(f"Seeded `home/issue.md` from `{seed_path}`.", result.message)
            self.assertTrue(issue_text.startswith("Seeded issue text.\n"))
            self.assertIn("Rally Paused", issue_text)

    def test_run_flow_from_file_with_new_archives_existing_run_and_seeds_new_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=find_run_dir(repo_root=repo_root, run_id="DMO-1"), body="Fix the old issue.\n")
            seed_path = repo_root / "seed-issue.md"
            seed_path.write_text("Seeded new issue.\n", encoding="utf-8")
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "fresh seeded run done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=True,
            ), patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=AssertionError("editor should not open for `--from-file`"),
            ):
                result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", start_new=True, issue_seed_path=seed_path),
                    subprocess_run=fake_run,
                )

            archived_dir = repo_root / "runs" / "archive" / "DMO-1"
            new_run_dir = repo_root / "runs" / "active" / "DMO-2"
            archived_issue = (archived_dir / "home" / "issue.md").read_text(encoding="utf-8")
            new_issue = (new_run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.run_id, "DMO-2")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue(archived_dir.is_dir())
            self.assertTrue(new_run_dir.is_dir())
            self.assertIn("Fix the old issue.", archived_issue)
            self.assertIn("Rally Archived", archived_issue)
            self.assertTrue(new_issue.startswith("Seeded new issue.\n"))
            self.assertIn(f"- Issue Seed: `{seed_path}`", new_issue)
            self.assertIn(f"Seeded `home/issue.md` from `{seed_path}`.", result.message)

    def test_run_flow_from_file_missing_file_stops_before_archiving_or_creating_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._create_pending_run(repo_root=repo_root)
            missing_path = repo_root / "missing-issue.md"

            with patch("rally.services.runner._confirm_replace_active_run") as confirm_replace:
                with self.assertRaisesRegex(RallyUsageError, "Issue seed file does not exist"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo", start_new=True, issue_seed_path=missing_path),
                        subprocess_run=_FakeCodexRun([]),
                    )

            confirm_replace.assert_not_called()
            self.assertTrue((repo_root / "runs" / "active" / "DMO-1").is_dir())
            self.assertFalse((repo_root / "runs" / "archive" / "DMO-1").exists())
            self.assertFalse((repo_root / "runs" / "active" / "DMO-2").exists())

    def test_run_flow_from_file_rejects_blank_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            seed_path = repo_root / "blank-issue.md"
            seed_path.write_text(" \n\t\n", encoding="utf-8")

            with self.assertRaisesRegex(RallyUsageError, "Issue seed file is blank"):
                run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", issue_seed_path=seed_path),
                    subprocess_run=_FakeCodexRun([]),
                )

            self.assertFalse((repo_root / "runs" / "active" / "DMO-1").exists())

    def test_run_flow_from_file_rejects_non_utf8_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            seed_path = repo_root / "bad-issue.md"
            seed_path.write_bytes(b"\xff\xfe\x00")

            with self.assertRaisesRegex(RallyUsageError, "must be valid UTF-8 text"):
                run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", issue_seed_path=seed_path),
                    subprocess_run=_FakeCodexRun([]),
                )

            self.assertFalse((repo_root / "runs" / "active" / "DMO-1").exists())

    def test_resume_run_from_paused_continues_without_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            first_result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1", step=True),
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
                        }
                    ]
                ),
            )
            second_result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=_FakeCodexRun(
                    [
                        {
                            "thread_id": "session-2",
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

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(first_result.status, RunStatus.PAUSED)
            self.assertEqual(second_result.status, RunStatus.DONE)
            self.assertEqual(state.status, RunStatus.DONE)
            self.assertIn("Rally Paused", issue_text)
            self.assertIn("Rally Done", issue_text)

    def test_resume_run_step_from_paused_advances_one_more_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            first_result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1", step=True),
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
                        }
                    ]
                ),
            )
            second_result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1", step=True),
                subprocess_run=_FakeCodexRun(
                    [
                        {
                            "thread_id": "session-2",
                            "last_message": {
                                "kind": "handoff",
                                "next_owner": "scope_lead",
                                "summary": None,
                                "reason": None,
                                "sleep_duration_seconds": None,
                            },
                        }
                    ]
                ),
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(first_result.status, RunStatus.PAUSED)
            self.assertEqual(second_result.status, RunStatus.PAUSED)
            self.assertEqual(second_result.current_agent_key, "01_scope_lead")
            self.assertEqual(state.status, RunStatus.PAUSED)
            self.assertEqual(state.current_agent_key, "01_scope_lead")
            self.assertEqual(state.turn_index, 2)
            self.assertEqual(issue_text.count("## Rally Paused"), 2)
            self.assertFalse((run_dir / "logs" / "adapter_launch" / "turn-003-scope_lead.json").exists())

    def test_resume_run_with_edit_and_step_pauses_after_one_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
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
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True, step=True),
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
                            }
                        ]
                    ),
                )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.PAUSED)
            self.assertEqual(state.status, RunStatus.PAUSED)
            self.assertTrue(issue_text.startswith("New issue text.\n"))
            self.assertIn("## user edited issue.md", issue_text)
            self.assertIn("-Old issue.\n+New issue text.\n", issue_text)
            self.assertIn("Rally Paused", issue_text)

    def test_resume_run_restart_with_step_pauses_after_one_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Original issue text.\n")

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=True,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", restart=True, step=True),
                    subprocess_run=_FakeCodexRun(
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
                            }
                        ]
                    ),
                )

            new_run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-2")
            state = load_run_state(run_dir=new_run_dir)
            issue_text = (new_run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.run_id, "DMO-2")
            self.assertEqual(result.status, RunStatus.PAUSED)
            self.assertEqual(result.current_agent_key, "02_change_engineer")
            self.assertEqual(state.status, RunStatus.PAUSED)
            self.assertEqual(state.current_agent_key, "02_change_engineer")
            self.assertTrue(issue_text.startswith("Original issue text.\n"))
            self.assertIn("- Source: `rally resume --restart`", issue_text)
            self.assertIn("Rally Paused", issue_text)

    def test_poem_loop_prompt_includes_kernel_skill_and_writer_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_poem_repo(repo_root=repo_root)
            flow_path = repo_root / "flows" / "poem_loop" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("  adapter: claude_code\n", "  adapter: codex\n")
            flow_text = flow_text.replace("    model: sonnet\n", "    model: gpt-5.4\n")
            flow_path.write_text(flow_text, encoding="utf-8")
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
                            "verdict": "accept",
                            "reviewed_artifact": "home:artifacts/poem.md",
                            "analysis_performed": "The sonnet keeps its moon focus, the images stay clear, and the draft now feels finished.",
                            "findings_first": "The poem is ready to keep as written."
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
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            prompt_text = fake_run.calls[0]["kwargs"]["input"]

            self.assertEqual(result.run_id, "POM-1")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIsNone(result.current_agent_key)
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-memory" / "SKILL.md").is_file())
            self.assertIn("## Skills", prompt_text)
            self.assertIn("### rally-kernel", prompt_text)
            self.assertIn("### rally-memory", prompt_text)
            self.assertIn("### Saved Run Note", prompt_text)
            self.assertNotIn("\n### Writer Issue Note\n", prompt_text)
            self.assertIn(
                "Rally runs this flow. Read `home:issue.md` first, use it as the shared ledger for this run, "
                "leave one short note only when later readers need it, and end the turn with the final JSON this role declares.",
                prompt_text,
            )
            self.assertIn("Use `home:issue.md` as the shared ledger for this run.", prompt_text)
            self.assertNotIn("### Read Order", prompt_text)
            self.assertNotIn("### Turn Sequence", prompt_text)
            self.assertNotIn("Use the shared `rally-kernel` skill for saved notes.", prompt_text)
            self.assertIn('Append With: `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`', prompt_text)
            self.assertIn("Artistic Rationale", prompt_text)
            self.assertIn("### Rally Turn Result", prompt_text)
            self.assertNotIn("\n### Writer Turn Result\n", prompt_text)
            self.assertIn("## Rally Note", issue_text)
            self.assertIn("- Source: `rally runtime review`", issue_text)
            self.assertIn("### Findings First", issue_text)
            self.assertIn("The poem is ready to keep as written.", issue_text)
            self.assertIn("```json\n{\n  \"verdict\": \"accept\"", issue_text)
            self.assertIn('"reviewed_artifact": "home:artifacts/poem.md"', issue_text)

    def test_resume_run_rebuilds_flow_and_stdlib_prompt_sources_before_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_poem_repo(repo_root=repo_root)
            self.ensure_flow_assets_built.side_effect = build_flow_assets
            pyproject_path = repo_root / "pyproject.toml"
            pyproject_path.write_text(
                pyproject_path.read_text(encoding="utf-8").replace("name = 'poem-fixture'", "name = 'rally'")
                + "\n[[tool.doctrine.emit.targets]]\n"
                'name = "rally-kernel"\n'
                'entrypoint = "skills/rally-kernel/prompts/SKILL.prompt"\n'
                'output_dir = "skills/rally-kernel/build"\n'
                "\n[[tool.doctrine.emit.targets]]\n"
                'name = "rally-memory"\n'
                'entrypoint = "skills/rally-memory/prompts/SKILL.prompt"\n'
                'output_dir = "skills/rally-memory/build"\n',
                encoding="utf-8",
            )
            shutil.rmtree(repo_root / "skills" / "rally-kernel")
            shutil.rmtree(repo_root / "skills" / "rally-memory")
            self._write_framework_builtin_skills(framework_root=repo_root)

            flow_path = repo_root / "flows" / "poem_loop" / "flow.yaml"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace("  max_command_turns: 20\n", "  max_command_turns: 1\n"),
                encoding="utf-8",
            )

            first_turn = _FakeCodexRun(
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
                first_result = run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="poem_loop"),
                    subprocess_run=first_turn,
                )

            run_dir = find_run_dir(repo_root=repo_root, run_id="POM-1")
            self.assertEqual(first_result.status, RunStatus.BLOCKED)
            self.assertEqual(first_result.current_agent_key, "02_poem_critic")

            flow_prompt_path = repo_root / "flows" / "poem_loop" / "prompts" / "roles" / "poem_critic.prompt"
            flow_prompt_marker = "Call out the anchor image before the verdict."
            flow_prompt_path.write_text(
                flow_prompt_path.read_text(encoding="utf-8").replace(
                    '    "Accept only when you would be glad to hand the poem back as finished."\n',
                    '    "Accept only when you would be glad to hand the poem back as finished."\n'
                    f'    "{flow_prompt_marker}"\n',
                ),
                encoding="utf-8",
            )

            stdlib_prompt_path = repo_root / "stdlib" / "rally" / "prompts" / "rally" / "base_agent.prompt"
            stdlib_prompt_marker = "Keep the shared Rally rules short and action-first."
            stdlib_prompt_path.write_text(
                stdlib_prompt_path.read_text(encoding="utf-8").replace(
                    '        "Rally runs this flow. Read `home:issue.md` first, use it as the shared ledger for this run, leave one short note only when later readers need it, and end the turn with the final JSON this role declares."\n',
                    '        "Rally runs this flow. Read `home:issue.md` first, use it as the shared ledger for this run, leave one short note only when later readers need it, and end the turn with the final JSON this role declares."\n'
                    f'        "{stdlib_prompt_marker}"\n',
                ),
                encoding="utf-8",
            )

            second_turn = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-poem-2",
                        "last_message": {
                            "verdict": "accept",
                            "reviewed_artifact": "home:artifacts/poem.md",
                            "analysis_performed": "The sonnet keeps its moon focus, the images stay clear, and the draft now feels finished.",
                            "findings_first": "The poem is ready to keep as written.",
                        },
                    }
                ]
            )

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                second_result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="POM-1", edit_issue=True),
                    subprocess_run=second_turn,
                )

            prompt_text = second_turn.calls[0]["kwargs"]["input"]
            repo_readback = (
                repo_root / "flows" / "poem_loop" / "build" / "agents" / "poem_critic" / "AGENTS.md"
            ).read_text(encoding="utf-8")
            run_home_readback = (run_dir / "home" / "agents" / "poem_critic" / "AGENTS.md").read_text(encoding="utf-8")

            # Prompt source is the shipped truth. A resume must rebuild prompt
            # source edits and send that updated text on the very next turn.
            self.assertEqual(second_result.status, RunStatus.DONE)
            self.assertIn(flow_prompt_marker, prompt_text)
            self.assertIn(stdlib_prompt_marker, prompt_text)
            self.assertIn(flow_prompt_marker, repo_readback)
            self.assertIn(stdlib_prompt_marker, repo_readback)
            self.assertIn(flow_prompt_marker, run_home_readback)
            self.assertIn(stdlib_prompt_marker, run_home_readback)

    def test_run_flow_syncs_builtin_skills_into_workspace_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, copy_framework_builtins=False)
            self.assertFalse((repo_root / "skills" / "rally-kernel").exists())
            self.assertFalse((repo_root / "skills" / "rally-memory").exists())

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

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

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue((repo_root / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((repo_root / "skills" / "rally-memory" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-memory" / "SKILL.md").is_file())

    def test_resume_run_passes_workspace_dir_to_prompt_input_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                runtime_env={
                    "PROJECT_ROOT": "workspace:fixtures/project",
                    "FLOW_ONLY": "from-flow",
                },
            )
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_path.write_text(
                flow_text.replace(
                    "  adapter_args:\n",
                    "  prompt_input_command: flow:setup/prompt_inputs.py\n  adapter_args:\n",
                ),
                encoding="utf-8",
            )
            (repo_root / "flows" / "demo" / "setup").mkdir(parents=True, exist_ok=True)
            (repo_root / "flows" / "demo" / "setup" / "prompt_inputs.py").write_text("print('{}')\n", encoding="utf-8")

            captured_env: dict[str, str] = {}

            def prompt_input_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                self.assertEqual(command[0], sys.executable)
                self.assertIn("RALLY_WORKSPACE_DIR", kwargs["env"])
                self.assertIn("RALLY_CLI_BIN", kwargs["env"])
                captured_env.update(kwargs["env"])
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout=json.dumps({"Env": {"workspace_dir": kwargs["env"]["RALLY_WORKSPACE_DIR"]}}),
                    stderr="",
                )

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            with patch.dict(os.environ, {"FLOW_ONLY": "from-shell"}, clear=False), patch(
                "rally.services.runner.subprocess.run",
                side_effect=prompt_input_run,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=fake_run,
                )

            prompt_text = fake_run.calls[0]["kwargs"]["input"]
            launch_record = json.loads(
                (run_dir / "logs" / "adapter_launch" / "turn-001-scope_lead.json").read_text(encoding="utf-8")
            )
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(captured_env["RALLY_WORKSPACE_DIR"], str(repo_root))
            self.assertEqual(captured_env["PROJECT_ROOT"], str(repo_root / "fixtures" / "project"))
            self.assertEqual(captured_env["FLOW_ONLY"], "from-flow")
            self.assertEqual(fake_run.calls[0]["kwargs"]["env"]["PROJECT_ROOT"], str(repo_root / "fixtures" / "project"))
            self.assertEqual(fake_run.calls[0]["kwargs"]["env"]["FLOW_ONLY"], "from-flow")
            self.assertNotIn("FLOW_ONLY", launch_record["env"])
            self.assertIn(str(repo_root), prompt_text)

    def test_run_flow_passes_flow_env_to_setup_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                runtime_env={
                    "PROJECT_ROOT": "workspace:fixtures/project",
                    "FLOW_ONLY": "from-flow",
                },
            )
            setup_path = repo_root / "flows" / "demo" / "setup" / "prepare_home.sh"
            setup_path.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    printf '%s\n%s\n' "$PROJECT_ROOT" "$FLOW_ONLY" > "$RALLY_RUN_HOME/setup-env.txt"
                    """
                ),
                encoding="utf-8",
            )
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch.dict(os.environ, {"FLOW_ONLY": "from-shell"}, clear=False), patch(
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
            setup_env_text = (run_dir / "home" / "setup-env.txt").read_text(encoding="utf-8")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(
                setup_env_text,
                f"{repo_root / 'fixtures' / 'project'}\nfrom-flow\n",
            )

    def test_resume_run_supports_claude_code_adapter_and_writes_claude_launch_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                runtime_env={"FLOW_ONLY": "from-flow"},
            )
            self._write_fixture_repo_mcp(repo_root=repo_root)
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("  adapter: codex\n", "  adapter: claude_code\n")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [fixture-repo]\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            fake_run = _FakeClaudeRun(
                [
                    {
                        "session_id": "claude-session-1",
                        "assistant_text": "Investigating the bug",
                        "structured_output": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "session_id": "claude-session-2",
                        "structured_output": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            session_text = (run_dir / "home" / "sessions" / "scope_lead" / "session.yaml").read_text(
                encoding="utf-8"
            )
            launch_record = json.loads(
                (run_dir / "logs" / "adapter_launch" / "turn-001-scope_lead.json").read_text(encoding="utf-8")
            )
            mcp_config = json.loads((run_dir / "home" / "claude_code" / "mcp.json").read_text(encoding="utf-8"))

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(fake_run.calls[0]["command"][0], "claude")
            self.assertIn("-p", fake_run.calls[0]["command"])
            self.assertIn("--verbose", fake_run.calls[0]["command"])
            self.assertIn("--permission-mode", fake_run.calls[0]["command"])
            self.assertIn("dontAsk", fake_run.calls[0]["command"])
            self.assertIn("--tools", fake_run.calls[0]["command"])
            self.assertIn("--allowedTools", fake_run.calls[0]["command"])
            self.assertIn("--strict-mcp-config", fake_run.calls[0]["command"])
            self.assertEqual(fake_run.calls[1]["command"][0], "claude")
            self.assertEqual(fake_run.calls[0]["kwargs"]["env"]["FLOW_ONLY"], "from-flow")
            self.assertEqual(launch_record["env"]["ENABLE_CLAUDEAI_MCP_SERVERS"], "false")
            self.assertNotIn("FLOW_ONLY", launch_record["env"])
            self.assertIn("claude-session-1", session_text)
            self.assertIn("fixture-repo", mcp_config["mcpServers"])
            self.assertEqual(
                mcp_config["mcpServers"]["fixture-repo"]["args"],
                ["run", "fixture-repo", "--repo", str(run_dir / "home" / "repos" / "demo_repo")],
            )
            self.assertEqual(
                mcp_config["mcpServers"]["fixture-repo"]["cwd"],
                str(Path("/tmp/fixture-repo").resolve(strict=False)),
            )
            self.assertTrue((run_dir / "home" / ".claude" / "skills").is_symlink())

    def test_resume_run_blocks_before_turn_when_required_claude_mcp_cannot_start(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._write_fixture_repo_mcp(repo_root=repo_root)
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("  adapter: codex\n", "  adapter: claude_code\n")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [fixture-repo]\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            (repo_root / "mcps" / "fixture-repo" / "server.toml").write_text(
                textwrap.dedent(
                    """\
                    command = "missing-fixture-mcp"
                    args = ["--repo", "home:repos/demo_repo"]
                    cwd = "host:/tmp/fixture-repo"
                    transport = "stdio"
                    """
                ),
                encoding="utf-8",
            )

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            fake_run = _FakeClaudeRun([])

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")

            # Claude should stop before turn 1 and record a user-visible MCP
            # blocker when a required launcher cannot start.
            self.assertEqual(result.status, RunStatus.BLOCKED)
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertEqual(state.turn_index, 0)
            self.assertIn("fixture-repo", state.blocker_reason or "")
            self.assertIn("command_startability", state.blocker_reason or "")
            self.assertIn("missing-fixture-mcp", state.blocker_reason or "")
            self.assertFalse((run_dir / "logs" / "adapter_launch" / "turn-001-scope_lead.json").exists())
            self.assertIn("Rally Blocked", issue_text)
            self.assertIn("MCP: `fixture-repo`", issue_text)
            self.assertIn("Check: `command_startability`", issue_text)
            self.assertNotIn("Starting turn 1", rendered_text)
            self.assertFalse(any(call["command"][0] == "claude" for call in fake_run.calls))

    def test_run_flow_activates_current_agent_skill_view_for_codex_turns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._write_doctrine_skill(
                repo_root=repo_root,
                skill_name="demo-git",
                prompt_title="Demo Git",
                emitted_heading="Demo Git",
                description="Use git commands in the demo repo.",
                include_reference=True,
            )
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace(
                    "  02_change_engineer:\n"
                    "    timeout_sec: 60\n"
                    "    allowed_skills: [repo-search]\n",
                    "  02_change_engineer:\n"
                    "    timeout_sec: 60\n"
                    "    allowed_skills: [demo-git]\n",
                ),
                encoding="utf-8",
            )

            observed_skill_sets: list[set[str]] = []

            class _AssertingCodexRun(_FakeCodexRun):
                def __call__(inner_self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                    run_home = Path(command[command.index("-C") + 1])
                    observed_skill_sets.append(
                        {path.name for path in (run_home / "skills").iterdir() if path.is_dir()}
                    )
                    return super().__call__(command, **kwargs)

            fake_run = _AssertingCodexRun(
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
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

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
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(
                observed_skill_sets,
                [
                    {"repo-search", "rally-kernel", "rally-memory"},
                    {"demo-git", "rally-kernel", "rally-memory"},
                ],
            )
            self.assertTrue((run_dir / "home" / "sessions" / "scope_lead" / "skills" / "repo-search" / "SKILL.md").is_file())
            self.assertFalse((run_dir / "home" / "sessions" / "scope_lead" / "skills" / "demo-git").exists())
            self.assertTrue((run_dir / "home" / "sessions" / "change_engineer" / "skills" / "demo-git" / "SKILL.md").is_file())
            self.assertTrue(
                (
                    run_dir
                    / "home"
                    / "sessions"
                    / "change_engineer"
                    / "skills"
                    / "demo-git"
                    / "references"
                    / "note_examples.md"
                ).is_file()
            )
            self.assertFalse(
                (run_dir / "home" / "sessions" / "change_engineer" / "skills" / "demo-git" / "prompts").exists()
            )
            self.assertTrue((run_dir / "home" / "skills" / "demo-git" / "SKILL.md").is_file())
            self.assertFalse((run_dir / "home" / "skills" / "repo-search").exists())

    def test_resume_run_activates_current_agent_skill_view_for_claude_turns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._write_markdown_skill(
                repo_root=repo_root,
                skill_name="pytest-local",
                heading="Pytest Local",
                description="Run local pytest commands.",
            )
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("  adapter: codex\n", "  adapter: claude_code\n")
            flow_text = flow_text.replace(
                "  02_change_engineer:\n"
                "    timeout_sec: 60\n"
                "    allowed_skills: [repo-search]\n",
                "  02_change_engineer:\n"
                "    timeout_sec: 60\n"
                "    allowed_skills: [pytest-local]\n",
            )
            flow_path.write_text(flow_text, encoding="utf-8")

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            observed_skill_sets: list[set[str]] = []

            class _AssertingClaudeRun(_FakeClaudeRun):
                def __call__(inner_self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                    skills_root = Path(kwargs["cwd"]) / ".claude" / "skills"
                    self.assertTrue(skills_root.is_symlink())
                    observed_skill_sets.append({path.name for path in skills_root.iterdir() if path.is_dir()})
                    return super().__call__(command, **kwargs)

            fake_run = _AssertingClaudeRun(
                [
                    {
                        "session_id": "claude-session-1",
                        "structured_output": {
                            "kind": "handoff",
                            "next_owner": "change_engineer",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "session_id": "claude-session-2",
                        "structured_output": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(
                observed_skill_sets,
                [
                    {"repo-search", "rally-kernel", "rally-memory"},
                    {"pytest-local", "rally-kernel", "rally-memory"},
                ],
            )
            self.assertTrue((run_dir / "home" / "sessions" / "scope_lead" / "skills" / "repo-search" / "SKILL.md").is_file())
            self.assertTrue(
                (run_dir / "home" / "sessions" / "change_engineer" / "skills" / "pytest-local" / "SKILL.md").is_file()
            )
            self.assertTrue((run_dir / "home" / ".claude" / "skills").is_symlink())
            self.assertTrue((run_dir / "home" / "skills" / "pytest-local" / "SKILL.md").is_file())
            self.assertFalse((run_dir / "home" / "skills" / "repo-search").exists())

    def test_poem_loop_claude_review_accepts_embedded_fenced_json_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_poem_repo(repo_root=repo_root)
            flow_path = repo_root / "flows" / "poem_loop" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("  adapter: codex\n", "  adapter: claude_code\n")
            flow_text = flow_text.replace("    model: gpt-5.4\n", "    model: sonnet\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            review_payload = {
                "verdict": "changes_requested",
                "reviewed_artifact": "home:artifacts/poem.md",
                "analysis_performed": (
                    "Checked the haiku against the brief and the writer rationale. "
                    "Line 2 explains the idea instead of making the reader feel it."
                ),
                "findings_first": (
                    "Line 3 lands. Line 2 still needs a sharper image before this poem is ready."
                ),
                "current_artifact": "home:artifacts/poem.md",
                "next_owner": "poem_writer",
                "failure_detail": {
                    "blocked_gate": None,
                    "failing_gates": [
                        "Middle line explains rather than shows the stranding."
                    ],
                },
            }
            fake_run = _FakeClaudeRun(
                [
                    {
                        "session_id": "claude-poem-1",
                        "structured_output": {
                            "kind": "handoff",
                            "next_owner": "poem_critic",
                            "summary": None,
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                    {
                        "session_id": "claude-poem-2",
                        "stdout_lines": [
                            {
                                "type": "system",
                                "subtype": "init",
                                "session_id": "claude-poem-2",
                            },
                            {
                                "type": "assistant",
                                "session_id": "claude-poem-2",
                                "message": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "The poem is close, but the middle line still needs work.",
                                        }
                                    ]
                                },
                            },
                            {
                                "type": "result",
                                "session_id": "claude-poem-2",
                                "usage": {
                                    "input_tokens": 5,
                                    "output_tokens": 13,
                                    "cache_read_input_tokens": 21,
                                },
                                "result": (
                                    "Now I have everything I need.\n\n```json\n"
                                    + json.dumps(review_payload, indent=2)
                                    + "\n```"
                                ),
                            },
                        ],
                    },
                    {
                        "session_id": "claude-poem-3",
                        "structured_output": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "revised poem ready",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    },
                ]
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Write a haiku about being stranded in interstellar space.\n", encoding="utf-8")
                return IssueEditorResult(
                    status="saved",
                    cleaned_text="Write a haiku about being stranded in interstellar space.\n",
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
            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            critic_last_message = json.loads(
                (run_dir / "home" / "sessions" / "poem_critic" / "turn-002" / "last_message.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(state.turn_index, 3)
            self.assertEqual(critic_last_message["verdict"], "changes_requested")
            self.assertEqual(critic_last_message["next_owner"], "poem_writer")
            self.assertTrue((run_dir / "logs" / "adapter_launch" / "turn-003-poem_writer.json").is_file())
            self.assertIn("### Findings First", issue_text)
            self.assertIn("Line 3 lands. Line 2 still needs a sharper image", issue_text)
            self.assertIn("Middle line explains rather than shows the stranding.", issue_text)
            self.assertIn("```json\n{\n  \"verdict\": \"changes_requested\"", issue_text)
            self.assertIn('"failure_detail": {', issue_text)
            self.assertIn('"failing_gates": [', issue_text)

    def test_run_flow_rebuild_failure_stops_before_creating_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self.ensure_flow_assets_built.side_effect = RallyConfigError("build failed")

            with self.assertRaisesRegex(RallyConfigError, "build failed"):
                run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo"),
                    subprocess_run=_FakeCodexRun([]),
                )

            self.assertFalse((repo_root / "runs" / "active" / "DMO-1").exists())
            self.ensure_flow_assets_built.assert_called_once()
            self.assertEqual(self.ensure_flow_assets_built.call_args.kwargs["flow_name"], "demo")
            self.assertEqual(
                self.ensure_flow_assets_built.call_args.kwargs["workspace"].workspace_root,
                repo_root,
            )

    def test_resume_run_renders_trace_details_on_tty_and_keeps_plain_log_compact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "stdout_lines": [
                            {"type": "thread.started", "thread_id": "session-1"},
                            {
                                "type": "item.completed",
                                "item": {
                                    "id": "item_1",
                                    "type": "reasoning",
                                    "text": "Trace the pagination path\nKeep the route narrow",
                                },
                            },
                            {
                                "type": "item.started",
                                "item": {
                                    "id": "item_2",
                                    "type": "command_execution",
                                    "command": 'rg -n "page" src',
                                    "aggregated_output": "",
                                    "status": "in_progress",
                                },
                            },
                            {
                                "type": "item.completed",
                                "item": {
                                    "id": "item_2",
                                    "type": "command_execution",
                                    "command": 'rg -n "page" src',
                                    "aggregated_output": "12 matches\nsrc/app.py:8",
                                    "exit_code": 0,
                                    "status": "completed",
                                },
                            },
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
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            stream = _FakeTtyStream()
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            def display_factory(run_record, flow):
                return build_terminal_display(
                    stream=stream,
                    context=DisplayContext(
                        run_id=run_record.id,
                        flow_name=flow.name,
                        flow_code=flow.code,
                        adapter_name=flow.adapter.name,
                        model_name="gpt-5.4",
                        reasoning_effort="medium",
                        start_agent_key=flow.start_agent_key,
                        agent_count=len(flow.agents),
                        agent_identities=tuple(
                            AgentDisplayIdentity(key=agent.key, slug=agent.slug)
                            for agent in flow.agents.values()
                        ),
                    ),
                )

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
                display_factory=display_factory,
            )

            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            tty_text = _strip_ansi(stream.getvalue())

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIn("Trace the pagination path", tty_text)
            self.assertIn("└ Keep the route narrow", tty_text)
            self.assertIn('rg -n "page" src', tty_text)
            self.assertIn("└ exit code 0", tty_text)
            self.assertIn("└ 12 matches", tty_text)
            self.assertIn("Trace the pagination path", rendered_text)
            self.assertIn('rg -n "page" src', rendered_text)
            self.assertNotIn("Keep the route narrow", rendered_text)
            self.assertNotIn("exit code 0", rendered_text)
            self.assertNotIn("12 matches", rendered_text)

    def test_resume_run_renders_memory_commands_as_memory_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            fake_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-1",
                        "stdout_lines": [
                            {"type": "thread.started", "thread_id": "session-1"},
                            {
                                "type": "item.started",
                                "item": {
                                    "id": "item_1",
                                    "type": "command_execution",
                                    "command": (
                                        '/bin/zsh -lc \'"$RALLY_CLI_BIN" memory search --run-id '
                                        '"$RALLY_RUN_ID" --query "focus the fix"\''
                                    ),
                                    "aggregated_output": "",
                                    "status": "in_progress",
                                },
                            },
                            {
                                "type": "item.completed",
                                "item": {
                                    "id": "item_1",
                                    "type": "command_execution",
                                    "command": (
                                        '/bin/zsh -lc \'"$RALLY_CLI_BIN" memory search --run-id '
                                        '"$RALLY_RUN_ID" --query "focus the fix"\''
                                    ),
                                    "aggregated_output": (
                                        "1. mem_dmo_scope_lead_focus_the_fix (0.83)\n"
                                        "   Focus the fix\n"
                                        "   Fix the concrete bug before widening scope."
                                    ),
                                    "exit_code": 0,
                                    "status": "completed",
                                },
                            },
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
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            stream = _FakeTtyStream()
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            def display_factory(run_record, flow):
                return build_terminal_display(
                    stream=stream,
                    context=DisplayContext(
                        run_id=run_record.id,
                        flow_name=flow.name,
                        flow_code=flow.code,
                        adapter_name=flow.adapter.name,
                        model_name="gpt-5.4",
                        reasoning_effort="medium",
                        start_agent_key=flow.start_agent_key,
                        agent_count=len(flow.agents),
                        agent_identities=tuple(
                            AgentDisplayIdentity(key=agent.key, slug=agent.slug)
                            for agent in flow.agents.values()
                        ),
                    ),
                )

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
                display_factory=display_factory,
            )

            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            tty_text = _strip_ansi(stream.getvalue())

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIn("MEM", tty_text)
            self.assertIn("Search memory for 'focus the fix'.", tty_text)
            self.assertIn("Found 1 memory hit.", tty_text)
            self.assertIn("└ mem_dmo_scope_lead_focus_the_fix: Focus the fix", tty_text)
            self.assertIn("MEM", rendered_text)
            self.assertIn("Found 1 memory hit.", rendered_text)
            self.assertNotIn('/bin/zsh -lc \'"$RALLY_CLI_BIN" memory search', rendered_text)

    def test_resume_run_refreshes_run_home_agents_before_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, max_command_turns=1)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            first_turn = _FakeCodexRun(
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
            first_result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=first_turn,
            )

            self.assertEqual(first_result.status, RunStatus.BLOCKED)
            self.assertTrue(first_turn.calls[0]["kwargs"]["input"].startswith("# ScopeLead\n"))

            updated_markdown = "# Fresh ChangeEngineer\n"
            (repo_root / "flows" / "demo" / "build" / "agents" / "change_engineer" / "AGENTS.md").write_text(
                updated_markdown,
                encoding="utf-8",
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            second_turn = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "verified",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )
            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                second_result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=second_turn,
                )

            self.assertEqual(second_result.status, RunStatus.DONE)
            self.assertTrue(second_turn.calls[0]["kwargs"]["input"].startswith(updated_markdown))
            self.assertEqual(
                (run_dir / "home" / "agents" / "change_engineer" / "AGENTS.md").read_text(encoding="utf-8"),
                updated_markdown,
            )

    def test_resume_run_refreshes_run_home_capabilities_before_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, max_command_turns=1)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            first_result = resume_run(
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
                        }
                    ]
                ),
            )

            self.assertEqual(first_result.status, RunStatus.BLOCKED)

            updated_skill = textwrap.dedent(
                """\
                ---
                name: repo-search
                description: "Use `rg` to find the exact files and tests for the current task."
                ---

                # Repo Search

                Updated for resume.
                """
            )
            (repo_root / "skills" / "repo-search" / "SKILL.md").write_text(updated_skill, encoding="utf-8")
            self._write_fixture_repo_mcp(repo_root=repo_root)

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [fixture-repo]\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                second_result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=_FakeCodexRun(
                        [
                            {
                                "thread_id": "session-2",
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

            self.assertEqual(second_result.status, RunStatus.DONE)
            self.assertEqual(
                (run_dir / "home" / "skills" / "repo-search" / "SKILL.md").read_text(encoding="utf-8"),
                updated_skill,
            )
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "references" / "note_examples.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-memory" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "mcps" / "fixture-repo" / "server.toml").is_file())
            config_text = (run_dir / "home" / "config.toml").read_text(encoding="utf-8")
            self.assertIn("project_doc_max_bytes = 0", config_text)
            self.assertIn('[mcp_servers."fixture-repo"]', config_text)
            self.assertIn('command = "uv"', config_text)
            self.assertIn(
                f'args = ["run", "fixture-repo", "--repo", "{run_dir / "home" / "repos" / "demo_repo"}"]',
                config_text,
            )
            self.assertIn(
                f'cwd = "{Path("/tmp/fixture-repo").resolve(strict=False)}"',
                config_text,
            )
            self.assertIn("required = true", config_text)

    def test_resume_run_blocks_before_turn_when_required_codex_mcp_cannot_start(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._write_fixture_repo_mcp(repo_root=repo_root)

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [fixture-repo]\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            (repo_root / "mcps" / "fixture-repo" / "server.toml").write_text(
                textwrap.dedent(
                    """\
                    command = "missing-fixture-mcp"
                    args = ["--repo", "home:repos/demo_repo"]
                    cwd = "host:/tmp/fixture-repo"
                    transport = "stdio"
                    """
                ),
                encoding="utf-8",
            )

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            fake_run = _FakeCodexRun([])

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
            self.assertEqual(state.turn_index, 0)
            self.assertEqual(state.current_agent_key, "01_scope_lead")
            self.assertIn("fixture-repo", state.blocker_reason or "")
            self.assertIn("command_startability", state.blocker_reason or "")
            self.assertIn("missing-fixture-mcp", state.blocker_reason or "")
            self.assertFalse((run_dir / "logs" / "adapter_launch" / "turn-001-scope_lead.json").exists())
            self.assertIn("Rally Blocked", issue_text)
            self.assertIn("MCP: `fixture-repo`", issue_text)
            self.assertIn("Check: `command_startability`", issue_text)
            self.assertIn("## Rally Blocked\n- Run ID: `DMO-1`\n- Time:", issue_text)
            self.assertNotIn("## Rally Blocked\n- Run ID: `DMO-1`\n- Turn:", issue_text)
            self.assertNotIn("Starting turn 1", rendered_text)
            self.assertFalse(any(call["command"][:2] == ["codex", "exec"] for call in fake_run.calls))

    def test_resume_run_blocks_before_turn_when_required_codex_mcp_is_not_logged_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            (repo_root / "mcps" / "issues-http").mkdir(parents=True)
            (repo_root / "mcps" / "issues-http" / "server.toml").write_text(
                'url = "https://example.com/issues"\n',
                encoding="utf-8",
            )

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [issues-http]\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)
            fake_run = _FakeCodexRun([])

            result = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.BLOCKED)
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertEqual(state.turn_index, 0)
            self.assertIn("issues-http", state.blocker_reason or "")
            self.assertIn("codex_auth_status", state.blocker_reason or "")
            self.assertIn("not_logged_in", state.blocker_reason or "")
            self.assertIn("MCP: `issues-http`", issue_text)
            self.assertIn("Check: `codex_auth_status`", issue_text)
            self.assertFalse(any(call["command"][:2] == ["codex", "exec"] for call in fake_run.calls))

    def test_resume_run_removes_stale_run_home_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, max_command_turns=1)
            self._write_fixture_repo_mcp(repo_root=repo_root)

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [fixture-repo]\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            first_result = resume_run(
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
                        }
                    ]
                ),
            )

            self.assertEqual(first_result.status, RunStatus.BLOCKED)
            self.assertTrue((run_dir / "home" / "skills" / "repo-search" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "references" / "note_examples.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-memory" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "sessions" / "scope_lead" / "skills" / "repo-search" / "SKILL.md").is_file())
            self.assertTrue(
                (run_dir / "home" / "sessions" / "change_engineer" / "skills" / "repo-search" / "SKILL.md").is_file()
            )
            self.assertTrue((run_dir / "home" / "mcps" / "fixture-repo" / "server.toml").is_file())

            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_skills: [repo-search]\n", "    allowed_skills: []\n")
            flow_text = flow_text.replace("    allowed_mcps: [fixture-repo]\n", "    allowed_mcps: []\n")
            flow_path.write_text(flow_text, encoding="utf-8")

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                second_result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=_FakeCodexRun(
                        [
                            {
                                "thread_id": "session-2",
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

            self.assertEqual(second_result.status, RunStatus.DONE)
            self.assertFalse((run_dir / "home" / "skills" / "repo-search").exists())
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-kernel" / "references" / "note_examples.md").is_file())
            self.assertTrue((run_dir / "home" / "skills" / "rally-memory" / "SKILL.md").is_file())
            self.assertFalse((run_dir / "home" / "sessions" / "scope_lead" / "skills" / "repo-search").exists())
            self.assertFalse((run_dir / "home" / "sessions" / "change_engineer" / "skills" / "repo-search").exists())
            self.assertTrue((run_dir / "home" / "sessions" / "scope_lead" / "skills" / "rally-kernel" / "SKILL.md").is_file())
            self.assertTrue(
                (run_dir / "home" / "sessions" / "change_engineer" / "skills" / "rally-memory" / "SKILL.md").is_file()
            )
            self.assertFalse((run_dir / "home" / "mcps" / "fixture-repo").exists())
            config_text = (run_dir / "home" / "config.toml").read_text(encoding="utf-8")
            self.assertEqual(config_text, "project_doc_max_bytes = 0\n")
            self.assertNotIn('mcp_servers."fixture-repo"', config_text)

    def test_run_flow_rejects_doctrine_skill_without_emitted_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            self._write_doctrine_skill(
                repo_root=repo_root,
                skill_name="demo-git",
                prompt_title="Demo Git",
                emitted_heading="Demo Git",
                description="Use git commands in the demo repo.",
                include_reference=False,
            )
            shutil.rmtree(repo_root / "skills" / "demo-git" / "build")
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace(
                    "    allowed_skills: [repo-search]\n",
                    "    allowed_skills: [repo-search, demo-git]\n",
                    1,
                ),
                encoding="utf-8",
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                with self.assertRaisesRegex(RallyConfigError, "missing emitted `build/SKILL.md`"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo"),
                        subprocess_run=_FakeCodexRun([]),
                    )

    def test_run_flow_rejects_allowed_mcp_without_server_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_path.write_text(
                flow_path.read_text(encoding="utf-8").replace(
                    "    allowed_mcps: []\n",
                    "    allowed_mcps: [fixture-repo]\n",
                    1,
                ),
                encoding="utf-8",
            )
            (repo_root / "mcps" / "fixture-repo").mkdir(parents=True, exist_ok=True)
            fake_run = _FakeCodexRun([])

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch(
                "rally.services.home_materializer.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.home_materializer.edit_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                with self.assertRaisesRegex(RallyConfigError, "missing `server.toml`"):
                    run_flow(
                        repo_root=repo_root,
                        request=RunRequest(flow_name="demo"),
                        subprocess_run=fake_run,
                    )

            # An incomplete shipped MCP bundle should fail with a clear Rally
            # config error before any adapter turn starts.
            self.assertFalse(fake_run.calls)

    def test_resume_run_does_not_rerun_setup_after_home_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, with_setup_script=True, max_command_turns=1)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            first_result = resume_run(
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
                        }
                    ]
                ),
            )

            self.assertEqual(first_result.status, RunStatus.BLOCKED)
            self.assertEqual((run_dir / "home" / "setup-ok.txt").read_text(encoding="utf-8"), "ok\n")

            (repo_root / "flows" / "demo" / "setup" / "prepare_home.sh").write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'reran\\n' > \"$RALLY_RUN_HOME/setup-ok.txt\"\n",
                encoding="utf-8",
            )

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Fix the pagination bug.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Fix the pagination bug.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                second_result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                    subprocess_run=_FakeCodexRun(
                        [
                            {
                                "thread_id": "session-2",
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

            self.assertEqual(second_result.status, RunStatus.DONE)
            self.assertEqual((run_dir / "home" / "setup-ok.txt").read_text(encoding="utf-8"), "ok\n")

    def test_resume_run_accepts_clean_guarded_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, with_guarded_repo=True)
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
                                "kind": "done",
                                "next_owner": None,
                                "summary": "guard clean",
                                "reason": None,
                                "sleep_duration_seconds": None,
                            },
                        }
                    ]
                ),
            )

            state = load_run_state(run_dir=run_dir)
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(state.status, RunStatus.DONE)
            self.assertTrue((run_dir / "home" / "repos" / "demo_repo" / ".git").is_dir())

    def test_resume_run_blocks_handoff_when_guarded_git_repo_is_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, with_guarded_repo=True)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            fake_run = _DirtyGuardedRepoCodexRun(
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
            self.assertEqual(result.current_agent_key, "01_scope_lead")
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertEqual(state.current_agent_key, "01_scope_lead")
            self.assertEqual(state.last_turn_kind, "handoff")
            self.assertIn("Guarded repo `repos/demo_repo` is not ready", state.blocker_reason or "")
            self.assertIn("Attempted Result: `handoff`", issue_text)
            self.assertIn("Guarded Repo `repos/demo_repo`", issue_text)
            self.assertNotIn("## Rally Turn Result\n- Run ID: `DMO-1`\n- Turn: `1`", issue_text)
            self.assertIn("blocked", rendered_text.lower())

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
            self.assertIn("## Rally Turn Result\n- Run ID: `DMO-1`\n- Turn: `1`", issue_text)
            self.assertIn("## Rally Blocked\n- Run ID: `DMO-1`\n- Turn: `1`", issue_text)
            self.assertNotIn("Rally Sleeping", issue_text)
            self.assertIn("```json\n{\n  \"kind\": \"sleep\"", issue_text)
            self.assertIn('"sleep_duration_seconds": 60', issue_text)
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

    def test_resume_run_restart_archives_done_run_and_restores_original_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Original issue text.\n")

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
                                "summary": "first pass done",
                                "reason": None,
                                "sleep_duration_seconds": None,
                            },
                        }
                    ]
                ),
            )
            (run_dir / "home" / "issue.md").write_text(
                textwrap.dedent(
                    f"""\
                    Edited issue text.

                    {ORIGINAL_ISSUE_END_MARKER}

                    ---

                    ## user edited issue.md
                    - Run ID: `DMO-1`
                    """
                ),
                encoding="utf-8",
            )
            fresh_run = _FakeCodexRun(
                [
                    {
                        "thread_id": "session-2",
                        "last_message": {
                            "kind": "done",
                            "next_owner": None,
                            "summary": "fresh run done",
                            "reason": None,
                            "sleep_duration_seconds": None,
                        },
                    }
                ]
            )

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=True,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", restart=True),
                    subprocess_run=fresh_run,
                )

            archived_dir = repo_root / "runs" / "archive" / "DMO-1"
            new_run_dir = repo_root / "runs" / "active" / "DMO-2"
            archived_issue = (archived_dir / "home" / "issue.md").read_text(encoding="utf-8")
            new_issue = (new_run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.run_id, "DMO-2")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertIn("Restarted run `DMO-1` as `DMO-2`.", result.message)
            self.assertTrue(archived_dir.is_dir())
            self.assertTrue(new_run_dir.is_dir())
            self.assertTrue(archived_issue.startswith("Edited issue text.\n"))
            self.assertIn("## Rally Archived", archived_issue)
            self.assertIn("- Source: `rally resume --restart`", archived_issue)
            self.assertTrue(new_issue.startswith("Original issue text.\n"))
            self.assertNotIn("Edited issue text.", new_issue)
            self.assertIn("## Rally Run Started", new_issue)
            self.assertIn("- Source: `rally resume --restart`", new_issue)
            self.assertIn("- Restarted From: `DMO-1`", new_issue)
            self.assertNotIn("resume", fresh_run.calls[0]["command"])

    def test_resume_run_restart_allows_blocked_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Restart this blocked issue.\n")
            blocked_state = replace(
                load_run_state(run_dir=run_dir),
                status=RunStatus.BLOCKED,
                blocker_reason="Need more detail.",
            )
            write_run_state(run_dir=run_dir, state=blocked_state)

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=True,
            ):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1", restart=True),
                    subprocess_run=_FakeCodexRun(
                        [
                            {
                                "thread_id": "session-1",
                                "last_message": {
                                    "kind": "done",
                                    "next_owner": None,
                                    "summary": "restarted from blocked",
                                    "reason": None,
                                    "sleep_duration_seconds": None,
                                },
                            }
                        ]
                    ),
                )

            archived_dir = repo_root / "runs" / "archive" / "DMO-1"
            new_run_dir = repo_root / "runs" / "active" / "DMO-2"
            new_issue = (new_run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.run_id, "DMO-2")
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue(archived_dir.is_dir())
            self.assertTrue(new_issue.startswith("Restart this blocked issue.\n"))
            self.assertIn("- Restarted From: `DMO-1`", new_issue)

    def test_resume_run_restart_cancels_when_replacement_not_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Keep this run.\n")

            with patch(
                "rally.services.runner._confirm_replace_active_run",
                return_value=False,
            ):
                with self.assertRaisesRegex(RallyUsageError, "Cancelled restarting run `DMO-1`"):
                    resume_run(
                        repo_root=repo_root,
                        request=ResumeRequest(run_id="DMO-1", restart=True),
                        subprocess_run=_FakeCodexRun([]),
                    )

            self.assertTrue((repo_root / "runs" / "active" / "DMO-1").is_dir())
            self.assertFalse((repo_root / "runs" / "active" / "DMO-2").exists())
            self.assertFalse((repo_root / "runs" / "archive" / "DMO-1").exists())

    def test_resume_run_restart_requires_interactive_tty_to_confirm_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="TTY only restart.\n")

            with patch("sys.stdin", io.StringIO("y\n")), patch("sys.stdout", io.StringIO()):
                with self.assertRaisesRegex(RallyUsageError, "needs an interactive TTY to confirm archiving"):
                    resume_run(
                        repo_root=repo_root,
                        request=ResumeRequest(run_id="DMO-1", restart=True),
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
                with self.assertRaisesRegex(RallyUsageError, "already done.*--restart"):
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

    def test_resume_run_blocks_before_setup_when_required_env_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_env=["PSMOBILE_ROOT"],
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            with self.assertRaisesRegex(RallyUsageError, "requires env var `PSMOBILE_ROOT`"):
                resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=_FakeCodexRun([]),
                )

            self.assertFalse((run_dir / "home" / "setup-ok.txt").exists())
            self.assertFalse((run_dir / "home" / ".rally_home_ready").exists())
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            self.assertIn("requires env var `PSMOBILE_ROOT`", rendered_text)

    def test_resume_run_accepts_required_env_from_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            runtime_root = (repo_root / "psmobile").resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_env=["PSMOBILE_ROOT"],
                runtime_env={"PSMOBILE_ROOT": str(runtime_root)},
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            with patch.dict(os.environ, {"PSMOBILE_ROOT": ""}, clear=False):
                result = resume_run(
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

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue((run_dir / "home" / "setup-ok.txt").is_file())
            self.assertTrue((run_dir / "home" / ".rally_home_ready").is_file())

    def test_resume_run_edit_keeps_issue_diff_when_startup_fails_before_first_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_env=["PSMOBILE_ROOT"],
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir, body="Original issue text.\n")

            def fake_edit_issue(*, issue_path: Path, editor_command: tuple[str, ...]) -> IssueEditorResult:
                self.assertEqual(editor_command, ("vim",))
                issue_path.write_text("Edited issue text.\n", encoding="utf-8")
                return IssueEditorResult(status="saved", cleaned_text="Edited issue text.\n")

            with patch(
                "rally.services.runner.resolve_interactive_issue_editor",
                return_value=("vim",),
            ), patch(
                "rally.services.runner.edit_existing_issue_file_in_editor",
                side_effect=fake_edit_issue,
            ):
                with self.assertRaisesRegex(RallyUsageError, "requires env var `PSMOBILE_ROOT`"):
                    resume_run(
                        repo_root=repo_root,
                        request=ResumeRequest(run_id="DMO-1", edit_issue=True),
                        subprocess_run=_FakeCodexRun([]),
                    )

            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            snapshots = sorted((run_dir / "issue_history").glob("*-issue.md"))

            # The operator edit is user-visible context. Rally must keep the
            # diff block and snapshot even if startup stops before turn 1.
            self.assertTrue(issue_text.startswith("Edited issue text.\n"))
            self.assertIn("## user edited issue.md", issue_text)
            self.assertIn("- Source: `rally resume --edit`", issue_text)
            self.assertTrue(snapshots)
            self.assertEqual(snapshots[-1].read_text(encoding="utf-8"), issue_text)
            self.assertFalse((run_dir / "home" / ".rally_home_ready").exists())

    def test_resume_run_blocks_before_setup_when_required_host_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            missing_file = (repo_root / "missing.env").resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_files=[f"host:{missing_file}"],
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            with self.assertRaisesRegex(RallyUsageError, "requires host file"):
                resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=_FakeCodexRun([]),
                )

            self.assertFalse((run_dir / "home" / "setup-ok.txt").exists())
            self.assertFalse((run_dir / "home" / ".rally_home_ready").exists())
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            self.assertIn(f"host:{missing_file}", rendered_text)

    def test_resume_run_accepts_required_host_file_from_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            config_root = (repo_root / "configs").resolve()
            config_root.mkdir(parents=True)
            (config_root / ".env").write_text("demo=true\n", encoding="utf-8")
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_files=["host:$CONFIG_ROOT/.env"],
                runtime_env={"CONFIG_ROOT": str(config_root)},
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            with patch.dict(os.environ, {"CONFIG_ROOT": ""}, clear=False):
                result = resume_run(
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

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue((run_dir / "home" / "setup-ok.txt").is_file())
            self.assertTrue((run_dir / "home" / ".rally_home_ready").is_file())

    def test_resume_run_blocks_before_setup_when_required_host_directory_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            missing_directory = (repo_root / "missing-dir").resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_directories=[f"host:{missing_directory}"],
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            with self.assertRaisesRegex(RallyUsageError, "requires host directory"):
                resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=_FakeCodexRun([]),
                )

            self.assertFalse((run_dir / "home" / "setup-ok.txt").exists())
            self.assertFalse((run_dir / "home" / ".rally_home_ready").exists())
            rendered_text = (run_dir / "logs" / "rendered.log").read_text(encoding="utf-8")
            self.assertIn(f"host:{missing_directory}", rendered_text)

    def test_resume_run_accepts_required_host_directory_from_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            source_repo = (repo_root / "psmobile").resolve()
            source_repo.mkdir(parents=True)
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_directories=["host:$PSMOBILE_SOURCE_REPO"],
                runtime_env={"PSMOBILE_SOURCE_REPO": str(source_repo)},
            )
            run_dir = self._create_pending_run(repo_root=repo_root)
            self._write_issue(run_dir=run_dir)

            with patch.dict(os.environ, {"PSMOBILE_SOURCE_REPO": ""}, clear=False):
                result = resume_run(
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

            self.assertEqual(result.status, RunStatus.DONE)
            self.assertTrue((run_dir / "home" / "setup-ok.txt").is_file())
            self.assertTrue((run_dir / "home" / ".rally_home_ready").is_file())

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
            self.assertIn("Next: `rally resume DMO-1 --edit` or `rally resume DMO-1 --restart`", result.message)
            self.assertIn("Rally Blocked", issue_text)
            self.assertIn("## Rally Turn Result\n- Run ID: `DMO-1`\n- Turn: `1`", issue_text)
            self.assertIn("## Rally Blocked\n- Run ID: `DMO-1`\n- Time:", issue_text)
            self.assertNotIn("## Rally Blocked\n- Run ID: `DMO-1`\n- Turn:", issue_text)
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
        with_guarded_repo: bool = False,
        max_command_turns: int = 8,
        required_env: list[str] | None = None,
        required_files: list[str] | None = None,
        required_directories: list[str] | None = None,
        runtime_env: dict[str, str] | None = None,
        copy_framework_builtins: bool = True,
    ) -> None:
        source_root = Path(__file__).resolve().parents[2]
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
        if copy_framework_builtins:
            self._write_framework_builtin_skills(framework_root=repo_root)
        shutil.copytree(source_root / "stdlib" / "rally", repo_root / "stdlib" / "rally")

        flow_root = repo_root / "flows" / "demo"
        (flow_root / "prompts").mkdir(parents=True)
        (flow_root / "build" / "agents" / "scope_lead").mkdir(parents=True)
        (flow_root / "build" / "agents" / "change_engineer").mkdir(parents=True)
        (flow_root / "prompts" / "AGENTS.prompt").write_text("agent Demo:\n", encoding="utf-8")
        if with_setup_script or with_guarded_repo:
            (flow_root / "setup").mkdir(parents=True)
            script_lines = ["#!/usr/bin/env bash", "set -euo pipefail"]
            if with_setup_script:
                script_lines.append("printf 'ok\\n' > \"$RALLY_RUN_HOME/setup-ok.txt\"")
            if with_guarded_repo:
                script_lines.extend(
                    [
                        "repo_dir=\"$RALLY_RUN_HOME/repos/demo_repo\"",
                        "mkdir -p \"$repo_dir\"",
                        "git init -b main \"$repo_dir\" >/dev/null 2>&1",
                        "git -C \"$repo_dir\" config user.name \"Rally Test\"",
                        "git -C \"$repo_dir\" config user.email \"rally-test@example.com\"",
                        "git -C \"$repo_dir\" commit --allow-empty -m \"seed repo\" >/dev/null 2>&1",
                    ]
                )
            (flow_root / "setup" / "prepare_home.sh").write_text("\n".join(script_lines) + "\n", encoding="utf-8")

        setup_home_line = "setup_home_script: flow:setup/prepare_home.sh\n" if (with_setup_script or with_guarded_repo) else ""
        host_inputs_lines: list[str] = []
        if required_env or required_files or required_directories:
            host_inputs_lines.append("host_inputs:\n")
            if required_env:
                host_inputs_lines.append(
                    "  required_env: [" + ", ".join(required_env) + "]\n"
                )
            if required_files:
                host_inputs_lines.append(
                    "  required_files: [" + ", ".join(json.dumps(item) for item in required_files) + "]\n"
                )
            if required_directories:
                host_inputs_lines.append(
                    "  required_directories: ["
                    + ", ".join(json.dumps(item) for item in required_directories)
                    + "]\n"
                )
        host_inputs_block = "".join(host_inputs_lines)
        guarded_git_repos_line = "  guarded_git_repos: [home:repos/demo_repo]\n" if with_guarded_repo else ""
        runtime_env_block = ""
        if runtime_env:
            runtime_env_lines = ["  env:\n"]
            for key, value in runtime_env.items():
                runtime_env_lines.append(f"    {key}: {json.dumps(value)}\n")
            runtime_env_block = "".join(runtime_env_lines)
        (flow_root / "flow.yaml").write_text(
            (
                "name: demo\n"
                "code: DMO\n"
                "start_agent: 01_scope_lead\n"
                f"{setup_home_line}"
                f"{host_inputs_block}"
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
                f"{guarded_git_repos_line}"
                f"{runtime_env_block}"
                "  adapter_args:\n"
                "    model: gpt-5.4\n"
                "    reasoning_effort: medium\n"
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

    def _write_fixture_repo_mcp(self, *, repo_root: Path) -> None:
        (repo_root / "mcps" / "fixture-repo").mkdir(parents=True)
        (repo_root / "mcps" / "fixture-repo" / "server.toml").write_text(
            textwrap.dedent(
                """\
                command = "uv"
                args = ["run", "fixture-repo", "--repo", "home:repos/demo_repo"]
                cwd = "host:/tmp/fixture-repo"
                transport = "stdio"
                """
            ),
            encoding="utf-8",
        )

    def _write_poem_repo(self, *, repo_root: Path, copy_framework_builtins: bool = True) -> None:
        source_root = Path(__file__).resolve().parents[2]
        shutil.copytree(source_root / "flows" / "poem_loop", repo_root / "flows" / "poem_loop")
        shutil.copytree(source_root / "stdlib" / "rally", repo_root / "stdlib" / "rally")
        self._write_poem_fixture_pyproject(repo_root=repo_root)
        if copy_framework_builtins:
            ensure_workspace_builtins_synced(
                workspace_root=repo_root,
                pyproject_path=repo_root / "pyproject.toml",
            )
        build_flow_assets(repo_root=repo_root, flow_name="poem_loop")

    def _write_poem_fixture_pyproject(self, *, repo_root: Path) -> None:
        (repo_root / "pyproject.toml").write_text(
            "\n".join(
                (
                    "[project]",
                    "name = 'poem-fixture'",
                    "version = '0.0.0'",
                    "",
                    "[tool.rally.workspace]",
                    "version = 1",
                    "",
                    "[tool.doctrine.compile]",
                    'additional_prompt_roots = ["stdlib/rally/prompts"]',
                    "",
                    "[tool.doctrine.emit]",
                    "",
                    "[[tool.doctrine.emit.targets]]",
                    'name = "poem_loop"',
                    'entrypoint = "flows/poem_loop/prompts/AGENTS.prompt"',
                    'output_dir = "flows/poem_loop/build/agents"',
                    "",
                )
            ),
            encoding="utf-8",
        )

    def _write_framework_builtin_skills(self, *, framework_root: Path) -> None:
        source_root = Path(__file__).resolve().parents[2]
        self._copy_builtin_skill(source_root=source_root, framework_root=framework_root, skill_name="rally-kernel")
        self._copy_builtin_skill(source_root=source_root, framework_root=framework_root, skill_name="rally-memory")

    def _copy_builtin_skill(self, *, source_root: Path, framework_root: Path, skill_name: str) -> None:
        skill_root = framework_root / "skills" / skill_name
        shutil.copytree(source_root / "skills" / skill_name, skill_root)
        if skill_name == "rally-memory" and not (skill_root / "build" / "SKILL.md").is_file():
            (skill_root / "build").mkdir(parents=True, exist_ok=True)
            (skill_root / "build" / "SKILL.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    name: "rally-memory"
                    description: "Shared Rally memory skill."
                    ---

                    # Rally Memory
                    """
                ),
                encoding="utf-8",
            )

    def _write_markdown_skill(
        self,
        *,
        repo_root: Path,
        skill_name: str,
        heading: str,
        description: str,
    ) -> None:
        skill_root = repo_root / "skills" / skill_name
        skill_root.mkdir(parents=True, exist_ok=True)
        (skill_root / "SKILL.md").write_text(
            textwrap.dedent(
                f"""\
                ---
                name: {skill_name}
                description: "{description}"
                ---

                # {heading}
                """
            ),
            encoding="utf-8",
        )

    def _write_doctrine_skill(
        self,
        *,
        repo_root: Path,
        skill_name: str,
        prompt_title: str,
        emitted_heading: str,
        description: str,
        include_reference: bool = False,
    ) -> None:
        skill_root = repo_root / "skills" / skill_name
        (skill_root / "prompts").mkdir(parents=True, exist_ok=True)
        (skill_root / "prompts" / "SKILL.prompt").write_text(
            textwrap.dedent(
                f"""\
                skill package DemoSkill: "{prompt_title}"
                    metadata:
                        name: "{skill_name}"
                        description: "{description}"
                    "A test Doctrine skill."
                """
            ),
            encoding="utf-8",
        )
        build_root = skill_root / "build"
        build_root.mkdir(parents=True, exist_ok=True)
        (build_root / "SKILL.md").write_text(
            textwrap.dedent(
                f"""\
                ---
                name: {skill_name}
                description: "{description}"
                ---

                # {emitted_heading}
                """
            ),
            encoding="utf-8",
        )
        if include_reference:
            (build_root / "references").mkdir(parents=True, exist_ok=True)
            (build_root / "references" / "note_examples.md").write_text(
                "# Note examples\n",
                encoding="utf-8",
            )

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
        self._exec_calls = 0
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append({"command": command, "kwargs": kwargs})
        if command[:3] == ["codex", "mcp", "list"]:
            return self._handle_mcp_list(command=command, kwargs=kwargs)
        if command[:3] == ["codex", "mcp", "get"]:
            return self._handle_mcp_get(command=command, kwargs=kwargs)
        if command[:2] != ["codex", "exec"]:
            return self._handle_stdio_probe(command=command, kwargs=kwargs)

        response = self._responses[self._exec_calls]
        self._exec_calls += 1

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

    def _handle_mcp_list(
        self,
        *,
        command: list[str],
        kwargs: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        payload = [
            {
                "name": name,
                "enabled": bool(server.get("enabled", True)),
                "disabled_reason": None,
                "transport": self._render_transport(server),
                "startup_timeout_sec": server.get("startup_timeout_sec"),
                "tool_timeout_sec": server.get("tool_timeout_sec"),
                "auth_status": self._auth_status_for(server),
            }
            for name, server in self._load_mcp_servers(kwargs).items()
        ]
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    def _handle_mcp_get(
        self,
        *,
        command: list[str],
        kwargs: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        server_name = command[3]
        servers = self._load_mcp_servers(kwargs)
        server = servers.get(server_name)
        if server is None:
            return subprocess.CompletedProcess(args=command, returncode=1, stdout="", stderr="server not found")
        payload = {
            "name": server_name,
            "enabled": bool(server.get("enabled", True)),
            "disabled_reason": None,
            "transport": self._render_transport(server),
            "enabled_tools": server.get("enabled_tools"),
            "disabled_tools": server.get("disabled_tools"),
            "startup_timeout_sec": server.get("startup_timeout_sec"),
            "tool_timeout_sec": server.get("tool_timeout_sec"),
        }
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    def _handle_stdio_probe(
        self,
        *,
        command: list[str],
        kwargs: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        executable = command[0]
        if executable.startswith("missing-"):
            raise FileNotFoundError(executable)
        raise subprocess.TimeoutExpired(cmd=command, timeout=float(kwargs["timeout"]))

    def _load_mcp_servers(self, kwargs: dict[str, object]) -> dict[str, dict[str, object]]:
        env = kwargs.get("env")
        assert isinstance(env, dict)
        codex_home = Path(str(env["CODEX_HOME"]))
        config = tomllib.loads((codex_home / "config.toml").read_text(encoding="utf-8"))
        servers = config.get("mcp_servers")
        if not isinstance(servers, dict):
            return {}
        return {
            str(name): server
            for name, server in servers.items()
            if isinstance(name, str) and isinstance(server, dict)
        }

    @staticmethod
    def _auth_status_for(server: dict[str, object]) -> str:
        if isinstance(server.get("url"), str):
            return "not_logged_in"
        return "unsupported"

    @staticmethod
    def _render_transport(server: dict[str, object]) -> dict[str, object]:
        if isinstance(server.get("url"), str):
            return {
                "type": "streamable_http",
                "url": server["url"],
                "bearer_token_env_var": server.get("bearer_token_env_var"),
                "http_headers": server.get("http_headers"),
                "env_http_headers": server.get("env_http_headers"),
            }
        raw_args = server.get("args")
        args = raw_args if isinstance(raw_args, list) else []
        raw_env_vars = server.get("env_vars")
        env_vars = raw_env_vars if isinstance(raw_env_vars, list) else []
        return {
            "type": "stdio",
            "command": server.get("command"),
            "args": args,
            "env": server.get("env"),
            "env_vars": env_vars,
            "cwd": server.get("cwd"),
        }


class _DirtyGuardedRepoCodexRun(_FakeCodexRun):
    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_home = Path(command[command.index("-C") + 1])
        repo_dir = run_home / "repos" / "demo_repo"
        (repo_dir / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        return super().__call__(command, **kwargs)


class _FakeClaudeRun:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[0] != "claude":
            executable = command[0]
            if executable.startswith("missing-"):
                raise FileNotFoundError(executable)
            raise subprocess.TimeoutExpired(cmd=command, timeout=float(kwargs["timeout"]))
        response = self._responses[len(self.calls)]
        self.calls.append({"command": command, "kwargs": kwargs})
        session_id = str(response["session_id"])
        stdout_lines = response.get("stdout_lines")
        if isinstance(stdout_lines, list):
            stdout = "".join(json.dumps(line) + "\n" for line in stdout_lines)
        else:
            event_lines: list[dict[str, object]] = [
                {
                    "type": "system",
                    "subtype": "init",
                    "session_id": session_id,
                }
            ]
            assistant_text = response.get("assistant_text")
            if isinstance(assistant_text, str) and assistant_text:
                event_lines.append(
                    {
                        "type": "assistant",
                        "session_id": session_id,
                        "message": {
                            "content": [{"type": "text", "text": assistant_text}],
                        },
                    }
                )
            event_lines.append(
                {
                    "type": "result",
                    "session_id": session_id,
                    "usage": {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "cache_read_input_tokens": 0,
                    },
                    "structured_output": response["structured_output"],
                }
            )
            stdout = "".join(json.dumps(line) + "\n" for line in event_lines)
        return subprocess.CompletedProcess(
            args=command,
            returncode=int(response.get("returncode", 0)),
            stdout=stdout,
            stderr=str(response.get("stderr", "")),
        )


class _FakeTtyStream(io.StringIO):
    def isatty(self) -> bool:
        return True


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


if __name__ == "__main__":
    unittest.main()
