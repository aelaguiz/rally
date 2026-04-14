from __future__ import annotations

import os
import selectors
import json
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
    load_adapter_session,
    prepare_adapter_turn_artifacts,
    record_adapter_session,
)
from rally.adapters.codex.event_stream import CodexEventStreamParser
from rally.adapters.codex.launcher import build_codex_launch_env, write_codex_launch_record
from rally.adapters.mcp_readiness import (
    allowed_mcp_names,
    probe_stdio_startability,
    probe_timeout_sec,
    render_probe_failure,
)
from rally.domain.flow import FlowAgent, FlowDefinition
from rally.domain.rooted_path import INTERNAL_PATH_ROOTS, expand_rooted_value
from rally.domain.run import RunRecord
from rally.errors import RallyConfigError
from rally.services.run_events import RunEventRecorder
from rally.services.workspace import WorkspaceContext


class CodexAdapter(RallyAdapter):
    name = "codex"
    display_name = "Codex"

    def validate_args(self, *, args: Mapping[str, object]) -> None:
        _validate_common_string_arg(args=args, key="model")
        _validate_common_string_arg(args=args, key="reasoning_effort")
        project_doc_max_bytes = args.get("project_doc_max_bytes", 0)
        if not isinstance(project_doc_max_bytes, int) or project_doc_max_bytes < 0:
            raise RallyConfigError("`runtime.adapter_args.project_doc_max_bytes` must be a non-negative integer.")
        _reject_unknown_args(args=args, allowed={"model", "reasoning_effort", "project_doc_max_bytes"})

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
        _write_codex_config(workspace_root=repo_root, run_home=run_home, flow=flow)
        _seed_codex_auth(run_home=run_home)

    def prepare_turn_artifacts(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        turn_index: int,
    ) -> TurnArtifactPaths:
        return prepare_adapter_turn_artifacts(run_home=run_home, agent_slug=agent_slug, turn_index=turn_index)

    def load_session(
        self,
        *,
        run_home: Path,
        agent_slug: str,
    ) -> AdapterSessionRecord | None:
        return load_adapter_session(run_home=run_home, agent_slug=agent_slug)

    def record_session(
        self,
        *,
        run_home: Path,
        agent_slug: str,
        session_id: str,
        cwd: Path,
        now=None,
    ) -> AdapterSessionRecord:
        return record_adapter_session(
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
        del repo_root, run_dir, recorder
        required_mcp_names = allowed_mcp_names(flow)
        if not required_mcp_names:
            return None

        config_file = run_home / "config.toml"
        if not config_file.is_file():
            return AdapterReadinessFailure(
                failed_check="run_home_materialization",
                reason=f"Expected Codex config at `{config_file}`.",
            )

        launch_env = {
            **os.environ,
            **build_codex_launch_env(
                workspace_dir=workspace.workspace_root,
                cli_bin=workspace.cli_bin,
                run_home=run_home,
                run_id=run_record.id,
                flow_code=run_record.flow_code,
                agent_slug=agent.slug,
                turn_index=turn_index,
            ),
        }
        listed_servers, list_failure = _load_codex_mcp_list(
            run_home=run_home,
            env=launch_env,
            subprocess_run=subprocess_run,
        )
        if list_failure is not None:
            return list_failure
        listed_by_name = {
            server["name"]: server
            for server in listed_servers
            if isinstance(server, dict) and isinstance(server.get("name"), str)
        }

        for mcp_name in required_mcp_names:
            server_file = run_home / "mcps" / mcp_name / "server.toml"
            if not server_file.is_file():
                return AdapterReadinessFailure(
                    failed_check="run_home_materialization",
                    reason=f"Expected projected MCP file at `{server_file}`.",
                    mcp_name=mcp_name,
                )

            server_config, get_failure = _load_codex_mcp_config(
                run_home=run_home,
                env=launch_env,
                mcp_name=mcp_name,
                subprocess_run=subprocess_run,
            )
            if get_failure is not None:
                return get_failure
            transport = _extract_transport(server_config=server_config)
            if transport is None:
                return AdapterReadinessFailure(
                    failed_check="codex_config_visibility",
                    reason="`codex mcp get --json` did not return a transport block.",
                    mcp_name=mcp_name,
                )

            listed_server = listed_by_name.get(mcp_name)
            if listed_server is None:
                return AdapterReadinessFailure(
                    failed_check="codex_auth_status",
                    reason="`codex mcp list --json` did not include this server.",
                    mcp_name=mcp_name,
                )
            auth_failure = _check_codex_auth_state(
                mcp_name=mcp_name,
                transport=transport,
                listed_server=listed_server,
            )
            if auth_failure is not None:
                return auth_failure

            start_failure = _probe_stdio_startability(
                mcp_name=mcp_name,
                transport=transport,
                run_home=run_home,
                env=launch_env,
                subprocess_run=subprocess_run,
            )
            if start_failure is not None:
                return start_failure
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
            "codex",
            "exec",
            "--json",
            "--dangerously-bypass-approvals-and-sandbox",
            "--skip-git-repo-check",
            "-C",
            str(run_home),
            "--output-schema",
            str(agent.compiled.final_output.schema_file),
            "-o",
            str(artifacts.last_message_file),
            "-c",
            f"project_doc_max_bytes={_project_doc_max_bytes(flow=flow)}",
        ]
        model = flow.adapter.args.get("model")
        if isinstance(model, str) and model.strip():
            command.extend(["-m", model.strip()])
        reasoning_effort = flow.adapter.args.get("reasoning_effort")
        if isinstance(reasoning_effort, str) and reasoning_effort.strip():
            command.extend(["-c", f'model_reasoning_effort="{reasoning_effort.strip()}"'])
        if previous_session is not None:
            command.extend(["resume", previous_session.session_id, "-"])
        else:
            command.append("-")

        env = {
            **os.environ,
            **build_codex_launch_env(
                workspace_dir=workspace.workspace_root,
                cli_bin=workspace.cli_bin,
                run_home=run_home,
                run_id=run_record.id,
                flow_code=run_record.flow_code,
                agent_slug=agent.slug,
                turn_index=turn_index,
            ),
        }
        write_codex_launch_record(
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
                f"Resuming Codex session `{previous_session.session_id}`."
                if previous_session is not None
                else "Launching Codex."
            ),
            turn_index=turn_index,
            agent_key=agent.key,
            agent_slug=agent.slug,
            data={"command": command},
        )
        if subprocess_run is subprocess.run:
            return _stream_codex_invocation(
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


CODEX_ADAPTER = CodexAdapter()


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
    parser = CodexEventStreamParser(
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
        stderr_text = f"codex exec timed out after {timeout_sec} seconds"
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
            session_id=parser.session_id or _extract_session_id(stdout_text),
        )

    stdout_text = completed.stdout or ""
    stderr_text = completed.stderr or ""
    _replay_stdout_lines(stdout_text=stdout_text, artifacts=artifacts, parser=parser, recorder=recorder)
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
        session_id=parser.session_id or _extract_session_id(stdout_text),
    )


def _stream_codex_invocation(
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
    parser = CodexEventStreamParser(
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
    if timed_out:
        timeout_text = f"codex exec timed out after {timeout_sec} seconds"
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
            session_id=parser.session_id or _extract_session_id(stdout_text),
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
        session_id=parser.session_id or _extract_session_id(stdout_text),
    )


def _replay_stdout_lines(
    *,
    stdout_text: str,
    artifacts: TurnArtifactPaths,
    parser: CodexEventStreamParser,
    recorder: RunEventRecorder,
    append_to_file: bool = True,
) -> None:
    if append_to_file and stdout_text:
        artifacts.exec_jsonl_file.write_text(stdout_text, encoding="utf-8")
    for line in stdout_text.splitlines(keepends=True):
        for draft in parser.consume_stdout_line(line):
            recorder.emit_draft(draft)
    for draft in parser.flush():
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
            source="codex",
            kind="warning",
            code="STDERR",
            message=raw_line.strip(),
            level=level,
            turn_index=turn_index,
            agent_key=agent.key,
            agent_slug=agent.slug,
        )


def _append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def _extract_session_id(stdout_text: str) -> str | None:
    for line in stdout_text.splitlines():
        if not line.strip():
            continue
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if decoded.get("type") == "thread.started" and isinstance(decoded.get("thread_id"), str):
            return str(decoded["thread_id"])
        if decoded.get("type") == "thread.resumed" and isinstance(decoded.get("thread_id"), str):
            return str(decoded["thread_id"])
    return None


def _coerce_stream_text(raw_value: str | bytes | None) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="replace")
    return raw_value


def _project_doc_max_bytes(*, flow: FlowDefinition) -> int:
    raw_value = flow.adapter.args.get("project_doc_max_bytes", 0)
    if not isinstance(raw_value, int) or raw_value < 0:
        raise RallyConfigError("`project_doc_max_bytes` must be a non-negative integer.")
    return raw_value


def _write_codex_config(*, workspace_root: Path, run_home: Path, flow: FlowDefinition) -> None:
    project_doc_max_bytes = flow.adapter.args.get("project_doc_max_bytes", 0)
    if not isinstance(project_doc_max_bytes, int) or project_doc_max_bytes < 0:
        raise RallyConfigError("`runtime.adapter_args.project_doc_max_bytes` must be a non-negative integer.")

    lines = [f"project_doc_max_bytes = {project_doc_max_bytes}", ""]
    for mcp_name in allowed_mcp_names(flow):
        server_file = run_home / "mcps" / mcp_name / "server.toml"
        payload = tomllib.loads(server_file.read_text(encoding="utf-8"))
        expanded_payload = _expand_mcp_payload(
            payload,
            workspace_root=workspace_root,
            run_home=run_home,
            flow=flow,
            context=f"MCP server `{mcp_name}`",
        )
        rendered_payload = {**expanded_payload, "required": True}
        lines.append(f'[mcp_servers."{mcp_name}"]')
        for key, value in rendered_payload.items():
            lines.append(f"{key} = {_render_toml_value(value)}")
        lines.append("")
    (run_home / "config.toml").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _seed_codex_auth(*, run_home: Path) -> None:
    source_home = Path.home() / ".codex"
    for file_name in ("auth.json", ".credentials.json"):
        source = source_home / file_name
        target = run_home / file_name
        if target.exists() or target.is_symlink():
            target.unlink()
        if not source.exists():
            continue
        target.symlink_to(source)


def _load_codex_mcp_list(
    *,
    run_home: Path,
    env: dict[str, str],
    subprocess_run: SubprocessRunner,
) -> tuple[list[dict[str, object]], AdapterReadinessFailure | None]:
    stdout_text, failure = _run_codex_probe(
        command=["codex", "mcp", "list", "--json"],
        run_home=run_home,
        env=env,
        subprocess_run=subprocess_run,
        failed_check="codex_auth_status",
    )
    if failure is not None:
        return [], failure
    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        return [], AdapterReadinessFailure(
            failed_check="codex_auth_status",
            reason=f"`codex mcp list --json` returned invalid JSON: {exc}.",
        )
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        return [], AdapterReadinessFailure(
            failed_check="codex_auth_status",
            reason="`codex mcp list --json` did not return a JSON list of servers.",
        )
    return payload, None


def _load_codex_mcp_config(
    *,
    run_home: Path,
    env: dict[str, str],
    mcp_name: str,
    subprocess_run: SubprocessRunner,
) -> tuple[dict[str, object], AdapterReadinessFailure | None]:
    stdout_text, failure = _run_codex_probe(
        command=["codex", "mcp", "get", mcp_name, "--json"],
        run_home=run_home,
        env=env,
        subprocess_run=subprocess_run,
        failed_check="codex_config_visibility",
        mcp_name=mcp_name,
    )
    if failure is not None:
        return {}, failure
    try:
        payload = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        return {}, AdapterReadinessFailure(
            failed_check="codex_config_visibility",
            reason=f"`codex mcp get --json` returned invalid JSON: {exc}.",
            mcp_name=mcp_name,
        )
    if not isinstance(payload, dict):
        return {}, AdapterReadinessFailure(
            failed_check="codex_config_visibility",
            reason="`codex mcp get --json` did not return a JSON object.",
            mcp_name=mcp_name,
        )
    return payload, None


def _run_codex_probe(
    *,
    command: list[str],
    run_home: Path,
    env: dict[str, str],
    subprocess_run: SubprocessRunner,
    failed_check: str,
    mcp_name: str | None = None,
) -> tuple[str, AdapterReadinessFailure | None]:
    try:
        completed = subprocess_run(
            command,
            capture_output=True,
            text=True,
            cwd=run_home,
            env=env,
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return "", AdapterReadinessFailure(
            failed_check=failed_check,
            reason="`codex` is not installed or not on PATH.",
            mcp_name=mcp_name,
        )
    except subprocess.TimeoutExpired:
        return "", AdapterReadinessFailure(
            failed_check=failed_check,
            reason=f"`{' '.join(command)}` timed out before Codex reported readiness data.",
            mcp_name=mcp_name,
        )
    if completed.returncode != 0:
        return "", AdapterReadinessFailure(
            failed_check=failed_check,
            reason=_render_probe_failure(command=command, returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr),
            mcp_name=mcp_name,
        )
    return completed.stdout or "", None


def _extract_transport(*, server_config: dict[str, object]) -> dict[str, object] | None:
    transport = server_config.get("transport")
    if isinstance(transport, dict):
        return transport
    return None


def _check_codex_auth_state(
    *,
    mcp_name: str,
    transport: dict[str, object],
    listed_server: dict[str, object],
) -> AdapterReadinessFailure | None:
    if transport.get("type") != "streamable_http":
        return None
    auth_status = listed_server.get("auth_status")
    if auth_status not in {"bearer_token", "oauth"}:
        return AdapterReadinessFailure(
            failed_check="codex_auth_status",
            reason=f"Codex reported non-usable auth status `{auth_status}` for this streamable HTTP server.",
            mcp_name=mcp_name,
        )
    return None


def _probe_stdio_startability(
    *,
    mcp_name: str,
    transport: dict[str, object],
    run_home: Path,
    env: dict[str, str],
    subprocess_run: SubprocessRunner,
) -> AdapterReadinessFailure | None:
    if transport.get("type") != "stdio":
        return None
    return probe_stdio_startability(
        mcp_name=mcp_name,
        command_name=transport.get("command"),
        raw_args=transport.get("args"),
        raw_env=transport.get("env"),
        raw_cwd=transport.get("cwd"),
        run_home=run_home,
        env=env,
        subprocess_run=subprocess_run,
        config_label="Codex config",
        timeout_sec=probe_timeout_sec(transport.get("startup_timeout_sec")),
    )


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


def _render_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, dict):
        rendered_pairs = [f"{json.dumps(key)} = {_render_toml_value(item)}" for key, item in value.items()]
        return "{ " + ", ".join(rendered_pairs) + " }"
    if isinstance(value, list):
        return "[" + ", ".join(_render_toml_value(item) for item in value) + "]"
    raise RallyConfigError(f"Unsupported TOML value in MCP server definition: `{value!r}`.")


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
    raise RallyConfigError(f"Unsupported adapter args for `codex`: {names}.")
