---
name: "rally-kernel"
description: "Shared Rally turn skill for leaving issue notes, adding flat structured note fields, and ending a turn with the declared final JSON. Use it when a Rally-managed agent needs to leave a note, write that note with `$RALLY_CLI_BIN issue note`, add `--field key=value` labels to that note, or shape final JSON without inventing another way to end the turn. Do not use it for flow-local planning, runtime code changes, or direct `home:issue.md` edits."
---

# Rally Kernel

Use this skill on Rally-managed turns when you need Rally's shared note and end-turn rules.
Do not use it to repeat flow-local prompt instructions.
Rally loads this skill on every Rally-managed turn. Flows do not need to list it by hand.

## When to use

_unordered list_

- You need to leave a note on the current Rally run before the turn ends.
- You need to add short machine-readable note fields such as `kind` or `lane`.
- You need to end the turn with the final JSON this turn declares.
- You need to keep the line clear between saved notes and turn control.

## Canonical user asks

_unordered list_

- "Leave a note on this Rally run before you end the turn."
- "Leave a structured Rally note with `--field` labels."
- "Use the Rally note path, not direct file edits."
- "End the turn with valid Rally JSON without inventing a second return path."

## When not to use

_unordered list_

- The work is local planning, code change, proof, or review inside a flow.
- The task is implementing Rally runtime code such as CLI parsing, ledger writes, or adapter launch behavior.
- The turn is trying to pass work, mark the run done, block, or sleep through note prose instead of final JSON.
- The lesson should help a later run. Use `rally-memory` for cross-run memory instead of this skill.

## Non-negotiables

_unordered list_

- Notes are context only. They never decide who works next or whether the run is done, blocked, or sleeping.
- Keep notes run-local. Use `rally-memory` for cross-run lessons.
- Structured note fields are labels only. Keep them short and flat.
- Note fields never carry `next_owner`, `done`, `blocker`, or `sleep` truth.
- Do not edit `home:issue.md` directly.
- Write notes with `"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID"`.
- Fail loud if `RALLY_CLI_BIN`, `RALLY_WORKSPACE_DIR`, or `RALLY_RUN_ID` is missing instead of guessing the active run or CLI path.
- Rally provides this skill on Rally-managed turns. Flows do not need to allowlist it by hand.
- End the turn through the adapter's final JSON path, not through a second CLI command or prose side path.
- When you use `handoff`, set `next_owner` to the owner key declared by the flow.
- Some review-native turns end with Doctrine review JSON that Rally can read. Those turns may not need a second saved note.

## First move

_ordered list_

1. Confirm this is a Rally-managed turn, that `RALLY_WORKSPACE_DIR` points at the active workspace root, that `RALLY_CLI_BIN` points at Rally CLI, and that `RALLY_RUN_ID` is present.
2. Decide whether a later reader needs a short note.
3. If yes, decide whether the note also needs flat `--field key=value` labels.
4. Write one short markdown note through the Rally CLI.
5. Shape the final turn result to match the declared JSON schema for this turn.

## Workflow

### Steps

_ordered list_

1. Decide whether a note is really needed. Use a note only when later readers would lose important context that does not belong in the flow's main file or in the final turn result itself.
2. Write the note through Rally CLI when needed.
3. Keep the note short. Save context, decisions, exact commands, or constraints that later turns should read. Do not restate the whole file or copy the final JSON.
4. Keep structured fields simple. Use short flat labels such as `kind`, `lane`, `artifact`, or `review_mode`. Put the human explanation in the note body, not in the field names.
5. End the turn with strict final JSON. Many turns use the shared Rally turn result. On that shared shape, send `agent_issues` with one short issue or `none`. Review-native turns may use declared Doctrine review JSON instead. The skill helps you shape that result, but it does not replace the adapter return path.
6. Keep route truth out of notes. If the turn routes, let final JSON carry `next_owner`.

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

- When no saved context is needed, the turn may emit only the final JSON result.
- When saved context is needed, the turn writes one note through Rally CLI and still ends with one final JSON result.
- When Rally already saves a review-native final response into `home:issue.md`, do not add a second note unless the flow asks for it.
- The skill never creates a second trusted routing path, second turn-ending command, or direct file-write shortcut.

## Reference map

_unordered list_

- Use `references/note_examples.md` for the exact note command forms.
- No extra `references/` or `scripts/` should ship in v1 unless review or repeated execution failures prove they are needed.
