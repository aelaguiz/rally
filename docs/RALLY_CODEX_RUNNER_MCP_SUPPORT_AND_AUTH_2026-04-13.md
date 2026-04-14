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
  - docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md
  - docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md
  - src/rally/services/home_materializer.py
  - src/rally/services/runner.py
  - src/rally/services/flow_loader.py
  - src/rally/domain/flow.py
  - src/rally/adapters/codex/launcher.py
  - tests/unit/test_runner.py
  - tests/unit/test_launcher.py
---

# TL;DR

## Outcome

Rally gets one clean way to support required MCP access in runner-owned agent
runs, starting with Codex, without baking Codex file names and auth rules into
shared runtime code. The same design also leaves a clear path for future
`claude_code` support.

## Problem

Rally already copies allowlisted MCP definitions into the run home and writes a
Codex `config.toml`, but it still lacks one honest story for MCP auth,
required-server readiness, and inner-runner inheritance. The current shared
runtime also knows too much about Codex bootstrap details, which will make
future Claude support messy if we keep going that way.

## Approach

Keep the adapter native. For Codex, keep `CODEX_HOME=<run_home>` and keep the
generated root `config.toml`, but move native file prep behind the Codex
adapter. Shared Rally code should keep the run-home shell, compiled agents,
allowed skills, and the copied policy snapshot in `home/mcps/`. The Codex
adapter should turn that snapshot into the real root `config.toml`, project
only the auth files and config keys Codex itself needs, and let native Codex
session start stay the fail-loud required-MCP gate. Shared Rally code should
only classify and report that blocker. Keep the shared Rally layer generic: it
should talk about prepared capabilities, adapter home prep, native startup,
and fail-loud blockers, not about `config.toml`, `auth.json`, or
`.credentials.json`. Do not lock this design from source reads alone. Every
important Codex assumption must be checked directly in the local
`~/workspace/codex` repo and then copied into Rally tests before the design is
treated as settled. Because MCP auth and transport guidance is client-specific
and still moving, Rally should not grow a shared OAuth discovery or
registration engine above adapters.

## Plan

1. Lock the small shared adapter boundary: home prep, native invoke,
   session/result handling, and blocker classification.
2. Deep-dive the current Rally and Codex seams, then move native Codex file and
   auth work fully behind that boundary.
3. Phase the Codex-first implementation so it proves required MCP startup,
   supported auth modes, and child-runner inheritance without adding a second
   MCP system.
4. Keep the design file-name-free at the shared layer so Claude can later plug
   in its own native home and auth story.

## Non-negotiables

- No second MCP discovery or auth system inside Rally.
- No silent fallback when a required MCP or required auth surface is missing.
- Shared runtime must not own Codex-specific file names or storage rules.
- Shared runtime must not own shared OAuth discovery or registration logic.
- Codex parent and child runners must end up with the same allowed MCP story.
- Do not "solve" Codex in a way that blocks future `claude_code` support.
- Do not rely on static code reading alone for Codex behavior claims. Prove the
  key assumptions directly in `~/workspace/codex` and mirror the needed cases
  in Rally tests.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done (2026-04-13)
external_research_grounding: done (2026-04-13)
deep_dive_pass_2: done (2026-04-13)
phase_plan: done (2026-04-13)
recommended_flow: planning complete -> implement or implement-loop
note: The planning arc is complete when the consistency helper below says the doc is decision-complete. This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can support required MCP access for Codex runners, including inner
runners, through one shared adapter capability boundary while still keeping the
real Codex setup native to Codex.

This claim is true only if all of this is true:

- Shared runtime owns policy, adapter selection, and clear blocker reporting.
- The Codex adapter owns native home prep, auth projection, native invoke,
  session/result plumbing, and startup failure classification.
- A Codex run that starts from the prepared run home gives the main runner and
  spawned subagents the same allowed MCP access story.
- A missing or broken required MCP stops native startup before normal work
  starts, with a clear reason.
- Shared runtime does not hardwire Codex file names such as `config.toml`,
  `auth.json`, or `.credentials.json` into the long-term adapter contract.
- Shared runtime does not own shared OAuth discovery or registration rules.
- Future `claude_code` support can implement the same shared boundary with its
  own native files and auth rules.
- The key Codex claims that shape this design are proved directly in the local
  `~/workspace/codex` repo and then reproduced in Rally tests before they are
  treated as plan truth.

## 0.2 In scope

- Define the shared adapter boundary for:
  - home prep
  - required capability checks
  - fail-loud blocker reporting
- Decide what Rally owns when it copies MCP definitions into the run home and
  what the adapter owns when it turns that policy into native runtime config.
- Define the Codex-native path for:
  - generated run-home `config.toml`
  - projected auth material
  - required MCP startup checks
  - child-runner inheritance
- Require direct Codex proof for every assumption that changes the design, then
  carry the same cases into Rally-owned tests.
- Make the v1 Codex auth assumptions explicit instead of leaving them hidden.
- Keep the design clean for later `claude_code` support from
  `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`.
- Align the durable Rally design docs when this plan lands.

Allowed convergence scope:

- refactor shared runtime and home-materialization ownership lines
- add small adapter-facing capability-prep abstractions
- move Codex bootstrap code behind the adapter boundary
- tighten flow validation if the adapter contract needs it
- update stale docs that would teach the wrong runtime model after the change

## 0.3 Out of scope

- Shipping full Claude adapter support in the same first Codex MCP change.
- Adding a machine-global Rally auth store or a shared cross-adapter auth
  broker.
- Changing Doctrine language or compiler behavior.
- Adding a second final-result path, handoff file, or hidden control plane.
- Supporting every possible Codex auth backend on day one if some of them do
  not project cleanly into a run-home-based `CODEX_HOME`.
- Adding silent retries, best-effort MCP fallbacks, or partial "maybe works"
  readiness checks.
- Treating unverified code reading as enough proof for a design-shaping Codex
  behavior claim.

## 0.4 Definition of done (acceptance evidence)

The work is done only when all of this is true:

- Shared runtime has one small adapter seam for home prep, native invoke, and
  startup-blocker classification.
- Codex still runs with `CODEX_HOME=<run_home>` and a generated root
  `config.toml`.
- Rally can project the allowed Codex MCP setup into the run home from an
  already working host Codex setup.
- Required Codex MCP failures show up before the turn in a clear blocker path.
- Codex child runners inherit the same MCP access story as the parent runner.
- The shared contract does not assume Codex file names, so a future Claude
  adapter can use its own native files.
- Durable docs teach the same story the code ships.
- Every design-shaping Codex assumption used by this plan is backed by a direct
  Codex-side proof and a Rally-side test or named test gap.

Behavior-preservation evidence:

- `uv run pytest tests/unit -q`
- current Codex runner and launcher tests stay green or move cleanly behind
  shared seams
- new tests prove adapter-owned home prep, startup blocker handling, and config
  refresh on resume
- direct proof runs in the local `~/workspace/codex` repo confirm the native
  behaviors this plan depends on
- one honest proof exists for parent-plus-child Codex MCP task success from the
  same prepared home, even if richer child tool traces still remain hardening
  work

## 0.5 Key invariants (fix immediately if violated)

- One run home is the whole working world for the runner.
- No second MCP path exists beside the native adapter path.
- No hidden auth fallback widens access past Rally policy.
- No shared OAuth discovery or registration engine appears in Rally core.
- Parent and child runners must share the same allowed MCP story in v1. Exact
  tool-set equality is still hardening work until a direct proof lands.
- Required MCP failures are fail-loud, not best-effort.
- Shared runtime stays adapter-generic even when Codex goes first.
- No plan-shaping Codex assumption graduates from "likely" to "settled" until
  it is directly verified in Codex and represented in Rally tests.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Keep the adapter native and simple.
2. Prove design-shaping Codex assumptions directly in Codex before we commit to
   the shape.
3. Fail before the turn when a required MCP cannot work.
4. Preserve Codex child-runner inheritance instead of building a second MCP
   system.
5. Keep the shared boundary clean enough for future Claude support.
6. Avoid auth machinery that buys little and adds long-term drag.

## 1.2 Constraints

- Rally already sets `CODEX_HOME=<run_home>`.
- Shared home materialization still writes Codex config and auth details today.
- Codex CLI auth and Codex MCP OAuth do not share the same storage behavior.
- The current docs already admit that required Codex MCP auth and readiness are
  not fully solved yet.
- Future Claude support will need the same shared shape, but not the same
  files.
- Source inspection is useful, but this plan now requires direct Codex proof
  for behavior claims that drive architecture.

## 1.3 Architectural principles (rules we will enforce)

- Rally policy first, adapter-native projection second.
- Shared runtime owns "what must exist"; the adapter owns "how this adapter
  makes it real."
- No new parallel MCP path.
- No hidden retries or soft passes for required MCPs.
- The run home stays the source of truth for what Rally prepared for the turn.

## 1.4 Known tradeoffs (explicit)

- Leaning on native Codex startup keeps the system simple, but it means Rally
  must classify startup failures instead of probing with a second custom check.
- Codex v1 may need to support only the auth modes that project cleanly into a
  run-home `CODEX_HOME`. That is narrower, but honest.
- Copying or linking only the needed native auth surfaces is simpler than
  inventing a shared Rally auth store, but it means adapter behavior stays
  adapter-specific by design.
- Requiring direct Codex proof and matching Rally tests up front slows planning
  a little, but it is much cheaper than building around a false assumption.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- `src/rally/services/home_materializer.py` copies allowlisted MCPs into
  `home/mcps/`, writes a root Codex `config.toml`, and seeds Codex auth files.
- `src/rally/adapters/codex/launcher.py` and `src/rally/services/runner.py`
  launch Codex with `CODEX_HOME=<run_home>`.
- Current unit tests already prove config refresh and stale MCP cleanup on
  resume.

## 2.2 What’s broken / missing (concrete)

- Rally does not yet have one clean, named seam for required capability prep.
- Codex already fails loud for a broken required MCP, but Rally still sees that
  as a generic exec failure instead of a named blocker.
- Shared runtime still knows Codex bootstrap details it should not own.
- The copied `home/mcps/` snapshot is not yet the real input to generated
  native config.
- The shared TOML writer cannot express all valid Codex MCP server shapes.
- The design story for parent and child MCP inheritance is still implied, not
  locked.
- This drift will make future Claude support harder if we do not clean it up.

## 2.3 Constraints implied by the problem

- Keep the run-home-based Codex launch story unless evidence forces a change.
- Do not make shared runtime depend on Codex file names.
- Once Rally has copied `home/mcps/`, that run-home snapshot should be enough to
  explain the prepared MCP policy.
- Do not lose valid Codex MCP fields while rewriting TOML.
- Do not claim auth portability that native Codex behavior does not support.
- Do not make the Codex fix so local that Claude later needs a second design.
- Verify the critical Codex behaviors directly before treating them as design
  inputs.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `~/workspace/codex/codex-rs/utils/home-dir/src/lib.rs` plus direct CLI proof
  on 2026-04-13 — adopt: `CODEX_HOME` is the native Codex home root and Codex
  really reads MCP config from that home, not from a hidden second location.
  Direct proof: `CODEX_HOME=<temp> codex mcp list` showed only the MCP server
  written into that temp `config.toml`.
- `~/workspace/codex/codex-rs/login/src/auth/storage_tests.rs` plus direct CLI
  proof on 2026-04-13 — adopt, but narrowly: file-projected `auth.json` is
  enough for a fresh `CODEX_HOME` to become logged in. Direct proof: an empty
  temp home showed `Not logged in`, while the same temp home with a projected
  `auth.json` showed `Logged in using ChatGPT`.
- `~/workspace/codex/codex-rs/exec/tests/suite/mcp_required_exit.rs` plus
  direct CLI proof on 2026-04-13 — adopt: a required broken MCP fails before
  normal work starts and Codex exits loudly. Direct proof:
  `CODEX_HOME=<temp> codex exec ...` with a required fake MCP exited code `1`
  with `required MCP servers failed to initialize`.
- Direct `codex exec --json` proof on 2026-04-13 with a temp `CODEX_HOME` and
  a local filesystem MCP — adopt for v1 inheritance confidence: the parent used
  the MCP server in a real run, then spawned a child from the same prepared
  home and the child completed the same MCP-dependent task with the same output.
  The event stream showed parent `mcp_tool_call` items plus `spawn_agent` /
  `wait` events, and the child returned the same file content. This is enough
  to treat “inner runner works from the same prepared home” as proved for the
  v1 plan, even though the JSON stream still did not expose an event-level MCP
  tool trace for the child.
- `~/workspace/codex/codex-rs/rmcp-client/src/oauth.rs` — adopt as current
  Codex-side testable shape for MCP OAuth storage: file fallback lives at
  `CODEX_HOME/.credentials.json`, while the store key is based on MCP
  `server_name` plus `server_url`. This is useful because it hints that MCP
  OAuth keyring behavior may survive a changed `CODEX_HOME` better than CLI
  auth does, but this specific claim still needs a direct Codex-side proof
  before Rally treats it as settled.
- Direct `codex login status` probe on 2026-04-13 with temp homes configured
  for `cli_auth_credentials_store = "file"` and
  `cli_auth_credentials_store = "keyring"` and with no projected `auth.json` —
  adopt negatively for v1 scope: both temp homes reported `Not logged in` on
  this machine. Combined with direct `auth.json` projection proof, this is good
  enough to keep v1 CLI auth support file-backed only instead of implying
  keyring continuity.
- `~/workspace/codex/codex-rs/core/tests/suite/subagent_notifications.rs`,
  `~/workspace/codex/codex-rs/core/src/agent/control.rs`, and
  `~/workspace/codex/codex-rs/core/src/thread_manager.rs` — adopt cautiously:
  Codex clearly has real spawned-child config inheritance. Combined with the
  direct CLI parent-plus-child filesystem proof, this is enough to settle the
  architecture choice for inner-runner inheritance. Exact event-level child MCP
  tool visibility is still a hardening target, not a plan blocker.
- `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md` — adopt:
  the shared Rally boundary must stay adapter-generic. Codex may keep native
  root home files because `CODEX_HOME` points at the run home, but the shared
  contract should talk about adapter home prep, required capability checks, and
  fail-loud blockers, not Codex file names.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `src/rally/services/home_materializer.py` — current owner of shared
    run-home layout, allowlisted MCP sync into `home/mcps/`, generated root
    Codex `config.toml`, and projected Codex auth files.
  - `src/rally/services/runner.py` — current owner of turn startup and the
    place where native startup failures are currently turned into blocked runs.
  - `src/rally/adapters/codex/launcher.py` — current owner of the Codex launch
    env, including `CODEX_HOME=<run_home>`.
  - `src/rally/services/flow_loader.py` and `src/rally/domain/flow.py` —
    current flow contract that already knows `runtime.adapter`, which is the
    right place to keep the shared adapter boundary generic.
- Canonical path / owner to reuse:
  - `src/rally/services/home_materializer.py` — should keep ownership of
    Rally-owned run-home layout and copied MCP policy.
  - `src/rally/adapters/codex/` — should own native Codex projection of that
    policy into `config.toml`, projected auth material, and startup failure
    classification.
  - `src/rally/services/runner.py` — should own the shared fail-loud blocker
    path when an adapter says required capability prep did not succeed.
- Existing patterns to reuse:
  - `tests/unit/test_runner.py` — already proves config refresh on resume and
    stale MCP cleanup, which is the main Rally preservation signal for this
    work.
  - `tests/unit/test_launcher.py` — already proves the Codex launch env shape.
  - `mcps/*/server.toml` plus flow MCP allowlists — already give Rally one
    policy source of truth for which MCPs should be present in a run.
- Prompt surfaces / agent contract to reuse:
  - `stdlib/rally/prompts/rally/base_agent.prompt` — already keeps the main
    agent contract adapter-neutral.
  - `skills/rally-kernel/SKILL.md` — already keeps notes and final-result rules
    Rally-owned rather than adapter-owned.
  - `stdlib/rally/prompts/rally/turn_results.prompt` — Rally already owns the
    final turn result. MCP support should not add a second result path.
- Native model or agent capabilities to lean on:
  - Codex already has native required-MCP startup handling and native child
    agent spawning. Rally should reuse those instead of inventing a second MCP
    inheritance layer.
- Existing grounding / tool / file exposure:
  - `runs/<run-id>/home/` — Rally's whole working world.
  - `home/mcps/` — Rally-owned copied MCP definitions.
  - root `home/config.toml` under `CODEX_HOME` — Codex-native config entry.
  - `home/auth.json` and `home/.credentials.json` — projected native auth
    surfaces that Codex may read.
- Duplicate or drifting paths relevant to this change:
  - `src/rally/services/home_materializer.py` still owns Codex-native file
    details that a future multi-adapter runtime should not keep in the shared
    layer.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, and
    `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md` still describe
    the Codex MCP auth and readiness story as incomplete.
  - `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`
    already points toward a cleaner shared adapter boundary than today's code.
- Capability-first opportunities before new tooling:
  - Use the native Codex `CODEX_HOME` model instead of creating a Rally-owned
    parallel MCP home.
  - Use direct `codex` CLI checks and Codex-side tests as the proof harness
    before adding Rally code.
  - Use Codex's native required-MCP startup failure path instead of adding a
    second custom Rally parser or retry layer.
- Behavior-preservation signals already available:
  - `uv run pytest tests/unit -q` — Rally's main regression floor.
  - `tests/unit/test_runner.py` — protects current Rally MCP config refresh and
    stale-entry cleanup behavior.
  - `tests/unit/test_launcher.py` — protects `CODEX_HOME` launch behavior.
  - `~/workspace/codex/codex-rs/exec/tests/suite/mcp_required_exit.rs` —
    Codex-side proof path for fail-loud required MCP startup.
  - `~/workspace/codex/codex-rs/login/src/auth/storage_tests.rs` — Codex-side
    proof path for file and keyring CLI auth storage behavior.
  - `~/workspace/codex/codex-rs/rmcp-client/src/oauth.rs` tests — Codex-side
    proof path for `.credentials.json` fallback behavior.
  - `~/workspace/codex/codex-rs/core/tests/suite/subagent_notifications.rs` —
    Codex-side proof path for child config inheritance, though not yet for MCP
    tool visibility specifically.

## 3.3 Decision gaps that must be resolved before implementation

- Locked in this pass: the small shared boundary is adapter home prep, native
  invoke, session/result plumbing, and startup blocker classification. Shared
  runtime keeps the run-home shell, compiled agents, allowed skills, copied
  policy snapshot, run state, and blocker reporting.
- Locked in this pass: Rally should regenerate run-owned Codex config from the
  prepared run home, not from live repo state. The adapter should read
  `home/mcps/*/server.toml`, write the root `config.toml`, and project only the
  host auth-linked inputs Codex really needs.
- Locked in this pass: native Codex session startup is the required-MCP gate.
  Rally should not add a second MCP probe if native startup already gives the
  real fail-loud answer.
- Locked in this pass: shared Rally code should not implement a client-agnostic
  MCP OAuth discovery or registration path. External guidance differs across
  spec versions and real clients already own this logic, so the adapter must
  keep it native.
- Locked in this pass: direct CLI proof now shows that a parent and spawned
  child from the same prepared home can complete the same MCP-dependent task.
  That is enough to treat inner-runner inheritance as settled for the v1 plan.
- Locked in this pass: direct CLI probing supports a file-backed v1 auth story
  only. Wider auth continuity is out of v1 unless a direct Codex proof lands.
- No plan-shaping architecture blocker remains after this second deep-dive.
  Remaining hardening work is proof-strengthening only:
  - a Codex-side test or richer trace that shows exact child MCP tool use or
    exact tool-set equality
  - direct proof for any auth mode broader than projected `auth.json` plus
    projected `.credentials.json`
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:external_research:start -->
# External Research (best-in-class references; plan-adjacent)

> Goal: anchor the plan in idiomatic, broadly accepted practices where
> applicable. This section intentionally avoids project-specific internals.

## Topics researched (and why)

- MCP transport split — this plan must support both local stdio servers and
  remote HTTP servers without losing valid config shape.
- MCP authorization discovery and credential scope — this plan touches auth and
  needs to avoid inventing a shared broker that fights native client behavior.
- Claude Code MCP configuration model — this plan must stay clean for a later
  `claude_code` adapter instead of freezing Codex file rules into Rally core.

## Findings + how we apply them

### MCP transport split

- Best practices (synthesized):
  - MCP defines two standard transports: `stdio` and Streamable HTTP.
  - Clients should support `stdio` whenever possible, but remote HTTP remains a
    first-class transport.
  - `stdio` servers are local subprocesses. `stderr` is a logging channel, not
    a proof that startup failed.
- Adopt for this plan:
  - Keep the local run-home launch model for Codex-owned `stdio` servers.
  - Treat transport-specific config as first-class data. The native config
    writer must preserve subprocess fields, env maps, HTTP headers, and nested
    transport settings without flattening them away.
  - Keep raw `stderr` and native startup output as evidence for blocker
    classification instead of using a brittle string-only wrapper.
- Reject for this plan:
  - Do not reduce Rally MCP definitions to a narrow shared shape such as only
    `command` and `args`.
  - Do not add a shared Rally transport abstraction that hides native client
    details the adapter still needs.
- Pitfalls / footguns:
  - Old HTTP+SSE compatibility still exists in the ecosystem. Rally should not
    freeze deprecated transport assumptions into the shared layer.
- Sources:
  - MCP Transports specification —
    https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
    — official protocol definition for transport types and behavior.
  - Claude Code MCP docs — https://code.claude.com/docs/en/mcp — official
    client docs showing both local and remote server setup surfaces.

### MCP authorization discovery and credential scope

- Best practices (synthesized):
  - MCP authorization is transport-level guidance for HTTP-based transports.
    `stdio` transports should use environment or locally acquired credentials
    instead of the HTTP OAuth flow.
  - Current MCP guidance uses OAuth 2.1, PKCE, protected resource metadata, and
    authorization-server metadata. Client registration and token state are tied
    to the specific authorization server.
  - Tokens must be audience-bound and must not be reused across unrelated
    servers or upstream APIs.
- Adopt for this plan:
  - Keep shared Rally code out of OAuth discovery, registration, and token
    reuse logic. The adapter should project native config and let the native
    client perform its own discovery flow.
  - Treat file-backed auth state as native adapter state, not as a shared Rally
    auth broker.
  - Keep `stdio` auth and HTTP OAuth auth as separate concerns in the plan and
    in tests.
- Reject for this plan:
  - Do not build one shared Rally OAuth discovery chain for all adapters.
  - Do not assume one client registration or one token is portable across MCP
    servers or authorization servers.
- Pitfalls / footguns:
  - MCP auth guidance is still evolving. The current draft requires protected
    resource metadata for discovery, while the older 2025-03-26 spec centers
    authorization-server metadata. That disagreement is another reason to keep
    discovery native to each adapter instead of freezing one shared Rally
    implementation.
- Sources:
  - MCP Authorization draft —
    https://modelcontextprotocol.io/specification/draft/basic/authorization —
    current official draft for HTTP auth flow, discovery order, PKCE, and token
    handling.
  - MCP Authorization 2025-03-26 —
    https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization
    — official older stable version that shows the discovery surface is still
    moving.
  - Understanding Authorization in MCP —
    https://modelcontextprotocol.io/docs/tutorials/security/authorization —
    official tutorial that clearly separates local `stdio` auth from HTTP OAuth.

### Claude Code MCP configuration model

- Best practices (synthesized):
  - Claude Code keeps MCP config in native Claude files and scopes, not in a
    shared cross-client format.
  - User and local MCP config live in `~/.claude.json`; project-shared MCP
    config lives in `.mcp.json`; managed installs can also add managed MCP
    policy files.
  - Missing env vars can fail config parsing, and some auth-related fields are
    helper commands rather than static file projection.
- Adopt for this plan:
  - Keep the shared Rally seam about policy copy, startup blocker reporting, and
    adapter invocation, not about any specific native config file name.
  - Leave room in the adapter seam for helper-based auth and client-specific
    settings instead of assuming every adapter can be bootstrapped by symlinking
    the same files.
  - Keep Rally policy and native adapter config separate so a future Claude
    adapter can map the same policy into Claude-native scopes and files.
- Reject for this plan:
  - Do not make `config.toml`, `auth.json`, or `.credentials.json` part of the
    shared Rally contract.
  - Do not assume Codex-style auth projection is the future shape for every
    adapter.
- Pitfalls / footguns:
  - Client-native config can fail early on missing env or helper issues. Rally
    should surface those as fail-loud startup blockers instead of silently
    degrading MCP availability.
- Sources:
  - Claude Code MCP docs — https://code.claude.com/docs/en/mcp — official docs
    for MCP server configuration and scope.
  - Claude Code settings docs — https://code.claude.com/docs/en/settings —
    official docs for config file locations, managed policy, and helper-based
    auth settings.

## Adopt / Reject summary

- Adopt:
  - Use a lossless native config writer and test both local `stdio` and remote
    HTTP server shapes.
  - Keep OAuth discovery, registration, and token handling adapter-native.
  - Keep shared Rally policy separate from native adapter config so Codex and
    Claude can each keep their own file and auth rules.
- Reject:
  - No shared Rally OAuth broker or shared discovery engine.
  - No transport-flattened MCP schema that loses env maps, headers, or nested
    native settings.
  - No Codex-only file assumptions in the shared adapter contract.

## Decision gaps that must be resolved before implementation

- No architecture blocker remains from external research after the second
  deep-dive. The remaining work is proof hardening only:
  - richer child MCP traces or a Codex-side equality test
  - direct proof before widening auth support beyond the file-backed v1 scope
<!-- arch_skill:block:external_research:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- `prepare_run_home_shell()` always creates
  `runs/<run-id>/home/{agents,skills,mcps,sessions,artifacts,repos}`.
- `materialize_run_home()` refreshes compiled agents into `home/agents/` and
  copies allowlisted skills and MCP folders into `home/skills/` and
  `home/mcps/`.
- Shared code then writes native Codex files at the run-home root:
  `home/config.toml`, `home/auth.json`, and `home/.credentials.json`.
- Important drift: generated `home/config.toml` is not built from the copied
  `home/mcps/*/server.toml` snapshot. `_write_codex_config()` rereads repo
  `mcps/*/server.toml` directly, so the run home is not yet the full prepared
  source of truth.
- Important lossiness: `_render_toml_value()` only supports booleans, ints,
  strings, and lists. Valid Codex MCP shapes that need maps or nested tables
  cannot be represented today.

## 4.2 Control paths (runtime)

1. `run_flow()` or `resume_run()` reaches `_execute_until_stop()` after flow
   build and run-state setup.
2. `_execute_until_stop()` calls `materialize_run_home()` once before the turn
   loop.
3. `materialize_run_home()` always resyncs agents, skills, MCP folders, root
   `config.toml`, and auth projection before it checks `.rally_home_ready`, so
   resume already refreshes capabilities.
4. `_execute_single_turn()` prepares turn artifacts, builds the prompt, loads
   the prior session from `home/sessions/`, and calls `_invoke_codex()`.
5. `_invoke_codex()` shells `codex exec ... -C <run_home>` and injects
   `CODEX_HOME=<run_home>` through `build_codex_launch_env()`.
6. `_invoke_codex()` also passes `-c project_doc_max_bytes=...` even though the
   same setting was already written into `home/config.toml`.
7. Success path loads the final response with Codex-specific result code and
   records the session. A non-zero exit becomes a blocked run with a generic
   exec failure reason.

## 4.3 Object model + key abstractions

- `runtime.adapter` already exists in the flow model, so the selector for a
  shared adapter seam is already present.
- Shared runtime still imports Codex-specific launch, event parse, session
  store, and final-response code directly from `rally.adapters.codex.*`.
- Shared home materialization mixes two jobs: Rally policy copy and Codex
  native projection.
- There is no small adapter contract yet for native home prep, turn invoke,
  session artifact handling, final response loading, and startup failure
  classification.
- Because that seam does not exist yet, Codex details leak across the shared
  runner instead of staying behind one owner.

## 4.4 Observability + failure behavior today

- `logs/adapter_launch/*.json` already captures the command, cwd, timeout, and
  the visible `RALLY_*` / `CODEX_HOME` env slice.
- Per-turn stdout and stderr already land in turn artifacts, so Rally has the
  raw data it needs to classify startup failures later.
- Direct Codex proof shows native required-MCP startup already fails loud before
  normal work. Rally does not reuse that signal cleanly yet.
- `_format_exec_failure()` turns every non-zero exit into a generic blocker
  string. It does not tell the operator whether the failure came from a
  required MCP, missing auth, timeout, or some other startup error.
- `_seed_codex_auth()` hardcodes the host source as `~/.codex` and symlinks out
  of the run home. It does not resolve the host home the way Codex itself does.
- `project_doc_max_bytes` has duplicate truth today: once in `home/config.toml`
  and again in the CLI command.

## 4.5 UI surfaces (ASCII mockups, if UI work)

No new UI surface is planned.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- Rally keeps the same run-home shell and copied policy snapshot:
  `home/agents/`, `home/skills/`, `home/mcps/`, `home/sessions/`,
  `home/artifacts/`, and `home/repos/`.
- `home/mcps/<name>/server.toml` becomes the prepared policy input the adapter
  reads when it builds native config. Once copied, Rally should not need to
  reread repo `mcps/` to explain the prepared state.
- The Codex adapter owns every native file at the run-home root, including
  `config.toml`, `auth.json`, `.credentials.json`, and any future
  Codex-specific support files.
- `config.toml` becomes the single source of truth for run-owned Codex settings
  such as `project_doc_max_bytes` and the allowed `mcp_servers.*` entries. The
  CLI should stop re-overriding the same setting.

## 5.2 Control paths (future)

1. Shared home materialization prepares the shell, compiled agents, mandatory
   and allowed skills, and the copied `home/mcps/` policy snapshot.
2. Shared runtime calls one small adapter hook after the copy step and again on
   resume. For Codex, that hook resolves the host native home, reads supported
   host config and auth inputs, and writes the run-home native files.
3. `_execute_single_turn()` routes through adapter-owned session, artifact, and
   invoke helpers instead of Codex imports in the shared runner.
4. Native Codex session startup stays the required-MCP gate. Rally does not add
   a second MCP probe or retry loop.
5. If startup fails, the adapter maps the native failure into a shared blocker
   shape. Shared runtime writes run state, issue notes, and logs from that
   blocker.
6. If startup succeeds, shared runtime continues with the same turn-result flow
   it already owns.

## 5.3 Object model + abstractions (future)

- Keep the abstraction small. Add a thin adapter bundle or protocol keyed by
  `runtime.adapter`. Do not build a large plugin system.
- Shared runtime owns the run-home shell, compiled agents, mandatory and
  allowed skill sync, the copied policy snapshot in `home/mcps/`, prompt build,
  run state transitions, issue and event records, guarded git repo checks, and
  final turn-result application.
- The adapter owns host native-home resolution, native config generation, auth
  projection, transport-specific auth discovery settings, invoke command
  details, event parsing, session persistence, final response loading, and
  startup error classification.
- Codex can reuse the current `launcher.py`, `session_store.py`,
  `event_stream.py`, and `result_contract.py`, but the shared runner should
  talk only to the thin adapter seam.

## 5.4 Invariants and boundaries

- Shared runtime never writes adapter file names directly.
- `home/mcps/` is the Rally policy snapshot. Root `config.toml` is the
  adapter-native materialization of that snapshot.
- Use a lossless native config writer. Do not keep the current hand-built TOML
  serializer if it cannot express maps or nested tables. Preserve env maps,
  HTTP headers, and nested native settings without flattening them away.
- Use native Codex startup as the only required-MCP gate.
- Shared Rally code does not implement a common OAuth discovery or registration
  engine. Native adapters keep their own transport-specific auth flow.
- V1 supported auth surfaces are only the ones directly proved to work from a
  changed `CODEX_HOME`: projected `auth.json`, plus projected
  `.credentials.json` when present for file-backed MCP OAuth. Any keyring-only
  mode stays unsupported or blocked until a direct Codex proof lands.
- Inner-runner inheritance is accepted at the task level for v1: a child from
  the same prepared home must be able to complete the same MCP-dependent task,
  not just inherit config on paper.
- Host native-home lookup must follow Codex rules, using `CODEX_HOME` when set
  and the default native home otherwise.
- Parent and child must end up with the same allowed MCP story. Exact child
  tool-set equality is a hardening target, but it is not the v1 architecture
  gate once the direct parent-plus-child MCP task proof exists.
- Future Claude support gets the same shared seam, but its own native files and
  auth rules.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No new UI surface is planned.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Shared home prep | `src/rally/services/home_materializer.py` | `materialize_run_home()` | Shared code copies policy and also writes Codex-native files | Split after `_copy_allowed_skills_and_mcps()` into a small adapter home-prep hook; keep refresh-before-ready behavior | Keep shared runtime generic while preserving resume refresh | `adapter.prepare_home(...)` or same-sized equivalent | `tests/unit/test_runner.py` and new adapter home-prep tests |
| Codex config projection | `src/rally/services/home_materializer.py` | `_write_codex_config()` | Shared code hand-writes `config.toml` from repo `mcps/*/server.toml` | Move config generation into the Codex adapter, read copied `home/mcps/*/server.toml`, make `config.toml` the single source of truth, and use a lossless TOML writer | Make the run home tell the full story and keep full Codex MCP shape support | Codex-native config builder | New Codex home-prep tests |
| Codex auth projection | `src/rally/services/home_materializer.py` | `_seed_codex_auth()` | Shared code hardcodes `~/.codex` and symlinks `auth.json` / `.credentials.json` | Move auth projection into the Codex adapter, resolve host home with Codex rules, project only supported auth surfaces, and block unsupported modes clearly | Keep auth native and honest | Codex-native auth projector | New auth projection tests and direct Codex proof notes |
| OAuth discovery boundary | `src/rally/services/runner.py`, `src/rally/adapters/codex/*` | shared startup path | No explicit rule prevents shared Rally code from growing client-agnostic OAuth logic later | Keep auth discovery, registration, and token handling inside the adapter; shared runtime only sees startup blocker shape | External MCP guidance and native clients differ enough that shared logic would drift fast | adapter-owned auth-discovery boundary | Runner blocker tests and adapter tests |
| Shared runner orchestration | `src/rally/services/runner.py` | direct imports from `rally.adapters.codex.*` | Shared runner calls Codex launch, session, parse, and result helpers directly | Route turn lifecycle through the adapter bundle for session handling, invoke, result loading, and startup failure classification | Stop Codex details leaking across the shared runner | Thin adapter runner contract | `tests/unit/test_runner.py`, `tests/unit/test_result_contract.py`, and `tests/unit/test_codex_event_stream.py` |
| Startup blocker path | `src/rally/services/runner.py` | `_execute_single_turn()` and `_format_exec_failure()` | Every non-zero exit becomes a generic exec blocker | Accept an adapter-classified startup blocker shape and preserve raw stderr and launch logs | Make required MCP and auth failures clear before operators dig through raw logs | shared startup-blocker shape | `tests/unit/test_runner.py` |
| Codex invoke details | `src/rally/services/runner.py`, `src/rally/adapters/codex/launcher.py` | `_invoke_codex()` and launch record helpers | Shared runner owns the command and duplicates `project_doc_max_bytes` in CLI flags | Move command build behind the Codex adapter, keep `CODEX_HOME=<run_home>`, keep launch records, and remove the duplicate CLI override once the config path is tested | One source of truth for native config | Codex adapter invoke helper | `tests/unit/test_launcher.py` and runner command tests |
| Adapter registry | `src/rally/adapters/` | new registry or protocol file(s) | No common adapter seam exists yet | Add the smallest lookup or protocol keyed by `runtime.adapter` | Fit Codex now and Claude later without a big framework | adapter bundle lookup | New adapter registry tests |
| Flow validation | `src/rally/services/flow_loader.py`, `src/rally/domain/flow.py` | adapter config parsing | Flow model already has `runtime.adapter`, but the runtime contract is still implicit | Tighten validation only where the new adapter seam needs it, without baking in Codex file names | Keep the flow contract generic | adapter-facing runtime contract | `tests/unit/test_flow_loader.py` |
| Durable docs | `docs/RALLY_MASTER_DESIGN_2026-04-12.md`, `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md` | lasting runtime docs | Current docs still describe Codex MCP auth and readiness as unresolved | Update the docs in the same pass as the code | Keep lasting repo truth honest | docs only | doc review |

## 6.2 Migration notes

Canonical owner path / shared code path:

- `src/rally/services/home_materializer.py` keeps the run-home shell, compiled
  agents, mandatory and allowed skills, and the copied MCP policy snapshot.
- `src/rally/services/runner.py` keeps shared orchestration and blocker
  reporting only.
- `src/rally/adapters/codex/` becomes the only owner of native Codex home prep,
  invoke details, session handling, result loading, and startup classification.

Deprecated APIs or ownership lines:

- Shared helpers `_write_codex_config()` and `_seed_codex_auth()` should retire
  from `home_materializer.py` once the adapter-owned replacements land.
- Shared direct imports from `rally.adapters.codex.*` inside `runner.py` should
  retire behind the small adapter bundle.
- The duplicate CLI override `-c project_doc_max_bytes=...` should retire once
  the adapter-owned `config.toml` writer is covered by tests.

Delete list:

- Delete the shared Codex-native file writers after the adapter-owned path is
  live and covered.
- Delete any replacement-proof helper or shim that would probe MCP readiness
  outside native Codex startup.
- Delete or rewrite any stale doc text that still says Codex MCP auth or inner
  runners are unresolved after the implementation lands.

Capability-replacing harnesses to delete or justify:

- Do not add a shared Rally OAuth discovery chain.
- Do not add a second MCP readiness subprocess.
- Do not keep the hand-built TOML serializer if it cannot preserve full native
  MCP shapes.

Live docs, comments, and instructions to update or delete:

- `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
- `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`
- `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md`
- Any code comment near the new adapter seam that still teaches shared
  Codex-specific ownership

Behavior-preservation signals for refactors:

- Keep the current refresh-before-ready behavior. Adapter home prep must still
  run on resume before `.rally_home_ready` can short-circuit setup work.
- Use the copied `home/mcps/*/server.toml` files as the input for native config
  generation so the run home tells the full capability story.
- Cover at least one local `stdio` MCP config with env fields and one remote
  HTTP MCP config with structured auth or header fields before calling the
  config writer done.
- If a host auth mode cannot be proved from a changed `CODEX_HOME`, fail with a
  clear blocker instead of guessing.
- Keep the shared adapter seam small. A lightweight factory or protocol is
  enough.
- Sync the master, CLI, phase, and Claude-facing docs in the same pass when the
  code lands.

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared home prep | `src/rally/services/home_materializer.py` | Shared layer prepares Rally-owned home contents and copied policy; adapters write native files | Prevents future adapter-specific file rules from leaking back into shared prep | include |
| Shared runner | `src/rally/services/runner.py` | Runner talks to one thin adapter bundle instead of importing Codex helpers directly | Prevents a second Codex-shaped control path and keeps Claude support clean | include |
| Native config writing | `src/rally/services/home_materializer.py`, future adapter-owned config builder | Read copied `home/mcps/*/server.toml` as the SSOT and use a lossless native writer | Prevents repo-state drift and field loss in transport or auth config | include |
| Startup blocking | `src/rally/services/runner.py`, `src/rally/adapters/codex/*` | Native startup is the gate; shared runtime only classifies and reports | Prevents duplicate readiness probes and contradictory blocker paths | include |
| Auth discovery | shared runtime plus future adapters | Keep OAuth discovery and registration native to each adapter | Prevents Rally core from freezing one client-specific auth flow | include |
| Durable docs | Rally master, CLI, phase, and Claude adapter docs | Teach the same shared seam and native-adapter ownership story | Prevents docs drift after code cutover | include |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks/runtime shims - the system must work correctly or fail loudly (delete superseded paths). The authoritative checklist must name the actual chosen work, not unresolved branches or "if needed" placeholders. Prefer programmatic checks per phase; defer manual/UI verification to finalization. Avoid negative-value tests and heuristic gates (deletion checks, visual constants, doc-driven gates, keyword or absence gates, repo-shape policing). Also: document new patterns/gotchas in code comments at the canonical boundary (high leverage, not comment spam).

## Phase 1 — Shared adapter seam and owner cut

* Goal: Put one small adapter boundary between shared Rally runtime and native
  Codex behavior without changing the live Codex behavior yet.
* Work: Add a thin adapter bundle keyed by `runtime.adapter`. Route
  `runner.py` through that bundle for home prep, invoke, session handling,
  result loading, and startup-failure classification. Keep
  `home_materializer.py` responsible for the run-home shell, compiled agents,
  mandatory and allowed skills, and the copied `home/mcps/` snapshot, then
  call the adapter hook after copy and on resume. Keep launch logs, run-state
  writes, and refresh-before-ready behavior the same. Do not add a plugin
  system, a second runner path, or a shared MCP or auth helper layer.
* Verification (required proof): `uv run pytest tests/unit -q` stays green.
  Extend `tests/unit/test_runner.py`, `tests/unit/test_flow_loader.py`,
  `tests/unit/test_launcher.py`, `tests/unit/test_result_contract.py`, and
  `tests/unit/test_codex_event_stream.py` so the shared runner no longer
  depends on direct Codex imports, resume still refreshes before
  `.rally_home_ready`, launch records still capture the same command, cwd, and
  env slice, and the seamed runner still uses the same result and event
  surfaces.
* Docs/comments (propagation; only if needed): Add one short boundary comment
  at the new adapter bundle that explains shared ownership versus native
  adapter ownership. Rewrite any nearby stale comment that still teaches shared
  Codex ownership.
* Exit criteria: Shared runtime selects an adapter by `runtime.adapter` and
  talks only to that seam. No shared service file imports Codex helpers
  directly for turn execution. There is one live control path, not a legacy
  path plus a seamed path.
* Rollback: Revert the seam cut as one unit. Do not keep a half-migrated
  runner where shared code and the adapter both own the same step.

## Phase 2 — Codex-native home prep, config, auth, and startup gate

* Goal: Make the Codex adapter the only owner of native Codex home files, auth
  projection, and startup blocker mapping.
* Work: Move `config.toml` generation, auth projection, and startup failure
  classification into `src/rally/adapters/codex/`. Build `config.toml` only
  from copied `home/mcps/*/server.toml` plus run-owned Codex settings. Replace
  the current lossy TOML writer with a lossless writer that preserves env maps,
  nested tables, headers, and auth settings. Resolve the host Codex home with
  Codex rules, project only `auth.json` and `.credentials.json`, and block
  unsupported auth modes instead of guessing. Remove the duplicate CLI
  `project_doc_max_bytes` override. Delete `_write_codex_config()`,
  `_seed_codex_auth()`, and any extra readiness probe once the adapter-owned
  path works.
* Verification (required proof): `uv run pytest tests/unit -q` stays green
  with added coverage in `tests/unit/test_launcher.py` and
  `tests/unit/test_runner.py` for one `stdio` MCP with env or cwd fields, one
  remote HTTP MCP with nested header or auth fields, supported file-backed
  auth projection, unsupported auth blocking, and adapter-classified startup
  blockers. Re-run the direct Codex CLI proofs for projected auth, required
  broken MCP failure, and prepared-home config loading before calling this
  phase done.
* Docs/comments (propagation; only if needed): Keep comments at the Codex
  home-prep boundary short and specific. Delete any live comment that still
  says shared Rally writes Codex-native files.
* Exit criteria: Shared Rally code no longer writes `config.toml`, `auth.json`,
  or `.credentials.json`. Native Codex startup is the only required-MCP gate.
  The prepared run home, not repo `mcps/`, explains the live Codex config.
* Rollback: Revert the native-home cut as one unit. Do not keep duplicated
  config writers, duplicated auth projectors, or a backup readiness path.

## Phase 3 — Rally proof mirror for required MCP and inner runners

* Goal: Mirror the plan-shaping Codex proofs in Rally-owned tests so the
  shipped support envelope is enforced by the repo, not only by notes in this
  doc.
* Work: Add a new `tests/integration/` suite with one Rally CLI proof for a
  broken required MCP and one Rally CLI proof for the parent-plus-child MCP
  task story. Use a local MCP server so the proof stays local and deterministic
  in CI or dev. The second proof must prepare a Codex run home with a local
  filesystem MCP, have the parent use the tool, spawn a child from the same
  prepared home, and check that the child completes the same MCP-backed task.
  Keep the v1 auth scope explicit: file-backed projection only. Do not widen
  support to keyring-only auth in this phase.
* Verification (required proof): `uv run pytest tests/unit -q` stays green.
  Run the new `uv run pytest tests/integration -q` suite and require both real
  Codex-backed MCP proofs to pass on the prepared test path. Keep the direct
  Codex CLI child-runner proof available as the outside-the-repo cross-check
  until the Rally integration proof is stable.
* Docs/comments (propagation; only if needed): Update any test note or inline
  fixture comment that still says child MCP inheritance or file-backed auth
  scope is unproved.
* Exit criteria: Rally has repo-owned proof for the required-MCP blocker story
  and the parent-plus-child MCP task story. The v1 support envelope is
  enforced by tests, and the remaining hardening gap is only exact tool-set
  equality.
* Rollback: Revert each new integration proof together with the code it
  validates if the environment cannot support deterministic runs yet. Do not
  keep a claimed support story that only lives in manual notes.

## Phase 4 — Durable doc sync and cutover cleanup

* Goal: Finish the cutover by deleting stale truth and teaching the same
  ownership model everywhere Rally keeps lasting guidance.
* Work: Update `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
  `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`,
  `docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md`, and
  `docs/RALLY_CLAUDE_CODE_FIRST_CLASS_ADAPTER_SUPPORT_2026-04-13.md` so they
  all say the same thing: shared Rally owns policy copy, state, and blocker
  reporting; native adapters own MCP config, auth, and startup mapping. Remove
  stale comments or doc text that still describe shared Codex file writing,
  unresolved Codex MCP auth, or unresolved inner-runner inheritance. Keep
  Claude guidance generic where the code is still Codex-only.
* Verification (required proof): Read the touched docs against the landed code
  and test results. Re-run `uv run pytest tests/unit -q` and
  `uv run pytest tests/integration -q` after the cleanup so the final docs pass
  is not hiding a late code change.
* Docs/comments (propagation; only if needed): This phase is the propagation
  pass. Delete dead explanation instead of preserving both old and new stories.
* Exit criteria: No live Rally doc or high-leverage code comment teaches the
  old ownership model. The shipped code, tests, and lasting docs all describe
  the same v1 support boundary.
* Rollback: Revert the doc sync with the matching code change if the cutover
  does not land. Do not leave docs claiming behavior that the repo does not
  ship.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- Keep `uv run pytest tests/unit -q` as the main regression floor.
- Add focused tests for the adapter seam, adapter-owned home prep, startup
  blocker failures, resume refresh behavior, launch-record preservation, and
  the shared result and event surfaces used by the seamed runner.
- Add config-generation tests that prove Rally preserves one `stdio` server
  with env or cwd fields and one remote HTTP server with nested header or auth
  fields.
- Add unit coverage for supported file-backed auth projection and clear
  blocking of unsupported auth modes.

## 8.2 Integration tests (flows)

- Add a new `tests/integration/` suite and run it with
  `uv run pytest tests/integration -q`.
- Use the Rally CLI path and the same flow-owned allowlists the runtime will
  really ship with.
- Keep two real Codex-backed proofs in that suite:
  a broken required MCP must block before work starts, and a parent plus child
  from the same prepared home must both complete the same local MCP-backed
  task.

## 8.3 E2E / device tests (realistic)

- No new device harness is planned.
- Keep the direct Codex CLI proof runs as an outside-the-repo cross-check until
  the Rally integration suite is stable.
- If live remote HTTP OAuth proof needs a manual run, keep it small and make
  the exact blocker plain if the environment cannot prove it yet.
- Do not block v1 on keyring continuity unless the scoped v1 auth story expands
  beyond the proved file-backed path.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Land the shared boundary and Codex path first.
- Keep the rollout local and CLI-first.
- Do not claim Claude support from this change, but keep the shared boundary
  ready for it.

## 9.2 Telemetry changes

- No new telemetry system is planned.
- Reuse existing launch records and run logs.
- If needed, add a small clear record of required-capability blockers.

## 9.3 Operational runbook

- Operators should see one clear pre-turn blocker when a required MCP or auth
  input is missing.
- The run-home files should stay enough to explain what Rally prepared for the
  run.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, `planning_passes`, and helper-block drift
  - `# TL;DR`
  - `# 0)` through `# 10)`
  - agreement across owner path, migration scope, phase order, verification burden, and rollout truth
- Findings summary:
  - the main plan was already aligned on the native-adapter MCP story, fail-loud startup, file-backed v1 auth scope, and Claude-compatible shared seam
  - one real ownership drift remained: Phase 1 and migration notes had narrowed shared home prep too far and silently dropped compiled-agent and skill refresh work
  - one proof drift remained: Phase 1 verification named fewer test surfaces than the call-site audit marked as impacted
  - one wording drift remained: the North Star invariant for parent and child MCP behavior was stricter than the accepted v1 task-level proof floor
- Integrated repairs:
  - updated `planning_passes` to show that planning is complete and the next move is implementation
  - restored shared ownership of compiled agents and allowed skills across the TL;DR and Sections 5, 6, and 7 so the owner path matches end to end
  - aligned Phase 1 and Section 8 verification with the impacted result-contract and event-stream test surfaces
  - normalized Section `3.3` back to the canonical decision-gap heading and aligned the parent-child invariant with the accepted v1 proof floor
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

## 2026-04-13 - Keep MCP support native to each adapter

Context

Rally needs a clean MCP story for Codex runners now, but it also needs to stay
clean for future Claude support.

Options

- Put Codex-native files and auth rules directly into shared runtime code.
- Build one shared Rally auth and MCP broker for every adapter.
- Keep the shared layer small and let each adapter project Rally policy into
  its own native MCP and auth setup.

Decision

Keep the shared layer small and let each adapter project Rally policy into its
own native MCP and auth setup.

Consequences

- Codex can keep its native `CODEX_HOME` model.
- Future Claude support can follow the same shared shape without copying Codex
  file rules.
- Some auth behavior will stay adapter-specific on purpose.

Follow-ups

- Deep-dive the current Codex auth and MCP storage rules.
- Lock the smallest shared adapter boundary that also fits Claude later.

## 2026-04-13 - Use native Codex startup as the required-MCP gate

Context

Direct Codex CLI proof now shows that a broken required MCP already fails loud
before normal work starts. Rally does not need a second MCP probe if Codex
native startup already gives the real answer.

Options

- Add a separate Rally-owned readiness subprocess before each turn.
- Let the real Codex startup path stay the gate, then classify the native
  failure for Rally state and issue notes.

Decision

Let the real Codex startup path stay the gate, then classify the native failure
for Rally state and issue notes.

Consequences

- The design stays simpler and more native.
- Required-MCP blockers come from the same path that real work uses.
- Rally still needs a clean shared blocker shape so operators do not have to
  read raw stderr every time.

Follow-ups

- Add an adapter-owned startup blocker classifier.
- Prove the same story through Rally tests.

## 2026-04-13 - Keep v1 run-home auth support file-backed until more is proved

Context

Direct proof exists for projected `auth.json` with a changed `CODEX_HOME`.
Codex source also shows a file fallback for `.credentials.json`. Keyring-only
portability from a changed `CODEX_HOME` is still not directly proved.

Options

- Claim support for every native Codex auth mode now.
- Support only the directly proved file-backed path in v1 and block anything
  wider until it is proved.

Decision

Support only the directly proved file-backed path in v1 and block anything
wider until it is proved.

Consequences

- v1 is narrower, but honest.
- Rally does not need a new shared auth broker.
- We avoid shipping a path that only works by accident on one machine.

Follow-ups

- Add direct Codex proof for any extra auth mode before widening support.
- Make unsupported auth modes fail with a clear blocker, not a soft fallback.

## 2026-04-13 - Keep OAuth discovery native to each adapter

Context

External MCP guidance is transport-specific and still moving. The current MCP
draft puts protected resource metadata at the center of discovery, while the
older 2025-03-26 spec centers authorization-server metadata. Claude Code also
keeps its own native MCP config and auth helper model.

Options

- Build one shared Rally OAuth discovery and registration engine.
- Keep shared Rally code at policy and blocker reporting, and let each adapter
  keep its native auth discovery and config rules.

Decision

Keep shared Rally code at policy and blocker reporting, and let each adapter
keep its native auth discovery and config rules.

Consequences

- Rally avoids freezing one auth flow that may already be wrong for another
  adapter.
- Codex and Claude can each keep their native config layering and callback
  rules.
- The adapter seam must be strong enough to carry transport-specific auth data.

Follow-ups

- Add transport-shape coverage to config-generation tests.
- Keep shared runtime file-name-free and discovery-free as Claude support lands.

## 2026-04-13 - Use task-level inner-runner MCP proof as the v1 acceptance floor

Context

The user-facing requirement is that inner runners should work when Rally copies
the right MCP config into the run home. Direct Codex source and tests show
spawned-child config inheritance, and a direct CLI run now shows a parent using
an MCP server and a spawned child from the same prepared home completing the
same MCP-dependent task.

Options

- Require exact event-level child MCP tool traces or exact tool-set equality
  before the architecture can move forward.
- Accept practical parent-plus-child MCP task success from the same prepared
  home as the v1 gate, and keep richer child trace proof as hardening work.

Decision

Accept practical parent-plus-child MCP task success from the same prepared home
as the v1 gate, and keep richer child trace proof as hardening work.

Consequences

- The plan now has direct proof for the real v1 behavior instead of only source
  inference.
- We can move to `phase-plan` without pretending the child story is still
  unproved.
- Exact child MCP tool visibility is still worth adding later if it can be done
  cleanly.

Follow-ups

- Mirror the same parent-plus-child task proof in Rally tests where feasible.
- Add richer child trace proof later if it improves confidence without adding
  harness theater.
