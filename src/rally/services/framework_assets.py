from __future__ import annotations

import shutil
from pathlib import Path

from rally.errors import RallyConfigError
from rally.services.workspace import WorkspaceContext

_RESERVED_FRAMEWORK_PATHS = (
    ("skills", "rally-kernel"),
    ("skills", "rally-memory"),
)


def ensure_framework_builtins(workspace: WorkspaceContext) -> None:
    for relative_parts in _RESERVED_FRAMEWORK_PATHS:
        source_root = workspace.framework_root.joinpath(*relative_parts)
        target_root = workspace.workspace_root.joinpath(*relative_parts)
        if source_root.resolve() == target_root.resolve():
            continue
        if not source_root.is_dir():
            raise RallyConfigError(f"Framework-owned built-in path is missing: `{source_root}`.")
        _sync_reserved_tree(
            source_root=source_root,
            target_root=target_root,
            label="/".join(relative_parts),
        )


def _sync_reserved_tree(*, source_root: Path, target_root: Path, label: str) -> None:
    if target_root.exists() and not target_root.is_dir():
        raise RallyConfigError(f"Reserved built-in path `{target_root}` is not a directory.")
    target_root.mkdir(parents=True, exist_ok=True)

    source_entries = {entry.name: entry for entry in sorted(source_root.iterdir())}
    target_entries = {entry.name: entry for entry in sorted(target_root.iterdir())}

    unexpected = sorted(name for name in target_entries if name not in source_entries)
    if unexpected:
        unexpected_paths = ", ".join(f"`{target_root / name}`" for name in unexpected)
        raise RallyConfigError(
            f"Reserved built-in path `{label}` has unsupported local files: {unexpected_paths}."
        )

    for name, source_entry in source_entries.items():
        target_entry = target_root / name
        if source_entry.is_dir():
            if target_entry.exists() and not target_entry.is_dir():
                raise RallyConfigError(
                    f"Reserved built-in path `{target_entry}` must stay a directory."
                )
            _sync_reserved_tree(
                source_root=source_entry,
                target_root=target_entry,
                label=f"{label}/{name}",
            )
            continue

        if target_entry.is_dir():
            raise RallyConfigError(f"Reserved built-in path `{target_entry}` must stay a file.")
        if not target_entry.exists():
            target_entry.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_entry, target_entry)
            continue
        if source_entry.read_bytes() != target_entry.read_bytes():
            raise RallyConfigError(
                f"Reserved built-in file `{target_entry}` was edited locally. "
                "Restore the framework-owned content or delete the file and rerun Rally."
            )
