from __future__ import annotations

import filecmp
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
import tomllib
from typing import Iterator

from rally.errors import RallyConfigError

_BUNDLED_PACKAGE = "rally._bundled"
_BUNDLED_ROOT = Path("src") / "rally" / "_bundled"
_IGNORED_BUNDLE_DIR_NAMES = {"__pycache__"}
_IGNORED_BUNDLE_SUFFIXES = {".pyc", ".pyo"}
_RALLY_SOURCE_WORKSPACE_PROJECT_NAMES = frozenset({"rally", "rally-agents"})


@dataclass(frozen=True)
class _BundleSpec:
    bundled_relative: Path
    workspace_relative: Path
    authored_relative: Path | None = None
    emit_target_name: str | None = None


_BUNDLE_SPECS = (
    _BundleSpec(
        bundled_relative=Path("stdlib") / "rally",
        workspace_relative=Path("stdlib") / "rally",
        authored_relative=Path("stdlib") / "rally",
    ),
    _BundleSpec(
        bundled_relative=Path("skills") / "rally-kernel",
        workspace_relative=Path("skills") / "rally-kernel",
        emit_target_name="rally-kernel",
    ),
)


def sync_bundled_assets(*, repo_root: Path, check: bool = False) -> list[str]:
    repo_root = repo_root.resolve()
    bundled_root = repo_root / _BUNDLED_ROOT
    with tempfile.TemporaryDirectory(prefix="rally-bundle-") as temp_dir:
        expected_root = Path(temp_dir) / "expected"
        _build_expected_bundle(repo_root=repo_root, expected_root=expected_root)
        differences = _compare_trees(expected_root=expected_root, actual_root=bundled_root)
        if check:
            return differences
        _replace_tree(source_root=expected_root, target_root=bundled_root)
        return differences


def ensure_workspace_builtins_synced(*, workspace_root: Path, pyproject_path: Path) -> list[str]:
    workspace_root = workspace_root.resolve()
    if workspace_owns_rally_builtins(pyproject_path=pyproject_path):
        return []

    copied: list[str] = []
    with _bundled_package_root() as bundle_root:
        for spec in _BUNDLE_SPECS:
            source = bundle_root / spec.bundled_relative
            target = workspace_root / spec.workspace_relative
            if not source.is_dir():
                raise RallyConfigError(f"Bundled Rally asset is missing: `{source}`.")
            _replace_tree(source_root=source, target_root=target)
            copied.append(spec.workspace_relative.as_posix())
    return copied


def workspace_owns_rally_builtins(*, pyproject_path: Path) -> bool:
    return _is_rally_source_workspace(pyproject_path=pyproject_path)


@contextmanager
def _bundled_package_root() -> Iterator[Path]:
    traversable = files(_BUNDLED_PACKAGE)
    with as_file(traversable) as root_path:
        yield Path(root_path)


def _build_expected_bundle(*, repo_root: Path, expected_root: Path) -> None:
    expected_root.mkdir(parents=True, exist_ok=True)
    (expected_root / "__init__.py").write_text(
        '"""Bundled Rally-owned built-ins shipped inside the installable package."""\n',
        encoding="utf-8",
    )
    # Skill bundles are authored as Doctrine source and emitted build output is
    # ignored in git, so clean-checkout verification has to emit the expected
    # package tree from source before it compares src/rally/_bundled.
    emit_targets = _load_emit_targets(repo_root=repo_root)
    for spec in _BUNDLE_SPECS:
        target = expected_root / spec.bundled_relative
        if spec.authored_relative is not None:
            source = repo_root / spec.authored_relative
            if not source.is_dir():
                raise RallyConfigError(f"Bundled asset source is missing: `{source}`.")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
            continue
        if spec.emit_target_name is not None:
            emit_target = emit_targets.get(spec.emit_target_name)
            if emit_target is None:
                raise RallyConfigError(
                    f"Doctrine emit target `{spec.emit_target_name}` is missing from `{repo_root / 'pyproject.toml'}`."
                )
            _emit_skill_bundle(emit_target=emit_target, output_dir=target)
            continue
        raise RallyConfigError(f"Bundled asset spec for `{spec.bundled_relative}` is incomplete.")


def _load_emit_targets(*, repo_root: Path) -> dict[str, object]:
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise RallyConfigError(f"Rally workspace pyproject is missing: `{pyproject_path}`.")
    try:
        from doctrine.diagnostics import DoctrineError
        from doctrine.emit_common import load_emit_targets
    except ImportError as exc:
        raise RallyConfigError(f"Failed to import Doctrine while building bundled assets: {exc}.") from exc

    try:
        return load_emit_targets(pyproject_path)
    except DoctrineError as exc:
        raise RallyConfigError(f"Failed to load Doctrine emit targets from `{pyproject_path}`: {exc}") from exc


def _emit_skill_bundle(*, emit_target: object, output_dir: Path) -> None:
    try:
        from doctrine.diagnostics import DoctrineError
        from doctrine.emit_skill import emit_target_skill
    except ImportError as exc:
        raise RallyConfigError(f"Failed to import Doctrine skill emitter while building bundled assets: {exc}.") from exc

    try:
        emit_target_skill(emit_target, output_dir_override=output_dir)
    except DoctrineError as exc:
        raise RallyConfigError(f"Failed to emit bundled skill package `{emit_target.name}`: {exc}") from exc


def _compare_trees(*, expected_root: Path, actual_root: Path) -> list[str]:
    expected_files = _list_relative_files(expected_root)
    actual_files = _list_relative_files(actual_root)
    differences: list[str] = []
    for relative_path in sorted(expected_files - actual_files):
        differences.append(f"missing `{relative_path.as_posix()}` in bundled assets")
    for relative_path in sorted(actual_files - expected_files):
        differences.append(f"unexpected `{relative_path.as_posix()}` in bundled assets")
    for relative_path in sorted(expected_files & actual_files):
        expected_file = expected_root / relative_path
        actual_file = actual_root / relative_path
        if filecmp.cmp(expected_file, actual_file, shallow=False):
            continue
        differences.append(f"content drift in `{relative_path.as_posix()}`")
    return differences


def _list_relative_files(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not _should_ignore_bundle_path(path.relative_to(root))
    }


def _should_ignore_bundle_path(relative_path: Path) -> bool:
    if any(part in _IGNORED_BUNDLE_DIR_NAMES for part in relative_path.parts):
        return True
    return relative_path.suffix in _IGNORED_BUNDLE_SUFFIXES


def _replace_tree(*, source_root: Path, target_root: Path) -> None:
    target_root.parent.mkdir(parents=True, exist_ok=True)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)


def _is_rally_source_workspace(*, pyproject_path: Path) -> bool:
    if not pyproject_path.is_file():
        return False
    try:
        raw = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return False
    project = raw.get("project")
    if not isinstance(project, dict):
        return False
    name = project.get("name")
    if not isinstance(name, str):
        return False
    return name.strip() in _RALLY_SOURCE_WORKSPACE_PROJECT_NAMES
