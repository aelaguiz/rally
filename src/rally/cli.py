from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rally.errors import RallyError, RallyUsageError
from rally.services.issue_ledger import append_issue_note
from rally.services.flow_loader import load_flow_definition


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

    run_parser = subparsers.add_parser("run", help="Preflight a Rally flow and prepare for execution.")
    run_parser.add_argument("flow_name", help="Flow directory name under flows/.")
    run_parser.add_argument(
        "--brief-file",
        required=True,
        help="Path to the authored run brief for this flow.",
    )
    run_parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Stop after validating flow and build inputs.",
    )
    run_parser.set_defaults(func=_run_command)

    resume_parser = subparsers.add_parser("resume", help="Resume an existing Rally run.")
    resume_parser.add_argument("run_id", help="Run identifier to resume.")
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
    brief_file = _resolve_user_file(Path(args.brief_file))
    if not brief_file.is_file():
        raise RallyUsageError(f"Brief file does not exist: `{brief_file}`.")

    flow = load_flow_definition(repo_root=repo_root, flow_name=args.flow_name)

    if args.preflight_only:
        print(
            "Preflight passed for flow "
            f"`{flow.name}` with {len(flow.agents)} agents, "
            f"start agent `{flow.start_agent_key}`, "
            f"and adapter `{flow.adapter.name}`."
        )
        return 0

    raise RallyUsageError(
        "Run execution is not implemented yet. "
        "Use `rally run <flow> --brief-file <path> --preflight-only` for the Phase 1 proof surface."
    )


def _resume_command(args: argparse.Namespace) -> int:
    raise RallyUsageError(
        "Resume is not implemented yet. "
        f"Run-store and session recovery surfaces are still pending for run `{args.run_id}`."
    )


def _issue_note_command(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    note_text = _read_note_text(args)
    result = append_issue_note(repo_root=repo_root, run_id=args.run_id, note_markdown=note_text)
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
