from __future__ import annotations

import os
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from rally.errors import RallyConfigError

_WORKSPACE_PATH_NAMES = ("flows", "skills", "mcps", "stdlib", "runs")

_EXTERNAL_SKILL_ROOT_ALIAS_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
# Aliases reserved either by Rally's own path-root vocabulary (`flow:`, `home:`,
# `workspace:`) or by the tier names used in docs and errors. Rejecting them
# keeps the "<alias>:<skill>" namespace legible at a glance.
_RESERVED_EXTERNAL_SKILL_ROOT_ALIASES = frozenset(
    {
        "rally",
        "stdlib",
        "system",
        "flow",
        "home",
        "workspace",
        "host",
        "local",
        "builtin",
        "builtins",
    }
)


@dataclass(frozen=True)
class ExternalSkillRoot:
    alias: str
    root: Path


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
    external_skill_roots: tuple[ExternalSkillRoot, ...] = field(default_factory=tuple)

    def external_skill_root(self, alias: str) -> ExternalSkillRoot | None:
        for entry in self.external_skill_roots:
            if entry.alias == alias:
                return entry
        return None


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
    external_skill_roots = _load_external_skill_roots(
        pyproject_path=pyproject_path,
        workspace_root=workspace_root,
    )
    return WorkspaceContext(
        workspace_root=workspace_root,
        pyproject_path=pyproject_path,
        flows_dir=layout_paths["flows"],
        skills_dir=layout_paths["skills"],
        mcps_dir=layout_paths["mcps"],
        stdlib_dir=layout_paths["stdlib"],
        runs_dir=layout_paths["runs"],
        cli_bin=resolved_cli_bin,
        external_skill_roots=external_skill_roots,
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


def load_external_skill_roots_for_repo_root(
    *,
    repo_root: Path,
) -> tuple[ExternalSkillRoot, ...]:
    """Load external skill roots from `<repo_root>/pyproject.toml`.

    Returns `()` if the pyproject is absent — callers that need the manifest
    enforced must use `workspace_context_from_root(..., require_manifest=True)`.
    Raises `RallyConfigError` if the manifest exists but declares invalid roots.
    """
    workspace_root = repo_root.resolve()
    pyproject_path = workspace_root / "pyproject.toml"
    return _load_external_skill_roots(
        pyproject_path=pyproject_path,
        workspace_root=workspace_root,
    )


def _load_external_skill_roots(
    *,
    pyproject_path: Path,
    workspace_root: Path,
) -> tuple[ExternalSkillRoot, ...]:
    if not pyproject_path.is_file():
        return ()
    payload = _load_pyproject(pyproject_path)
    workspace_payload = (
        payload.get("tool", {}).get("rally", {}).get("workspace", {})
        if isinstance(payload.get("tool"), dict)
        else {}
    )
    raw_roots = workspace_payload.get("external_skill_roots") if isinstance(workspace_payload, dict) else None
    if raw_roots is None:
        return ()
    if not isinstance(raw_roots, dict):
        raise RallyConfigError(
            f"`[tool.rally.workspace.external_skill_roots]` in `{pyproject_path}` "
            "must be a table mapping alias to absolute directory path."
        )

    entries: list[ExternalSkillRoot] = []
    seen_aliases: set[str] = set()
    for raw_alias, raw_path in raw_roots.items():
        if not isinstance(raw_alias, str):
            raise RallyConfigError(
                f"External skill root aliases in `{pyproject_path}` must be strings."
            )
        alias = raw_alias.strip()
        if not _EXTERNAL_SKILL_ROOT_ALIAS_RE.fullmatch(alias):
            raise RallyConfigError(
                f"External skill root alias `{raw_alias}` in `{pyproject_path}` must match "
                "`[a-z][a-z0-9_-]*` (lowercase identifier)."
            )
        if alias in _RESERVED_EXTERNAL_SKILL_ROOT_ALIASES:
            raise RallyConfigError(
                f"External skill root alias `{alias}` in `{pyproject_path}` is reserved. "
                "Pick a different name."
            )
        if alias in seen_aliases:
            raise RallyConfigError(
                f"External skill root alias `{alias}` is declared more than once in `{pyproject_path}`."
            )
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise RallyConfigError(
                f"External skill root `{alias}` in `{pyproject_path}` must map to a non-empty path string."
            )
        expanded = Path(raw_path).expanduser()
        if not expanded.is_absolute():
            raise RallyConfigError(
                f"External skill root `{alias}` in `{pyproject_path}` must be an absolute path; got `{raw_path}`."
            )
        resolved = expanded.resolve()
        if not resolved.is_dir():
            raise RallyConfigError(
                f"External skill root `{alias}` in `{pyproject_path}` does not exist or is not a directory: `{resolved}`."
            )
        try:
            resolved.relative_to(workspace_root)
        except ValueError:
            pass
        else:
            raise RallyConfigError(
                f"External skill root `{alias}` in `{pyproject_path}` points inside the workspace (`{resolved}`). "
                "Use `allowed_skills` for workspace-local skills instead."
            )
        seen_aliases.add(alias)
        entries.append(ExternalSkillRoot(alias=alias, root=resolved))
    return tuple(entries)
