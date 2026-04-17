from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import yaml

from rally.errors import RallyStateError
from rally.services.run_store import find_run_dir

ORIGINAL_ISSUE_END_MARKER = "<!-- RALLY_ORIGINAL_ISSUE_END -->"
_NOTE_FIELD_KEY_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")
_RALLY_BLOCK_TITLES = (
    "Rally Note",
    "user edited issue.md",
    "Rally Run Started",
    "Rally Turn Result",
    "Rally Blocked",
    "Rally Done",
    "Rally Archived",
    "Rally Sleeping",
)
_RALLY_BLOCK_TITLE_PATTERN = "|".join(re.escape(title) for title in _RALLY_BLOCK_TITLES)
_RALLY_BLOCK_PATTERN = re.compile(rf"(?:\A|\n\n---\n\n)(## (?P<title>{_RALLY_BLOCK_TITLE_PATTERN})\n)")


@dataclass(frozen=True)
class IssueNoteAppendResult:
    run_id: str
    issue_file: Path
    snapshot_file: Path


@dataclass(frozen=True)
class IssueLedgerBlock:
    title: str
    markdown: str


@dataclass(frozen=True)
class IssueCurrentView:
    run_id: str
    opening_issue: str
    latest_turn_result: str | None
    latest_note: str | None
    latest_blocked: str | None

    def render_markdown(self) -> str:
        sections = [
            "# Rally Issue Current View",
            f"- Run ID: `{self.run_id}`",
            "- Full Ledger: `home:issue.md`",
            "",
            "## Opening Issue",
            self.opening_issue.rstrip() if self.opening_issue.strip() else "_No opening issue text._",
            "",
            "## Latest Rally Turn Result",
            self.latest_turn_result.rstrip()
            if self.latest_turn_result is not None
            else "_No `Rally Turn Result` block yet._",
            "",
            "## Latest Rally Note",
            self.latest_note.rstrip() if self.latest_note is not None else "_No `Rally Note` block yet._",
        ]
        if self.latest_blocked is not None:
            sections.extend(
                (
                    "",
                    "## Current Rally Blocked",
                    self.latest_blocked.rstrip(),
                )
            )
        sections.extend(
            (
                "",
                "## Full Ledger",
                "Open `home:issue.md` only when you need older history or the full block text.",
            )
        )
        return "\n".join(sections).rstrip() + "\n"


def append_issue_note(
    *,
    repo_root: Path,
    run_id: str,
    note_markdown: str,
    note_fields: Iterable[tuple[str, str]] = (),
    turn_index: int | None = None,
    now: datetime | None = None,
) -> IssueNoteAppendResult:
    note_body = _normalize_note_body(note_markdown)
    detail_lines = [
        f"Field {key}: `{value}`"
        for key, value in _normalize_note_fields(note_fields)
    ]
    return append_issue_event(
        repo_root=repo_root,
        run_id=run_id,
        title="Rally Note",
        source="rally issue note",
        detail_lines=detail_lines,
        body=note_body,
        turn_index=turn_index,
        now=now,
    )


def append_issue_edit_diff(
    *,
    repo_root: Path,
    run_id: str,
    before_text: str,
    after_text: str,
    now: datetime | None = None,
) -> IssueNoteAppendResult:
    if before_text == after_text:
        raise RallyStateError("Issue edit diff requires changed text.")

    return append_issue_event(
        repo_root=repo_root,
        run_id=run_id,
        title="user edited issue.md",
        source="rally resume --edit",
        detail_lines=(),
        body=_render_issue_edit_diff(before_text=before_text, after_text=after_text),
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
    turn_index: int | None = None,
    now: datetime | None = None,
) -> IssueNoteAppendResult:
    if not run_id.strip():
        raise RallyStateError("Run id must not be empty.")
    if turn_index is not None and turn_index < 1:
        raise RallyStateError("Turn index must be 1 or greater when present.")

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
        turn_index=turn_index,
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


def load_original_issue_text(*, repo_root: Path, run_id: str) -> str:
    issue_file = _resolve_issue_file(repo_root=repo_root, run_id=run_id)
    snapshot_file = _find_earliest_issue_snapshot(issue_file=issue_file)
    if snapshot_file is not None:
        original_text = extract_original_issue_text(snapshot_file.read_text(encoding="utf-8"))
        if original_text.strip():
            return original_text

    if not issue_file.is_file():
        raise RallyStateError(f"Issue log does not exist: `{issue_file}`.")
    original_text = extract_original_issue_text(issue_file.read_text(encoding="utf-8"))
    if not original_text.strip():
        raise RallyStateError(f"Could not recover the original issue from `{issue_file}`.")
    return original_text


def load_issue_current_view(*, repo_root: Path, run_id: str) -> IssueCurrentView:
    issue_file = _resolve_issue_file(repo_root=repo_root, run_id=run_id)
    if not issue_file.is_file():
        raise RallyStateError(f"Issue log does not exist: `{issue_file}`.")

    issue_text = issue_file.read_text(encoding="utf-8")
    blocks = _list_rally_blocks(issue_text)
    latest_blocked = blocks[-1].markdown if blocks and blocks[-1].title == "Rally Blocked" else None
    return IssueCurrentView(
        run_id=run_id,
        opening_issue=extract_current_issue_text(issue_text),
        latest_turn_result=_latest_block_markdown(blocks=blocks, title="Rally Turn Result"),
        latest_note=_latest_block_markdown(blocks=blocks, title="Rally Note"),
        latest_blocked=latest_blocked,
    )


def render_issue_current_view(*, repo_root: Path, run_id: str) -> str:
    return load_issue_current_view(repo_root=repo_root, run_id=run_id).render_markdown()


def load_current_issue_text(*, repo_root: Path, run_id: str) -> str:
    issue_file = _resolve_issue_file(repo_root=repo_root, run_id=run_id)
    if not issue_file.is_file():
        raise RallyStateError(f"Issue log does not exist: `{issue_file}`.")
    return extract_current_issue_text(issue_file.read_text(encoding="utf-8"))


def extract_original_issue_text(issue_text: str) -> str:
    return extract_current_issue_text(issue_text)


def extract_current_issue_text(issue_text: str) -> str:
    marker_index = issue_text.find(ORIGINAL_ISSUE_END_MARKER)
    if marker_index >= 0:
        return _normalize_original_issue_text(issue_text[:marker_index])

    block_start = _find_first_rally_block_start(issue_text)
    if block_start is None:
        return _normalize_original_issue_text(issue_text)
    return _normalize_original_issue_text(issue_text[:block_start])


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


def _normalize_note_fields(note_fields: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    normalized_fields: list[tuple[str, str]] = []
    seen_keys: set[str] = set()

    for raw_key, raw_value in note_fields:
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            raise RallyStateError("Note fields must use string keys and values.")

        key = raw_key.strip()
        value = raw_value.strip()
        if not key:
            raise RallyStateError("Note field keys must not be empty.")
        if not _NOTE_FIELD_KEY_PATTERN.fullmatch(key):
            raise RallyStateError(
                "Note field keys must match `[a-z][a-z0-9_]*`."
            )
        if not value:
            raise RallyStateError(f"Note field `{key}` must not have an empty value.")
        if key in seen_keys:
            raise RallyStateError(f"Note field `{key}` is duplicated.")
        if "`" in value:
            raise RallyStateError(f"Note field `{key}` must not contain backticks.")
        if "\n" in value or "\r" in value:
            raise RallyStateError(f"Note field `{key}` must stay on one line.")

        seen_keys.add(key)
        normalized_fields.append((key, value))

    return normalized_fields


def _render_issue_edit_diff(*, before_text: str, after_text: str) -> str:
    diff_text = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            after_text.splitlines(keepends=True),
            fromfile="before/issue.md",
            tofile="after/issue.md",
        )
    )
    if diff_text and not diff_text.endswith("\n"):
        diff_text += "\n"
    return f"```diff\n{diff_text}```"


def _format_issue_block(
    *,
    run_id: str,
    title: str,
    source: str,
    detail_lines: list[str],
    body: str | None,
    turn_index: int | None,
    timestamp: datetime,
) -> str:
    rendered_time = timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    lines = [
        f"## {title}",
        f"- Run ID: `{run_id}`",
    ]
    if turn_index is not None:
        lines.append(f"- Turn: `{turn_index}`")
    lines.extend(
        [
            f"- Time: `{rendered_time}`",
            f"- Source: `{source}`",
        ]
    )
    lines.extend(f"- {line}" for line in detail_lines)
    if body:
        lines.extend(("", body))
    return "\n".join(lines) + "\n"


def _append_block(*, current_text: str, block: str) -> str:
    if not current_text.strip():
        return f"{current_text}{block}"
    prefix = current_text.rstrip("\n")
    if _should_insert_original_issue_marker(current_text):
        return f"{prefix}\n\n{ORIGINAL_ISSUE_END_MARKER}\n\n---\n\n{block}"
    return f"{prefix}\n\n---\n\n{block}"


def _write_snapshot(*, issue_file: Path, timestamp: datetime) -> Path:
    history_dir = issue_file.parent.parent / "issue_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = history_dir / f"{_snapshot_stamp(timestamp)}-issue.md"
    snapshot_file.write_text(issue_file.read_text(encoding="utf-8"), encoding="utf-8")
    return snapshot_file


def _snapshot_stamp(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _find_earliest_issue_snapshot(*, issue_file: Path) -> Path | None:
    history_dir = issue_file.parent.parent / "issue_history"
    if not history_dir.is_dir():
        return None
    snapshots = sorted(history_dir.glob("*-issue.md"))
    return snapshots[0] if snapshots else None


def _find_first_rally_block_start(issue_text: str) -> int | None:
    candidates: list[int] = []
    for title in _RALLY_BLOCK_TITLES:
        divider_match = issue_text.find(f"\n\n---\n\n## {title}\n")
        if divider_match >= 0:
            candidates.append(divider_match)
        if issue_text.startswith(f"## {title}\n"):
            candidates.append(0)
    return min(candidates) if candidates else None


def _list_rally_blocks(issue_text: str) -> list[IssueLedgerBlock]:
    matches = list(_RALLY_BLOCK_PATTERN.finditer(issue_text))
    blocks: list[IssueLedgerBlock] = []
    for index, match in enumerate(matches):
        block_start = match.start(1)
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(issue_text)
        blocks.append(
            IssueLedgerBlock(
                title=match.group("title"),
                markdown=issue_text[block_start:block_end].rstrip("\n"),
            )
        )
    return blocks


def _latest_block_markdown(*, blocks: list[IssueLedgerBlock], title: str) -> str | None:
    for block in reversed(blocks):
        if block.title == title:
            return block.markdown
    return None


def _normalize_original_issue_text(issue_text: str) -> str:
    if not issue_text.strip():
        return ""
    return issue_text.rstrip("\n") + "\n"


def _should_insert_original_issue_marker(issue_text: str) -> bool:
    if ORIGINAL_ISSUE_END_MARKER in issue_text:
        return False
    return _find_first_rally_block_start(issue_text) is None
