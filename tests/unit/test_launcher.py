from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rally.adapters.codex.launcher import build_codex_launch_env, write_codex_launch_record
from rally.errors import RallyStateError


class LauncherTests(unittest.TestCase):
    def test_build_codex_launch_env_sets_rally_and_codex_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "FLW-1" / "home"
            run_home.mkdir(parents=True)

            env = build_codex_launch_env(
                repo_root=repo_root,
                run_home=run_home,
                run_id="FLW-1",
                flow_code="FLW",
                agent_slug="scope_lead",
                turn_index=2,
            )

            self.assertEqual(env["CODEX_HOME"], str(run_home.resolve()))
            self.assertEqual(env["RALLY_BASE_DIR"], str(repo_root.resolve()))
            self.assertEqual(env["RALLY_RUN_ID"], "FLW-1")
            self.assertEqual(env["RALLY_FLOW_CODE"], "FLW")
            self.assertEqual(env["RALLY_AGENT_SLUG"], "scope_lead")
            self.assertEqual(env["RALLY_TURN_NUMBER"], "2")

    def test_build_codex_launch_env_rejects_blank_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "FLW-1" / "home"
            run_home.mkdir(parents=True)

            with self.assertRaisesRegex(RallyStateError, "Run id must not be empty"):
                build_codex_launch_env(
                    repo_root=repo_root,
                    run_home=run_home,
                    run_id="",
                    flow_code="FLW",
                    agent_slug="scope_lead",
                    turn_index=1,
                )

    def test_build_codex_launch_env_rejects_blank_flow_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "FLW-1" / "home"
            run_home.mkdir(parents=True)

            with self.assertRaisesRegex(RallyStateError, "Flow code must not be empty"):
                build_codex_launch_env(
                    repo_root=repo_root,
                    run_home=run_home,
                    run_id="FLW-1",
                    flow_code="",
                    agent_slug="scope_lead",
                    turn_index=1,
                )

    def test_build_codex_launch_env_rejects_non_positive_turn_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            run_home = repo_root / "runs" / "FLW-1" / "home"
            run_home.mkdir(parents=True)

            with self.assertRaisesRegex(RallyStateError, "Turn index must be 1 or greater"):
                build_codex_launch_env(
                    repo_root=repo_root,
                    run_home=run_home,
                    run_id="FLW-1",
                    flow_code="FLW",
                    agent_slug="scope_lead",
                    turn_index=0,
                )

    def test_write_codex_launch_record_captures_command_and_rally_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "FLW-1"
            run_dir.mkdir(parents=True)

            record_file = write_codex_launch_record(
                run_dir=run_dir,
                turn_index=2,
                agent_slug="scope_lead",
                command=["codex", "exec", "--json"],
                cwd=run_dir,
                env={
                    "CODEX_HOME": str(run_dir / "home"),
                    "RALLY_RUN_ID": "FLW-1",
                    "RALLY_FLOW_CODE": "FLW",
                    "RALLY_TURN_NUMBER": "2",
                    "IGNORED": "value",
                },
                timeout_sec=60,
            )

            payload = json.loads(record_file.read_text(encoding="utf-8"))
            self.assertEqual(record_file.name, "turn-002-scope_lead.json")
            self.assertEqual(payload["command"], ["codex", "exec", "--json"])
            self.assertEqual(payload["timeout_sec"], 60)
            self.assertIn("CODEX_HOME", payload["env"])
            self.assertIn("RALLY_RUN_ID", payload["env"])
            self.assertEqual(payload["env"]["RALLY_TURN_NUMBER"], "2")
            self.assertNotIn("IGNORED", payload["env"])


if __name__ == "__main__":
    unittest.main()
