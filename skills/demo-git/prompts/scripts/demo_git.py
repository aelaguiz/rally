#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Read stable demo repo git facts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Print branch, head, and dirty status as JSON.")
    status_parser.add_argument("repo", type=Path)

    log_parser = subparsers.add_parser("log", help="Print the recent commit log as JSON.")
    log_parser.add_argument("repo", type=Path)
    log_parser.add_argument("--count", type=int, default=5)

    args = parser.parse_args()
    if args.command == "status":
        payload = repo_status(args.repo)
    else:
        payload = repo_log(args.repo, count=args.count)
    json.dump(payload, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def repo_status(repo: Path) -> dict[str, object]:
    ensure_git_repo(repo)
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head = git(repo, "rev-parse", "HEAD")
    status_lines = git(repo, "status", "--short").splitlines()
    return {
        "repo": repo.as_posix(),
        "branch": branch,
        "head_commit": head,
        "clean": len(status_lines) == 0,
        "status_lines": status_lines,
    }


def repo_log(repo: Path, *, count: int) -> dict[str, object]:
    ensure_git_repo(repo)
    history = git(
        repo,
        "log",
        f"--max-count={count}",
        "--pretty=format:%H%x09%s",
    ).splitlines()
    return {
        "repo": repo.as_posix(),
        "commits": [
            {"commit": line.split("\t", 1)[0], "subject": line.split("\t", 1)[1]}
            for line in history
            if "\t" in line
        ],
    }


def ensure_git_repo(repo: Path) -> None:
    if not repo.is_dir():
        raise SystemExit(f"Repo directory does not exist: {repo}")
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "not a git repo"
        raise SystemExit(f"Repo is not a git work tree: {detail}")


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise SystemExit(detail)
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
