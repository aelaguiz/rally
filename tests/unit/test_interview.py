from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

import yaml

from rally.adapters.base import record_adapter_session
from rally.domain.flow import (
    AdapterConfig,
    CompiledAgentContract,
    FinalOutputContract,
    FlowAgent,
    FlowDefinition,
    FlowHostInputs,
)
from rally.domain.interview import InterviewRequest
from rally.domain.run import RunRecord, RunState, RunStatus
from rally.errors import RallyUsageError
from rally.services.interview import run_interview
from rally.services.run_store import create_run, load_run_state, write_run_state
from rally.services.workspace import workspace_context_from_root


class InterviewServiceTests(unittest.TestCase):
    def test_run_interview_writes_artifacts_and_reuses_diagnostic_session_for_claude(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow, agent = _demo_flow(repo_root=repo_root)
            record = create_run(repo_root=repo_root, flow=flow)
            run_home = _prepare_run_home(repo_root=repo_root, run_record=record, agent_slug=agent.slug)
            live_session = record_adapter_session(
                run_home=run_home,
                agent_slug=agent.slug,
                session_id="live-session-1",
                cwd=run_home,
            )
            live_session_text = (run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8")
            launch_seen: list[bool] = []

            def _assert_launch_before_call(command: list[str], kwargs: dict[str, object], call_index: int) -> None:
                del command, kwargs
                if call_index == 0:
                    launch_file = run_home / "interviews" / agent.slug / "interview-001" / "launch.json"
                    launch_seen.append(launch_file.is_file())

            fake_run = _FakeClaudeRun(
                [
                    {"session_id": "claude-diagnostic-1", "assistant_text": "The routing rule is hard to follow."},
                    {"session_id": "claude-diagnostic-1", "assistant_text": "The blocker text is a bit vague."},
                ],
                on_call=_assert_launch_before_call,
            )
            output = io.StringIO()

            with (
                patch("rally.services.interview.sync_workspace_builtins"),
                patch("rally.services.interview.ensure_flow_assets_built"),
                patch("rally.services.interview.load_flow_definition", return_value=flow),
                patch("rally.services.interview.prepare_interview_home", return_value=run_home),
            ):
                result = run_interview(
                    workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                    request=InterviewRequest(run_id=record.id),
                    input_stream=io.StringIO("What is confusing?\nAnything else?\n/exit\n"),
                    output_stream=output,
                    subprocess_run=fake_run,
                )

            interview_dir = run_home / "interviews" / agent.slug / "interview-001"
            transcript_lines = [
                json.loads(line)
                for line in (interview_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            session_payload = yaml.safe_load((interview_dir / "session.yaml").read_text(encoding="utf-8"))
            launch_payload = json.loads((interview_dir / "launch.json").read_text(encoding="utf-8"))
            prompt_text = (interview_dir / "prompt.md").read_text(encoding="utf-8")
            raw_events_text = (interview_dir / "raw_events.jsonl").read_text(encoding="utf-8")
            interview_events = _load_interview_events(repo_root=repo_root, run_id=record.id)

            self.assertEqual(result.interview_id, "interview-001")
            self.assertEqual(result.mode, "fresh")
            self.assertIn("Closed fresh interview `interview-001`", result.message)
            self.assertIn("Rally Interview", output.getvalue())
            self.assertIn("agent> The routing rule is hard to follow.", output.getvalue())
            self.assertIn("Type `/exit` to stop.", output.getvalue())
            self.assertEqual(launch_seen, [True])
            self.assertEqual(session_payload["diagnostic_session_id"], "claude-diagnostic-1")
            self.assertIsNone(session_payload["source_session_id"])
            self.assertEqual(session_payload["mode"], "fresh")
            self.assertTrue((interview_dir / "stderr.log").is_file())
            self.assertIn("Mode: `fresh`", prompt_text)
            self.assertIn("Boundary: Do not change the live run.", prompt_text)
            self.assertIn("You are in interview mode", prompt_text)
            self.assertEqual([entry["role"] for entry in transcript_lines], ["user", "assistant", "user", "assistant"])
            self.assertEqual(transcript_lines[1]["session_id"], "claude-diagnostic-1")
            self.assertIn('"type": "assistant"', raw_events_text)
            self.assertEqual(launch_payload["mode"], "fresh")
            self.assertEqual(launch_payload["env"]["RALLY_RUN_ID"], record.id)
            self.assertEqual(fake_run.calls[0]["command"][0], "claude")
            self.assertIn("--bare", fake_run.calls[0]["command"])
            self.assertIn("--include-partial-messages", fake_run.calls[0]["command"])
            self.assertIn("--system-prompt", fake_run.calls[0]["command"])
            self.assertNotIn("--resume", fake_run.calls[0]["command"])
            self.assertEqual(fake_run.calls[0]["kwargs"]["input"], "What is confusing?")
            self.assertIn("--resume", fake_run.calls[1]["command"])
            self.assertNotIn("--system-prompt", fake_run.calls[1]["command"])
            resume_index = fake_run.calls[1]["command"].index("--resume")
            self.assertEqual(fake_run.calls[1]["command"][resume_index + 1], "claude-diagnostic-1")
            self.assertEqual(
                [event["code"] for event in interview_events],
                ["USER", "LAUNCH", "ASSIST", "USER", "ASSIST", "CLOSE"],
            )
            self.assertEqual(interview_events[1]["data"]["interview_id"], "interview-001")
            self.assertEqual((run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8"), live_session_text)
            self.assertEqual(live_session.session_id, "live-session-1")

    def test_run_interview_rejects_missing_current_agent_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow, agent = _demo_flow(repo_root=repo_root)
            record = create_run(repo_root=repo_root, flow=flow)
            run_dir = repo_root / "runs" / "active" / record.id
            state = load_run_state(run_dir=run_dir)
            write_run_state(
                run_dir=run_dir,
                state=RunState(
                    status=RunStatus.DONE,
                    current_agent_key=None,
                    current_agent_slug=None,
                    turn_index=state.turn_index,
                    updated_at=state.updated_at,
                ),
            )
            run_home = _prepare_run_home(repo_root=repo_root, run_record=record, agent_slug=agent.slug)

            with (
                patch("rally.services.interview.sync_workspace_builtins"),
                patch("rally.services.interview.ensure_flow_assets_built"),
                patch("rally.services.interview.load_flow_definition", return_value=flow),
                patch("rally.services.interview.prepare_interview_home", return_value=run_home),
            ):
                with self.assertRaisesRegex(RallyUsageError, "Pass `--agent <slug>`"):
                    run_interview(
                        workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                        request=InterviewRequest(run_id=record.id),
                        input_stream=io.StringIO("/exit\n"),
                        output_stream=io.StringIO(),
                    )

    def test_run_interview_forks_claude_session_without_touching_live_session_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow, agent = _demo_flow(repo_root=repo_root)
            record = create_run(repo_root=repo_root, flow=flow)
            run_home = _prepare_run_home(repo_root=repo_root, run_record=record, agent_slug=agent.slug)
            record_adapter_session(
                run_home=run_home,
                agent_slug=agent.slug,
                session_id="live-session-9",
                cwd=run_home,
            )
            live_session_text = (run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8")
            launch_seen: list[bool] = []

            def _assert_launch_before_call(command: list[str], kwargs: dict[str, object], call_index: int) -> None:
                del command, kwargs
                if call_index == 0:
                    launch_file = run_home / "interviews" / agent.slug / "interview-001" / "launch.json"
                    launch_seen.append(launch_file.is_file())

            fake_run = _FakeClaudeRun(
                [
                    {"session_id": "forked-diagnostic-1", "assistant_text": "The live thread stopped after the handoff."},
                ],
                on_call=_assert_launch_before_call,
            )

            with (
                patch("rally.services.interview.sync_workspace_builtins"),
                patch("rally.services.interview.ensure_flow_assets_built"),
                patch("rally.services.interview.load_flow_definition", return_value=flow),
                patch("rally.services.interview.prepare_interview_home", return_value=run_home),
            ):
                result = run_interview(
                    workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                    request=InterviewRequest(run_id=record.id, fork=True),
                    input_stream=io.StringIO("Why did you stop?\n/exit\n"),
                    output_stream=io.StringIO(),
                    subprocess_run=fake_run,
                )

            interview_dir = run_home / "interviews" / agent.slug / "interview-001"
            session_payload = yaml.safe_load((interview_dir / "session.yaml").read_text(encoding="utf-8"))
            interview_events = _load_interview_events(repo_root=repo_root, run_id=record.id)

            self.assertEqual(result.mode, "fork")
            self.assertEqual(launch_seen, [True])
            self.assertEqual(session_payload["mode"], "fork")
            self.assertEqual(session_payload["source_session_id"], "live-session-9")
            self.assertEqual(session_payload["diagnostic_session_id"], "forked-diagnostic-1")
            self.assertEqual((run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8"), live_session_text)
            self.assertIn("--fork-session", fake_run.calls[0]["command"])
            resume_index = fake_run.calls[0]["command"].index("--resume")
            self.assertEqual(fake_run.calls[0]["command"][resume_index + 1], "live-session-9")
            self.assertEqual(interview_events[1]["code"], "LAUNCH")
            self.assertEqual(interview_events[1]["data"]["source_session_id"], "live-session-9")
            self.assertEqual(interview_events[-1]["code"], "CLOSE")

    def test_run_interview_streams_claude_reply_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow, agent = _demo_flow(repo_root=repo_root)
            record = create_run(repo_root=repo_root, flow=flow)
            run_home = _prepare_run_home(repo_root=repo_root, run_record=record, agent_slug=agent.slug)
            launch_seen: list[bool] = []
            fake_process = _FakeClaudeProcess(
                stdout_lines=[
                    {"type": "system", "subtype": "init", "session_id": "claude-diagnostic-1"},
                    {
                        "type": "stream_event",
                        "session_id": "claude-diagnostic-1",
                        "subtype": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "The routing "},
                    },
                    {
                        "type": "stream_event",
                        "session_id": "claude-diagnostic-1",
                        "subtype": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "rule is hard to follow."},
                    },
                    {
                        "type": "assistant",
                        "session_id": "claude-diagnostic-1",
                        "message": {
                            "content": [{"type": "text", "text": "The routing rule is hard to follow."}],
                        },
                    },
                    {"type": "result", "session_id": "claude-diagnostic-1", "usage": {"input_tokens": 1, "output_tokens": 1}},
                ]
            )
            fake_popen = _FakeClaudePopenFactory(
                fake_process,
                on_call=lambda command, kwargs: launch_seen.append(
                    (run_home / "interviews" / agent.slug / "interview-001" / "launch.json").is_file()
                ),
            )
            output = io.StringIO()

            with (
                patch("rally.services.interview.sync_workspace_builtins"),
                patch("rally.services.interview.ensure_flow_assets_built"),
                patch("rally.services.interview.load_flow_definition", return_value=flow),
                patch("rally.services.interview.prepare_interview_home", return_value=run_home),
            ):
                run_interview(
                    workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                    request=InterviewRequest(run_id=record.id),
                    input_stream=io.StringIO("What is confusing?\n/exit\n"),
                    output_stream=output,
                    claude_popen_factory=fake_popen,
                )

            rendered = output.getvalue()
            interview_events = _load_interview_events(repo_root=repo_root, run_id=record.id)
            self.assertEqual(launch_seen, [True])
            self.assertIn("agent> The routing rule is hard to follow.", rendered)
            self.assertEqual(rendered.count("agent> The routing rule is hard to follow."), 1)
            self.assertEqual([event["code"] for event in interview_events], ["USER", "LAUNCH", "ASSIST", "CLOSE"])

    def test_run_interview_writes_artifacts_and_reuses_diagnostic_thread_for_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow, agent = _demo_flow(
                repo_root=repo_root,
                adapter_name="codex",
                adapter_args={"model": "gpt-5.4", "reasoning_effort": "high", "project_doc_max_bytes": 0},
            )
            record = create_run(repo_root=repo_root, flow=flow)
            run_home = _prepare_run_home(repo_root=repo_root, run_record=record, agent_slug=agent.slug)
            record_adapter_session(
                run_home=run_home,
                agent_slug=agent.slug,
                session_id="live-thread-1",
                cwd=run_home,
            )
            live_session_text = (run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8")
            launch_seen: list[bool] = []
            fake_process = _FakeCodexAppServerProcess(
                stdout_lines=[
                    {"id": 1, "result": {}},
                    {"id": 2, "result": {"thread": {"id": "codex-diagnostic-1"}}},
                    {"method": "thread/started", "params": {"thread": {"id": "codex-diagnostic-1"}}},
                    {"id": 3, "result": {"turn": {"id": "turn-1"}}},
                    {"method": "turn/started", "params": {"threadId": "codex-diagnostic-1", "turn": {"id": "turn-1"}}},
                    {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turnId": "turn-1",
                            "itemId": "msg-1",
                            "delta": "The routing ",
                        },
                    },
                    {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turnId": "turn-1",
                            "itemId": "msg-1",
                            "delta": "rule is hard to follow.",
                        },
                    },
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turnId": "turn-1",
                            "item": {
                                "type": "agentMessage",
                                "id": "msg-1",
                                "text": "The routing rule is hard to follow.",
                            },
                        },
                    },
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turn": {"id": "turn-1", "status": "completed"},
                        },
                    },
                    {"id": 4, "result": {"turn": {"id": "turn-2"}}},
                    {"method": "turn/started", "params": {"threadId": "codex-diagnostic-1", "turn": {"id": "turn-2"}}},
                    {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turnId": "turn-2",
                            "itemId": "msg-2",
                            "delta": "The blocker text ",
                        },
                    },
                    {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turnId": "turn-2",
                            "itemId": "msg-2",
                            "delta": "is a bit vague.",
                        },
                    },
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turnId": "turn-2",
                            "item": {
                                "type": "agentMessage",
                                "id": "msg-2",
                                "text": "The blocker text is a bit vague.",
                            },
                        },
                    },
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "codex-diagnostic-1",
                            "turn": {"id": "turn-2", "status": "completed"},
                        },
                    },
                ]
            )
            fake_popen = _FakeCodexPopenFactory(
                fake_process,
                on_call=lambda command, kwargs: launch_seen.append(
                    (run_home / "interviews" / agent.slug / "interview-001" / "launch.json").is_file()
                ),
            )
            output = io.StringIO()

            with (
                patch("rally.services.interview.sync_workspace_builtins"),
                patch("rally.services.interview.ensure_flow_assets_built"),
                patch("rally.services.interview.load_flow_definition", return_value=flow),
                patch("rally.services.interview.prepare_interview_home", return_value=run_home),
            ):
                result = run_interview(
                    workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                    request=InterviewRequest(run_id=record.id),
                    input_stream=io.StringIO("What is confusing?\nAnything else?\n/exit\n"),
                    output_stream=output,
                    codex_popen_factory=fake_popen,
                )

            interview_dir = run_home / "interviews" / agent.slug / "interview-001"
            transcript_lines = [
                json.loads(line)
                for line in (interview_dir / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            session_payload = yaml.safe_load((interview_dir / "session.yaml").read_text(encoding="utf-8"))
            launch_payload = json.loads((interview_dir / "launch.json").read_text(encoding="utf-8"))
            prompt_text = (interview_dir / "prompt.md").read_text(encoding="utf-8")
            raw_events_text = (interview_dir / "raw_events.jsonl").read_text(encoding="utf-8")
            sent_messages = fake_process.sent_messages()
            interview_events = _load_interview_events(repo_root=repo_root, run_id=record.id)

            self.assertEqual(result.mode, "fresh")
            self.assertEqual(launch_seen, [True])
            self.assertEqual(session_payload["diagnostic_session_id"], "codex-diagnostic-1")
            self.assertIsNone(session_payload["source_session_id"])
            self.assertEqual(session_payload["mode"], "fresh")
            self.assertIn("agent> The routing rule is hard to follow.", output.getvalue())
            self.assertIn("agent> The blocker text is a bit vague.", output.getvalue())
            self.assertEqual(output.getvalue().count("agent> The routing rule is hard to follow."), 1)
            self.assertEqual(output.getvalue().count("agent> The blocker text is a bit vague."), 1)
            self.assertEqual([entry["role"] for entry in transcript_lines], ["user", "assistant", "user", "assistant"])
            self.assertEqual(transcript_lines[1]["session_id"], "codex-diagnostic-1")
            self.assertIn('"method": "turn/completed"', raw_events_text)
            self.assertEqual(launch_payload["mode"], "fresh")
            self.assertEqual(launch_payload["env"]["CODEX_HOME"], str(run_home.resolve()))
            self.assertEqual(fake_popen.calls[0]["command"], ["codex", "app-server", "--listen", "stdio://"])
            self.assertIn("You are in interview mode", prompt_text)
            self.assertEqual(sent_messages[0]["method"], "initialize")
            self.assertEqual(sent_messages[1]["method"], "initialized")
            self.assertEqual(sent_messages[2]["method"], "thread/start")
            self.assertEqual(sent_messages[2]["params"]["approvalPolicy"], "never")
            self.assertEqual(sent_messages[2]["params"]["sandbox"], "read-only")
            self.assertIn("You are in interview mode", sent_messages[2]["params"]["developerInstructions"])
            self.assertEqual(sent_messages[3]["method"], "turn/start")
            self.assertEqual(sent_messages[3]["params"]["threadId"], "codex-diagnostic-1")
            self.assertEqual(sent_messages[3]["params"]["input"][0]["text"], "What is confusing?")
            self.assertEqual(sent_messages[3]["params"]["sandboxPolicy"]["type"], "readOnly")
            self.assertEqual(sent_messages[4]["method"], "turn/start")
            self.assertEqual(sent_messages[4]["params"]["threadId"], "codex-diagnostic-1")
            self.assertEqual(sent_messages[4]["params"]["input"][0]["text"], "Anything else?")
            self.assertEqual(
                [event["code"] for event in interview_events],
                ["USER", "LAUNCH", "ASSIST", "USER", "ASSIST", "CLOSE"],
            )
            self.assertEqual((run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8"), live_session_text)
            self.assertTrue(fake_process.terminated)

    def test_run_interview_forks_codex_thread_without_touching_live_session_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve() / "rally"
            repo_root.mkdir(parents=True)
            (repo_root / "pyproject.toml").write_text("[project]\nname = 'rally'\n", encoding="utf-8")
            flow, agent = _demo_flow(
                repo_root=repo_root,
                adapter_name="codex",
                adapter_args={"model": "gpt-5.4", "reasoning_effort": "high", "project_doc_max_bytes": 0},
            )
            record = create_run(repo_root=repo_root, flow=flow)
            run_home = _prepare_run_home(repo_root=repo_root, run_record=record, agent_slug=agent.slug)
            record_adapter_session(
                run_home=run_home,
                agent_slug=agent.slug,
                session_id="live-thread-9",
                cwd=run_home,
            )
            live_session_text = (run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8")
            launch_seen: list[bool] = []
            fake_process = _FakeCodexAppServerProcess(
                stdout_lines=[
                    {"id": 1, "result": {}},
                    {"id": 2, "result": {"thread": {"id": "forked-diagnostic-1"}}},
                    {"method": "thread/started", "params": {"thread": {"id": "forked-diagnostic-1"}}},
                    {"id": 3, "result": {"turn": {"id": "turn-1"}}},
                    {"method": "turn/started", "params": {"threadId": "forked-diagnostic-1", "turn": {"id": "turn-1"}}},
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": "forked-diagnostic-1",
                            "turnId": "turn-1",
                            "item": {
                                "type": "agentMessage",
                                "id": "msg-1",
                                "text": "The live thread stopped after the handoff.",
                            },
                        },
                    },
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "forked-diagnostic-1",
                            "turn": {"id": "turn-1", "status": "completed"},
                        },
                    },
                    {"id": 4, "result": {"turn": {"id": "turn-2"}}},
                    {"method": "turn/started", "params": {"threadId": "forked-diagnostic-1", "turn": {"id": "turn-2"}}},
                    {
                        "method": "item/completed",
                        "params": {
                            "threadId": "forked-diagnostic-1",
                            "turnId": "turn-2",
                            "item": {
                                "type": "agentMessage",
                                "id": "msg-2",
                                "text": "It also kept the stale blocker note.",
                            },
                        },
                    },
                    {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "forked-diagnostic-1",
                            "turn": {"id": "turn-2", "status": "completed"},
                        },
                    },
                ]
            )
            fake_popen = _FakeCodexPopenFactory(
                fake_process,
                on_call=lambda command, kwargs: launch_seen.append(
                    (run_home / "interviews" / agent.slug / "interview-001" / "launch.json").is_file()
                ),
            )

            with (
                patch("rally.services.interview.sync_workspace_builtins"),
                patch("rally.services.interview.ensure_flow_assets_built"),
                patch("rally.services.interview.load_flow_definition", return_value=flow),
                patch("rally.services.interview.prepare_interview_home", return_value=run_home),
            ):
                result = run_interview(
                    workspace=workspace_context_from_root(repo_root, cli_bin=repo_root / "bin" / "rally"),
                    request=InterviewRequest(run_id=record.id, fork=True),
                    input_stream=io.StringIO("Why did you stop?\nAnything else?\n/exit\n"),
                    output_stream=io.StringIO(),
                    codex_popen_factory=fake_popen,
                )

            interview_dir = run_home / "interviews" / agent.slug / "interview-001"
            session_payload = yaml.safe_load((interview_dir / "session.yaml").read_text(encoding="utf-8"))
            sent_messages = fake_process.sent_messages()
            interview_events = _load_interview_events(repo_root=repo_root, run_id=record.id)

            self.assertEqual(result.mode, "fork")
            self.assertEqual(launch_seen, [True])
            self.assertEqual(session_payload["mode"], "fork")
            self.assertEqual(session_payload["source_session_id"], "live-thread-9")
            self.assertEqual(session_payload["diagnostic_session_id"], "forked-diagnostic-1")
            self.assertEqual(sent_messages[2]["method"], "thread/fork")
            self.assertEqual(sent_messages[2]["params"]["threadId"], "live-thread-9")
            self.assertIn("You are in interview mode", sent_messages[2]["params"]["developerInstructions"])
            self.assertEqual(sent_messages[3]["params"]["threadId"], "forked-diagnostic-1")
            self.assertEqual(sent_messages[4]["params"]["threadId"], "forked-diagnostic-1")
            self.assertEqual(interview_events[1]["code"], "LAUNCH")
            self.assertEqual(interview_events[1]["data"]["source_session_id"], "live-thread-9")
            self.assertEqual(interview_events[-1]["code"], "CLOSE")
            self.assertEqual((run_home / "sessions" / agent.slug / "session.yaml").read_text(encoding="utf-8"), live_session_text)
            self.assertTrue(fake_process.terminated)


def _demo_flow(
    *,
    repo_root: Path,
    adapter_name: str = "claude_code",
    adapter_args: dict[str, object] | None = None,
) -> tuple[FlowDefinition, FlowAgent]:
    flow_root = repo_root / "flows" / "demo"
    flow_root.mkdir(parents=True, exist_ok=True)
    prompt_path = flow_root / "prompts" / "AGENTS.prompt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("prompt source\n", encoding="utf-8")
    agent_dir = flow_root / "build" / "agents" / "scope_lead"
    agent_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = agent_dir / "AGENTS.md"
    markdown_path.write_text("compiled agent\n", encoding="utf-8")
    (agent_dir / "INTERVIEW.md").write_text(
        "You are in interview mode for a Rally agent.\nStay in interview mode.\n",
        encoding="utf-8",
    )
    contract_path = agent_dir / "AGENTS.contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    schema_file = repo_root / "stdlib" / "rally" / "schemas" / "rally_turn_result.schema.json"
    example_file = repo_root / "stdlib" / "rally" / "examples" / "rally_turn_result.example.json"
    schema_file.parent.mkdir(parents=True, exist_ok=True)
    example_file.parent.mkdir(parents=True, exist_ok=True)
    schema_file.write_text("{}", encoding="utf-8")
    example_file.write_text("{}", encoding="utf-8")
    final_output = FinalOutputContract(
        exists=True,
        declaration_key="DemoTurnResult",
        declaration_name="DemoTurnResult",
        format_mode="json_schema",
        schema_profile="OpenAIStructuredOutput",
        schema_file=schema_file,
        example_file=example_file,
    )
    agent = FlowAgent(
        key="01_scope_lead",
        slug="scope_lead",
        timeout_sec=60,
        allowed_skills=(),
        allowed_mcps=(),
        compiled=CompiledAgentContract(
            name="ScopeLead",
            slug="scope_lead",
            entrypoint=prompt_path,
            markdown_path=markdown_path,
            contract_path=contract_path,
            contract_version=1,
            final_output=final_output,
        ),
    )
    flow = FlowDefinition(
        name="demo",
        code="DMO",
        root_dir=flow_root,
        flow_file=flow_root / "flow.yaml",
        prompt_entrypoint=prompt_path,
        build_agents_dir=flow_root / "build" / "agents",
        setup_home_script=None,
        start_agent_key=agent.key,
        max_command_turns=8,
        guarded_git_repos=(),
        runtime_env={},
        host_inputs=FlowHostInputs(required_env=(), required_files=(), required_directories=()),
        agents={agent.key: agent},
        adapter=AdapterConfig(
            name=adapter_name,
            prompt_input_command=None,
            args=adapter_args or {"model": "sonnet", "reasoning_effort": "high"},
        ),
    )
    return flow, agent


def _prepare_run_home(*, repo_root: Path, run_record: RunRecord, agent_slug: str) -> Path:
    run_home = repo_root / "runs" / "active" / run_record.id / "home"
    (run_home / "agents" / agent_slug).mkdir(parents=True, exist_ok=True)
    (run_home / "interviews").mkdir(parents=True, exist_ok=True)
    (run_home / "sessions" / agent_slug).mkdir(parents=True, exist_ok=True)
    source_agent_dir = repo_root / "flows" / "demo" / "build" / "agents" / agent_slug
    for name in ("AGENTS.md", "INTERVIEW.md", "AGENTS.contract.json"):
        (run_home / "agents" / agent_slug / name).write_text(
            (source_agent_dir / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return run_home


class _FakeClaudeRun:
    def __init__(
        self,
        responses: list[dict[str, object]],
        on_call: Callable[[list[str], dict[str, object], int], None] | None = None,
    ) -> None:
        self._responses = responses
        self._on_call = on_call
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        response = self._responses[len(self.calls)]
        self.calls.append({"command": command, "kwargs": kwargs})
        if self._on_call is not None:
            self._on_call(command, kwargs, len(self.calls) - 1)
        session_id = str(response["session_id"])
        event_lines = [
            {
                "type": "system",
                "subtype": "init",
                "session_id": session_id,
            },
            {
                "type": "assistant",
                "session_id": session_id,
                "message": {
                    "content": [{"type": "text", "text": str(response.get("assistant_text", ""))}],
                },
            },
            {
                "type": "result",
                "session_id": session_id,
                "usage": {
                    "input_tokens": 1,
                    "output_tokens": 1,
                },
            },
        ]
        stdout = "".join(json.dumps(line) + "\n" for line in event_lines)
        return subprocess.CompletedProcess(
            args=command,
            returncode=int(response.get("returncode", 0)),
            stdout=stdout,
            stderr=str(response.get("stderr", "")),
        )


class _FakeClaudePopenFactory:
    def __init__(self, process: "_FakeClaudeProcess", on_call: Callable[[list[str], dict[str, object]], None] | None = None) -> None:
        self._process = process
        self._on_call = on_call
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> "_FakeClaudeProcess":
        self.calls.append({"command": command, "kwargs": kwargs})
        if self._on_call is not None:
            self._on_call(command, kwargs)
        self._process.launch_command = command
        self._process.launch_kwargs = kwargs
        return self._process


class _FakeClaudeProcess:
    def __init__(self, *, stdout_lines: list[dict[str, object]], stderr_text: str = "") -> None:
        self.stdin = _RecordingPipe()
        self.stdout = io.StringIO("".join(json.dumps(line) + "\n" for line in stdout_lines))
        self.stderr = io.StringIO(stderr_text)
        self.returncode = 0
        self.launch_command: list[str] | None = None
        self.launch_kwargs: dict[str, object] | None = None

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


class _FakeCodexPopenFactory:
    def __init__(
        self,
        process: "_FakeCodexAppServerProcess",
        on_call: Callable[[list[str], dict[str, object]], None] | None = None,
    ) -> None:
        self._process = process
        self._on_call = on_call
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> "_FakeCodexAppServerProcess":
        self.calls.append({"command": command, "kwargs": kwargs})
        if self._on_call is not None:
            self._on_call(command, kwargs)
        self._process.launch_command = command
        self._process.launch_kwargs = kwargs
        return self._process


class _FakeCodexAppServerProcess:
    def __init__(self, *, stdout_lines: list[dict[str, object]], stderr_text: str = "") -> None:
        self.stdin = _RecordingPipe()
        self.stdout = io.StringIO("".join(json.dumps(line) + "\n" for line in stdout_lines))
        self.stderr = io.StringIO(stderr_text)
        self.returncode: int | None = None
        self.terminated = False
        self.launch_command: list[str] | None = None
        self.launch_kwargs: dict[str, object] | None = None

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        if self.returncode is None:
            self.returncode = 0

    def kill(self) -> None:
        self.terminated = True
        self.returncode = -9

    def sent_messages(self) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in self.stdin.getvalue().splitlines()
            if line.strip()
        ]


class _RecordingPipe:
    def __init__(self) -> None:
        self._chunks: list[str] = []
        self.closed = False

    def write(self, text: str) -> int:
        self._chunks.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    def getvalue(self) -> str:
        return "".join(self._chunks)


def _load_interview_events(*, repo_root: Path, run_id: str) -> list[dict[str, object]]:
    events_file = repo_root / "runs" / "active" / run_id / "logs" / "events.jsonl"
    return [
        payload
        for payload in (
            json.loads(line)
            for line in events_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if payload.get("source") == "interview"
    ]


if __name__ == "__main__":
    unittest.main()
