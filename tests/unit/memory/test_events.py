from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rally.memory.events import record_memory_saved, record_memory_used
from rally.memory.models import MemoryEntry, MemorySaveResult, MemoryScope


class MemoryEventTests(unittest.TestCase):
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
            self.assertIn('"kind": "memory_used"', events)
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
                turn_index=3,
                agent_slug="scope_lead",
            )

            events = (run_dir / "logs" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"kind": "memory_saved"', events)
            self.assertIn('"outcome": "updated"', events)


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


if __name__ == "__main__":
    unittest.main()
