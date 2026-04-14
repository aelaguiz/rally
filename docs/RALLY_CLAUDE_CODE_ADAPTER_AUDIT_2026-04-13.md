---
title: "Rally - Claude Code Adapter Audit"
date: 2026-04-13
status: audit
doc_type: technical_audit
related:
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - docs/RALLY_HERMES_ADAPTER_AUDIT_2026-04-13.md
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - src/rally/services/runner.py
  - src/rally/services/home_materializer.py
  - src/rally/services/flow_loader.py
  - src/rally/services/workspace.py
  - src/rally/services/run_store.py
  - src/rally/domain/run.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/codex/event_stream.py
  - src/rally/services/final_response_loader.py
  - src/rally/adapters/codex/session_store.py
---

# Plain Answer

Yes. Rally can add Claude Code as a real second adapter beside Codex.

Claude Code now has a good headless contract for Rally:

- `claude -p`
- `--output-format json`
- `--output-format stream-json`
- `--json-schema`
- `--resume`
- `--mcp-config` and `--strict-mcp-config`
- `--tools` and `--allowedTools`
- `--permission-mode`

So the adapter is not blocked on missing machine interfaces.

At audit time, Rally was not ready to ship it yet. The runtime was still
Codex-only in practice. `runner.py` launched Codex directly.
`home_materializer.py` still wrote Codex config and Codex auth links from
shared code.

This audit recommended the v1 path that later shipped:

1. add a real `claude_code` adapter beside `codex`
2. keep Rally's shared prompt assembly and pass that prompt to Claude on stdin
3. write one valid final JSON object to Rally's shared `last_message.json`
4. generate Claude MCP config under the run home
5. use the user's existing Claude login and config in v1

That last point matters. Full Claude clean-room auth is still a later mode, not
the current v1 plan.

## Implementation status on 2026-04-13

The main runtime recommendations from this audit are now in tree:

- shared adapter boundary in `src/rally/adapters/base.py`
- shared registry in `src/rally/adapters/registry.py`
- shared final JSON loader in `src/rally/services/final_response_loader.py`
- Codex cut over to the shared adapter boundary
- Claude shipped as a real `claude_code` adapter with generated
  `home/claude_code/mcp.json`, `home/.claude/skills`, explicit built-in tool
  clamps, and the shared `last_message.json` final path

The remaining honest v1 caveat from this audit still stands:

- Claude support still depends on the user's existing local Claude login and
  Claude's native session store outside the run home

Read the rest of this file as the audit basis, not the shipped contract.
Where this audit's recommended flags differ from the shipped adapter, the code
and `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md` win.
The main shipped differences are:

- Claude now uses `--permission-mode dontAsk`
- Claude now uses explicit `--tools` and `--allowedTools`
- Claude now has `src/rally/adapters/claude_code/session_store.py` as a thin
  adapter-owned wrapper over the shared session helpers
- Claude final-output extraction now also accepts JSON from `result.result`
  and assistant text content, including fenced JSON blocks from live Claude
  output

# Scope

This audit is about Anthropic Claude Code.

It is not about the local `hermes-agent` repo.

The shared adapter-boundary direction from the Hermes docs is still useful. But
Claude Code facts are strong enough, and different enough, that Rally should
treat Claude as its own concrete adapter target.

Main question:

Can Rally support `runtime.adapter: claude_code` beside `codex` while keeping
Rally's current rules:

- one flow-wide adapter
- one run home
- one issue-ledger path
- one final JSON result path
- no hidden Rally control plane outside the repo

# What I Checked

## Rally files

- `src/rally/services/runner.py`
- `src/rally/services/home_materializer.py`
- `src/rally/services/flow_loader.py`
- `src/rally/services/workspace.py`
- `src/rally/services/run_store.py`
- `src/rally/domain/flow.py`
- `src/rally/domain/run.py`
- `src/rally/adapters/codex/launcher.py`
- `src/rally/adapters/codex/event_stream.py`
- `src/rally/adapters/codex/session_store.py`
- `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`
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
  `claude auto-mode defaults` showed extra control surfaces
- `claude -p --output-format json --json-schema ...` returned one JSON envelope
  with `session_id`, usage fields, and `structured_output`
- `claude -p --output-format stream-json --verbose --bare ...` returned
  newline-delimited event objects
- `CLAUDE_CONFIG_DIR=$(mktemp -d) claude auth status` returned `loggedIn:
  false`

## Official Claude Code docs

I checked current official docs from `code.claude.com` and the current
changelog. Key pages:

- CLI reference
- headless usage
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

Claude Code now has an official non-interactive CLI, strict structured output,
session resume, and explicit config flags that line up with Rally much better
than a plain chat CLI.

## Is Rally ready for it today?

At audit time: no.

Today: yes for the shipped v1 path described in
`docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`.

## What was the main blocker at audit time?

The main blocker was the shared adapter boundary. Auth and state ownership were
the hardest Claude-specific design constraint, but the repo also needed to
stop importing Codex helpers straight into shared runtime code.

The codebase has shifted enough that the path is clearer than before:

- `flow.yaml` already carries `runtime.adapter`, `runtime.adapter_args`, and
  `runtime.prompt_input_command`
- `run.yaml` already stores `adapter_name`
- `WorkspaceContext` already gives shared runtime code one honest workspace,
  CLI, and framework-root owner
- Rally already projects `RALLY_WORKSPACE_DIR` and `RALLY_CLI_BIN`
- home materialization already refreshes shared run-home content on each start
  or resume

So Claude support is now more about cutting the current Codex path over to a
real adapter seam than about inventing a new runtime from scratch.

# Key Findings

## 1. Claude Code already has the machine contract Rally needs

Current official docs say `claude -p` is the supported non-interactive path.
It supports:

- `--output-format json`
- `--output-format stream-json`
- `--json-schema`
- `--resume`
- `--continue`
- `--mcp-config`
- `--strict-mcp-config`
- `--allowedTools`
- `--tools`
- `--permission-mode`

This is enough for Rally to build:

- strict final JSON
- saved session ids
- adapter launch logs
- adapter event parsing
- per-turn prompt injection
- adapter-owned MCP translation

## 2. The current Rally runtime already had useful shared seams

At audit time the runtime was still Codex-only, but the code around it was
more generic than the older Claude notes assumed.

Current reusable Rally-owned seams:

- `flow_loader.py` already owns `runtime.adapter`, `runtime.adapter_args`, and
  `runtime.prompt_input_command`
- `run_store.py` already persists `adapter_name` in `run.yaml`
- `workspace.py` already resolves one shared workspace root, CLI path, and
  framework root
- `runner.py` already builds one prompt from compiled `AGENTS.md` plus runtime
  prompt inputs
- `home_materializer.py` already owns shared run-home layout, issue gating,
  agent sync, skill sync, MCP sync, setup script runs, and issue snapshots

That means Claude support should reuse these shared Rally seams instead of
building a second local runtime path.

## 3. Claude can return strict structured output today

Official docs and simple CLI probes said:

- `--output-format json` returns a JSON envelope with metadata
- `--json-schema` puts the schema-checked object in `structured_output`
- `session_id` is present in the result

Local proof matched that.

This meant Rally did not need a Claude-only best-effort parser. The adapter
could:

1. capture the raw Claude result envelope
2. extract `session_id`
3. write the final JSON object to Rally's `last_message.json`
4. reuse Rally's shared final-response loader after that

## 4. Claude can stream events, but the event model is different

Official docs say `--output-format stream-json --verbose` returns
newline-delimited event objects.

Local proof showed `system`, `assistant`, and `result` event objects.

So Rally can build a `ClaudeCodeEventStreamParser`, but it cannot reuse the
Codex JSONL parser. This is adapter-owned work.

## 5. The v1 auth call is now clear: ambient existing Claude login

The current Rally plan no longer treats isolated Claude auth as a v1
requirement.

The supported v1 local path is:

- use the user's existing Claude login and config
- do not set `CLAUDE_CONFIG_DIR`
- do not require `--bare`
- clamp the Claude surfaces Rally can clamp with runtime flags

This is the current practical choice because a fresh `CLAUDE_CONFIG_DIR` loses
the user's normal subscription login on this machine.

This choice has one honest cost:

- v1 does not give full run-home ownership of Claude auth or all Claude ambient
  behavior

The docs must say that plainly.

## 6. Strict isolated Claude modes are still real later options

Claude still supports cleaner future modes if Rally later wants them:

- isolated OAuth token mode
- strict API-key or `apiKeyHelper` mode with `--bare`

Those are future cleanup modes. They are not the current v1 gate.

## 7. Rally should keep using stdin prompt delivery

Official docs say Claude reads `CLAUDE.md`, not `AGENTS.md`.

That does not force Rally to rename files or add Claude-only prompt files.

The cleaner path is:

1. Rally builds its normal compiled prompt text
2. Rally appends runtime prompt inputs
3. the Claude adapter sends that prompt on stdin to `claude -p`

That keeps one prompt source and avoids Claude-only prompt drift.

## 8. Claude MCP and tool clamps fit Rally well

Current Rally already owns MCP allowlists and built-in skill and MCP projection
into the run home.

Claude gives Rally native ways to clamp its own runtime surfaces:

- `--mcp-config`
- `--strict-mcp-config`
- `--tools`
- `--allowedTools`
- `--permission-mode`

So the clean Claude path is:

1. keep `mcps/*/server.toml` as source
2. generate Claude JSON config under the run home
3. launch Claude with strict MCP config and explicit tool clamps

## 9. Rally should not depend on headless Claude skill discovery for correctness

Claude supports skills, but user-invoked slash commands are interactive-only.

That matters because Rally already depends on shared rules such as the
Rally-managed note and final JSON contract.

The safe rule is:

- keep must-have Rally behavior in prompt source
- treat Claude skill loading as optional extra help, not as correctness law

## 10. Subagents, agent teams, plugins, hooks, and auto memory are not v1 surfaces

Claude has more ambient features than Rally wants inside one flow turn:

- subagents
- agent teams
- plugins
- hooks
- auto memory

For v1:

- do not use Claude subagents
- do not use agent teams
- do not rely on plugins or hooks
- clamp the runtime surfaces Claude exposes
- document the remaining ambient dependency honestly

# Claude Code vs Rally Concerns

| Concern | Claude Code fact | Rally impact | Recommendation |
| --- | --- | --- | --- |
| Final result | `--json-schema` returns schema-checked data in `structured_output` | strong fit for Rally final JSON | parse envelope, save `structured_output` to `last_message.json`, then reuse Rally loader |
| Session resume | `session_id`, `--resume`, `--continue`, and `--fork-session` are supported | good fit for per-agent session save | keep one Claude session id per Rally agent slug |
| Event stream | `stream-json` exists, but event types differ from Codex | new parser needed | build Claude-specific event parsing |
| Prompt source | Claude reads `CLAUDE.md`, not `AGENTS.md` | file-name discovery is a bad fit | keep Rally's shared prompt assembly and pass the prompt on stdin |
| Skills | skills exist, but slash invocation is interactive-only | required Rally rules may drift in `-p` mode | do not depend on headless skill discovery for correctness |
| MCP | `--mcp-config` plus `--strict-mcp-config` is supported | good fit for generated allowlist | translate Rally MCP TOML to generated Claude JSON |
| Permissions | tool set and auto-approval are separate | safer than Codex, but more setup | set both `--tools` and `--allowedTools`, plus `dontAsk` when needed |
| Auth | fresh `CLAUDE_CONFIG_DIR` loses local login | isolated auth is not the v1 default | support ambient existing Claude login in v1, keep stricter modes later |
| Auto memory, hooks, and plugins | still ambient outside `--bare` | not full clean-room in v1 | clamp what Claude exposes and call out the remaining ambient risk |
| Subagents and teams | built in, and teams are user-global | can hide extra work inside one Rally turn | keep them out of v1 |

# Recommended Claude Adapter Shape

## Adapter name

Use `claude_code`, not `claude`, `anthropic`, or `hermes`.

Reason:

- it names the real runner surface
- it avoids confusion with model API naming
- it matches the current architecture plan

## Adapter boundary

Claude should sit behind the same shared adapter boundary Codex needs.

Shared Rally code should own:

- flow loading
- run creation and resumption
- shared run-home layout
- shared prompt assembly
- final-response loading from `last_message.json`
- turn-result routing and issue-ledger writes

The Claude adapter should own:

- adapter arg validation details
- adapter home prep
- Claude CLI launch shape
- Claude event parsing
- Claude session storage
- Claude result-envelope parsing before Rally sees `last_message.json`

## Recommended v1 launch shape

For the current v1 plan, a Claude turn should look like this in spirit:

```bash
claude -p \
  --output-format stream-json \
  --verbose \
  --json-schema "$SCHEMA_JSON" \
  --permission-mode dontAsk \
  --strict-mcp-config \
  --mcp-config "$RUN_HOME/claude_code/mcp.json" \
  --tools "Bash,Read,Edit,Write,Glob,Grep" \
  --allowedTools "Bash,Read,Edit,Write,Glob,Grep" \
  --model "claude-sonnet-4-6"
```

Important v1 rules:

- pass the Rally prompt on stdin
- use `--resume <session-id>` when Rally has a saved Claude session
- do not set `CLAUDE_CONFIG_DIR`
- do not require `--bare`

## Run-home layout

Keep the current Rally operator proof paths:

- `logs/adapter_launch/`
- `home/sessions/<agent>/session.yaml`
- `home/sessions/<agent>/turn-<n>/exec.jsonl`
- `home/sessions/<agent>/turn-<n>/stderr.log`
- `home/sessions/<agent>/turn-<n>/last_message.json`

Add only a small Claude-owned area under the run home, for example:

- `runs/<id>/home/claude_code/mcp.json`
- `runs/<id>/home/claude_code/` for any later generated Claude-owned helper
  files Rally truly needs

Do not move Claude auth into the run home in v1.

## Prompt injection plan

Use Rally's current shared prompt path.

Do not depend on:

- ambient `CLAUDE.md`
- renaming compiled `AGENTS.md`
- a Claude-only prompt file for v1

Recommended flow:

1. build Rally's normal compiled prompt
2. append runtime prompt inputs
3. send the result on stdin to `claude -p`

## Session plan

Keep one Claude session id per Rally agent slug.

Store:

- session id
- cwd
- updated time
- any Claude-specific metadata only if the adapter really needs it

This keeps the public operator path the same as the current Codex session
story.

## Result loading plan

Claude result handling should stay simple:

1. parse the final Claude result envelope
2. extract `session_id`
3. extract `structured_output`
4. write `structured_output` to Rally's `last_message.json`
5. let Rally's shared final-response loader parse the result after that

## Event plan

Use `stream-json --verbose` for live output.

Map at least:

- init and resume events
- assistant text and progress
- retry events
- final result events
- auth, permission, and other hard errors

# Auth Modes Rally Could Support

## Mode 1: supported v1 local mode

Use the user's existing Claude login and config.

Shape:

- default Claude config paths
- no `CLAUDE_CONFIG_DIR`
- no `--bare`
- explicit runtime clamps for tools, MCPs, and permission mode

Pros:

- easiest honest local path
- matches the current Rally Claude plan
- avoids per-run auth bootstrap

Cons:

- not full run-home ownership
- some ambient Claude behavior remains outside Rally control

## Mode 2: future isolated OAuth mode

Use when Rally wants stronger local isolation without forcing API-key auth.

Shape:

- `CLAUDE_CONFIG_DIR` under the run home
- not bare
- `CLAUDE_CODE_OAUTH_TOKEN`
- clean working dir and explicit config flags

Pros:

- tighter run-home ownership
- still works with subscription-style auth

Cons:

- more setup work
- still not as clean as strict bare mode

## Mode 3: future strict API mode

Best fit for full clean-room support.

Shape:

- `CLAUDE_CONFIG_DIR` under the run home
- `--bare`
- `ANTHROPIC_API_KEY` or `apiKeyHelper`

Pros:

- cleanest run-home ownership
- best scripted and CI story

Cons:

- not backed by the normal local Claude subscription login

# What This Means For Earlier Hermes Exploration

The useful part that carried forward is still small and clear:

- real adapter registry
- adapter-owned launch rules
- adapter-owned session handling
- adapter-owned event parsing

Use the current master design, Phase 4 runtime doc, and CLI/logging doc for
live runtime truth.
- adapter-owned result-envelope parsing

But Claude changes three practical assumptions:

## 1. We do not need to start from a weak CLI surface

Claude Code already has official structured output and stream output.

## 2. Auth is still the top Claude-specific risk, but the v1 answer is now explicit

The current answer is:

- ambient existing Claude login in v1
- isolated auth only later if Rally decides the extra ownership is worth it

## 3. Rally should reuse its current prompt and final-result paths

Claude support should not add:

- a second prompt graph
- a Claude-only prompt file path for correctness
- a second turn-ending result path

# Remaining Implementation Questions

## 1. What is the exact Claude built-in tool allowlist?

Rally should keep this narrow and make it explicit.

## 2. Do we need any Claude skill support at all in headless v1?

Probably not for correctness. The current safe answer is to keep Rally's must
have rules in prompt source.

## 3. Which adapter args should stay shared and which should stay Claude-only?

Shared candidates:

- `model`
- `reasoning_effort`

Possible Claude-only later args:

- `max_turns`
- `max_budget_usd`

## 4. When is isolated Claude auth worth shipping?

That is now a product choice, not a blocker for the first Claude adapter.

# Recommended Next Step

The clean next step is:

1. land the shared adapter boundary and shared final-response loader
2. cut the current Codex path over to that boundary without changing current
   runtime behavior
3. add a guarded `claude_code` adapter with stdin prompt delivery, generated
   run-home MCP config, and ambient-auth v1
4. only after live proof call `claude_code` a supported adapter name

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
