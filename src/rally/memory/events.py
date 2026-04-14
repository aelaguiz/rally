from __future__ import annotations

from pathlib import Path

from rally.memory.models import MemoryEntry, MemorySaveResult
from rally.services.run_events import RunEvent, RunEventRecorder


def record_memory_used(
    *,
    run_dir: Path,
    run_id: str,
    flow_code: str,
    entry: MemoryEntry,
    turn_index: int | None,
    agent_slug: str,
) -> RunEvent:
    recorder = RunEventRecorder(run_dir=run_dir, run_id=run_id, flow_code=flow_code)
    try:
        return recorder.emit(
            source="rally memory use",
            kind="memory_used",
            code="MEM USE",
            message=f"Used memory `{entry.memory_id}`.",
            data={
                "memory_id": entry.memory_id,
                "flow_code": entry.scope.flow_code,
                "agent_slug": entry.scope.agent_slug,
                "path": str(entry.path),
                "source_run_id": entry.source_run_id,
            },
            turn_index=turn_index,
            agent_slug=agent_slug,
        )
    finally:
        recorder.close()


def record_memory_saved(
    *,
    run_dir: Path,
    run_id: str,
    flow_code: str,
    save_result: MemorySaveResult,
    turn_index: int | None,
    agent_slug: str,
) -> RunEvent:
    entry = save_result.entry
    recorder = RunEventRecorder(run_dir=run_dir, run_id=run_id, flow_code=flow_code)
    try:
        return recorder.emit(
            source="rally memory save",
            kind="memory_saved",
            code="MEM SAVE",
            message=f"Saved memory `{entry.memory_id}` ({save_result.outcome}).",
            data={
                "memory_id": entry.memory_id,
                "flow_code": entry.scope.flow_code,
                "agent_slug": entry.scope.agent_slug,
                "path": str(entry.path),
                "source_run_id": entry.source_run_id,
                "outcome": save_result.outcome,
            },
            turn_index=turn_index,
            agent_slug=agent_slug,
        )
    finally:
        recorder.close()
