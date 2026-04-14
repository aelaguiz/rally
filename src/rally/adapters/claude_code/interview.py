from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Callable

from rally.adapters.claude_code.launcher import build_claude_code_launch_env
from rally.domain.flow import FlowAgent, FlowDefinition
from rally.domain.interview import InterviewLaunch, InterviewReply, TextDeltaCallback
from rally.domain.run import RunRecord
from rally.errors import RallyStateError
from rally.services.workspace import WorkspaceContext

_INSPECT_ONLY_TOOLS = ("Read", "Grep", "Glob")
ClaudePopenFactory = Callable[..., subprocess.Popen[str]]


def describe_claude_interview_launch(
    *,
    workspace: WorkspaceContext,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    interview_prompt: str,
    message_index: int,
    previous_session_id: str | None,
    source_session_id: str | None,
    fork_session: bool,
) -> InterviewLaunch:
    command, env = _build_claude_interview_command_and_env(
        workspace=workspace,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        interview_prompt=interview_prompt,
        message_index=message_index,
        previous_session_id=previous_session_id,
        source_session_id=source_session_id,
        fork_session=fork_session,
    )
    return InterviewLaunch(
        command=tuple(command),
        cwd=str(run_home.resolve()),
        env=env,
    )


def run_claude_interview_turn(
    *,
    workspace: WorkspaceContext,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    interview_prompt: str,
    user_message: str,
    message_index: int,
    previous_session_id: str | None,
    source_session_id: str | None,
    fork_session: bool,
    on_text_delta: TextDeltaCallback | None = None,
    subprocess_run=subprocess.run,
    popen_factory=subprocess.Popen,
) -> InterviewReply:
    command, env = _build_claude_interview_command_and_env(
        workspace=workspace,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        interview_prompt=interview_prompt,
        message_index=message_index,
        previous_session_id=previous_session_id,
        source_session_id=source_session_id,
        fork_session=fork_session,
    )
    if subprocess_run is not subprocess.run and popen_factory is subprocess.Popen:
        return _run_claude_interview_capture(
            command=command,
            run_home=run_home,
            env=env,
            agent=agent,
            user_message=user_message,
            subprocess_run=subprocess_run,
        )
    return _run_claude_interview_stream(
        command=command,
        run_home=run_home,
        env=env,
        agent=agent,
        user_message=user_message,
        on_text_delta=on_text_delta,
        popen_factory=popen_factory,
    )


def _build_claude_interview_command_and_env(
    *,
    workspace: WorkspaceContext,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    interview_prompt: str,
    message_index: int,
    previous_session_id: str | None,
    source_session_id: str | None,
    fork_session: bool,
) -> tuple[list[str], dict[str, str]]:
    command = [
        "claude",
        "-p",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--verbose",
        "--bare",
        "--permission-mode",
        "dontAsk",
        "--tools",
        ",".join(_INSPECT_ONLY_TOOLS),
        "--allowedTools",
        ",".join(_INSPECT_ONLY_TOOLS),
    ]
    model = flow.adapter.args.get("model")
    if isinstance(model, str) and model.strip():
        command.extend(["--model", model.strip()])
    reasoning_effort = flow.adapter.args.get("reasoning_effort")
    if isinstance(reasoning_effort, str) and reasoning_effort.strip():
        command.extend(["--effort", reasoning_effort.strip()])

    if previous_session_id is not None:
        command.extend(["--resume", previous_session_id])
    elif fork_session:
        if not source_session_id:
            raise RallyStateError("Claude interview fork needs a source session id.")
        command.extend(["--resume", source_session_id, "--fork-session"])
    if previous_session_id is None:
        command.extend(["--system-prompt", interview_prompt])

    env = {
        **os.environ,
        **build_claude_code_launch_env(
            workspace_dir=workspace.workspace_root,
            cli_bin=workspace.cli_bin,
            run_id=run_record.id,
            flow_code=run_record.flow_code,
            agent_slug=agent.slug,
            turn_index=message_index,
        ),
    }
    return command, env


def _run_claude_interview_capture(
    *,
    command: list[str],
    run_home: Path,
    env: dict[str, str],
    agent: FlowAgent,
    user_message: str,
    subprocess_run,
) -> InterviewReply:
    completed = subprocess_run(
        command,
        input=user_message,
        capture_output=True,
        text=True,
        cwd=run_home,
        env=env,
        timeout=agent.timeout_sec,
        check=False,
    )
    raw_lines = tuple(line for line in completed.stdout.splitlines() if line.strip())
    session_id, assistant_text = _parse_claude_interview_output(raw_lines=raw_lines)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or assistant_text or "Claude interview failed."
        raise RallyStateError(f"Claude interview failed: {detail}")
    if session_id is None:
        raise RallyStateError("Claude interview did not report a diagnostic session id.")
    return InterviewReply(
        session_id=session_id,
        text=assistant_text,
        command=tuple(command),
        cwd=str(run_home.resolve()),
        env=env,
        raw_event_lines=raw_lines,
        stderr_text=completed.stderr,
    )


def _run_claude_interview_stream(
    *,
    command: list[str],
    run_home: Path,
    env: dict[str, str],
    agent: FlowAgent,
    user_message: str,
    on_text_delta: TextDeltaCallback | None,
    popen_factory,
) -> InterviewReply:
    process = popen_factory(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=run_home,
        env=env,
        text=True,
        bufsize=1,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise RallyStateError("Claude interview process must expose stdin, stdout, and stderr pipes.")

    raw_lines: list[str] = []
    stderr_chunks: list[str] = []
    worker_errors: list[BaseException] = []
    stderr_lock = threading.Lock()

    def _read_stdout() -> None:
        try:
            while True:
                raw_line = process.stdout.readline()
                if raw_line == "":
                    break
                stripped = raw_line.strip()
                if not stripped:
                    continue
                raw_lines.append(stripped)
                _emit_claude_partial_text(raw_line=stripped, on_text_delta=on_text_delta)
        except BaseException as exc:  # pragma: no cover - defensive thread handoff
            worker_errors.append(exc)

    def _read_stderr() -> None:
        try:
            while True:
                raw_line = process.stderr.readline()
                if raw_line == "":
                    break
                with stderr_lock:
                    stderr_chunks.append(raw_line)
        except BaseException as exc:  # pragma: no cover - defensive thread handoff
            worker_errors.append(exc)

    stdout_thread = threading.Thread(target=_read_stdout, name="rally-claude-interview-stdout", daemon=True)
    stderr_thread = threading.Thread(target=_read_stderr, name="rally-claude-interview-stderr", daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    try:
        process.stdin.write(user_message)
        process.stdin.close()
        try:
            process.wait(timeout=agent.timeout_sec)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait(timeout=1)
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            raise RallyStateError(
                f"Claude interview timed out after {agent.timeout_sec} seconds."
            ) from exc
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

    if worker_errors:
        raise RallyStateError("Claude interview stream reader failed.") from worker_errors[0]

    session_id, assistant_text = _parse_claude_interview_output(raw_lines=tuple(raw_lines))
    stderr_text = "".join(stderr_chunks)
    if process.returncode != 0:
        detail = stderr_text.strip() or assistant_text or "Claude interview failed."
        raise RallyStateError(f"Claude interview failed: {detail}")
    if session_id is None:
        raise RallyStateError("Claude interview did not report a diagnostic session id.")
    return InterviewReply(
        session_id=session_id,
        text=assistant_text,
        command=tuple(command),
        cwd=str(run_home.resolve()),
        env=env,
        raw_event_lines=tuple(raw_lines),
        stderr_text=stderr_text,
    )


def _parse_claude_interview_output(*, raw_lines: tuple[str, ...]) -> tuple[str | None, str]:
    session_id: str | None = None
    assistant_parts: list[str] = []
    for raw_line in raw_lines:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        session_id = _string_value(payload.get("session_id")) or session_id
        if payload.get("type") != "assistant":
            continue
        message = payload.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "text":
                continue
            text = _string_value(item.get("text"))
            if text:
                assistant_parts.append(text)
    return session_id, "\n".join(part.rstrip() for part in assistant_parts if part.strip()).strip()


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _emit_claude_partial_text(*, raw_line: str, on_text_delta: TextDeltaCallback | None) -> None:
    if on_text_delta is None:
        return
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict):
        return
    text = _extract_claude_partial_text(payload)
    if text:
        on_text_delta(text)


def _extract_claude_partial_text(payload: dict[str, object]) -> str | None:
    if payload.get("type") != "stream_event":
        return None
    delta = payload.get("delta")
    if isinstance(delta, dict):
        text = _string_value(delta.get("text"))
        if text is not None:
            return text
        text = _string_value(delta.get("delta"))
        if text is not None:
            return text
        text = _string_value(delta.get("value"))
        if text is not None:
            return text
    content_block = payload.get("content_block")
    if isinstance(content_block, dict):
        text = _string_value(content_block.get("text"))
        if text is not None:
            return text
    return None
