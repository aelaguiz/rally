from __future__ import annotations

import shlex
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Sequence

from rally.adapters.registry import get_adapter
from rally.domain.flow import FlowAgent, FlowDefinition
from rally.domain.rooted_path import RootedPath, resolve_rooted_path
from rally.domain.run import RunRecord
from rally.errors import RallyConfigError, RallyStateError, RallyUsageError
from rally.services.flow_env import build_flow_subprocess_env
from rally.services.issue_editor import edit_issue_file_in_editor, resolve_interactive_issue_editor
from rally.services.issue_ledger import snapshot_issue_log
from rally.services.run_events import RunEventRecorder
from rally.services.run_store import find_run_dir
from rally.services.builtin_assets import RallyBuiltinAssets, resolve_rally_builtin_assets
from rally.services.skill_bundles import (
    MANDATORY_SKILL_NAMES,
    resolve_external_skill_bundle_source,
    resolve_skill_bundle_source,
    split_external_skill_name,
)
from rally.services.workspace import (
    ExternalSkillRoot,
    WorkspaceContext,
    workspace_context_from_root,
)

_HOME_READY_MARKER = ".rally_home_ready"


def prepare_run_home_shell(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    run_record: RunRecord,
    event_recorder: RunEventRecorder | None = None,
) -> Path:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    run_dir = find_run_dir(repo_root=workspace_context.workspace_root, run_id=run_record.id)
    run_home = run_dir / "home"

    _ensure_run_layout(run_dir=run_dir, run_home=run_home)
    if event_recorder is not None:
        event_recorder.emit(
            source="rally",
            kind="lifecycle",
            code="HOME",
            message="Prepared run home shell.",
        )
    return run_home


def materialize_run_home(
    *,
    workspace: WorkspaceContext | None = None,
    repo_root: Path | None = None,
    flow: FlowDefinition,
    run_record: RunRecord,
    event_recorder: RunEventRecorder | None = None,
) -> Path:
    workspace_context = _coerce_workspace(workspace=workspace, repo_root=repo_root)
    run_dir = find_run_dir(repo_root=workspace_context.workspace_root, run_id=run_record.id)
    run_home = run_dir / "home"
    issue_path = run_home / "issue.md"

    _ensure_run_layout(run_dir=run_dir, run_home=run_home)
    _require_issue_ready(
        issue_path=issue_path,
        run_id=run_record.id,
        event_recorder=event_recorder,
    )
    builtins = resolve_rally_builtin_assets(workspace=workspace_context)
    _sync_compiled_agents(run_home=run_home, flow=flow)
    # Refresh each agent's stable skill view here. The runner activates one
    # of these views into the live `home/skills/` tree right before launch.
    _refresh_agent_skill_views(
        repo_root=workspace_context.workspace_root,
        run_home=run_home,
        flow=flow,
        builtins=builtins,
        external_skill_roots=workspace_context.external_skill_roots,
    )
    _copy_allowed_mcps(repo_root=workspace_context.workspace_root, run_home=run_home, flow=flow)
    get_adapter(flow.adapter.name).prepare_home(
        repo_root=workspace_context.workspace_root,
        workspace=workspace_context,
        run_home=run_home,
        flow=flow,
        run_record=run_record,
        event_recorder=event_recorder,
    )
    if _home_ready_marker(run_home).is_file():
        return run_home

    if event_recorder is not None:
        event_recorder.emit(
            source="rally",
            kind="lifecycle",
            code="HOME",
            message="Preparing run home.",
        )
    _require_host_inputs_ready(
        workspace=workspace_context,
        flow=flow,
        run_home=run_home,
        event_recorder=event_recorder,
    )
    _run_setup_script(
        workspace=workspace_context,
        flow=flow,
        run_record=run_record,
        run_home=run_home,
        issue_path=issue_path,
        event_recorder=event_recorder,
    )
    snapshot_issue_log(repo_root=workspace_context.workspace_root, run_id=run_record.id)
    _home_ready_marker(run_home).write_text("prepared\n", encoding="utf-8")
    if event_recorder is not None:
        event_recorder.emit(
            source="rally",
            kind="lifecycle",
            code="READY",
            message="Run home is ready.",
        )
    return run_home


def _ensure_run_layout(*, run_dir: Path, run_home: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "issue_history").mkdir(parents=True, exist_ok=True)
    run_home.mkdir(parents=True, exist_ok=True)
    for relative_dir in (
        "agents",
        "skills",
        "mcps",
        "sessions",
        "artifacts",
        "repos",
    ):
        (run_home / relative_dir).mkdir(parents=True, exist_ok=True)


def _require_issue_ready(
    *,
    issue_path: Path,
    run_id: str,
    event_recorder: RunEventRecorder | None,
) -> None:
    # Rally has one sanctioned shared startup input: `home/issue.md`.
    # Startup must fail if that file is missing or blank. Do not add a
    # `--brief-file` flag, stdin brief path, repo-root brief file, or shared
    # sidecar such as `operator_brief.md`. If a run needs extra files later,
    # the flow may create them on purpose, but Rally itself starts from
    # `home/issue.md` only.
    if _issue_has_text(issue_path):
        return

    editor_command = resolve_interactive_issue_editor()
    if editor_command is not None:
        _emit_issue_editor_opened(
            run_id=run_id,
            issue_path=issue_path,
            editor_command=editor_command,
            event_recorder=event_recorder,
        )
        edit_result = edit_issue_file_in_editor(
            issue_path=issue_path,
            editor_command=editor_command,
        )
        if edit_result.status == "saved":
            _emit_issue_editor_saved(
                run_id=run_id,
                issue_path=issue_path,
                event_recorder=event_recorder,
            )
            return
        _emit_issue_editor_cancelled(
            run_id=run_id,
            issue_path=issue_path,
            reason=edit_result.reason,
            event_recorder=event_recorder,
        )

    if not issue_path.is_file():
        _emit_issue_waiting(
            run_id=run_id,
            issue_path=issue_path,
            event_recorder=event_recorder,
        )
        raise RallyUsageError(
            f"Run `{run_id}` is waiting for `{issue_path}`. Create that file, "
            f"write the issue there, then run `rally resume {run_id}`."
        )
    _emit_issue_waiting(
        run_id=run_id,
        issue_path=issue_path,
        event_recorder=event_recorder,
    )
    raise RallyUsageError(
        f"Run `{run_id}` is waiting for a non-empty issue in `{issue_path}`. "
        f"Write the issue there, then run `rally resume {run_id}`."
    )


def _issue_has_text(issue_path: Path) -> bool:
    return issue_path.is_file() and bool(issue_path.read_text(encoding="utf-8").strip())


def _emit_issue_waiting(
    *,
    run_id: str,
    issue_path: Path,
    event_recorder: RunEventRecorder | None,
) -> None:
    if event_recorder is None:
        return
    event_recorder.emit(
        source="rally",
        kind="warning",
        code="WAITING",
        message=(
            f"Run `{run_id}` is waiting for `home/issue.md` at `{issue_path}`."
        ),
        level="warning",
    )


def _emit_issue_editor_opened(
    *,
    run_id: str,
    issue_path: Path,
    editor_command: Sequence[str],
    event_recorder: RunEventRecorder | None,
) -> None:
    if event_recorder is None:
        return
    event_recorder.emit(
        source="rally",
        kind="lifecycle",
        code="EDITOR",
        message=(
            f"Opening editor for `home/issue.md` at `{issue_path}` with "
            f"`{shlex.join(editor_command)}`."
        ),
        data={"run_id": run_id},
    )


def _emit_issue_editor_saved(
    *,
    run_id: str,
    issue_path: Path,
    event_recorder: RunEventRecorder | None,
) -> None:
    if event_recorder is None:
        return
    event_recorder.emit(
        source="rally",
        kind="lifecycle",
        code="EDITOR",
        message=f"Saved issue from editor to `{issue_path}`.",
        data={"run_id": run_id},
    )


def _emit_issue_editor_cancelled(
    *,
    run_id: str,
    issue_path: Path,
    reason: str | None,
    event_recorder: RunEventRecorder | None,
) -> None:
    if event_recorder is None:
        return
    event_recorder.emit(
        source="rally",
        kind="warning",
        code="EDITOR",
        message=_render_issue_editor_cancel_message(issue_path=issue_path, reason=reason),
        level="warning",
        data={"run_id": run_id},
    )


def _render_issue_editor_cancel_message(*, issue_path: Path, reason: str | None) -> str:
    if reason == "blank_issue":
        return f"Editor closed without a non-empty issue for `{issue_path}`."
    if reason == "editor_exit":
        return f"Editor exited before Rally got a saved issue for `{issue_path}`."
    if reason == "launch_failed":
        return f"Editor failed to open for `{issue_path}`."
    return f"Editor did not produce a saved issue for `{issue_path}`."


def _home_ready_marker(run_home: Path) -> Path:
    return run_home / _HOME_READY_MARKER


def _sync_compiled_agents(*, run_home: Path, flow: FlowDefinition) -> None:
    # Copy each compiled agent package directory whole so compiler-owned peers
    # such as `SOUL.md` survive into the run home without Rally re-emitting
    # them or treating them as a second prompt surface.
    _sync_named_directories(
        target_root=run_home / "agents",
        sources_by_name={
            agent.slug: agent.compiled.markdown_path.parent for agent in flow.agents.values()
        },
    )


def _sync_named_directories(*, target_root: Path, sources_by_name: dict[str, Path]) -> None:
    expected_names = set(sources_by_name)
    for existing in sorted(target_root.iterdir()):
        if existing.name in expected_names:
            continue
        _remove_path(existing)
    for name, source in sorted(sources_by_name.items()):
        target = target_root / name
        _remove_path(target)
        shutil.copytree(source, target)


def _remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def activate_agent_skills(*, run_home: Path, agent: FlowAgent) -> None:
    skill_view_root = _agent_skill_view_root(run_home=run_home, agent_slug=agent.slug)
    skill_sources = _load_agent_skill_view_sources(skill_view_root=skill_view_root, agent=agent)
    _sync_named_directories(target_root=run_home / "skills", sources_by_name=skill_sources)


def _refresh_agent_skill_views(
    *,
    repo_root: Path,
    run_home: Path,
    flow: FlowDefinition,
    builtins: RallyBuiltinAssets,
    external_skill_roots: tuple[ExternalSkillRoot, ...] = (),
) -> None:
    sessions_root = run_home / "sessions"
    expected_agent_slugs = {agent.slug for agent in flow.agents.values()}
    for existing in sorted(sessions_root.iterdir()):
        if existing.name in expected_agent_slugs:
            continue
        _remove_path(existing / "skills")

    external_roots_by_alias = {entry.alias: entry.root for entry in external_skill_roots}
    for agent in flow.agents.values():
        skill_view_root = _agent_skill_view_root(run_home=run_home, agent_slug=agent.slug)
        skill_view_root.mkdir(parents=True, exist_ok=True)
        _sync_named_directories(
            target_root=skill_view_root,
            sources_by_name=_resolve_agent_skill_sources(
                repo_root=repo_root,
                agent=agent,
                builtins=builtins,
                external_roots_by_alias=external_roots_by_alias,
            ),
        )


def _copy_allowed_mcps(*, repo_root: Path, run_home: Path, flow: FlowDefinition) -> None:
    mcp_sources: dict[str, Path] = {}
    for mcp_name in _allowed_mcp_names(flow):
        source = repo_root / "mcps" / mcp_name
        if not source.is_dir():
            raise RallyConfigError(f"Allowed MCP does not exist: `{source}`.")
        server_file = source / "server.toml"
        if not server_file.is_file():
            raise RallyConfigError(f"Allowed MCP `{mcp_name}` is missing `server.toml`: `{server_file}`.")
        mcp_sources[mcp_name] = source

    _sync_named_directories(target_root=run_home / "mcps", sources_by_name=mcp_sources)


def _resolve_agent_skill_sources(
    *,
    repo_root: Path,
    agent: FlowAgent,
    builtins: RallyBuiltinAssets,
    external_roots_by_alias: Mapping[str, Path],
) -> dict[str, Path]:
    # The per-agent view is keyed by the unqualified skill name — that is the
    # directory name adapters expose to the agent (`.claude/skills/<name>/`).
    # The tier the skill came from is an authoring concept that does not leak
    # into the runtime layout.
    skill_sources: dict[str, Path] = {}

    for skill_name in (*MANDATORY_SKILL_NAMES, *agent.allowed_skills, *agent.system_skills):
        if skill_name in skill_sources:
            continue
        bundle = resolve_skill_bundle_source(
            repo_root=repo_root,
            skill_name=skill_name,
            builtins=builtins,
        )
        skill_sources[skill_name] = bundle.runtime_source_dir()

    for qualified_name in agent.external_skills:
        alias, unqualified = split_external_skill_name(qualified_name)
        root = external_roots_by_alias.get(alias)
        if root is None:
            raise RallyConfigError(
                f"External skill `{qualified_name}` referenced by agent `{agent.key}` has no "
                f"registered root alias `{alias}`. Register it under "
                "`[tool.rally.workspace.external_skill_roots]` in pyproject.toml."
            )
        if unqualified in skill_sources:
            raise RallyConfigError(
                f"Agent `{agent.key}` expects two skills named `{unqualified}`: one from a "
                f"workspace or stdlib tier, and one from `external_skills` "
                f"(`{qualified_name}`). Rename one to avoid the collision."
            )
        bundle = resolve_external_skill_bundle_source(
            root=root,
            alias=alias,
            skill_name=unqualified,
        )
        skill_sources[unqualified] = bundle.runtime_source_dir()

    return skill_sources


def _load_agent_skill_view_sources(*, skill_view_root: Path, agent: FlowAgent) -> dict[str, Path]:
    if not skill_view_root.is_dir():
        raise RallyStateError(
            f"Run home is missing the prebuilt skill view for `{agent.slug}` at `{skill_view_root}`."
        )

    skill_sources = {
        existing.name: existing for existing in sorted(skill_view_root.iterdir()) if existing.is_dir()
    }
    expected_names = set(_agent_skill_names(agent))
    actual_names = set(skill_sources)
    if actual_names != expected_names:
        missing_names = sorted(expected_names - actual_names)
        unexpected_names = sorted(actual_names - expected_names)
        mismatch_parts: list[str] = []
        if missing_names:
            mismatch_parts.append(f"missing {missing_names}")
        if unexpected_names:
            mismatch_parts.append(f"unexpected {unexpected_names}")
        mismatch_text = ", ".join(mismatch_parts) if mismatch_parts else "unknown mismatch"
        raise RallyStateError(
            f"Run home skill view for `{agent.slug}` is out of sync at `{skill_view_root}`: {mismatch_text}."
        )
    return skill_sources


def _agent_skill_names(agent: FlowAgent) -> tuple[str, ...]:
    external_unqualified = tuple(
        split_external_skill_name(name)[1] for name in agent.external_skills
    )
    return tuple(
        sorted(
            {
                *(MANDATORY_SKILL_NAMES),
                *(agent.allowed_skills),
                *(agent.system_skills),
                *external_unqualified,
            }
        )
    )


def _agent_skill_view_root(*, run_home: Path, agent_slug: str) -> Path:
    return run_home / "sessions" / agent_slug / "skills"


def _allowed_mcp_names(flow: FlowDefinition) -> tuple[str, ...]:
    return tuple(sorted({mcp for agent in flow.agents.values() for mcp in agent.allowed_mcps}))


def _run_setup_script(
    *,
    workspace: WorkspaceContext,
    flow: FlowDefinition,
    run_record: RunRecord,
    run_home: Path,
    issue_path: Path,
    event_recorder: RunEventRecorder | None = None,
) -> None:
    if flow.setup_home_script is None:
        return

    if event_recorder is not None:
        event_recorder.emit(
            source="rally",
            kind="lifecycle",
            code="SETUP",
            message=f"Running setup script `{flow.setup_home_script.name}`.",
        )

    env = build_flow_subprocess_env(
        flow=flow,
        workspace=workspace,
        run_home=run_home,
        extra_env={
            "RALLY_CLI_BIN": str(workspace.cli_bin.resolve()),
            "RALLY_FLOW_CODE": run_record.flow_code,
            "RALLY_FLOW_HOME": str(run_home.resolve()),
            "RALLY_ISSUE_PATH": str(issue_path.resolve()),
            "RALLY_RUN_HOME": str(run_home.resolve()),
            "RALLY_RUN_ID": run_record.id,
            "RALLY_WORKSPACE_DIR": str(workspace.workspace_root.resolve()),
        },
    )
    completed = subprocess.run(
        ["bash", str(flow.setup_home_script)],
        cwd=flow.root_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "setup script failed"
        if event_recorder is not None:
            event_recorder.emit(
                source="rally",
                kind="warning",
                code="ERROR",
                message=f"Setup script failed: {stderr}",
                level="error",
                data={"setup_script": str(flow.setup_home_script)},
            )
        raise RallyStateError(
            f"Setup script `{flow.setup_home_script}` failed for run `{run_record.id}`: {stderr}"
        )
    if event_recorder is not None:
        event_recorder.emit(
            source="rally",
            kind="lifecycle",
            code="SETUP OK",
            message=f"Setup script `{flow.setup_home_script.name}` finished.",
        )


def _require_host_inputs_ready(
    *,
    workspace: WorkspaceContext,
    flow: FlowDefinition,
    run_home: Path,
    event_recorder: RunEventRecorder | None = None,
) -> None:
    effective_env = build_flow_subprocess_env(
        flow=flow,
        workspace=workspace,
        run_home=run_home,
    )
    for env_name in flow.host_inputs.required_env:
        if effective_env.get(env_name, "").strip():
            continue
        message = (
            f"Flow `{flow.name}` requires env var `{env_name}` before "
            "`setup_home_script` can run."
        )
        _emit_host_input_error(message=message, event_recorder=event_recorder, data={"env_var": env_name})
        raise RallyUsageError(message)

    for rooted_path in flow.host_inputs.required_files:
        resolved_path = _resolve_host_input_path(
            workspace=workspace,
            rooted_path=rooted_path,
            env=effective_env,
        )
        if resolved_path.is_file():
            continue
        message = (
            f"Flow `{flow.name}` requires host file `{rooted_path}` before "
            "`setup_home_script` can run."
        )
        _emit_host_input_error(
            message=message,
            event_recorder=event_recorder,
            data={"required_file": str(rooted_path), "resolved_path": str(resolved_path)},
        )
        raise RallyUsageError(message)

    for rooted_path in flow.host_inputs.required_directories:
        resolved_path = _resolve_host_input_path(
            workspace=workspace,
            rooted_path=rooted_path,
            env=effective_env,
        )
        if resolved_path.is_dir():
            continue
        message = (
            f"Flow `{flow.name}` requires host directory `{rooted_path}` before "
            "`setup_home_script` can run."
        )
        _emit_host_input_error(
            message=message,
            event_recorder=event_recorder,
            data={"required_directory": str(rooted_path), "resolved_path": str(resolved_path)},
        )
        raise RallyUsageError(message)


def _resolve_host_input_path(
    *,
    workspace: WorkspaceContext,
    rooted_path: RootedPath,
    env: Mapping[str, str] | None = None,
) -> Path:
    return resolve_rooted_path(
        rooted_path,
        workspace_root=workspace.workspace_root,
        env=env,
        context="host input",
    )


def _emit_host_input_error(
    *,
    message: str,
    event_recorder: RunEventRecorder | None,
    data: dict[str, object],
) -> None:
    if event_recorder is None:
        return
    event_recorder.emit(
        source="rally",
        kind="warning",
        code="INPUT",
        message=message,
        level="error",
        data=data,
    )


def _coerce_workspace(
    *,
    workspace: WorkspaceContext | None,
    repo_root: Path | None,
) -> WorkspaceContext:
    if workspace is not None and repo_root is not None:
        raise RallyConfigError("Pass either `workspace` or `repo_root`, not both.")
    if workspace is not None:
        return workspace
    if repo_root is None:
        raise RallyConfigError("Run-home materialization needs a workspace root.")
    return workspace_context_from_root(repo_root)
