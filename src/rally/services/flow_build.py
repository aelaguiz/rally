from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from rally.errors import RallyConfigError

BuildSubprocessRunner = Callable[..., subprocess.CompletedProcess[str]]


def ensure_flow_agents_built(
    *,
    repo_root: Path,
    flow_name: str,
    subprocess_run: BuildSubprocessRunner = subprocess.run,
) -> None:
    config_path = repo_root / "pyproject.toml"
    if not config_path.is_file():
        raise RallyConfigError(f"Rally pyproject is missing: `{config_path}`.")

    doctrine_root = (repo_root.parent / "doctrine").resolve()
    if not doctrine_root.is_dir():
        raise RallyConfigError(f"Paired Doctrine repo is missing: `{doctrine_root}`.")
    if not (doctrine_root / "pyproject.toml").is_file():
        raise RallyConfigError(f"Doctrine pyproject is missing: `{doctrine_root / 'pyproject.toml'}`.")

    command = [
        "uv",
        "run",
        "--project",
        str(doctrine_root),
        "--locked",
        "python",
        "-m",
        "doctrine.emit_docs",
        "--pyproject",
        str(config_path),
        "--target",
        flow_name,
    ]
    try:
        completed = subprocess_run(
            command,
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RallyConfigError(f"Failed to start Doctrine rebuild for `{flow_name}`: {exc}.") from exc

    if completed.returncode == 0:
        return

    detail = completed.stderr.strip() or completed.stdout.strip() or "Doctrine emit_docs failed."
    raise RallyConfigError(f"Failed to rebuild flow `{flow_name}` with Doctrine emit_docs: {detail}")
