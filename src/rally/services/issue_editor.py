from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence, TextIO

EditorRunner = Callable[..., subprocess.CompletedProcess[str]]

_ISSUE_EDITOR_PROMPT = """<!-- RALLY_ISSUE_PROMPT_START -->
Write the issue below.
Say what you want in plain words.
Name the poem type and the subject if the flow needs them.
Save and quit to continue.
Leave the file blank to cancel.
<!-- RALLY_ISSUE_PROMPT_END -->

"""


@dataclass(frozen=True)
class IssueEditorResult:
    status: str
    cleaned_text: str | None = None
    reason: str | None = None


def resolve_interactive_issue_editor(
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...] | None:
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    if not (_stream_is_tty(input_stream) and _stream_is_tty(output_stream)):
        return None

    env = os.environ if environ is None else environ
    path = env.get("PATH")
    for name in ("VISUAL", "EDITOR"):
        command = _parse_editor_command(env.get(name))
        if command is not None and _command_exists(command[0], path=path):
            return command

    for fallback in ("vim", "vi"):
        if _command_exists(fallback, path=path):
            return (fallback,)
    return None


def edit_issue_file_in_editor(
    *,
    issue_path: Path,
    editor_command: Sequence[str],
    run: EditorRunner = subprocess.run,
) -> IssueEditorResult:
    issue_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="rally-issue-",
        suffix=".md",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(_ISSUE_EDITOR_PROMPT)

    try:
        try:
            completed = run([*editor_command, str(temp_path)], check=False)
        except OSError:
            return IssueEditorResult(status="cancelled", reason="launch_failed")

        raw_text = temp_path.read_text(encoding="utf-8")
    finally:
        temp_path.unlink(missing_ok=True)

    if completed.returncode != 0:
        return IssueEditorResult(status="cancelled", reason="editor_exit")

    cleaned_text = clean_issue_editor_text(raw_text)
    if not cleaned_text.strip():
        return IssueEditorResult(status="cancelled", reason="blank_issue")

    issue_path.write_text(cleaned_text, encoding="utf-8")
    return IssueEditorResult(status="saved", cleaned_text=cleaned_text)


def clean_issue_editor_text(raw_text: str) -> str:
    if raw_text.startswith(_ISSUE_EDITOR_PROMPT):
        return _trim_leading_blank_lines(raw_text.removeprefix(_ISSUE_EDITOR_PROMPT))
    return raw_text


def _parse_editor_command(raw_value: str | None) -> tuple[str, ...] | None:
    if raw_value is None or not raw_value.strip():
        return None
    try:
        parts = tuple(shlex.split(raw_value))
    except ValueError:
        return None
    return parts or None


def _command_exists(command: str, *, path: str | None) -> bool:
    return shutil.which(command, path=path) is not None


def _stream_is_tty(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except OSError:
        return False


def _trim_leading_blank_lines(text: str) -> str:
    lines = text.splitlines(keepends=True)
    while lines and not lines[0].strip():
        lines.pop(0)
    return "".join(lines)
