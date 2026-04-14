from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rally.services.bundled_assets import ensure_workspace_builtins_synced, workspace_owns_rally_builtins
from rally.services.workspace import WorkspaceContext


@dataclass(frozen=True)
class WorkspaceSyncResult:
    workspace_root: Path
    synced_paths: tuple[str, ...]
    already_owned: bool
    message: str


def sync_workspace_builtins(*, workspace: WorkspaceContext) -> WorkspaceSyncResult:
    workspace_root = workspace.workspace_root.resolve()
    if workspace_owns_rally_builtins(pyproject_path=workspace.pyproject_path):
        return WorkspaceSyncResult(
            workspace_root=workspace_root,
            synced_paths=(),
            already_owned=True,
            message=(
                f"Workspace `{workspace_root}` already owns Rally built-ins. Nothing to sync.\n"
                "Next: emit your flow if needed, or start one with `rally run <flow>`."
            ),
        )

    copied = tuple(
        ensure_workspace_builtins_synced(
            workspace_root=workspace.workspace_root,
            pyproject_path=workspace.pyproject_path,
        )
    )
    rendered_paths = ", ".join(f"`{path}`" for path in copied)
    return WorkspaceSyncResult(
        workspace_root=workspace_root,
        synced_paths=copied,
        already_owned=False,
        message=(
            f"Synced Rally built-ins into `{workspace_root}`: {rendered_paths}.\n"
            "Next: emit your flow if needed, or start one with `rally run <flow>`."
        ),
    )
