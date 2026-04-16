from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
from typing import TextIO

from rally.domain.flow import FlowDefinition
from rally.domain.run import ResumeRequest, RunRecord, RunRequest
from rally.errors import RallyError, RallyUsageError
from rally.memory.service import refresh_memory, save_memory, search_memory, use_memory
from rally.services.issue_ledger import append_issue_note, render_issue_current_view
from rally.services.run_status import show_status
from rally.services.runner import resume_run, run_flow
from rally.services.workspace import resolve_workspace
from rally.terminal.display import AgentDisplayIdentity, DisplayContext, build_terminal_display


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RallyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rally",
        description=(
            "Run filesystem-first Rally workflows from the repo root.\n\n"
            "Use `rally run <flow>` to start work, `rally status` to see what is active, "
            "and `rally resume <run-id>` to keep moving."
        ),
        epilog=_examples(
            "Examples",
            (
                "rally run demo",
                "rally run demo --from-file ./issue.md",
                "rally status",
                "rally resume DMO-1 --step",
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Start a run for one flow.",
        description=(
            "Create a Rally run shell for one flow and start it when `home/issue.md` is ready.\n\n"
            "Use this when you want to begin new work from a flow definition under `flows/`."
        ),
        epilog=_examples(
            "Examples",
            (
                "rally run demo",
                "rally run demo --step",
                "rally run demo --new",
                "rally run demo --from-file ./issue.md",
                "rally run demo --new --from-file ./issue.md",
            ),
        )
        + "\n\nNext: Rally will either start the run or tell you to fill in `home/issue.md` and use `rally resume <run-id>`.",
        formatter_class=_HelpFormatter,
    )
    run_parser.add_argument("flow_name", help="Flow directory name under flows/.")
    run_parser.add_argument(
        "--new",
        action="store_true",
        help="Archive the current active run for this flow, then start a fresh run.",
    )
    run_parser.add_argument(
        "--step",
        action="store_true",
        help="Run one agent turn, then pause so you can resume later.",
    )
    run_parser.add_argument(
        "--from-file",
        help="Copy the starting `home/issue.md` text from this file before the run starts.",
    )
    run_parser.set_defaults(func=_run_command)

    resume_parser = subparsers.add_parser(
        "resume",
        help="Continue a stopped run.",
        description=(
            "Resume one Rally run by id.\n\n"
            "Use this after Rally stops for issue text, pauses after `--step`, or needs an operator decision."
        ),
        epilog=_examples(
            "Examples",
            (
                "rally resume DMO-1",
                "rally resume DMO-1 --step",
                "rally resume DMO-1 --edit",
                "rally resume DMO-1 --restart",
            ),
        )
        + "\n\nNext: Use `rally status <run-id>` first if you are not sure what state the run is in.",
        formatter_class=_HelpFormatter,
    )
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
    resume_parser.add_argument(
        "--step",
        action="store_true",
        help="Run one agent turn, then pause so you can resume later.",
    )
    resume_parser.set_defaults(func=_resume_command)

    status_parser = subparsers.add_parser(
        "status",
        help="Show active runs or inspect one run.",
        description=(
            "Inspect Rally run state from repo files.\n\n"
            "Use this to see what is active, which agent is current, and what command should usually come next."
        ),
        epilog=_examples(
            "Examples",
            (
                "rally status",
                "rally status DMO-1",
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    status_parser.add_argument(
        "run_id",
        nargs="?",
        help="Run identifier to inspect. Leave this empty to list active runs.",
    )
    status_parser.set_defaults(func=_status_command)

    issue_parser = subparsers.add_parser(
        "issue",
        help="Work with a Rally issue log.",
        description=(
            "Read or update one run's `home/issue.md` ledger.\n\n"
            "Use this when you need the bounded current view or need to leave durable context in the run ledger."
        ),
        formatter_class=_HelpFormatter,
    )
    issue_subparsers = issue_parser.add_subparsers(dest="issue_command", required=True)

    issue_note_parser = issue_subparsers.add_parser(
        "note",
        help="Append a note to a Rally issue log.",
        description=(
            "Append one note block to a run's `home/issue.md`.\n\n"
            "Use `--text`, `--file`, or stdin for the note body, and `--field key=value` for flat note labels."
        ),
        epilog=_examples(
            "Examples",
            (
                'rally issue note --run-id DMO-1 --text "Need review from QA."',
                "rally issue note --run-id DMO-1 --file ./note.md",
                'printf "### Note\\n- operator context\\n" | rally issue note --run-id DMO-1',
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    issue_note_parser.add_argument("--run-id", required=True, help="Run identifier to update.")
    issue_note_parser.add_argument(
        "--field",
        action="append",
        metavar="key=value",
        help="Add one flat structured note field. Repeat for more fields.",
    )
    note_source = issue_note_parser.add_mutually_exclusive_group()
    note_source.add_argument("--text", help="Inline note text to append.")
    note_source.add_argument("--file", help="Read note markdown from this file.")
    issue_note_parser.set_defaults(func=_issue_note_command)

    issue_current_parser = issue_subparsers.add_parser(
        "current",
        help="Show the bounded current issue view for one run.",
        description=(
            "Print the opening issue plus the newest shared Rally state for one run.\n\n"
            "Use this when you want the latest shared truth without rereading the full append-only ledger."
        ),
        epilog=_examples(
            "Examples",
            (
                "rally issue current --run-id DMO-1",
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    issue_current_parser.add_argument("--run-id", required=True, help="Run identifier to read.")
    issue_current_parser.set_defaults(func=_issue_current_command)

    memory_parser = subparsers.add_parser(
        "memory",
        help="Work with Rally memory.",
        description=(
            "Read and write repo-local Rally memory.\n\n"
            "Use this when a run or agent needs durable memory beyond the issue ledger."
        ),
        formatter_class=_HelpFormatter,
    )
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)

    memory_search_parser = memory_subparsers.add_parser(
        "search",
        help="Search scoped Rally memory.",
        description="Search memory entries for one run scope.",
        epilog=_examples(
            "Examples",
            (
                'rally memory search --run-id DMO-1 --query "pagination bug"',
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    memory_search_parser.add_argument("--run-id", required=True, help="Run identifier to use for memory scope.")
    memory_search_parser.add_argument("--agent-slug", help="Override the scoped agent slug.")
    memory_search_parser.add_argument("--query", required=True, help="Search text.")
    memory_search_parser.add_argument("--limit", type=int, default=5, help="Maximum number of hits to print.")
    memory_search_parser.set_defaults(func=_memory_search_command)

    memory_use_parser = memory_subparsers.add_parser(
        "use",
        help="Read one scoped Rally memory.",
        description="Read one saved memory entry for one run scope.",
        epilog=_examples(
            "Examples",
            (
                "rally memory use --run-id DMO-1 memory_0001",
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    memory_use_parser.add_argument("--run-id", required=True, help="Run identifier to use for memory scope.")
    memory_use_parser.add_argument("--agent-slug", help="Override the scoped agent slug.")
    memory_use_parser.add_argument("memory_id", help="Memory id to read.")
    memory_use_parser.set_defaults(func=_memory_use_command)

    memory_save_parser = memory_subparsers.add_parser(
        "save",
        help="Save one scoped Rally memory.",
        description="Save one memory entry for one run scope.",
        epilog=_examples(
            "Examples",
            (
                'rally memory save --run-id DMO-1 --text "# Lesson\\nAsk for one clear next step."',
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    memory_save_parser.add_argument("--run-id", required=True, help="Run identifier to use for memory scope.")
    memory_save_parser.add_argument("--agent-slug", help="Override the scoped agent slug.")
    memory_source = memory_save_parser.add_mutually_exclusive_group()
    memory_source.add_argument("--text", help="Inline memory markdown to save.")
    memory_source.add_argument("--file", help="Read memory markdown from this file.")
    memory_save_parser.set_defaults(func=_memory_save_command)

    memory_refresh_parser = memory_subparsers.add_parser(
        "refresh",
        help="Refresh the scoped Rally memory index.",
        description="Rebuild the memory index for one run scope.",
        epilog=_examples(
            "Examples",
            (
                "rally memory refresh --run-id DMO-1",
            ),
        ),
        formatter_class=_HelpFormatter,
    )
    memory_refresh_parser.add_argument("--run-id", required=True, help="Run identifier to use for memory scope.")
    memory_refresh_parser.add_argument("--agent-slug", help="Override the scoped agent slug.")
    memory_refresh_parser.set_defaults(func=_memory_refresh_command)
    return parser


def _run_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    issue_seed_path = None
    if args.from_file is not None:
        issue_seed_path = Path(args.from_file).expanduser().resolve()
    result = run_flow(
        workspace=workspace,
        request=RunRequest(
            flow_name=args.flow_name,
            start_new=args.new,
            step=args.step,
            issue_seed_path=issue_seed_path,
        ),
        display_factory=_build_display_factory(sys.stdout),
    )
    print(result.message)
    return 0


def _resume_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    result = resume_run(
        workspace=workspace,
        request=ResumeRequest(
            run_id=args.run_id,
            edit_issue=args.edit,
            restart=args.restart,
            step=args.step,
        ),
        display_factory=_build_display_factory(sys.stdout),
    )
    print(result.message)
    return 0


def _status_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    result = show_status(
        repo_root=workspace.workspace_root,
        run_id=args.run_id,
    )
    print(result.message)
    return 0


def _issue_note_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    note_text = _read_note_text(args)
    note_fields = _parse_note_fields(args.field)
    result = append_issue_note(
        repo_root=workspace.workspace_root,
        run_id=args.run_id,
        note_markdown=note_text,
        note_fields=note_fields,
        turn_index=_turn_index_from_env(),
    )
    print(
        f"Appended note for run `{result.run_id}` to `{result.issue_file}`. "
        f"Saved snapshot `{result.snapshot_file}`."
    )
    return 0


def _issue_current_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    print(
        render_issue_current_view(
            repo_root=workspace.workspace_root,
            run_id=args.run_id,
        ).rstrip()
    )
    return 0


def _memory_search_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    hits = search_memory(
        repo_root=workspace.workspace_root,
        run_id=args.run_id,
        query=args.query,
        limit=args.limit,
        agent_slug=args.agent_slug,
        turn_index=_turn_index_from_env(),
    )
    if not hits:
        print("No scoped memories found.")
        return 0
    for index, hit in enumerate(hits, start=1):
        print(f"{index}. {hit.memory_id} ({hit.score:.2f})")
        print(f"   {hit.title}")
        print(f"   {hit.snippet}")
    return 0


def _memory_use_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    entry = use_memory(
        repo_root=workspace.workspace_root,
        run_id=args.run_id,
        memory_id=args.memory_id,
        agent_slug=args.agent_slug,
        turn_index=_turn_index_from_env(),
    )
    print(f"Memory `{entry.memory_id}` from `{entry.path}`")
    print()
    print(entry.body_markdown().rstrip())
    return 0


def _memory_save_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    memory_text = _read_memory_text(args)
    save_result, refresh_result = save_memory(
        repo_root=workspace.workspace_root,
        run_id=args.run_id,
        memory_markdown=memory_text,
        agent_slug=args.agent_slug,
        turn_index=_turn_index_from_env(),
    )
    print(
        f"{save_result.outcome.title()} memory `{save_result.entry.memory_id}` at `{save_result.entry.path}`. "
        f"Indexed {refresh_result.indexed} new, {refresh_result.updated} updated, "
        f"{refresh_result.unchanged} unchanged, {refresh_result.removed} removed."
    )
    return 0


def _memory_refresh_command(args: argparse.Namespace) -> int:
    workspace = resolve_workspace()
    result = refresh_memory(
        repo_root=workspace.workspace_root,
        run_id=args.run_id,
        agent_slug=args.agent_slug,
        turn_index=_turn_index_from_env(),
    )
    print(
        f"Refreshed scoped memory index. Indexed {result.indexed} new, {result.updated} updated, "
        f"{result.unchanged} unchanged, {result.removed} removed."
    )
    return 0


def _resolve_user_file(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _read_note_text(args: argparse.Namespace) -> str:
    return _read_command_text(args=args, empty_message="Note body is empty.", label="Note")


def _read_memory_text(args: argparse.Namespace) -> str:
    return _read_command_text(args=args, empty_message="Memory body is empty.", label="Memory")


def _read_command_text(*, args: argparse.Namespace, empty_message: str, label: str) -> str:
    if args.text is not None:
        note_text = args.text
    elif args.file is not None:
        note_file = _resolve_user_file(Path(args.file))
        if not note_file.is_file():
            raise RallyUsageError(f"{label} file does not exist: `{note_file}`.")
        note_text = note_file.read_text(encoding="utf-8")
    else:
        note_text = sys.stdin.read()

    if not note_text.strip():
        raise RallyUsageError(empty_message)
    return note_text


def _examples(title: str, lines: tuple[str, ...]) -> str:
    body = "\n".join(f"  {line}" for line in lines)
    return f"{title}:\n{body}"


def _parse_note_fields(raw_fields: list[str] | None) -> tuple[tuple[str, str], ...]:
    if not raw_fields:
        return ()

    parsed_fields: list[tuple[str, str]] = []
    for raw_field in raw_fields:
        key, separator, value = raw_field.partition("=")
        if not separator:
            raise RallyUsageError("Note fields must use `key=value`.")
        parsed_fields.append((key, value))
    return tuple(parsed_fields)


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
