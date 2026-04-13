#!/usr/bin/env bash
set -euo pipefail

archive_root="$RALLY_WORKSPACE_DIR/runs/archive"
repo_dir="$RALLY_RUN_HOME/repos/demo_repo"
flow_code="$RALLY_FLOW_CODE"
issue_branch="issue/$(printf '%s' "$RALLY_RUN_ID" | tr '[:upper:]' '[:lower:]')"

find_source_repo() {
  python3 - "$archive_root" "$flow_code" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

import yaml

archive_root = Path(sys.argv[1])
flow_code = sys.argv[2]
best: tuple[int, Path] | None = None
if archive_root.is_dir():
    prefix = f"{flow_code}-"
    for run_dir in archive_root.iterdir():
        if not run_dir.is_dir() or not run_dir.name.startswith(prefix):
            continue
        try:
            sequence = int(run_dir.name.removeprefix(prefix))
        except ValueError:
            continue
        state_file = run_dir / "state.yaml"
        repo_dir = run_dir / "home" / "repos" / "demo_repo"
        if not state_file.is_file() or not (repo_dir / ".git").is_dir():
            continue
        state = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
        if state.get("status") != "done":
            continue
        if best is None or sequence > best[0]:
            best = (sequence, repo_dir)
if best is not None:
    print(best[1])
PY
}

configure_repo() {
  git -C "$repo_dir" config user.name "Rally Demo"
  git -C "$repo_dir" config user.email "rally-demo@example.com"
}

source_repo="$(find_source_repo)"
if [[ -n "$source_repo" ]]; then
  mkdir -p "$repo_dir"
  # Copy the whole repo, including `.git`, so later issues build on real history.
  cp -R "$source_repo"/. "$repo_dir"/
else
  mkdir -p "$repo_dir"
  git init "$repo_dir" >/dev/null
  git -C "$repo_dir" symbolic-ref HEAD refs/heads/main
  configure_repo
  git -C "$repo_dir" commit --allow-empty -m "chore: seed demo repo" >/dev/null
fi

configure_repo
git -C "$repo_dir" checkout -B "$issue_branch" >/dev/null
