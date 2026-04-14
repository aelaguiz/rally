from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rally.domain.memory import MemoryEntry, MemorySaveResult, MemoryScope
from rally.errors import RallyStateError

_BODY_SECTION_TITLES = ("Lesson", "When This Matters", "What To Do")
_BODY_SECTION_PATTERN = re.compile(r"(?m)^# (Lesson|When This Matters|What To Do)\s*$")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def save_memory_entry(
    *,
    repo_root: Path,
    scope: MemoryScope,
    run_id: str,
    memory_markdown: str,
    now: datetime | None = None,
) -> MemorySaveResult:
    # Markdown files under `runs/memory/entries/` are the durable memory truth.
    sections = _parse_memory_body(memory_markdown)
    memory_id = _build_memory_id(scope=scope, lesson=sections["Lesson"])
    memory_path = scope.entries_dir(repo_root) / f"{memory_id}.md"
    timestamp = _render_time(now)
    outcome = "created"
    created_at = timestamp

    if memory_path.is_file():
        existing = load_memory_entry(repo_root=repo_root, scope=scope, memory_id=memory_id)
        created_at = existing.created_at
        outcome = "updated"

    entry = MemoryEntry(
        memory_id=memory_id,
        scope=scope,
        source_run_id=run_id,
        created_at=created_at,
        updated_at=timestamp,
        lesson=sections["Lesson"],
        when_this_matters=sections["When This Matters"],
        what_to_do=sections["What To Do"],
        path=memory_path,
    )
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(entry.file_markdown(), encoding="utf-8")
    return MemorySaveResult(outcome=outcome, entry=entry)


def load_memory_entry(
    *,
    repo_root: Path,
    scope: MemoryScope,
    memory_id: str,
) -> MemoryEntry:
    memory_path = scope.entries_dir(repo_root) / f"{memory_id}.md"
    if not memory_path.is_file():
        raise RallyStateError(f"Memory entry does not exist: `{memory_path}`.")
    return load_memory_entry_from_path(memory_path, expected_scope=scope)


def list_memory_entries(
    *,
    repo_root: Path,
    scope: MemoryScope,
) -> tuple[MemoryEntry, ...]:
    entries_dir = scope.entries_dir(repo_root)
    if not entries_dir.is_dir():
        return ()
    return tuple(
        load_memory_entry_from_path(path, expected_scope=scope)
        for path in sorted(entries_dir.glob("*.md"))
    )


def load_memory_entry_from_path(path: Path, *, expected_scope: MemoryScope | None = None) -> MemoryEntry:
    if not path.is_file():
        raise RallyStateError(f"Memory entry does not exist: `{path}`.")
    raw_text = path.read_text(encoding="utf-8")
    frontmatter_text, body_text = _split_frontmatter(raw_text, path=path)
    payload = _load_frontmatter(frontmatter_text, path=path)
    scope = MemoryScope(
        flow_code=_require_frontmatter_string(payload, "flow_code", path=path),
        agent_slug=_require_frontmatter_string(payload, "agent_slug", path=path),
    )
    if expected_scope is not None and scope != expected_scope:
        raise RallyStateError(
            f"Memory entry `{path}` belongs to `{scope.flow_code}/{scope.agent_slug}`, "
            f"not `{expected_scope.flow_code}/{expected_scope.agent_slug}`."
        )
    memory_id = _require_frontmatter_string(payload, "id", path=path)
    if path.stem != memory_id:
        raise RallyStateError(
            f"Memory entry `{path}` must use filename `{memory_id}.md` to match frontmatter id."
        )
    sections = _parse_memory_body(body_text)
    return MemoryEntry(
        memory_id=memory_id,
        scope=scope,
        source_run_id=_require_frontmatter_string(payload, "source_run_id", path=path),
        created_at=_require_frontmatter_string(payload, "created_at", path=path),
        updated_at=_require_frontmatter_string(payload, "updated_at", path=path),
        lesson=sections["Lesson"],
        when_this_matters=sections["When This Matters"],
        what_to_do=sections["What To Do"],
        path=path,
    )


def _split_frontmatter(raw_text: str, *, path: Path) -> tuple[str, str]:
    if not raw_text.startswith("---\n"):
        raise RallyStateError(f"Memory entry `{path}` must start with YAML frontmatter.")
    end_marker = raw_text.find("\n---\n", 4)
    if end_marker < 0:
        raise RallyStateError(f"Memory entry `{path}` is missing the closing YAML frontmatter marker.")
    frontmatter_text = raw_text[4:end_marker]
    body_text = raw_text[end_marker + len("\n---\n") :].lstrip("\n")
    return frontmatter_text, body_text


def _load_frontmatter(frontmatter_text: str, *, path: Path) -> dict[str, object]:
    try:
        payload = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        raise RallyStateError(f"Memory entry `{path}` has invalid YAML frontmatter.") from exc
    if not isinstance(payload, dict):
        raise RallyStateError(f"Memory entry `{path}` frontmatter must decode to a map.")
    return payload


def _require_frontmatter_string(payload: dict[str, object], field: str, *, path: Path) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RallyStateError(f"Memory entry `{path}` requires non-empty frontmatter field `{field}`.")
    return value.strip()


def _parse_memory_body(memory_markdown: str) -> dict[str, str]:
    stripped = memory_markdown.strip()
    if not stripped:
        raise RallyStateError("Memory body is empty.")
    matches = list(_BODY_SECTION_PATTERN.finditer(stripped))
    titles = [match.group(1) for match in matches]
    if titles != list(_BODY_SECTION_TITLES):
        expected = ", ".join(f"`# {title}`" for title in _BODY_SECTION_TITLES)
        raise RallyStateError(f"Memory body must contain exactly these sections in order: {expected}.")

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(stripped)
        content = stripped[start:end].strip()
        if not content:
            raise RallyStateError(f"Memory section `# {match.group(1)}` must not be empty.")
        sections[match.group(1)] = content
    return sections


def _build_memory_id(*, scope: MemoryScope, lesson: str) -> str:
    slug = _SLUG_PATTERN.sub("_", lesson.lower()).strip("_")
    if not slug:
        slug = "lesson"
    slug = slug[:48].strip("_") or "lesson"
    return f"mem_{scope.flow_code.lower()}_{scope.agent_slug}_{slug}"


def _render_time(now: datetime | None) -> str:
    return (now or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")
