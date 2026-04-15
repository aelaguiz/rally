---
name: "rally-memory"
description: "Shared Rally memory skill for searching, using, saving, and refreshing cross-run memory through Rally CLI."
---

# Rally Memory

Use this skill when past work could help on this turn.

## Quick model

- Memory keeps cross-run lessons.

## When to use

- Past work like this could help.
- You found a memory that clearly fits this role and issue.
- You had to fix your own work and learned a short lesson worth keeping.
- The memory index needs a refresh from the markdown source files.

## Hard rules

- Use Rally CLI for memory actions.
- Use a memory only when it clearly fits this issue and role.
- Save only short reusable lessons.
- Do not edit memory files or QMD state directly.
- Fail loud if `RALLY_CLI_BIN`, `RALLY_RUN_ID`, or `RALLY_AGENT_SLUG` is missing.

## First move

1. Decide whether past work could help or whether you just learned a lesson worth keeping.
2. Choose `search`, `use`, `save`, or `refresh` through Rally CLI.

## Workflow

- For tasks like this one, start with `search`.
- Use `use` only after you pick one memory that clearly fits.
- If you had to fix your own work, use `save` to keep the general lesson.
- Use `refresh` when the index needs to rebuild from markdown files.

## Search Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory search --run-id "$RALLY_RUN_ID" --query "narrow the review before rewrite"
```

## Use Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory use --run-id "$RALLY_RUN_ID" mem_example_id
```

## Save Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory save --run-id "$RALLY_RUN_ID" <<'EOF'
# Lesson
Ask for one concrete revision target before asking for a full rewrite.

# When This Matters
Use this after a weak draft or a vague critique.

# What To Do
Write the one concrete target, then hand off with normal final JSON.
EOF
```

## Refresh Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory refresh --run-id "$RALLY_RUN_ID"
```

## Output expectations

- Use `search` for discovery only.
- `use` and `save` should become visible Rally records.
