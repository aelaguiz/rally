from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.adapters.codex.launcher import build_codex_launch_env
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
            )

            self.assertEqual(env["CODEX_HOME"], str(run_home.resolve()))
            self.assertEqual(env["RALLY_BASE_DIR"], str(repo_root.resolve()))
            self.assertEqual(env["RALLY_RUN_ID"], "FLW-1")
            self.assertEqual(env["RALLY_FLOW_CODE"], "FLW")

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
                )


if __name__ == "__main__":
    unittest.main()
