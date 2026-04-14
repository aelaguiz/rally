# Rally Kernel Note Examples

Use these examples when you need the exact Rally note command forms.

## Stdin Note

```bash
"$RALLY_CLI_BIN" issue note --run-id "$RALLY_RUN_ID" <<'EOF'
### Note
- Explain the context worth preserving for the next owner or later turn.
EOF
```

## Structured Note Fields

```bash
"$RALLY_CLI_BIN" issue note \
  --run-id "$RALLY_RUN_ID" \
  --field kind=producer_handoff \
  --field lane=producer \
  --field artifact=section_plan <<'EOF'
Kept the body short. Read the field labels first, then this note.
EOF
```

## Short Forms

- Use `--text` when a one-line note is clearer than stdin.
- Use `--file` when the note already exists in a small prepared file.
- Keep the human explanation in the note body, not in the field names.
