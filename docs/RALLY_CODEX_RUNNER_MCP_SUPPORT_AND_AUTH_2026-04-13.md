---
title: "Rally - Codex Runner MCP Support And Auth - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: architectural_change
related:
  - docs/RALLY_MASTER_DESIGN_2026-04-12.md
  - docs/RALLY_CLI_AND_LOGGING_2026-04-13.md
  - docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md
  - docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md
  - docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13_WORKLOG.md
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - src/rally/adapters/base.py
  - src/rally/adapters/codex/adapter.py
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - src/rally/services/flow_loader.py
  - src/rally/domain/flow.py
  - tests/unit/test_adapter_mcp_projection.py
  - tests/unit/test_runner.py
  - tests/unit/test_launcher.py
---

# TL;DR

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-14
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Code blockers (why code is not done)
- None. Fresh audit checked the full approved Section 7 frontier and found no
  remaining code gaps.

## Reopened phases (false-complete fixes)
- None. Phase 2, Phase 3, and Phase 4 now match the approved plan.

## Missing items (code gaps; evidence-anchored; no tables)
- None.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.
<!-- arch_skill:block:implementation_audit:end -->

## Outcome

Rally ships one honest Codex MCP readiness contract. Before agent work starts,
Rally can stop a Codex-backed run with one clear blocker when a required Codex
MCP or its projected auth is broken, and Rally can prove the same access story
for the parent run and any child agent Codex starts from that turn.

## Problem

Today Rally copies allowed MCP files into `home/mcps`, writes Codex
`config.toml`, links file-backed Codex auth into the run home, and launches
with `CODEX_HOME=<run_home>`. What it does not do is map that projected MCP set
onto Codex's native `required` startup contract, prove readiness before the
turn starts, or classify failure into one clear blocker that names the broken
MCP and reason.

## Approach

Keep the boundary simple. Rally owns policy, run-home prep, and blocker
reporting. The Codex adapter owns native config, auth projection, launch, and
startup readiness classification. For this slice, `required MCP` means the MCP
set Codex can actually see today: the flow-wide union Rally materializes into
`home/mcps/` and projects into run-home `config.toml`. The design will add one
pre-turn readiness path on that shipped contract instead of adding a side
system.

## Plan

1. Ground the plan in the live docs, flow model, adapter seam, and runner path.
2. Deep-dive pass 1 to lock the current path, target architecture, and full
   call-site list.
3. Deep-dive pass 2 to harden that same design before phase planning.
4. Write the authoritative phase plan for contract changes, tests, live proof,
   and doc sync.
5. Implement only after the plan is decision-complete.

## Non-negotiables

- No shared MCP broker or auth broker.
- No silent fallback, retry loop, or shim when readiness fails.
- Do not claim broader Codex auth support than the file-backed projection Rally
  can prove.
- Keep one clear blocker path that names the broken MCP and reason.
- Keep this work on the canonical Rally runner and adapter path.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-14
external_research_grounding: not started
deep_dive_pass_2: done 2026-04-14
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

When this plan is complete, a Codex-backed Rally run will do one honest
readiness check before agent work starts. A healthy run with projected
file-backed Codex auth will still launch. A run with a broken required MCP or
broken projected auth will stop early with one clear blocker that names the MCP
and the reason. The same doc, tests, and direct Codex proof will all tell that
same story.

## 0.2 In scope

- Turn this note into the canonical plan artifact for the Codex MCP readiness
  gap.
- Lock `required MCP` for this slice to the Codex-visible shared MCP set Rally
  already exposes today.
- Design one runner and adapter contract for pre-turn readiness plus typed
  blocker reporting.
- Design the proof story for projected auth from changed `CODEX_HOME`, broken
  MCP startup, and parent versus child-agent access parity.
- Sync the live Rally runtime docs when implementation changes the design truth.

## 0.3 Out of scope

- New Codex auth modes beyond the current file-backed projection.
- A shared MCP or auth broker for all adapters.
- Broad Claude auth or Claude MCP redesign work.
- Unrelated CLI, logging, or run-home cleanup work.
- Full per-agent MCP isolation across the whole runtime in this first draft.
  If research shows that readiness cannot stay honest without it, the plan must
  say that plainly before implementation starts.

## 0.4 Definition of done (acceptance evidence)

- This plan is confirmed and decision-complete.
- Focused Rally tests cover the chosen readiness contract, config projection,
  and startup-blocker handling.
- One direct Codex proof shows that projected file-backed auth still works from
  the changed `CODEX_HOME` path.
- One direct Codex proof shows that a broken required MCP stops the run before
  agent work starts and writes one clear blocker.
- The plan names and proves the real parent versus child-agent access story
  instead of leaving that phrase vague.
- The master design, CLI/logging doc, and Phase 4 doc stay aligned if the
  shipped runtime contract changes.

## 0.5 Key invariants (fix immediately if violated)

- No new parallel readiness path outside the canonical Rally runner and adapter
  boundary.
- No silent behavior drift in healthy Codex runs that already work today.
- No broader auth claim than the file-backed Codex projection Rally can prove.
- Fail loud before agent work starts when readiness fails.
- Keep one source of truth for the blocker reason.
- No fallbacks or runtime shims.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Honest runtime truth over broad support claims.
2. Reuse the current Rally runner and Codex adapter path.
3. Produce one clear blocker the operator can act on.
4. Keep the proof set lean, direct, and repeatable.

## 1.2 Constraints

- The live runtime docs still say this readiness gap is open.
- The current flow model exposes `allowed_mcps`, not a separate
  `required_mcps` field.
- The current Codex path already depends on `home/mcps`, `config.toml`,
  projected auth files, and `CODEX_HOME=<run_home>`.
- Codex itself already has a native `required` MCP startup contract, so Rally
  should align with that instead of inventing a second meaning.
- Rally should not patch around Doctrine for this runtime problem.

## 1.3 Architectural principles (rules we will enforce)

- Keep readiness adapter-native and blocker reporting Rally-owned.
- Prefer the smallest runtime change that makes `required MCP` real.
- Fail loud instead of retrying, auto-healing, or hiding the broken reason.
- Do not add a second control plane, sidecar service, or global state path.

## 1.4 Known tradeoffs (explicit)

- A narrow readiness slice may leave broader per-agent MCP isolation for later.
- Earlier failure is a feature here. Runs that reach the agent today may stop
  sooner once the contract becomes honest.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- `src/rally/services/home_materializer.py` copies the union of allowed MCPs
  into shared `home/mcps/`.
- `src/rally/adapters/codex/adapter.py` writes `home/config.toml` from that
  run-home snapshot and links `auth.json` plus `.credentials.json` into the run
  home.
- `src/rally/services/runner.py` starts the turn, then treats a failed adapter
  invocation as a generic blocked run.
- The live runtime docs still describe MCP readiness as unfinished work.

## 2.2 What’s broken / missing (concrete)

- Rally does not yet map its projected MCP set onto Codex's native
  `required = true` startup contract.
- Rally does not prove readiness before the turn starts.
- Rally does not prove that projected Codex auth is still usable.
- The blocker path is too generic. It does not guarantee one named MCP reason.
- The parent versus child-agent Codex access story is still not defined.

## 2.3 Constraints implied by the problem

- The fix should stay on the shared adapter boundary, the Codex adapter, the
  runner, focused tests, and live design docs.
- The plan should not add a new flow policy field in this slice.
- The fix must preserve healthy runs that already work through the current
  Codex path.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- None adopted yet — reject outside expansion for now — this pass is about the
  shipped Rally and Codex runtime contract, not outside pattern shopping.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/home_materializer.py:48-83` — Rally prepares the run
    home, copies the union of flow `allowed_mcps` into shared `home/mcps/`,
    then calls the adapter's `prepare_home(...)`.
  - `src/rally/services/home_materializer.py:347-355` and
    `src/rally/services/home_materializer.py:410-411` — the current MCP source
    set is the flow-wide union of all agents' `allowed_mcps`, not a per-agent
    active set.
  - `src/rally/domain/flow.py:93-124` and
    `src/rally/services/flow_loader.py:75-103` — the flow/runtime model only
    has `allowed_mcps`; there is no separate `required_mcps` field today.
  - `src/rally/adapters/codex/adapter.py:44-56` — the Codex adapter already
    owns native run-home prep by writing `config.toml` and projecting file-based
    auth into the run home.
  - `src/rally/adapters/codex/adapter.py:465-501` — Codex `config.toml` is
    built from the run-home `mcps/` snapshot, and the MCP set again comes from
    the flow-wide union of `allowed_mcps`.
  - `src/rally/adapters/codex/launcher.py:8-28` — Codex sees the run through
    `CODEX_HOME=<run_home>`.
  - `src/rally/services/runner.py:578-598` and
    `src/rally/services/runner.py:645-757` — the runner materializes the run
    home before the turn loop, marks the turn `RUNNING`, then treats adapter
    failure as a generic blocked run after `invoke(...)` returns.
  - `src/rally/services/runner.py:1405-1412` — current blocker text is just
    stderr/stdout or exit code, not a typed MCP-ready failure.
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md:371-382`,
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md:366-390`, and
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md:113-119` — the
    live docs still treat adapter-native MCP readiness as unfinished work.
  - `/Users/aelaguiz/workspace/codex/codex-rs/utils/home-dir/src/lib.rs:4-17`
    — Codex resolves its config root from `CODEX_HOME` and treats that as the
    real home path.
  - `/Users/aelaguiz/workspace/codex/codex-rs/config/src/mcp_edit.rs:19-39`
    — Codex loads MCP server config from `CODEX_HOME/config.toml`.
  - `/Users/aelaguiz/workspace/codex/codex-rs/login/src/auth/storage.rs:28-45`
    — Codex file-backed auth lives at `CODEX_HOME/auth.json`.
  - `/Users/aelaguiz/workspace/codex/codex-rs/cli/src/mcp_cmd.rs:467-538` and
    `/Users/aelaguiz/workspace/codex/codex-rs/cli/src/mcp_cmd.rs:716-774`
    — native `codex mcp list/get` read effective config under the active
    `CODEX_HOME`; `list --json` exposes `auth_status`, while `get --json` is
    config-only.
  - `/Users/aelaguiz/workspace/codex/codex-rs/codex-mcp/src/mcp/auth.rs:126-180`
    — auth status is computed natively, but stdio MCPs always report
    `unsupported`; usable auth states only apply to streamable HTTP MCPs.
  - `/Users/aelaguiz/workspace/codex/codex-rs/config/src/mcp_types.rs:64-82`
    — Codex already has a native `required` MCP field and startup timeout
    field in config.
  - `/Users/aelaguiz/workspace/codex/codex-rs/core/src/codex.rs:2128-2193` and
    `/Users/aelaguiz/workspace/codex/codex-rs/codex-mcp/src/mcp_connection_manager.rs:882-904`
    — Codex already waits for required MCP startup and fails the session when a
    required MCP does not initialize.
  - `/Users/aelaguiz/workspace/codex/codex-rs/exec/tests/suite/mcp_required_exit.rs:8-35`
    — that required-startup failure path already has a native exec test.
  - `/Users/aelaguiz/workspace/codex/codex-rs/core/src/tools/handlers/multi_agents_common.rs:196-234`,
    `/Users/aelaguiz/workspace/codex/codex-rs/core/src/agent/control.rs:168-245`,
    `/Users/aelaguiz/workspace/codex/codex-rs/core/src/thread_manager.rs:228-242`,
    and `/Users/aelaguiz/workspace/codex/codex-rs/core/src/thread_manager.rs:886-924`
    — child agents are spawned from a clone of the parent turn config and run
    inside the same `ThreadManager`, which is rooted at one `codex_home` and
    one shared `McpManager`.
  - Local CLI probe on 2026-04-14 — `CODEX_HOME=<temp> codex mcp list --json`
    and `codex mcp get <name> --json` matched the source-backed behavior above:
    config is read from the run-home `CODEX_HOME`, `list --json` exposes
    `auth_status`, and `list/get` alone do not prove stdio command startability.
- Canonical path / owner to reuse:
  - `src/rally/services/home_materializer.py` +
    `src/rally/adapters/codex/adapter.py` +
    `src/rally/services/runner.py` — this is the current owned path for
    materialization, native Codex prep, launch, and blocked-run handling. The
    readiness contract should land here, not in a side broker.
- Existing patterns to reuse:
  - `src/rally/services/runner.py:726-757` — Rally already has one canonical
    blocked-run path and issue-ledger write path; the missing piece is better
    readiness classification before agent work starts.
  - `src/rally/adapters/codex/launcher.py:31-50` and
    `tests/unit/test_launcher.py:95-116` — launch proof already records
    `CODEX_HOME` and Rally env vars. That gives the plan an existing log surface
    to reuse instead of adding new debug files.
  - `src/rally/services/home_materializer.py:72-75` and
    `src/rally/services/home_materializer.py:369-407` — per-agent skill views
    already exist as a clear capability-isolation pattern. MCPs do not have an
    equivalent path yet, which is why the broader runtime gap stays open.
- Prompt surfaces / agent contract to reuse:
  - None are primary here. This is a runner and adapter contract change, not a
    prompt-behavior problem. The relevant surface is the Codex launch env and
    run-home bootstrap path.
- Native model or agent capabilities to lean on:
  - Codex already has one native supported startup path in this repo:
    `CODEX_HOME` points at the prepared run home, `config.toml` lives there, and
    file-based auth is projected there. The plan should strengthen that path,
    not wrap it in a second broker or sidecar.
- Existing grounding / tool / file exposure:
  - `home/mcps/<name>/server.toml` — the run-home MCP snapshot Codex config is
    built from.
  - `home/config.toml` — the Codex-native MCP config Rally writes.
  - `home/auth.json` and `home/.credentials.json` — the current projected auth
    files.
  - `logs/adapter_launch/turn-*.json` — launch proof that already records
    `CODEX_HOME`.
- Duplicate or drifting paths relevant to this change:
  - The repo already has a split capability story: skills are activated per
    agent, but MCPs are still copied as one shared flow-wide union. The live
    docs also keep calling out per-agent MCP handling as unfinished work in
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md:609-617`,
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md:117-118`, and
    `docs/LESSONS_RALLY_PORT_GAP_READ_2026-04-13.md:104-144`.
  - The master design speaks about child agents, not Rally child runs, in
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md:372-389`. The separate deferred
    question about recursion shape in
    `docs/RALLY_MASTER_DESIGN_2026-04-12.md:648-650` is future work and should
    not force this plan to invent a new run model.
- Capability-first opportunities before new tooling:
  - Use the existing Codex-native startup surface (`CODEX_HOME`, run-home
    `config.toml`, projected auth, launch proof) to classify readiness before
    launch instead of adding a shared broker, parser stack, or wrapper service.
  - Align Rally with Codex's native `required` startup behavior instead of
    inventing a second readiness meaning that Codex itself does not use.
- Behavior-preservation signals already available:
  - `tests/unit/test_adapter_mcp_projection.py:20-90` — proves Codex config is
    built from the run-home MCP copy and rooted paths expand correctly.
  - `tests/unit/test_runner.py:1130-1246` — proves run-home capability refresh
    updates and removes MCP config as flow `allowed_mcps` change.
  - `tests/unit/test_launcher.py:20-35` and `tests/unit/test_launcher.py:95-116`
    — proves `CODEX_HOME` is set and recorded in launch proof.
  - `uv run pytest tests/unit -q` — current whole-unit baseline for the shipped
    runtime.

## 3.3 Decision gaps that must be resolved before implementation

- None at the plan-shaping level after the deep-dive passes.
- Chosen answers:
  - `required MCP` in this slice means every MCP Rally currently materializes
    into the run home and projects into Codex config, which is the flow-wide
    union of `allowed_mcps`. Rally should map that set onto Codex's native
    `required` startup contract rather than invent a second `required` meaning.
  - This slice stays honest without a new `required_mcps` field because the
    target readiness rule is defined against the MCP set Codex can actually see
    today.
  - The clean seam is a new pre-turn adapter readiness hook with typed failure
    data, not an overloaded `AdapterInvocation`.
  - Child-agent parity means Codex child agents keep using the same run-home
    `codex_home` and shared `McpManager` path because they are spawned from the
    parent turn config inside the same Codex process. The acceptance proof is
    still a direct Codex child-agent check, not a new Rally recursion model.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `flows/*/flow.yaml` declares per-agent `allowed_mcps`, and
  `src/rally/services/flow_loader.py` carries that list into
  `FlowAgent.allowed_mcps`.
- `src/rally/services/home_materializer.py` copies the flow-wide union of those
  MCP names into shared `home/mcps/<name>/server.toml`.
- `src/rally/adapters/codex/adapter.py` writes `home/config.toml` from that
  run-home MCP snapshot.
- The same Codex adapter projects `home/auth.json` and
  `home/.credentials.json` into the run home from `~/.codex`.
- The only checked-in MCP server definition today is stdio-shaped
  (`mcps/fixture-repo/server.toml`).
- `logs/adapter_launch/turn-*.json` records the Codex launch command and
  `CODEX_HOME`.

## 4.2 Control paths (runtime)

1. Flow loading parses agent `allowed_mcps` and validates adapter args.
2. `materialize_run_home(...)` refreshes agents, skills, and the shared MCP
   snapshot, then calls the adapter's `prepare_home(...)`.
3. The Codex adapter writes `config.toml` plus projected auth into the run
   home.
4. The runner enters the turn loop, resolves the current agent, activates live
   skills, and prepares turn artifacts.
5. The runner marks the run `RUNNING` and emits the `TURN` event before any
   Codex-specific readiness classification happens.
6. The Codex adapter invokes `codex exec` with `-C <run_home>` and
   `CODEX_HOME=<run_home>`.
7. If Codex exits non-zero, the runner turns that into a generic blocked run by
   copying stderr, stdout, or exit code into one blocker reason.

## 4.3 Object model + key abstractions

- `FlowAgent.allowed_mcps` is the only MCP policy input in the authored flow
  model today.
- `RallyAdapter` exposes `prepare_home(...)` and `invoke(...)`, but no pre-turn
  readiness hook.
- `AdapterInvocation` is process-shaped. It carries `returncode`, stdout,
  stderr, and session id, but no typed readiness failure.
- The Codex adapter computes its MCP exposure from the flow-wide union of
  `allowed_mcps`.
- Codex itself already knows how to fail startup on required MCPs, but Rally
  does not yet mark its projected MCP set as required through that native path.
- The runner owns the final blocked-state write, event emission, and issue-log
  append when adapter execution fails.

## 4.4 Observability + failure behavior today

- Launch proof already shows `CODEX_HOME` and the exact Codex command.
- Whole-run and agent logs already capture the standard lifecycle stream.
- The issue ledger already has one canonical blocked-run write path.
- Focused unit tests already prove config projection, rooted-path expansion, run
  home refresh, and MCP removal on resume.
- Missing today:
  - no named MCP readiness check before agent work starts
  - no typed failed-check taxonomy
  - no Rally proof that its projected MCP set is marked required through
    Codex's native startup path
  - no direct proof that a child agent started by Codex keeps the same shared
    `codex_home` and MCP-manager access story

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI surface is expected for this change. The operator-facing output is CLI
and issue-ledger text only.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Keep the current authored MCP policy surface unchanged in this slice:
  `allowed_mcps` remains the only flow field.
- Keep the current run-home MCP and Codex bootstrap layout unchanged:
  `home/mcps/`, `home/config.toml`, `home/auth.json`,
  `home/.credentials.json`, and `logs/adapter_launch/`.
- Do not add a second broker, sidecar service, or global state path.
- If readiness needs extra proof data, extend existing launch or event records
  instead of adding a new control-plane file.

## 5.2 Control paths (future)

1. Flow loading and run-home materialization stay as they are today.
2. For this slice, the required MCP set is defined as the MCP set Codex can
   really see today: every MCP Rally materializes into `home/mcps/` and writes
   into Codex `config.toml`, which is the flow-wide union of `allowed_mcps`.
   Rally maps that set onto Codex's native required-startup path.
3. Before a turn is marked `RUNNING` and before the normal agent prompt is
   built, the runner calls a new adapter readiness hook.
4. The Codex adapter evaluates each required MCP with four checks against the
   same prepared run home:
   - `run_home_materialization`
     `home/mcps/<name>/server.toml` exists and can be decoded.
   - `codex_config_visibility`
     native `codex mcp get <name> --json` under the same `CODEX_HOME` sees that
     server through the supported config path.
   - `codex_auth_status`
     native `codex mcp list --json` under the same `CODEX_HOME` reports a usable
     auth state for that server. In the current repo shape, stdio MCPs are
     expected to report `unsupported`, and that is a good no-auth-needed state.
     Non-usable streamable HTTP auth states fail loudly.
   - `command_startability`
     for the current repo's stdio MCP shape, Rally starts the configured command
     with its expanded args, cwd, and env under a short timeout. If spawn fails
     or the process exits early with failure, readiness fails. If the process
     stays alive past the short timeout, Rally treats it as startable and ends
     the probe cleanly.
5. If any required MCP fails one of those checks, the runner writes a blocked
   state before agent work starts and records the MCP name plus failed check in
   the event stream and issue ledger.
6. If all required MCPs pass, the runner proceeds with the current normal Codex
   turn path.
7. The same readiness hook runs again on resume and on later turns so Rally can
   catch drift after the first launch.
8. Child-agent parity is not a new runtime path. The acceptance proof uses the
   same run-home `CODEX_HOME` contract and the real Codex child-agent feature
   to show the same required MCP set remains available through the shared
   Codex `ThreadManager` and `McpManager` path.

## 5.3 Object model + abstractions (future)

- Keep `FlowAgent.allowed_mcps` unchanged and do not add a new
  `required_mcps` field in this slice.
- Extend the shared adapter boundary with a new pre-turn readiness hook, such
  as `check_turn_readiness(...)`, instead of overloading `invoke(...)`.
- Add a typed readiness result owned by the shared adapter boundary, for
  example:
  - `ok`
  - `mcp_name`
  - `failed_check`
  - `detail`
- `failed_check` is a small closed set in this slice:
  - `run_home_materialization`
  - `codex_config_visibility`
  - `codex_auth_status`
  - `command_startability`
- The Codex adapter owns translating native Codex and run-home facts into that
  typed result.
- `claude_code` adopts the same hook as a no-op in this slice so the shared
  adapter boundary stays coherent without pretending Claude now has the same
  readiness contract.

## 5.4 Invariants and boundaries

- Rally owns policy, run-home prep, and blocker reporting.
- The Codex adapter owns native config, auth projection, launch, and readiness
  classification.
- For this slice, `required MCP` means the Codex-visible configured MCP set, not
  just the current agent's authored subset, and Rally should feed that set into
  Codex's native required-startup behavior.
- No turn reaches `RUNNING` when readiness fails.
- No shared broker and no silent fallback path.
- This slice does not claim to solve per-agent MCP isolation.
- Child-agent parity means the same run-home contract stays visible to Codex
  child agents because they are spawned inside the same Codex process with the
  same `codex_home` and shared managers. It does not add a new Rally child-run
  model.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No UI surface is expected for this change.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Flow policy surface | `src/rally/domain/flow.py` and `src/rally/services/flow_loader.py` | `FlowAgent.allowed_mcps` and flow loading | `allowed_mcps` is the only authored MCP policy surface | Keep this unchanged; do not add `required_mcps` in this slice | The target contract is defined against the Codex-visible MCP set Rally already exposes | no new flow field | existing loader tests stay green |
| Run-home MCP materialization | `src/rally/services/home_materializer.py` | `_copy_allowed_mcps(...)` and `_allowed_mcp_names(...)` | Copies the flow-wide union of `allowed_mcps` into shared `home/mcps/` | Keep this semantics as the required-set source for Codex readiness; extract only small helper reuse if needed | This is the MCP set Codex can actually see today | no new runtime mode | `tests/unit/test_runner.py` |
| Shared adapter boundary | `src/rally/adapters/base.py` | `RallyAdapter` protocol and shared adapter types | Has `prepare_home()` and `invoke()` only | Add a pre-turn readiness hook and typed readiness result | Need a clean shared seam for early blocker handling | `check_turn_readiness(...)` plus readiness result/failure type | new focused adapter/runner tests |
| Codex adapter | `src/rally/adapters/codex/adapter.py` | run-home prep, MCP config, launch, failure classification | Writes config/auth and launches Codex, but does not yet drive Codex's native required-MCP startup path for the projected set | Implement required-set resolution, map it onto Codex-native required startup, keep native `codex mcp` visibility/auth checks, add the bounded stdio startability probe, and return typed failure classification | Codex-native startup and auth handling belongs here | Codex readiness failure data uses `mcp_name` + `failed_check` | `tests/unit/test_adapter_mcp_projection.py`, new focused Codex readiness tests, `tests/unit/test_runner.py` |
| Runner | `src/rally/services/runner.py` | `_execute_single_turn(...)` blocked-run path | Marks `RUNNING` before adapter failure is known and writes a generic blocker on process failure | Run readiness before `RUNNING`, block early, and preserve one canonical blocker path | Need fail-loud behavior before agent work starts | runner consumes typed readiness failures before normal invoke | `tests/unit/test_runner.py` |
| Nearby shared-adapter adopter | `src/rally/adapters/claude_code/adapter.py` | `ClaudeCodeAdapter` shared interface implementation | Implements the current shared adapter boundary | Adopt the new readiness hook as a truthful no-op for now | Keep the shared adapter boundary coherent without widening this plan's product scope | no-op readiness hook | focused adapter registry/runner coverage if needed |
| Native Codex probe surface | local `codex` CLI under `CODEX_HOME` | `codex mcp list/get` plus native required startup | Not used by Rally today | Reuse `codex mcp list/get` as the supported native visibility/auth probe and align the runtime with Codex's native required-startup behavior | Avoids inventing a second config parser or broker | no new Rally-owned config format | direct probe plus focused tests |
| Live docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and this plan | MCP readiness language | Current docs say the gap is open and broader per-agent MCP handling is still future work | Sync docs to the shipped contract while preserving the broader deferred per-agent MCP story | Keep live truth aligned and avoid a second story | no new API | doc proof plus unit proof |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  The contract lands on the current Rally runner + shared adapter boundary +
  Codex adapter path.
- Deprecated APIs (if any):
  None. This slice explicitly avoids a new `required_mcps` flow field.
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  No new shim or side broker may survive this work.
- Capability-replacing harnesses to delete or justify:
  None. This plan should use native Codex catalog surfaces and a narrow local
  startability check instead of a wrapper service.
- Live docs/comments/instructions to update or delete:
  At minimum the master design, CLI/logging doc, Phase 4 doc, and this plan.
- Behavior-preservation signals for refactors:
  `uv run pytest tests/unit -q` plus focused adapter/runner proof and one direct
  Codex proof on changed `CODEX_HOME`.

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared adapter boundary | `src/rally/adapters/claude_code/adapter.py` | adopt the new shared readiness hook as a no-op | prevents the base adapter contract from drifting into a Codex-only special case | include |
| Flow model | `src/rally/domain/flow.py` and `src/rally/services/flow_loader.py` | add `required_mcps` as a second authored field | would create a second MCP policy surface before the repo proves it is needed | exclude |
| MCP isolation frontier | future per-agent MCP runtime path | per-agent active MCP config like the shipped skill-activation path | still a real broader gap, but not required to make this Codex slice honest | defer |
| Live design docs | master design, CLI/logging, Phase 4 doc | same required-set semantics and blocker story | prevents docs from splitting into "flow-wide now" versus "agent-specific now" confusion | include |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 — Lock the shared readiness seam

* Goal:
  Land the minimal shared adapter and runner contract needed for pre-turn
  readiness without changing the authored flow policy surface.
* Work:
  Add a shared adapter readiness hook and typed readiness result in
  `src/rally/adapters/base.py`.
  Update `src/rally/adapters/claude_code/adapter.py` to implement the new hook
  as a truthful no-op.
  Update `src/rally/services/runner.py` so readiness runs before a turn is
  marked `RUNNING`, and so typed readiness failures flow through one canonical
  blocked-run path.
* Verification (required proof):
  Focused unit tests prove the new shared adapter seam and the runner's
  pre-`RUNNING` block behavior.
  Existing non-readiness unit coverage still passes under `uv run pytest tests/unit -q`.
* Docs/comments (propagation; only if needed):
  Add one short code comment at the shared adapter boundary if the new readiness
  result or failed-check taxonomy is non-obvious.
* Exit criteria:
  The runtime has one pre-turn readiness seam, Claude still works through the
  shared adapter boundary, and no turn reaches `RUNNING` after a typed readiness
  failure.
* Rollback:
  Revert the shared adapter hook and runner preflight changes together so the
  runtime falls back to the current pre-change behavior cleanly.

## Phase 2 — Implement Codex-native readiness checks

Status: COMPLETE (fresh audit confirmed the planned code and proof landed)

* Goal:
  Make the Codex adapter classify required MCP readiness against the Codex-
  visible MCP set Rally already exposes today.
* Work:
  In `src/rally/adapters/codex/adapter.py`, resolve the required MCP set from
  the existing flow-wide run-home MCP snapshot and map that set onto Codex's
  native required-startup path.
  Implement the four chosen checks:
  `run_home_materialization`,
  `codex_config_visibility`,
  `codex_auth_status`, and
  `command_startability`.
  Reuse native `codex mcp get/list` under the prepared `CODEX_HOME`.
  Implement the bounded stdio command-startability probe for the current repo
  MCP shape.
  Return typed `mcp_name` plus `failed_check` data instead of generic process
  stderr for readiness failures.
* Verification (required proof):
  Focused adapter tests prove:
  config visibility uses the run-home `CODEX_HOME`,
  auth-status parsing works,
  startability failures name the MCP and failed check,
  and healthy config projection behavior from existing tests still passes.
* Docs/comments (propagation; only if needed):
  Add one short code comment in the Codex adapter where the readiness checks are
  ordered if that order would otherwise be easy to break later.
* Exit criteria:
  The Codex adapter can tell Rally, for every required MCP in this slice,
  whether the server is materialized, visible through native Codex config, in a
  usable auth state, and startable under the bounded stdio probe.
* Rollback:
  Revert only the Codex readiness implementation while keeping Phase 1 seam
  changes if needed for recovery.

## Phase 3 — Prove blocker behavior and parent/child-agent parity

Status: COMPLETE (fresh audit confirmed the planned code and proof landed)

* Goal:
  Prove the shipped runtime now fails loud with one actionable blocker and that
  the same run-home contract stays visible to Codex child agents through the
  shared Codex manager path.
* Work:
  Add focused runner tests that prove readiness failure blocks before `RUNNING`
  and writes one named MCP failure reason.
  Add focused Codex proof coverage for:
  projected file-backed auth from changed `CODEX_HOME`,
  broken required MCP early failure,
  and child-agent parity from the same prepared run home.
  Keep the proof set lean; do not add a wrapper harness or a second probe
  system.
* Verification (required proof):
  `uv run pytest tests/unit -q`
  plus the focused new readiness tests.
  One direct Codex proof for healthy auth,
  one direct Codex proof for broken-MCP early block,
  and one direct Codex child-agent proof on the same run-home contract.
* Docs/comments (propagation; only if needed):
  If the child-agent parity proof depends on a non-obvious Codex behavior,
  record that truth in the plan and, if warranted, one short code comment near
  the Codex readiness boundary.
* Exit criteria:
  The blocker path is early, typed, and actionable, and the direct Codex proof
  set covers healthy auth, broken MCP failure, and child-agent parity.
* Rollback:
  Revert the new readiness proof-specific runtime behavior together with the
  Codex readiness checks if the proof shows the contract is not yet honest.

## Phase 4 — Sync live docs and finish the cutover

Status: COMPLETE (fresh audit confirmed the live-doc sync landed)

* Goal:
  Align the surviving live design docs with the shipped readiness contract
  without overstating the still-deferred per-agent MCP isolation work.
* Work:
  Update
  `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
  `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`,
  `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`,
  and this plan
  so they all say the same thing about:
  the required MCP set for this slice,
  the new pre-turn readiness path,
  the clear blocker story,
  and the still-open per-agent MCP frontier.
  Remove any stale wording that implies the old generic gap is still the whole
  story after the implementation lands.
* Verification (required proof):
  Cold-read the updated docs against the shipped code path and the direct proof
  outcomes.
  Confirm the docs do not silently claim per-agent MCP isolation if Phase 2 and
  Phase 3 did not ship it.
* Docs/comments (propagation; only if needed):
  This phase owns the live-doc reality sync.
* Exit criteria:
  The code, proof, and live docs agree, and there is no second story left in
  the surviving docs.
* Rollback:
  Revert the doc sync as a group if the shipped code contract changes again
  before merge.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

Keep the unit proof lean. The current baseline is `uv run pytest tests/unit -q`
plus focused runner, shared-adapter, and Codex adapter tests for the chosen
readiness contract.
Prefer behavior-level tests around typed readiness failures and early blocking,
not tests that grep for deleted wording or police repo shape.

## 8.2 Integration tests (flows)

If unit proof is not enough, prefer a narrow Rally integration proof on the
real Codex runtime path over a broad new harness or wrapper service.

## 8.3 E2E / device tests (realistic)

One direct Codex proof matters more than broad end-to-end ceremony here:

- projected file-backed auth still works from changed `CODEX_HOME`
- a broken required MCP blocks before agent work starts
- a child agent started by Codex from the same turn keeps the same required MCP
  access story through the shared `codex_home` and manager path
- the real parent versus child-agent access story is proven and named plainly

The checked-in direct proof record lives in
`docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13_WORKLOG.md`.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

This is a runtime contract change, not a staged product rollout. The likely
rollout is one hard cutover after code, proof, and live docs agree.

## 9.2 Telemetry changes

No new telemetry is assumed yet. The change may only need clearer existing
event and blocker text.

## 9.3 Operational runbook

The operator-facing runbook should stay simple: if readiness fails, Rally
should tell the operator which MCP broke and why before any agent work starts.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: self-integrator
- Scope checked:
  - frontmatter, `# TL;DR`, and `# 0)` through `# 9)`
  - `planning_passes`
  - current architecture, target architecture, call-site audit, and phase plan
  - verification burden, rollout scope, and Decision Log alignment
- Findings summary:
  - the artifact now says one consistent story end to end about required MCP
    scope, canonical owner path, typed blocker handling, proof expectations, and
    the still-deferred per-agent MCP isolation frontier
  - the warn-first choice to skip external research is explicit and does not
    leave a plan-shaping gap
- Integrated repairs:
  - normalized Section 3.3 wording so it reflects both deep-dive passes
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

## 2026-04-14 - Convert the Codex MCP note into the canonical plan doc

### Context

The repo already had a good status note for the Codex MCP readiness gap, but it
did not have the canonical full-arch scaffold needed for `arch-step`.

### Options

- Keep the note as-is and create a second plan doc.
- Convert the existing doc in place into the canonical plan artifact.

### Decision

Convert this existing doc in place so it becomes the single plan artifact for
the Codex MCP readiness work.

### Consequences

- Later `arch-step` commands can use this file as the default `DOC_PATH`.
- The next command should be North Star confirmation, then `research`.
- The repo keeps one planning source of truth instead of a note plus a plan.

### Follow-ups

- Confirm or edit the drafted North Star.
- Run `$arch-step research docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13.md`
  after confirmation.

## 2026-04-14 - North Star confirmed

### Context

The draft plan artifact was in place, but `arch-step new` requires explicit
confirmation before deeper planning can start.

### Options

- Keep the plan in `draft` and revise the North Star.
- Confirm the drafted North Star and activate the plan.

### Decision

Confirm the drafted North Star and move the plan from `draft` to `active`
without changing scope.

### Consequences

- This file is now the default canonical `DOC_PATH` for later `arch-step`
  commands in this thread.
- The next honest move is `research`.

### Follow-ups

- Run `$arch-step research docs/RALLY_CODEX_RUNNER_MCP_SUPPORT_AND_AUTH_2026-04-13.md`.

## 2026-04-14 - Deep-dive pass 1 locked the readiness shape

### Context

Research grounded the current runtime enough to choose the target architecture
for this slice without inventing a new MCP policy field or a new recursion
model.

### Options

- Add a new `required_mcps` flow field and treat readiness as a new authored
  policy surface.
- Keep this slice honest against the MCP set Codex already sees today and land
  the contract on the shared adapter boundary plus Codex adapter path.

### Decision

Keep `allowed_mcps` as-is for this slice. Define `required MCP` as the
flow-wide MCP set Rally materializes into the run home and projects into Codex
config today. Add a pre-turn adapter readiness hook with typed failures, and
prove child-agent parity through the same run-home `CODEX_HOME` contract rather
than a new Rally child-run model.

### Consequences

- This slice can move forward without inventing a second MCP policy field.
- The target contract no longer needs a model-backed startup probe if native
  `codex mcp` surfaces plus a bounded stdio startability check prove enough.
- Per-agent MCP isolation stays as a later runtime frontier.
- The next deep-dive pass can harden the same architecture instead of reopening
  the core shape.

### Follow-ups

- Run deep-dive pass 2 after any needed external research, or directly if no
  outside grounding is needed.
- Write the authoritative phase plan once the second deep-dive pass still
  agrees with this shape.

## 2026-04-14 - Deep-dive pass 2 hardened the native probe

### Context

The first deep-dive pass still carried one expensive assumption: that Codex
might need a model-backed startup probe to make MCP auth and readiness honest.
Local CLI probing on 2026-04-14 showed a better native surface.

### Options

- Keep a model-backed Codex startup probe in the target design.
- Use native `codex mcp list/get` under the prepared `CODEX_HOME` for config and
  auth visibility, plus a short local stdio startability check for the current
  repo MCP shape.

### Decision

Use the native `codex mcp` catalog as the primary readiness probe and pair it
with a bounded stdio command-startability check. Do not add a model-backed
startup probe in this slice.

### Consequences

- The readiness path stays cheaper and more deterministic.
- The plan still uses real Codex-native surfaces for config and auth truth.
- The remaining implementation work is now phase-plan material, not a
  plan-shaping blocker.

### Follow-ups

- Write the authoritative phase plan.

## 2026-04-14 - Deep-dive refresh grounded the plan in Codex source

### Context

The first deep-dive passes were grounded in Rally code plus local Codex CLI
behavior. That shaped the plan, but it still left room for doubt about how
native Codex required MCP startup, auth status, and child-agent inheritance
actually work.

### Options

- Keep the plan as-is and treat local CLI behavior as enough proof.
- Re-open the deep dive against `/Users/aelaguiz/workspace/codex` and tighten
  the plan where source truth is stronger or more precise.

### Decision

Re-open the deep dive against Codex source and update the plan with what the
source actually says.

### Consequences

- The plan now says plainly that Codex already has a native `required` MCP
  startup contract, so Rally should align to that instead of inventing a second
  meaning.
- The plan now says `codex mcp list/get` are config and auth probes, not stdio
  startability proof.
- The child-agent parity story is tighter: spawned child agents are built from a
  clone of the parent turn config and run inside the same Codex `ThreadManager`
  and shared `McpManager`, not through a new shell-level home lookup.

### Follow-ups

- Keep the implementation and proof plan aligned with these Codex-source facts.
- If implementation work finds a mismatch between the local Codex repo and the
  installed Codex build, stop and record the drift plainly.

## 2026-04-14 - Phase plan froze the execution order

### Context

Both deep-dive passes agreed on the architecture, and local Codex CLI probing
was enough to harden the native probe choice. The recommended flow still showed
`external_research_grounding: not started`, so this phase-plan pass had to make
an explicit warn-first choice instead of leaving the gap implicit.

### Options

- Stop and require an external-research pass before phase planning.
- Continue to phase-plan because repo truth and the local Codex CLI surface were
  already enough to remove plan-shaping uncertainty.

### Decision

Continue to `phase-plan` without an external-research pass. Treat outside
research as unnecessary unless a later consistency read shows a real missing
anchor.

### Consequences

- Section 7 is now the one authoritative execution checklist.
- `consistency-pass` should still confirm that the missing external-research
  pass did not hide a real plan gap.

### Follow-ups

- Run `consistency-pass` after phase-plan.

## 2026-04-14 - Reopened implementation phases were completed with direct Codex proof

### Context

The first implementation pass left two real gaps: the shipped readiness
taxonomy drifted from the approved four-check contract, and the repo still
lacked the direct Codex proof set for changed `CODEX_HOME`, broken required
MCP startup, and child-agent parity.

### Options

- Keep the earlier unit-only proof and treat the direct proof frontier as
  optional.
- Align the shipped readiness contract with the plan, run the direct Codex
  proof set, and record those results in a checked-in artifact.

### Decision

Align the code to the approved four-check contract, run the direct Codex proof
set, and record the outputs in the checked-in worklog.

### Consequences

- The Codex adapter now emits the approved `failed_check` values:
  `run_home_materialization`,
  `codex_config_visibility`,
  `codex_auth_status`,
  and `command_startability`.
- Streamable HTTP MCPs now block on every non-usable auth state instead of
  only `not_logged_in`.
- The repo now has a checked-in direct proof artifact for:
  changed `CODEX_HOME`,
  broken required MCP startup,
  and child-agent parity through the same prepared run home.
- The live docs were re-read against the final proof outcomes instead of the
  earlier partial implementation state.

### Follow-ups

- Let the next fresh audit confirm the coding frontier is now complete.
