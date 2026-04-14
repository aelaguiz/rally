from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.memory.logging import MEMORY_EVENT_MODE_ADAPTER, MEMORY_EVENT_MODE_ENV
from rally.memory.service import refresh_memory, save_memory, search_memory, use_memory


class MemoryServiceTests(unittest.TestCase):
    def test_save_memory_writes_file_and_event_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)

            issue_path = repo_root / "runs" / "POM-7" / "home" / "issue.md"
            before_issue = issue_path.read_text(encoding="utf-8")

            save_result, refresh_result = save_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_markdown=self._memory_body(),
                subprocess_run=self._fake_bridge_run,
            )

            events_text = (repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(save_result.outcome, "created")
            self.assertEqual(refresh_result.indexed, 1)
            self.assertTrue(save_result.entry.path.is_file())
            self.assertEqual(issue_path.read_text(encoding="utf-8"), before_issue)
            self.assertIn('"kind": "memory"', events_text)
            self.assertIn('"action": "save"', events_text)

    def test_use_memory_records_event_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)

            save_result, _ = save_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_markdown=self._memory_body(),
                subprocess_run=self._fake_bridge_run,
            )
            issue_path = repo_root / "runs" / "POM-7" / "home" / "issue.md"
            before_issue = issue_path.read_text(encoding="utf-8")

            entry = use_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_id=save_result.entry.memory_id,
            )

            events_text = (repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(entry.memory_id, save_result.entry.memory_id)
            self.assertEqual(issue_path.read_text(encoding="utf-8"), before_issue)
            self.assertIn('"kind": "memory"', events_text)
            self.assertIn('"action": "use"', events_text)

    def test_search_memory_records_event_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)
            entries_dir = repo_root / "runs" / "memory" / "entries" / "POM" / "poem_writer"
            entries_dir.mkdir(parents=True, exist_ok=True)
            (entries_dir / "mem_pom_poem_writer_focus_revision.md").write_text("memory\n", encoding="utf-8")

            issue_path = repo_root / "runs" / "POM-7" / "home" / "issue.md"
            before_text = issue_path.read_text(encoding="utf-8")

            hits = search_memory(
                repo_root=repo_root,
                run_id="POM-7",
                query="target before rewrite",
                subprocess_run=self._fake_bridge_run,
            )

            events_text = (repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(len(hits), 1)
            self.assertEqual(issue_path.read_text(encoding="utf-8"), before_text)
            self.assertIn('"kind": "memory"', events_text)
            self.assertIn('"action": "search"', events_text)

    def test_refresh_memory_records_event_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)
            issue_path = repo_root / "runs" / "POM-7" / "home" / "issue.md"
            before_text = issue_path.read_text(encoding="utf-8")

            result = refresh_memory(
                repo_root=repo_root,
                run_id="POM-7",
                subprocess_run=self._fake_bridge_run,
            )

            events_text = (repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(result.indexed, 1)
            self.assertEqual(issue_path.read_text(encoding="utf-8"), before_text)
            self.assertIn('"kind": "memory"', events_text)
            self.assertIn('"action": "refresh"', events_text)

    def test_memory_commands_skip_direct_events_in_adapter_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)
            env = {MEMORY_EVENT_MODE_ENV: MEMORY_EVENT_MODE_ADAPTER}

            save_result, _ = save_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_markdown=self._memory_body(),
                env=env,
                subprocess_run=self._fake_bridge_run,
            )
            search_hits = search_memory(
                repo_root=repo_root,
                run_id="POM-7",
                query="target before rewrite",
                env=env,
                subprocess_run=self._fake_bridge_run,
            )
            entry = use_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_id=save_result.entry.memory_id,
                env=env,
            )
            refresh_result = refresh_memory(
                repo_root=repo_root,
                run_id="POM-7",
                env=env,
                subprocess_run=self._fake_bridge_run,
            )

            self.assertEqual(save_result.outcome, "created")
            self.assertEqual(len(search_hits), 1)
            self.assertEqual(entry.memory_id, save_result.entry.memory_id)
            self.assertEqual(refresh_result.indexed, 1)
            self.assertFalse((repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").exists())

    def _write_run(self, *, repo_root: Path, run_id: str, flow_code: str, current_agent_slug: str) -> None:
        run_dir = repo_root / "runs" / run_id
        (run_dir / "home").mkdir(parents=True)
        (run_dir / "issue_history").mkdir(parents=True)
        (run_dir / "home" / "issue.md").write_text("# Brief\n\nWrite a sonnet.\n", encoding="utf-8")
        (run_dir / "run.yaml").write_text(
            textwrap.dedent(
                f"""\
                id: {run_id}
                flow_name: poem_loop
                flow_code: {flow_code}
                adapter_name: codex
                start_agent_key: 01_poem_writer
                created_at: "2026-04-13T20:00:00Z"
                issue_file: home/issue.md
                """
            ),
            encoding="utf-8",
        )
        (run_dir / "state.yaml").write_text(
            textwrap.dedent(
                f"""\
                status: running
                current_agent_key: 01_poem_writer
                current_agent_slug: {current_agent_slug}
                turn_index: 1
                updated_at: "2026-04-13T20:05:00Z"
                """
            ),
            encoding="utf-8",
        )

    def _write_bridge(self, *, repo_root: Path) -> None:
        bridge_script = repo_root / "tools" / "qmd_bridge" / "main.mjs"
        bridge_script.parent.mkdir(parents=True, exist_ok=True)
        bridge_script.write_text("// bridge\n", encoding="utf-8")

    def _fake_bridge_run(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        if command[-1] == "refresh":
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "collections": 1,
                        "indexed": 1,
                        "updated": 0,
                        "unchanged": 0,
                        "removed": 0,
                        "needsEmbedding": 0,
                        "docsProcessed": 0,
                        "chunksEmbedded": 0,
                        "embedErrors": 0,
                    }
                ),
                stderr="",
            )
        if command[-1] == "search":
            memory_path = (
                Path(command[1]).resolve().parents[2]
                / "runs"
                / "memory"
                / "entries"
                / "POM"
                / "poem_writer"
                / "mem_pom_poem_writer_focus_revision.md"
            )
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "results": [
                            {
                                "memoryId": "mem_pom_poem_writer_focus_revision",
                                "path": str(memory_path),
                                "title": "Focus revision",
                                "snippet": "Ask for one target before a rewrite.",
                                "score": 0.8,
                            }
                        ]
                    }
                ),
                stderr="",
            )
        raise AssertionError(f"Unexpected bridge command: {command}")

    def _memory_body(self) -> str:
        return textwrap.dedent(
            """\
            # Lesson
            Ask for one concrete revision target before you ask for a rewrite.

            # When This Matters
            Use this after a weak draft or a vague critique.

            # What To Do
            Write the one concrete target, then keep the normal handoff.
            """
        )


if __name__ == "__main__":
    unittest.main()
