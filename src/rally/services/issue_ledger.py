from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from rally.errors import RallyStateError


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
    timestamp = now or datetime.now(UTC)
    run_dir = repo_root / "runs" / run_id
    run_file = run_dir / "run.yaml"

    if not run_file.is_file():
        raise RallyStateError(f"Run file does not exist: `{run_file}`.")

    run_record = _load_run_record(run_file)
    actual_run_id = run_record.get("id")
    if actual_run_id != run_id:
        raise RallyStateError(
            f"Run file `{run_file}` has id `{actual_run_id}`, not requested run `{run_id}`."
        )

    issue_file = _resolve_issue_file(run_dir=run_dir, run_record=run_record)
    if not issue_file.is_file():
        raise RallyStateError(f"Issue log does not exist: `{issue_file}`.")

    history_dir = run_dir / "issue_history"
    history_dir.mkdir(parents=True, exist_ok=True)

    updated_issue = _append_block(
        current_text=issue_file.read_text(encoding="utf-8"),
        block=_format_issue_note_block(run_id=run_id, note_body=note_body, timestamp=timestamp),
    )
    issue_file.write_text(updated_issue, encoding="utf-8")

    snapshot_file = history_dir / f"{_snapshot_stamp(timestamp)}-issue.md"
    snapshot_file.write_text(updated_issue, encoding="utf-8")

    return IssueNoteAppendResult(run_id=run_id, issue_file=issue_file, snapshot_file=snapshot_file)


def _load_run_record(run_file: Path) -> dict[str, object]:
    try:
        loaded = yaml.safe_load(run_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RallyStateError(f"Run file `{run_file}` is not valid YAML.") from exc

    if not isinstance(loaded, dict):
        raise RallyStateError(f"Run file `{run_file}` must load to a YAML map.")
    return loaded


def _resolve_issue_file(*, run_dir: Path, run_record: dict[str, object]) -> Path:
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


def _normalize_note_body(note_markdown: str) -> str:
    if not note_markdown.strip():
        raise RallyStateError("Note body is empty.")
    return note_markdown.strip("\n")


def _format_issue_note_block(*, run_id: str, note_body: str, timestamp: datetime) -> str:
    rendered_time = timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return (
        "## Rally Note\n"
        f"- Run ID: `{run_id}`\n"
        f"- Time: `{rendered_time}`\n"
        "- Source: `rally issue note`\n\n"
        f"{note_body}\n"
    )


def _append_block(*, current_text: str, block: str) -> str:
    if not current_text:
        return block
    if current_text.endswith("\n"):
        return f"{current_text}\n{block}"
    return f"{current_text}\n\n{block}"


def _snapshot_stamp(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
