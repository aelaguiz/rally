from __future__ import annotations

import tempfile
import textwrap
import unittest
from datetime import UTC, datetime
from pathlib import Path

from rally.errors import RallyStateError
from rally.memory.models import MemoryScope
from rally.memory.store import load_memory_entry_from_path, save_memory_entry


class MemoryStoreTests(unittest.TestCase):
    def test_memory_scope_rejects_invalid_flow_code(self) -> None:
        # Memory directories are keyed by flow code, so invalid values must fail
        # before path building can write to the wrong place.
        with self.assertRaisesRegex(ValueError, "exactly three uppercase ASCII letters"):
            MemoryScope(flow_code="DEMO", agent_slug="poem_writer")

    def test_save_memory_entry_creates_markdown_file_with_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            scope = MemoryScope(flow_code="POM", agent_slug="poem_writer")

            result = save_memory_entry(
                repo_root=repo_root,
                scope=scope,
                run_id="POM-7",
                memory_markdown=self._memory_body("Ask for one clear next step."),
                now=datetime(2026, 4, 13, 21, 0, tzinfo=UTC),
            )

            self.assertEqual(result.outcome, "created")
            self.assertTrue(result.entry.path.is_file())
            saved_text = result.entry.path.read_text(encoding="utf-8")
            self.assertIn('id: "mem_pom_poem_writer_ask_for_one_clear_next_step"', saved_text)
            self.assertIn('flow_code: "POM"', saved_text)
            self.assertIn('agent_slug: "poem_writer"', saved_text)
            self.assertIn('source_run_id: "POM-7"', saved_text)
            self.assertIn("# Lesson\nAsk for one clear next step.", saved_text)

    def test_save_memory_entry_updates_existing_entry_and_keeps_created_at(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            scope = MemoryScope(flow_code="POM", agent_slug="poem_writer")

            first_result = save_memory_entry(
                repo_root=repo_root,
                scope=scope,
                run_id="POM-7",
                memory_markdown=self._memory_body("Ask for one clear next step."),
                now=datetime(2026, 4, 13, 21, 0, tzinfo=UTC),
            )
            second_result = save_memory_entry(
                repo_root=repo_root,
                scope=scope,
                run_id="POM-8",
                memory_markdown=self._memory_body(
                    "Ask for one clear next step.",
                    what_to_do="Write the one clear target, then keep the normal handoff.",
                ),
                now=datetime(2026, 4, 13, 21, 5, tzinfo=UTC),
            )

            self.assertEqual(second_result.outcome, "updated")
            self.assertEqual(second_result.entry.created_at, first_result.entry.created_at)
            self.assertEqual(second_result.entry.source_run_id, "POM-8")
            self.assertEqual(second_result.entry.updated_at, "2026-04-13T21:05:00Z")
            self.assertIn(
                "Write the one clear target, then keep the normal handoff.",
                second_result.entry.path.read_text(encoding="utf-8"),
            )

    def test_load_memory_entry_rejects_invalid_body_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir).resolve() / "mem_pom_poem_writer_bad.md"
            path.write_text(
                textwrap.dedent(
                    """\
                    ---
                    id: mem_pom_poem_writer_bad
                    flow_code: POM
                    agent_slug: poem_writer
                    created_at: 2026-04-13T21:00:00Z
                    updated_at: 2026-04-13T21:00:00Z
                    source_run_id: POM-7
                    ---

                    # Lesson
                    Missing the rest.
                    """
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RallyStateError, "must contain exactly these sections"):
                load_memory_entry_from_path(path)

    def _memory_body(
        self,
        lesson: str,
        *,
        when_this_matters: str = "Use this after a weak draft or a vague critique.",
        what_to_do: str = "Write one clear revision target before you ask for a full rewrite.",
    ) -> str:
        return textwrap.dedent(
            f"""\
            # Lesson
            {lesson}

            # When This Matters
            {when_this_matters}

            # What To Do
            {what_to_do}
            """
        )


if __name__ == "__main__":
    unittest.main()
