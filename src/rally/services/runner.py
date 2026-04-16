from __future__ import annotations

from collections.abc import Mapping
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence

from rally.adapters.base import AdapterInvocation, AdapterReadinessFailure
from rally.adapters.registry import get_adapter
from rally.domain.flow import AdapterConfig, FlowAgent, FlowDefinition
from rally.domain.run import ResumeRequest, RunRecord, RunRequest, RunState, RunStatus
from rally.domain.turn_result import (
    BlockerTurnResult,
    DoneTurnResult,
    HandoffTurnResult,
    SleepTurnResult,
    TurnResult,
)
from rally.errors import RallyConfigError, RallyError, RallyStateError, RallyUsageError
from rally.services.flow_build import ensure_flow_assets_built
from rally.services.final_response_loader import LoadedReviewTruth, load_agent_final_response
from rally.services.flow_loader import load_flow_code, load_flow_definition
from rally.services.guarded_git_repos import check_guarded_git_repos, render_guarded_git_repo_blocker
from rally.services.home_materializer import activate_agent_skills, materialize_run_home, prepare_run_home_shell
from rally.services.issue_editor import (
    edit_existing_issue_file_in_editor,
    resolve_interactive_issue_editor,
)
from rally.services.issue_ledger import append_issue_edit_diff, append_issue_event, load_original_issue_text
from rally.services.previous_turn_inputs import render_previous_turn_appendix
from rally.services.run_events import EventConsumer, RunEventRecorder
from rally.services.run_store import (
    archive_run,
    archive_runs_dir,
    create_run,
    find_run_dir,
    find_active_run_for_flow,
    flow_lock,
    load_run_record,
    load_run_state,
    write_run_record,
    write_run_state,
)
from rally.services.workspace import WorkspaceContext, workspace_context_from_root

SubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]
DisplayFactory = Callable[[RunRecord, FlowDefinition], EventConsumer]


@dataclass(frozen=True)
class RunCommandResult:
    run_id: str
    status: RunStatus
    current_agent_key: str | None
    message: str


@dataclass(frozen=True)
class _IssueEditDiff:
    before_text: str
    after_text: str


@dataclass(frozen=True)
class _TurnExecutionOutcome:
    state: RunState
    turn_result: TurnResult | None
    command_result: RunCommandResult | None


@dataclass(frozen=True)
class _AdapterOverrides:
    model_override: str | None = None
    reasoning_effort_override: str | None = None


@dataclass(frozen=True)
class _ResolvedFlowConfig:
    flow: FlowDefinition
    overrides: _AdapterOverrides


def run_flow(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    request: RunRequest,
    subprocess_run: SubprocessRunner = subprocess.run,
    display_factory: DisplayFactory | None = None,
) -> RunCommandResult:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    repo_root = workspace_context.workspace_root
    flow_code = load_flow_code(repo_root=repo_root, flow_name=request.flow_name)

    with flow_lock(repo_root=repo_root, flow_code=flow_code):
        ensure_flow_assets_built(workspace=workspace_context, flow_name=request.flow_name)
        flow = load_flow_definition(repo_root=repo_root, flow_name=request.flow_name)
        resolved_flow = _resolve_effective_flow(
            flow=flow,
            model_override=request.model_override,
            reasoning_effort_override=request.reasoning_effort_override,
        )
        flow = resolved_flow.flow
        issue_seed = _load_issue_seed(
            issue_seed_path=request.issue_seed_path,
        )
        _maybe_archive_replaced_run(
            repo_root=repo_root,
            flow=flow,
            request=request,
        )
        run_record = create_run(
            repo_root=repo_root,
            flow=flow,
            model_override=resolved_flow.overrides.model_override,
            reasoning_effort_override=resolved_flow.overrides.reasoning_effort_override,
        )
        result = _execute_new_run(
            workspace=workspace_context,
            repo_root=repo_root,
            flow=flow,
            run_record=run_record,
            display_factory=display_factory,
            subprocess_run=subprocess_run,
            step=request.step,
            lifecycle_code="RUN",
            lifecycle_message=f"Created run `{run_record.id}` for flow `{flow.name}`.",
            lifecycle_data={
                "flow_name": flow.name,
                "flow_code": flow.code,
                "start_agent_key": flow.start_agent_key,
            },
            issue_text=issue_seed.issue_text,
            run_started_detail_lines=issue_seed.run_started_detail_lines,
        )
        if issue_seed.seed_path is None:
            return result
        return RunCommandResult(
            run_id=result.run_id,
            status=result.status,
            current_agent_key=result.current_agent_key,
            message=f"Seeded `home/issue.md` from `{issue_seed.seed_path}`.\n{result.message}",
        )


def resume_run(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    request: ResumeRequest,
    subprocess_run: SubprocessRunner = subprocess.run,
    display_factory: DisplayFactory | None = None,
) -> RunCommandResult:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    repo_root = workspace_context.workspace_root
    if request.edit_issue and request.restart:
        raise RallyUsageError("`rally resume` accepts either `--edit` or `--restart`, not both.")

    run_dir = find_run_dir(repo_root=repo_root, run_id=request.run_id)
    if run_dir.is_relative_to(archive_runs_dir(repo_root)):
        raise RallyUsageError(
            f"Run `{request.run_id}` is archived and cannot be resumed. "
            f"Use `rally status {request.run_id}` to inspect it."
        )
    run_record = load_run_record(run_dir=run_dir)

    with flow_lock(repo_root=repo_root, flow_code=run_record.flow_code):
        ensure_flow_assets_built(workspace=workspace_context, flow_name=run_record.flow_name)
        flow = load_flow_definition(repo_root=repo_root, flow_name=run_record.flow_name)
        resolved_flow = _resolve_effective_flow(
            flow=flow,
            model_override=request.model_override,
            reasoning_effort_override=request.reasoning_effort_override,
            saved_model_override=run_record.model_override,
            saved_reasoning_effort_override=run_record.reasoning_effort_override,
        )
        flow = resolved_flow.flow
        updated_run_record = _run_record_with_overrides(run_record=run_record, overrides=resolved_flow.overrides)
        if updated_run_record != run_record:
            write_run_record(run_dir=run_dir, record=updated_run_record)
            run_record = updated_run_record
        if request.restart:
            return _restart_run(
                workspace=workspace_context,
                repo_root=repo_root,
                flow=flow,
                run_record=run_record,
                subprocess_run=subprocess_run,
                display_factory=display_factory,
                step=request.step,
            )
        recorder = _build_recorder(
            run_dir=run_dir,
            run_record=run_record,
            flow=flow,
            display_factory=display_factory,
        )
        try:
            state = load_run_state(run_dir=run_dir)
            issue_edit_diff: _IssueEditDiff | None = None
            if request.edit_issue:
                issue_edit_diff = _edit_issue_before_resume(
                    run_dir=run_dir,
                    run_record=run_record,
                    state=state,
                    recorder=recorder,
                )
            recorder.emit(
                source="rally",
                kind="lifecycle",
                code="RESUME",
                message=f"Resuming run `{run_record.id}`.",
            )
            return _execute_until_stop(
                workspace=workspace_context,
                repo_root=repo_root,
                flow=flow,
                run_record=run_record,
                recorder=recorder,
                issue_edit_diff=issue_edit_diff,
                subprocess_run=subprocess_run,
                step=request.step,
            )
        finally:
            recorder.close()


def _execute_new_run(
    *,
    workspace: WorkspaceContext,
    repo_root: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    display_factory: DisplayFactory | None,
    subprocess_run: SubprocessRunner,
    step: bool,
    lifecycle_code: str,
    lifecycle_message: str,
    lifecycle_data: dict[str, object] | None,
    issue_text: str | None = None,
    run_start_source: str = "rally run",
    run_started_detail_lines: Sequence[str] = (),
) -> RunCommandResult:
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_record.id)
    recorder = _build_recorder(
        run_dir=run_dir,
        run_record=run_record,
        flow=flow,
        display_factory=display_factory,
    )
    try:
        recorder.emit(
            source="rally",
            kind="lifecycle",
            code=lifecycle_code,
            message=lifecycle_message,
            data=lifecycle_data,
        )
        prepare_run_home_shell(
            workspace=workspace,
            run_record=run_record,
            event_recorder=recorder,
        )
        if issue_text is not None:
            (run_dir / "home" / "issue.md").write_text(issue_text, encoding="utf-8")
        return _execute_until_stop(
            workspace=workspace,
            repo_root=repo_root,
            flow=flow,
            run_record=run_record,
            recorder=recorder,
            subprocess_run=subprocess_run,
            step=step,
            run_start_source=run_start_source,
            run_started_detail_lines=run_started_detail_lines,
        )
    finally:
        recorder.close()


def _restart_run(
    *,
    workspace: WorkspaceContext,
    repo_root: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    subprocess_run: SubprocessRunner,
    display_factory: DisplayFactory | None,
    step: bool,
) -> RunCommandResult:
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_record.id)
    state = load_run_state(run_dir=run_dir)
    original_issue = load_original_issue_text(repo_root=repo_root, run_id=run_record.id)
    if not _confirm_replace_active_run(
        active_run=run_record,
        active_state=state,
        command_text=f"rally resume {run_record.id} --restart",
        prompt=(
            f"Archive active run `{run_record.id}` with status `{state.status.value}` "
            "and restart it from the original issue? [y/N]: "
        ),
    ):
        raise RallyUsageError(f"Cancelled restarting run `{run_record.id}`.")

    _record_archived_run(
        repo_root=repo_root,
        active_run=run_record,
        active_state=state,
        run_dir=run_dir,
        event_message=f"Archiving run `{run_record.id}` before restarting it from the original issue.",
        issue_source="rally resume --restart",
        issue_reason=f"Restarting from the original issue with `rally resume {run_record.id} --restart`.",
    )
    archive_run(repo_root=repo_root, run_id=run_record.id)

    new_run = create_run(
        repo_root=repo_root,
        flow=flow,
        model_override=run_record.model_override,
        reasoning_effort_override=run_record.reasoning_effort_override,
    )
    restarted_result = _execute_new_run(
        workspace=workspace,
        repo_root=repo_root,
        flow=flow,
        run_record=new_run,
        display_factory=display_factory,
        subprocess_run=subprocess_run,
        step=step,
        lifecycle_code="RESTART",
        lifecycle_message=f"Restarted run `{run_record.id}` as `{new_run.id}` for flow `{flow.name}`.",
        lifecycle_data={
            "flow_name": flow.name,
            "flow_code": flow.code,
            "start_agent_key": flow.start_agent_key,
            "restarted_from_run_id": run_record.id,
        },
        issue_text=original_issue,
        run_start_source="rally resume --restart",
        run_started_detail_lines=(f"Restarted From: `{run_record.id}`",),
    )
    return RunCommandResult(
        run_id=restarted_result.run_id,
        status=restarted_result.status,
        current_agent_key=restarted_result.current_agent_key,
        message=f"Restarted run `{run_record.id}` as `{new_run.id}`.\n{restarted_result.message}",
    )


def _resolve_effective_flow(
    *,
    flow: FlowDefinition,
    model_override: str | None = None,
    reasoning_effort_override: str | None = None,
    saved_model_override: str | None = None,
    saved_reasoning_effort_override: str | None = None,
) -> _ResolvedFlowConfig:
    overrides = _AdapterOverrides(
        model_override=_select_override(command_value=model_override, saved_value=saved_model_override),
        reasoning_effort_override=_select_override(
            command_value=reasoning_effort_override,
            saved_value=saved_reasoning_effort_override,
        ),
    )
    adapter_args = dict(flow.adapter.args)
    if overrides.model_override is not None:
        adapter_args["model"] = overrides.model_override
    if overrides.reasoning_effort_override is not None:
        adapter_args["reasoning_effort"] = overrides.reasoning_effort_override
    get_adapter(flow.adapter.name).validate_args(args=adapter_args)
    return _ResolvedFlowConfig(
        flow=replace(
            flow,
            adapter=AdapterConfig(name=flow.adapter.name, args=adapter_args),
        ),
        overrides=overrides,
    )


def _select_override(*, command_value: str | None, saved_value: str | None) -> str | None:
    if command_value is None:
        return saved_value
    return command_value.strip()


def _run_record_with_overrides(*, run_record: RunRecord, overrides: _AdapterOverrides) -> RunRecord:
    return replace(
        run_record,
        model_override=overrides.model_override,
        reasoning_effort_override=overrides.reasoning_effort_override,
    )


def _maybe_archive_replaced_run(
    *,
    repo_root: Path,
    flow: FlowDefinition,
    request: RunRequest,
) -> None:
    if not request.start_new:
        return

    active_run = find_active_run_for_flow(repo_root=repo_root, flow_code=flow.code)
    if active_run is None:
        return

    active_run_dir = find_run_dir(repo_root=repo_root, run_id=active_run.id)
    active_state = load_run_state(run_dir=active_run_dir)
    if not _confirm_replace_active_run(
        active_run=active_run,
        active_state=active_state,
        command_text=f"rally run {flow.name} --new",
        prompt=(
            f"Archive active run `{active_run.id}` with status `{active_state.status.value}` "
            f"and start a new `{flow.name}` run? [y/N]: "
        ),
    ):
        raise RallyUsageError(f"Cancelled starting a new `{flow.name}` run.")

    _record_archived_run(
        repo_root=repo_root,
        active_run=active_run,
        active_state=active_state,
        run_dir=active_run_dir,
        event_message=f"Archiving run `{active_run.id}` before starting a new `{flow.name}` run.",
        issue_source="rally run --new",
        issue_reason=f"Starting a fresh `{flow.name}` run with `rally run {flow.name} --new`.",
    )
    archive_run(repo_root=repo_root, run_id=active_run.id)


def _confirm_replace_active_run(
    *,
    active_run: RunRecord,
    active_state: RunState,
    command_text: str,
    prompt: str,
) -> bool:
    if not (_stream_is_tty(sys.stdin) and _stream_is_tty(sys.stdout)):
        raise RallyUsageError(
            f"`{command_text}` needs an interactive TTY to confirm archiving "
            f"active run `{active_run.id}`."
        )

    sys.stdout.write(prompt)
    sys.stdout.flush()
    response = sys.stdin.readline()
    return response.strip().lower() in {"y", "yes"}


def _stream_is_tty(stream) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except OSError:
        return False


def _record_archived_run(
    *,
    repo_root: Path,
    active_run: RunRecord,
    active_state: RunState,
    run_dir: Path,
    event_message: str,
    issue_source: str,
    issue_reason: str,
) -> None:
    recorder = RunEventRecorder(
        run_dir=run_dir,
        run_id=active_run.id,
        flow_code=active_run.flow_code,
    )
    try:
        recorder.emit(
            source="rally",
            kind="lifecycle",
            code="ARCHIVE",
            message=event_message,
            data={"status": active_state.status.value},
        )
    finally:
        recorder.close()

    if (run_dir / "home" / "issue.md").is_file():
        append_issue_event(
            repo_root=repo_root,
            run_id=active_run.id,
            title="Rally Archived",
            source=issue_source,
            detail_lines=(
                f"Status: `{active_state.status.value}`",
                f"Reason: {issue_reason}",
            ),
        )


@dataclass(frozen=True)
class _IssueSeed:
    seed_path: Path | None
    issue_text: str | None
    run_started_detail_lines: Sequence[str] = ()


def _load_issue_seed(*, issue_seed_path: Path | None) -> _IssueSeed:
    if issue_seed_path is None:
        return _IssueSeed(seed_path=None, issue_text=None)

    seed_path = issue_seed_path.expanduser().resolve()
    if not seed_path.exists():
        raise RallyUsageError(f"Issue seed file does not exist: `{seed_path}`.")
    if not seed_path.is_file():
        raise RallyUsageError(f"Issue seed path is not a file: `{seed_path}`.")
    try:
        issue_text = seed_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RallyUsageError(f"Issue seed file must be valid UTF-8 text: `{seed_path}`.") from exc
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise RallyUsageError(f"Could not read issue seed file `{seed_path}`: {detail}.") from exc
    if not issue_text.strip():
        raise RallyUsageError(
            f"Issue seed file is blank: `{seed_path}`. Write non-empty issue text there or omit `--from-file`."
        )
    return _IssueSeed(
        seed_path=seed_path,
        issue_text=issue_text,
        run_started_detail_lines=(f"Issue Seed: `{seed_path}`",),
    )


def _build_recorder(
    *,
    run_dir: Path,
    run_record: RunRecord,
    flow: FlowDefinition,
    display_factory: DisplayFactory | None,
) -> RunEventRecorder:
    consumer = display_factory(run_record, flow) if display_factory is not None else None
    return RunEventRecorder(
        run_dir=run_dir,
        run_id=run_record.id,
        flow_code=run_record.flow_code,
        consumer=consumer,
    )


def _edit_issue_before_resume(
    *,
    run_dir: Path,
    run_record: RunRecord,
    state: RunState,
    recorder: RunEventRecorder,
) -> _IssueEditDiff | None:
    if state.status == RunStatus.DONE:
        raise RallyUsageError(
            f"Run `{run_record.id}` is already done. "
            f"Use `rally resume {run_record.id} --restart` to start fresh from the original issue."
        )

    editor_command = resolve_interactive_issue_editor()
    if editor_command is None:
        raise RallyUsageError(
            f"`rally resume {run_record.id} --edit` needs an interactive TTY and an editor."
        )

    issue_path = run_dir / "home" / "issue.md"
    before_text = issue_path.read_text(encoding="utf-8") if issue_path.is_file() else ""
    _emit_resume_issue_editor_opened(
        run_id=run_record.id,
        issue_path=issue_path,
        editor_command=editor_command,
        recorder=recorder,
    )
    edit_result = edit_existing_issue_file_in_editor(
        issue_path=issue_path,
        editor_command=editor_command,
    )
    if edit_result.status != "saved":
        _emit_resume_issue_editor_cancelled(
            run_id=run_record.id,
            issue_path=issue_path,
            reason=edit_result.reason,
            recorder=recorder,
        )
        if not _issue_has_text(issue_path):
            _emit_resume_issue_waiting(
                run_id=run_record.id,
                issue_path=issue_path,
                recorder=recorder,
            )
            raise RallyUsageError(
                f"Run `{run_record.id}` is waiting for a non-empty issue in `{issue_path}`. "
                f"Write the issue there, then run `rally resume {run_record.id}`."
            )
        raise RallyUsageError(_render_resume_issue_editor_cancel_message(issue_path, edit_result.reason))

    _emit_resume_issue_editor_saved(
        run_id=run_record.id,
        issue_path=issue_path,
        recorder=recorder,
    )
    after_text = issue_path.read_text(encoding="utf-8")
    if state.status == RunStatus.BLOCKED:
        write_run_state(
            run_dir=run_dir,
            state=_clear_blocked_state(state=state),
        )
    if before_text == after_text:
        return None
    return _IssueEditDiff(before_text=before_text, after_text=after_text)


def _issue_has_text(issue_path: Path) -> bool:
    return issue_path.is_file() and bool(issue_path.read_text(encoding="utf-8").strip())


def _clear_blocked_state(*, state: RunState) -> RunState:
    return RunState(
        status=RunStatus.PENDING,
        current_agent_key=state.current_agent_key,
        current_agent_slug=state.current_agent_slug,
        turn_index=state.turn_index,
        updated_at=_render_time(),
        last_turn_kind=state.last_turn_kind,
    )


def _emit_resume_issue_waiting(
    *,
    run_id: str,
    issue_path: Path,
    recorder: RunEventRecorder,
) -> None:
    recorder.emit(
        source="rally",
        kind="warning",
        code="WAITING",
        message=f"Run `{run_id}` is waiting for `home/issue.md` at `{issue_path}`.",
        level="warning",
    )


def _emit_resume_issue_editor_opened(
    *,
    run_id: str,
    issue_path: Path,
    editor_command: Sequence[str],
    recorder: RunEventRecorder,
) -> None:
    recorder.emit(
        source="rally",
        kind="lifecycle",
        code="EDITOR",
        message=(
            f"Opening editor for `home/issue.md` at `{issue_path}` with "
            f"`{shlex.join(editor_command)}`."
        ),
        data={"run_id": run_id},
    )


def _emit_resume_issue_editor_saved(
    *,
    run_id: str,
    issue_path: Path,
    recorder: RunEventRecorder,
) -> None:
    recorder.emit(
        source="rally",
        kind="lifecycle",
        code="EDITOR",
        message=f"Saved issue from editor to `{issue_path}`.",
        data={"run_id": run_id},
    )


def _emit_resume_issue_editor_cancelled(
    *,
    run_id: str,
    issue_path: Path,
    reason: str | None,
    recorder: RunEventRecorder,
) -> None:
    recorder.emit(
        source="rally",
        kind="warning",
        code="EDITOR",
        message=_render_resume_issue_editor_cancel_message(issue_path, reason),
        level="warning",
        data={"run_id": run_id},
    )


def _render_resume_issue_editor_cancel_message(issue_path: Path, reason: str | None) -> str:
    if reason == "blank_issue":
        return f"Editor closed without a non-empty issue for `{issue_path}`."
    if reason == "editor_exit":
        return f"Editor exited before Rally got a saved issue for `{issue_path}`."
    if reason == "launch_failed":
        return f"Editor failed to open for `{issue_path}`."
    return f"Editor did not produce a saved issue for `{issue_path}`."


def _execute_until_stop(
    *,
    workspace: WorkspaceContext,
    repo_root: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    recorder: RunEventRecorder,
    issue_edit_diff: _IssueEditDiff | None = None,
    subprocess_run: SubprocessRunner,
    step: bool = False,
    run_start_source: str = "rally run",
    run_started_detail_lines: Sequence[str] = (),
) -> RunCommandResult:
    run_dir = find_run_dir(repo_root=repo_root, run_id=run_record.id)
    initial_state = load_run_state(run_dir=run_dir)
    _assert_resumable(state=initial_state, run_id=run_record.id)
    try:
        run_home = materialize_run_home(
            workspace=workspace,
            flow=flow,
            run_record=run_record,
            event_recorder=recorder,
        )
    except RallyError:
        if issue_edit_diff is not None:
            append_issue_edit_diff(
                repo_root=repo_root,
                run_id=run_record.id,
                before_text=issue_edit_diff.before_text,
                after_text=issue_edit_diff.after_text,
            )
        raise
    _append_run_started_event_if_needed(
        repo_root=repo_root,
        run_dir=run_dir,
        run_record=run_record,
        flow=flow,
        state=initial_state,
        source=run_start_source,
        extra_detail_lines=run_started_detail_lines,
    )
    if issue_edit_diff is not None:
        append_issue_edit_diff(
            repo_root=repo_root,
            run_id=run_record.id,
            before_text=issue_edit_diff.before_text,
            after_text=issue_edit_diff.after_text,
        )

    turns_started = 0
    while True:
        state = load_run_state(run_dir=run_dir)
        _assert_resumable(state=state, run_id=run_record.id)
        if turns_started >= flow.max_command_turns:
            return _block_for_command_turn_cap(
                repo_root=repo_root,
                run_dir=run_dir,
                flow=flow,
                run_record=run_record,
                state=state,
                recorder=recorder,
            )

        outcome = _execute_single_turn(
            repo_root=repo_root,
            run_dir=run_dir,
            run_home=run_home,
            workspace=workspace,
            flow=flow,
            run_record=run_record,
            recorder=recorder,
            subprocess_run=subprocess_run,
            pause_on_handoff=step,
        )
        turns_started += 1
        if outcome.command_result is not None:
            return outcome.command_result


def _execute_single_turn(
    *,
    repo_root: Path,
    run_dir: Path,
    run_home: Path,
    workspace: WorkspaceContext,
    flow: FlowDefinition,
    run_record: RunRecord,
    recorder: RunEventRecorder,
    subprocess_run: SubprocessRunner,
    pause_on_handoff: bool = False,
) -> _TurnExecutionOutcome:
    state = load_run_state(run_dir=run_dir)
    _assert_resumable(state=state, run_id=run_record.id)
    agent = _resolve_current_agent(flow=flow, state=state)
    adapter = get_adapter(flow.adapter.name)
    turn_index = state.turn_index + 1
    activate_agent_skills(run_home=run_home, agent=agent)

    previous_session = adapter.load_session(run_home=run_home, agent_slug=agent.slug)
    if state.status == RunStatus.SLEEPING and previous_session is None:
        raise RallyStateError(
            f"Run `{run_record.id}` is sleeping on `{agent.slug}`, but no {adapter.display_name} session was saved."
        )

    readiness_failure = adapter.check_turn_readiness(
        repo_root=repo_root,
        workspace=workspace,
        run_dir=run_dir,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        turn_index=turn_index,
        recorder=recorder,
        subprocess_run=subprocess_run,
    )
    if readiness_failure is not None:
        return _block_for_adapter_readiness(
            repo_root=repo_root,
            run_dir=run_dir,
            run_record=run_record,
            state=state,
            agent=agent,
            adapter_name=adapter.display_name,
            readiness_failure=readiness_failure,
            recorder=recorder,
        )

    artifacts = adapter.prepare_turn_artifacts(run_home=run_home, agent_slug=agent.slug, turn_index=turn_index)

    running_state = RunState(
        status=RunStatus.RUNNING,
        current_agent_key=agent.key,
        current_agent_slug=agent.slug,
        turn_index=state.turn_index,
        updated_at=_render_time(),
        last_turn_kind=state.last_turn_kind,
    )
    write_run_state(run_dir=run_dir, state=running_state)
    recorder.emit(
        source="rally",
        kind="lifecycle",
        code="TURN",
        message=f"Starting turn {turn_index} on `{agent.key}`.",
        turn_index=turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
    )

    prompt = _build_agent_prompt(
        workspace=workspace,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        recorder=recorder,
        turn_index=turn_index,
        previous_turn_inputs_file=artifacts.previous_turn_inputs_file,
    )

    invocation = adapter.invoke(
        repo_root=repo_root,
        workspace=workspace,
        run_dir=run_dir,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        prompt=prompt,
        previous_session=previous_session,
        artifacts=artifacts,
        recorder=recorder,
        turn_index=turn_index,
        subprocess_run=subprocess_run,
    )

    artifacts.exec_jsonl_file.write_text(invocation.stdout_text, encoding="utf-8")
    artifacts.stderr_file.write_text(invocation.stderr_text, encoding="utf-8")

    final_session_id = invocation.session_id or (previous_session.session_id if previous_session else None)
    if final_session_id:
        adapter.record_session(
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
        recorder.emit(
            source="rally",
            kind="warning",
            code="BLOCKED",
            message=f"{adapter.display_name} run failed: {blocked_state.blocker_reason}",
            level="error",
            turn_index=turn_index,
            agent_key=agent.key,
            agent_slug=agent.slug,
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
            turn_index=turn_index,
        )
        return _TurnExecutionOutcome(
            state=blocked_state,
            turn_result=None,
            command_result=RunCommandResult(
                run_id=run_record.id,
                status=blocked_state.status,
                current_agent_key=blocked_state.current_agent_key,
                message=_render_blocked_message(
                    run_id=run_record.id,
                    reason=f"blocked on `{agent.key}`: {blocked_state.blocker_reason}",
                ),
            ),
        )

    loaded_final_response = load_agent_final_response(
        compiled_agent=agent.compiled,
        last_message_file=artifacts.last_message_file,
    )
    recorder.emit_final_json(
        payload=loaded_final_response.payload,
        payload_file=artifacts.last_message_file,
        turn_index=turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
    )
    turn_result = loaded_final_response.turn_result
    if isinstance(turn_result, SleepTurnResult):
        blocked_state = RunState(
            status=RunStatus.BLOCKED,
            current_agent_key=agent.key,
            current_agent_slug=agent.slug,
            turn_index=turn_index,
            updated_at=_render_time(),
            last_turn_kind=turn_result.kind.value,
            blocker_reason="Sleep turn results are not supported in chained execution yet.",
        )
        _emit_turn_result_event(
            recorder=recorder,
            run_record=run_record,
            agent=agent,
            turn_index=turn_index,
            state=blocked_state,
            turn_result=turn_result,
        )
        _append_issue_records_for_turn_result(
            repo_root=repo_root,
            run_id=run_record.id,
            agent=agent,
            turn_result=turn_result,
            payload=loaded_final_response.payload,
            review_truth=loaded_final_response.review_truth,
            turn_index=turn_index,
        )
        write_run_state(run_dir=run_dir, state=blocked_state)
        recorder.emit(
            source="rally",
            kind="warning",
            code="BLOCKED",
            message=f"Run `{run_record.id}` is blocked: {blocked_state.blocker_reason}",
            level="error",
            turn_index=turn_index,
            agent_key=agent.key,
            agent_slug=agent.slug,
        )
        return _TurnExecutionOutcome(
            state=blocked_state,
            turn_result=turn_result,
            command_result=RunCommandResult(
                run_id=run_record.id,
                status=blocked_state.status,
                current_agent_key=blocked_state.current_agent_key,
                message=_render_blocked_message(
                    run_id=run_record.id,
                    reason=blocked_state.blocker_reason or "run is blocked",
                ),
            ),
        )

    guarded_repo_block = _block_for_guarded_git_repos(
        repo_root=repo_root,
        run_dir=run_dir,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        agent=agent,
        turn_index=turn_index,
        turn_result=turn_result,
        recorder=recorder,
    )
    if guarded_repo_block is not None:
        return _TurnExecutionOutcome(
            state=guarded_repo_block.state,
            turn_result=turn_result,
            command_result=guarded_repo_block.command_result,
        )

    next_state = _state_from_turn_result(
        flow=flow,
        state=state,
        agent=agent,
        turn_index=turn_index,
        turn_result=turn_result,
        pause_on_handoff=pause_on_handoff,
    )
    write_run_state(run_dir=run_dir, state=next_state)
    _emit_turn_result_event(
        recorder=recorder,
        run_record=run_record,
        agent=agent,
        turn_index=turn_index,
        state=next_state,
        turn_result=turn_result,
    )
    _append_issue_records_for_turn_result(
        repo_root=repo_root,
        run_id=run_record.id,
        agent=agent,
        turn_result=turn_result,
        payload=loaded_final_response.payload,
        review_truth=loaded_final_response.review_truth,
        turn_index=turn_index,
    )

    result = None
    if pause_on_handoff and isinstance(turn_result, HandoffTurnResult):
        _emit_step_pause_event(
            recorder=recorder,
            run_record=run_record,
            state=next_state,
            turn_index=turn_index,
        )
        _append_issue_pause_record(
            repo_root=repo_root,
            run_id=run_record.id,
            state=next_state,
            turn_index=turn_index,
        )
        result = RunCommandResult(
            run_id=run_record.id,
            status=next_state.status,
            current_agent_key=next_state.current_agent_key,
            message=_render_step_pause_message(run_record=run_record, state=next_state),
        )
    elif not isinstance(turn_result, HandoffTurnResult):
        result = RunCommandResult(
            run_id=run_record.id,
            status=next_state.status,
            current_agent_key=next_state.current_agent_key,
            message=_render_status_message(run_record=run_record, state=next_state, turn_result=turn_result),
        )
    return _TurnExecutionOutcome(
        state=next_state,
        turn_result=turn_result,
        command_result=result,
    )


def _block_for_adapter_readiness(
    *,
    repo_root: Path,
    run_dir: Path,
    run_record: RunRecord,
    state: RunState,
    agent: FlowAgent,
    adapter_name: str,
    readiness_failure: AdapterReadinessFailure,
    recorder: RunEventRecorder,
) -> _TurnExecutionOutcome:
    blocker_reason = _format_adapter_readiness_failure(
        adapter_name=adapter_name,
        readiness_failure=readiness_failure,
    )
    blocked_state = RunState(
        status=RunStatus.BLOCKED,
        current_agent_key=agent.key,
        current_agent_slug=agent.slug,
        turn_index=state.turn_index,
        updated_at=_render_time(),
        last_turn_kind=state.last_turn_kind,
        blocker_reason=blocker_reason,
    )
    write_run_state(run_dir=run_dir, state=blocked_state)
    event_data: dict[str, object] = {"failed_check": readiness_failure.failed_check}
    if readiness_failure.mcp_name is not None:
        event_data["mcp_name"] = readiness_failure.mcp_name
    recorder.emit(
        source="rally",
        kind="warning",
        code="BLOCKED",
        message=f"Run `{run_record.id}` is blocked: {blocker_reason}",
        level="error",
        turn_index=state.turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
        data=event_data,
    )
    detail_lines = [
        f"Agent: `{agent.key}`",
        f"Check: `{readiness_failure.failed_check}`",
        f"Reason: {blocker_reason}",
    ]
    if readiness_failure.mcp_name is not None:
        detail_lines.insert(1, f"MCP: `{readiness_failure.mcp_name}`")
    append_issue_event(
        repo_root=repo_root,
        run_id=run_record.id,
        title="Rally Blocked",
        source="rally runtime",
        detail_lines=tuple(detail_lines),
    )
    return _TurnExecutionOutcome(
        state=blocked_state,
        turn_result=None,
        command_result=RunCommandResult(
            run_id=run_record.id,
            status=blocked_state.status,
            current_agent_key=blocked_state.current_agent_key,
            message=_render_blocked_message(
                run_id=run_record.id,
                reason=f"blocked on `{agent.key}`: {blocked_state.blocker_reason}",
            ),
        ),
    )


def _block_for_command_turn_cap(
    *,
    repo_root: Path,
    run_dir: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    state: RunState,
    recorder: RunEventRecorder,
) -> RunCommandResult:
    agent = _resolve_current_agent(flow=flow, state=state)
    blocker_reason = (
        f"Reached runtime.max_command_turns={flow.max_command_turns} before the next turn could start."
    )
    blocked_state = RunState(
        status=RunStatus.BLOCKED,
        current_agent_key=state.current_agent_key,
        current_agent_slug=state.current_agent_slug,
        turn_index=state.turn_index,
        updated_at=_render_time(),
        last_turn_kind=state.last_turn_kind,
        blocker_reason=blocker_reason,
    )
    write_run_state(run_dir=run_dir, state=blocked_state)
    recorder.emit(
        source="rally",
        kind="warning",
        code="BLOCKED",
        message=f"Run `{run_record.id}` is blocked: {blocker_reason}",
        level="error",
        turn_index=state.turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
    )
    append_issue_event(
        repo_root=repo_root,
        run_id=run_record.id,
        title="Rally Blocked",
        source="rally runtime",
        detail_lines=(
            f"Agent: `{agent.key}`",
            f"Reason: {blocker_reason}",
        ),
    )
    return RunCommandResult(
        run_id=run_record.id,
        status=blocked_state.status,
        current_agent_key=blocked_state.current_agent_key,
        message=_render_blocked_message(run_id=run_record.id, reason=blocker_reason),
    )


def _build_agent_prompt(
    *,
    workspace: WorkspaceContext,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    recorder: RunEventRecorder,
    turn_index: int,
    previous_turn_inputs_file: Path,
) -> str:
    # Rally keeps compiler-owned prompt text as the base, then appends one
    # deterministic previous-turn appendix when the emitted `io` contract asks
    # for it. There is no second prompt layer and no prose summarizer here.
    compiled_markdown = (run_home / "agents" / agent.slug / "AGENTS.md").read_text(encoding="utf-8").rstrip()
    previous_turn_appendix = render_previous_turn_appendix(
        workspace_root=workspace.workspace_root,
        run_home=run_home,
        flow=flow,
        agent=agent,
        turn_index=turn_index,
    ).rstrip()
    previous_turn_inputs_file.parent.mkdir(parents=True, exist_ok=True)
    previous_turn_inputs_file.write_text(
        previous_turn_appendix + ("\n" if previous_turn_appendix else ""),
        encoding="utf-8",
    )
    if not previous_turn_appendix:
        return compiled_markdown + "\n"
    return compiled_markdown + "\n\n" + previous_turn_appendix + "\n"


@dataclass(frozen=True)
class _GuardedRepoBlockOutcome:
    state: RunState
    command_result: RunCommandResult


def _block_for_guarded_git_repos(
    *,
    repo_root: Path,
    run_dir: Path,
    run_home: Path,
    flow: FlowDefinition,
    run_record: RunRecord,
    agent: FlowAgent,
    turn_index: int,
    turn_result: TurnResult,
    recorder: RunEventRecorder,
) -> _GuardedRepoBlockOutcome | None:
    if not isinstance(turn_result, (HandoffTurnResult, DoneTurnResult)):
        return None
    if not flow.guarded_git_repos:
        return None

    violations = check_guarded_git_repos(
        run_home=run_home,
        guarded_git_repos=flow.guarded_git_repos,
    )
    if not violations:
        return None

    blocker_reason = render_guarded_git_repo_blocker(violations=violations)
    blocked_state = RunState(
        status=RunStatus.BLOCKED,
        current_agent_key=agent.key,
        current_agent_slug=agent.slug,
        turn_index=turn_index,
        updated_at=_render_time(),
        last_turn_kind=turn_result.kind.value,
        blocker_reason=blocker_reason,
    )
    write_run_state(run_dir=run_dir, state=blocked_state)
    recorder.emit(
        source="rally",
        kind="warning",
        code="BLOCKED",
        message=f"Run `{run_record.id}` is blocked: {blocker_reason}",
        level="error",
        turn_index=turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
        data={"result_kind": turn_result.kind.value},
    )
    detail_lines = [
        f"Agent: `{agent.key}`",
        f"Attempted Result: `{turn_result.kind.value}`",
        f"Reason: {blocker_reason}",
    ]
    for violation in violations:
        detail_lines.append(
            f"Guarded Repo `{violation.relative_path.as_posix()}`: {violation.reason}"
        )
    append_issue_event(
        repo_root=repo_root,
        run_id=run_record.id,
        title="Rally Blocked",
        source="rally runtime",
        detail_lines=detail_lines,
        turn_index=turn_index,
    )
    return _GuardedRepoBlockOutcome(
        state=blocked_state,
        command_result=RunCommandResult(
            run_id=run_record.id,
            status=blocked_state.status,
            current_agent_key=blocked_state.current_agent_key,
            message=_render_blocked_message(run_id=run_record.id, reason=blocker_reason),
        ),
    )


def _state_from_turn_result(
    *,
    flow: FlowDefinition,
    state: RunState,
    agent: FlowAgent,
    turn_index: int,
    turn_result: TurnResult,
    pause_on_handoff: bool = False,
) -> RunState:
    updated_at = _render_time()
    if isinstance(turn_result, HandoffTurnResult):
        next_agent = _resolve_next_agent(flow=flow, next_owner=turn_result.next_owner)
        return RunState(
            status=RunStatus.PAUSED if pause_on_handoff else RunStatus.RUNNING,
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
    raise RallyConfigError(f"Unsupported turn result type: `{type(turn_result).__name__}`.")


def _emit_turn_result_event(
    *,
    recorder: RunEventRecorder,
    run_record: RunRecord,
    agent: FlowAgent,
    turn_index: int,
    state: RunState,
    turn_result: TurnResult,
) -> None:
    event_data: dict[str, object] = {"result_kind": turn_result.kind.value}
    if isinstance(turn_result, HandoffTurnResult):
        message = f"Handed off to `{state.current_agent_key}`."
        code = "HANDOFF"
        event_data["next_owner"] = turn_result.next_owner
    elif isinstance(turn_result, DoneTurnResult):
        message = f"Run `{run_record.id}` is done: {turn_result.summary}"
        code = "DONE"
    elif isinstance(turn_result, BlockerTurnResult):
        message = f"Run `{run_record.id}` is blocked: {turn_result.reason}"
        code = "BLOCKED"
    else:
        message = (
            f"Run `{run_record.id}` asked to sleep for "
            f"`{turn_result.sleep_duration_seconds}` second(s): {turn_result.reason}"
        )
        code = "SLEEP"

    recorder.emit(
        source="rally",
        kind="status",
        code=code,
        message=message,
        level="error" if isinstance(turn_result, BlockerTurnResult) else "info",
        turn_index=turn_index,
        agent_key=agent.key,
        agent_slug=agent.slug,
        data=event_data,
    )


def _append_issue_records_for_turn_result(
    *,
    repo_root: Path,
    run_id: str,
    agent: FlowAgent,
    turn_result: TurnResult,
    payload: Mapping[str, object],
    review_truth: LoadedReviewTruth | None,
    turn_index: int,
) -> None:
    detail_lines = _turn_result_issue_detail_lines(
        agent=agent,
        turn_result=turn_result,
        review_truth=review_truth,
    )

    append_issue_event(
        repo_root=repo_root,
        run_id=run_id,
        title="Rally Turn Result",
        source="rally runtime",
        detail_lines=detail_lines,
        body=_render_turn_result_payload_markdown(payload=payload),
        turn_index=turn_index,
    )


def _turn_result_issue_detail_lines(
    *,
    agent: FlowAgent,
    turn_result: TurnResult,
    review_truth: LoadedReviewTruth | None,
) -> list[str]:
    detail_lines = [f"Agent: `{agent.key}`", f"Result: `{turn_result.kind.value}`"]
    if review_truth is not None:
        detail_lines.append(f"Review Verdict: `{review_truth.verdict}`")
        if review_truth.reviewed_artifact is not None:
            detail_lines.append(f"Reviewed Artifact: `{review_truth.reviewed_artifact}`")
        if review_truth.readback is not None:
            detail_lines.append(f"Findings First: {review_truth.readback}")
        elif review_truth.analysis is not None:
            detail_lines.append(f"Review Summary: {review_truth.analysis}")
        if review_truth.current_artifact is not None:
            detail_lines.append(f"Current Artifact: `{review_truth.current_artifact}`")
        if review_truth.next_owner is not None:
            detail_lines.append(f"Next Owner: `{review_truth.next_owner}`")
        if review_truth.blocked_gate is not None:
            detail_lines.append(f"Blocked Gate: {review_truth.blocked_gate}")
        if review_truth.failing_gates:
            detail_lines.append(
                "Failing Gates: " + ", ".join(f"`{gate}`" for gate in review_truth.failing_gates)
            )
        return detail_lines

    if isinstance(turn_result, HandoffTurnResult):
        detail_lines.append(f"Next Owner: `{turn_result.next_owner}`")
    if isinstance(turn_result, DoneTurnResult):
        detail_lines.append(f"Summary: {turn_result.summary}")
    if isinstance(turn_result, BlockerTurnResult):
        detail_lines.append(f"Reason: {turn_result.reason}")
    if isinstance(turn_result, SleepTurnResult):
        detail_lines.append(f"Reason: {turn_result.reason}")
        detail_lines.append(f"Sleep Seconds: `{turn_result.sleep_duration_seconds}`")
    return detail_lines


def _render_turn_result_payload_markdown(*, payload: Mapping[str, object]) -> str:
    rendered_payload = json.dumps(payload, indent=2)
    return f"```json\n{rendered_payload}\n```"


def _emit_step_pause_event(
    *,
    recorder: RunEventRecorder,
    run_record: RunRecord,
    state: RunState,
    turn_index: int,
) -> None:
    recorder.emit(
        source="rally",
        kind="status",
        code="PAUSED",
        message=_render_step_pause_message(run_record=run_record, state=state),
        level="info",
        turn_index=turn_index,
        agent_key=state.current_agent_key,
        agent_slug=state.current_agent_slug,
        data={"step": True},
    )


def _append_issue_pause_record(
    *,
    repo_root: Path,
    run_id: str,
    state: RunState,
    turn_index: int,
) -> None:
    append_issue_event(
        repo_root=repo_root,
        run_id=run_id,
        title="Rally Paused",
        source="rally runtime",
        detail_lines=(
            f"Agent: `{state.current_agent_key}`",
            "Reason: `--step` stopped after one turn.",
            f"Resume: `rally resume {run_id}`",
            f"Step Again: `rally resume {run_id} --step`",
        ),
        turn_index=turn_index,
    )


def _append_run_started_event_if_needed(
    *,
    repo_root: Path,
    run_dir: Path,
    run_record: RunRecord,
    flow: FlowDefinition,
    state: RunState,
    source: str,
    extra_detail_lines: Sequence[str] = (),
) -> None:
    if state.turn_index != 0:
        return
    marker = run_dir / ".run_started_logged"
    if marker.is_file():
        return
    append_issue_event(
        repo_root=repo_root,
        run_id=run_record.id,
        title="Rally Run Started",
        source=source,
        detail_lines=(
            f"Flow: `{flow.name}`",
            f"Flow Code: `{flow.code}`",
            f"Start Agent: `{flow.start_agent_key}`",
            *extra_detail_lines,
        ),
    )
    marker.write_text("logged\n", encoding="utf-8")


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
        raise RallyUsageError(
            f"Run `{run_id}` is already done. "
            f"Use `rally resume {run_id} --restart` to start fresh from the original issue."
        )
    if state.status == RunStatus.BLOCKED:
        raise RallyUsageError(_render_blocked_message(run_id=run_id, reason=state.blocker_reason or "run is blocked"))
    if state.status != RunStatus.SLEEPING:
        return
    if state.sleep_until is None:
        raise RallyStateError(f"Run `{run_id}` is sleeping without `sleep_until`.")
    wake_time = _parse_time(state.sleep_until)
    if wake_time > datetime.now(UTC):
        raise RallyUsageError(
            f"Run `{run_id}` is sleeping until `{state.sleep_until}`: {state.sleep_reason}.\n"
            f"Next: `rally resume {run_id}` after that time."
        )


def _resolve_next_agent(*, flow: FlowDefinition, next_owner: str) -> FlowAgent:
    try:
        return flow.agent_by_slug(next_owner)
    except KeyError:
        pass
    try:
        return flow.agent(next_owner)
    except KeyError:
        pass
    for agent in flow.agents.values():
        if agent.compiled.name == next_owner:
            return agent
    raise RallyStateError(f"Turn result handed off to unknown owner `{next_owner}`.")


def _render_status_message(*, run_record: RunRecord, state: RunState, turn_result: TurnResult) -> str:
    if isinstance(turn_result, HandoffTurnResult):
        if state.status == RunStatus.PAUSED:
            return _render_step_pause_message(run_record=run_record, state=state)
        return f"Run `{run_record.id}` paused after a handoff to `{state.current_agent_key}`."
    if isinstance(turn_result, DoneTurnResult):
        return _with_next_action(
            f"Run `{run_record.id}` is done: {turn_result.summary}",
            f"`rally resume {run_record.id} --restart`",
        )
    if isinstance(turn_result, BlockerTurnResult):
        return _render_blocked_message(run_id=run_record.id, reason=turn_result.reason)
    if isinstance(turn_result, SleepTurnResult):
        return _render_blocked_message(run_id=run_record.id, reason=state.blocker_reason or "run is blocked")
    return f"Run `{run_record.id}` updated."


def _render_step_pause_message(*, run_record: RunRecord, state: RunState) -> str:
    return _with_next_action(
        f"Run `{run_record.id}` paused after one step on `{state.current_agent_key}`.",
        f"`rally resume {run_record.id}` or `rally resume {run_record.id} --step`",
    )


def _render_blocked_message(*, run_id: str, reason: str) -> str:
    return _with_next_action(
        f"Run `{run_id}` is blocked: {reason}",
        f"`rally resume {run_id} --edit` or `rally resume {run_id} --restart`",
    )


def _with_next_action(summary: str, next_action: str) -> str:
    return f"{summary}\nNext: {next_action}"


def _format_exec_failure(invocation: AdapterInvocation) -> str:
    stderr = invocation.stderr_text.strip()
    if stderr:
        return stderr
    stdout = invocation.stdout_text.strip()
    if stdout:
        return stdout.splitlines()[-1]
    return f"adapter run exited with code {invocation.returncode}"


def _format_adapter_readiness_failure(
    *,
    adapter_name: str,
    readiness_failure: AdapterReadinessFailure,
) -> str:
    if readiness_failure.mcp_name is not None:
        return (
            f"{adapter_name} MCP `{readiness_failure.mcp_name}` failed "
            f"`{readiness_failure.failed_check}`: {readiness_failure.reason}"
        )
    return f"{adapter_name} failed `{readiness_failure.failed_check}`: {readiness_failure.reason}"


def _render_time() -> str:
    return datetime.now(UTC).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(raw_value: str) -> datetime:
    if raw_value.endswith("Z"):
        raw_value = f"{raw_value[:-1]}+00:00"
    return datetime.fromisoformat(raw_value).astimezone(UTC)


def _coerce_workspace(
    *,
    workspace: WorkspaceContext | None,
    repo_root: Path | None,
) -> WorkspaceContext:
    if workspace is not None and repo_root is not None:
        raise RallyUsageError("Pass either `workspace` or `repo_root`, not both.")
    if workspace is not None:
        return workspace
    if repo_root is None:
        raise RallyUsageError("Rally runtime needs a workspace root.")
    return workspace_context_from_root(repo_root)
