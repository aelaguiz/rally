from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable

from rally.domain.memory import MemoryRefreshResult, MemoryScope, MemorySearchHit
from rally.errors import RallyStateError
from rally.services.memory_store import load_memory_entry_from_path

BridgeSubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]
_FRONTMATTER_ID_RE = re.compile(r'\bid:\s*"([^"]+)"')


def refresh_memory_index(
    *,
    repo_root: Path,
    scope: MemoryScope,
    subprocess_run: BridgeSubprocessRunner = subprocess.run,
) -> MemoryRefreshResult:
    entries_dir = scope.entries_dir(repo_root)
    entries_dir.mkdir(parents=True, exist_ok=True)
    payload = _run_bridge(
        repo_root=repo_root,
        command_name="refresh",
        payload={
            "dbPath": str(memory_db_path(repo_root)),
            "collectionName": scope.collection_name,
            "collectionPath": str(entries_dir),
            "rootContext": scope.root_context,
        },
        subprocess_run=subprocess_run,
    )
    return MemoryRefreshResult(
        collections=_require_int(payload, "collections"),
        indexed=_require_int(payload, "indexed"),
        updated=_require_int(payload, "updated"),
        unchanged=_require_int(payload, "unchanged"),
        removed=_require_int(payload, "removed"),
        needs_embedding=_require_int(payload, "needsEmbedding"),
        docs_processed=_require_int(payload, "docsProcessed"),
        chunks_embedded=_require_int(payload, "chunksEmbedded"),
        embed_errors=_require_int(payload, "embedErrors"),
    )


def search_memory_index(
    *,
    repo_root: Path,
    scope: MemoryScope,
    query: str,
    limit: int = 5,
    subprocess_run: BridgeSubprocessRunner = subprocess.run,
) -> tuple[MemorySearchHit, ...]:
    if not query.strip():
        raise RallyStateError("Memory search query must not be empty.")
    entries_dir = scope.entries_dir(repo_root)
    if not entries_dir.is_dir() or not any(entries_dir.glob("*.md")):
        return ()
    payload = _run_bridge(
        repo_root=repo_root,
        command_name="search",
        payload={
            "dbPath": str(memory_db_path(repo_root)),
            "collectionName": scope.collection_name,
            "collectionPath": str(entries_dir),
            "query": query,
            "limit": limit,
        },
        subprocess_run=subprocess_run,
    )
    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        raise RallyStateError("QMD bridge search response is missing `results`.")
    hits: list[MemorySearchHit] = []
    for item in raw_results:
        if not isinstance(item, dict):
            raise RallyStateError("QMD bridge search results must be JSON objects.")
        path = Path(_require_string(item, "path"))
        memory_id = _require_string(item, "memoryId")
        title = _require_string(item, "title")
        snippet = _require_string(item, "snippet")
        canonical_path = path
        if not canonical_path.is_file():
            frontmatter_id = _extract_frontmatter_id(snippet)
            if frontmatter_id is not None:
                candidate_path = scope.entries_dir(repo_root) / f"{frontmatter_id}.md"
                if candidate_path.is_file():
                    canonical_path = candidate_path
                    memory_id = frontmatter_id
        if canonical_path.is_file():
            try:
                entry = load_memory_entry_from_path(canonical_path, expected_scope=scope)
            except RallyStateError:
                pass
            else:
                canonical_path = entry.path
                memory_id = entry.memory_id
                title = entry.title
                snippet = _render_search_snippet(entry.when_this_matters)
        hits.append(
            MemorySearchHit(
                memory_id=memory_id,
                path=canonical_path,
                title=title,
                snippet=snippet,
                score=_require_float(item, "score"),
            )
        )
    return tuple(hits)


def memory_db_path(repo_root: Path) -> Path:
    return repo_root / "runs" / "memory" / "qmd" / "index.sqlite"


def memory_cache_dir(repo_root: Path) -> Path:
    return repo_root / "runs" / "memory" / "qmd" / "cache"


def _run_bridge(
    *,
    repo_root: Path,
    command_name: str,
    payload: dict[str, object],
    subprocess_run: BridgeSubprocessRunner,
) -> dict[str, object]:
    bridge_dir = repo_root / "tools" / "qmd_bridge"
    bridge_script = bridge_dir / "main.mjs"
    if not bridge_script.is_file():
        raise RallyStateError(f"QMD bridge script is missing: `{bridge_script}`.")

    db_path = memory_db_path(repo_root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = memory_cache_dir(repo_root)
    cache_dir.mkdir(parents=True, exist_ok=True)

    command = ["node", str(bridge_script), command_name]
    try:
        completed = subprocess_run(
            command,
            cwd=bridge_dir,
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            env=_bridge_env(cache_dir=cache_dir),
        )
    except OSError as exc:
        raise RallyStateError(f"Failed to start the QMD bridge for `{command_name}`: {exc}.") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown QMD bridge failure"
        raise RallyStateError(f"QMD bridge `{command_name}` failed: {detail}")
    decoded = _decode_bridge_output(stdout_text=completed.stdout, command_name=command_name)
    if not isinstance(decoded, dict):
        raise RallyStateError(f"QMD bridge `{command_name}` must return a JSON object.")
    return decoded


def _bridge_env(*, cache_dir: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    return env


def _require_string(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RallyStateError(f"QMD bridge response requires string field `{field}`.")
    return value


def _require_int(payload: dict[str, object], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int):
        raise RallyStateError(f"QMD bridge response requires integer field `{field}`.")
    return value


def _require_float(payload: dict[str, object], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, int):
        return float(value)
    if not isinstance(value, float):
        raise RallyStateError(f"QMD bridge response requires numeric field `{field}`.")
    return value


def _decode_bridge_output(*, stdout_text: str, command_name: str) -> dict[str, object]:
    raw_text = stdout_text.strip()
    if not raw_text:
        raise RallyStateError(f"QMD bridge `{command_name}` returned empty output.")
    try:
        decoded = json.loads(raw_text)
    except json.JSONDecodeError:
        for line in reversed(stdout_text.splitlines()):
            candidate = line.strip()
            if not candidate:
                continue
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                return decoded
        raise RallyStateError(f"QMD bridge `{command_name}` returned invalid JSON.") from None
    if not isinstance(decoded, dict):
        raise RallyStateError(f"QMD bridge `{command_name}` must return a JSON object.")
    return decoded


def _render_search_snippet(text: str, *, max_chars: int = 200) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 3].rstrip()}..."


def _extract_frontmatter_id(text: str) -> str | None:
    match = _FRONTMATTER_ID_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip() or None
