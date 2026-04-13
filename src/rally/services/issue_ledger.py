from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
import yaml

from rally.errors import RallyStateError
from rally.services.run_store import find_run_dir


@dataclass(frozen=True)
class IssueNoteAppendResult:
    run_id: str
    issue_file: Path
    snapshot_file: Path


def append_issue_note(
    *,
    repo_root: Path,
    run_id: str,
    note_markdown: str,
    now: datetime | None = None,
) -> IssueNoteAppendResult:
    note_body = _normalize_note_body(note_markdown)
    return append_issue_event(
        repo_root=repo_root,
        run_id=run_id,
        title="Rally Note",
        source="rally issue note",
        detail_lines=(),
        body=note_body,
        now=now,
    )


def append_issue_event(
    *,
    repo_root: Path,
    run_id: str,
    title: str,
    source: str,
    detail_lines: Iterable[str],
    body: str | None = None,
    now: datetime | None = None,
) -> IssueNoteAppendResult:
    if not run_id.strip():
        raise RallyStateError("Run id must not be empty.")

    timestamp = now or datetime.now(UTC)
    issue_file = _resolve_issue_file(repo_root=repo_root, run_id=run_id)
    if not issue_file.is_file():
        raise RallyStateError(f"Issue log does not exist: `{issue_file}`.")

    block = _format_issue_block(
        run_id=run_id,
        title=title,
        source=source,
        detail_lines=list(detail_lines),
        body=body,
        timestamp=timestamp,
    )
    updated_issue = _append_block(current_text=issue_file.read_text(encoding="utf-8"), block=block)
    issue_file.write_text(updated_issue, encoding="utf-8")
    snapshot_file = _write_snapshot(issue_file=issue_file, timestamp=timestamp)
    return IssueNoteAppendResult(run_id=run_id, issue_file=issue_file, snapshot_file=snapshot_file)


def snapshot_issue_log(*, repo_root: Path, run_id: str, now: datetime | None = None) -> Path:
    issue_file = _resolve_issue_file(repo_root=repo_root, run_id=run_id)
    if not issue_file.is_file():
        raise RallyStateError(f"Issue log does not exist: `{issue_file}`.")
    return _write_snapshot(issue_file=issue_file, timestamp=now or datetime.now(UTC))


def _resolve_issue_file(*, repo_root: Path, run_id: str) -> Path:
    run_dir, run_record = _load_run_record_map(repo_root=repo_root, run_id=run_id)
    actual_run_id = run_record.get("id")
    if actual_run_id != run_id:
        raise RallyStateError(
            f"Run file `{run_dir / 'run.yaml'}` has id `{actual_run_id}`, not requested run `{run_id}`."
        )
    raw_issue_file = run_record.get("issue_file", "home/issue.md")
    if not isinstance(raw_issue_file, str) or not raw_issue_file.strip():
        raise RallyStateError("Run file `issue_file` must be a non-empty string when present.")
    issue_file = (run_dir / raw_issue_file).resolve()
    expected_issue_file = (run_dir / "home" / "issue.md").resolve()
    if issue_file != expected_issue_file:
        raise RallyStateError(
            f"Run file points at `{issue_file}`, but Rally only writes `{expected_issue_file}`."
        )
    return issue_file


def _load_run_record_map(*, repo_root: Path, run_id: str) -> tuple[Path, dict[str, object]]:
    try:
        run_dir = find_run_dir(repo_root=repo_root, run_id=run_id)
    except RallyStateError as exc:
        run_file = repo_root / "runs" / run_id / "run.yaml"
        raise RallyStateError(f"Run file does not exist: `{run_file}`.") from exc
    run_file = run_dir / "run.yaml"
    if not run_file.is_file():
        raise RallyStateError(f"Run file does not exist: `{run_file}`.")
    try:
        loaded = yaml.safe_load(run_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RallyStateError(f"Run file `{run_file}` is not valid YAML.") from exc
    if not isinstance(loaded, dict):
        raise RallyStateError(f"Run file `{run_file}` must load to a YAML map.")
    return run_dir, loaded


def _normalize_note_body(note_markdown: str) -> str:
    if not note_markdown.strip():
        raise RallyStateError("Note body is empty.")
    lines = note_markdown.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _format_issue_block(
    *,
    run_id: str,
    title: str,
    source: str,
    detail_lines: list[str],
    body: str | None,
    timestamp: datetime,
) -> str:
    rendered_time = timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    lines = [
        f"## {title}",
        f"- Run ID: `{run_id}`",
        f"- Time: `{rendered_time}`",
        f"- Source: `{source}`",
    ]
    lines.extend(f"- {line}" for line in detail_lines)
    if body:
        lines.extend(("", body))
    return "\n".join(lines) + "\n"


def _append_block(*, current_text: str, block: str) -> str:
    if not current_text:
        return block
    if current_text.endswith("\n"):
        return f"{current_text}\n{block}"
    return f"{current_text}\n\n{block}"


def _write_snapshot(*, issue_file: Path, timestamp: datetime) -> Path:
    history_dir = issue_file.parent.parent / "issue_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = history_dir / f"{_snapshot_stamp(timestamp)}-issue.md"
    snapshot_file.write_text(issue_file.read_text(encoding="utf-8"), encoding="utf-8")
    return snapshot_file


def _snapshot_stamp(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
