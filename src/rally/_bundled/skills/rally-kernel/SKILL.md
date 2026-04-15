---
name: "rally-kernel"
description: "Shared Rally turn skill for saving one short run note through Rally CLI and ending the turn with the declared final JSON."
---

# Rally Kernel

Use this skill when you need one saved run note or the final JSON for this turn.
Rally loads this skill on every Rally-managed turn.

## Quick model

_unordered list_

- Notes save run-local context only.
- Final JSON decides `handoff`, `done`, `blocker`, and `sleep`.
- Use Rally CLI for notes and the adapter return path for the final JSON.

## When to use

_unordered list_

- A later reader needs one short saved note on this run.
- The note also needs short `--field key=value` labels.
- The turn needs the declared final JSON.
- You need to keep saved context separate from turn control.

## Hard rules

_unordered list_

- Write notes with `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`.
- Do not edit `home:issue.md` directly.
- Keep notes run-local. Use `rally-memory` for cross-run lessons.
- Keep `--field` labels short and flat.
- Keep `next_owner`, `done`, `blocker`, and `sleep` in final JSON, not in notes.
- Fail loud if `RALLY_CLI_BIN`, `RALLY_WORKSPACE_DIR`, or `RALLY_RUN_ID` is missing instead of guessing the active run or CLI path.
- If Rally already saves a review result to `home:issue.md`, do not add a second note unless the flow asks for one.

## First move

_ordered list_

1. Confirm `RALLY_CLI_BIN`, `RALLY_RUN_ID`, and the active Rally workspace are present.
2. Read `home:issue.md` again before you act.
3. Decide whether a later reader needs one short saved note.
4. Shape the final JSON this turn declares.

## Workflow

### Steps

_ordered list_

1. Read `home:issue.md` again before you act. This keeps the shared ledger current after wake and resume.
2. Use a note only when later readers would lose context that does not belong in the main file or the final JSON.
3. Write the note through Rally CLI when needed.
4. Keep the note short. Save context, exact commands, or constraints. Do not restate the whole file or copy the final JSON.
5. Keep `--field` labels simple. Put the human explanation in the note body, not in the field names.
6. End the turn with the declared final JSON. If the turn routes, let final JSON carry `next_owner`.

### Preferred stdin form

_Advisory · code · bash_

```bash

"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID" <<'EOF'
### Note
- Explain the context worth preserving for the next owner or later turn.
EOF
```

### Flat field form

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

### Short forms

_unordered list_

- Use `--text` when a one-line note is clearer than stdin.
- Use `--file` when the note already exists in a small prepared file.
- Read `references/note_examples.md` when you need the exact alternate note forms.

## Output expectations

_unordered list_

- When no saved context is needed, end with the final JSON only.
- When saved context is needed, write one note and still end with one final JSON result.
- This skill never creates a second trusted routing path or second turn-ending command.

## Reference map

_unordered list_

- Use `references/note_examples.md` for the exact note command forms.
- No extra `references/` or `scripts/` should ship in v1 unless review or repeated execution failures prove they are needed.
