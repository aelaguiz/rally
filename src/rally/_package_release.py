from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib

_SUPPORTED_DOCTRINE_PACKAGE_NAMES = frozenset({"doctrine", "doctrine-agents"})
_DEPENDENCY_NAME_RE = re.compile(r"^\s*(?P<name>[A-Za-z0-9_.-]+)")


@dataclass(frozen=True)
class PackageReleaseMetadata:
    distribution_name: str
    version: str
    import_name: str
    pypi_environment: str
    testpypi_environment: str

    @property
    def pypi_project_url(self) -> str:
        return f"https://pypi.org/project/{self.distribution_name}/"

    @property
    def testpypi_project_url(self) -> str:
        return f"https://test.pypi.org/project/{self.distribution_name}/"

    def as_json(self) -> dict[str, str]:
        return {
            "distribution_name": self.distribution_name,
            "version": self.version,
            "import_name": self.import_name,
            "pypi_environment": self.pypi_environment,
            "testpypi_environment": self.testpypi_environment,
            "pypi_project_url": self.pypi_project_url,
            "testpypi_project_url": self.testpypi_project_url,
        }


def load_package_release_metadata(repo_root: Path) -> PackageReleaseMetadata:
    pyproject_path = repo_root / "pyproject.toml"
    try:
        raw = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"`{pyproject_path}` is missing.") from exc
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(f"`{pyproject_path}` is not valid TOML.") from exc

    project = raw.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("`pyproject.toml` must contain a `[project]` table.")

    distribution_name = _require_string(project, key="name", table_name="[project]")
    version = _require_string(project, key="version", table_name="[project]")

    tool = raw.get("tool")
    rally_tool = tool.get("rally") if isinstance(tool, dict) else None
    package = rally_tool.get("package") if isinstance(rally_tool, dict) else None
    if not isinstance(package, dict):
        raise RuntimeError("`pyproject.toml` must contain a `[tool.rally.package]` table.")

    import_name = _require_string(
        package,
        key="import_name",
        table_name="[tool.rally.package]",
    )
    pypi_environment = _require_string(
        package,
        key="pypi_environment",
        table_name="[tool.rally.package]",
    )
    testpypi_environment = _require_string(
        package,
        key="testpypi_environment",
        table_name="[tool.rally.package]",
    )
    return PackageReleaseMetadata(
        distribution_name=distribution_name,
        version=version,
        import_name=import_name,
        pypi_environment=pypi_environment,
        testpypi_environment=testpypi_environment,
    )


def load_doctrine_dependency_line(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    raw = _load_pyproject(pyproject_path)
    project = raw.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("`pyproject.toml` must contain a `[project]` table.")

    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        raise RuntimeError("`[project].dependencies` must be a list of strings.")

    matching_lines = [
        requirement.strip()
        for requirement in dependencies
        if isinstance(requirement, str) and _dependency_name(requirement) in _SUPPORTED_DOCTRINE_PACKAGE_NAMES
    ]
    if len(matching_lines) != 1:
        raise RuntimeError(
            "Expected exactly one Doctrine dependency line under `[project].dependencies`."
        )
    return matching_lines[0]


def resolve_distribution_artifact(*, dist_dir: Path, artifact_type: str) -> Path:
    if artifact_type == "wheel":
        matches = sorted(dist_dir.glob("*.whl"))
    elif artifact_type == "sdist":
        matches = sorted(dist_dir.glob("*.tar.gz"))
    else:
        raise RuntimeError(f"Unsupported artifact type `{artifact_type}`.")

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {artifact_type} artifact in `{dist_dir}`, found {len(matches)}."
        )
    return matches[0].resolve()


def smoke_test_distribution(
    *,
    repo_root: Path,
    artifact_type: str,
    dist_dir: Path,
) -> None:
    metadata = load_package_release_metadata(repo_root)
    artifact_path = resolve_distribution_artifact(dist_dir=dist_dir, artifact_type=artifact_type)

    with tempfile.TemporaryDirectory(prefix="rally-package-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        venv_root = temp_root / "venv"
        python_path = _venv_python(venv_root)
        rally_path = _venv_rally(venv_root)

        _run([sys.executable, "-m", "venv", str(venv_root)], cwd=repo_root)
        _run([str(python_path), "-m", "pip", "install", str(artifact_path)], cwd=repo_root)

        help_result = _run([str(rally_path), "--help"], cwd=temp_root)
        if "usage: rally" not in help_result.stdout:
            raise RuntimeError("Installed Rally CLI did not print the expected `rally --help` output.")

        version_result = _run(
            [
                str(python_path),
                "-c",
                (
                    f"import {metadata.import_name}; "
                    f"print({metadata.import_name}.__version__)"
                ),
            ],
            cwd=temp_root,
        )
        if version_result.stdout.strip() != metadata.version:
            raise RuntimeError(
                "Installed Rally package did not report the expected package metadata version."
            )


def write_github_outputs(*, metadata: PackageReleaseMetadata, output_path: Path) -> None:
    lines = [
        f"distribution_name={metadata.distribution_name}",
        f"version={metadata.version}",
        f"import_name={metadata.import_name}",
        f"pypi_environment={metadata.pypi_environment}",
        f"testpypi_environment={metadata.testpypi_environment}",
        f"pypi_project_url={metadata.pypi_project_url}",
        f"testpypi_project_url={metadata.testpypi_project_url}",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
def _venv_python(venv_root: Path) -> Path:
    if sys.platform == "win32":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _venv_rally(venv_root: Path) -> Path:
    if sys.platform == "win32":
        return venv_root / "Scripts" / "rally.exe"
    return venv_root / "bin" / "rally"


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed
    detail = (completed.stderr or completed.stdout).strip()
    if not detail:
        detail = f"Command exited with status {completed.returncode}."
    raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")


def _load_pyproject(pyproject_path: Path) -> dict[object, object]:
    try:
        return tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"`{pyproject_path}` is missing.") from exc
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(f"`{pyproject_path}` is not valid TOML.") from exc


def _dependency_name(requirement: str) -> str | None:
    match = _DEPENDENCY_NAME_RE.match(requirement)
    if match is None:
        return None
    return match.group("name")


def _require_string(raw: dict[object, object], *, key: str, table_name: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"`{table_name}.{key}` must be a non-empty string.")
    return value.strip()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read Rally package release metadata and run package smoke checks."
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    metadata = subparsers.add_parser(
        "metadata",
        help="Print package release metadata for repo-owned workflows.",
    )
    metadata.add_argument(
        "--repo-root",
        default=".",
        help="Repo root that contains `pyproject.toml`.",
    )
    metadata.add_argument(
        "--format",
        choices=("json", "github-output"),
        default="json",
        help="Output format.",
    )
    metadata.add_argument(
        "--output",
        help="Output file path for `github-output` format.",
    )

    smoke = subparsers.add_parser(
        "smoke",
        help="Install one built dist artifact in a fresh venv and run a small CLI proof.",
    )
    smoke.add_argument(
        "--repo-root",
        default=".",
        help="Repo root that contains `pyproject.toml`.",
    )
    smoke.add_argument(
        "--artifact-type",
        choices=("wheel", "sdist"),
        required=True,
        help="Dist artifact type to smoke test.",
    )
    smoke.add_argument(
        "--dist-dir",
        default="dist",
        help="Directory that contains built dist artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        if args.command == "metadata":
            metadata = load_package_release_metadata(repo_root)
            if args.format == "json":
                print(json.dumps(metadata.as_json(), sort_keys=True))
                return 0
            if not args.output:
                raise RuntimeError("`metadata --format github-output` requires `--output`.")
            write_github_outputs(metadata=metadata, output_path=Path(args.output).resolve())
            return 0

        smoke_test_distribution(
            repo_root=repo_root,
            artifact_type=args.artifact_type,
            dist_dir=(repo_root / args.dist_dir).resolve(),
        )
        return 0
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
