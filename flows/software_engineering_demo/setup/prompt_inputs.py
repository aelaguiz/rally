#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import yaml


def main() -> int:
    run_home = Path(os.environ["RALLY_RUN_HOME"]).resolve()
    issue_path = Path(os.environ["RALLY_ISSUE_PATH"]).resolve()
    flow_code = os.environ["RALLY_FLOW_CODE"]
    current_agent_key = os.environ["RALLY_AGENT_KEY"]
    demo_repo = run_home / "repos" / "demo_repo"
    issue_text = issue_path.read_text(encoding="utf-8") if issue_path.is_file() else ""

    payload = {
        "Demo Repo Facts": repo_status(demo_repo),
        "Carry Forward": carry_forward_source(
            repo=demo_repo,
            archive_root=Path(os.environ["RALLY_WORKSPACE_DIR"]).resolve() / "runs" / "archive",
            flow_code=flow_code,
        ),
        "Review Facts": review_facts(
            issue_text=issue_text,
            current_agent_key=current_agent_key,
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def repo_status(repo: Path) -> dict[str, object]:
    if not repo.is_dir():
        return {
            "repo_path": "home:repos/demo_repo",
            "exists": False,
            "branch": None,
            "head_commit": None,
            "clean": False,
            "status_lines": ["repo directory is missing"],
        }
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head = git(repo, "rev-parse", "HEAD")
    status_lines = git(repo, "status", "--short").splitlines()
    history_lines = git(repo, "log", "--max-count=3", "--pretty=format:%h %s").splitlines()
    return {
        "repo_path": "home:repos/demo_repo",
        "exists": True,
        "branch": branch,
        "head_commit": head,
        "clean": len(status_lines) == 0,
        "status_lines": status_lines,
        "recent_commits": history_lines,
    }


def carry_forward_source(*, repo: Path, archive_root: Path, flow_code: str) -> dict[str, object]:
    if not repo.is_dir() or not (repo / ".git").is_dir():
        return {"mode": "missing_repo", "source_run_id": None, "source_head_commit": None}
    current_head = git(repo, "rev-parse", "HEAD")
    best: tuple[int, str, str] | None = None
    prefix = f"{flow_code}-"
    if archive_root.is_dir():
        for run_dir in archive_root.iterdir():
            if not run_dir.is_dir() or not run_dir.name.startswith(prefix):
                continue
            try:
                sequence = int(run_dir.name.removeprefix(prefix))
            except ValueError:
                continue
            state_file = run_dir / "state.yaml"
            archived_repo = run_dir / "home" / "repos" / "demo_repo"
            if not state_file.is_file() or not (archived_repo / ".git").is_dir():
                continue
            state = yaml.safe_load(state_file.read_text(encoding="utf-8")) or {}
            if state.get("status") != "done":
                continue
            archived_head = git(archived_repo, "rev-parse", "HEAD")
            if archived_head != current_head and not is_ancestor(repo, archived_head, current_head):
                continue
            if best is None or sequence > best[0]:
                best = (sequence, run_dir.name, archived_head)
    if best is None:
        return {"mode": "bootstrap", "source_run_id": None, "source_head_commit": None}
    return {
        "mode": "carry_forward",
        "source_run_id": best[1],
        "source_head_commit": best[2],
    }


def review_facts(*, issue_text: str, current_agent_key: str) -> dict[str, object]:
    last_turn_agent = normalize_agent_name(latest_turn_agent(issue_text))
    selected_mode = {
        "architect": "architect_review",
        "developer": "developer_review",
        "qa_docs_tester": "qa_review",
    }.get(last_turn_agent, "architect_review")
    basis_missing = current_agent_key == "02_critic" and last_turn_agent not in {
        "architect",
        "developer",
        "qa_docs_tester",
    }
    latest_review = latest_critic_review(issue_text)
    return {
        "selected_mode": selected_mode,
        "review_basis_missing": basis_missing,
        "last_turn_agent": last_turn_agent,
        "latest_critic_verdict": latest_review["verdict"],
        "latest_critic_next_owner": latest_review["next_owner"],
        "latest_critic_findings_first": latest_review["findings_first"],
    }


def normalize_agent_name(agent_name: str | None) -> str | None:
    if agent_name is None:
        return None
    return re.sub(r"^\d+_", "", agent_name)


def latest_turn_agent(issue_text: str) -> str | None:
    for block in reversed(rally_blocks(issue_text, title="Rally Turn Result")):
        match = re.search(r"^- Agent: `([^`]+)`$", block, flags=re.MULTILINE)
        if match is not None:
            return match.group(1)
    return None


def latest_critic_review(issue_text: str) -> dict[str, object]:
    for block in reversed(rally_blocks(issue_text, title="Rally Note")):
        source_match = re.search(r"^- Source: `([^`]+)`$", block, flags=re.MULTILINE)
        if source_match is None or source_match.group(1) != "rally runtime review":
            continue
        verdict_match = re.search(r"^- Verdict: `([^`]+)`$", block, flags=re.MULTILINE)
        next_owner_match = re.search(r"^- Next Owner: `([^`]+)`$", block, flags=re.MULTILINE)
        findings_match = re.search(
            r"^### Findings First\n(?P<body>.*?)(?=^### |\Z)",
            block,
            flags=re.MULTILINE | re.DOTALL,
        )
        return {
            "verdict": verdict_match.group(1) if verdict_match is not None else None,
            "next_owner": next_owner_match.group(1) if next_owner_match is not None else None,
            "findings_first": findings_match.group("body").strip() if findings_match is not None else None,
        }
    return {"verdict": None, "next_owner": None, "findings_first": None}


def rally_blocks(issue_text: str, *, title: str) -> list[str]:
    pattern = re.compile(rf"^## {re.escape(title)}\n.*?(?=^## |\Z)", flags=re.MULTILINE | re.DOTALL)
    return [match.group(0) for match in pattern.finditer(issue_text)]


def is_ancestor(repo: Path, older: str, newer: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


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
