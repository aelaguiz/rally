from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.memory.events import (
    record_memory_refreshed,
    record_memory_saved,
    record_memory_searched,
    record_memory_used,
)
from rally.memory.models import MemoryEntry, MemoryRefreshResult, MemorySaveResult, MemoryScope, MemorySearchHit


class MemoryEventTests(unittest.TestCase):
    def test_record_memory_searched_writes_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)

            record_memory_searched(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                query="focus the fix",
                hits=(_memory_hit(run_dir),),
                turn_index=1,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory"', events)
            self.assertIn('"action": "search"', events)
            self.assertIn('"memory_ids": ["mem_dmo_scope_lead_focus_the_fix"]', events)

    def test_record_memory_used_writes_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)

            record_memory_used(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                entry=_memory_entry(run_dir),
                turn_index=2,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory"', events)
            self.assertIn('"action": "use"', events)
            self.assertIn('"memory_id": "mem_dmo_scope_lead_focus_the_fix"', events)

    def test_record_memory_saved_writes_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)

            record_memory_saved(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                save_result=MemorySaveResult(outcome="updated", entry=_memory_entry(run_dir)),
                refresh_result=_refresh_result(),
                turn_index=3,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory"', events)
            self.assertIn('"action": "save"', events)
            self.assertIn('"outcome": "updated"', events)

    def test_record_memory_refreshed_writes_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir).resolve() / "runs" / "DMO-1"
            run_dir.mkdir(parents=True)

            record_memory_refreshed(
                run_dir=run_dir,
                run_id="DMO-1",
                flow_code="DMO",
                refresh_result=_refresh_result(),
                turn_index=4,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory"', events)
            self.assertIn('"action": "refresh"', events)
            self.assertIn('"indexed": 1', events)


def _memory_entry(run_dir: Path) -> MemoryEntry:
    return MemoryEntry(
        memory_id="mem_dmo_scope_lead_focus_the_fix",
        scope=MemoryScope(flow_code="DMO", agent_slug="scope_lead"),
        source_run_id="DMO-1",
        created_at="2026-04-13T19:30:00Z",
        updated_at="2026-04-13T19:35:00Z",
        lesson="Focus the fix before widening scope.",
        when_this_matters="Use this when the first bug is still not fixed.",
        what_to_do="Fix the concrete bug, then widen only if proof shows a second issue.",
        path=run_dir / "runs" / "memory" / "entries" / "DMO" / "scope_lead" / "mem_dmo_scope_lead_focus_the_fix.md",
    )


def _memory_hit(run_dir: Path) -> MemorySearchHit:
    return MemorySearchHit(
        memory_id="mem_dmo_scope_lead_focus_the_fix",
        path=run_dir / "runs" / "memory" / "entries" / "DMO" / "scope_lead" / "mem_dmo_scope_lead_focus_the_fix.md",
        title="Focus the fix",
        snippet="Fix the concrete bug before widening scope.",
        score=0.83,
    )


def _refresh_result() -> MemoryRefreshResult:
    return MemoryRefreshResult(
        collections=1,
        indexed=1,
        updated=2,
        unchanged=3,
        removed=0,
        needs_embedding=0,
        docs_processed=4,
        chunks_embedded=5,
        embed_errors=0,
    )


if __name__ == "__main__":
    unittest.main()
