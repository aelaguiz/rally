---
name: "rally-memory"
description: "Shared Rally memory skill for searching, using, saving, and refreshing cross-run memory through Rally CLI."
---

# Rally Memory

Use this skill when past work could help on this turn.
Rally loads this skill on every Rally-managed turn.

## Quick model

_unordered list_

- Read the issue and local repo state first.
- Memory is cross-run context, not a run-local note.
- Final JSON still controls the turn.

## When to use

_unordered list_

- Past work like this could help.
- You found a memory that clearly fits this role and issue.
- You had to fix your own work and learned a short lesson worth keeping.
- The memory index needs a refresh from the markdown source files.

## Hard rules

_unordered list_

- Use Rally CLI for memory actions.
- Use a memory only when it clearly fits this issue and role.
- Save only short reusable lessons.
- Do not use memory to replace run-local notes.
- Do not use memory to pass routing, `done`, `blocker`, or `sleep` truth.
- Do not edit memory files or QMD state directly.
- Fail loud if `RALLY_CLI_BIN`, `RALLY_RUN_ID`, or `RALLY_AGENT_SLUG` is missing.

## First move

_ordered list_

1. Read the issue and this role's local rules first.
2. Decide whether past work could help or whether you just learned a lesson worth keeping.
3. Choose `search`, `use`, `save`, or `refresh` through Rally CLI.

## Workflow

### Steps

_ordered list_

1. For tasks like this one, start with `search`.
2. Use `use` only after you pick one memory that clearly fits.
3. If you had to fix your own work, use `save` to keep the general lesson.
4. Use `refresh` when the index needs to rebuild from markdown files.
5. Keep the issue and local repo state primary. Memory is support context.

### Search Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory search --run-id "$RALLY_RUN_ID" --query "narrow the review before rewrite"
```

### Use Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory use --run-id "$RALLY_RUN_ID" mem_example_id
```

### Save Example

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

### Refresh Example

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" memory refresh --run-id "$RALLY_RUN_ID"
```

## Output expectations

_unordered list_

- Use `search` for discovery only.
- `use` and `save` should become visible Rally records.
- This skill never creates a second turn-ending path.
