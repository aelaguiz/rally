---
title: "Rally - Agent Interview And Session Forking - Architecture Plan"
date: 2026-04-14
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - README.md
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - docs/RALLY_RUNTIME.md
  - src/rally/cli.py
  - src/rally/adapters/base.py
  - src/rally/adapters/registry.py
  - src/rally/adapters/claude_code/adapter.py
  - src/rally/adapters/claude_code/session_store.py
  - stdlib/rally/prompts/rally/base_agent.prompt
  - src/rally/services/flow_build.py
  - src/rally/services/final_response_loader.py
  - flows/software_engineering_demo/prompts/AGENTS.prompt
  - src/rally/services/runner.py
  - src/rally/services/home_materializer.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/adapters/codex/launcher.py
  - src/rally/adapters/codex/session_store.py
  - tests/unit/test_cli.py
  - tests/unit/test_runner.py
---

# TL;DR

## Outcome

Rally gets one explicit diagnostic interview path so an operator can talk to an
agent about its instructions, ask what is confusing, and propose doctrine
changes without putting that agent back into normal work mode. When an adapter
can do it safely, Rally can also fork a saved session into that same interview
mode without changing the live run. This must feel like a normal Rally CLI
feature, not a debug-only escape hatch. The shipped design must support both
Codex and Claude, not just one of them.

## Problem

Today Rally only has the normal work path: it builds one `AGENTS.md`, appends
runtime prompt inputs, and either starts a fresh session or resumes the saved
session for that agent. There is no clean way to say "explain your rules, do
not follow them right now," and there is no safe fork path for mid-run session
debugging. A hand-made runtime stub would also break Rally's rule that prompt
source lives in `.prompt` files, not runtime sidecars.

## Approach

Keep the interview instructions as real prompt source and let Rally choose that
readback on purpose. The diagnostic prompt must tell the agent in plain words
that it is in interview mode, that it must not do its normal job, and that it
should explain the real instruction file it was pointed at. Rally should ship
one `rally interview` chat command with two modes behind it: a fresh interview
and a forked interview. That command should use compiled interview prompt
source, keep its own transcript and session record under the run tree, and stay
outside the normal Rally turn-result path. Claude can use its public CLI
session controls. Codex should widen only the diagnostic path to native thread
start, turn, and fork support instead of trying to fake fork on `codex exec`.
The command should use a read-only diagnostic home refresh, not the normal
issue-gated run-start path.

## Plan

1. Emit one shared compiled `INTERVIEW.md` sidecar and add a diagnostic-safe
   home refresh path.
2. Ship `rally interview` plus the fresh Claude diagnostic path on Claude's
   public session surface.
3. Add the fresh Codex diagnostic path on Codex native thread and turn APIs
   while keeping `codex exec` for work turns.
4. Add safe fork support for both adapters without changing the live saved
   session record.
5. Sync the live docs and finish with the focused proof set.

## Non-negotiables

- No runtime-authored instruction stub or markdown overlay outside the declared
  prompt graph.
- A diagnostic interview must say plainly that the agent is not here to do its
  normal work.
- A live run must stay resumable and unchanged after a diagnostic session.
- The design must support both Codex and Claude.
- No hidden global state or side control plane outside Rally's run files.
- No awkward debug-only operator path that feels bolted on.
- Research real adapter capabilities before choosing the final runtime shape.
- Fail loud if either adapter cannot meet the approved safety bar.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-14
Verdict (code): COMPLETE
Manual QA: pending (non-blocking)

## Code blockers (why code is not done)
- None. This fresh audit checked the full approved Phase 1 through Phase 5
  frontier, not only the later reopened follow-through.

## Reopened phases (false-complete fixes)
- None. No phase is false-complete on code after this audit.

## Missing items (code gaps; evidence-anchored; no tables)
- None.

## Code-complete evidence checked
- Phase 1 is covered by the shared interview prompt source, bundled prompt
  copy, shared sidecar render path, diagnostic home refresh, and artifact
  helpers:
  `stdlib/rally/prompts/rally/interview_agent.prompt`,
  `src/rally/_bundled/stdlib/rally/prompts/rally/interview_agent.prompt`,
  `src/rally/services/flow_build.py`, `src/rally/services/home_materializer.py`,
  and `src/rally/adapters/base.py`.
- Phase 2 is covered by the `rally interview` command, shared interview
  service, Claude fresh and fork paths, pre-launch `launch.json`, transcript
  writes, run-log events, and live assistant streaming:
  `src/rally/cli.py`, `src/rally/services/interview.py`, and
  `src/rally/adapters/claude_code/interview.py`.
- Phase 3 is covered by the Codex diagnostic-only app-server client on
  `thread/start` and later `turn/start`, with the normal work path still on
  `codex exec`: `src/rally/adapters/codex/interview.py`,
  `src/rally/adapters/codex/adapter.py`, and
  `src/rally/adapters/codex/launcher.py`.
- Phase 4 is covered by Claude `--fork-session`, Codex `thread/fork`, separate
  diagnostic session records under `home/interviews/...`, and unchanged live
  `home/sessions/<agent>/session.yaml` records.
- Phase 5 is covered by the new debugging guide plus synced README, master
  design, CLI/logging, communication, and runtime docs:
  `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md`, `README.md`,
  `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_CLI_AND_LOGGING.md`,
  `docs/RALLY_COMMUNICATION_MODEL.md`, and `docs/RALLY_RUNTIME.md`.
- Fresh proof in this audit:
  `uv sync --dev` and `uv run pytest tests/unit -q` passed with `264 passed`.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- Run the planned fresh and fork `/exit` manual smoke on both adapters when a
  live authenticated environment is available and cost is acceptable.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-14
external_research_grounding: done 2026-04-14
deep_dive_pass_2: done 2026-04-14
phase_plan: done 2026-04-14
consistency_pass: done 2026-04-14
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> consistency pass -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

When this plan is complete, an operator will have one explicit Rally command to
start a diagnostic interview with an agent. That interview will let the
operator ask about the agent's instructions and confusion points without
letting the agent act on its normal task doctrine. Rally will support that
feature for both Codex and Claude. It will also provide a safe forked interview
path for both adapters without changing the saved live session id or the live
run's next normal resume path. The CLI for this feature will be simple,
first-class, and easy for a human to discover and use.

## 0.2 In scope

- Design one operator-visible Rally feature for diagnostic agent interviews.
- Keep that feature as a clean first-class Rally CLI path for human operators.
- Support both Codex and Claude in the shipped design.
- Keep the interview instructions in `.prompt` source so Rally still compiles
  the readback instead of writing ad hoc runtime markdown.
- Make the interview prompt point at the real instruction file and say in plain
  words that the agent must explain those instructions, not execute them.
- Design the safe boundary between a fresh diagnostic interview and a forked
  diagnostic interview from a saved session.
- Research real Codex capabilities from `~/workspace/codex`.
- Research real Claude capabilities from the Claude CLI and, if needed,
  external source material.
- Define where diagnostic transcripts, launch facts, and session references
  live inside the run tree.

## 0.3 Out of scope

- Mutating a live run in place while the operator experiments with the agent.
- Hidden debugger state outside `runs/`.
- Runtime-written `AGENTS.md` files or other instruction sidecars that bypass
  Doctrine source.
- Guessing unsupported agent state that the adapter cannot really expose.
- Shipping a one-adapter-only version of this feature.
- Broad new agent-debugging features that are not needed for instruction
  interviews or safe session forking.

## 0.4 Definition of done (acceptance evidence)

- This plan is confirmed and later made decision-complete.
- The chosen CLI path is simple, first-class, and fits naturally with the rest
  of Rally's operator commands.
- Rally can open one Rally-owned chat session that uses compiled prompt source
  and clearly tells the agent not to do normal work.
- Rally supports that interview path for both Codex and Claude.
- The diagnostic chat writes its own transcript, prompt copy, launch proof, and
  session record under the run tree without changing the live run's normal turn
  state.
- Proof shows Rally can fork a saved session for both Codex and Claude into
  interview mode and still resume the original run normally afterward.
- Rally ships one deep operator-facing debugging guide for this feature at
  `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md`.
- `README.md`, the CLI/logging doc, and the master design doc all link a
  reader to that debugging guide when this feature ships.
- The master design, CLI/logging doc, debugging guide, and runtime doc stay
  aligned if the shipped run contract changes.

## 0.5 Key invariants (fix immediately if violated)

- No live session mutation during a diagnostic interview.
- No second instruction path outside prompt source.
- No hand-edited compiled `AGENTS.md`.
- Diagnostic interviews are outside Rally's turn engine. They do not hand off
  work, mark work done, advance the live run, or ask for a Rally final JSON.
- The override text must make the interview mode obvious enough that the agent
  cannot mistake it for a normal work turn.
- Human operators should not need adapter-specific knowledge just to start a
  diagnostic interview.
- Do not guess what Codex or Claude can do; use real feature evidence.
- No fallbacks or silent mode switches.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Protect the live run first.
2. Make the CLI path simple and natural for humans.
3. Support both Codex and Claude.
4. Keep prompt-source ownership honest.
5. Reuse the current run-home and session model where it fits.
6. Keep adapter limits honest instead of papering over them.

## 1.2 Constraints

- `src/rally/services/runner.py` builds each turn from compiled `AGENTS.md`
  plus runtime prompt inputs.
- `src/rally/adapters/codex/adapter.py` reuses a saved session id when Rally
  resumes a Codex-backed agent.
- `src/rally/services/home_materializer.py` keeps run-owned files under one
  prepared home and one `home/sessions/<agent>/` tree.
- `src/rally/services/home_materializer.py` copies whole compiled agent
  directories into `home/agents/<slug>/`, so a generated interview sidecar can
  ride that same sync path.
- `materialize_run_home(...)` is issue-gated and setup-heavy today. A
  diagnostic command cannot blindly inherit that path because explaining
  doctrine should not force a normal work-start preflight.
- Phase 3 and the repo `AGENTS.md` both say Rally should keep one final control
  path and should not move instruction prose into runtime files.
- Section 3 and the public Claude CLI both show `--fork-session`; the current
  Rally Claude path still only uses `--resume`.
- The user requires support for both Codex and Claude, so research cannot stop
  at a one-adapter design.

## 1.3 Architectural principles (rules we will enforce)

- Prompt source owns the interview doctrine. Runtime only chooses how to launch
  it.
- The CLI should expose one clean mental model even when adapters differ under
  the hood.
- Fresh interview and forked interview should look like one feature to the
  operator across both adapters.
- A diagnostic path must fail loud when Rally cannot prove safety.
- A diagnostic chat is not a Rally work turn. Do not overload `TurnResult`,
  `final_response_loader`, or run-state routing to fake one.
- Keep all durable truth for this feature under the run tree.
- Prefer the smallest new operator surface that makes the behavior obvious.

## 1.4 Known tradeoffs (explicit)

- A fresh interview is safer and easier, but it does not capture live session
  state.
- A forked interview is more useful for mid-run debugging, but Rally has to
  prove it for both adapters instead of assuming feature parity.
- A stronger override prompt may feel blunt, but weak wording is a bigger risk
  because the agent might slip back into normal work mode.
- Codex will likely need a wider diagnostic-only integration boundary than
  Claude, because the current `codex exec` path does not expose a safe fork
  plus instruction-override surface.
- Claude and Codex do not share one native chat transport. Rally has to hide
  that split behind one command without pretending the transports are the same.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Rally builds one normal agent prompt from compiled `AGENTS.md` and optional
  runtime prompt inputs.
- Rally stores one saved session id per agent and uses that id again on normal
  resume.
- The live operator commands are `rally run` and `rally resume`; neither one is
  shaped for a read-only interview about doctrine.
- Rally already keeps run-owned logs, sessions, and launch proof in the run
  tree.

## 2.2 What’s broken / missing (concrete)

- There is no clean operator path for "talk to this agent about its
  instructions."
- There is no authored interview doctrine that clearly says "ignore your normal
  task instructions and explain them instead."
- There is no safe fork story for asking a live agent what is going on without
  risking the real saved session.
- Rally does not yet have a proven dual-adapter story for this feature.
- The current runtime path would push operators toward ad hoc prompt stubs or
  unsafe resume experiments.

## 2.3 Constraints implied by the problem

- The fix has to split cleanly between prompt source, runtime launch logic,
  session handling, and proof.
- Normal flow execution must keep working the same way when this feature is not
  used.
- Adapter limits have to shape the feature instead of being hidden behind fake
  parity.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- Anthropic Claude Code CLI reference —
  https://code.claude.com/docs/en/cli-reference — adopt the public Claude
  flags that matter here: `-p`, `--resume`, `--fork-session`,
  `--append-system-prompt`, `--system-prompt`, `--bare`, `--json-schema`, and
  `--output-format`; reject any Rally design that assumes Claude fork or
  instruction override needs hidden internals when the public CLI already
  exposes those controls.
- Anthropic Claude Code settings reference —
  https://code.claude.com/docs/en/settings — adopt the warning that
  `CLAUDE.md` and settings are ambient startup inputs, and reject ambient
  `CLAUDE.md` discovery for Rally diagnostic turns when Rally needs one clean
  prompt graph and no side-door instructions.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/runner.py:708-744` — Rally builds one prompt, invokes
    the adapter with that prompt plus the saved session when present, then
    rewrites the saved session id from the adapter result. A diagnostic path has
    to protect that live session write.
  - `src/rally/services/runner.py:1044-1057` — the current prompt is exactly
    compiled `home/agents/<slug>/AGENTS.md` plus optional runtime prompt
    inputs. That is the canonical Rally instruction path today.
  - `src/rally/services/runner.py:1140-1179` — runtime prompt inputs already
    get `RALLY_RUN_HOME`, `RALLY_ISSUE_PATH`, `RALLY_RUN_ID`,
    `RALLY_WORKSPACE_DIR`, and agent identity. Rally already has a native way
    to add grounded diagnostic context without inventing a second note file.
  - `stdlib/rally/prompts/rally/base_agent.prompt:10-98` — the shared Rally
    base prompt binds run identity, final JSON rules, and `home:issue.md`.
    Diagnostic interview doctrine has to preserve those core Rally boundaries
    while disabling normal work behavior.
  - `src/rally/cli.py:30-59` — Rally's current human-facing run control is just
    `run` and `resume` with a small explicit modifier surface. There is no
    diagnostic operator path yet.
  - `src/rally/adapters/base.py:200-248` — one shared session file per agent
    slug is the current source of truth for saved adapter session ids. Any safe
    fork design must avoid clobbering that file for the live run.
  - `src/rally/adapters/registry.py:9-24` — the shared adapter boundary is now
    real and only `codex` plus `claude_code` are supported. The interview
    feature should land on that shared boundary, not in flow-specific glue.
  - `src/rally/adapters/codex/adapter.py:213-237` — Rally's current Codex path
    is non-interactive `codex exec`; resumed turns use `codex exec resume
    <session-id> -`. There is no fork path in the current Rally adapter.
  - Local Codex CLI probe on 2026-04-14 — `codex exec resume --help` accepts a
    prompt plus `--ephemeral`, `--json`, and `--output-last-message`, but it
    does not expose any fork flag on the non-interactive `exec` surface.
  - `/Users/aelaguiz/workspace/codex/codex-rs/cli/src/main.rs:140-265` —
    current Codex does have top-level `codex resume` and `codex fork`
    interactive commands, so fork is a real product capability even though
    Rally's current adapter path does not use it.
  - Local Codex CLI probe on 2026-04-14 — `codex fork --help` accepts
    `SESSION_ID` and an optional `PROMPT`, but it is the interactive TUI path,
    not the current `codex exec` automation path Rally uses.
  - `/Users/aelaguiz/workspace/codex/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartParams.ts:12-24`
    — lower-level Codex thread start already supports `baseInstructions` and
    `developerInstructions`.
  - `/Users/aelaguiz/workspace/codex/codex-rs/app-server-protocol/schema/typescript/v2/ThreadResumeParams.ts:12-43`
    — lower-level Codex thread resume also supports `baseInstructions` and
    `developerInstructions`.
  - `/Users/aelaguiz/workspace/codex/codex-rs/app-server-protocol/schema/typescript/v2/ThreadForkParams.ts:10-34`
    — lower-level Codex thread fork supports forking by thread id and also
    supports `baseInstructions`, `developerInstructions`, and `ephemeral`.
    Codex can do the needed shape internally; the open question is which
    surfaced path Rally should use.
  - `src/rally/adapters/claude_code/adapter.py:153-179` — Rally's current
    Claude path is `claude -p ... --json-schema ...` with `--resume` when a
    saved session exists. It does not yet use `--fork-session`, `--bare`,
    `--append-system-prompt`, or `--system-prompt`.
  - Local Claude CLI probe on 2026-04-14 plus official docs — the public Claude
    CLI already exposes `-p`, `--resume`, `--fork-session`,
    `--append-system-prompt`, `--system-prompt`, `--bare`, `--json-schema`, and
    `--output-format`. Claude gives Rally a real public fork-and-override path
    today.
- Canonical path / owner to reuse:
  - `src/rally/cli.py` + `src/rally/services/runner.py` +
    `src/rally/adapters/base.py` + the adapter implementations — this is the
    owned path for operator-facing commands, prompt assembly, session storage,
    and adapter-specific launch rules. The interview feature should converge
    here.
- Existing patterns to reuse:
  - `src/rally/cli.py:46-59` and `src/rally/services/runner.py:117-176` —
    `rally resume` already uses one simple command plus a small modifier
    surface. That is the closest human-facing CLI pattern for a simple
    interview command.
  - `src/rally/services/runner.py:734-744` plus
    `src/rally/adapters/base.py:219-236` — Rally already centralizes session-id
    persistence after each turn. That pattern should be reused for a separate
    forked diagnostic session record instead of mutating the live one.
  - `tests/unit/test_runner.py:351-416` and
    `tests/unit/test_runner.py:1525-1578` — Rally already has focused proof for
    Claude resume behavior and Codex saved-session reuse. Those tests are the
    right preservation surface for later refactors.
- Prompt surfaces / agent contract to reuse:
  - `src/rally/services/runner.py:1044-1057` — compiled `AGENTS.md` remains the
    canonical authored instruction readback.
  - `src/rally/services/runner.py:1140-1234` — runtime prompt inputs are the
    existing grounded add-on surface.
  - `stdlib/rally/prompts/rally/base_agent.prompt:82-102` — Rally-managed
    doctrine already says Rally owns the run home, the note path, and the final
    JSON. Interview mode should be an authored variant on top of that base, not
    a runtime markdown hack.
- Native model or agent capabilities to lean on:
  - Codex public non-interactive capability — `codex exec resume` can resume a
    saved session and accept a new prompt on stdin.
  - Codex internal capability — the checked-out Codex repo shows lower-level
    thread start, resume, and fork support with instruction overrides. If the
    public `exec` surface is too narrow, Codex still has a native fork
    primitive before Rally would need custom transcript cloning.
  - Claude public capability — the CLI can resume, fork on resume, append or
    replace system instructions, and run in `--bare` mode to suppress ambient
    startup context.
- Existing grounding / tool / file exposure:
  - `home/agents/<slug>/AGENTS.md` — Rally's compiled instruction readback for
    the current agent.
  - `RALLY_RUN_HOME`, `RALLY_ISSUE_PATH`, `RALLY_WORKSPACE_DIR`,
    `RALLY_RUN_ID`, and agent env vars from
    `src/rally/services/runner.py:1166-1176` — enough current context to point
    a diagnostic turn at the right run files.
  - `home/sessions/<agent>/session.yaml` through `src/rally/adapters/base.py`
    — the live saved session reference Rally must not overwrite accidentally.
- Duplicate or drifting paths relevant to this change:
  - Codex fork exists today on the interactive/app-server side, while Rally's
    Codex adapter is built on `codex exec`. That is the main current drift
    between desired behavior and the shipped adapter path.
  - Claude has both prompt-on-stdin and system-prompt flags. Rally needs one
    clear policy for how interview doctrine is injected so Codex and Claude do
    not drift into different instruction models.
- Capability-first opportunities before new tooling:
  - Use authored interview prompt source and runtime prompt inputs before any
    generated runtime stub.
  - Use Claude's public `--fork-session`, `--system-prompt` or
    `--append-system-prompt`, and `--bare` before inventing custom session-copy
    machinery.
  - Use Codex's native fork/resume primitives from the checked-out product
    before inventing transcript replay or session file duplication.
- Behavior-preservation signals already available:
  - `tests/unit/test_runner.py:351-416` — current Claude resume path and launch
    proof.
  - `tests/unit/test_runner.py:1525-1578` — current Codex saved-session resume
    path.
  - `tests/unit/test_cli.py:68-100` — current human CLI behavior around resume
    modifiers.

## 3.3 Decision gaps that must be resolved before implementation

None remain after deep-dive and phase planning. These decisions are now locked
for implementation:

- CLI shape — choose one new command:
  `rally interview <run-id> [--agent <slug>] [--fork]`. This keeps `run` and
  `resume` clean. The default target is the run's current agent. `--agent`
  overrides that. `--fork` means "fork the saved live session for that agent."
- Codex boundary — do not fake fork on `codex exec`. Keep normal Rally work
  turns on `codex exec`, but widen the diagnostic-only path to Codex's native
  thread start, resume, and fork support so Rally can set real override
  instructions on the diagnostic session.
- Instruction policy — compiled interview doctrine becomes the active
  instructions for the diagnostic session. The normal `AGENTS.md` stays on disk
  as the file being explained, not as live instructions for the interview.
  Runtime facts may name the target file path and the source live session id,
  but they do not author the interview doctrine.
- Closeout contract — diagnostic interviews are not Rally turns. They do not go
  through `TurnResult`, `final_response_loader`, or run-state routing. Rally
  owns the chat loop, transcript, and interview metadata instead.
- Prompt-build shape — emit one shared Rally-owned `INTERVIEW.md` sidecar into
  every compiled agent directory in this slice. Do not require per-flow
  interview prompts.
- Home-refresh shape — add one lighter diagnostic-home refresh path that syncs
  compiled agents, skills, MCPs, and adapter home files but skips issue
  readiness, flow setup, and run-state mutation.
- Message-loop shape — Claude can use repeated `claude -p` calls that resume
  the diagnostic session id after the first turn. Codex should use one
  Rally-owned `codex app-server` stdio client so Rally can create or fork the
  thread once and then send repeated `turn/start` messages on that diagnostic
  thread.
- Safety posture — diagnostic chat is read-only by boundary, not by trust
  alone. Claude should use `--bare` plus inspect-only tools. Codex should use a
  read-only sandbox and the same `CODEX_HOME=<run_home>` rule as normal turns.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `runs/<run-id>/home/agents/<agent>/AGENTS.md` is the only compiled
  instruction readback Rally uses today for real work turns.
- `runs/<run-id>/home/sessions/<agent>/session.yaml` is the one Rally-owned
  live session record per agent.
- `runs/<run-id>/home/sessions/<agent>/turn-<n>/` stores per-turn stdout,
  stderr, and final JSON files for the turn engine.
- `runs/<run-id>/logs/adapter_launch/turn-<n>-<agent>.json` stores launch
  proof for work turns only.
- `src/rally/services/home_materializer.py:288-300` copies whole compiled agent
  directories into `home/agents/`, so extra generated sidecars can already ride
  that path if Rally emits them.
- There is no `INTERVIEW.md`, no `home/interviews/`, and no run-owned
  transcript path for human diagnostic chat today.
- There is also no lighter "refresh prompts and adapter home only" helper.
  `materialize_run_home(...)` is the only full refresh path.

## 4.2 Control paths (runtime)

1. `rally run` and `rally resume` both resolve a flow and route into
   `src/rally/services/runner.py`.
2. `materialize_run_home(...)` prepares the run home, copies compiled agent
   directories, refreshes skills and MCPs, and lets the adapter refresh its own
   home files.
3. The runner loads the current live session from
   `home/sessions/<agent>/session.yaml`.
4. `_build_agent_prompt(...)` reads `home/agents/<agent>/AGENTS.md` and
   appends runtime prompt inputs.
5. `adapter.invoke(...)` runs one non-interactive turn and returns process
   output plus a session id.
6. The runner writes that session id back to the live session record, then
   loads the final JSON through `final_response_loader.py`.
7. The runner updates run state, issue history, and turn routing from that
   final JSON.

Adapter-specific reality today:

- Claude work turns are one-shot `claude -p` calls that return a `session_id`
  for later resume.
- Codex work turns are one-shot `codex exec` calls that return a `thread_id`
  for later resume.
- There is no shipped Rally chat loop that can send a second human question on
  a non-work session.

Current consequence:

- Every shipped path is shaped like a Rally work turn.
- Forcing diagnostic chat through that path would either overwrite the live
  session id, mutate run state, or require a fake diagnostic `TurnResult`.

## 4.3 Object model + key abstractions

- `RunRecord` and `RunState` describe normal run progress, not side chat.
- `FlowAgent` and `CompiledAgentContract` point to the normal compiled agent
  readback and final-output schema.
- `RallyAdapter`, `AdapterInvocation`, and `TurnArtifactPaths` are all turn
  shaped. They assume one prompt in, one process run, one final response out.
- `AdapterSessionRecord` is stored by agent slug only. There is no second store
  for forked or operator-owned diagnostic sessions.
- `flow_build.py` already has one sidecar pattern through `SOUL.prompt` and
  `SOUL.md`, but there is no interview sidecar today.
- The current sidecar build path is role-scoped and optional. There is no
  generic "emit one shared sidecar beside every compiled agent" helper yet.

## 4.4 Observability + failure behavior today

- Work turns already have launch proof, raw adapter stdout, stderr, rendered
  logs, and issue-ledger writes.
- Resume behavior is already covered in focused CLI and runner tests for both
  adapters.
- There is no transcript format for human chat with an agent.
- There is no diagnostic event code, interview banner, or saved prompt copy.
- There is no fail-loud operator path for "fork this agent safely." The only
  saved session record is the live one.
- There is no current proof that a read-only diagnostic surface can be started
  without tripping the normal issue-gated run-start rules.

## 4.5 UI surfaces (ASCII mockups, if UI work)

Current CLI surface:

```bash
rally run <flow>
rally resume <run-id> [--edit|--restart]
```

There is no first-class Rally command that means "open a read-only interview
with this agent."
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Add one generated interview sidecar beside every compiled agent readback:
  `flows/<flow>/build/agents/<agent>/INTERVIEW.md`.
- Emit that sidecar from one Rally-owned shared prompt source in this slice.
  Do not require every flow or role to author its own interview prompt just to
  get the feature.
- `home_materializer.py` keeps copying whole agent directories, so that same
  sidecar lands at `runs/<run-id>/home/agents/<agent>/INTERVIEW.md`.
- Add one Rally-owned diagnostic tree per run:
  `runs/<run-id>/home/interviews/<agent>/<interview-id>/`.
- Each interview directory stores:
  - `session.yaml` — adapter, target agent, mode (`fresh` or `fork`), live
    source session id when present, diagnostic session id, and timestamps.
  - `prompt.md` — the exact compiled interview readback plus grounded facts
    Rally used to start the session.
  - `transcript.jsonl` — ordered user and assistant messages.
  - `raw_events.jsonl` — adapter-native event stream when available.
  - `stderr.log` — adapter stderr for the chat.
  - `launch.json` — launch command or request facts that explain how the
    interview started.
- Keep `home/sessions/<agent>/session.yaml` as the live work-session record.
  The diagnostic tree never overwrites it.

## 5.2 Control paths (future)

1. Add one new command:
   `rally interview <run-id> [--agent <slug>] [--fork]`.
2. The command resolves the run, refuses archived runs, and chooses the target
   agent. If `--agent` is not passed, it uses the run's current agent. If the
   run has no current agent, Rally fails loud and asks for `--agent`.
3. The command uses a lighter diagnostic-home refresh path:
   - create the run home shell if needed
   - sync compiled agent directories so `AGENTS.md` and `INTERVIEW.md` are
     fresh
   - refresh stable skill views and adapter home files
   - skip issue readiness, flow setup, issue snapshots, and run-state writes
4. Rally loads `home/agents/<agent>/INTERVIEW.md`, appends grounded facts such
   as:
   - target agent key and slug
   - target doctrine file path
   - mode (`fresh` or `fork`)
   - live source session id when `--fork` is used
   - plain reminder that this chat must not change the live run
5. Rally creates `home/interviews/<agent>/<interview-id>/` and writes the
   launch metadata before the first model call.
6. Fresh mode:
   - start a new diagnostic session with the compiled interview readback as the
     active instructions
   - do not read or write the live session record
7. Fork mode:
   - load `home/sessions/<agent>/session.yaml`
   - fail loud if no live session exists
   - ask the adapter to fork that saved session into a new diagnostic session
   - set the compiled interview readback as the active override instructions
     for the forked session
   - never resume the live session in place
8. After the first question, Rally stays in one simple chat loop:
   - Claude path: each user message runs one `claude -p` call; after the first
     turn, Rally resumes the saved diagnostic `session_id`
   - Codex path: Rally keeps one `codex app-server` stdio session open; after
     the thread is started or forked, each user message becomes one native
     `turn/start` call on that diagnostic `thread_id`
   - both paths stream assistant output back to the human and append normalized
     messages to `transcript.jsonl`
9. Exiting the chat only closes the interview session record. It does not
   change `RunState`, write to `home:issue.md`, call `final_response_loader`,
   or touch the live session record.

## 5.3 Object model + abstractions (future)

- Keep the existing work-turn adapter contract intact. Do not overload
  `RallyAdapter.invoke(...)` or `AdapterInvocation` with chat-only behavior.
- Add a new diagnostic boundary owned by Rally runtime, with small shared types
  such as:
  - `InterviewRequest`
  - `InterviewSessionRecord`
  - `InterviewMessage`
  - `InterviewReply`
- Add one Rally-owned interview service that:
  - resolves the run and target agent
  - refreshes a diagnostic-safe run home
  - builds the diagnostic prompt
  - creates the interview artifact tree
  - owns the human chat loop
  - routes message exchange through the adapter-specific diagnostic client
- Claude diagnostic client:
  - use the public Claude CLI surface
  - run with `--bare` so Rally does not pick up ambient `CLAUDE.md` or hidden
    startup state
  - use inspect-only tools in this slice: `Read`, `Grep`, and `Glob`
  - use Claude's session controls for fresh and forked interview sessions
  - use the compiled interview readback as the system prompt for the first
    diagnostic turn, then resume the saved diagnostic `session_id`
- Codex diagnostic client:
  - keep normal Rally work turns on `codex exec`
  - widen only the diagnostic path to `codex app-server --listen stdio://` plus
    native `thread/start`, `thread/fork`, and `turn/start` because that path
    exposes real instruction overrides and repeated user turns
  - use the compiled interview readback as the active base or developer
    instructions when the diagnostic thread is created or forked
  - keep the diagnostic thread in read-only sandbox mode under the same
    `CODEX_HOME=<run_home>` and `cwd=<run_home>` boundary Rally already owns
  - do not rely on `codex exec` for fork, and do not rely on the top-level
    `codex fork` prompt arg alone to replace instructions

## 5.4 Invariants and boundaries

- Prompt source owns the interview doctrine. Runtime only adds grounded facts
  like target paths and source session ids.
- `INTERVIEW.md` is the live instruction surface for diagnostic chat.
  `AGENTS.md` is the file being explained.
- Diagnostic chat is not a Rally turn. It has no Rally final JSON, no
  `TurnResult`, no route changes, and no issue-ledger side effects.
- The live work-session record under `home/sessions/<agent>/session.yaml`
  remains the source of truth for normal `rally resume`.
- Diagnostic chat must be read-only with respect to Rally flow control and repo
  state. The adapter launch should use a read-only or inspect-only tool posture
  that Rally can actually prove for that adapter.
- Claude interviews must run in `--bare` mode with inspect-only tools.
- Codex interviews must keep the current Rally rule that ambient project-doc
  discovery stays off, compiled prompt text is injected directly, and the
  diagnostic thread stays inside a read-only sandbox.
- The first diagnostic turn is the only place that sets or replaces interview
  instructions. Later chat turns reuse the saved diagnostic session id or
  thread id instead of trying to mutate instructions mid-chat.
- There is no fallback from `--fork` to "resume the live session anyway." If
  safe fork is unavailable, Rally stops with one clear blocker.

## 5.5 UI surfaces (ASCII mockups, if UI work)

User-facing command shape:

```bash
rally interview DMO-1
rally interview DMO-1 --agent change_engineer
rally interview DMO-1 --fork
```

Chat banner:

```text
Rally Interview
Run: DMO-1
Agent: scope_lead
Adapter: codex
Mode: fork
Live session: session-1
Transcript: runs/DMO-1/home/interviews/scope_lead/<interview-id>/transcript.jsonl

Type your questions. Type /exit to leave.
```
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| CLI | `src/rally/cli.py` | `_build_parser`, new command handler | Only `run` and `resume` own run execution | Add `interview` as one first-class top-level command with `run_id`, optional `--agent`, and `--fork` | Human-friendly front door | `rally interview <run-id> [--agent <slug>] [--fork]` | `tests/unit/test_cli.py` |
| Interview service | `src/rally/services/interview.py` (new) | new service module | No Rally-owned chat service exists | Add run resolution, target-agent selection, prompt build, interview artifact writes, and chat loop | Keep diagnostics out of `runner.py` turn routing | `start_interview(...)`, `run_interview_chat(...)` | new interview service tests |
| Prompt source | `stdlib/rally/prompts/rally/interview_agent.prompt` (new) | shared interview doctrine | No authored interview doctrine exists | Add one Rally-owned interview prompt that says "explain this doctrine, do not follow it" | Keep doctrine in `.prompt` source | compiled `INTERVIEW.md` sidecar | `tests/unit/test_flow_build.py` |
| Flow build | `src/rally/services/flow_build.py` | sidecar build sweep | Builds `AGENTS.md` and optional `SOUL.md` sidecars only | Emit one shared `INTERVIEW.md` beside each compiled agent directory without requiring flow-owned interview prompts | Make interview prompt a generated readback, not a runtime stub | standard sidecar build path for shared interview sidecar | `tests/unit/test_flow_build.py` |
| Run home sync | `src/rally/services/home_materializer.py` | `_ensure_run_layout`, new diagnostic refresh helper, `_sync_compiled_agents` | Full materialization is issue-gated and setup-heavy | Reserve `home/interviews/` and add a lighter diagnostic refresh path that skips issue and setup gates | Keep interview truth under the run tree without inheriting work-turn blockers | `prepare_interview_home(...)` and `home/interviews/<agent>/<interview-id>/...` | runner/interview home tests |
| Shared adapter boundary | `src/rally/adapters/base.py` | current turn-only dataclasses and helpers | Shared adapter types assume turn execution only | Add a separate interview boundary and shared interview record helpers; do not overload `AdapterInvocation` | Keep work turns and chat sessions separate | interview-specific shared types and storage helpers | adapter contract tests |
| Claude interview path | `src/rally/adapters/claude_code/interview.py` (new) plus launcher/event helpers | no diagnostic client exists | Current Claude adapter only runs `claude -p` work turns with final JSON | Add fresh and forked diagnostic chat using `--bare`, inspect-only tools, `--resume`, and `--fork-session` | Claude already exposes the needed public controls | first turn seeds diagnostic session, later turns resume saved diagnostic `session_id` | `tests/unit/test_runner.py`, `tests/unit/test_claude_code_launcher.py`, new Claude interview tests |
| Codex interview path | `src/rally/adapters/codex/interview.py` (new) plus JSON-RPC transport helper | no diagnostic client exists | Current Codex adapter only runs `codex exec` work turns and cannot fork there | Add diagnostic-only `codex app-server` stdio client with native `thread/start`, `thread/fork`, and `turn/start` calls | Safe fork plus repeated chat needs a wider native boundary than `codex exec` | first turn creates or forks diagnostic thread; later turns use saved diagnostic `thread_id` | `tests/unit/test_runner.py`, `tests/unit/test_launcher.py`, new Codex interview tests |
| Session storage | `src/rally/adapters/codex/session_store.py`, `src/rally/adapters/claude_code/session_store.py`, or new interview store module | current live session record | Stores one live session record per agent only | Keep live record untouched and store diagnostic session records under `home/interviews/` | Normal resume must stay stable | separate live vs diagnostic session records | session-store tests |
| Prompt and final-response helpers | `src/rally/services/runner.py`, `src/rally/services/final_response_loader.py` | `_build_agent_prompt`, final JSON load path | Work turns always build `AGENTS.md` and parse final JSON | Extract only safe shared helpers if needed; do not route interviews through final JSON loading | Diagnostic chat is not a turn | shared prompt-copy helper only, no diagnostic `TurnResult` | runner preservation tests |
| Logging | `src/rally/services/run_events.py`, `src/rally/adapters/claude_code/event_stream.py`, `src/rally/adapters/codex/event_stream.py`, and launch-record helpers | turn launch events only | No interview launch or message event codes | Add interview launch, close, and normalized message events without touching turn state | Keep archaeology bundled and readable | interview lifecycle event codes and transcript normalization | event/log tests |
| Docs | `README.md`, `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md` (new), `docs/RALLY_CLI_AND_LOGGING.md`, `docs/RALLY_MASTER_DESIGN.md`, `docs/RALLY_COMMUNICATION_MODEL.md`, `docs/RALLY_RUNTIME.md` | live design, command, and operator docs | No interview command, diagnostic run tree, or deep debugging guide is documented in the current canonical docs | Add the deep debugging guide, link it from `README.md`, and update command shape, artifact paths, safety rules, and adapter support truth in the live docs | Avoid stale runtime truth and make the feature discoverable and usable without code archaeology | doc sync in same pass as code plus explicit README-to-guide links | doc checks plus focused tests |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  `rally interview` -> `src/rally/services/interview.py` -> shared interview
  adapter boundary -> adapter-specific diagnostic client -> run-owned interview
  artifacts under `home/interviews/`.
- Deprecated APIs (if any):
  None on the public `run` and `resume` path. The main rule is "do not overload
  the turn engine."
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - any runtime-written interview stub `AGENTS.md`
  - any fake diagnostic final JSON schema or `TurnResult`
  - any attempt to reuse `home/sessions/<agent>/session.yaml` for diagnostic
    session ids
  - any `codex exec` fork hack that pretends fork exists where it does not
- Capability-replacing harnesses to delete or justify:
  - reject transcript replay as a fork substitute
  - reject copying live adapter session files into a second fake "forked"
    session
  - justify the Rally-owned chat loop only as a thin human I/O bridge over
    native session and instruction controls
- Live docs/comments/instructions to update or delete:
  - `README.md`
  - `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md`
  - `docs/RALLY_CLI_AND_LOGGING.md`
  - `docs/RALLY_MASTER_DESIGN.md`
  - `docs/RALLY_COMMUNICATION_MODEL.md`
  - `docs/RALLY_RUNTIME.md`
- Behavior-preservation signals for refactors:
  - `tests/unit/test_cli.py` for command shape
  - `tests/unit/test_runner.py:351-416` for Claude resume preservation
  - `tests/unit/test_runner.py:1525-1578` for Codex saved-session preservation
  - flow-build proof that `INTERVIEW.md` is generated and copied beside
    `AGENTS.md`
  - proof that `rally interview` can refresh a run home without requiring a
    normal issue-ready gate

## 6.3 Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Prompt sidecars | `src/rally/services/flow_build.py`, `flows/*/build/agents/*` | Standard sidecar build sweep for `INTERVIEW.md` beside `AGENTS.md` | Keeps interview doctrine in the same generated-readback world as other agent sidecars | include |
| Run-owned chat artifacts | `src/rally/services/home_materializer.py`, `home/interviews/` | Separate interview artifact tree from live `home/sessions/` plus a diagnostic-safe home refresh | Prevents diagnostic state from drifting into live run state and prevents issue-gated run blockers from leaking into doctrine chat | include |
| Adapter boundaries | `src/rally/adapters/base.py`, adapter-specific interview modules | Keep work-turn adapter path separate from diagnostic chat path | Prevents `invoke(...)` from becoming a mixed turn/chat catch-all | include |
| Codex integration | `src/rally/adapters/codex/*` | Keep `codex exec` for work turns; use `codex app-server` thread and turn APIs only for diagnostic chat | Prevents unsafe fake fork support on the wrong surface and gives Rally a real chat transport | include |
| Claude launch rules | `src/rally/adapters/claude_code/*` | Always use `--bare` plus inspect-only tools for interviews | Prevents ambient `CLAUDE.md` drift and tool-surface drift on diagnostic chat | include |
| Turn-result routing | `src/rally/services/final_response_loader.py`, `stdlib/rally/prompts/rally/turn_results.prompt` | Keep diagnostic chat out of final JSON routing | Prevents a second fake turn-ending control path | exclude |
| Run docs | master design, CLI/logging, Phase 3, Phase 4 docs | Keep interview command, run-tree artifacts, and safety rules aligned in one doc pass | Prevents stale operator truth | include |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 - Build the shared interview readback and diagnostic-home seam

Status: COMPLETE

Completed work:
- Added the shared interview doctrine source at
  `stdlib/rally/prompts/rally/interview_agent.prompt` and mirrored it into the
  bundled built-ins.
- `ensure_flow_assets_built(...)` now renders `INTERVIEW.md` beside each
  compiled `AGENTS.md` and removes stale interview sidecars from non-agent
  directories.
- `prepare_interview_home(...)` now creates a diagnostic-ready run home and
  skips the normal issue-ready, setup, snapshot, and run-state mutation path.
- Added shared interview artifact and session helpers in
  `src/rally/adapters/base.py` for later adapter work.

* Goal:
  Land the prompt-source and run-home foundations so Rally can explain doctrine
  without touching the work-turn engine or tripping normal issue/setup gates.
* Work:
  Add `stdlib/rally/prompts/rally/interview_agent.prompt` as the one shared
  Rally-owned interview doctrine source.
  Update `src/rally/services/flow_build.py` to emit `INTERVIEW.md` beside every
  compiled agent directory through one shared sidecar path, and remove stale
  `INTERVIEW.md` files when an agent directory disappears.
  Update `src/rally/services/home_materializer.py` to create `home/interviews/`
  and add a lighter `prepare_interview_home(...)` refresh path that syncs
  compiled agent directories, stable skill views, MCPs, and adapter home files
  while skipping issue readiness, flow setup, issue snapshots, and run-state
  writes.
  Add shared interview record and artifact helpers at the owning boundary
  instead of trying to reuse `TurnArtifactPaths` or the live session store.
* Verification (required proof):
  Add focused `tests/unit/test_flow_build.py` coverage that proves
  `INTERVIEW.md` is emitted and copied beside `AGENTS.md`.
  Add focused home-materializer tests that prove the diagnostic refresh path
  works without a non-empty `home/issue.md` and does not mutate run state.
  Keep `uv run pytest tests/unit -q` green.
* Docs/comments (propagation; only if needed):
  Add one short code comment at the new diagnostic-home helper if the split
  from full materialization would otherwise be easy to collapse later.
* Exit criteria:
  Rally can generate and refresh the interview readback and interview artifact
  tree without invoking the normal work-turn startup path.
* Rollback:
  Revert the interview sidecar emission and diagnostic-home helper together so
  Rally falls back to the current pre-change home model cleanly.

## Phase 2 - Ship the shared `rally interview` command and fresh Claude path

Status: DONE

Completed work:
- Added the top-level `rally interview <run-id> [--agent <slug>] [--fork]`
  command and routed it into `src/rally/services/interview.py`.
- The shared interview service now resolves the target agent, writes
  `prompt.md`, `session.yaml`, `launch.json`, `transcript.jsonl`, and
  `raw_events.jsonl`, and owns the human chat loop outside `runner.py`.
- Added `src/rally/adapters/claude_code/interview.py` for the Claude diagnostic
  path with `--bare`, inspect-only tools, first-turn system prompt injection,
  and saved diagnostic session reuse on later questions.
- Added focused CLI and interview tests that prove fresh Claude interviews
  write run-owned artifacts and leave the live work-session record untouched.
- Claude `--fork` also landed cleanly on `--resume <live-session>
  --fork-session`, so the live `home/sessions/<agent>/session.yaml` stays
  unchanged even before the Codex half is done.
- Moved `launch.json` to the pre-launch boundary so the first adapter call now
  has a saved launch record before the model starts.
- Added shared interview `USER`, `LAUNCH`, `ASSIST`, and `CLOSE` rows in the
  normal run log.
- Fresh and forked Claude interviews now stream assistant text live through
  the shared chat loop.

* Goal:
  Deliver the operator-facing command and one fresh diagnostic chat path on the
  simplest public native capability surface first.
* Work:
  Add `rally interview <run-id> [--agent <slug>] [--fork]` to `src/rally/cli.py`
  and route it into a new `src/rally/services/interview.py`.
  In that service, resolve the target agent, build `prompt.md`, create
  `session.yaml`, `launch.json`, `transcript.jsonl`, and `raw_events.jsonl`,
  and own the human chat loop outside `runner.py`.
  Implement `src/rally/adapters/claude_code/interview.py` so fresh interviews
  use `claude -p` with `--bare`, inspect-only tools, the compiled interview
  readback as the system prompt, and saved diagnostic `session_id` reuse after
  the first turn.
  Normalize Claude event stream output into the shared transcript shape and
  keep the live `home/sessions/<agent>/session.yaml` untouched.
* Verification (required proof):
  Add focused CLI tests in `tests/unit/test_cli.py` for the new command and
  target-agent resolution rules.
  Add focused Claude interview tests that prove:
  fresh launch writes interview artifacts,
  later questions resume the diagnostic `session_id`,
  and the live work-session record is unchanged.
  Keep existing Claude resume coverage and `uv run pytest tests/unit -q` green.
* Docs/comments (propagation; only if needed):
  Add one short comment at the shared interview service if the separation from
  the turn engine would otherwise be non-obvious.
* Exit criteria:
  `rally interview` works end to end for fresh Claude interviews, writes the
  run-owned transcript artifacts, and does not change live run state.
* Rollback:
  Revert the CLI command, interview service, and Claude interview client
  together rather than leaving a partial operator surface behind.

## Phase 3 - Add the fresh Codex interview path on native thread and turn APIs

Status: DONE

Completed work:
- Added `src/rally/adapters/codex/interview.py` with the minimum owned
  JSON-RPC stdio client for `codex app-server --listen stdio://`.
- The shared interview service now opens a Codex diagnostic client instead of
  rejecting non-Claude adapters.
- Fresh Codex interviews now create one diagnostic thread with `thread/start`
  and keep later questions on that saved `thread_id`.
- The Codex diagnostic path reuses Rally's normal `CODEX_HOME=<run_home>`
  launch rule, keeps the interview in read-only sandbox mode, and leaves the
  normal `codex exec` work-turn path alone.
- Codex diagnostic turns now stream assistant text from app-server delta
  notifications into the shared operator chat loop.
- The shared interview event surface now covers Codex fresh interviews too.

* Goal:
  Make fresh Codex interviews real on the native Codex session surface without
  changing the shipped `codex exec` work-turn path.
* Work:
  Shipped as planned.
* Verification (required proof):
  - `uv run pytest tests/unit/test_interview.py -q`
  - `uv run pytest tests/unit/test_workspace.py tests/unit/test_cli.py tests/unit/test_interview.py tests/unit/test_launcher.py tests/unit/test_runner.py -q`
  - `uv run pytest tests/unit -q`
* Docs/comments (propagation; only if needed):
  Added one short code comment at the Codex transport boundary that says the
  wider app-server client is diagnostic-only and does not replace `codex exec`
  work turns.
* Exit criteria:
  Met.
* Rollback:
  Remove the Codex diagnostic client and transport helper together while
  keeping the shared command and Claude path intact.

## Phase 4 - Add safe fork support and live-session protection on both adapters

Status: DONE

Completed work:
- Claude fork support still runs on `--resume <live-session> --fork-session`.
- Codex fork support now runs on native `thread/fork`.
- The shared interview service now stores only diagnostic session records under
  `home/interviews/...` and keeps the live `home/sessions/<agent>/session.yaml`
  record untouched.
- Forked diagnostic chat on both adapters now stays on the saved diagnostic
  session or thread after the first answer.
- Forked Claude and Codex interviews now use the same live streamed-output loop
  and the same normalized interview event writes as fresh interviews.

* Goal:
  Make `--fork` real for both adapters while keeping the live saved session as
  the source of truth for later `rally resume`.
* Work:
  Shipped as planned.
* Verification (required proof):
  - `uv run pytest tests/unit/test_interview.py -q`
  - `uv run pytest tests/unit/test_workspace.py tests/unit/test_cli.py tests/unit/test_interview.py tests/unit/test_launcher.py tests/unit/test_runner.py -q`
  - `uv run pytest tests/unit -q`
* Docs/comments (propagation; only if needed):
  The code path stays small enough that no extra split comment was needed
  beyond the shared interview-service and Codex diagnostic boundary comments.
* Exit criteria:
  Met.
* Rollback:
  Revert fork support on both adapters and restore `--fork` to a loud blocker
  rather than risking live-session mutation.

## Phase 5 - Sync live docs and close with final proof

Status: DONE

Completed work:
- Added the deep operator guide at
  `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md`.
- Linked that guide from `README.md`,
  `docs/RALLY_MASTER_DESIGN.md`,
  `docs/RALLY_CLI_AND_LOGGING.md`,
  `docs/RALLY_COMMUNICATION_MODEL.md`, and
  `docs/RALLY_RUNTIME.md`.
- Synced the live docs so they now all say the same thing about
  `rally interview`, `home/interviews/`, and the rule that interview chat
  stays outside Rally's turn engine.
- Restored the planned front-door proof path by teaching
  `src/rally/services/workspace.py` to fall back to the repo-root `rally`
  wrapper when an editable venv is missing a generated entrypoint.
- Re-cold-read and tightened the operator docs so they now also say that
  interview replies stream live and that Rally writes normalized interview rows
  into `logs/events.jsonl`.

* Goal:
  Align the surviving live docs with the shipped command, artifact layout,
  adapter support truth, and operator-debugging story, then finish with the
  real proof set.
* Work:
  Shipped for the guide, README links, live-doc sync, and the front-door proof
  path fix.
* Verification (required proof):
  - `uv sync --dev`
  - `uv run pytest tests/unit/test_interview.py -q`
  - `uv run pytest tests/unit/test_workspace.py tests/unit/test_cli.py tests/unit/test_interview.py tests/unit/test_launcher.py tests/unit/test_runner.py -q`
  - `uv run pytest tests/unit -q`
  - Cold-read the updated docs against the shipped code and saved proof outputs
    from `tests/unit/test_interview.py`
  - Manual CLI smoke on live authenticated adapters was not run in this pass
    and remains a non-blocking follow-up
* Docs/comments (propagation; only if needed):
  This phase owned the live-doc reality sync, the new debugging guide, and the
  README links.
* Exit criteria:
  Met for code and live docs. Manual smoke remains a non-blocking follow-up.
* Rollback:
  Revert the live-doc sync as a group if the shipped runtime contract changes
  again before merge.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- `tests/unit/test_flow_build.py` proves `INTERVIEW.md` is generated beside
  `AGENTS.md`.
- Home-materializer coverage proves the diagnostic-home refresh path works
  without the normal issue-ready gate and without run-state mutation.
- CLI coverage proves `rally interview` parsing and target-agent resolution.
- Interview-service coverage proves `prompt.md`, `launch.json`, `session.yaml`,
  and transcript files land under `home/interviews/` instead of live
  `home/sessions/`.
- Claude interview tests prove fresh launch, transcript writes, and diagnostic
  `session_id` reuse.
- Codex interview tests prove fresh thread start, later `turn/start` use of the
  saved diagnostic `thread_id`, and preservation of the normal `codex exec`
  work-turn path.
- Fork tests for both adapters prove the live saved session record stays
  unchanged.

## 8.2 Integration tests (flows)

- One Claude-backed run can start a fresh interview, exit, and then resume
  normal work on the same live run.
- One Codex-backed run can start a fresh interview through the app-server
  client, exit, and then resume normal work on the same live run.
- One Claude-backed run can fork a saved live session into interview mode and
  leave the original resume path intact.
- One Codex-backed run can fork a saved live thread into interview mode and
  leave the original resume path intact.
- Each integration proof should inspect `home/interviews/<agent>/<interview-id>/`
  so transcript, prompt copy, launch facts, and diagnostic session record are
  all present.

## 8.3 E2E / device tests (realistic)

- Manual CLI smoke for `rally interview <run-id>` and
  `rally interview <run-id> --fork` on both adapters.
- Manual check that the interview answers explain doctrine instead of acting
  like a normal work turn.
- Manual check that `/exit` leaves the live run resumable and leaves no new
  `home:issue.md` or run-state side effects.
- Manual check that the shared CLI feels natural even though Claude and Codex
  use different native transports under the hood.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

Ship this behind one explicit top-level Rally command:
`rally interview <run-id> [--agent <slug>] [--fork]`.
Normal `run` and `resume` behavior should stay unchanged unless the operator
asks for diagnostics.

## 9.2 Telemetry changes

Record interview launch, close, and normalized message events plus enough
launch facts to show diagnostic mode, target agent, source live session id
when relevant, and whether Rally used fresh launch or safe fork on Codex or
Claude.

## 9.3 Operational runbook

The runbook should tell the operator when to use a fresh interview, when to use
`--fork`, what clear blocker messages can stop `--fork`, and how to tell that
the live run is still safe to resume, all in simple Rally CLI terms. The new
debugging guide should be the deep how-to document for this feature, and the
README plus live docs should route readers to it instead of making them dig
through architecture plans.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator cold read 1, self-integrator cold read 2
- Scope checked:
  - frontmatter, TL;DR, and planning-pass state
  - North Star, research grounding, target architecture, and call-site audit
  - phase plan, verification, rollout, and decision log alignment
  - helper-block drift and implementation readiness
- Findings summary:
  - the planning-pass tracker still skipped `consistency-pass`
  - Section 3 lacked an explicit "no remaining decision gaps" readiness read
  - rollout text was still looser than the chosen `rally interview` command
  - Phase 5 proof and telemetry text needed to match the interview artifact
    and event ownership already chosen elsewhere in the doc
- Integrated repairs:
  - marked `consistency_pass: done 2026-04-14` and fixed the recommended stage
    order
  - turned Section 3.3 into an explicit "no remaining decision gaps" surface
    while keeping the locked implementation decisions
  - tightened rollout, telemetry, and runbook text to the chosen command and
    fail-loud fork behavior
  - aligned Phase 5 proof with the required `home/interviews/...` archaeology
- Remaining inconsistencies:
  - none
- Unresolved decisions:
  - none
- Unauthorized scope cuts:
  - none
- Decision-complete:
  - yes
- Decision: proceed to implement? yes
<!-- arch_skill:block:consistency_pass:end -->

# 10) Decision Log (append-only)

## 2026-04-14 - Keep interview doctrine in prompt source

Context

The user asked for a stub `AGENTS.md` style interview mode so they can talk to
an agent about its real instructions without triggering normal behavior.

Options

- Write interview instructions at runtime as a one-off stub.
- Keep interview instructions in `.prompt` source and let Rally choose that
  readback at launch.

Decision

Keep interview doctrine in prompt source. Rally may choose and launch a
diagnostic readback, but it should not author runtime markdown instructions.

Consequences

- The feature stays inside Rally's existing prompt-source rule.
- Prompt and runtime work both matter for this change.
- If current Doctrine structure cannot express the interview prompt cleanly, the
  plan must name that gap instead of hiding it with a runtime patch.

Follow-ups

- Research the cleanest prompt-source shape for interview mode.
- Deep-dive the runtime path that selects it.

## 2026-04-14 - Support both Codex and Claude

Context

The user clarified that this feature must support both Codex and Claude and
that the design should research the real feature set for each one before
locking the runtime shape.

Options

- Ship one adapter first and leave the other for later.
- Make dual-adapter support a core requirement and research both before deeper
  planning.

Decision

Make dual-adapter support a core requirement. Research Codex from
`~/workspace/codex` and research Claude from the CLI and, if needed, external
sources before the deeper design pass.

Consequences

- The plan cannot hide behind one-adapter assumptions.
- Research is now a required next stage, not a nice-to-have.
- The final CLI should still feel like one Rally feature even if adapter
  internals differ.

Follow-ups

- Run the `research` stage against both adapter surfaces.
- Keep the CLI mental model simple while the implementation honors real adapter
  facts.

## 2026-04-14 - Protect the live run by default

Context

The user wants to ask live agents questions without destroying the running
session or taking it in strange directions.

Options

- Resume the live session in place and hope the override prompt is enough.
- Treat diagnostics as a separate fresh or forked path that must not change the
  live run.

Decision

Treat diagnostics as a separate path. The live run must stay safe to resume
normally after diagnostic work.

Consequences

- Rally needs explicit session and artifact handling for diagnostics.
- Fork support must be adapter-gated and proven.
- A fresh interview path is likely the first safe slice.

Follow-ups

- Research which adapters can really fork.
- Deep-dive where diagnostic session references and transcripts should live.

## 2026-04-14 - Make diagnostics a separate `rally interview` chat command

Context

Research showed that every shipped Rally path today is a work turn with one
final JSON result, one live session record, and one run-state update path.
That shape does not fit a human diagnostic chat.

Options

- Force interviews through `rally resume` and fake a special turn shape.
- Add one new Rally command that owns a separate diagnostic chat path.

Decision

Add one new first-class command:
`rally interview <run-id> [--agent <slug>] [--fork]`.
This command owns its own prompt copy, transcript, and session record under the
run tree and stays outside Rally's normal turn engine.

Consequences

- The operator gets one simple front door for fresh and forked interviews.
- Rally does not need a fake diagnostic `TurnResult`.
- The implementation should add a small interview service instead of bloating
  `runner.py`.

Follow-ups

- Add the interview artifact tree under `home/interviews/`.
- Keep the live `home/sessions/<agent>/session.yaml` record untouched.

## 2026-04-14 - Keep `codex exec` for work turns and widen only the Codex diagnostic path

Context

Codex research showed a real mismatch: Rally's current work-turn path uses
`codex exec`, which can resume but does not expose fork. The checked-out Codex
repo does expose thread start, resume, and fork with instruction overrides at a
lower native layer.

Options

- Try to fake diagnostic fork on `codex exec`.
- Use the top-level interactive `codex fork` prompt path and hope that one user
  prompt is strong enough to replace instructions.
- Keep work turns on `codex exec` and widen only the diagnostic path to native
  Codex thread APIs that can set real override instructions.

Decision

Keep normal Rally work turns on `codex exec`. Widen only the diagnostic path to
Codex's native thread start, resume, and fork support so Rally can launch
interview sessions with real override instructions instead of a weak prompt
hack.

Consequences

- The shipped run path stays stable for normal work.
- Codex diagnostic support will need a dedicated adapter-side client instead of
  reuse of `invoke(...)`.
- The design stays honest about the current public `exec` limit.

Follow-ups

- Phase-plan the new Codex diagnostic client separately from normal work-turn
  execution.
- Prove that forked diagnostic sessions leave the live saved session untouched.

## 2026-04-14 - Emit one shared `INTERVIEW.md` sidecar for every compiled agent

Context

The user wants a clear interview-mode instruction surface that points at the
real doctrine file instead of running it. Rally also has a hard rule against
runtime-written instruction stubs.

Options

- Reuse `AGENTS.md` and hope runtime facts are enough to suppress normal work.
- Require every flow or role to author its own interview sidecar prompt.
- Emit one Rally-owned shared `INTERVIEW.md` sidecar beside every compiled
  agent and let runtime facts point that sidecar at the real `AGENTS.md`.

Decision

Emit one shared Rally-owned `INTERVIEW.md` sidecar beside every compiled agent
in this slice. The sidecar is the live instruction surface for diagnostic chat.
The normal `AGENTS.md` stays the file being explained.

Consequences

- Interview doctrine stays in prompt source and in generated build output.
- Rally does not need flow authors to do extra work just to get the core
  feature.
- The build path needs one new shared sidecar emission rule.

Follow-ups

- Add the shared interview prompt source under `stdlib/rally/prompts/`.
- Prove the sidecar is emitted into build output and copied into the run home.

## 2026-04-14 - Add a diagnostic-safe home refresh instead of reusing full run materialization

Context

The normal `materialize_run_home(...)` path is issue-gated and setup-heavy.
That is correct for work turns, but it is the wrong default for doctrine chat.

Options

- Reuse full run materialization and accept issue/setup blockers on interview.
- Skip home refresh entirely and trust stale run-home files.
- Add a lighter refresh path for diagnostic chat that keeps prompts and adapter
  home files fresh without tripping normal work-turn gates.

Decision

Add a lighter diagnostic-home refresh path. It should create the run home shell
if needed, sync compiled agent directories and adapter bootstrap, and skip
issue readiness, flow setup, issue snapshots, and run-state writes.

Consequences

- `rally interview` can explain doctrine without pretending it is starting
  normal work.
- Interview mode still gets fresh prompt and adapter state.
- Home-materializer code needs a second explicit owned path instead of one
  catch-all helper.

Follow-ups

- Phase-plan the new home refresh helper and its proof.
- Prove that interview refresh keeps work-turn behavior unchanged.

## 2026-04-14 - Make deep operator docs a shipping requirement

Context

The user asked for strong documentation requirements so this feature ships
with a real debugging guide that teaches operators how to use it, not just
architecture notes.

Options

- Treat docs as a light follow-up and only update the existing design docs.
- Make a deep operator-facing debugging guide plus README links part of the
  shipping bar.

Decision

Make docs a hard shipping requirement. The feature must ship with one deep
guide at `docs/RALLY_AGENT_INTERVIEW_DEBUGGING_GUIDE_2026-04-14.md`, and
`README.md` plus the live Rally docs must route readers to it.

Consequences

- Phase 5 now owns authoring the guide, not just syncing existing docs.
- Discoverability from `README.md` is part of done.
- Final proof must cold-read the guide and its links, not just runtime docs.

Follow-ups

- Add the guide to the docs sync list and README update list.
- Verify the links and guide content in the final documentation proof.
