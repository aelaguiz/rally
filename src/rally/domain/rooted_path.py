from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from rally.errors import RallyConfigError

PathRoot = Literal["home", "flow", "workspace", "host", "stdlib"]

HOME_ROOT: PathRoot = "home"
FLOW_ROOT: PathRoot = "flow"
WORKSPACE_ROOT: PathRoot = "workspace"
HOST_ROOT: PathRoot = "host"
STDLIB_ROOT: PathRoot = "stdlib"

PUBLIC_PATH_ROOTS = frozenset({HOME_ROOT, FLOW_ROOT, WORKSPACE_ROOT, HOST_ROOT})
INTERNAL_PATH_ROOTS = frozenset({*PUBLIC_PATH_ROOTS, STDLIB_ROOT})


@dataclass(frozen=True)
class RootedPath:
    root: PathRoot
    path_text: str

    def __str__(self) -> str:
        return f"{self.root}:{self.path_text}"

    def relative_path(self) -> PurePosixPath:
        if self.root == HOST_ROOT:
            raise ValueError("`host:` paths are not flow-relative.")
        return PurePosixPath(self.path_text)


def parse_rooted_path(
    raw_value: str,
    *,
    context: str,
    allowed_roots: Collection[PathRoot],
    example: str,
) -> RootedPath:
    value = raw_value.strip()
    root_name, separator, path_text = value.partition(":")
    if not separator:
        raise RallyConfigError(f"{context} must use a rooted Rally path like `{example}`, not `{raw_value}`.")
    if not root_name or root_name not in INTERNAL_PATH_ROOTS:
        allowed = ", ".join(f"`{root}:...`" for root in sorted(allowed_roots))
        raise RallyConfigError(f"{context} must start with one of {allowed}, not `{raw_value}`.")
    root = root_name  # typed by membership check above
    if root not in allowed_roots:
        allowed = ", ".join(f"`{allowed_root}:...`" for allowed_root in sorted(allowed_roots))
        raise RallyConfigError(f"{context} must use {allowed}, not `{raw_value}`.")
    if root == HOST_ROOT:
        return RootedPath(root=root, path_text=_normalize_host_path(path_text=path_text, context=context))
    return RootedPath(root=root, path_text=_normalize_relative_path(path_text=path_text, context=context))


def maybe_parse_rooted_path(
    raw_value: str,
    *,
    context: str,
    allowed_roots: Collection[PathRoot],
    example: str,
) -> RootedPath | None:
    value = raw_value.strip()
    root_name, separator, _path_text = value.partition(":")
    if not separator or root_name not in INTERNAL_PATH_ROOTS:
        return None
    return parse_rooted_path(
        raw_value=value,
        context=context,
        allowed_roots=allowed_roots,
        example=example,
    )


def resolve_rooted_path(
    rooted_path: RootedPath,
    *,
    workspace_root: Path | None = None,
    flow_root: Path | None = None,
    run_home: Path | None = None,
    framework_root: Path | None = None,
    context: str,
) -> Path:
    if rooted_path.root == HOST_ROOT:
        return Path(rooted_path.path_text).expanduser().resolve(strict=False)

    if rooted_path.root == HOME_ROOT:
        return _resolve_under_root(
            base_path=_require_base_path(run_home, label="run home", context=context),
            rooted_path=rooted_path,
            context=context,
        )
    if rooted_path.root == FLOW_ROOT:
        return _resolve_under_root(
            base_path=_require_base_path(flow_root, label="flow root", context=context),
            rooted_path=rooted_path,
            context=context,
        )
    if rooted_path.root == WORKSPACE_ROOT:
        return _resolve_under_root(
            base_path=_require_base_path(workspace_root, label="workspace root", context=context),
            rooted_path=rooted_path,
            context=context,
        )
    if rooted_path.root == STDLIB_ROOT:
        if framework_root is not None:
            return _resolve_under_root(
                base_path=_require_base_path(framework_root, label="framework root", context=context)
                / "stdlib"
                / "rally",
                rooted_path=rooted_path,
                context=context,
            )
        workspace_base = _require_base_path(workspace_root, label="workspace root", context=context)
        return _resolve_under_root(
            base_path=workspace_base / "stdlib" / "rally",
            rooted_path=rooted_path,
            context=context,
        )
    raise AssertionError(f"Unhandled rooted path root: {rooted_path.root}")


def expand_rooted_string(
    raw_value: str,
    *,
    workspace_root: Path | None = None,
    flow_root: Path | None = None,
    run_home: Path | None = None,
    framework_root: Path | None = None,
    allowed_roots: Collection[PathRoot] = INTERNAL_PATH_ROOTS,
    context: str,
    example: str = "home:issue.md",
) -> str:
    rooted_path = maybe_parse_rooted_path(
        raw_value,
        context=context,
        allowed_roots=allowed_roots,
        example=example,
    )
    if rooted_path is None:
        return raw_value
    return str(
        resolve_rooted_path(
            rooted_path,
            workspace_root=workspace_root,
            flow_root=flow_root,
            run_home=run_home,
            framework_root=framework_root,
            context=context,
        )
    )


def expand_rooted_value(
    raw_value: object,
    *,
    workspace_root: Path | None = None,
    flow_root: Path | None = None,
    run_home: Path | None = None,
    framework_root: Path | None = None,
    allowed_roots: Collection[PathRoot] = INTERNAL_PATH_ROOTS,
    context: str,
    example: str = "home:issue.md",
) -> object:
    if isinstance(raw_value, str):
        return expand_rooted_string(
            raw_value,
            workspace_root=workspace_root,
            flow_root=flow_root,
            run_home=run_home,
            framework_root=framework_root,
            allowed_roots=allowed_roots,
            context=context,
            example=example,
        )
    if isinstance(raw_value, list):
        return [
            expand_rooted_value(
                item,
                workspace_root=workspace_root,
                flow_root=flow_root,
                run_home=run_home,
                framework_root=framework_root,
                allowed_roots=allowed_roots,
                context=context,
                example=example,
            )
            for item in raw_value
        ]
    if isinstance(raw_value, dict):
        return {
            key: expand_rooted_value(
                value,
                workspace_root=workspace_root,
                flow_root=flow_root,
                run_home=run_home,
                framework_root=framework_root,
                allowed_roots=allowed_roots,
                context=f"{context}.{key}",
                example=example,
            )
            for key, value in raw_value.items()
        }
    return raw_value


def _normalize_relative_path(*, path_text: str, context: str) -> str:
    value = path_text.strip()
    pure_path = PurePosixPath(value)
    if pure_path.is_absolute():
        raise RallyConfigError(f"{context} must stay relative after the root, not `{path_text}`.")
    if value in {"", "."}:
        raise RallyConfigError(f"{context} must name a child path after the root.")
    if ".." in pure_path.parts:
        raise RallyConfigError(f"{context} must not escape its root with `..`.")
    return pure_path.as_posix()


def _normalize_host_path(*, path_text: str, context: str) -> str:
    value = path_text.strip()
    if not value:
        raise RallyConfigError(f"{context} must name a host path after `host:`.")
    if value == "~" or value.startswith("~/"):
        return value
    if not Path(value).is_absolute():
        raise RallyConfigError(f"{context} must use an absolute path or `~/...` after `host:`.")
    return value


def _resolve_under_root(*, base_path: Path, rooted_path: RootedPath, context: str) -> Path:
    resolved_base = base_path.resolve()
    candidate = (resolved_base / rooted_path.relative_path()).resolve()
    try:
        candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise RallyConfigError(f"{context} escapes `{resolved_base}`: `{rooted_path}`.") from exc
    return candidate


def _require_base_path(base_path: Path | None, *, label: str, context: str) -> Path:
    if base_path is not None:
        return base_path
    raise RallyConfigError(f"{context} needs the {label} to resolve rooted paths.")
