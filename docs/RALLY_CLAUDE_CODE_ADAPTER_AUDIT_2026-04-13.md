---
title: "Rally - Claude Code Adapter Audit"
date: 2026-04-13
status: audit
doc_type: technical_audit
related:
  - docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md
  - docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - src/rally/services/runner.py
  - src/rally/services/home_materializer.py
  - src/rally/services/flow_loader.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/codex/event_stream.py
  - src/rally/adapters/codex/result_contract.py
  - src/rally/adapters/codex/session_store.py
---

# Plain Answer

Yes. Rally can add Claude Code as a real second runner beside Codex.

This is much more realistic than the older Hermes notes suggest.

Claude Code now has a strong headless contract:

- `claude -p` for non-interactive runs
- `--output-format json`
- `--output-format stream-json`
- `--json-schema`
- `--resume` and `--continue`
- `--mcp-config` and `--strict-mcp-config`
- `--allowedTools`, `--tools`, and permission modes
- `--system-prompt-file` and `--append-system-prompt-file`
- a Python and TypeScript Agent SDK

So this is not blocked on missing machine interfaces.

But Rally still needs a real adapter boundary. We should not swap `codex` for
`claude` in `runner.py` and call it done.

The hard part is not prompt format. The hard part is auth plus run-home
ownership.

My recommendation is:

1. Add a first-class `claude_code` adapter beside `codex`.
2. Start with the Claude Code CLI, not the SDK.
3. Treat auth as adapter-owned bootstrap.
4. Use a Rally-owned Claude home only when auth is explicit.
5. Do not rely on Claude subagents, agent teams, plugins, or ambient project
   config in v1.

# Scope

This audit is about Anthropic Claude Code.

It is not about the local `hermes-agent` repo.

The Hermes runtime-generalization work is still the right direction for Rally.
The adapter boundary work should stay generic. But the Claude Code facts are
different enough that we should not reuse Hermes assumptions without checking
them again.

Main question:

Can Rally support Claude Code as a clean second runner beside Codex while
keeping Rally's current rules:

- one flow-wide adapter
- one run home
- one issue log path
- one final JSON result path
- no hidden machine-global control plane

# What I Checked

## Rally files

- `src/rally/services/runner.py`
- `src/rally/services/home_materializer.py`
- `src/rally/services/flow_loader.py`
- `src/rally/domain/flow.py`
- `src/rally/adapters/codex/launcher.py`
- `src/rally/adapters/codex/event_stream.py`
- `src/rally/adapters/codex/result_contract.py`
- `src/rally/adapters/codex/session_store.py`
- `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md`
- `docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md`
- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`

## Local Claude Code checks

I checked the installed CLI directly.

Local facts from this machine:

- `claude --version` returned `2.1.104 (Claude Code)`
- `claude auth status` showed a live first-party `claude.ai` login
- `claude --help` showed core headless, session, MCP, tool, and permission
  flags
- `claude mcp --help`, `claude agents --help`, `claude plugin --help`, and
  `claude auto-mode defaults` confirmed extra control surfaces
- `claude -p --output-format json --json-schema ...` returned one JSON envelope
  with `session_id`, usage fields, and `structured_output`
- `claude -p --output-format stream-json --verbose --bare ...` returned
  newline-delimited event objects
- `CLAUDE_CONFIG_DIR=$(mktemp -d) claude auth status` returned `loggedIn:
  false`

That last point matters a lot. A fresh Claude config dir lost local
subscription auth.

## Official Claude Code docs

I checked current official docs from `code.claude.com` and current changelog
notes. Key pages:

- CLI reference
- headless or programmatic usage
- authentication
- settings
- permissions
- MCP
- skills
- memory and `CLAUDE.md`
- subagents
- agent teams
- Agent SDK overview
- Agent SDK sessions
- Agent SDK hooks
- GitHub Actions
- changelog

# Bottom-Line Verdict

## Could Rally add Claude Code?

Yes.

## Is Claude Code a better runner target than the older Hermes audit implied?

Yes.

Claude Code now has a supported headless path, structured output, session
resume, and explicit config flags that line up with Rally much better than a
plain chat CLI.

## Is Rally ready for it today?

No.

Shared runtime code is still Codex-only.

## What is the main blocker?

Auth plus state ownership.

If Rally wants a clean Claude adapter home inside `runs/<id>/home/`, it cannot
just point `CLAUDE_CONFIG_DIR` at a fresh folder and expect the user's local
Claude login to work.

That means full support needs one of these:

- API key auth
- `apiKeyHelper`
- long-lived `CLAUDE_CODE_OAUTH_TOKEN` in non-bare mode
- some other explicit adapter-owned auth bootstrap

Using the user's default global Claude state is okay for a local spike. It is
not okay for a clean Rally adapter.

# Key Findings

## 1. Claude Code already has the machine contract Rally needs

Current official docs say `claude -p` is the supported non-interactive path.
It supports:

- `--output-format json`
- `--output-format stream-json`
- `--json-schema`
- `--resume` and `--continue`
- `--mcp-config`
- `--strict-mcp-config`
- `--allowedTools`
- `--tools`
- `--permission-mode`
- `--system-prompt-file`
- `--append-system-prompt-file`
- `--max-turns`
- `--session-id`

This is enough for Rally to build:

- strict final JSON
- saved session ids
- adapter launch logs
- adapter event parsing
- per-turn prompt injection
- adapter-owned MCP translation

This is the biggest difference from the older Hermes shape.

## 2. `claude --help` is not the full contract

The official CLI reference says `claude --help` does not list every flag.

That matched local reality. Local `--help` did not show all flags, but these
flags still parsed on this machine:

- `--system-prompt-file`
- `--append-system-prompt-file`
- `--max-turns`

Rally should treat the docs as the source of truth for Claude flags, not the
short local help text alone.

## 3. Claude Code can return strict structured output today

Official docs say:

- `--output-format json` returns a JSON envelope with metadata
- `--json-schema` puts the schema-checked object in `structured_output`
- `session_id` is present in the result

Local proof matched that.

This means Rally does not need a file-output flag like Codex has. The adapter
can:

1. capture the raw JSON result
2. write the raw envelope to adapter logs
3. write `structured_output` to Rally's `last_message.json`
4. feed that file into Rally's existing final-result loader

## 4. Claude Code can stream events, but the event model is different

Official docs say `--output-format stream-json --verbose` returns
newline-delimited event objects. Docs also show:

- `stream_event` items for streaming deltas
- `system/api_retry` events
- final result objects with `session_id`

Local proof showed `system`, `assistant`, and `result` event objects.

So Rally can build a `ClaudeCodeEventStreamParser`, but it cannot reuse the
Codex JSONL parser. This is adapter-owned work.

## 5. `--bare` is a strong fit for Rally, but only with explicit auth

Official docs call `--bare` the recommended scripted mode. It skips:

- hooks
- skills
- plugins
- MCP auto-discovery
- auto memory
- `CLAUDE.md`

This is very close to what Rally wants for a clean run:

- no ambient repo instructions
- no ambient plugins
- no ambient MCP servers
- no surprise memory writes

But official docs also say `--bare` skips OAuth and keychain reads.

So `--bare` only works cleanly when auth comes from:

- `ANTHROPIC_API_KEY`, or
- `apiKeyHelper`, or
- third-party cloud provider auth

It does not work with the user's normal Claude subscription login.

## 6. A fresh `CLAUDE_CONFIG_DIR` breaks subscription login

Local proof on this machine:

- default config dir: logged in
- fresh `CLAUDE_CONFIG_DIR`: not logged in
- copying `~/.claude.json` into a fresh config dir still did not restore login

That means Rally cannot assume Claude auth follows the run home the same way
Codex auth symlinks do today.

This is the most important new local finding.

If Rally wants adapter-local Claude state under the run home, it must solve
auth on purpose.

## 7. Non-bare isolated mode is possible, but still needs auth bootstrap

Official docs say `CLAUDE_CODE_OAUTH_TOKEN` works for scripts and CI.
Official docs also say bare mode does not read that token.

So Claude has two realistic isolated modes for Rally:

### Mode A: strict isolated mode

- `CLAUDE_CONFIG_DIR=<run-home>/claude`
- `--bare`
- `ANTHROPIC_API_KEY` or `apiKeyHelper`

This is the cleanest Rally fit.

### Mode B: isolated OAuth mode

- `CLAUDE_CONFIG_DIR=<run-home>/claude`
- not bare
- `CLAUDE_CODE_OAUTH_TOKEN`
- clean working dir and explicit config flags

This can preserve Rally's run-home model while still using subscription-style
auth, but it needs a one-time token setup step outside the run.

### Mode C: local spike mode only

- default global Claude config
- normal `/login` auth

This is okay for personal testing. It is not okay for full Rally support,
because state leaks into `~/.claude` and `~/.claude.json`.

## 8. Rally should not rely on Claude slash commands in `-p` mode

Official docs say user-invoked skills and built-in slash commands are only
available in interactive mode. In `-p` mode you should describe the task in
plain text instead.

This matters for Rally because today Rally relies on shared skills such as
`rally-kernel`.

Claude Code does support skills, including automatic skill loading. But in
headless runs Rally should not depend on a human-style `/skill-name` path, and
it should not treat auto-loading as proven until we test the Rally skills
directly.

That creates one prompt-side question for Rally:

- either prove the needed skills auto-load well enough in headless mode
- or move must-have rules into prompt source so the runner does not depend on
  runtime skill discovery for correctness

The main shared Rally rules are too important to leave to a maybe.

## 9. Claude Code reads `CLAUDE.md`, not `AGENTS.md`

Official docs say Claude reads `CLAUDE.md`, not `AGENTS.md`.

But Claude also supports `--system-prompt-file` and
`--append-system-prompt-file`.

That means Rally does not need to rename its compiled prompt artifact just to
support Claude.

The clean path is:

- keep Rally's compiled `AGENTS.md`
- build a Claude adapter prompt file from it
- pass that file with a system-prompt flag

That avoids adding Claude-only prompt files to the repo.

## 10. MCP mapping is simpler than Hermes, but still adapter-owned

Current Rally writes Codex MCP config in `config.toml`.

Claude wants MCP config in JSON via:

- `--mcp-config`
- `--strict-mcp-config`
- `.mcp.json`

Official docs also say project-scoped `.mcp.json` can trigger approval and
ambient discovery, while `--strict-mcp-config` ignores other MCP sources.

So the clean Rally path is:

1. keep Rally's `mcps/*/server.toml` as source
2. translate allowlisted MCPs into one generated JSON file inside the run home
3. launch Claude with `--mcp-config <generated-file> --strict-mcp-config`

This is a good fit for Rally.

## 11. Claude built-in subagents exist, but Rally should disable them in v1

Official docs say Claude supports:

- custom subagents
- CLI-defined subagents with `--agents`
- built-in agent types
- experimental agent teams

That is useful in general, but Rally already has its own flow agents.

If Rally lets Claude spawn subagents freely inside one Rally turn, we get:

- hidden parallel work
- extra token burn
- more session state
- a second ownership model inside a single Rally agent turn

Recommendation for v1:

- do not use `--agent`, `--agents`, or agent teams
- exclude the `Agent` tool from the allowed tool set
- keep one Rally flow agent mapped to one Claude session

## 12. Agent teams are not a v1 fit

Official docs say agent teams are:

- experimental
- off by default
- token-heavy
- limited around resume and shutdown

Docs also say team state lives in user-global paths under `~/.claude/teams/`
and `~/.claude/tasks/`.

That conflicts with Rally's run-home rules.

So agent teams should stay out of scope for the first Claude adapter.

## 13. Claude permissions are strong enough for Rally, but the defaults matter

Official docs define these modes:

- `default`
- `acceptEdits`
- `plan`
- `auto`
- `dontAsk`
- `bypassPermissions`

For Rally, the important ones are:

- `dontAsk` for strict non-interactive runs
- `acceptEdits` if we want file-write auto-approval but still gate other tools
- `bypassPermissions` only in very isolated environments

The docs are clear that `allowedTools` only auto-approves the listed tools. It
does not limit the tool set by itself. That means Rally needs both:

- `--tools` to choose which built-in tools exist
- `--allowedTools` and or `dontAsk` to avoid interactive prompts

This is a better permission story than Rally has today with Codex's full
bypass launch.

## 14. Claude SDK is powerful, but it changes the auth and product story

Official docs say the Agent SDK gives the same tools, hooks, permissions,
sessions, and structured outputs as Claude Code.

That is attractive for Rally because it would give:

- native Python message objects
- easier hook integration
- easier event parsing
- direct session APIs

But the docs also say the SDK should use API key or provider auth, not a
Claude subscription login for third-party products.

That matters.

Rally is a local CLI product. If we want users to bring their own installed
Claude Code and local login, the CLI is the cleaner v1 surface.

The SDK is still a strong later option if we are ready to require explicit API
key style auth.

# Claude Code vs Rally Concerns

| Concern | Claude Code fact | Rally impact | Recommendation |
| --- | --- | --- | --- |
| Final result | `--json-schema` returns schema-checked data in `structured_output` | strong fit for Rally final JSON | parse envelope, save `structured_output` to Rally result file |
| Session resume | `session_id`, `--resume`, `--continue`, `--fork-session` are supported | good fit for per-agent session save | keep adapter session store and save Claude session id per agent |
| Event stream | `stream-json` exists, but event types differ from Codex | new parser needed | build Claude-specific event parser |
| Prompt source | Claude reads `CLAUDE.md`, not `AGENTS.md` | cannot rely on file-name discovery | use system-prompt file flags from Rally |
| Skills | skills exist, but slash invocation is interactive-only | required Rally skills may be shaky in `-p` | do not rely on manual slash skills for correctness |
| MCP | `--mcp-config` plus `--strict-mcp-config` is supported | good fit for generated allowlist | translate TOML to generated JSON |
| Permissions | tool set and allow rules are separate | safer but more setup than Codex | set both `--tools` and `--allowedTools` |
| Auth | fresh `CLAUDE_CONFIG_DIR` loses local login | hard blocker for clean run-home ownership | require explicit auth bootstrap for full support |
| Auto memory | on by default outside bare mode | hidden machine-local state | prefer bare mode or clean config plus memory off |
| Plugins and hooks | auto-discovered outside bare mode | ambient behavior can leak in | do not allow them in v1 |
| Subagents | built in | can hide extra work inside a turn | disable in v1 |
| Agent teams | experimental and user-global | bad fit for Rally v1 | out of scope |

# Recommended Claude Adapter Shape

## Adapter name

Use `claude_code`, not `claude`, `anthropic`, or `hermes`.

Reason:

- it names the real runner surface
- it avoids confusion with model API naming
- it matches the docs and local CLI name

## Adapter boundary

The same runtime split the Hermes generalization doc already asks for still
makes sense:

- adapter validation in flow loading
- adapter-owned home materialization
- adapter-owned launch env
- adapter-owned invocation
- adapter-owned event parsing
- adapter-owned session handling
- adapter-owned result loading

Codex and Claude Code should both sit behind that boundary.

## Recommended v1 launch shape

For the clean path, a Claude turn should look like this in spirit:

```bash
CLAUDE_CONFIG_DIR="$RUN_HOME/adapters/claude_code" \
ANTHROPIC_API_KEY="..." \
claude --bare -p \
  --output-format json \
  --json-schema "$SCHEMA_JSON" \
  --tools "Bash,Read,Edit,Write,Glob,Grep" \
  --allowedTools "Bash,Read,Edit,Write,Glob,Grep" \
  --permission-mode dontAsk \
  --strict-mcp-config \
  --mcp-config "$RUN_HOME/adapters/claude_code/mcp.json" \
  --append-system-prompt-file "$RUN_HOME/adapters/claude_code/system_prompt.md" \
  --model claude-sonnet-4-6 \
  "Complete the turn and return schema-valid JSON."
```

The real adapter may choose `stream-json` instead of `json` when we want live
event rendering.

## Run-home layout

Do not mix Claude internal files into Rally's current generic folders.

Use an adapter-private home, for example:

- `runs/<id>/home/adapters/claude_code/`
- `runs/<id>/home/adapters/claude_code/.claude.json`
- `runs/<id>/home/adapters/claude_code/projects/`
- `runs/<id>/home/adapters/claude_code/sessions/`
- `runs/<id>/home/adapters/claude_code/mcp.json`
- `runs/<id>/home/adapters/claude_code/settings.json`
- `runs/<id>/home/adapters/claude_code/system_prompt.md`

Then keep Rally's public proof paths where operators already expect them:

- `logs/adapter_launch/`
- `home/sessions/<agent>/session.yaml`
- `home/sessions/<agent>/turn-<n>/...`

Rally should mirror or reference Claude state from the adapter-private home
into those stable operator paths.

## Prompt injection plan

Use a system-prompt file flag.

Do not depend on:

- ambient `CLAUDE.md`
- renaming compiled `AGENTS.md`
- extra repo-root Claude files

Recommended flow:

1. Build Rally's normal compiled `AGENTS.md`
2. Append runtime prompt input sections
3. Write one generated Claude system prompt file in the adapter home
4. Pass it with `--append-system-prompt-file`

Only switch to `--system-prompt-file` if Claude's default system prompt causes
real problems. Docs recommend append mode for most cases.

## Session plan

Keep one Claude session id per Rally agent slug.

That matches current Codex behavior and fits official Claude resume docs.

Store:

- session id
- cwd
- updated time
- maybe transcript path inside adapter home

Claude session files are local to the machine and the working directory. That
means the adapter should treat saved session ids as valid only when:

- the adapter home still exists
- the working directory still matches
- the adapter auth mode still works

## Result loading plan

Claude result loading should be adapter-owned but simple:

1. parse the final JSON envelope
2. extract `session_id`
3. extract `structured_output` when schema mode is used
4. write `structured_output` to Rally's final message artifact
5. reuse Rally's existing turn-result parsing after that

## Event plan

Use `stream-json --verbose` when we want live output.

Map at least:

- init and session-start events
- assistant message text
- retry events
- final result event
- auth and other errors

If CLI stream coverage is too thin for good operator output, re-check the SDK
for event handling only after the auth and product story is settled.

# Auth Modes Rally Could Support

## Mode 1: strict isolated API mode

Best fit for Rally invariants.

Use when:

- CI
- containers
- enterprise setups
- users can provide API-key style auth

Shape:

- `CLAUDE_CONFIG_DIR` under run home
- `--bare`
- `ANTHROPIC_API_KEY` or `apiKeyHelper`

Pros:

- clean run-home ownership
- no ambient discovery
- docs-recommended scripted mode

Cons:

- not backed by local Claude subscription login

## Mode 2: isolated OAuth token mode

Best fit when users want subscription-backed auth but still want Rally-owned
state.

Shape:

- `CLAUDE_CONFIG_DIR` under run home
- not bare
- `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`
- clean working dir and explicit config flags

Pros:

- keeps run-home control
- works for CI and scripts

Cons:

- one more user setup step
- not as clean as bare mode

## Mode 3: default local login mode

This is for spikes only.

Shape:

- default `~/.claude` and `~/.claude.json`
- regular `/login` state

Pros:

- easiest way to test locally

Cons:

- state escapes Rally run home
- hard to prove and replay
- violates Rally's storage rules for full support

# What This Changes In The Hermes Planning Docs

The general direction in `RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION` is
still good:

- real adapter registry
- adapter-owned launch rules
- adapter-owned session handling
- adapter-owned event parsing
- adapter-owned result loading

But Claude Code changes three key assumptions:

## 1. We do not need to start from a weak CLI surface

Claude Code already has official structured output and stream output. So the
adapter can start from a supported machine path instead of a scrape-heavy chat
path.

## 2. Auth is the top risk

For Hermes, skill sync and MCP wiring looked like the bigger problem.

For Claude Code, auth plus config-dir behavior is the top risk.

## 3. Bare mode gives Rally a better clean-room story than Hermes had

Hermes looked like it would need more startup cleanup.

Claude bare mode already disables most ambient behavior. That is a major
advantage, as long as auth is explicit.

# Main Open Questions

## 1. Do we require explicit Claude auth for full support?

I think yes.

Without that, Rally cannot honestly say Claude state lives in the run home.

## 2. Do we want CLI-first or SDK-first?

I recommend CLI-first for v1.

Reason:

- it matches Rally's current Codex pattern
- it supports local installed Claude Code
- official docs support it directly
- it avoids early SDK auth and product-policy questions

Use SDK later if we need stronger event objects or hook integration and we are
ready to require API-key style auth.

## 3. How do we handle Rally mandatory skills?

This still needs a design call.

Claude supports skills, but headless runs should not depend on user-style slash
invocation.

The safe choices are:

- prove auto-loaded Claude skills are enough, or
- move must-have shared rules into prompt source

## 4. Do we expose `model`, `effort`, `max_budget_usd`, and `max_turns` in
`adapter_args`?

Probably yes.

Claude names the reasoning knob `effort`, not `reasoning_effort`, so the
adapter either needs a mapping rule or its own adapter-specific arg names.

## 5. Do we support Claude internal subagents later?

Not in v1.

Rally already has multi-agent flow control. We should not add a second hidden
agent system until the single-session adapter is solid.

# Recommended Next Step

If we move forward, the clean next step is:

1. Finish the generic adapter boundary work from the runtime generalization
   doc.
2. Add `claude_code` as a validated adapter name in flow loading.
3. Build a docs-only or test-only Claude launch prototype behind a new adapter
   module.
4. Start with strict isolated API mode or isolated OAuth token mode.
5. Do not call local default-login mode "supported" even if it works for a
   smoke test.

# Source Links

## Official Claude Code docs

- CLI reference: https://code.claude.com/docs/en/cli-reference
- Programmatic usage: https://code.claude.com/docs/en/headless
- Authentication: https://code.claude.com/docs/en/iam
- Settings: https://code.claude.com/docs/en/settings
- Permissions: https://code.claude.com/docs/en/permissions
- Environment variables: https://code.claude.com/docs/en/env-vars
- MCP: https://code.claude.com/docs/en/mcp
- Skills: https://code.claude.com/docs/en/skills
- Memory and `CLAUDE.md`: https://code.claude.com/docs/en/memory
- Subagents: https://code.claude.com/docs/en/sub-agents
- Agent teams: https://code.claude.com/docs/en/agent-teams
- Hooks: https://code.claude.com/docs/en/hooks
- Agent SDK overview: https://code.claude.com/docs/en/agent-sdk/overview
- Agent SDK sessions: https://code.claude.com/docs/en/agent-sdk/sessions
- Agent SDK permissions: https://code.claude.com/docs/en/agent-sdk/permissions
- Agent SDK hooks: https://code.claude.com/docs/en/agent-sdk/hooks
- GitHub Actions: https://code.claude.com/docs/en/github-actions
- Changelog: https://code.claude.com/docs/en/changelog

## Local checks run for this audit

- `claude --version`
- `claude --help`
- `claude auth status`
- `claude mcp --help`
- `claude agents --help`
- `claude plugin --help`
- `claude auto-mode defaults`
- `claude -p --output-format json --json-schema ...`
- `claude -p --output-format stream-json --verbose --bare ...`
- `CLAUDE_CONFIG_DIR=$(mktemp -d) claude auth status`
