# Rally Master Design

Date: 2026-04-12
Status: working draft
Purpose: define Rally's stable design law, ownership boundary, core runtime contract, and roadmap without duplicating the exact Phase 3 and Phase 4 specs.

This doc is intentionally the constitutional version of the design.
It should stay short enough to orient a fresh reader quickly.
Exact implementation details now live in:

- [RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md](RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md)
- [RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md](RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md)
- [RALLY_CLI_AND_LOGGING_2026-04-13.md](RALLY_CLI_AND_LOGGING_2026-04-13.md)

## Repo Guide

This repo sits beside three useful neighboring repos, but Rally should stay conceptually separate from all of them:

- `../paperclip`
  - inspiration for orchestration rigor, resumable sessions, issue-centered work, and durable run lifecycle
  - not the product shell Rally is trying to copy
- `../doctrine`
  - the authoring language and compiler substrate for Rally agent doctrine
  - not the Rally runtime, CLI, or standard library home
- `../paperclip_agents`
  - the first real set of pressure tests and example agent families
  - not Rally's product/domain model and not framework law
- `./`
  - the Rally framework repo itself
  - should become a CLI-native, filesystem-native, Doctrine-native flow runner

## North Stars

These are the rules Rally should keep returning to:

1. Filesystem truth comes first.
   Rally should keep its semantic source of truth on disk in normal files the operator can inspect and edit.

2. Workspace root is Rally home.
   Rally assumes fixed workspace-root `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/` directories.

3. Doctrine-native `.prompt` authoring is the only instruction source.
   Compiled Markdown is generated readback, not authored truth.

4. No side doors into agents.
   If instruction prose reaches an agent, it must come from the declared `.prompt` graph for that flow.

5. Home is the whole world.
   Every run gets one prepared home; skills, MCPs, repos, artifacts, sessions, and adapter-local state all live there.

6. One active run per flow.
   Rally should refuse concurrent active execution of the same flow unless the design changes intentionally.

7. Flow-first, not company-first.
   Rally is about authored flows and runs, not org charts, dashboards, boards, or registry products.

8. Programmer-native operation.
   The system should feel natural in a shell, in git, and on the filesystem.

9. General-purpose framework, not domain cargo.
   `paperclip_agents` provides pressure and examples, but domain nouns there must not become framework primitives here.

10. Doctrine will move with Rally.
   If Rally needs generic authored-semantics or compiler support to stay clean, that support belongs in Doctrine rather than in Rally-side hacks.

11. No hidden global Rally state.
   Rally-owned state lives under the active workspace root, not under `~/.rally`, `~/.config`, or similar hidden control planes.

12. No GUI, board, company, or registry carryover.
   Rally keeps Paperclip's runtime rigor, not its surrounding product shell.

## Ownership Boundary

This is the canonical split between Doctrine and Rally.

### Doctrine owns

- `.prompt` language semantics
- compiler behavior
- deterministic build emission
- generic final-output semantics
- generic route semantics
- generic review semantics when they are truly authored-language concerns
- machine-readable emitted build metadata Rally can consume without scraping Markdown

### Rally owns

- the standard library contents under `stdlib/rally/`
- flow runtime contract under `flows/*/flow.yaml`
- the run model, run ids, logs, sessions, and locks
- home preparation and home materialization
- adapter launch rules
- CLI behavior
- issue-log ordering and snapshots
- the shared `rally issue note` surface
- the Rally kernel skill
- the Rally memory skill
- repo-local memory files, QMD state, and memory indexing
- durable memory files, memory indexing, and runtime event records
- the runtime's interpretation of validated final turn results

### `paperclip_agents` owns nothing in the framework

That repo is pressure and examples only.
It does not get to define Rally primitives.

### Decision rule

If the missing capability is generic authored semantics, generic compile-time metadata, or generic emitted build structure, it belongs in Doctrine first.

If the missing capability is runtime behavior, adapter launch, CLI behavior, run-home layout, or issue-log materialization, it belongs in Rally.

Rally should fail loudly on missing Doctrine support instead of encoding a local workaround that hardens the wrong boundary.

## What Rally Is

Rally is:

- a flow runner
- CLI-first
- filesystem-first
- Doctrine-native
- repo-root-native
- general-purpose
- shipped today with `codex` and `claude_code` as the supported adapters

Rally is not:

- a clone of the Paperclip app
- a company control plane
- a board or dashboard product
- a marketplace or plugin-host product
- a database-first runtime
- a workspace-mode repo manager
- a domain-specific framework for any one product family

## Core Runtime Model

### Flows

A flow is the authored template for a repeatable multi-agent process.
Each runnable flow lives under `flows/<flow-slug>/`.

The canonical runtime contract for a flow is `flows/<flow-slug>/flow.yaml`.
That file declares runtime facts, not instruction prose.
It also carries runtime limits such as `runtime.max_command_turns`, plus
runtime hooks such as one setup script, one prompt-input reducer, and guarded
git repo paths.

Every runnable flow has three stable identities:

- the directory slug such as `poem_loop`
- a human-readable `name`
- a validated three-letter uppercase `code`

The `code` rules are:

- exactly three uppercase ASCII letters
- unique across runnable flows in the repo
- required for every runnable flow

Examples:

- `FLW`
- `CDR`
- `BUG`

### Runs

A run is one concrete execution of a flow.

Run ids are per flow and have the shape `<FLOW_CODE>-<n>`.
The numeric portion starts at `1` for each flow and counts upward within that flow.

Examples:

- the first run of `FLW` is `FLW-1`
- the three-hundred-forty-second run of `CDR` is `CDR-342`

`run.yaml` is the stable identity record for a run.
`state.yaml` is the compact machine-readable current summary.

Rally should keep one active run per flow unless the operator asks to replace it on purpose.

### Home

Each run gets one prepared home directory.

The setup script prepares that home before the first agent runs.
On every `run` or `resume`, Rally refreshes its own copied agents, skills,
MCPs, and adapter-owned bootstrap files before the next turn starts.
After that:

- agents assume home is already prepared
- agents operate inside that home rather than inventing ad hoc repo-management behavior
- Rally refreshes one stable skill view per agent under
  `home/sessions/<agent>/skills/` from repo-root `skills/`, whether the source
  is markdown `SKILL.md` or Doctrine `prompts/SKILL.prompt` plus emitted
  `build/SKILL.md`
- before each turn, Rally copies the current agent's prebuilt skill view into
  the live `home/skills/` tree
- MCP definitions are still materialized from repo-root `mcps/` into shared
  `home/mcps/` from the flow's per-agent allowlists
- repos, artifacts, env files, and adapter-local state live there
- agents do not escape home

A flow may also declare one prompt-input reducer that runs before each turn and
one guarded-git list that Rally checks before it accepts `handoff` or `done`.

Adapter-specific bootstrap rules still stay narrow:

- for Codex, Rally points `CODEX_HOME` at the run home and keeps Codex root
  files there
- for Claude Code, Rally generates `home/claude_code/mcp.json` and links
  `home/.claude/skills` to `home/skills`
- Claude v1 still uses the user's existing local Claude login and Claude's
  native session store outside the run home

Follow-up gap to resolve later:

- Rally still needs a clean runtime enforcement story for per-agent
  `allowed_mcps`

### Ledger, Notes, And Turn Results

`home/issue.md` is the live semantic ledger for the run.

It should:

- begin with the operator's brief exactly as entered
- remain append-only after that initial brief
- add one hidden `<!-- RALLY_ORIGINAL_ISSUE_END -->` marker before the first Rally-owned block
- hold setup notes, serialized notes, normalized final-turn response records, and runner-generated status records
- use one Markdown `---` divider between Rally-owned blocks after that marker
- add `- Turn: \`N\`` on turn-scoped blocks without asking the agent to manage that line

Rally does not create a second shared brief file.
The opening brief lives at the top of `home/issue.md`.

After every Rally-owned append, Rally should snapshot the full file into `issue_history/`.

The communication model is now explicit:

- there is no such thing as a human handoff
- there is no separate authored handoff object
- there are only serialized notes plus the structured final turn result

Serialized notes are durable context only.
They do not carry trusted routing, blocker, sleep, or done truth.
They may carry flat string note fields when later turns need stable labels.

The structured final turn result is the only turn-ending control surface.
It tells Rally whether to route, stop, block, or ask for sleep.
The shared JSON always carries the same five keys:

- `kind`
- `next_owner`
- `summary`
- `reason`
- `sleep_duration_seconds`

Fields that do not apply are `null` on the classic shared shape.
Review-native turns may use control-ready Doctrine review JSON instead of the five-key object.
If the result uses `kind: handoff`, that is only the label of the route-to-next-owner branch in the classic shared result.
Rally now keeps running across handoffs inside one `run` or `resume`
command until it reaches a real stop point.
Sleep requests are recorded, then blocked, until true sleep support lands.

The end-turn helper inside the Rally kernel skill may help the agent shape that JSON, but it is not a second return path.
The actual return still comes back through the adapter's strict final JSON-schema path.

Rally does not add a shared file-state carrier on top of Doctrine.
If a local authored review needs review-state syntax, treat that as local Doctrine syntax, not as a Rally communication channel.

### Standard Library And Core Skills

Rally ships a mandatory standard library written in Doctrine.
Every Rally flow and every Rally agent inherits from it.

The standard library should stay light-touch.
It should start with:

- one tiny shared `rally.turn_results` final-output contract
- one shared issue-ledger input for run-home-relative `issue.md`
- one shared note path
- one shared memory contract
- one mandatory Rally kernel skill
- one mandatory Rally memory skill

The Rally kernel skill should:

- teach agents to use the shared `rally issue note` CLI surface for durable notes
- teach agents how to shape schema-valid end-of-turn JSON
- remain helper-shaped rather than becoming a second runtime

The Rally memory skill should:

- teach agents to use `rally memory search`, `rally memory use`, `rally memory save`, and `rally memory refresh`
- keep memory as explicit CLI behavior instead of hidden prompt-only magic
- keep memory visible in Rally logs as first-class memory rows instead of raw shell traces
- keep reusable lessons in the shared memory path

The checked-in shared prompts under `stdlib/rally/prompts/rally/` should stay small and direct.
The favored design is now:

- `rally.turn_results` as the machine control contract
- one shared issue-ledger input and one shared memory document shape in Doctrine source
- notes through Rally-owned skill-plus-CLI behavior
- memory through Rally-owned skill-plus-CLI behavior backed by repo-local markdown plus repo-local QMD state
- no separate authored handoff artifact

The mixed-skill path is now real.
Doctrine-authored `rally-kernel` and `demo-git` can live beside markdown skills
in the same prepared run home.

## Runtime Contract Summary

### Instruction And Isolation Rules

If instruction prose reaches an agent, it must come from the declared `.prompt` graph for that flow.

Rally should explicitly ban:

- shared Markdown overlays
- ad hoc `.md` files mounted as extra instruction payload
- ambient repo-root `AGENTS.md` bleed-through
- random docs or scratch files entering agent homes implicitly
- runtime prompt augmentation that is not declared in the `.prompt` source tree

`flow.yaml`, `run.yaml`, session sidecars, logs, and setup scripts may control orchestration, but they must not author doctrine.

### Adapter Launch Contract

Every adapter launch must follow these shared rules:

- choose `cwd` explicitly
- inject compiled doctrine explicitly
- inject `RALLY_RUN_ID=<run-id>` and `RALLY_FLOW_CODE=<flow-code>`
- inject `RALLY_AGENT_SLUG=<agent-slug>`
- inject `RALLY_TURN_NUMBER=<turn-number>` for runtime-owned note labeling
- keep one adapter launch proof record under `logs/adapter_launch/`
- require one strict final-turn JSON path for end-of-turn completion

Current Codex launch facts:

- set `CODEX_HOME` to the run home
- launch with `--dangerously-bypass-approvals-and-sandbox`
- disable ambient project-doc discovery with `project_doc_max_bytes = 0`
- assemble MCP config through the Codex home files Rally prepares

Current Claude launch facts:

- use `claude -p`
- pass the Rally prompt on stdin
- use `--output-format stream-json --verbose`
- use `--permission-mode dontAsk`
- use generated `home/claude_code/mcp.json` with `--strict-mcp-config`
- clamp Claude.ai MCP servers with `ENABLE_CLAUDEAI_MCP_SERVERS=false`
- clamp built-in tools with explicit `--tools` and `--allowedTools` lists

Rally should fail closed if it cannot prove what instruction surface an
adapter is actually seeing.

### Adapter MCP And Auth Health

Rally still needs one clean adapter-native way to make required MCPs usable
inside the run.

This section records the need.
It does not choose the answer yet.

Rally should be able to tell, for each required MCP:

- was it materialized into the run home
- does the current adapter see it through the supported config path
- does the run have the auth that MCP needs
- will a child agent started from that turn keep the same MCP access
- can Rally detect when that setup is broken on a later turn or on resume

Rules:

- A Rally-managed agent and any child agent it starts should get the same
  required MCP access story.
- Rally should use one clean supported path for MCP auth.
  It should not depend on luck, hidden machine state, or one-off manual repair
  inside a live session.
- If a required MCP is missing, not authed, expired, or otherwise not usable,
  Rally should stop with a clear blocker.
- That blocker should name the MCP and the failed check.
- Launch proof and run logs should make it easy to see which MCPs Rally
  expected and why Rally refused to run.
- This work should stay in the Rally runtime and adapter boundary unless it
  reveals a true adapter or Doctrine platform gap.

The next design pass should compare the smallest honest options and prove which
one keeps both parent and child agents ready across fresh runs and resumes.

### Canonical Runtime Surfaces

These are the stable runtime surfaces the design depends on:

| Surface | Role |
| --- | --- |
| `flows/*/flow.yaml` | runtime contract for a flow |
| `flows/*/prompts/**` | authored doctrine source |
| `flows/*/build/**` | compiled readback only |
| `run.yaml` | stable run identity |
| `state.yaml` | compact machine status |
| `home/issue.md` | live semantic ledger |
| `issue_history/` | full-file ledger snapshots |
| `runs/memory/entries/` | durable cross-run memory markdown truth |
| `runs/memory/qmd/` | repo-local QMD index and cache root |
| `logs/events.jsonl` | structured run telemetry |
| `logs/agents/` | per-agent event mirrors |
| `logs/rendered.log` | plain operator transcript |
| `logs/adapter_launch/` | proof of the launch contract per turn |
| `home/agents/` | per-run copy of compiled agent outputs, refreshed on each start or resume |
| `home/skills/` | live adapter-facing skill tree for the current agent, refreshed before each turn |
| `home/mcps/` | materialized allowed MCP capabilities, refreshed on each start or resume |
| `home/sessions/<agent>/skills/` | stable per-agent skill views, refreshed on each start or resume |
| `home/sessions/` | adapter session sidecars or stable references |

### Operator Surface

The operator surface should stay small.
Conceptually it is:

```bash
rally run <flow> [--new]
rally resume <FLOW_CODE>-<n> [--edit|--restart]
rally archive <FLOW_CODE>-<n>
rally issue note --run-id <FLOW_CODE>-<n> [--field key=value ...]
rally memory search --run-id <FLOW_CODE>-<n> --query "<text>"
rally memory use --run-id <FLOW_CODE>-<n> <memory-id>
rally memory save --run-id <FLOW_CODE>-<n> [--text "<markdown>" | --file <path>]
rally memory refresh --run-id <FLOW_CODE>-<n>
```

`rally run` and `rally resume` should give the operator one clean live view on
a TTY and a plain text fallback when the output is not interactive. That
startup view should show the run id, flow, flow code, model, thinking level,
adapter, start agent, and agent count.
Before either command starts the next turn, Rally should rebuild that flow's
compiled agents through the paired Doctrine emit target and refresh the
run-home `home/agents/` copy from the rebuilt readback.
`rally run` creates the run shell first. If `home/issue.md` is missing or
blank on a real TTY, Rally should open the editor, seed a short issue prompt,
strip that prompt back out if it is still there, and keep going after save.
If the shell is not interactive or the editor does not produce real issue
text, Rally should still stop loud and tell the operator to fill in that file
before `rally resume`.
`rally run --new` should ask before it archives the current active run for that
flow, then start a fresh run and reuse the same `home/issue.md` editor path.
Archived runs should not resume.
`rally resume --edit` should open the current `home/issue.md` in place before
the turn starts. If the run is blocked, a saved non-empty edit should move it
back to `pending` and let Rally try the turn again. A blank save should stop
and wait for a real issue. If the operator changed the file text, Rally should
append one `user edited issue.md` block with a unified diff at the end of the
same ledger before the turn resumes. Done and archived runs should still
refuse plain resume.
`rally resume --restart` should ask before it archives the current active run,
recover the original issue from the earliest issue snapshot when it can, start
a fresh run with a new run id, and seed that new run's `home/issue.md` with
only the recovered original issue. The new `Rally Run Started` block should
use source `rally resume --restart` and include `Restarted From: <old-run-id>`.
Done runs may restart even though they cannot resume.

`rally issue note` is the shared durable-note write surface for both agents and operators.
When Rally launched the active turn, the CLI should add the current turn
number to the normalized note block automatically.
It should support:

- stdin
- `--file /path/to/note.md`
- `--text "..."`
- repeatable `--field key=value` for flat note labels

Rally should also keep one tiny adapter-backed helper seam for simple strict-JSON maintenance tasks such as:

- branch-name generation
- brief or note markdown cleanup

That seam should use the same adapter stack Rally already owns rather than a separate helper stack.

## Doctrine Support Boundary

Rally should keep one explicit register of Doctrine-side requirements instead of routing around them.

| Area | Status | Why it matters |
| --- | --- | --- |
| Import-root and packaging support for `stdlib/rally/` | required | Rally needs a clean standard-library import path |
| Generic `final_output:`-style turn designation | required | Rally needs an authored final-return contract |
| Generic readable `route.*` semantics in final outputs | required | Rally routes from validated final JSON, not prose |
| Machine-readable emitted metadata | required | Rally must not scrape generated Markdown to recover compiler meaning |
| Authored capability declarations | desirable | Doctrine may declare semantic capability needs while Rally still owns runtime materialization |
| Currentness or review extensions | only if needed | Add only for real generic authored-semantics gaps |

Rally should now plan against the live local Doctrine direction:

- route-aware `final_output` support is real
- split review prose plus structured final output is real
- same-output review JSON finals with emitted review metadata are real
- routed-owner reads must be structurally bound
- missing or dishonest route bindings fail loudly

What must not move into Doctrine:

- run directories
- runtime files
- adapter launch policy
- CLI or renderer behavior
- home confinement
- note materialization order
- Rally-specific run-store or lock behavior

## Roadmap Summary

### Phase 1: Build The Rally Standard Library

Status: the authored standard-library baseline is done in this repo.

What survives from this phase:

- the shared `rally.turn_results` contract
- schema and example assets for that contract
- the import/composition pattern Rally flows use to adopt those conventions

What remains true:

- legacy note and handoff output shapes are transitional
- runtime execution belongs to Phase 4

### Phase 2: Build One Narrow Authored Flow

Status: the first enduring authored flow is now `poem_loop`.

What this phase gives Rally:

- one enduring authored flow under `flows/poem_loop/`
- one small multi-agent loop with durable notes and one durable artifact
- one authored shape that later runtime work must satisfy without changing the prompt contract

### Phase 3: Pivot Issue Communication To A Rally-Owned Skill

Owner doc:
[RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md](RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md)

Phase 3 locks the communication pivot:

- no human handoff
- no separate authored handoff object
- serialized notes through the Rally kernel skill plus `rally issue note`
- strict final JSON as the only turn-ending control path
- `RALLY_RUN_ID`, `RALLY_FLOW_CODE`, and `RALLY_TURN_NUMBER` injected on every Rally-managed launch
- the tiny schema-bound helper seam exists on the same adapter stack

The exact Phase 3 deliverables, acceptance criteria, and non-goals live in the Phase 3 doc rather than here.

### Phase 4: Build The First Runnable Runtime Slice

Owner doc:
[RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md](RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md)

Phase 4 is the first runtime phase.
It began by proving Rally could execute the authored assets from Phase 1
through Phase 3 honestly on Codex.
The shipped runtime now extends that slice through one shared adapter boundary
with `codex` and `claude_code`.

At a high level, Phase 4 owns:

- the first real `src/rally/` runtime package
- the first real `rally` CLI entrypoint
- the shared adapter boundary
- one real Codex adapter path
- one real Claude adapter path
- one real end-to-end execution path for `poem_loop`
- run storage, home preparation, note and final-response materialization, sessions, and logs

The exact checked-in structure, runtime-created structure, behavior list, and acceptance criteria now live in the Phase 4 doc rather than here.

### Phase 5: Make Rally Operator-Native And Prove The Shape Repeats

Phase 5 begins only after Phase 4 proves the first honest runnable flow.
That proof now exists for `poem_loop` on the Codex path.

Its job is to make the runtime believable as a narrow v1 without broadening the product shape.
At a high level, Phase 5 should add:

- real archive behavior
- dirty-state refusal and stale-run diagnosis
- the history-backed renderer already implied by the design
- one explicit Rally-to-Doctrine compatibility boundary
- a live proof run for the second narrow flow

Phase 5 should still remain:

- adapter-boundary-first
- filesystem-first
- one-active-run-per-flow
- repo-root-local
- no GUI
- no DB source of truth
- no background scheduler

Phase 5 should also close the MCP gap with:

- one honest adapter-native MCP auth and readiness path
- clear failure when a required MCP is missing or broken
- proof that child agents keep the same MCP access on fresh runs and resumes

Phase 5 should also close the remaining per-agent capability gap with:

- real runtime enforcement of each agent's `allowed_mcps`
- a per-agent MCP isolation path that is as clear as the shipped per-turn
  skill activation path

### Phase 6: Add Human-In-The-Loop Flow Requirements

Phase 6 should make human review and human feedback a supported required part
of a flow.

This is a future implementation requirement.
Rally should be able to require human review and feedback before a flow can
continue when the authored flow calls for it.

The exact runtime shape, operator flow, and authored syntax are deferred to the
phase doc for that work.

## Design Notes Appendix

These notes are still useful, but they no longer need to dominate the doc.

### Resolved Notes Worth Keeping

- One semantic ledger plus minimal rebuildable sidecars is the right v1 center of gravity.
- There should be no DB as source of truth in v1.
- `home/issue.md` is the only agent-to-agent communication layer.
- Only `AGENTS.md` is formalized as Rally's runtime instruction contract; other emitted artifacts may exist, but they are compiler-owned readback rather than Rally-authored workflow law.
- Canonical numbered agent keys are identity, not execution order.
- Sessions should stay per agent and per run, and resume should be delta-oriented rather than a fresh-world reinjection.
- The renderer should be history-backed from structured logs, not just a dumb tail of stdout.
- Archive and closeout should stay explicit operator actions.
- Crash recovery should stay explicit and operator-driven.
- No overlays or hidden support planes should appear in the runtime.

### Deferred Questions

- Recursion shape: nested child runs versus sibling runs with explicit parent references.
- Whether `home/issue.md` will eventually need to split into multiple surfaces after real usage proves it is carrying too many concerns.

### Future Direction After Phase 5

The next architecture move after Phase 5 should not be more product shell.
Built-in per-flow and per-agent memory now ships through repo-local markdown,
repo-local QMD state, and Rally-owned CLI and issue/event paths.

The next memory-related work should stay on the same rails:

- keep repo-local state
- keep markdown as the durable truth
- keep search and rebuild repair on the Rally front door
- add replay, archive, and broader live-flow proof before broader memory scope
- avoid hidden global control planes and DB-first truth
