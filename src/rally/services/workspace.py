from __future__ import annotations

import os
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

from rally.errors import RallyConfigError

_WORKSPACE_PATH_NAMES = ("flows", "skills", "mcps", "stdlib", "runs")


@dataclass(frozen=True)
class WorkspaceContext:
    workspace_root: Path
    pyproject_path: Path
    flows_dir: Path
    skills_dir: Path
    mcps_dir: Path
    stdlib_dir: Path
    runs_dir: Path
    cli_bin: Path


def resolve_workspace(*, start_path: Path | None = None) -> WorkspaceContext:
    search_root = _resolve_search_root(start_path)
    matches = _find_workspace_manifests(search_root)
    if not matches:
        raise RallyConfigError(
            "No Rally workspace manifest was found from "
            f"`{search_root}` upward. Add `[tool.rally.workspace]` to the "
            "workspace root `pyproject.toml`."
        )
    if len(matches) > 1:
        rendered = ", ".join(f"`{path}`" for path in matches)
        raise RallyConfigError(
            f"Ambiguous Rally workspace root for `{search_root}`. "
            f"Found nested workspace manifests: {rendered}."
        )
    return workspace_context_from_root(matches[0].parent, require_manifest=True)


def workspace_context_from_root(
    workspace_root: Path,
    *,
    cli_bin: Path | None = None,
    require_manifest: bool = False,
) -> WorkspaceContext:
    workspace_root = workspace_root.resolve()
    pyproject_path = workspace_root / "pyproject.toml"
    if require_manifest and not pyproject_path.is_file():
        raise RallyConfigError(f"Rally workspace pyproject is missing: `{pyproject_path}`.")
    if require_manifest and not _pyproject_has_workspace_manifest(pyproject_path):
        raise RallyConfigError(
            f"Rally workspace manifest is missing from `{pyproject_path}`. "
            "Add `[tool.rally.workspace]` to the workspace root."
        )

    resolved_cli_bin = (cli_bin or resolve_rally_cli_bin()).resolve()
    layout_paths = {name: workspace_root / name for name in _WORKSPACE_PATH_NAMES}
    return WorkspaceContext(
        workspace_root=workspace_root,
        pyproject_path=pyproject_path,
        flows_dir=layout_paths["flows"],
        skills_dir=layout_paths["skills"],
        mcps_dir=layout_paths["mcps"],
        stdlib_dir=layout_paths["stdlib"],
        runs_dir=layout_paths["runs"],
        cli_bin=resolved_cli_bin,
    )


def resolve_rally_cli_bin() -> Path:
    env_path = os.environ.get("RALLY_CLI_BIN")
    if env_path:
        return Path(env_path).expanduser().resolve()

    which_match = shutil.which("rally")
    if which_match:
        return Path(which_match).resolve()

    executable_peer = Path(sys.executable).resolve().with_name("rally")
    if executable_peer.is_file():
        return executable_peer

    raise RallyConfigError(
        "Rally CLI executable is missing. Set `RALLY_CLI_BIN` or add `rally` to PATH."
    )

def _resolve_search_root(start_path: Path | None) -> Path:
    candidate = (start_path or Path.cwd()).expanduser().resolve()
    if candidate.is_file():
        return candidate.parent
    return candidate


def _find_workspace_manifests(search_root: Path) -> list[Path]:
    matches: list[Path] = []
    for candidate in (search_root, *search_root.parents):
        pyproject_path = candidate / "pyproject.toml"
        if _pyproject_has_workspace_manifest(pyproject_path):
            matches.append(pyproject_path)
    return matches


def _pyproject_has_workspace_manifest(pyproject_path: Path) -> bool:
    if not pyproject_path.is_file():
        return False
    payload = _load_pyproject(pyproject_path)
    tool_payload = payload.get("tool")
    if not isinstance(tool_payload, dict):
        return False
    rally_payload = tool_payload.get("rally")
    if not isinstance(rally_payload, dict):
        return False
    return isinstance(rally_payload.get("workspace"), dict)


def _load_pyproject(pyproject_path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise RallyConfigError(f"Workspace pyproject is not valid TOML: `{pyproject_path}`.") from exc
