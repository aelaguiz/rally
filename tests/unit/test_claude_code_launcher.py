from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rally.adapters.claude_code.launcher import build_claude_code_launch_env, write_claude_code_launch_record
from rally.errors import RallyStateError


class ClaudeCodeLauncherTests(unittest.TestCase):
    def test_build_claude_code_launch_env_sets_rally_env_and_disables_claude_ai_mcps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()

            env = build_claude_code_launch_env(
                workspace_dir=repo_root,
                cli_bin=repo_root / "bin" / "rally",
                run_id="FLW-1",
                flow_code="FLW",
                agent_slug="scope_lead",
                turn_index=2,
            )

            self.assertEqual(env["RALLY_RUN_ID"], "FLW-1")
            self.assertEqual(env["RALLY_FLOW_CODE"], "FLW")
            self.assertEqual(env["RALLY_AGENT_SLUG"], "scope_lead")
            self.assertEqual(env["RALLY_TURN_NUMBER"], "2")
            self.assertEqual(env["RALLY_WORKSPACE_DIR"], str(repo_root.resolve()))
            self.assertEqual(env["ENABLE_CLAUDEAI_MCP_SERVERS"], "false")

    def test_build_claude_code_launch_env_rejects_blank_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()

            with self.assertRaisesRegex(RallyStateError, "Run id must not be empty"):
                build_claude_code_launch_env(
                    workspace_dir=repo_root,
                    cli_bin=repo_root / "bin" / "rally",
                    run_id="",
                    flow_code="FLW",
                    agent_slug="scope_lead",
                    turn_index=1,
                )

    def test_write_claude_code_launch_record_keeps_only_rally_and_clamped_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "FLW-1"
            run_dir.mkdir(parents=True)

            record_file = write_claude_code_launch_record(
                run_dir=run_dir,
                turn_index=2,
                agent_slug="scope_lead",
                command=["claude", "-p", "--output-format", "stream-json"],
                cwd=run_dir,
                env={
                    "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
                    "RALLY_RUN_ID": "FLW-1",
                    "RALLY_FLOW_CODE": "FLW",
                    "RALLY_TURN_NUMBER": "2",
                    "IGNORED": "value",
                },
                timeout_sec=60,
            )

            payload = json.loads(record_file.read_text(encoding="utf-8"))
            self.assertEqual(record_file.name, "turn-002-scope_lead.json")
            self.assertEqual(payload["command"], ["claude", "-p", "--output-format", "stream-json"])
            self.assertEqual(payload["timeout_sec"], 60)
            self.assertEqual(payload["env"]["ENABLE_CLAUDEAI_MCP_SERVERS"], "false")
            self.assertEqual(payload["env"]["RALLY_TURN_NUMBER"], "2")
            self.assertNotIn("IGNORED", payload["env"])


if __name__ == "__main__":
    unittest.main()
