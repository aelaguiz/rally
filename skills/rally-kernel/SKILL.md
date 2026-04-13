---
name: rally-kernel
description: "Shared Rally turn skill for leaving issue notes when needed and ending a turn with the declared final JSON. Use it when a Rally-managed agent needs to leave a note, write that note with `$RALLY_BASE_DIR/rally issue note`, or shape final JSON without inventing another way to end the turn. Do not use it for flow-local planning, runtime code changes, or direct `issue.md` edits."
---

# Rally Kernel

Use this skill on Rally-managed turns when you need Rally's shared note and
end-turn rules. Do not use it to repeat flow-local prompt instructions.

Rally loads this skill on every Rally-managed turn. Flows do not need to list
it by hand.

## When to use

- You need to leave a note on the current Rally run before the turn ends.
- You need to end the turn with the final JSON this turn declares.
- You need to keep the line clear between saved notes and turn control.

Canonical user asks:

- "Leave a note on this Rally run before you end the turn."
- "Use the Rally note path, not direct file edits."
- "End the turn with valid Rally JSON without inventing a second return path."

## When not to use

- The work is local planning, code change, proof, or review inside a flow.
- The task is implementing Rally runtime code such as CLI parsing, ledger
  writes, or adapter launch behavior.
- The turn is trying to pass work, mark the run done, block, or sleep through
  note prose instead of final JSON.

## Non-negotiables

- Notes are context only. They never decide who works next or whether the run
  is done, blocked, or sleeping.
- Do not edit `home/issue.md` directly.
- Write notes with `"$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID"`.
- Fail loud if `RALLY_BASE_DIR` or `RALLY_RUN_ID` is missing instead of
  guessing the active run or CLI path.
- Rally provides this skill on Rally-managed turns. Flows do not need to
  allowlist it by hand.
- End the turn through the adapter's final JSON path, not through a second CLI
  command or prose side path.
- When you use `handoff`, set `next_owner` to the owner key declared by the
  flow.
- Some review-native turns end with Doctrine review JSON that Rally can read.
  Those turns may not need a second saved note.

## First move

1. Confirm this is a Rally-managed turn, that `RALLY_BASE_DIR` points at the
   Rally repo root, and that `RALLY_RUN_ID` is present.
2. Decide whether a later reader needs a short note.
3. If yes, write one short markdown note through the Rally CLI.
4. Shape the final turn result to match the declared JSON schema for this turn.

## Workflow

1. Decide whether a note is really needed.
   Use a note only when later readers would lose important context that does
   not belong in the flow's main file or in the final turn result itself.

2. Write the note through Rally CLI when needed.
   Prefer the stdin form:

   ```bash
   "$RALLY_BASE_DIR/rally" issue note --run-id "$RALLY_RUN_ID" <<'EOF'
   ### Note
   - Explain the context worth preserving for the next owner or later turn.
   EOF
   ```

   Short forms may use `--text` or `--file` when they are clearer.

3. Keep the note short.
   Save context, decisions, exact commands, or constraints that later turns
   should read. Do not restate the whole file or copy the final JSON.

4. End the turn with strict final JSON.
   Many turns use the shared five-key Rally turn result. Review-native turns
   may use declared Doctrine review JSON instead. The skill helps you shape
   that result, but it does not replace the adapter return path.

5. Keep route truth out of note prose.
   If the turn routes, let final JSON carry `next_owner`.

## Output expectations

- When no saved context is needed, the turn may emit only the final JSON
  result.
- When saved context is needed, the turn writes one note through Rally CLI and
  still ends with one final JSON result.
- When Rally already saves a review-native final response into `issue.md`, do
  not add a second note unless the flow asks for it.
- The skill never creates a second trusted routing path, second turn-ending
  command, or direct file-write shortcut.

## Reference map

- No extra `references/` or `scripts/` should ship in v1 unless review or
  repeated execution failures prove they are needed.
