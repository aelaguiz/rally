from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from rally.domain.run import ResumeRequest, RunRequest, RunStatus
from rally.errors import RallyConfigError, RallyUsageError
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
            self.assertFalse((run_dir / "home" / "operator_brief.md").exists())
            self.assertIn("Fix the pagination bug.", issue_text)
            self.assertIn("Rally Run Started", issue_text)
            self.assertIn("Rally Turn Result", issue_text)
            self.assertIn("Rally Done", issue_text)
            self.assertIn("## Rally Run Started\n- Run ID: `DMO-1`\n- Time:", issue_text)
            self.assertIn("## Rally Turn Result\n- Run ID: `DMO-1`\n- Turn: `1`", issue_text)
            self.assertIn("## Rally Done\n- Run ID: `DMO-1`\n- Turn: `2`", issue_text)
            self.assertIn("\n---\n\n## Rally Turn Result", issue_text)
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
                            "verdict": "accept",
                            "reviewed_artifact": "artifacts/poem.md",
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
            self.assertIn("## Skills", prompt_text)
            self.assertIn("### rally-kernel", prompt_text)
            self.assertIn("### Issue Note", prompt_text)
            self.assertNotIn("\n### Writer Issue Note\n", prompt_text)
            self.assertIn("Use the shared `rally-kernel` skill for that note.", prompt_text)
            self.assertIn('Append With: `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`', prompt_text)
            self.assertIn("Artistic Rationale", prompt_text)
            self.assertIn("### Rally Turn Result", prompt_text)
            self.assertNotIn("\n### Writer Turn Result\n", prompt_text)
            self.assertIn("## Rally Note", issue_text)
            self.assertIn("- Source: `rally runtime review`", issue_text)
            self.assertIn("### Findings First", issue_text)
            self.assertIn("The poem is ready to keep as written.", issue_text)

    def test_resume_run_passes_workspace_dir_to_prompt_input_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_path.write_text(
                flow_text.replace(
                    "  adapter_args:\n",
                    "  prompt_input_command: setup/prompt_inputs.py\n  adapter_args:\n",
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

            with patch("rally.services.runner.subprocess.run", side_effect=prompt_input_run):
                result = resume_run(
                    repo_root=repo_root,
                    request=ResumeRequest(run_id="DMO-1"),
                    subprocess_run=fake_run,
                )

            prompt_text = fake_run.calls[0]["kwargs"]["input"]
            self.assertEqual(result.status, RunStatus.DONE)
            self.assertEqual(captured_env["RALLY_WORKSPACE_DIR"], str(repo_root))
            self.assertIn(str(repo_root), prompt_text)

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
            flow_text = flow_text.replace("    project_doc_max_bytes: 0\n", "    project_doc_max_bytes: 2048\n")
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
            self.assertTrue((run_dir / "home" / "mcps" / "fixture-repo" / "server.toml").is_file())
            config_text = (run_dir / "home" / "config.toml").read_text(encoding="utf-8")
            self.assertIn("project_doc_max_bytes = 2048", config_text)
            self.assertIn('[mcp_servers."fixture-repo"]', config_text)
            self.assertIn('command = ["uv", "run", "fixture-repo"]', config_text)

    def test_resume_run_removes_stale_run_home_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root, max_command_turns=1)
            self._write_fixture_repo_mcp(repo_root=repo_root)

            flow_path = repo_root / "flows" / "demo" / "flow.yaml"
            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_mcps: []\n", "    allowed_mcps: [fixture-repo]\n")
            flow_text = flow_text.replace("    project_doc_max_bytes: 0\n", "    project_doc_max_bytes: 512\n")
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
            self.assertTrue((run_dir / "home" / "mcps" / "fixture-repo" / "server.toml").is_file())

            flow_text = flow_path.read_text(encoding="utf-8")
            flow_text = flow_text.replace("    allowed_skills: [repo-search]\n", "    allowed_skills: []\n")
            flow_text = flow_text.replace("    allowed_mcps: [fixture-repo]\n", "    allowed_mcps: []\n")
            flow_text = flow_text.replace("    project_doc_max_bytes: 512\n", "    project_doc_max_bytes: 0\n")
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

    def test_resume_run_blocks_before_setup_when_required_host_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            missing_file = (repo_root / "missing.env").resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_files=[str(missing_file)],
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
            self.assertIn(str(missing_file), rendered_text)

    def test_resume_run_blocks_before_setup_when_required_host_directory_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            missing_directory = (repo_root / "missing-dir").resolve()
            self._write_demo_repo(
                repo_root=repo_root,
                with_setup_script=True,
                required_directories=[str(missing_directory)],
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
            self.assertIn(str(missing_directory), rendered_text)

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
        shutil.copytree(source_root / "skills" / "rally-kernel", repo_root / "skills" / "rally-kernel")
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

        setup_home_line = "setup_home_script: setup/prepare_home.sh\n" if (with_setup_script or with_guarded_repo) else ""
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
        guarded_git_repos_line = "  guarded_git_repos: [repos/demo_repo]\n" if with_guarded_repo else ""
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

    def _write_fixture_repo_mcp(self, *, repo_root: Path) -> None:
        (repo_root / "mcps" / "fixture-repo").mkdir(parents=True)
        (repo_root / "mcps" / "fixture-repo" / "server.toml").write_text(
            textwrap.dedent(
                """\
                command = ["uv", "run", "fixture-repo"]
                cwd = "/tmp/fixture-repo"
                """
            ),
            encoding="utf-8",
        )

    def _write_poem_repo(self, *, repo_root: Path) -> None:
        source_root = Path(__file__).resolve().parents[2]
        shutil.copytree(source_root / "flows" / "poem_loop", repo_root / "flows" / "poem_loop")
        shutil.copytree(source_root / "skills" / "rally-kernel", repo_root / "skills" / "rally-kernel")
        shutil.copytree(source_root / "stdlib" / "rally", repo_root / "stdlib" / "rally")

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


class _DirtyGuardedRepoCodexRun(_FakeCodexRun):
    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        run_home = Path(command[command.index("-C") + 1])
        repo_dir = run_home / "repos" / "demo_repo"
        (repo_dir / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        return super().__call__(command, **kwargs)


class _FakeTtyStream(io.StringIO):
    def isatty(self) -> bool:
        return True


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


if __name__ == "__main__":
    unittest.main()
