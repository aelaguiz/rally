from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from rally.adapters.codex.launcher import build_codex_launch_env
from rally.adapters.codex.result_contract import load_turn_result
from rally.adapters.codex.session_store import (
    CodexSessionRecord,
    TurnArtifactPaths,
    load_session,
    prepare_turn_artifacts,
    record_session,
)
from rally.domain.flow import FlowAgent, FlowDefinition
from rally.domain.run import ResumeRequest, RunRecord, RunRequest, RunState, RunStatus
from rally.domain.turn_result import (
    BlockerTurnResult,
    DoneTurnResult,
    HandoffTurnResult,
    SleepTurnResult,
    TurnResult,
)
from rally.errors import RallyConfigError, RallyStateError, RallyUsageError
from rally.services.event_log import append_event
from rally.services.flow_loader import load_flow_definition
from rally.services.home_materializer import materialize_run_home
from rally.services.issue_ledger import append_issue_event
from rally.services.run_store import (
    create_run,
    find_run_dir,
    flow_lock,
    load_run_record,
    load_run_state,
    write_run_state,
)

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class RunCommandResult:
    run_id: str
    status: RunStatus
    current_agent_key: str | None
    message: str


def run_flow(
    *,
    repo_root: Path,
    request: RunRequest,
    subprocess_run: SubprocessRunner = subprocess.run,
) -> RunCommandResult:
    flow = load_flow_definition(repo_root=repo_root, flow_name=request.flow_name)
    brief_markdown = request.brief_file.read_text(encoding="utf-8")

    with flow_lock(repo_root=repo_root, flow_code=flow.code):
        run_record = create_run(
            repo_root=repo_root,
            flow=flow,
            brief_file=request.brief_file,
        )
        run_dir = find_run_dir(repo_root=repo_root, run_id=run_record.id)
        materialize_run_home(
            repo_root=repo_root,
            flow=flow,
            run_record=run_record,
            brief_markdown=brief_markdown,
        )
        append_event(
            run_dir=run_dir,
            event_type="run.created",
            payload={
                "flow_name": flow.name,
                "flow_code": flow.code,
                "start_agent_key": flow.start_agent_key,
            },
        )
        append_issue_event(
            repo_root=repo_root,
            run_id=run_record.id,
            title="Rally Run Started",
            source="rally run",
            detail_lines=(
                f"Flow: `{flow.name}`",
                f"Flow Code: `{flow.code}`",
                f"Start Agent: `{flow.start_agent_key}`",
            ),
        )
        return _execute_current_turn(
            repo_root=repo_root,
            flow=flow,
            run_record=run_record,
            subprocess_run=subprocess_run,
        )


def resume_run(
    *,
    repo_root: Path,
    request: ResumeRequest,
    subprocess_run: SubprocessRunner = subprocess.run,
) -> RunCommandResult:
    run_dir = find_run_dir(repo_root=repo_root, run_id=request.run_id)
    run_record = load_run_record(run_dir=run_dir)
    flow = load_flow_definition(repo_root=repo_root, flow_name=run_record.flow_name)

    with flow_lock(repo_root=repo_root, flow_code=run_record.flow_code):
        return _execute_current_turn(
            repo_root=repo_root,
            flow=flow,
            run_record=run_record,
            subprocess_run=subprocess_run,
        )


def _execute_current_turn(
    *,
    repo_root: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    subprocess_run: SubprocessRunner,
) -> RunCommandResult:
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_record.id)
    run_home = run_dir / "home"
    if not run_home.is_dir():
        raise RallyStateError(f"Run home does not exist for `{run_record.id}`.")

    state = load_run_state(run_dir=run_dir)
    agent = _resolve_current_agent(flow=flow, state=state)
    _assert_resumable(state=state, run_id=run_record.id)

    turn_index = state.turn_index + 1
    artifacts = prepare_turn_artifacts(run_home=run_home, agent_slug=agent.slug, turn_index=turn_index)

    running_state = RunState(
        status=RunStatus.RUNNING,
        current_agent_key=agent.key,
        current_agent_slug=agent.slug,
        turn_index=state.turn_index,
        updated_at=_render_time(),
        last_turn_kind=state.last_turn_kind,
    )
    write_run_state(run_dir=run_dir, state=running_state)

    append_event(
        run_dir=run_dir,
        event_type="turn.started",
        payload={"agent_key": agent.key, "agent_slug": agent.slug, "turn_index": turn_index},
    )

    prompt = _build_agent_prompt(
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
    )
    previous_session = load_session(run_home=run_home, agent_slug=agent.slug)
    if state.status == RunStatus.SLEEPING and previous_session is None:
        raise RallyStateError(
            f"Run `{run_record.id}` is sleeping on `{agent.slug}`, but no Codex session was saved."
        )

    invocation = _invoke_codex(
        repo_root=repo_root,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        prompt=prompt,
        previous_session=previous_session,
        artifacts=artifacts,
        subprocess_run=subprocess_run,
    )

    artifacts.exec_jsonl_file.write_text(invocation.stdout_text, encoding="utf-8")
    artifacts.stderr_file.write_text(invocation.stderr_text, encoding="utf-8")

    final_session_id = invocation.session_id or (previous_session.session_id if previous_session else None)
    if final_session_id:
        record_session(
            run_home=run_home,
            agent_slug=agent.slug,
            session_id=final_session_id,
            cwd=run_home,
        )

    if invocation.returncode != 0:
        blocked_state = RunState(
            status=RunStatus.BLOCKED,
            current_agent_key=agent.key,
            current_agent_slug=agent.slug,
            turn_index=turn_index,
            updated_at=_render_time(),
            last_turn_kind="blocker",
            blocker_reason=_format_exec_failure(invocation),
        )
        write_run_state(run_dir=run_dir, state=blocked_state)
        append_event(
            run_dir=run_dir,
            event_type="turn.failed",
            payload={
                "agent_key": agent.key,
                "turn_index": turn_index,
                "reason": blocked_state.blocker_reason,
            },
        )
        append_issue_event(
            repo_root=repo_root,
            run_id=run_record.id,
            title="Rally Blocked",
            source="rally runtime",
            detail_lines=(
                f"Agent: `{agent.key}`",
                f"Reason: {blocked_state.blocker_reason}",
            ),
        )
        return RunCommandResult(
            run_id=run_record.id,
            status=blocked_state.status,
            current_agent_key=blocked_state.current_agent_key,
            message=f"Run `{run_record.id}` blocked on `{agent.key}`: {blocked_state.blocker_reason}",
        )

    turn_result = load_turn_result(last_message_file=artifacts.last_message_file)
    next_state = _state_from_turn_result(
        flow=flow,
        state=state,
        agent=agent,
        turn_index=turn_index,
        turn_result=turn_result,
    )
    write_run_state(run_dir=run_dir, state=next_state)

    append_event(
        run_dir=run_dir,
        event_type="turn.completed",
        payload={
            "agent_key": agent.key,
            "agent_slug": agent.slug,
            "turn_index": turn_index,
            "result_kind": next_state.last_turn_kind,
            "next_agent_key": next_state.current_agent_key,
        },
    )
    _append_issue_records_for_turn_result(
        repo_root=repo_root,
        run_id=run_record.id,
        agent=agent,
        turn_result=turn_result,
    )

    return RunCommandResult(
        run_id=run_record.id,
        status=next_state.status,
        current_agent_key=next_state.current_agent_key,
        message=_render_status_message(run_record=run_record, state=next_state, turn_result=turn_result),
    )


def _build_agent_prompt(
    *,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
) -> str:
    compiled_markdown = (run_home / "agents" / agent.slug / "AGENTS.md").read_text(encoding="utf-8").rstrip()
    prompt_inputs = _load_prompt_inputs(
        flow=flow,
        run_record=run_record,
        run_home=run_home,
        agent=agent,
    )
    parts = [compiled_markdown]
    if prompt_inputs:
        parts.append(_render_prompt_inputs(prompt_inputs))
    return "\n\n".join(parts).rstrip() + "\n"


def _load_prompt_inputs(
    *,
    flow: FlowDefinition,
    run_record: RunRecord,
    run_home: Path,
    agent: FlowAgent,
) -> dict[str, object]:
    command_path = flow.adapter.prompt_input_command
    if command_path is None:
        return {}

    completed = subprocess.run(
        [sys.executable, str(command_path)],
        cwd=flow.root_dir,
        env={
            **os.environ,
            "RALLY_AGENT_KEY": agent.key,
            "RALLY_AGENT_SLUG": agent.slug,
            "RALLY_FLOW_CODE": run_record.flow_code,
            "RALLY_ISSUE_PATH": str((run_home / "issue.md").resolve()),
            "RALLY_RUN_HOME": str(run_home.resolve()),
            "RALLY_RUN_ID": run_record.id,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "prompt input command failed"
        raise RallyStateError(f"Prompt input command failed for `{agent.key}`: {stderr}")

    raw_output = completed.stdout.strip()
    if not raw_output:
        return {}
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RallyStateError("Prompt input command did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise RallyStateError("Prompt input command must return one JSON object.")
    return payload


def _render_prompt_inputs(payload: dict[str, object]) -> str:
    sections = ["## Runtime Prompt Inputs"]
    for key, value in payload.items():
        sections.append(f"### {key}")
        if isinstance(value, str):
            sections.append(value.rstrip())
            continue
        sections.append("```json")
        sections.append(json.dumps(value, indent=2, sort_keys=True))
        sections.append("```")
    return "\n\n".join(section for section in sections if section)


def _invoke_codex(
    *,
    repo_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    prompt: str,
    previous_session: CodexSessionRecord | None,
    artifacts: TurnArtifactPaths,
    subprocess_run: SubprocessRunner,
) -> "_CodexInvocation":
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
            repo_root=repo_root,
            run_home=run_home,
            run_id=run_record.id,
            flow_code=run_record.flow_code,
            agent_slug=agent.slug,
        ),
    }
    try:
        completed = subprocess_run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=run_home,
            env=env,
            timeout=agent.timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_text = _coerce_stream_text(exc.stdout)
        stderr_tail = _coerce_stream_text(exc.stderr).strip()
        stderr_text = f"codex exec timed out after {agent.timeout_sec} seconds"
        if stderr_tail:
            stderr_text = f"{stderr_text}\n{stderr_tail}"
        return _CodexInvocation(
            returncode=124,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            session_id=_extract_session_id(stdout_text),
        )
    return _CodexInvocation(
        returncode=completed.returncode,
        stdout_text=completed.stdout,
        stderr_text=completed.stderr,
        session_id=_extract_session_id(completed.stdout),
    )


def _state_from_turn_result(
    *,
    flow: FlowDefinition,
    state: RunState,
    agent: FlowAgent,
    turn_index: int,
    turn_result: TurnResult,
) -> RunState:
    updated_at = _render_time()
    if isinstance(turn_result, HandoffTurnResult):
        next_agent = _resolve_next_agent(flow=flow, next_owner=turn_result.next_owner)
        return RunState(
            status=RunStatus.RUNNING,
            current_agent_key=next_agent.key,
            current_agent_slug=next_agent.slug,
            turn_index=turn_index,
            updated_at=updated_at,
            last_turn_kind=turn_result.kind.value,
        )
    if isinstance(turn_result, DoneTurnResult):
        return RunState(
            status=RunStatus.DONE,
            current_agent_key=None,
            current_agent_slug=None,
            turn_index=turn_index,
            updated_at=updated_at,
            last_turn_kind=turn_result.kind.value,
            done_summary=turn_result.summary,
        )
    if isinstance(turn_result, BlockerTurnResult):
        return RunState(
            status=RunStatus.BLOCKED,
            current_agent_key=agent.key,
            current_agent_slug=agent.slug,
            turn_index=turn_index,
            updated_at=updated_at,
            last_turn_kind=turn_result.kind.value,
            blocker_reason=turn_result.reason,
        )
    if isinstance(turn_result, SleepTurnResult):
        sleep_until = datetime.now(UTC) + timedelta(seconds=turn_result.sleep_duration_seconds)
        return RunState(
            status=RunStatus.SLEEPING,
            current_agent_key=agent.key,
            current_agent_slug=agent.slug,
            turn_index=turn_index,
            updated_at=updated_at,
            last_turn_kind=turn_result.kind.value,
            sleep_until=sleep_until.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            sleep_reason=turn_result.reason,
        )
    raise RallyConfigError(f"Unsupported turn result type: `{type(turn_result).__name__}`.")


def _append_issue_records_for_turn_result(
    *,
    repo_root: Path,
    run_id: str,
    agent: FlowAgent,
    turn_result: TurnResult,
) -> None:
    detail_lines = [f"Agent: `{agent.key}`", f"Result: `{turn_result.kind.value}`"]
    if isinstance(turn_result, HandoffTurnResult):
        detail_lines.append(f"Next Owner: `{turn_result.next_owner}`")
    if isinstance(turn_result, DoneTurnResult):
        detail_lines.append(f"Summary: {turn_result.summary}")
    if isinstance(turn_result, BlockerTurnResult):
        detail_lines.append(f"Reason: {turn_result.reason}")
    if isinstance(turn_result, SleepTurnResult):
        detail_lines.append(f"Reason: {turn_result.reason}")
        detail_lines.append(f"Sleep Seconds: `{turn_result.sleep_duration_seconds}`")

    append_issue_event(
        repo_root=repo_root,
        run_id=run_id,
        title="Rally Turn Result",
        source="rally runtime",
        detail_lines=detail_lines,
    )
    if isinstance(turn_result, BlockerTurnResult):
        append_issue_event(
            repo_root=repo_root,
            run_id=run_id,
            title="Rally Blocked",
            source="rally runtime",
            detail_lines=(f"Agent: `{agent.key}`", f"Reason: {turn_result.reason}"),
        )
    if isinstance(turn_result, SleepTurnResult):
        append_issue_event(
            repo_root=repo_root,
            run_id=run_id,
            title="Rally Sleeping",
            source="rally runtime",
            detail_lines=(
                f"Agent: `{agent.key}`",
                f"Reason: {turn_result.reason}",
                f"Sleep Seconds: `{turn_result.sleep_duration_seconds}`",
            ),
        )
    if isinstance(turn_result, DoneTurnResult):
        append_issue_event(
            repo_root=repo_root,
            run_id=run_id,
            title="Rally Done",
            source="rally runtime",
            detail_lines=(f"Agent: `{agent.key}`", f"Summary: {turn_result.summary}"),
        )


def _resolve_current_agent(*, flow: FlowDefinition, state: RunState) -> FlowAgent:
    if state.current_agent_key is None:
        raise RallyStateError(f"Run is not pointing at an active agent for flow `{flow.name}`.")
    try:
        return flow.agent(state.current_agent_key)
    except KeyError as exc:
        raise RallyStateError(
            f"Run state points at unknown agent `{state.current_agent_key}`."
        ) from exc


def _assert_resumable(*, state: RunState, run_id: str) -> None:
    if state.status == RunStatus.DONE:
        raise RallyUsageError(f"Run `{run_id}` is already done.")
    if state.status == RunStatus.BLOCKED:
        raise RallyUsageError(f"Run `{run_id}` is blocked: {state.blocker_reason}.")
    if state.status != RunStatus.SLEEPING:
        return
    if state.sleep_until is None:
        raise RallyStateError(f"Run `{run_id}` is sleeping without `sleep_until`.")
    wake_time = _parse_time(state.sleep_until)
    if wake_time > datetime.now(UTC):
        raise RallyUsageError(
            f"Run `{run_id}` is sleeping until `{state.sleep_until}`: {state.sleep_reason}."
        )


def _resolve_next_agent(*, flow: FlowDefinition, next_owner: str) -> FlowAgent:
    try:
        return flow.agent_by_slug(next_owner)
    except KeyError:
        try:
            return flow.agent(next_owner)
        except KeyError as exc:
            raise RallyStateError(
                f"Turn result handed off to unknown owner `{next_owner}`."
            ) from exc


def _render_status_message(*, run_record: RunRecord, state: RunState, turn_result: TurnResult) -> str:
    if isinstance(turn_result, HandoffTurnResult):
        return (
            f"Run `{run_record.id}` finished one turn and handed off to "
            f"`{state.current_agent_key}`."
        )
    if isinstance(turn_result, DoneTurnResult):
        return f"Run `{run_record.id}` is done: {turn_result.summary}"
    if isinstance(turn_result, BlockerTurnResult):
        return f"Run `{run_record.id}` is blocked: {turn_result.reason}"
    if isinstance(turn_result, SleepTurnResult):
        return (
            f"Run `{run_record.id}` is sleeping on `{state.current_agent_key}` "
            f"until `{state.sleep_until}`."
        )
    return f"Run `{run_record.id}` updated."


def _project_doc_max_bytes(*, flow: FlowDefinition) -> int:
    raw_value = flow.adapter.args.get("project_doc_max_bytes", 0)
    if not isinstance(raw_value, int) or raw_value < 0:
        raise RallyConfigError("`project_doc_max_bytes` must be a non-negative integer.")
    return raw_value


def _extract_session_id(stdout_text: str) -> str | None:
    for line in stdout_text.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started" and isinstance(payload.get("thread_id"), str):
            return str(payload["thread_id"])
    return None


def _format_exec_failure(invocation: "_CodexInvocation") -> str:
    stderr = invocation.stderr_text.strip()
    if stderr:
        return stderr
    stdout = invocation.stdout_text.strip()
    if stdout:
        return stdout.splitlines()[-1]
    return f"codex exec exited with code {invocation.returncode}"


def _render_time() -> str:
    return datetime.now(UTC).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(raw_value: str) -> datetime:
    if raw_value.endswith("Z"):
        raw_value = f"{raw_value[:-1]}+00:00"
    return datetime.fromisoformat(raw_value).astimezone(UTC)


def _coerce_stream_text(raw_value: str | bytes | None) -> str:
    if raw_value is None:
        return ""
    if isinstance(raw_value, bytes):
        return raw_value.decode("utf-8", errors="replace")
    return raw_value


@dataclass(frozen=True)
class _CodexInvocation:
    returncode: int
    stdout_text: str
    stderr_text: str
    session_id: str | None
