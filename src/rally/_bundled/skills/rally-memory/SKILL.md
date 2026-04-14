---
name: "rally-memory"
description: "Shared Rally memory skill for searching, using, saving, and refreshing cross-run memory through Rally CLI. Use it for tasks like past work or when you had to fix your own work and learned a lesson worth keeping."
---

# Rally Memory

Use this skill on Rally-managed turns when cross-run memory could help.
Do not use it to replace the issue, notes, or final JSON.
Rally loads this skill on every Rally-managed turn. Flows do not need to list it by hand.

## When to use

_unordered list_

- Check memory for tasks like this one.
- You found a memory that clearly fits this role and issue.
- If you had to fix your own work, save the general lesson for later.
- The memory index needs a refresh from the markdown source files.

## When not to use

_unordered list_

- Do not search memory before you understand the current issue.
- Do not use memory to replace run-local notes.
- Do not use memory to pass routing, `done`, `blocker`, or `sleep` truth.
- Do not edit memory files or QMD state directly.

## Non-negotiables

_unordered list_

- Use Rally CLI for memory actions.
- Rally scopes memory by flow and agent.
- Memory is context only. Final JSON still controls the turn.
- Save only short reusable lessons.
- Fail loud if `RALLY_CLI_BIN`, `RALLY_RUN_ID`, or `RALLY_AGENT_SLUG` is missing.

## First move

_ordered list_

1. Read the issue and this role's local rules first.
2. Decide whether this task looks like past work or whether you just learned a lesson worth keeping.
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
