from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TextIO

from rally.domain.flow import FlowDefinition
from rally.domain.run import ResumeRequest, RunRecord, RunRequest
from rally.errors import RallyError, RallyUsageError
from rally.services.issue_ledger import append_issue_note
from rally.services.runner import resume_run, run_flow
from rally.terminal.display import AgentDisplayIdentity, DisplayContext, build_terminal_display


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RallyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rally")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Create a Rally run shell and start when the issue is ready.",
    )
    run_parser.add_argument("flow_name", help="Flow directory name under flows/.")
    run_parser.add_argument(
        "--new",
        action="store_true",
        help="Archive the current active run for this flow, then start a fresh run.",
    )
    run_parser.set_defaults(func=_run_command)

    resume_parser = subparsers.add_parser("resume", help="Resume an existing Rally run.")
    resume_parser.add_argument("run_id", help="Run identifier to resume.")
    resume_action = resume_parser.add_mutually_exclusive_group()
    resume_action.add_argument(
        "--edit",
        action="store_true",
        help="Open `home/issue.md` in your editor before Rally resumes the run.",
    )
    resume_action.add_argument(
        "--restart",
        action="store_true",
        help="Archive this run, restore the original issue, and start a fresh run.",
    )
    resume_parser.set_defaults(func=_resume_command)

    issue_parser = subparsers.add_parser("issue", help="Work with a Rally issue log.")
    issue_subparsers = issue_parser.add_subparsers(dest="issue_command", required=True)

    issue_note_parser = issue_subparsers.add_parser("note", help="Append a note to a Rally issue log.")
    issue_note_parser.add_argument("--run-id", required=True, help="Run identifier to update.")
    note_source = issue_note_parser.add_mutually_exclusive_group()
    note_source.add_argument("--text", help="Inline note text to append.")
    note_source.add_argument("--file", help="Read note markdown from this file.")
    issue_note_parser.set_defaults(func=_issue_note_command)
    return parser


def _run_command(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    result = run_flow(
        repo_root=repo_root,
        request=RunRequest(flow_name=args.flow_name, start_new=args.new),
        display_factory=_build_display_factory(sys.stdout),
    )
    print(result.message)
    return 0


def _resume_command(args: argparse.Namespace) -> int:
    result = resume_run(
        repo_root=_repo_root(),
        request=ResumeRequest(
            run_id=args.run_id,
            edit_issue=args.edit,
            restart=args.restart,
        ),
        display_factory=_build_display_factory(sys.stdout),
    )
    print(result.message)
    return 0


def _issue_note_command(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    note_text = _read_note_text(args)
    result = append_issue_note(
        repo_root=repo_root,
        run_id=args.run_id,
        note_markdown=note_text,
        turn_index=_turn_index_from_env(),
    )
    print(
        f"Appended note for run `{result.run_id}` to `{result.issue_file}`. "
        f"Saved snapshot `{result.snapshot_file}`."
    )
    return 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_user_file(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _read_note_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        note_text = args.text
    elif args.file is not None:
        note_file = _resolve_user_file(Path(args.file))
        if not note_file.is_file():
            raise RallyUsageError(f"Note file does not exist: `{note_file}`.")
        note_text = note_file.read_text(encoding="utf-8")
    else:
        note_text = sys.stdin.read()

    if not note_text.strip():
        raise RallyUsageError("Note body is empty.")
    return note_text


def _turn_index_from_env() -> int | None:
    raw_value = os.environ.get("RALLY_TURN_NUMBER")
    if raw_value is None:
        return None
    if not raw_value.strip():
        raise RallyUsageError("`RALLY_TURN_NUMBER` must not be empty when set.")
    try:
        turn_index = int(raw_value)
    except ValueError as exc:
        raise RallyUsageError("`RALLY_TURN_NUMBER` must be an integer when set.") from exc
    if turn_index < 1:
        raise RallyUsageError("`RALLY_TURN_NUMBER` must be 1 or greater when set.")
    return turn_index


def _build_display_factory(stream: TextIO):
    def _factory(run_record: RunRecord, flow: FlowDefinition):
        return build_terminal_display(
            stream=stream,
            context=DisplayContext(
                run_id=run_record.id,
                flow_name=flow.name,
                flow_code=flow.code,
                adapter_name=flow.adapter.name,
                model_name=_optional_adapter_string(flow.adapter.args.get("model")),
                reasoning_effort=_optional_adapter_string(flow.adapter.args.get("reasoning_effort")),
                start_agent_key=flow.start_agent_key,
                agent_count=len(flow.agents),
                agent_identities=tuple(
                    AgentDisplayIdentity(key=agent.key, slug=agent.slug)
                    for agent in flow.agents.values()
                ),
            ),
        )

    return _factory


def _optional_adapter_string(raw_value: object) -> str | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    return raw_value.strip()
