from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Protocol, TextIO

from rally.adapters.base import (
    AdapterSessionRecord,
    prepare_interview_artifacts,
    record_interview_session,
)
from rally.adapters.claude_code.interview import ClaudePopenFactory, describe_claude_interview_launch, run_claude_interview_turn
from rally.adapters.codex.interview import CodexInterviewSession, CodexPopenFactory
from rally.adapters.registry import get_adapter
from rally.domain.flow import FlowAgent, FlowDefinition, flow_agent_key_to_slug
from rally.domain.interview import (
    InterviewCommandResult,
    InterviewLaunch,
    InterviewReply,
    InterviewRequest,
    TextDeltaCallback,
)
from rally.domain.run import RunRecord, RunState
from rally.errors import RallyStateError, RallyUsageError
from rally.services.flow_build import ensure_flow_assets_built
from rally.services.flow_loader import load_flow_definition
from rally.services.home_materializer import prepare_interview_home
from rally.services.run_events import RunEventRecorder
from rally.services.run_store import (
    archive_runs_dir,
    find_run_dir,
    flow_lock,
    load_run_record,
    load_run_state,
)
from rally.services.workspace import WorkspaceContext, workspace_context_from_root
from rally.services.workspace_sync import sync_workspace_builtins

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


class InterviewDriver(Protocol):
    def describe_launch(self, *, message_index: int) -> InterviewLaunch:
        """Describe the first adapter launch before the first model call."""

    def ask(
        self,
        *,
        question: str,
        message_index: int,
        on_text_delta: TextDeltaCallback | None = None,
    ) -> InterviewReply:
        """Ask one question inside the active interview session."""

    def close(self) -> str:
        """Close any live adapter state and return unread stderr text."""


def run_interview(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    request: InterviewRequest,
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    subprocess_run: SubprocessRunner = subprocess.run,
    claude_popen_factory: ClaudePopenFactory = subprocess.Popen,
    codex_popen_factory: CodexPopenFactory = subprocess.Popen,
) -> InterviewCommandResult:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    repo_root = workspace_context.workspace_root
    run_dir = find_run_dir(repo_root=repo_root, run_id=request.run_id)
    if run_dir.is_relative_to(archive_runs_dir(repo_root)):
        raise RallyUsageError(f"Run `{request.run_id}` is archived and cannot be interviewed.")
    run_record = load_run_record(run_dir=run_dir)
    recorder = RunEventRecorder(
        run_dir=run_dir,
        run_id=run_record.id,
        flow_code=run_record.flow_code,
    )
    driver: InterviewDriver | None = None
    artifacts = None
    agent = None
    interview_id = ""
    source_session = None
    flow = None
    run_home = None
    prompt_text = ""
    diagnostic_session_id: str | None = None
    message_index = 0

    try:
        with flow_lock(repo_root=repo_root, flow_code=run_record.flow_code):
            sync_workspace_builtins(workspace=workspace_context)
            ensure_flow_assets_built(workspace=workspace_context, flow_name=run_record.flow_name)
            flow = load_flow_definition(repo_root=repo_root, flow_name=run_record.flow_name)
            state = load_run_state(run_dir=run_dir)
            agent = _resolve_target_agent(flow=flow, state=state, requested_agent_slug=request.agent_slug)
            run_home = prepare_interview_home(
                workspace=workspace_context,
                flow=flow,
                run_record=run_record,
                event_recorder=recorder,
            )
            interview_id = _allocate_interview_id(run_home=run_home, agent_slug=agent.slug)
            artifacts = prepare_interview_artifacts(
                run_home=run_home,
                agent_slug=agent.slug,
                interview_id=interview_id,
            )
            source_session = _load_source_session(
                run_home=run_home,
                flow=flow,
                agent=agent,
                fork=request.fork,
            )
            prompt_text = _build_interview_prompt(
                run_home=run_home,
                run_record=run_record,
                state=state,
                flow=flow,
                agent=agent,
                request=request,
                source_session=source_session,
            )
            artifacts.prompt_file.write_text(prompt_text, encoding="utf-8")
            artifacts.transcript_file.touch(exist_ok=True)
            artifacts.raw_events_file.touch(exist_ok=True)
            artifacts.stderr_file.touch(exist_ok=True)
            record_interview_session(
                interview_dir=artifacts.interview_dir,
                interview_id=interview_id,
                adapter_name=flow.adapter.name,
                agent_slug=agent.slug,
                mode="fork" if request.fork else "fresh",
                source_session_id=source_session.session_id if source_session is not None else None,
                cwd=run_home,
            )

        driver = _open_interview_driver(
            workspace=workspace_context,
            run_home=run_home,
            flow=flow,
            run_record=run_record,
            agent=agent,
            prompt_text=prompt_text,
            fork=request.fork,
            source_session=source_session,
            subprocess_run=subprocess_run,
            claude_popen_factory=claude_popen_factory,
            codex_popen_factory=codex_popen_factory,
        )
        launch_written = False
        # Interview chat explains doctrine. It is not a Rally turn and never
        # writes a TurnResult, route change, or issue note.
        _write_banner(
            output_stream=output_stream,
            run_record=run_record,
            agent=agent,
            adapter_name=flow.adapter.name,
            interview_id=interview_id,
            mode="fork" if request.fork else "fresh",
            source_session=source_session,
        )
        while True:
            output_stream.write("you> ")
            output_stream.flush()
            question = input_stream.readline()
            if question == "":
                break
            question = question.rstrip("\n")
            if not question.strip():
                continue
            if question.strip().lower() in {"/exit", "exit", "quit"}:
                break
            message_index += 1
            _append_transcript_entry(
                transcript_file=artifacts.transcript_file,
                interview_id=interview_id,
                agent=agent,
                message_index=message_index,
                role="user",
                text=question,
            )
            _emit_interview_message_event(
                recorder=recorder,
                interview_id=interview_id,
                mode="fork" if request.fork else "fresh",
                agent=agent,
                message_index=message_index,
                role="user",
                text=question,
                session_id=diagnostic_session_id,
            )
            if not launch_written:
                launch = driver.describe_launch(message_index=message_index)
                _write_launch_record(
                    launch_file=artifacts.launch_file,
                    mode="fork" if request.fork else "fresh",
                    source_session=source_session,
                    launch=launch,
                )
                _emit_interview_launch_event(
                    recorder=recorder,
                    interview_id=interview_id,
                    mode="fork" if request.fork else "fresh",
                    adapter_name=flow.adapter.name,
                    agent=agent,
                    source_session=source_session,
                    launch=launch,
                )
                launch_written = True
            printer = _LiveReplyPrinter(output_stream=output_stream)
            reply = driver.ask(
                question=question,
                message_index=message_index,
                on_text_delta=printer.push,
            )
            diagnostic_session_id = reply.session_id or diagnostic_session_id
            _append_raw_events(raw_events_file=artifacts.raw_events_file, raw_event_lines=reply.raw_event_lines)
            _append_stderr(stderr_file=artifacts.stderr_file, stderr_text=reply.stderr_text)
            record_interview_session(
                interview_dir=artifacts.interview_dir,
                interview_id=interview_id,
                adapter_name=flow.adapter.name,
                agent_slug=agent.slug,
                mode="fork" if request.fork else "fresh",
                diagnostic_session_id=reply.session_id,
                source_session_id=source_session.session_id if source_session is not None else None,
                cwd=Path(reply.cwd),
            )
            _append_transcript_entry(
                transcript_file=artifacts.transcript_file,
                interview_id=interview_id,
                agent=agent,
                message_index=message_index,
                role="assistant",
                text=reply.text,
                session_id=reply.session_id,
            )
            _emit_interview_message_event(
                recorder=recorder,
                interview_id=interview_id,
                mode="fork" if request.fork else "fresh",
                agent=agent,
                message_index=message_index,
                role="assistant",
                text=reply.text,
                session_id=reply.session_id,
            )
            printer.finish(reply.text)
    finally:
        if driver is not None:
            close_stderr = driver.close()
            if artifacts is not None:
                _append_stderr(stderr_file=artifacts.stderr_file, stderr_text=close_stderr)
        if agent is not None and interview_id:
            _emit_interview_close_event(
                recorder=recorder,
                interview_id=interview_id,
                mode="fork" if request.fork else "fresh",
                agent=agent,
                message_count=message_index,
                session_id=diagnostic_session_id,
            )
        recorder.close()
    return InterviewCommandResult(
        run_id=run_record.id,
        agent_slug=agent.slug,
        interview_id=interview_id,
        mode="fork" if request.fork else "fresh",
        message=(
            f"Closed {('forked' if request.fork else 'fresh')} interview "
            f"`{interview_id}` for run `{run_record.id}` agent `{agent.slug}`."
        ),
    )


def _open_interview_driver(
    *,
    workspace: WorkspaceContext,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    prompt_text: str,
    fork: bool,
    source_session: AdapterSessionRecord | None,
    subprocess_run: SubprocessRunner,
    claude_popen_factory: ClaudePopenFactory,
    codex_popen_factory: CodexPopenFactory,
) -> InterviewDriver:
    if flow.adapter.name == "claude_code":
        return _ClaudeInterviewDriver(
            workspace=workspace,
            run_home=run_home,
            flow=flow,
            run_record=run_record,
            agent=agent,
            prompt_text=prompt_text,
            fork=fork,
            source_session=source_session,
            subprocess_run=subprocess_run,
            popen_factory=claude_popen_factory,
        )
    if flow.adapter.name == "codex":
        return CodexInterviewSession(
            workspace=workspace,
            run_home=run_home,
            flow=flow,
            run_record=run_record,
            agent=agent,
            interview_prompt=prompt_text,
            fork_session=fork,
            source_session_id=source_session.session_id if source_session is not None else None,
            popen_factory=codex_popen_factory,
        )
    raise RallyUsageError(
        f"Adapter `{flow.adapter.name}` does not support `rally interview` yet."
    )


def _coerce_workspace(
    *,
    workspace: WorkspaceContext | None,
    repo_root: Path | None,
) -> WorkspaceContext:
    if workspace is not None and repo_root is not None:
        raise RallyStateError("Pass either `workspace` or `repo_root`, not both.")
    if workspace is not None:
        return workspace
    if repo_root is None:
        raise RallyStateError("Interview runtime needs either `workspace` or `repo_root`.")
    return workspace_context_from_root(repo_root)


def _resolve_target_agent(
    *,
    flow: FlowDefinition,
    state: RunState,
    requested_agent_slug: str | None,
) -> FlowAgent:
    if requested_agent_slug is not None:
        try:
            return flow.agent_by_slug(requested_agent_slug)
        except KeyError as exc:
            raise RallyUsageError(
                f"Flow `{flow.name}` has no agent slug `{requested_agent_slug}`."
            ) from exc
    if state.current_agent_slug is not None:
        return flow.agent_by_slug(state.current_agent_slug)
    if state.current_agent_key is not None:
        return flow.agent_by_slug(flow_agent_key_to_slug(state.current_agent_key))
    raise RallyUsageError(
        "Run has no current agent. Pass `--agent <slug>` to choose one."
    )


def _load_source_session(
    *,
    run_home: Path,
    flow: FlowDefinition,
    agent: FlowAgent,
    fork: bool,
) -> AdapterSessionRecord | None:
    if not fork:
        return None
    source_session = get_adapter(flow.adapter.name).load_session(run_home=run_home, agent_slug=agent.slug)
    if source_session is None:
        raise RallyUsageError(
            f"Run has no saved live session for `{agent.slug}`, so `--fork` cannot start."
        )
    return source_session


def _build_interview_prompt(
    *,
    run_home: Path,
    run_record: RunRecord,
    state: RunState,
    flow: FlowDefinition,
    agent: FlowAgent,
    request: InterviewRequest,
    source_session: AdapterSessionRecord | None,
) -> str:
    interview_path = Path("home") / "agents" / agent.slug / "INTERVIEW.md"
    agent_path = Path("home") / "agents" / agent.slug / "AGENTS.md"
    interview_markdown_text = (run_home / "agents" / agent.slug / "INTERVIEW.md").read_text(encoding="utf-8").rstrip()
    context_lines = [
        "## Rally Interview Context",
        f"- Run ID: `{run_record.id}`",
        f"- Flow: `{flow.name}` (`{flow.code}`)",
        f"- Agent Key: `{agent.key}`",
        f"- Agent Slug: `{agent.slug}`",
        f"- Doctrine File: `{agent_path.as_posix()}`",
        f"- Interview File: `{interview_path.as_posix()}`",
        f"- Run Status: `{state.status.value}`",
        f"- Mode: `{'fork' if request.fork else 'fresh'}`",
        "- Boundary: Do not change the live run. Do not do normal work.",
    ]
    if source_session is not None:
        context_lines.append(f"- Live Session ID: `{source_session.session_id}`")
    return interview_markdown_text + "\n\n" + "\n".join(context_lines) + "\n"


def _allocate_interview_id(*, run_home: Path, agent_slug: str) -> str:
    interviews_root = run_home / "interviews" / agent_slug
    interviews_root.mkdir(parents=True, exist_ok=True)
    highest = 0
    for existing in interviews_root.iterdir():
        if not existing.is_dir():
            continue
        if not existing.name.startswith("interview-"):
            continue
        suffix = existing.name.removeprefix("interview-")
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"interview-{highest + 1:03d}"


def _write_banner(
    *,
    output_stream: TextIO,
    run_record: RunRecord,
    agent: FlowAgent,
    adapter_name: str,
    interview_id: str,
    mode: str,
    source_session: AdapterSessionRecord | None,
) -> None:
    lines = [
        "Rally Interview",
        f"Run: {run_record.id}",
        f"Agent: {agent.slug}",
        f"Adapter: {adapter_name}",
        f"Mode: {mode}",
        f"Interview: {interview_id}",
    ]
    if source_session is not None:
        lines.append(f"Live session: {source_session.session_id}")
    lines.append("Type `/exit` to stop.")
    output_stream.write("\n".join(lines) + "\n\n")
    output_stream.flush()


def _write_launch_record(
    *,
    launch_file: Path,
    mode: str,
    source_session: AdapterSessionRecord | None,
    launch: InterviewLaunch,
) -> None:
    keep_keys = sorted(
        key
        for key in launch.env
        if key.startswith("RALLY_")
        or key in {"ENABLE_CLAUDEAI_MCP_SERVERS", "CODEX_HOME"}
    )
    payload = {
        "ts": _render_time(),
        "mode": mode,
        "source_session_id": source_session.session_id if source_session is not None else None,
        "command": list(launch.command),
        "cwd": launch.cwd,
        "env": {key: launch.env[key] for key in keep_keys},
    }
    launch_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _emit_interview_launch_event(
    *,
    recorder: RunEventRecorder,
    interview_id: str,
    mode: str,
    adapter_name: str,
    agent: FlowAgent,
    source_session: AdapterSessionRecord | None,
    launch: InterviewLaunch,
) -> None:
    recorder.emit(
        source="interview",
        kind="lifecycle",
        code="LAUNCH",
        message=(
            f"Forked live `{adapter_name}` session into interview `{interview_id}`."
            if mode == "fork"
            else f"Launched fresh `{adapter_name}` interview `{interview_id}`."
        ),
        agent_key=agent.key,
        agent_slug=agent.slug,
        data={
            "interview_id": interview_id,
            "mode": mode,
            "command": list(launch.command),
            "cwd": launch.cwd,
            "source_session_id": source_session.session_id if source_session is not None else None,
        },
    )


def _emit_interview_message_event(
    *,
    recorder: RunEventRecorder,
    interview_id: str,
    mode: str,
    agent: FlowAgent,
    message_index: int,
    role: str,
    text: str,
    session_id: str | None,
) -> None:
    recorder.emit(
        source="interview",
        kind=role,
        code="USER" if role == "user" else "ASSIST",
        message=text or "[No reply text returned.]",
        agent_key=agent.key,
        agent_slug=agent.slug,
        data={
            "interview_id": interview_id,
            "mode": mode,
            "message_index": message_index,
            "role": role,
            "session_id": session_id,
        },
    )


def _emit_interview_close_event(
    *,
    recorder: RunEventRecorder,
    interview_id: str,
    mode: str,
    agent: FlowAgent,
    message_count: int,
    session_id: str | None,
) -> None:
    recorder.emit(
        source="interview",
        kind="lifecycle",
        code="CLOSE",
        message=f"Closed {mode} interview `{interview_id}`.",
        agent_key=agent.key,
        agent_slug=agent.slug,
        data={
            "interview_id": interview_id,
            "mode": mode,
            "message_count": message_count,
            "session_id": session_id,
        },
    )


def _append_transcript_entry(
    *,
    transcript_file: Path,
    interview_id: str,
    agent: FlowAgent,
    message_index: int,
    role: str,
    text: str,
    session_id: str | None = None,
) -> None:
    payload = {
        "ts": _render_time(),
        "interview_id": interview_id,
        "agent_key": agent.key,
        "agent_slug": agent.slug,
        "turn_index": message_index,
        "role": role,
        "text": text,
        "session_id": session_id,
    }
    with transcript_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True))
        handle.write("\n")


def _append_raw_events(*, raw_events_file: Path, raw_event_lines: tuple[str, ...]) -> None:
    if not raw_event_lines:
        return
    with raw_events_file.open("a", encoding="utf-8") as handle:
        for line in raw_event_lines:
            handle.write(line.rstrip())
            handle.write("\n")


def _append_stderr(*, stderr_file: Path, stderr_text: str) -> None:
    if not stderr_text.strip():
        return
    with stderr_file.open("a", encoding="utf-8") as handle:
        handle.write(stderr_text.rstrip())
        handle.write("\n")


def _render_time() -> str:
    return datetime.now(UTC).astimezone(UTC).isoformat().replace("+00:00", "Z")


class _ClaudeInterviewDriver:
    def __init__(
        self,
        *,
        workspace: WorkspaceContext,
        run_home: Path,
        flow: FlowDefinition,
        run_record: RunRecord,
        agent: FlowAgent,
        prompt_text: str,
        fork: bool,
        source_session: AdapterSessionRecord | None,
        subprocess_run: SubprocessRunner,
        popen_factory: ClaudePopenFactory,
    ) -> None:
        self._workspace = workspace
        self._run_home = run_home
        self._flow = flow
        self._run_record = run_record
        self._agent = agent
        self._prompt_text = prompt_text
        self._fork = fork
        self._source_session = source_session
        self._subprocess_run = subprocess_run
        self._popen_factory = popen_factory
        self._diagnostic_session_id: str | None = None

    def describe_launch(self, *, message_index: int) -> InterviewLaunch:
        return describe_claude_interview_launch(
            workspace=self._workspace,
            run_home=self._run_home,
            flow=self._flow,
            run_record=self._run_record,
            agent=self._agent,
            interview_prompt=self._prompt_text,
            message_index=message_index,
            previous_session_id=self._diagnostic_session_id,
            source_session_id=self._source_session.session_id if self._source_session is not None else None,
            fork_session=self._fork and self._diagnostic_session_id is None,
        )

    def ask(
        self,
        *,
        question: str,
        message_index: int,
        on_text_delta: TextDeltaCallback | None = None,
    ) -> InterviewReply:
        reply = run_claude_interview_turn(
            workspace=self._workspace,
            run_home=self._run_home,
            flow=self._flow,
            run_record=self._run_record,
            agent=self._agent,
            interview_prompt=self._prompt_text,
            user_message=question,
            message_index=message_index,
            previous_session_id=self._diagnostic_session_id,
            source_session_id=self._source_session.session_id if self._source_session is not None else None,
            fork_session=self._fork and self._diagnostic_session_id is None,
            on_text_delta=on_text_delta,
            subprocess_run=self._subprocess_run,
            popen_factory=self._popen_factory,
        )
        self._diagnostic_session_id = reply.session_id
        return reply

    def close(self) -> str:
        return ""


class _LiveReplyPrinter:
    def __init__(self, *, output_stream: TextIO) -> None:
        self._output_stream = output_stream
        self._chunks: list[str] = []
        self._started = False
        self._lock = threading.Lock()

    def push(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            if not self._started:
                self._output_stream.write("agent> ")
                self._started = True
            self._chunks.append(text)
            self._output_stream.write(text)
            self._output_stream.flush()

    def finish(self, final_text: str) -> None:
        display_text = final_text or "[No reply text returned.]"
        with self._lock:
            if not self._started:
                self._output_stream.write("agent> ")
                self._output_stream.write(display_text.rstrip())
                self._output_stream.write("\n\n")
                self._output_stream.flush()
                return
            streamed_text = "".join(self._chunks)
            if display_text.startswith(streamed_text):
                suffix = display_text[len(streamed_text) :]
                if suffix:
                    self._output_stream.write(suffix)
            self._output_stream.write("\n\n")
            self._output_stream.flush()
