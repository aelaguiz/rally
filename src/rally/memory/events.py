from __future__ import annotations

from pathlib import Path
from typing import Sequence

from rally.memory.logging import count_summary_text
from rally.memory.models import MemoryEntry, MemoryRefreshResult, MemorySaveResult, MemorySearchHit
from rally.services.run_events import RunEvent, RunEventRecorder


def record_memory_searched(
    *,
    run_dir: Path,
    run_id: str,
    flow_code: str,
    query: str,
    hits: Sequence[MemorySearchHit],
    turn_index: int | None,
    agent_slug: str,
) -> RunEvent:
    noun = "hit" if len(hits) == 1 else "hits"
    detail_lines = [f"{hit.memory_id}: {hit.title}" for hit in hits[:3]]
    message = "No scoped memories found." if not hits else f"Found {len(hits)} memory {noun}."
    recorder = RunEventRecorder(run_dir=run_dir, run_id=run_id, flow_code=flow_code)
    try:
        return recorder.emit(
            source="rally memory search",
            kind="memory",
            code="MEM OK",
            message=message,
            data={
                "trace_class": "memory",
                "action": "search",
                "query": query,
                "hit_count": len(hits),
                "memory_ids": [hit.memory_id for hit in hits],
                "detail_lines": detail_lines,
            },
            turn_index=turn_index,
            agent_slug=agent_slug,
        )
    finally:
        recorder.close()


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
            kind="memory",
            code="MEM OK",
            message=f"Loaded memory `{entry.memory_id}`.",
            data={
                "trace_class": "memory",
                "action": "use",
                "memory_id": entry.memory_id,
                "flow_code": entry.scope.flow_code,
                "agent_slug": entry.scope.agent_slug,
                "path": str(entry.path),
                "source_run_id": entry.source_run_id,
                "detail_lines": [str(entry.path), entry.title],
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
    refresh_result: MemoryRefreshResult,
    turn_index: int | None,
    agent_slug: str,
) -> RunEvent:
    entry = save_result.entry
    recorder = RunEventRecorder(run_dir=run_dir, run_id=run_id, flow_code=flow_code)
    try:
        return recorder.emit(
            source="rally memory save",
            kind="memory",
            code="MEM OK",
            message=f"{save_result.outcome.title()} memory `{entry.memory_id}`.",
            data={
                "trace_class": "memory",
                "action": "save",
                "memory_id": entry.memory_id,
                "flow_code": entry.scope.flow_code,
                "agent_slug": entry.scope.agent_slug,
                "path": str(entry.path),
                "source_run_id": entry.source_run_id,
                "outcome": save_result.outcome,
                "indexed": refresh_result.indexed,
                "updated": refresh_result.updated,
                "unchanged": refresh_result.unchanged,
                "removed": refresh_result.removed,
                "detail_lines": [
                    str(entry.path),
                    count_summary_text(
                        indexed=refresh_result.indexed,
                        updated=refresh_result.updated,
                        unchanged=refresh_result.unchanged,
                        removed=refresh_result.removed,
                    ),
                ],
            },
            turn_index=turn_index,
            agent_slug=agent_slug,
        )
    finally:
        recorder.close()


def record_memory_refreshed(
    *,
    run_dir: Path,
    run_id: str,
    flow_code: str,
    refresh_result: MemoryRefreshResult,
    turn_index: int | None,
    agent_slug: str,
) -> RunEvent:
    recorder = RunEventRecorder(run_dir=run_dir, run_id=run_id, flow_code=flow_code)
    try:
        return recorder.emit(
            source="rally memory refresh",
            kind="memory",
            code="MEM OK",
            message="Refreshed scoped memory index.",
            data={
                "trace_class": "memory",
                "action": "refresh",
                "indexed": refresh_result.indexed,
                "updated": refresh_result.updated,
                "unchanged": refresh_result.unchanged,
                "removed": refresh_result.removed,
                "detail_lines": [
                    count_summary_text(
                        indexed=refresh_result.indexed,
                        updated=refresh_result.updated,
                        unchanged=refresh_result.unchanged,
                        removed=refresh_result.removed,
                    )
                ],
            },
            turn_index=turn_index,
            agent_slug=agent_slug,
        )
    finally:
        recorder.close()
