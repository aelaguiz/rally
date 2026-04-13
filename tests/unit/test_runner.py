from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from dataclasses import replace
from pathlib import Path

from rally.errors import RallyConfigError
from rally.domain.run import ResumeRequest, RunRequest, RunStatus
from rally.services.run_store import find_run_dir, load_run_state, write_run_state
from rally.services.runner import resume_run, run_flow


class RunnerTests(unittest.TestCase):
    def test_run_flow_creates_active_run_and_handoff_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            brief_file = repo_root / "brief.md"
            brief_file.write_text("Fix the pagination bug.\n", encoding="utf-8")

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

            result = run_flow(
                repo_root=repo_root,
                request=RunRequest(flow_name="demo", brief_file=brief_file),
                subprocess_run=fake_run,
            )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")
            session_text = (run_dir / "home" / "sessions" / "scope_lead" / "session.yaml").read_text(
                encoding="utf-8"
            )

            self.assertEqual(result.run_id, "DMO-1")
            self.assertEqual(result.status, RunStatus.RUNNING)
            self.assertEqual(result.current_agent_key, "02_change_engineer")
            self.assertEqual(state.current_agent_key, "02_change_engineer")
            self.assertEqual(state.turn_index, 1)
            self.assertIn("Rally Run Started", issue_text)
            self.assertIn("Rally Turn Result", issue_text)
            self.assertIn("session-1", session_text)
            self.assertIn("--output-schema", fake_run.calls[0]["command"])
            self.assertIn("-C", fake_run.calls[0]["command"])
            self.assertIn(
                "--dangerously-bypass-approvals-and-sandbox",
                fake_run.calls[0]["command"],
            )

    def test_resume_run_uses_saved_session_and_finishes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            brief_file = repo_root / "brief.md"
            brief_file.write_text("Fix the pagination bug.\n", encoding="utf-8")

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

            first = run_flow(
                repo_root=repo_root,
                request=RunRequest(flow_name="demo", brief_file=brief_file),
                subprocess_run=fake_run,
            )
            self.assertEqual(first.status, RunStatus.SLEEPING)

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            sleeping_state = load_run_state(run_dir=run_dir)
            write_run_state(
                run_dir=run_dir,
                state=replace(sleeping_state, sleep_until="2000-01-01T00:00:00Z"),
            )

            resumed = resume_run(
                repo_root=repo_root,
                request=ResumeRequest(run_id="DMO-1"),
                subprocess_run=fake_run,
            )

            state = load_run_state(run_dir=run_dir)
            self.assertEqual(resumed.status, RunStatus.DONE)
            self.assertEqual(state.status, RunStatus.DONE)
            self.assertIn("resume", fake_run.calls[1]["command"])
            self.assertIn("session-1", fake_run.calls[1]["command"])

    def test_run_flow_rejects_skill_without_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            brief_file = repo_root / "brief.md"
            brief_file.write_text("Fix the pagination bug.\n", encoding="utf-8")
            (repo_root / "skills" / "repo-search" / "SKILL.md").write_text(
                "# Repo Search\n",
                encoding="utf-8",
            )

            with self.assertRaises(RallyConfigError):
                run_flow(
                    repo_root=repo_root,
                    request=RunRequest(flow_name="demo", brief_file=brief_file),
                    subprocess_run=_FakeCodexRun([]),
                )

    def test_run_flow_blocks_when_codex_times_out(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_demo_repo(repo_root=repo_root)
            brief_file = repo_root / "brief.md"
            brief_file.write_text("Fix the pagination bug.\n", encoding="utf-8")

            result = run_flow(
                repo_root=repo_root,
                request=RunRequest(flow_name="demo", brief_file=brief_file),
                subprocess_run=_TimeoutCodexRun(),
            )

            run_dir = find_run_dir(repo_root=repo_root, run_id="DMO-1")
            state = load_run_state(run_dir=run_dir)
            issue_text = (run_dir / "home" / "issue.md").read_text(encoding="utf-8")

            self.assertEqual(result.status, RunStatus.BLOCKED)
            self.assertEqual(state.status, RunStatus.BLOCKED)
            self.assertIn("timed out", state.blocker_reason or "")
            self.assertIn("Rally Blocked", issue_text)

    def _write_demo_repo(self, *, repo_root: Path) -> None:
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
        (flow_root / "flow.yaml").write_text(
            textwrap.dedent(
                """\
                name: demo
                code: DMO
                start_agent: 01_scope_lead
                agents:
                  01_scope_lead:
                    timeout_sec: 60
                    allowed_skills: [repo-search]
                    allowed_mcps: []
                  02_change_engineer:
                    timeout_sec: 60
                    allowed_skills: [repo-search]
                    allowed_mcps: []
                runtime:
                  adapter: codex
                  adapter_args:
                    model: gpt-5.4
                    reasoning_effort: medium
                    project_doc_max_bytes: 0
                """
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

        output_path = Path(command[command.index("-o") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(response["last_message"]) + "\n", encoding="utf-8")

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


class _TimeoutCodexRun:
    def __call__(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=float(kwargs["timeout"]),
            output='{"type":"thread.started","thread_id":"session-timeout"}\n',
            stderr="partial stderr",
        )


if __name__ == "__main__":
    unittest.main()
