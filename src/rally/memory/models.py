from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rally.domain.flow import normalize_flow_code


MemorySaveKind = Literal["created", "updated"]


@dataclass(frozen=True)
class MemoryScope:
    flow_code: str
    agent_slug: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "flow_code", normalize_flow_code(self.flow_code))
        normalized_agent_slug = self.agent_slug.strip()
        if not normalized_agent_slug:
            raise ValueError("Memory scope agent_slug must not be empty.")
        object.__setattr__(self, "agent_slug", normalized_agent_slug)

    @property
    def collection_name(self) -> str:
        return f"mem_{self.flow_code.lower()}_{self.agent_slug}"

    def entries_dir(self, repo_root: Path) -> Path:
        return repo_root / "runs" / "memory" / "entries" / self.flow_code / self.agent_slug

    @property
    def root_context(self) -> str:
        return (
            f"Rally memory for flow `{self.flow_code}` and agent `{self.agent_slug}`. "
            "These files are short cross-run lessons."
        )


@dataclass(frozen=True)
class MemoryEntry:
    memory_id: str
    scope: MemoryScope
    source_run_id: str
    created_at: str
    updated_at: str
    lesson: str
    when_this_matters: str
    what_to_do: str
    path: Path

    @property
    def title(self) -> str:
        first_line = self.lesson.splitlines()[0].strip()
        return first_line or self.memory_id

    def body_markdown(self) -> str:
        return (
            "# Lesson\n"
            f"{self.lesson.strip()}\n\n"
            "# When This Matters\n"
            f"{self.when_this_matters.strip()}\n\n"
            "# What To Do\n"
            f"{self.what_to_do.strip()}\n"
        )

    def file_markdown(self) -> str:
        return (
            "---\n"
            f'id: "{self.memory_id}"\n'
            f'flow_code: "{self.scope.flow_code}"\n'
            f'agent_slug: "{self.scope.agent_slug}"\n'
            f'created_at: "{self.created_at}"\n'
            f'updated_at: "{self.updated_at}"\n'
            f'source_run_id: "{self.source_run_id}"\n'
            "---\n\n"
            f"{self.body_markdown()}"
        )


@dataclass(frozen=True)
class MemorySearchHit:
    memory_id: str
    path: Path
    title: str
    snippet: str
    score: float


@dataclass(frozen=True)
class MemorySaveResult:
    outcome: MemorySaveKind
    entry: MemoryEntry


@dataclass(frozen=True)
class MemoryRefreshResult:
    collections: int
    indexed: int
    updated: int
    unchanged: int
    removed: int
    needs_embedding: int
    docs_processed: int
    chunks_embedded: int
    embed_errors: int
