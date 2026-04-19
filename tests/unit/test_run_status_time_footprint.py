from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.services.run_status import show_status


class RunStatusTimeFootprintTests(unittest.TestCase):
    def test_time_footprint_present_when_timing_json_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="DMO-1")
            self._write_timing_json(
                repo_root=repo_root,
                run_id="DMO-1",
                wall_ms=12 * 60 * 1000,
                active_ms=5 * 60 * 1000,
                idle_ms=7 * 60 * 1000,
                top_tools=[
                    {"tool_name": "Bash", "count": 10, "total_ms": 180_000, "error_count": 0},
                ],
                tokens={"output_tokens": 8500, "cache_read_input_tokens": 640_000},
                errors=0,
            )

            result = show_status(repo_root=repo_root, run_id="DMO-1")

            self.assertIn("Time:", result.message)
            self.assertIn("wall", result.message)
            self.assertIn("active", result.message)
            self.assertIn("Tools:", result.message)
            self.assertIn("Bash", result.message)
            self.assertIn("Tokens:", result.message)
            self.assertIn("cached", result.message)

    def test_time_footprint_omitted_when_timing_json_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="DMO-1")

            result = show_status(repo_root=repo_root, run_id="DMO-1")

            self.assertNotIn("Time:", result.message)
            self.assertNotIn("Tools:", result.message)
            self.assertNotIn("Tokens:", result.message)

    def test_error_count_rendered_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="DMO-1")
            self._write_timing_json(
                repo_root=repo_root,
                run_id="DMO-1",
                wall_ms=60_000,
                active_ms=60_000,
                idle_ms=0,
                top_tools=[
                    {"tool_name": "Bash", "count": 10, "total_ms": 30_000, "error_count": 3},
                ],
                tokens={"output_tokens": 100, "cache_read_input_tokens": 0},
                errors=3,
            )

            result = show_status(repo_root=repo_root, run_id="DMO-1")

            self.assertIn("3 errors", result.message)

    def _write_run(self, *, repo_root: Path, run_id: str) -> None:
        parent = repo_root / "runs" / "active" / run_id
        home_dir = parent / "home"
        home_dir.mkdir(parents=True, exist_ok=True)
        (home_dir / "issue.md").write_text("# Issue\n", encoding="utf-8")
        (parent / "run.yaml").write_text(
            textwrap.dedent(
                f"""\
                id: {run_id}
                flow_name: demo
                flow_code: DMO
                adapter_name: codex
                start_agent_key: 01_scope_lead
                created_at: "2026-04-14T00:00:00Z"
                issue_file: home/issue.md
                """
            ),
            encoding="utf-8",
        )
        (parent / "state.yaml").write_text(
            textwrap.dedent(
                """\
                status: paused
                current_agent_key: 01_scope_lead
                current_agent_slug: 01_scope_lead
                turn_index: 1
                updated_at: "2026-04-14T01:00:00Z"
                """
            ),
            encoding="utf-8",
        )

    def _write_timing_json(
        self,
        *,
        repo_root: Path,
        run_id: str,
        wall_ms: int,
        active_ms: int,
        idle_ms: int,
        top_tools: list[dict],
        tokens: dict,
        errors: int,
    ) -> None:
        timing = {
            "run_id": run_id,
            "flow_code": run_id.split("-")[0],
            "run_status": "running",
            "last_turn_index": 1,
            "wall_ms": wall_ms,
            "active_ms": active_ms,
            "idle_ms": idle_ms,
            "setup_ms": 0,
            "tokens": {
                "input_tokens": 0,
                "output_tokens": tokens.get("output_tokens", 0),
                "cache_read_input_tokens": tokens.get("cache_read_input_tokens", 0),
                "cache_creation_input_tokens": 0,
            },
            "per_agent": [
                {
                    "agent_slug": "a",
                    "agent_key": "a",
                    "turns": 1,
                    "wall_ms": wall_ms,
                    "tool_ms": 0,
                    "model_ms": wall_ms,
                    "tools_called": sum(t["count"] for t in top_tools),
                    "errors": errors,
                    "tokens": {
                        "input_tokens": 0,
                        "output_tokens": tokens.get("output_tokens", 0),
                        "cache_read_input_tokens": tokens.get("cache_read_input_tokens", 0),
                        "cache_creation_input_tokens": 0,
                    },
                }
            ],
            "top_tools": top_tools,
            "top_commands": [],
            "turns": [],
            "flags": [],
        }
        path = repo_root / "runs" / "active" / run_id / "timing.json"
        path.write_text(json.dumps(timing, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
