from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Literal
import tomllib

from rally.errors import RallyConfigError
from rally.services.workspace import WorkspaceContext

RALLY_DISTRIBUTION_NAME = "rally-agents"
RALLY_BUILTIN_SKILL_NAMES = ("rally-kernel", "rally-memory")
RALLY_REQUIRED_BUILTIN_SKILL_NAMES = ("rally-kernel",)
RALLY_STDLIB_PROVIDER_NAME = "rally_stdlib"
_RALLY_SOURCE_PROJECT_NAMES = frozenset({"rally", "rally-agents"})
_ASSET_PREFIX = "rally_assets"


BuiltinAssetSourceKind = Literal["source_checkout", "installed_distribution"]


@dataclass(frozen=True)
class RallyBuiltinAssets:
    stdlib_root: Path
    stdlib_prompts_root: Path
    skill_runtime_dirs: dict[str, Path]
    source_kind: BuiltinAssetSourceKind
    source_root: Path | None = None

    def provided_prompt_roots(self):
        from doctrine.compiler import ProvidedPromptRoot

        return (
            ProvidedPromptRoot(
                name=RALLY_STDLIB_PROVIDER_NAME,
                path=self.stdlib_prompts_root,
            ),
        )

    def skill_runtime_dir(self, skill_name: str) -> Path:
        try:
            return self.skill_runtime_dirs[skill_name]
        except KeyError as exc:
            raise RallyConfigError(f"Unknown Rally built-in skill `{skill_name}`.") from exc


def resolve_rally_builtin_assets(
    *,
    workspace: WorkspaceContext | None = None,
    workspace_root: Path | None = None,
) -> RallyBuiltinAssets:
    # This resolver owns the source-checkout versus installed-package split.
    # Do not add fallback paths that could hide stale built-in copies.
    if workspace is not None and workspace_root is not None:
        raise RallyConfigError("Pass either `workspace` or `workspace_root`, not both.")
    root_hint = workspace.workspace_root if workspace is not None else workspace_root
    source_root = _resolve_source_checkout_root(root_hint=root_hint)
    if source_root is not None:
        return _assets_from_source_checkout(source_root)
    return _assets_from_installed_distribution()


def is_rally_source_checkout(*, workspace_root: Path) -> bool:
    return _resolve_source_checkout_root(root_hint=workspace_root) == workspace_root.resolve()


def reject_reserved_builtin_skill_shadow(
    *,
    workspace_root: Path,
    skill_names: tuple[str, ...] = RALLY_BUILTIN_SKILL_NAMES,
    builtins: RallyBuiltinAssets | None = None,
) -> None:
    assets = builtins or resolve_rally_builtin_assets(workspace_root=workspace_root)
    if assets.source_root is not None and workspace_root.resolve() == assets.source_root.resolve():
        return
    for skill_name in skill_names:
        candidate = workspace_root / "skills" / skill_name
        if candidate.exists():
            raise RallyConfigError(
                f"Workspace skill `{candidate}` shadows Rally-owned built-in skill `{skill_name}`. "
                "Remove the workspace copy; Rally resolves built-in skills from its installed assets."
            )


def _resolve_source_checkout_root(*, root_hint: Path | None) -> Path | None:
    for candidate in _candidate_source_roots(root_hint=root_hint):
        if _is_rally_source_root(candidate):
            return candidate.resolve()
    return None


def _candidate_source_roots(*, root_hint: Path | None) -> tuple[Path, ...]:
    module_source_root = Path(__file__).resolve().parents[3]
    candidates: list[Path] = []
    if root_hint is not None:
        candidates.append(root_hint.resolve())
    candidates.append(module_source_root)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return tuple(deduped)


def _is_rally_source_root(candidate: Path) -> bool:
    pyproject_path = candidate / "pyproject.toml"
    if _project_name(pyproject_path) not in _RALLY_SOURCE_PROJECT_NAMES:
        return False
    return _required_source_paths(candidate)


def _required_source_paths(source_root: Path) -> bool:
    return (
        (source_root / "stdlib" / "rally" / "prompts" / "rally" / "base_agent.prompt").is_file()
        and (source_root / "skills" / "rally-kernel" / "prompts" / "SKILL.prompt").is_file()
    )


def _project_name(pyproject_path: Path) -> str | None:
    if not pyproject_path.is_file():
        return None
    try:
        raw = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    project = raw.get("project")
    if not isinstance(project, dict):
        return None
    name = project.get("name")
    return name.strip() if isinstance(name, str) else None


def _assets_from_source_checkout(source_root: Path) -> RallyBuiltinAssets:
    stdlib_root = source_root / "stdlib" / "rally"
    stdlib_prompts_root = stdlib_root / "prompts"
    skill_runtime_dirs = {
        skill_name: source_root / "skills" / skill_name / "build"
        for skill_name in RALLY_BUILTIN_SKILL_NAMES
    }
    assets = RallyBuiltinAssets(
        stdlib_root=stdlib_root,
        stdlib_prompts_root=stdlib_prompts_root,
        skill_runtime_dirs=skill_runtime_dirs,
        source_kind="source_checkout",
        source_root=source_root,
    )
    _validate_assets(assets)
    return assets


def _assets_from_installed_distribution() -> RallyBuiltinAssets:
    try:
        dist = distribution(RALLY_DISTRIBUTION_NAME)
    except PackageNotFoundError as exc:
        raise RallyConfigError(
            f"Rally built-in assets are unavailable because `{RALLY_DISTRIBUTION_NAME}` is not installed."
        ) from exc

    stdlib_marker = _locate_distribution_file(
        dist=dist,
        relative_path=f"{_ASSET_PREFIX}/stdlib/rally/prompts/rally/base_agent.prompt",
    )
    stdlib_prompts_root = stdlib_marker.parents[1]
    stdlib_root = stdlib_prompts_root.parent
    skill_runtime_dirs = {
        skill_name: _locate_distribution_file(
            dist=dist,
            relative_path=f"{_ASSET_PREFIX}/skills/{skill_name}/SKILL.md",
        ).parent
        for skill_name in RALLY_BUILTIN_SKILL_NAMES
    }
    assets = RallyBuiltinAssets(
        stdlib_root=stdlib_root,
        stdlib_prompts_root=stdlib_prompts_root,
        skill_runtime_dirs=skill_runtime_dirs,
        source_kind="installed_distribution",
        source_root=None,
    )
    _validate_assets(assets)
    return assets


def _locate_distribution_file(*, dist, relative_path: str) -> Path:
    suffix = f"/{relative_path}"
    for dist_file in dist.files or ():
        dist_path = dist_file.as_posix()
        if dist_path == relative_path or dist_path.endswith(suffix):
            located = Path(dist_file.locate())
            if located.is_file():
                return located
    raise RallyConfigError(
        f"Installed Rally package is missing built-in asset `{relative_path}`."
    )


def _validate_assets(assets: RallyBuiltinAssets) -> None:
    if not assets.stdlib_prompts_root.is_dir():
        raise RallyConfigError(f"Rally stdlib prompt root is missing: `{assets.stdlib_prompts_root}`.")
    for skill_name in RALLY_REQUIRED_BUILTIN_SKILL_NAMES:
        skill_dir = assets.skill_runtime_dir(skill_name)
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise RallyConfigError(f"Rally built-in skill `{skill_name}` is missing `{skill_file}`.")
