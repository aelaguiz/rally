# Rally Hermes Adapter Audit

Date: 2026-04-13
Status: audit
Scope: can Rally accept `runtime.adapter: hermes` beside `runtime.adapter: codex`, and what would we need to decide and build to support it cleanly

## Plain Answer

Yes, Rally could support Hermes as a second accepted adapter.

No, it is not a small patch.

The prompt side is mostly ready already. The real work is in Rally runtime,
run-home setup, final-result enforcement, session resume, event logging, skill
and MCP wiring, auth, and test coverage.

My recommendation is:

1. Treat `hermes` as a real second adapter, not as a codex alias.
2. Do not start with `hermes chat -q -Q` as the long-term adapter surface.
3. Add a Rally adapter registry and a new `src/rally/adapters/hermes/` tree.
4. Require a strict final JSON contract before calling Hermes "fully
   supported" for Rally.

Today Rally is only generic in schema and flow metadata. It is not generic in
runtime behavior.

## Bottom-Line Verdict

### Could we add Hermes?

Yes.

### Could we add it as a fully supported Rally adapter right now?

No.

### What blocks "full support" today?

- Rally runtime is hard-wired to Codex launch, Codex session ids, Codex JSONL
  events, Codex auth seeding, and Codex config materialization.
- Hermes does not expose the same clean machine contract that Rally uses with
  `codex exec --json --output-schema ...`.
- Hermes CLI startup does extra work before the query runs.
- Hermes auto-syncs its own bundled skills into `HERMES_HOME/skills`, which
  would break Rally's skill allowlist model if we point `HERMES_HOME` at the
  current run home without more work.
- Hermes MCP loading comes from `config.yaml`, not from Rally's copied
  `mcps/*/server.toml` files.

### Is this blocked on Doctrine?

No.

This is a Rally runtime problem, not a Doctrine language or compiler problem.
The prompt graph can stay Doctrine-authored.

## What I Checked

### Rally files

- `src/rally/services/runner.py`
- `src/rally/services/home_materializer.py`
- `src/rally/services/flow_loader.py`
- `src/rally/domain/flow.py`
- `src/rally/cli.py`
- `src/rally/terminal/display.py`
- `src/rally/services/run_events.py`
- `src/rally/services/run_store.py`
- `src/rally/adapters/codex/launcher.py`
- `src/rally/adapters/codex/event_stream.py`
- `src/rally/adapters/codex/session_store.py`
- `tests/unit/test_launcher.py`
- `tests/unit/test_runner.py`
- `tests/unit/test_run_events.py`
- `tests/unit/test_flow_loader.py`
- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`

### Hermes files

- `../hermes-agent/AGENTS.md`
- `../hermes-agent/README.md`
- `../hermes-agent/hermes_cli/main.py`
- `../hermes-agent/cli.py`
- `../hermes-agent/run_agent.py`
- `../hermes-agent/hermes_constants.py`
- `../hermes-agent/hermes_cli/config.py`
- `../hermes-agent/hermes_cli/runtime_provider.py`
- `../hermes-agent/hermes_cli/auth.py`
- `../hermes-agent/hermes_state.py`
- `../hermes-agent/toolsets.py`
- `../hermes-agent/tools/skills_sync.py`
- `../hermes-agent/agent/prompt_builder.py`
- `../hermes-agent/tools/mcp_tool.py`
- `../hermes-agent/tools/approval.py`
- `../hermes-agent/acp_adapter/server.py`

## What Already Fits Well

These parts are already friendly to a Hermes adapter:

- `flow.yaml` already carries a generic `runtime.adapter` string.
- `FlowDefinition.adapter.name` is generic on paper.
- Rally compiled agent prompts are plain Markdown and do not depend on Codex
  syntax.
- Rally final result parsing is driven by the compiled schema, not by the flow
  name.
- Rally skills already use YAML frontmatter, and Hermes can parse that style.
- Hermes supports `HERMES_HOME`, so a Rally-owned run home can isolate Hermes
  state.
- Hermes supports per-session ids and persistent session storage.
- Hermes exposes callback hooks for tool progress, thinking, streaming text,
  and step updates.
- Hermes also has an ACP server, so there is a future path to structured event
  transport if we want it.

## What Is Codex-Only In Rally Today

This is the main gap.

| Area | Current Rally reality | Evidence |
| --- | --- | --- |
| Adapter invocation | Runner imports only Codex modules and only calls `codex exec` | `src/rally/services/runner.py` |
| Launch env | Rally builds `CODEX_HOME` and writes only Codex launch records | `src/rally/adapters/codex/launcher.py` |
| Session resume | Rally stores a Codex session id per agent and resumes with `codex exec resume` | `src/rally/adapters/codex/session_store.py`, `src/rally/services/runner.py` |
| Event parsing | Rally parses Codex JSONL event shapes into Rally events | `src/rally/adapters/codex/event_stream.py` |
| Home setup | Rally always writes `config.toml` for Codex MCP config and seeds Codex auth symlinks | `src/rally/services/home_materializer.py` |
| Skill validation note | Rally skill bundle validation is written around Codex skill loading | `src/rally/services/home_materializer.py` |
| Docs | Master design and phase docs describe a Codex-first vertical slice | docs listed above |
| Tests | Most runtime tests fake only Codex behavior | `tests/unit/test_runner.py`, `tests/unit/test_launcher.py`, `tests/unit/test_codex_event_stream.py` |

So the adapter field is generic, but the runtime path is still a single-adapter
system.

## Hermes Facts That Matter For Rally

| Hermes fact | Why it matters |
| --- | --- |
| `HERMES_HOME` controls config, logs, sessions, skills, and auth | Rally can isolate Hermes inside a run-owned home |
| `get_subprocess_home()` uses `HERMES_HOME/home` as subprocess `HOME` when present | Rally can isolate git, ssh, gh, and other tool state if it creates that directory |
| `hermes chat -q -Q` exists | There is a headless CLI path |
| Quiet mode prints final response plus a trailing `session_id:` line | This is close to machine use, but not a strong contract |
| `cmd_chat()` still does provider checks and `sync_skills()` before the query | CLI mode has startup side effects and extra noise risk |
| Hermes stores session logs in `HERMES_HOME/sessions/` and indexed history in `HERMES_HOME/state.db` | Rally must decide whether to use Hermes-native session state, Rally-native state, or both |
| Hermes MCP servers come from `config.yaml -> mcp_servers`, not from `server.toml` files | Rally must translate MCP definitions for Hermes |
| Hermes skills are scanned from `HERMES_HOME/skills/` and optional external dirs | Rally can project allowlisted skills, but only if it controls that directory cleanly |
| `tools/skills_sync.py` auto-copies bundled Hermes skills into `HERMES_HOME/skills/` on CLI launch | This can silently widen the skill surface past Rally allowlists |
| Hermes tool access is controlled by toolsets | Rally must decide how toolsets map to Rally policy |
| Hermes dangerous command approval can block or prompt | Rally must choose approval policy for non-interactive runs |
| `AIAgent.run_conversation()` returns a Python dict with `final_response`, `last_reasoning`, token stats, and flags | A library-backed adapter can avoid a lot of CLI scraping |
| Hermes ACP already bridges tool progress, thinking, messages, and approvals into a structured protocol | ACP is a possible later event path, but it is more work than a direct adapter |

## The Biggest Design Choice

We need to pick the Hermes integration plane.

### Option A: shell out to `hermes chat -q -Q`

Pros:

- CLI-first
- small first demo
- easy to test by hand

Cons:

- no strict output-schema flag
- query output is mixed with `session_id:` text
- startup does provider checks, config migration checks, and skill sync
- hard to map tool/thinking events into Rally event logs
- hard to preserve Rally skill allowlists because `sync_skills()` mutates the
  local skills dir

Verdict:

Good for a throwaway spike. Bad for a clean Rally adapter.

### Option B: Rally imports Hermes Python code and calls `AIAgent`

Pros:

- best control over inputs and outputs
- no CLI startup chatter
- direct access to `final_response`, `last_reasoning`, token stats, and flags
- direct callback hooks for tools, thinking, streaming, and step events
- can avoid `sync_skills()` entirely
- easier to keep `HERMES_HOME` nested and controlled

Cons:

- tighter Python-level coupling between repos
- Rally must own more Hermes session restore code
- Rally still needs a strict final JSON strategy

Verdict:

Best v1 path if we want Hermes support to be real.

### Option C: Rally talks to `hermes acp`

Pros:

- structured event stream already exists
- approval bridging already exists
- session create/resume/fork ideas already exist

Cons:

- Rally does not have ACP client code today
- more moving parts than needed for a first adapter
- still does not solve strict final JSON by itself

Verdict:

Good future path for rich event parity. Not the shortest path to a usable
adapter.

## Recommendation

Build Hermes support as a library-backed Rally adapter first.

Do not make the first real implementation depend on `hermes chat`.

## The Hard Decisions We Would Need To Make

### 1. Is adapter choice flow-wide or agent-wide?

Current Rally model: flow-wide. `runtime.adapter` lives in `flow.yaml`.

Recommendation: keep it flow-wide for v1.

Reason:

- the current runtime model is flow-wide already
- per-agent adapters would widen scope a lot
- mixed Codex/Hermes flows are a second project

### 2. Do we make adapters first-class in Rally?

Current Rally model: string field, but one real implementation.

Recommendation: yes.

Needed result:

- a small adapter registry or adapter interface
- `codex` and `hermes` both validated in `flow_loader`
- adapter-specific home setup and invoke paths

### 3. Where does Hermes live inside the run home?

Recommendation: do not point `HERMES_HOME` at Rally's current run home root.

Use:

- Rally run home: `runs/<id>/home/`
- Hermes home: `runs/<id>/home/hermes/`

Reason:

- avoids collisions with Rally's own `home/sessions/`
- avoids mixing Hermes `state.db`, `config.yaml`, and `sessions/` with Rally
  files
- makes it easier to keep adapter-local archaeology together

### 4. How do we keep Hermes from widening the skill surface?

This is a major policy decision.

Options:

- let Hermes auto-sync bundled skills
- disable that and project only Rally-approved skills
- keep Hermes bundled skills local and point Rally skills through
  `skills.external_dirs`

Recommendation:

- do not use Hermes auto skill sync for Rally turns
- project only Rally-approved skills into the Hermes-visible skill dirs

Reason:

- Rally's `allowed_skills` and mandatory `rally-kernel` should stay the source
  of truth
- `sync_skills()` would otherwise add a large unreviewed skill index into each
  run

### 5. How do Rally MCPs become Hermes MCPs?

Current mismatch:

- Rally stores MCP definitions in `mcps/*/server.toml`
- Codex consumes `config.toml`
- Hermes consumes `config.yaml -> mcp_servers`

Recommendation:

- add Hermes-specific MCP projection in `home_materializer`
- translate each allowlisted `server.toml` into the Hermes config shape

### 6. What tool surface does a Rally Hermes turn get?

Current mismatch:

- Codex brings its own tool surface
- Hermes uses toolsets
- Rally flow config does not model toolsets

Recommendation:

- do not let Hermes default to its broad CLI toolset
- add a narrow Rally-owned Hermes toolset or a fixed mapping in the adapter
- keep v1 small, likely around terminal, process, file, search, web, and
  maybe browser only if needed

### 7. What is the approval policy?

This must be explicit.

Choices:

- `off`
- smart/manual approval
- session YOLO

Recommendation:

- choose one adapter policy and encode it clearly
- if Rally wants Codex-like behavior, then Hermes must run without interactive
  approval prompts for Rally-managed turns

Reason:

- Rally runs are non-interactive once the turn launches
- a prompt-capable approval path would hang or fail

### 8. How do we enforce Rally's strict final JSON result?

This is the single most important decision.

Current Rally law:

- Rally ends each turn through one final JSON result
- current Codex path uses an output schema and writes to a file

Current Hermes reality:

- I did not find a native CLI flag that matches Codex's output-schema contract
- `AIAgent.run_conversation()` returns plain text in `final_response`

Possible choices:

- prompt-only JSON and validate after the fact
- prompt-only JSON plus repair/retry loop on invalid output
- add Hermes-side structured output support
- restrict Hermes adapter to providers that can do strict structured output

Recommendation:

- do not call Hermes "fully supported" until we have a strict result path
- best answer is a Hermes-side or adapter-side structured output contract

If we refuse Hermes-side work, the fallback is:

- validate returned JSON with Rally
- hard-block the run on invalid output

That is workable, but weaker than the current Codex path.

### 9. How does session resume work?

Current Codex path:

- Rally stores one session id per agent slug
- resume is simple and explicit

Hermes path choices:

- stateless: no session resume between turns
- store Hermes `session_id` only and let Hermes reload state
- store `session_id` and use Hermes `SessionDB` to restore conversation history

Recommendation:

- keep per-agent session ids in Rally's session files
- use Hermes `session_id` plus Hermes session DB restore for resumed turns

### 10. Do we want Rally to log Hermes inner events?

Choices:

- opaque adapter: only final stdout/stderr
- callback-mapped events in the direct adapter
- ACP-backed event mapping

Recommendation:

- callback-mapped events in the direct adapter
- keep ACP as a later richer option

Reason:

- Hermes already exposes callbacks
- Rally's live logs are one of its best operator surfaces

### 11. How do we seed auth?

Current Codex path:

- symlink `.codex/auth.json`
- project `CODEX_HOME`

Hermes path:

- Hermes wants `HERMES_HOME/auth.json`, `.env`, and `config.yaml`
- Hermes may also import or write back Codex tokens when the provider is
  `openai-codex`

Recommendation:

- create a Hermes-specific auth projection
- do not reuse Codex-only seeding as the general answer

### 12. What does `adapter_args` mean for Hermes?

Current Codex args:

- `model`
- `reasoning_effort`
- `project_doc_max_bytes`

Hermes will need more choices.

Likely fields:

- `model`
- `provider`
- `api_mode` if we need to override it
- `toolsets`
- `approval_mode`
- `max_turns` or whether Rally owns the turn cap alone
- maybe `fallback_model`

Recommendation:

- define an explicit Hermes adapter-args schema and validate it

### 13. Do we support all Hermes providers or a narrower subset?

Recommendation:

- keep v1 small
- likely support only providers we can validate well under Rally's final JSON
  contract

Reason:

- "Hermes adapter" and "all Hermes providers" are not the same scope

### 14. Do we treat Hermes as user-facing or adapter-private?

Recommendation:

- adapter-private at first

Meaning:

- flow authors use `runtime.adapter: hermes`
- Rally owns the exact home layout, config projection, and launch path
- users do not need to manually run `hermes setup` inside a run home

### 15. Do we want mixed archaeology or adapter-local archaeology?

Recommendation:

- keep Rally as the canonical run owner
- keep Hermes artifacts under a clear adapter-local subtree under the run

Example:

- `home/hermes/config.yaml`
- `home/hermes/state.db`
- `home/hermes/sessions/`
- Rally still keeps canonical `run.yaml`, `state.yaml`, `issue.md`,
  `logs/events.jsonl`, and `logs/rendered.log`

## Files Rally Would Need To Change

### High-confidence Rally changes

- `src/rally/services/flow_loader.py`
  - validate supported adapters
  - validate Hermes adapter args

- `src/rally/services/runner.py`
  - split Codex-only invoke code behind an adapter seam
  - add Hermes session load/save path
  - add Hermes invocation and result handling

- `src/rally/services/home_materializer.py`
  - branch home setup by adapter
  - add Hermes home materialization
  - add Hermes config/auth/MCP projection
  - stop assuming every skill rule is "because Codex loads it"

- `src/rally/adapters/`
  - add a real adapter package shape
  - new `src/rally/adapters/hermes/`

- `tests/unit/test_runner.py`
  - add Hermes path coverage

- `tests/unit/test_flow_loader.py`
  - validate adapter names and Hermes args

- `tests/unit/test_launcher.py`
  - either generalize to adapter launchers or add Hermes launcher tests

- `tests/unit/test_run_events.py`
  - verify Hermes event sources and display output

### Likely new Rally files

- `src/rally/adapters/hermes/launcher.py`
- `src/rally/adapters/hermes/session_store.py`
- `src/rally/adapters/hermes/event_bridge.py`
- maybe `src/rally/adapters/base.py` or similar

### Docs that would need follow-up if we implement this

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`

Those docs currently describe a Codex-first real slice. They are not wrong,
but they would need a careful update once Hermes is real.

## Hermes-Side Changes That Would Make This Much Cleaner

Rally can do some of this alone, but these Hermes changes would make the
integration much cleaner:

1. A true machine mode for one-shot runs.
   Example: a CLI or library surface that returns only machine-safe JSON.

2. A strict output-schema mode.
   This is the biggest missing piece for Rally parity.

3. A way to disable bundled skill sync for adapter-controlled homes.

4. A stable public library wrapper for:
   - one turn
   - session restore
   - callback wiring
   - final response
   - token stats

5. A documented non-interactive provider/config bootstrap path.

## Suggested Implementation Order

### Phase 1: Make Rally adapters real

- add adapter validation
- split runner by adapter
- keep Codex behavior unchanged

### Phase 2: Add Hermes home setup

- nested Hermes home under the run
- Hermes config projection
- Hermes auth projection
- MCP translation
- controlled skill projection

### Phase 3: Add a minimal Hermes invoke path

- library-backed if possible
- session id persistence
- no ACP yet
- block on invalid final JSON

### Phase 4: Add event parity

- map Hermes callbacks into Rally events
- keep rendered logs operator-friendly

### Phase 5: Harden the contract

- strict schema result path
- approval policy
- toolset policy
- test matrix
- docs updates

## Proof We Should Require Before Calling It Done

- one demo flow runs with `runtime.adapter: hermes`
- Rally home stays the source of truth
- Hermes state stays inside the run
- Rally skill allowlists still mean what they say
- Rally allowlisted MCPs are the only MCPs visible
- invalid final JSON blocks cleanly with a clear reason
- per-agent resume works across handoffs
- rendered logs still show assistant, tool, and thinking progress in a useful
  way

## Final Recommendation

If the goal is:

"Can we add Hermes as an accepted adapter value beside Codex?"

then the answer is:

Yes, and we should do it as a real second adapter.

If the goal is:

"Can we do that by lightly patching the current Codex path or by shelling out
to `hermes chat` and calling it done?"

then the answer is:

No.

The clean line is:

- no Doctrine work needed
- real Rally runtime work needed
- likely one or two Hermes runtime features would make the final result much
  cleaner

My call:

- worth doing if we want Rally to be multi-adapter
- not worth doing as a quick alias
- best first implementation is a library-backed Hermes adapter with a nested
  Hermes home and a hard rule that invalid final JSON blocks the run
