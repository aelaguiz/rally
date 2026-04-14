from __future__ import annotations

import json
import os
import selectors
import shutil
import subprocess
import time
import tomllib
from pathlib import Path
from typing import Mapping

from rally.adapters.base import (
    AdapterInvocation,
    AdapterReadinessFailure,
    AdapterSessionRecord,
    RallyAdapter,
    SubprocessRunner,
    TurnArtifactPaths,
)
from rally.adapters.claude_code.event_stream import ClaudeCodeEventStreamParser, extract_structured_output
from rally.adapters.claude_code.launcher import build_claude_code_launch_env, write_claude_code_launch_record
from rally.adapters.claude_code.session_store import (
    load_session as load_claude_code_session,
    prepare_turn_artifacts as prepare_claude_code_turn_artifacts,
    record_session as record_claude_code_session,
)
from rally.domain.flow import FlowAgent, FlowDefinition
from rally.domain.rooted_path import INTERNAL_PATH_ROOTS, expand_rooted_value
from rally.domain.run import RunRecord
from rally.errors import RallyConfigError
from rally.services.run_events import RunEventRecorder
from rally.services.workspace import WorkspaceContext

_ALLOWED_BUILTIN_TOOLS = (
    "Bash",
    "Edit",
    "Glob",
    "Grep",
    "NotebookEdit",
    "Read",
    "Skill",
    "TodoWrite",
    "ToolSearch",
    "WebFetch",
    "WebSearch",
    "Write",
)


class ClaudeCodeAdapter(RallyAdapter):
    name = "claude_code"
    display_name = "Claude Code"

    def validate_args(self, *, args: Mapping[str, object]) -> None:
        _validate_common_string_arg(args=args, key="model")
        _validate_common_string_arg(args=args, key="reasoning_effort")
        _reject_unknown_args(args=args, allowed={"model", "reasoning_effort"})

    def prepare_home(
        self,
        *,
        repo_root: Path,
        workspace: WorkspaceContext,
        run_home: Path,
        flow: FlowDefinition,
        run_record: RunRecord,
        event_recorder: RunEventRecorder | None,
    ) -> None:
        del workspace, run_record, event_recorder
        claude_root = run_home / "claude_code"
        claude_root.mkdir(parents=True, exist_ok=True)
        (claude_root / "mcp.json").write_text(
            json.dumps(_build_mcp_config(workspace_root=repo_root, run_home=run_home, flow=flow), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        _sync_claude_skills(run_home=run_home)

    def prepare_turn_artifacts(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        turn_index: int,
    ) -> TurnArtifactPaths:
        return prepare_claude_code_turn_artifacts(
            run_home=run_home,
            agent_slug=agent_slug,
            turn_index=turn_index,
        )

    def load_session(
        self,
        *,
        run_home: Path,
        agent_slug: str,
    ) -> AdapterSessionRecord | None:
        return load_claude_code_session(run_home=run_home, agent_slug=agent_slug)

    def record_session(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        session_id: str,
        cwd: Path,
        now=None,
        ) -> AdapterSessionRecord:
        return record_claude_code_session(
            run_home=run_home,
            agent_slug=agent_slug,
            session_id=session_id,
            cwd=cwd,
            now=now,
        )

    def check_turn_readiness(
        self,
        *,
        repo_root: Path,
        workspace: WorkspaceContext,
        run_dir: Path,
        run_home: Path,
        flow: FlowDefinition,
        run_record: RunRecord,
        agent: FlowAgent,
        turn_index: int,
        recorder: RunEventRecorder,
        subprocess_run: SubprocessRunner,
    ) -> AdapterReadinessFailure | None:
        del repo_root, workspace, run_dir, run_home, flow, run_record, agent, turn_index, recorder, subprocess_run
        return None

    def invoke(
        self,
        *,
        repo_root: Path,
        workspace: WorkspaceContext,
        run_dir: Path,
        run_home: Path,
        flow: FlowDefinition,
        run_record: RunRecord,
        agent: FlowAgent,
        prompt: str,
        previous_session: AdapterSessionRecord | None,
        artifacts: TurnArtifactPaths,
        recorder: RunEventRecorder,
        turn_index: int,
        subprocess_run: SubprocessRunner,
    ) -> AdapterInvocation:
        del repo_root
        command = [
            "claude",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-mode",
            "dontAsk",
            "--mcp-config",
            str(run_home / "claude_code" / "mcp.json"),
            "--strict-mcp-config",
            "--tools",
            ",".join(_ALLOWED_BUILTIN_TOOLS),
            "--allowedTools",
            ",".join(_ALLOWED_BUILTIN_TOOLS),
            "--json-schema",
            agent.compiled.final_output.schema_file.read_text(encoding="utf-8"),
        ]
        model = flow.adapter.args.get("model")
        if isinstance(model, str) and model.strip():
            command.extend(["--model", model.strip()])
        reasoning_effort = flow.adapter.args.get("reasoning_effort")
        if isinstance(reasoning_effort, str) and reasoning_effort.strip():
            command.extend(["--effort", reasoning_effort.strip()])
        if previous_session is not None:
            command.extend(["--resume", previous_session.session_id])

        env = {
            **os.environ,
            **build_claude_code_launch_env(
                workspace_dir=workspace.workspace_root,
                cli_bin=workspace.cli_bin,
                run_id=run_record.id,
                flow_code=run_record.flow_code,
                agent_slug=agent.slug,
                turn_index=turn_index,
            ),
        }
        write_claude_code_launch_record(
            run_dir=run_dir,
            turn_index=turn_index,
            agent_slug=agent.slug,
            command=command,
            cwd=run_home,
            env=env,
            timeout_sec=agent.timeout_sec,
        )
        recorder.emit(
            source="rally",
            kind="lifecycle",
            code="LAUNCH",
            message=(
                f"Resuming Claude Code session `{previous_session.session_id}`."
                if previous_session is not None
                else "Launching Claude Code."
            ),
            turn_index=turn_index,
            agent_key=agent.key,
            agent_slug=agent.slug,
            data={"command": command},
        )
        if subprocess_run is subprocess.run:
            return _stream_claude_code_invocation(
                command=command,
                prompt=prompt,
                cwd=run_home,
                env=env,
                timeout_sec=agent.timeout_sec,
                artifacts=artifacts,
                recorder=recorder,
                turn_index=turn_index,
                agent=agent,
            )
        return _capture_completed_invocation(
            command=command,
            prompt=prompt,
            cwd=run_home,
            env=env,
            timeout_sec=agent.timeout_sec,
            artifacts=artifacts,
            recorder=recorder,
            turn_index=turn_index,
            agent=agent,
            subprocess_run=subprocess_run,
        )


CLAUDE_CODE_ADAPTER = ClaudeCodeAdapter()


def _capture_completed_invocation(
    *,
    command: list[str],
    prompt: str,
    cwd: Path,
    env: dict[str, str],
    timeout_sec: int,
    artifacts: TurnArtifactPaths,
    recorder: RunEventRecorder,
    turn_index: int,
    agent: FlowAgent,
    subprocess_run: SubprocessRunner,
) -> AdapterInvocation:
    parser = ClaudeCodeEventStreamParser(
        turn_index=turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
    )
    try:
        completed = subprocess_run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=env,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_text = _coerce_stream_text(exc.stdout)
        stderr_tail = _coerce_stream_text(exc.stderr).strip()
        _replay_stdout_lines(stdout_text=stdout_text, artifacts=artifacts, parser=parser, recorder=recorder)
        stderr_text = f"claude -p timed out after {timeout_sec} seconds"
        if stderr_tail:
            stderr_text = f"{stderr_text}\n{stderr_tail}"
        _emit_stderr_events(
            recorder=recorder,
            turn_index=turn_index,
            agent=agent,
            stderr_text=stderr_text,
            level="error",
        )
        return AdapterInvocation(
            returncode=124,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            session_id=parser.session_id,
        )

    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    _replay_stdout_lines(stdout_text=stdout_text, artifacts=artifacts, parser=parser, recorder=recorder)
    _write_structured_output(stdout_text=stdout_text, last_message_file=artifacts.last_message_file)
    _emit_stderr_events(
        recorder=recorder,
        turn_index=turn_index,
        agent=agent,
        stderr_text=stderr_text,
        level="error" if completed.returncode != 0 else "warning",
    )
    return AdapterInvocation(
        returncode=completed.returncode,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        session_id=parser.session_id,
    )


def _stream_claude_code_invocation(
    *,
    command: list[str],
    prompt: str,
    cwd: Path,
    env: dict[str, str],
    timeout_sec: int,
    artifacts: TurnArtifactPaths,
    recorder: RunEventRecorder,
    turn_index: int,
    agent: FlowAgent,
) -> AdapterInvocation:
    parser = ClaudeCodeEventStreamParser(
        turn_index=turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=env,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    process.stdin.write(prompt)
    process.stdin.close()

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + timeout_sec
    timed_out = False

    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                process.kill()
                break

            ready = selector.select(timeout=min(0.25, remaining))
            if not ready:
                continue

            for key, _ in ready:
                line = key.fileobj.readline()
                if line == "":
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "stdout":
                    _append_text(artifacts.exec_jsonl_file, line)
                    stdout_chunks.append(line)
                    for draft in parser.consume_stdout_line(line):
                        recorder.emit_draft(draft)
                    continue
                stderr_chunks.append(line)
    finally:
        selector.close()

    remaining_stdout, remaining_stderr = process.communicate()
    if remaining_stdout:
        _append_text(artifacts.exec_jsonl_file, remaining_stdout)
        stdout_chunks.append(remaining_stdout)
        _replay_stdout_lines(
            stdout_text=remaining_stdout,
            artifacts=artifacts,
            parser=parser,
            recorder=recorder,
            append_to_file=False,
        )
    if remaining_stderr:
        stderr_chunks.append(remaining_stderr)

    for draft in parser.flush():
        recorder.emit_draft(draft)

    stdout_text = "".join(stdout_chunks)
    stderr_text = "".join(stderr_chunks)
    _write_structured_output(stdout_text=stdout_text, last_message_file=artifacts.last_message_file)
    if timed_out:
        timeout_text = f"claude -p timed out after {timeout_sec} seconds"
        stderr_text = f"{timeout_text}\n{stderr_text}".strip()
        _emit_stderr_events(
            recorder=recorder,
            turn_index=turn_index,
            agent=agent,
            stderr_text=stderr_text,
            level="error",
        )
        return AdapterInvocation(
            returncode=124,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            session_id=parser.session_id,
        )

    _emit_stderr_events(
        recorder=recorder,
        turn_index=turn_index,
        agent=agent,
        stderr_text=stderr_text,
        level="error" if process.returncode else "warning",
    )
    return AdapterInvocation(
        returncode=process.returncode or 0,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        session_id=parser.session_id,
    )


def _replay_stdout_lines(
    *,
    stdout_text: str,
    artifacts: TurnArtifactPaths,
    parser: ClaudeCodeEventStreamParser,
    recorder: RunEventRecorder,
    append_to_file: bool = True,
) -> None:
    if append_to_file and stdout_text:
        artifacts.exec_jsonl_file.write_text(stdout_text, encoding="utf-8")
    for line in stdout_text.splitlines(keepends=True):
        for draft in parser.consume_stdout_line(line):
            recorder.emit_draft(draft)


def _emit_stderr_events(
    *,
    recorder: RunEventRecorder,
    turn_index: int,
    agent: FlowAgent,
    stderr_text: str,
    level: str,
) -> None:
    if not stderr_text.strip():
        return
    for raw_line in stderr_text.splitlines():
        if not raw_line.strip():
            continue
        recorder.emit(
            source="claude_code",
            kind="warning",
            code="STDERR",
            message=raw_line.strip(),
            level=level,
            turn_index=turn_index,
            agent_key=agent.key,
            agent_slug=agent.slug,
        )


def _write_structured_output(*, stdout_text: str, last_message_file: Path) -> None:
    payload = extract_structured_output(stdout_text)
    if payload is None:
        return
    last_message_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def _coerce_stream_text(raw_value: str | bytes | None) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="replace")
    return raw_value


def _build_mcp_config(*, workspace_root: Path, run_home: Path, flow: FlowDefinition) -> dict[str, object]:
    mcp_servers: dict[str, object] = {}
    for mcp_name in sorted({mcp for agent in flow.agents.values() for mcp in agent.allowed_mcps}):
        server_file = run_home / "mcps" / mcp_name / "server.toml"
        payload = tomllib.loads(server_file.read_text(encoding="utf-8"))
        expanded_payload = _expand_mcp_payload(
            payload,
            workspace_root=workspace_root,
            run_home=run_home,
            flow=flow,
            context=f"MCP server `{mcp_name}`",
        )
        command = expanded_payload.get("command")
        args = expanded_payload.get("args", [])
        if isinstance(command, list):
            if not command or not all(isinstance(item, str) and item for item in command):
                raise RallyConfigError(
                    f"MCP server `{mcp_name}` must declare `command` as a non-empty string or string list."
                )
            command, extra_args = command[0], command[1:]
            args = [*extra_args, *args]
        if not isinstance(command, str) or not command.strip():
            raise RallyConfigError(
                f"MCP server `{mcp_name}` must declare `command` as a non-empty string or string list."
            )
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            raise RallyConfigError(f"MCP server `{mcp_name}` must declare `args` as a string list.")
        env = expanded_payload.get("env", {})
        if not isinstance(env, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in env.items()):
            raise RallyConfigError(f"MCP server `{mcp_name}` must declare `env` as a string map when present.")
        server_payload: dict[str, object] = {
            "type": "stdio",
            "command": command,
            "args": args,
            "env": env,
        }
        cwd = expanded_payload.get("cwd")
        if isinstance(cwd, str) and cwd.strip():
            server_payload["cwd"] = cwd
        mcp_servers[mcp_name] = server_payload
    return {"mcpServers": mcp_servers}


def _expand_mcp_payload(
    payload: dict[str, object],
    *,
    workspace_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    context: str,
) -> dict[str, object]:
    expanded = expand_rooted_value(
        payload,
        workspace_root=workspace_root,
        flow_root=flow.root_dir,
        run_home=run_home,
        allowed_roots=INTERNAL_PATH_ROOTS,
        context=context,
        example="home:repos/demo_repo",
    )
    if not isinstance(expanded, dict):
        raise RallyConfigError(f"{context} must decode to a TOML table.")
    return expanded


def _sync_claude_skills(*, run_home: Path) -> None:
    claude_skills_root = run_home / ".claude"
    claude_skills_root.mkdir(parents=True, exist_ok=True)
    target = claude_skills_root / "skills"
    source = run_home / "skills"
    if target.exists() or target.is_symlink():
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
    target.symlink_to(source, target_is_directory=True)


def _validate_common_string_arg(*, args: Mapping[str, object], key: str) -> None:
    value = args.get(key)
    if value is None:
        return
    if isinstance(value, str) and value.strip():
        return
    raise RallyConfigError(f"`runtime.adapter_args.{key}` must be a non-empty string when present.")


def _reject_unknown_args(*, args: Mapping[str, object], allowed: set[str]) -> None:
    unknown = sorted(set(args) - allowed)
    if not unknown:
        return
    names = ", ".join(f"`{name}`" for name in unknown)
    raise RallyConfigError(f"Unsupported adapter args for `claude_code`: {names}.")
