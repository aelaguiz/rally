from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from rally.errors import RallyStateError, RallyUsageError
from rally.memory.events import (
    record_memory_refreshed,
    record_memory_saved,
    record_memory_searched,
    record_memory_used,
)
from rally.memory.index import BridgeSubprocessRunner, refresh_memory_index, search_memory_index
from rally.memory.logging import should_record_memory_events
from rally.memory.models import MemoryEntry, MemoryRefreshResult, MemorySaveResult, MemoryScope, MemorySearchHit
from rally.memory.store import load_memory_entry, save_memory_entry
from rally.services.run_store import find_run_dir, load_run_record, load_run_state


@dataclass(frozen=True)
class MemoryCommandContext:
    repo_root: Path
    run_id: str
    run_dir: Path
    turn_index: int | None
    scope: MemoryScope


def resolve_memory_context(
    *,
    repo_root: Path,
    run_id: str,
    agent_slug: str | None = None,
    turn_index: int | None = None,
    env: Mapping[str, str] | None = None,
) -> MemoryCommandContext:
    resolved_env = env or os.environ
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_id)
    run_record = load_run_record(run_dir=run_dir)
    run_state = load_run_state(run_dir=run_dir)

    env_flow_code = _optional_env(resolved_env, "RALLY_FLOW_CODE")
    if env_flow_code is not None and env_flow_code != run_record.flow_code:
        raise RallyStateError(
            f"`RALLY_FLOW_CODE` says `{env_flow_code}`, but run `{run_id}` belongs to `{run_record.flow_code}`."
        )

    env_agent_slug = _optional_env(resolved_env, "RALLY_AGENT_SLUG")
    resolved_agent_slug = agent_slug or env_agent_slug or run_state.current_agent_slug
    if resolved_agent_slug is None:
        raise RallyUsageError(
            "Memory scope needs an agent slug. Set `RALLY_AGENT_SLUG`, use an active run, or pass `--agent-slug`."
        )
    if env_agent_slug is not None and agent_slug is not None and env_agent_slug != agent_slug:
        raise RallyStateError(
            f"`RALLY_AGENT_SLUG` says `{env_agent_slug}`, but the command asked for `{agent_slug}`."
        )
    if env_agent_slug is not None and run_state.current_agent_slug is not None and env_agent_slug != run_state.current_agent_slug:
        raise RallyStateError(
            f"`RALLY_AGENT_SLUG` says `{env_agent_slug}`, but run `{run_id}` is on `{run_state.current_agent_slug}`."
        )

    return MemoryCommandContext(
        repo_root=repo_root,
        run_id=run_id,
        run_dir=run_dir,
        turn_index=turn_index,
        scope=MemoryScope(flow_code=run_record.flow_code, agent_slug=resolved_agent_slug),
    )


def search_memory(
    *,
    repo_root: Path,
    run_id: str,
    query: str,
    limit: int = 5,
    agent_slug: str | None = None,
    turn_index: int | None = None,
    env: Mapping[str, str] | None = None,
    subprocess_run: BridgeSubprocessRunner = subprocess.run,
) -> tuple[MemorySearchHit, ...]:
    resolved_env = env or os.environ
    context = resolve_memory_context(
        repo_root=repo_root,
        run_id=run_id,
        agent_slug=agent_slug,
        turn_index=turn_index,
        env=resolved_env,
    )
    hits = search_memory_index(
        repo_root=context.repo_root,
        scope=context.scope,
        query=query,
        limit=limit,
        subprocess_run=subprocess_run,
    )
    if should_record_memory_events(env=resolved_env):
        record_memory_searched(
            run_dir=context.run_dir,
            run_id=context.run_id,
            flow_code=context.scope.flow_code,
            query=query,
            hits=hits,
            turn_index=context.turn_index,
            agent_slug=context.scope.agent_slug,
        )
    return hits


def use_memory(
    *,
    repo_root: Path,
    run_id: str,
    memory_id: str,
    agent_slug: str | None = None,
    turn_index: int | None = None,
    env: Mapping[str, str] | None = None,
) -> MemoryEntry:
    resolved_env = env or os.environ
    context = resolve_memory_context(
        repo_root=repo_root,
        run_id=run_id,
        agent_slug=agent_slug,
        turn_index=turn_index,
        env=resolved_env,
    )
    entry = load_memory_entry(repo_root=context.repo_root, scope=context.scope, memory_id=memory_id)
    if should_record_memory_events(env=resolved_env):
        record_memory_used(
            run_dir=context.run_dir,
            run_id=context.run_id,
            flow_code=context.scope.flow_code,
            entry=entry,
            turn_index=context.turn_index,
            agent_slug=context.scope.agent_slug,
        )
    return entry


def save_memory(
    *,
    repo_root: Path,
    run_id: str,
    memory_markdown: str,
    agent_slug: str | None = None,
    turn_index: int | None = None,
    env: Mapping[str, str] | None = None,
    subprocess_run: BridgeSubprocessRunner = subprocess.run,
) -> tuple[MemorySaveResult, MemoryRefreshResult]:
    resolved_env = env or os.environ
    context = resolve_memory_context(
        repo_root=repo_root,
        run_id=run_id,
        agent_slug=agent_slug,
        turn_index=turn_index,
        env=resolved_env,
    )
    save_result = save_memory_entry(
        repo_root=context.repo_root,
        scope=context.scope,
        run_id=context.run_id,
        memory_markdown=memory_markdown,
    )
    refresh_result = refresh_memory_index(
        repo_root=context.repo_root,
        scope=context.scope,
        subprocess_run=subprocess_run,
    )
    if should_record_memory_events(env=resolved_env):
        record_memory_saved(
            run_dir=context.run_dir,
            run_id=context.run_id,
            flow_code=context.scope.flow_code,
            save_result=save_result,
            refresh_result=refresh_result,
            turn_index=context.turn_index,
            agent_slug=context.scope.agent_slug,
        )
    return save_result, refresh_result


def refresh_memory(
    *,
    repo_root: Path,
    run_id: str,
    agent_slug: str | None = None,
    turn_index: int | None = None,
    env: Mapping[str, str] | None = None,
    subprocess_run: BridgeSubprocessRunner = subprocess.run,
) -> MemoryRefreshResult:
    resolved_env = env or os.environ
    context = resolve_memory_context(
        repo_root=repo_root,
        run_id=run_id,
        agent_slug=agent_slug,
        turn_index=turn_index,
        env=resolved_env,
    )
    result = refresh_memory_index(
        repo_root=context.repo_root,
        scope=context.scope,
        subprocess_run=subprocess_run,
    )
    if should_record_memory_events(env=resolved_env):
        record_memory_refreshed(
            run_dir=context.run_dir,
            run_id=context.run_id,
            flow_code=context.scope.flow_code,
            refresh_result=result,
            turn_index=context.turn_index,
            agent_slug=context.scope.agent_slug,
        )
    return result


def _optional_env(env: Mapping[str, str], name: str) -> str | None:
    raw_value = env.get(name)
    if raw_value is None:
        return None
    value = raw_value.strip()
    return value or None
