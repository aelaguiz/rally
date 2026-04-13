from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class GuardedGitRepoViolation:
    relative_path: Path
    reason: str


def check_guarded_git_repos(
    *,
    run_home: Path,
    guarded_git_repos: Sequence[Path],
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[GuardedGitRepoViolation, ...]:
    violations: list[GuardedGitRepoViolation] = []
    for relative_path in guarded_git_repos:
        repo_path = run_home / relative_path
        if not repo_path.exists():
            violations.append(
                GuardedGitRepoViolation(
                    relative_path=relative_path,
                    reason="repo is missing from the run home",
                )
            )
            continue
        if not repo_path.is_dir():
            violations.append(
                GuardedGitRepoViolation(
                    relative_path=relative_path,
                    reason="repo path is not a directory",
                )
            )
            continue
        try:
            completed = subprocess_run(
                ["git", "-C", str(repo_path), "status", "--short"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            violations.append(
                GuardedGitRepoViolation(
                    relative_path=relative_path,
                    reason=f"git status failed to start: {exc}",
                )
            )
            continue
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "git status failed"
            violations.append(
                GuardedGitRepoViolation(
                    relative_path=relative_path,
                    reason=detail,
                )
            )
            continue
        status_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not status_lines:
            continue
        preview = "; ".join(status_lines[:5])
        if len(status_lines) > 5:
            preview += "; ..."
        violations.append(
            GuardedGitRepoViolation(
                relative_path=relative_path,
                reason=f"repo is dirty: {preview}",
            )
        )
    return tuple(violations)


def render_guarded_git_repo_blocker(
    *,
    violations: Sequence[GuardedGitRepoViolation],
) -> str:
    if not violations:
        raise ValueError("Guarded git repo blocker requires at least one violation.")
    if len(violations) == 1:
        violation = violations[0]
        return f"Guarded repo `{violation.relative_path.as_posix()}` is not ready: {violation.reason}."
    parts = [
        f"`{violation.relative_path.as_posix()}`: {violation.reason}"
        for violation in violations
    ]
    return "Guarded repos are not ready: " + "; ".join(parts) + "."
