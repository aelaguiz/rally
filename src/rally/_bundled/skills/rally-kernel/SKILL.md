---
name: "rally-kernel"
description: "Shared Rally note skill for saving one short run note through Rally CLI."
---

# Rally Kernel

Use this skill when a later reader needs one short saved note on this run.

## Quick model

- Use Rally CLI for notes.

## When to use

- A later reader needs one short saved note on this run.
- The note also needs short `--field key=value` labels.

## Hard rules

- Write notes with `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`.
- Do not edit `home:issue.md` directly.
- Keep `--field` labels short and flat.
- Fail loud if `RALLY_CLI_BIN`, `RALLY_WORKSPACE_DIR`, or `RALLY_RUN_ID` is missing instead of guessing the active run or CLI path.
- If Rally already saves a review result to `home:issue.md`, do not add a second note unless the flow asks for one.

## First move

1. Confirm `RALLY_CLI_BIN`, `RALLY_RUN_ID`, and the active Rally workspace are present.
2. Decide whether a later reader needs one short saved note.

## Workflow

1. Use a note only when later readers would lose context that does not belong in the main file.
2. Write the note through Rally CLI when needed.
3. Keep the note short. Save context, exact commands, or constraints.
4. Keep `--field` labels simple. Put the human explanation in the note body, not in the field names.

## Preferred stdin form

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID" <<'EOF'
### Note
- Explain the context worth preserving for the next owner or later turn.
EOF
```

## Flat field form

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" issue note \
  --run-id "$RALLY_RUN_ID" \
  --field kind=producer_handoff \
  --field lane=producer \
  --field artifact=section_plan <<'EOF'
Kept the body short. Read the field labels first, then this note.
EOF
```

## Short forms

- Use `--text` when a one-line note is clearer than stdin.
- Use `--file` when the note already exists in a small prepared file.
- Read `references/note_examples.md` when you need the exact alternate note forms.

## Output expectations

- When no saved context is needed, do not write a note.
- When saved context is needed, write one note only.

## Reference map

- Use `references/note_examples.md` for the exact note command forms.
- No extra `references/` or `scripts/` should ship in v1 unless review or repeated execution failures prove they are needed.
