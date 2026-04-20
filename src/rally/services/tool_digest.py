"""Short, secret-scrubbed fingerprints for tool-call inputs.

`make_input_digest` turns a tool-call input into a ≤120-char label suitable for
storing on a `TOOL` / `CMD` event and surfacing in receipts (hot-command rows,
retry detection). It picks the most informative field per tool, strips the
standard Codex `/bin/zsh -lc "..."` wrapper, redacts obvious secret-bearing
tokens, and truncates. Pure function, no I/O.
"""
from __future__ import annotations

import re
from typing import Mapping

DEFAULT_MAX_LEN = 120

_ZSH_WRAPPER = re.compile(
    r"""^/bin/zsh\s+-lc\s+          # the wrapper prefix
        (?P<q>['"])                 # opening quote
        (?P<body>.*)                # everything inside
        (?P=q)\s*$                  # matching closing quote
    """,
    re.VERBOSE | re.DOTALL,
)

_SCRUB_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(--(?:password|token|secret|api[-_]?key))=\S+"), r"\1=<scrub>"),
    (re.compile(r"(?i)(-H\s+['\"]?Authorization:\s*)[^'\"\n]+"), r"\1<scrub>"),
    (re.compile(r"(?i)\b(API_KEY|GH_TOKEN|GITHUB_TOKEN|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY)=\S+"), r"\1=<scrub>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<scrub-aws-key>"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "<scrub-slack>"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "<scrub-openai>"),
]


def _strip_zsh_wrapper(text: str) -> str:
    match = _ZSH_WRAPPER.match(text.strip())
    if not match:
        return text
    return match.group("body").strip()


def scrub_secrets(text: str) -> str:
    out = text
    for pattern, replacement in _SCRUB_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def _truncate(text: str, max_len: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1].rstrip() + "…"


def make_input_digest(
    tool_name: str,
    tool_input: object,
    *,
    max_len: int = DEFAULT_MAX_LEN,
) -> str | None:
    """Return a short, scrubbed label for a tool-call input, or None.

    `tool_input` may be a dict (Claude Code-style `{"command": "...", ...}`),
    a raw string (Codex's `item.command`), or None. Returns None when nothing
    usable can be extracted, so callers can omit the field on the event.
    """
    raw = _extract_raw(tool_name, tool_input)
    if raw is None:
        return None
    stripped = _strip_zsh_wrapper(raw)
    scrubbed = scrub_secrets(stripped)
    digest = _truncate(scrubbed, max_len)
    return digest or None


def _extract_raw(tool_name: str, tool_input: object) -> str | None:
    if isinstance(tool_input, str):
        return tool_input or None
    if not isinstance(tool_input, Mapping):
        return None
    name = (tool_name or "").lower()
    if name in {"bash", "shell"}:
        return _str(tool_input.get("command"))
    if name in {"read", "edit", "write", "notebookedit"}:
        return _str(tool_input.get("file_path")) or _str(tool_input.get("path"))
    if name in {"glob", "grep", "toolsearch", "websearch"}:
        return _str(tool_input.get("pattern")) or _str(tool_input.get("query"))
    if name in {"webfetch"}:
        return _str(tool_input.get("url"))
    if name in {"skill"}:
        skill = _str(tool_input.get("skill_name")) or _str(tool_input.get("skill"))
        args = _str(tool_input.get("args"))
        if skill and args:
            return f"{skill} {args}"
        return skill
    if name in {"task", "agent", "explore"}:
        desc = _str(tool_input.get("description")) or _str(tool_input.get("prompt"))
        sub = _str(tool_input.get("subagent_type"))
        if sub and desc:
            return f"{sub}: {desc}"
        return desc
    for key in ("command", "file_path", "path", "pattern", "query", "url", "description"):
        value = _str(tool_input.get(key))
        if value:
            return value
    return None


def _str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


_SUB_KIND_BY_TOOL: dict[str, str] = {
    "bash": "bash",
    "shell": "bash",
    "read": "read",
    "edit": "edit",
    "write": "edit",
    "notebookedit": "edit",
    "glob": "search",
    "grep": "search",
    "toolsearch": "search",
    "websearch": "search",
    "webfetch": "fetch",
    "skill": "skill",
    "task": "sub_agent",
    "agent": "sub_agent",
    "explore": "sub_agent",
    "plan": "sub_agent",
}


def classify_sub_kind(tool_name: str) -> str:
    """Classify a tool into a coarse `sub_kind` for receipt grouping."""
    return _SUB_KIND_BY_TOOL.get((tool_name or "").lower(), "other")
