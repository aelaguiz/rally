from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from rally.services.memory_runtime import save_memory, search_memory, use_memory


class MemoryRuntimeTests(unittest.TestCase):
    def test_save_memory_writes_file_and_visible_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del command, kwargs
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

            save_result, refresh_result = save_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_markdown=self._memory_body(),
                subprocess_run=fake_run,
            )

            issue_text = (repo_root / "runs" / "POM-7" / "home" / "issue.md").read_text(encoding="utf-8")
            events_text = (repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(save_result.outcome, "created")
            self.assertEqual(refresh_result.indexed, 1)
            self.assertTrue(save_result.entry.path.is_file())
            self.assertIn("## Memory Saved", issue_text)
            self.assertIn("- Outcome: `created`", issue_text)
            self.assertIn('"kind": "memory_saved"', events_text)

    def test_use_memory_appends_issue_and_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)

            def fake_refresh(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del command, kwargs
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

            save_result, _ = save_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_markdown=self._memory_body(),
                subprocess_run=fake_refresh,
            )
            issue_path = repo_root / "runs" / "POM-7" / "home" / "issue.md"
            issue_path.write_text("# Brief\n\nWrite a sonnet.\n", encoding="utf-8")

            entry = use_memory(
                repo_root=repo_root,
                run_id="POM-7",
                memory_id=save_result.entry.memory_id,
            )

            issue_text = issue_path.read_text(encoding="utf-8")
            events_text = (repo_root / "runs" / "POM-7" / "logs" / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(entry.memory_id, save_result.entry.memory_id)
            self.assertIn("## Memory Used", issue_text)
            self.assertIn(f"- Memory ID: `{entry.memory_id}`", issue_text)
            self.assertIn('"kind": "memory_used"', events_text)

    def test_search_memory_does_not_touch_issue_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            self._write_run(repo_root=repo_root, run_id="POM-7", flow_code="POM", current_agent_slug="poem_writer")
            self._write_bridge(repo_root=repo_root)
            entries_dir = repo_root / "runs" / "memory" / "entries" / "POM" / "poem_writer"
            entries_dir.mkdir(parents=True, exist_ok=True)
            (entries_dir / "mem_pom_poem_writer_focus_revision.md").write_text("memory\n", encoding="utf-8")

            def fake_search(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                del command, kwargs
                return subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "results": [
                                {
                                    "memoryId": "mem_pom_poem_writer_focus_revision",
                                    "path": str(entries_dir / "mem_pom_poem_writer_focus_revision.md"),
                                    "title": "Focus revision",
                                    "snippet": "Ask for one target before a rewrite.",
                                    "score": 0.8,
                                }
                            ]
                        }
                    ),
                    stderr="",
                )

            issue_path = repo_root / "runs" / "POM-7" / "home" / "issue.md"
            before_text = issue_path.read_text(encoding="utf-8")

            hits = search_memory(
                repo_root=repo_root,
                run_id="POM-7",
                query="target before rewrite",
                subprocess_run=fake_search,
            )

            self.assertEqual(len(hits), 1)
            self.assertEqual(issue_path.read_text(encoding="utf-8"), before_text)
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
