from __future__ import annotations

import io
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from rally.cli import main
from rally.memory.models import MemoryEntry, MemoryRefreshResult, MemorySaveResult, MemoryScope, MemorySearchHit
from rally.services.workspace import workspace_context_from_root


class MemoryCliTests(unittest.TestCase):
    def test_memory_search_prints_hits(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.search_memory",
            return_value=(
                MemorySearchHit(
                    memory_id="mem_flw_scope_lead_focus_the_fix",
                    path=Path("/tmp/repo/runs/memory/entries/FLW/scope_lead/mem_flw_scope_lead_focus_the_fix.md"),
                    title="Focus the fix",
                    snippet="Fix the concrete bug before widening scope.",
                    score=0.83,
                ),
            ),
        ) as search_memory_mock:
            with redirect_stdout(stdout):
                exit_code = main(["memory", "search", "--run-id", "FLW-1", "--query", "focus the fix"])

        self.assertEqual(exit_code, 0)
        self.assertIn("mem_flw_scope_lead_focus_the_fix", stdout.getvalue())
        self.assertEqual(search_memory_mock.call_args.kwargs["run_id"], "FLW-1")

    def test_memory_use_prints_memory_body(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.use_memory",
            return_value=self._memory_entry(Path("/tmp/repo")),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["memory", "use", "--run-id", "FLW-1", "mem_flw_scope_lead_focus_the_fix"])

        self.assertEqual(exit_code, 0)
        self.assertIn("# Lesson", stdout.getvalue())
        self.assertIn("Focus the fix before widening scope.", stdout.getvalue())

    def test_memory_save_reads_stdin_and_reports_outcome(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))
        save_result = MemorySaveResult(outcome="created", entry=self._memory_entry(Path("/tmp/repo")))
        refresh_result = MemoryRefreshResult(
            collections=1,
            indexed=1,
            updated=0,
            unchanged=0,
            removed=0,
            needs_embedding=0,
            docs_processed=0,
            chunks_embedded=0,
            embed_errors=0,
        )

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.save_memory",
            return_value=(save_result, refresh_result),
        ) as save_memory_mock, patch("sys.stdin", io.StringIO(self._memory_body())):
            with redirect_stdout(stdout):
                exit_code = main(["memory", "save", "--run-id", "FLW-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Created memory", stdout.getvalue())
        self.assertIn("mem_flw_scope_lead_focus_the_fix", stdout.getvalue())
        self.assertEqual(save_memory_mock.call_args.kwargs["run_id"], "FLW-1")

    def test_memory_refresh_reports_counts(self) -> None:
        stdout = io.StringIO()
        workspace = self._workspace(Path("/tmp/repo"))

        with patch("rally.cli.resolve_workspace", return_value=workspace), patch(
            "rally.cli.refresh_memory",
            return_value=MemoryRefreshResult(
                collections=1,
                indexed=1,
                updated=2,
                unchanged=3,
                removed=0,
                needs_embedding=0,
                docs_processed=5,
                chunks_embedded=7,
                embed_errors=0,
            ),
        ):
            with redirect_stdout(stdout):
                exit_code = main(["memory", "refresh", "--run-id", "FLW-1"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Refreshed scoped memory index.", stdout.getvalue())
        self.assertIn("1 new, 2 updated, 3 unchanged, 0 removed", stdout.getvalue())

    def _workspace(self, repo_root: Path):
        return workspace_context_from_root(
            repo_root,
            cli_bin=repo_root / "bin" / "rally",
            framework_root=Path(__file__).resolve().parents[3],
        )

    def _memory_entry(self, repo_root: Path) -> MemoryEntry:
        return MemoryEntry(
            memory_id="mem_flw_scope_lead_focus_the_fix",
            scope=MemoryScope(flow_code="FLW", agent_slug="scope_lead"),
            source_run_id="FLW-1",
            created_at="2026-04-13T20:00:00Z",
            updated_at="2026-04-13T20:05:00Z",
            lesson="Focus the fix before widening scope.",
            when_this_matters="Use this when the first bug is still not fixed.",
            what_to_do="Fix the concrete bug, then widen only if proof shows a second issue.",
            path=repo_root / "runs" / "memory" / "entries" / "FLW" / "scope_lead" / "mem_flw_scope_lead_focus_the_fix.md",
        )

    def _memory_body(self) -> str:
        return textwrap.dedent(
            """\
            # Lesson
            Focus the fix before widening scope.

            # When This Matters
            Use this when the first bug is still not fixed.

            # What To Do
            Fix the concrete bug, then widen only if proof shows a second issue.
            """
        )


if __name__ == "__main__":
    unittest.main()
