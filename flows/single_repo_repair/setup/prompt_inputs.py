#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> None:
    run_home = Path(os.environ["RALLY_RUN_HOME"])
    agent_slug = os.environ["RALLY_AGENT_SLUG"]

    payload: dict[str, object] = {}
    if agent_slug == "scope_lead":
        payload["WorkBrief"] = _opening_brief_from_issue(
            (run_home / "issue.md").read_text(encoding="utf-8")
        )
    if agent_slug == "acceptance_critic":
        payload["AcceptanceFacts"] = _acceptance_facts(run_home=run_home)

    print(json.dumps(payload))


def _opening_brief_from_issue(issue_text: str) -> str:
    brief_lines: list[str] = []
    for line in issue_text.splitlines():
        if line.startswith("## Rally "):
            break
        brief_lines.append(line)
    return "\n".join(brief_lines).rstrip()


def _acceptance_facts(*, run_home: Path) -> dict[str, bool]:
    verification_file = run_home / "artifacts" / "verification.md"
    verification_text = verification_file.read_text(encoding="utf-8") if verification_file.is_file() else ""
    lowered = verification_text.lower()

    has_pytest = "pytest" in lowered
    has_pass_signal = any(
        token in lowered
        for token in (
            "passed",
            "0 failed",
            "exit code 0",
            "all checks passed",
        )
    )
    issue_still_reproducible = any(
        token in lowered
        for token in (
            "still reproduces",
            "still fails",
            "issue still happens",
            "bug still happens",
        )
    )
    out_of_scope_change = "out of scope" in lowered and "not out of scope" not in lowered

    return {
        "issue_still_reproducible": issue_still_reproducible,
        "out_of_scope_change": out_of_scope_change,
        "missing_regression_proof": not (has_pytest and has_pass_signal),
    }


if __name__ == "__main__":
    main()
