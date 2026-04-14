from __future__ import annotations

import filecmp
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path
from typing import Iterator

from rally.errors import RallyConfigError

_BUNDLED_PACKAGE = "rally._bundled"
_BUNDLED_ROOT = Path("src") / "rally" / "_bundled"
_IGNORED_BUNDLE_DIR_NAMES = {"__pycache__"}
_IGNORED_BUNDLE_SUFFIXES = {".pyc", ".pyo"}


@dataclass(frozen=True)
class _BundleSpec:
    authored_relative: Path
    bundled_relative: Path
    workspace_relative: Path


_BUNDLE_SPECS = (
    _BundleSpec(
        authored_relative=Path("stdlib") / "rally",
        bundled_relative=Path("stdlib") / "rally",
        workspace_relative=Path("stdlib") / "rally",
    ),
    _BundleSpec(
        authored_relative=Path("skills") / "rally-kernel" / "build",
        bundled_relative=Path("skills") / "rally-kernel",
        workspace_relative=Path("skills") / "rally-kernel",
    ),
    _BundleSpec(
        authored_relative=Path("skills") / "rally-memory" / "build",
        bundled_relative=Path("skills") / "rally-memory",
        workspace_relative=Path("skills") / "rally-memory",
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
    if _is_rally_source_workspace(pyproject_path=pyproject_path):
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
    for spec in _BUNDLE_SPECS:
        source = repo_root / spec.authored_relative
        if not source.is_dir():
            raise RallyConfigError(f"Bundled asset source is missing: `{source}`.")
        target = expected_root / spec.bundled_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)


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
    text = pyproject_path.read_text(encoding="utf-8")
    return 'name = "rally"' in text or "name = 'rally'" in text
