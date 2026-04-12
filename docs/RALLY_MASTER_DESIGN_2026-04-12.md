# Rally Master Design

Date: 2026-04-12
Status: working draft
Purpose: establish the core design direction for Rally before implementation hardens the wrong abstractions.

## Repo Guide

This section exists to keep the three neighboring repos conceptually separate.

- `../paperclip`
  - What it is to us: the inspiration and reference implementation for orchestration concerns.
  - What we are borrowing: resumable CLI sessions, issue-centered work tracking, single-owner execution, skill injection, home-binding rigor, and durable run lifecycle ideas.
  - What it is not to us: the product shape we plan to copy. Rally is not trying to become the same GUI-centric company control plane.

- `../doctrine`
  - What it is to us: the authoring language and compiler substrate for Rally agent doctrine.
  - What we are borrowing: source-owned `.prompt` files, deterministic Markdown emission, typed inputs and outputs, workflow law, currentness, route-only turns, review semantics, and flow visualization.
  - What it is not to us: a complete runtime runner. Doctrine gives us authored semantics, not the full filesystem-native orchestration machine we want.

- `../paperclip_agents`
  - What it is to us: the first real set of use cases and pressure tests for the system.
  - What we are borrowing: the on-disk doctrine layout, generated role-home pattern, explicit skill allowlists, and practical examples of strict handoff discipline.
  - What it is not to us: Rally's product/domain model. We should not bake in lessons, core-dev, PRD-factory, poker, `psmobile`, or any of the current role names as framework concepts.

- `./`
  - What it is to us: the new general-purpose framework repo we are designing and will implement.
  - What it should become: a CLI-native, filesystem-native, Doctrine-native multi-agent flow runner that keeps its real source of truth on disk.

## North Stars

These are the constraints Rally should keep returning to.

### 1. Filesystem Truth

The real source of truth for runs lives on disk in normal files the operator can inspect and edit.
Rally should not hide core workflow state behind a GUI or a database-first control plane.

### 2. Repo Root Is The Rally Home

Rally is always run from the base of a Rally repo.

That repo root is not configurable at runtime and is not split into separate workspace roots.
Rally should simply expect the directories it needs to exist there:

- `flows/`
- `skills/`
- `mcps/`
- `runs/`

No workspace mode.
No configurable skills root.
No configurable MCP root.
No repo URL or repo ref fields in the core run model.

### 3. Doctrine-Native `.prompt` Authoring

Agent instruction source is authored in Doctrine `.prompt` files.
Compiled Markdown exists only as generated compatibility readback, not as an authored instruction surface.

### 4. No Side Doors Into Agents

If instruction prose reaches an agent, it must come from the declared `.prompt` graph for that flow.

Rally should explicitly ban:

- shared Markdown overlays
- ad hoc `.md` files mounted into agents as extra instruction payload
- repo-root `AGENTS.md` bleed-through
- random docs or scratch files entering agent homes implicitly
- hidden runtime prompt augmentation that is not declared in the `.prompt` source tree

`flow.yaml`, `run.yaml`, session sidecars, and similar runtime files may control orchestration, but they must not inject new instruction prose into agents.

### 5. Home Is The Whole World

Each run gets one canonical home directory.

The setup step prepares that home before the first agent runs.
After that:

- agents assume home is already prepared for them
- all paths used by agents are relative to home
- skills available to agents are materialized into home from repo-root `skills/`
- MCP definitions available to agents are materialized into home from repo-root `mcps/`
- checked out repos, worktrees, env files, and generated artifacts that agents need live in home
- agents do not escape home

No machine-global skills.
No machine-global MCP config.
No reaching out into arbitrary filesystem locations.
No assuming ambient machine state beyond what the setup step placed in home.

### 6. One Active Run Per Flow

Rally should not support concurrent active execution of the same flow.

One flow slug gets at most one active prepared home at a time.
If that flow is already active, Rally should refuse to start another run for it until the first run ends or is explicitly cleared.

This is a simplification we want, not a missing feature.
It keeps ownership, home preparation, resume logic, and crash recovery much simpler and much more honest.

### 7. Flow-First, Not Company-First

Rally is about flows and runs, not org charts, companies, dashboards, or board-management abstractions.

### 8. Programmer-Native Operation

The system should feel natural to someone working in a shell, in git, and on the filesystem.
It should feel like a developer tool, not a SaaS product wearing terminal clothes.

### 9. General-Purpose Framework, Not Domain Cargo

Use `paperclip_agents` as pressure and examples, but do not let lessons, poker, PRD-factory, `psmobile`, or current role names become framework primitives.

### 10. Doctrine Will Move With Rally

Rally will ship a mandatory Doctrine-native standard library, and we should expect to make supporting changes in Doctrine to support it cleanly.

We should not work around missing Doctrine support by pushing core Rally semantics into ad hoc runtime hacks.
If Rally needs Doctrine-native capabilities to stay clean, we should make room to add them in Doctrine.

## Working Thesis

Rally should be a filesystem-native orchestration framework for coding agents.

The key idea is simple:

- Doctrine owns authored agent and flow doctrine through `.prompt` files.
- The filesystem owns the real runtime source of truth.
- Codex CLI and similar adapters are the actual execution engines.
- Rally is the thin runtime that runs from repo root, executes a start-of-flow home-setup script, materializes the declared agent artifacts into that home, injects only the allowed home-local skills and MCP definitions, resumes sessions honestly, appends handoffs, and moves work from one agent to the next.

That is a very different center of gravity from Paperclip.

Paperclip is a company-scoped control plane with a UI, a database, projects, goals, budgets, approvals, plugins, and many product-facing abstractions. Rally should instead assume that the user is a programmer at a shell who wants inspectable files, editable state, and a direct relationship with the actual runtime.

## Problem Statement

The current reference stack solves real problems, but it does so with more control-plane surface area than we want.

Paperclip proves that the following problems are real:

- driving many coding agents at once needs honest ownership and handoff semantics
- resumable sessions matter
- skills need runtime injection and capability scoping
- work needs a durable current artifact and a durable handoff
- execution needs strong home binding and recovery after interruption

But Paperclip also brings many things we likely do not want in the center of the system:

- a database as the primary durable control plane
- a GUI as the main operator surface
- company, org-chart, and board-style abstractions
- plugins, dashboards, auth, mobile/product surface, and general product complexity

Doctrine proves that the authored side can be much cleaner:

- prompt source can be structured and reusable
- currentness, route-only turns, review, and trust can be compiler-owned
- compiled runtime Markdown can stay visible and inspectable
- flow structure can be emitted as a graph

`paperclip_agents` proves that a practical on-disk doctrine layout works well, but it still assumes Paperclip as the runtime control plane.

Rally exists to close that gap:

- keep Doctrine-native authoring
- keep Codex-native execution
- move runtime truth onto the filesystem
- reduce the control plane to the minimum necessary runtime

## What Rally Is

Rally is provisionally:

- a flow runner, not a company operating system
- CLI-first, not GUI-first
- filesystem-first, not database-first
- Doctrine-native, not handwritten-Markdown-first
- adapter-based, with Codex CLI as the primary initial runtime
- repo-root-native, with fixed `flows/`, `skills/`, `mcps/`, and `runs/` directories
- general-purpose, not specialized to any one product domain

## What Rally Is Not

Rally is not:

- a clone of the Paperclip app
- a company/org-chart model
- a marketplace or plugin-host product
- a dashboard-first task manager
- a magic no-files automation system
- a workspace-mode repo manager
- a domain framework for lessons, poker, mobile, PRDs, or core-dev specifically

## What We Want To Keep From Paperclip

These are the Paperclip ideas that appear genuinely valuable independent of the UI product:

### 1. Resumable session discipline

Paperclip treats session persistence as a first-class runtime concern. That is correct.

Rally should preserve:

- one persistent adapter session per agent per run when compatible
- adapter-specific session IDs
- resume-vs-fresh compatibility checks
- task-scoped session state
- home-aware resume rules
- distinct initial-wake versus resume prompting
- graceful recovery when a saved session is no longer resumable

### 2. Single-owner execution

Paperclip's issue + wake + assignment model enforces one current owner at a time. Rally should keep that spirit even if it changes the storage model.

### 3. Explicit skill injection

Paperclip distinguishes authored skills from the runtime-injected set available to an agent. That separation is important.

Rally should keep:

- explicit per-agent allowlists
- runtime materialization into the actual agent home
- the same explicit allowlist idea for MCP servers

### 4. Home binding

Paperclip's session logic is careful about cwd compatibility. Rally should keep that level of rigor, but bind it to the prepared run home only. Resumable CLI sessions are only safe when their saved scope still matches the prepared home they are supposed to run inside.

### 5. Durable run lifecycle

Paperclip models wake, run, failure, timeout, recovery, and retry as real runtime states. Rally should do the same, but on disk.

## What We Want To Keep From Doctrine

Doctrine already gives Rally a large fraction of the authored semantics we need.

### 1. Source-owned prompt authoring

Use `.prompt` files as the authoring source of truth.

### 2. Deterministic compiled Markdown

Keep compiled `AGENTS.md` visible on disk as the formal generated runtime contract.
Allow additional compiled Doctrine-backed Markdown artifacts as generated compatibility artifacts and human readback when the flow wants them.
`SOUL.md` can be one such convention, but it should not be a Rally primitive.
Do not allow handwritten Markdown to become a second authored instruction surface.

### 3. Workflow law and currentness

Keep compiler-owned semantics for:

- current artifact
- current none
- route-only turns
- invalidation
- scope and preservation
- trust surfaces

### 4. Review semantics

Keep `review` and `review_family` as the typed home for critic/reviewer behavior instead of turning review into prose conventions.

### 5. Flow graph visibility

Keep `emit_flow` style graph emission so flows remain inspectable as real structures, not just long text.

## What We Want To Keep From paperclip_agents

`paperclip_agents` is not Rally's domain model, but it contains several structural lessons worth preserving.

### 1. Authored source vs generated runtime readback

The split between authored doctrine and generated runtime homes is healthy.

### 2. Per-agent skill allowlists

The `agent_configs.json` idea is basically right, even if Rally should likely rename or reshape it.

### 3. AGENTS plus additional Doctrine output

It is useful to let an agent have one formal `AGENTS.md` contract plus any number of additional Doctrine-backed generated artifacts.
`SOUL.md` is a reasonable convention for one of those, but Rally should not hardcode that name, meaning, or location.

### 4. One current artifact, one handoff, one next owner

That contract shape is highly reusable and should carry forward.

## What Rally Should Explicitly Cut

These are the Paperclip features or assumptions that Rally should intentionally not center in v1.

- GUI-first operation
- company/org-chart abstractions
- goals/projects as mandatory first-class product objects
- DB-first control plane
- auth/account/member management
- budgets and cost governance in the core v1
- approval workflows in the core v1
- plugin UI hosting and host-side widget ecosystems
- dashboard/mobile/product surfaces
- company skill library import as a separate product layer
- marketplace/template product framing
- shared Markdown overlays or any other non-`.prompt` instruction sidecars
- implicit runtime instruction inheritance from random repo files
- configurable workspace or repo-root indirection in the core runtime
- configurable global skills roots or MCP roots
- repo URL or repo ref as a required part of `run.yaml`

This does not mean Rally can never have some of these ideas later.

It means they should not become mandatory architecture early, because they push the design back toward Paperclip.

## What Rally Must Figure Out For Itself

Paperclip solved several real runtime problems that Rally will still need to solve, even if the storage model changes.

### 1. How to represent runs durably on disk

We need a real run model, not just emitted doctrine.

### 2. How to represent resumable adapter sessions on disk

We need session persistence that survives process restarts but remains honest about home compatibility.

### 3. How to enforce one active run per flow without a DB

The filesystem model still needs a crash-safe activation and lock story, but it is much simpler if we refuse concurrent active runs for the same flow.

### 4. How to inject only the allowed skills and MCPs into the real runtime

This needs to be deterministic and inspectable.

### 5. How to recover after abort, crash, or operator interruption

We need restart semantics that do not corrupt the run ledger.

### 6. How to separate semantic truth from volatile runtime plumbing

A pure single-file dream is attractive, but process IDs, locks, and adapter session metadata are runtime plumbing. Rally needs a clean rule for what is semantic truth and what is disposable machine state.

## Proposed Core Concepts

Rally should start with a small vocabulary.

### Flow Definition

A reusable authored flow with:

- a set of agents
- a start agent
- Doctrine `.prompt` source only
- a start-of-flow home setup script
- skill policy
- MCP policy

Everything that contributes instruction prose to agents must come from the declared `.prompt` tree for the flow.
The flow decides when it ends by following Rally's standard Doctrine-native conventions, not by filling out extra terminal metadata in Rally config.

### Canonical Agent Order

Agent directories should have a canonical numeric order inside the flow.

- Rally only needs to enforce that each agent directory name starts with a number
- by convention, the first agent is `01`
- by convention, later agents increase from there
- the examples in this doc use zero-padded two-digit prefixes like `01_core_dev_lead` and `02_bugfix_engineer`
- the rest of the directory name can be whatever human-meaningful slug the flow wants

This numbering is for canonical authored order and debugging, not for limiting runtime recursion.
An agent can recur as many times as needed during execution.
The number tells you where that agent sits in the canonical flow definition, which makes logs, issue history, and session archaeology much easier to read later.

### Flow Run

A concrete execution instance of a flow.

It owns:

- the operator-supplied brief or starting artifact
- the append-only handoff ledger
- the current owner
- the canonical prepared home directory for the run
- runtime session state
- produced artifacts
- run status

### Agent Home

The concrete runtime home that an executing agent sees.

This is the materialized combination of:

- compiled `AGENTS.md`
- any additional compiled Doctrine-backed generated artifacts copied from that agent's build output
- the injected allowed skill set inside home
- the enabled MCP definitions inside home
- the prepared repos, worktrees, env files, and artifacts inside home
- the bound environment for the current run

The important rule is negative:

- no extra Markdown doctrine
- no shared overlay files
- no repo-level sidecar instruction docs
- no undeclared prose entering through runtime plumbing
- no escaping home
- no machine-global skills outside home
- no machine-global MCP config outside home

Rally should only formalize `AGENTS.md` by name.
Any additional generated artifacts are flow-owned Doctrine output that Rally can copy generically as long as they come from the declared build output and are explicitly referenced by `AGENTS.md`.

### Artifact

A durable file that can become the current artifact for a lane or run.

### Ledger

The append-only run truth surface that records handoffs, current artifact changes, and ownership transitions in a human-readable form.

### Session Record

The adapter-specific sidecar that lets Rally honestly wake, resume, or retire a saved CLI session.

## Proposed On-Disk Model

The most important design choice is to separate:

- authored flow definitions
- compiled runtime readback
- concrete run instances

A strong starting point is:

```text
<rally-repo-root>/
  flows/
    <flow-slug>/
      flow.yaml
      setup/
        prepare_home.sh
      prompts/
        shared/
          ...
        agents/
          <nn-agent-slug>/
            AGENTS.prompt
            ...
      build/
        agents/
          <nn-agent-slug>/
            AGENTS.md
            ...
  skills/
    <skill-slug>/
      SKILL.md
      ...
  mcps/
    <mcp-slug>/
      server.toml

  runs/
    active/
      <flow-slug>.lock
    archive/
      <run-id>/
        ...
    <run-id>/
      run.yaml
      state.yaml
      logs/
        events.jsonl
        rendered.log
        agents/
          01_core_dev_lead.jsonl
          02_bugfix_engineer.jsonl
      issue_history/
        0001-2026-04-12T14-41-10Z-01_core_dev_lead-to-02_bugfix_engineer.md
        0002-2026-04-12T15-03-22Z-02_bugfix_engineer-to-01_core_dev_lead.md
      home/
        issue.md
        agents/
          <nn-agent-slug>/
            AGENTS.md
            ...
        skills/
          <skill-slug>/
            SKILL.md
            ...
        mcps/
          <mcp-slug>/
            server.toml
        repos/
          <repo-slug>/
            ...
        artifacts/
          ...
        sessions/
          <nn-agent-slug>.json
        runtime/
          lock.json
          pids.json
          logs/
```

### Why this shape

- `flows/<flow-slug>` is durable authored source plus compiled readback.
- `skills/` and `mcps/` are stable repo-root capability libraries, not configurable global roots.
- `runs/<run-id>` is concrete execution state.
- `runs/<run-id>/home/` is the only world agents live in.
- `runs/archive/` is where closed-out runs can move once the operator archives an issue.
- `runs/active/<flow-slug>.lock` is the simple v1 enforcement point for one active run per flow.
- `home/issue.md` starts with the operator's brief exactly as entered and then grows append-only from there.
- `issue_history/` stores full-copy backups of `home/issue.md` at handoff points so the run can be read archaeologically over time.
- numbered agent directory names make canonical flow position visible in logs, snapshots, and session records.
- `logs/` is the per-run excavatable trace mirror, separate from whatever canonical Codex session directories exist elsewhere.
- `state.yaml` is the small machine-readable summary of current status.
- `home/sessions/*.json` is adapter/runtime state, not authored truth.
- `home/agents/<agent>` is the per-run copy of that agent's compiled build output.
- `home/skills/` is the only runtime skill surface agents see.
- `home/mcps/` is the only runtime MCP surface agents see.
- `home/repos/` is where the setup script can clone, create worktrees, or otherwise prepare code for agents.
- the only authored instruction source is the `.prompt` tree under `flows/<flow-slug>/prompts/`
- Doctrine decides what compiled files appear under `flows/<flow-slug>/build/agents/<agent>/`
- Rally copies that compiled agent build output into `runs/<run-id>/home/agents/<agent>/` at execution time

## Hard Rule: Instruction Content Comes From `.prompt` Only

Rally should make this mechanically true, not culturally aspirational.

The runtime should reject or ignore any attempt to add instruction prose from:

- Markdown overlays
- random shared docs
- root `AGENTS.md` files outside the compiled flow output
- ad hoc mounted context docs
- runtime-added prompt text that is not declared by the flow's `.prompt` graph

If a team wants shared cross-cutting doctrine, it should live in shared `.prompt` files and be imported through Doctrine like everything else.
If a flow wants extra generated docs beyond `AGENTS.md`, those should also come from the declared `.prompt` graph and be explicitly referenced by `AGENTS.md`.

## Hard Rule: Agents Do Not Leave Home

Rally should treat home confinement as a real runtime guarantee, not a suggestion.

That means:

- all agent-facing paths are relative to home
- the setup script prepares whatever repos, worktrees, env files, and support assets the flow needs inside home
- agents assume that setup already happened
- agents do not read or write outside home
- skills available to agents are materialized from repo-root `skills/` into home and are not global
- MCP definitions available to agents are materialized from repo-root `mcps/` into home and are not global

If a flow needs three repos, two worktrees, and env wiring, the setup script does that up front.
The agents then operate inside the prepared home rather than inventing their own repo-management behavior mid-run.

## Provisional Rule: Single Semantic Ledger, Minimal Runtime Sidecars

The user intent is clear: the filesystem should own the truth, and a run should feel like a real editable object on disk.

The best current interpretation is:

- `home/issue.md` should be the semantic source of truth for the run's history and handoffs.
- it should start with the operator's human-authored brief exactly as entered, with nothing prepended above it
- Rally, the setup script, and later agents may only append after that starting brief
- after each handoff append, Rally should write a full-copy backup of the current `home/issue.md` into `runs/<run-id>/issue_history/`
- `state.yaml` should contain only the compact current summary needed for orchestration.
- `home/sessions/*.json`, `home/runtime/lock.json`, and similar files are runtime plumbing and should be treated as rebuildable sidecars, not semantic truth.

This gives us the human simplicity of a single readable ledger without forcing session IDs, process locks, or adapter internals into Markdown, while still preserving archaeological checkpoints of how the issue evolved.

## Mandatory Rally Standard Library

Rally should ship a mandatory standard library written in Doctrine.

Every Rally flow and every Rally agent should inherit from that standard library.
This is how Rally gets consistent runtime behavior without inventing a second non-Doctrine policy layer.

The important thing to specify now is that the standard library is:

- mandatory
- Doctrine-native
- inherited by all Rally agents
- the home for shared Rally runtime conventions

We should not try to fully author that standard library in this doc.

What it should minimally define is the common Doctrine contract for:

- normal wake and resume behavior
- blocker or error termination
- normal completion
- sleep and later wake-up

Those end outcomes should be treated as standard Rally conventions:

- blocker or error
  - something is wrong and the flow is ending with a human-readable explanation of why
- done
  - the flow is complete and ends with a human-readable summary of what work was completed
- sleep
  - the flow is not done, but it wants Rally to wake it again after a requested duration such as two minutes, five minutes, or ten minutes

This should stay flow-driven.
Rally does not need extra config fields for end agents or terminal conditions.
The flow ends when it ends, and it does so through the mandatory Doctrine-native standard library conventions.

## Proposed `flow.yaml`

`flow.yaml` should be the small runtime contract that Doctrine does not currently own.

It likely needs:

```yaml
name: core-dev
start_agent: 01_core_dev_lead
setup_home_script: setup/prepare_home.sh
agents:
  01_core_dev_lead:
    allowed_skills:
      - github-access
      - publish-followthrough
    allowed_mcps:
      - db
  02_bugfix_engineer:
    allowed_skills:
      - mobile-sim
      - github-access
    allowed_mcps:
      - db
runtime:
  adapter: codex
  adapter_args:
    model: gpt-5.4
    reasoning_effort: high
```

The key point is that this file should declare runtime availability, not authored semantic preference or extra instruction prose.

Doctrine can still say which skills are required or advisory in the prompt sense.
Rally should decide which skills are materially available in the runtime.

That means the real rule is:

- Doctrine declares semantic capability references.
- Rally declares runtime capability availability and the one setup script that prepares home.
- The adapter sees the intersection.

The agent keys in `flow.yaml` should match the numbered agent directory names.
That keeps the canonical authored order visible everywhere Rally surfaces agent identity.

There is no separate workspace root, repo ref, or skills-root config here.
The flow runs in a prepared home, and Rally itself assumes repo-root `skills/` and `mcps/` as the authored capability libraries.

The setup script contract should also include the path to `home/issue.md`.
That lets the script append flow-specific runtime notes, such as prepared branches, checked out repos, or local environment facts that the downstream agents should know.

Provisional v1 shape:

- Rally invokes the script with stable environment variables
- one of those variables is the absolute path to `home/issue.md`
- the script may append to that file, but should not rewrite or prepend above the original operator brief

## Proposed `run.yaml`

`run.yaml` should establish the stable identity of the run.

Likely fields:

```yaml
id: 2026-04-12T14-30-00Z-core-dev-fix-abc
flow: core-dev
status: active
started_at: 2026-04-12T14:30:00Z
current_owner: 02_bugfix_engineer
current_artifact: artifacts/fix-plan.md
home:
  path: runs/2026-04-12T14-30-00Z-core-dev-fix-abc/home
adapter:
  type: codex
```

This is the compact machine summary of the run identity, not the append-only narrative.

## Proposed `issue.md`

`home/issue.md` should be the primary human-readable run record.

It should begin with the operator's brief exactly as typed.
Rally should not prepend a generated header, YAML frontmatter, or machine metadata above that brief.

After the initial brief exists, the file grows append-only.
Rally may append structured sections after the brief.
The setup script may append flow-specific runtime notes after the brief.
Agents may append handoffs after that.
After each handoff append, Rally should snapshot the full file into `runs/<run-id>/issue_history/`.

Possible shape:

```md
Fix the flaky subscription upgrade flow on iOS.
Repro is intermittent.
We need a real fix, not a band-aid.

## Setup Notes

- Prepared repo at `home/repos/psmobile`
- Current branch: `fix/subscription-upgrade`
- iOS env vars loaded from `home/env/ios.env`

## Handoffs

### 2026-04-12T14:41:10Z - 01_core_dev_lead -> 02_bugfix_engineer

Current Artifact: artifacts/fix-plan.md
What Changed:
...
What To Use Now:
...
Next Owner: 02_bugfix_engineer
```

This file should stay readable and editable by humans.
Its top should always remain the operator-authored brief, not Rally-generated metadata.
The history copies are for archaeology; `home/issue.md` remains the live truth surface.

## Run Lifecycle

The happy path should look like this:

1. Operator starts a run from a flow and an initial brief.
2. Rally refuses to start if `runs/active/<flow-slug>.lock` already exists.
3. Rally creates `runs/<run-id>/`, records the active-flow lock, and writes `home/issue.md` with the operator's brief as the initial contents.
4. Rally runs the flow's home-setup script once.
5. The setup script receives the path to `home/issue.md`, prepares `runs/<run-id>/home/` exactly how the flow expects, including repos, worktrees, env files, and any other non-instruction runtime assets, and may append setup notes to the end of `home/issue.md`.
6. Rally copies each agent's compiled build output into that run's home, then materializes the allowed skills and MCP definitions inside that home.
7. Rally starts per-run event capture and invokes the start agent through the chosen adapter, using an initial wake for a fresh session or a resume envelope for a compatible existing one.
8. The agent writes artifacts and appends a handoff entry to `home/issue.md`.
9. Rally writes a timestamped full-copy backup of `home/issue.md` into `runs/<run-id>/issue_history/`.
10. Rally updates `state.yaml`, current owner, current artifact, and session sidecars.
11. The next agent runs in the same prepared home, again using that agent's own compatible resumed session when possible and an initial wake otherwise.
12. The flow eventually emits one of the standard library end outcomes such as blocker, done, or sleep, and Rally responds accordingly.

At a high level:

- blocker or done
  - stop the run, preserve the files, and clear active-flow state
- sleep
  - preserve the run, record the requested wake time, and leave it resumable

Abort and resume should be first-class:

- abort marks the run stopped but preserves all files
- resume reloads `run.yaml`, `state.yaml`, `home/issue.md`, and any compatible `home/sessions/*.json`

## Proposed Run Logs And Trace Capture

Runner logging is a core product surface, not an afterthought.

Codex will still emit its normal canonical session directories wherever Codex emits them.
Rally should not fight that.
But Rally should also capture a per-run mirror of everything observable so the operator can excavate and debug one run from one directory.

Proposed run-local log surfaces:

- `runs/<run-id>/logs/events.jsonl`
  - the structured merged event stream for the whole run
- `runs/<run-id>/logs/agents/<agent-id>.jsonl`
  - the per-agent filtered event stream
- `runs/<run-id>/logs/rendered.log`
  - a flattened human-readable transcript suitable for grep and quick inspection

`events.jsonl` should capture, at minimum:

- Rally lifecycle events
- setup-script start, finish, and output
- adapter wake and resume events
- reasoning trace events
- tool-call start, arguments, streamed output chunks, completion, and failure
- any other adapter-visible event payload the operator could have watched live
- handoff events
- archive events
- warnings and hard errors

The important rule is completeness:
if the operator could have seen it happen in the runner, Rally should mirror it into the run-local trace log.

The important second rule is replayability:
the terminal renderer should read from this structured event history, not just tail stdout.
That is what makes it possible to toggle tool calls and reasoning traces on and off across the full history instead of only for future output.

## Proposed CLI Shape

The CLI should stay very small.

Proposed primary commands:

```bash
rally run <flow> <issue-file>
rally resume <run-id>
rally archive <run-id>
```

### `rally run`

Starts a new run for a flow from an issue file or brief file.
It seeds `home/issue.md` from that file, prepares home, starts the runner, and opens the live terminal renderer.

This command should be conservative.
If the target flow is in a clearly dirty or ambiguous state, it should refuse to run and print the exact blocker.

Examples of clearly dirty state:

- `runs/active/<flow-slug>.lock` already exists
- a partially initialized run directory exists for that flow
- `run.yaml`, `state.yaml`, and filesystem reality disagree in an obvious way
- a previous run for that flow still needs explicit archival before the next issue starts

The CLI should not try to auto-heal these cases silently.
Refuse loudly and make the operator choose the next move.

### `rally resume`

Reopens an existing run, reloads its history, resumes any compatible agent sessions, and opens the same live renderer on top of the full stored event history.

### `rally archive`

Closes out a stopped or completed run, moves it under `runs/archive/`, clears any stale active-flow state that should not survive archival, and leaves the repo ready for the next issue.

The point of `archive` is to make "this issue is done, set me up cleanly for the next one" a first-class operator action.

## Proposed Terminal Renderer

The live CLI surface should not be a dumb log tail.
It should be a smart renderer backed by the full run event history.

### Renderer behavior

- `rally run` and `rally resume` should both open the same renderer
- on startup, the renderer replays the existing run history from `logs/events.jsonl`
- after replay, it follows live events as they arrive
- because it has the full history model, visibility toggles apply to both past and future events

### Renderer controls

- `T`
  - toggle tool-call visibility
- `R`
  - toggle reasoning-trace visibility
- `Q`
  - quit the renderer without stopping the run

### Renderer layout

- top status bar
  - run id, flow, current agent, run state, elapsed time
  - current filters such as `tools:on/off` and `reasoning:on/off`
- main event pane
  - chronological event stream with agent badges and timestamps
- bottom hint bar
  - compact key hints such as `T tools`, `R reasoning`, `Q quit`

### Renderer color rules

- timestamps
  - dim gray
- flow and lifecycle events
  - cyan
- current agent badges
  - blue
- reasoning traces
  - dim white
- tool calls
  - yellow
- successful tool completion
  - green
- warnings
  - amber
- failures and hard errors
  - red

### Renderer event style

Each line should be compact and scannable.
A good mental model is:

```text
14:41:10  01_core_dev_lead  WAKE      initial wake
14:41:14  01_core_dev_lead  REASON    tracing root cause in subscription flow
14:41:18  01_core_dev_lead  TOOL      rg -n "subscription" apps/mobile
14:41:19  01_core_dev_lead  TOOL OK   12 matches
14:44:02  01_core_dev_lead  HANDOFF   -> 02_bugfix_engineer  artifact=artifacts/fix-plan.md
```

The renderer should feel elegant and watchable in real time, but the structured logs remain the deeper debug surface.

## Proposed Skill Model

Rally should not have a separate company-skill database or import layer in v1.

Instead:

- each flow declares which skills each agent may use
- Rally sources those skills from repo-root `skills/`
- Rally materializes only those skills into that run's home-local skill directory
- the actual adapter sees only those injected home-local skills
- agents never rely on machine-global skills outside home

This preserves Paperclip's good runtime scoping behavior without needing Paperclip's control plane.

## Proposed MCP Model

Rally should treat MCP definitions the same way it treats skills: repo-owned, explicitly allowlisted, and materialized into home.

- repo-root `mcps/<mcp-slug>/server.toml` stores one MCP definition in a Codex-shaped TOML format
- that file should look like the body of a single `mcp_servers.<name>` entry, not a new invented config DSL
- each flow declares which MCPs each agent may use
- Rally sources those definitions from repo-root `mcps/`
- Rally materializes only the allowed MCPs into `home/mcps/`
- the Codex adapter assembles those materialized definitions into the adapter config it launches with
- skills that depend on MCPs do not auto-enable them; the flow must explicitly allow both the skill and the MCP

Possible `server.toml` shape:

```toml
command = "/opt/homebrew/bin/npx"
args = ["-y", "mcp-remote@latest", "http://127.0.0.1:5100/mcp"]
startup_timeout_sec = 120.0

[env]
PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
```

For remote servers, the same file could instead be:

```toml
url = "https://mcp.figma.com/mcp"
```

## Proposed Session Model

Sessions should be stored per run and per agent.
The intended model is one persistent Codex session per agent per run whenever resume compatibility holds.

Example:

```json
{
  "agent": "01_core_dev_lead",
  "adapter": "codex",
  "session_id": "codex-session-1",
  "cwd": ".",
  "wake_count": 2,
  "last_woken_by": "02_bugfix_engineer",
  "last_seen_issue_snapshot": "0002-2026-04-12T15-03-22Z-02_bugfix_engineer-to-01_core_dev_lead.md",
  "updated_at": "2026-04-12T14:55:10Z"
}
```

The saved `cwd` is always home-relative.
There is no separate workspace or repo-ref identity to reconcile during resume.

Resume should be allowed only when:

- adapter type matches
- saved cwd is still valid inside home
- the same prepared home is still in effect
- flow/run scope still matches
- the session has not been explicitly invalidated

Otherwise Rally should start a fresh session and record why.

## Proposed Wake And Resume Protocol

Rally should treat initial wake and later resume as two different runtime envelopes.

### Initial wake

If an agent has no compatible saved session for this run, Rally should start a fresh adapter session for that agent and send a standardized initial-wake message.

That message should say, in effect:

- you are being woken for the first time on this run
- this is your prepared home
- `home/issue.md` is the live truth surface
- follow `AGENTS.md`, any Doctrine-backed generated artifacts it explicitly references, and the latest issue state

### Resume

If an agent already has a compatible saved session for this run, Rally should resume that same adapter session and send a standardized resume message.

That message should say, in effect:

- you have been woken up again
- you were resumed by `<previous-owner-agent-id>`
- since you were last woken, these agents operated: `<agent-id list>`
- check the latest `home/issue.md`
- continue following `AGENTS.md`, any Doctrine-backed generated artifacts it explicitly references, and the latest issue state

The important point is that Rally is not inventing new authored instructions here.
This is runtime control context about the session and the latest state transition, not a side door for flow-specific prose.

The intervening agent list should come from the actual run history, not from guesswork.
In v1, Rally can derive that from handoff entries or `issue_history/` snapshots since the agent's last seen checkpoint.

## Doctrine Changes Rally Likely Needs

This section should be treated as a required design surface, not a maybe-later note.
We expect Rally to need supporting changes in Doctrine, and we want to make those changes instead of building permanent workarounds in Rally.

## Required Supporting Changes In Doctrine

Placeholder section.

This section exists so future Rally design and implementation work has an explicit home for Doctrine-side requirements.
Do not work around core Doctrine gaps just because this section is still incomplete.

What belongs here:

- Doctrine features Rally clearly needs for a clean design
- Doctrine parser, compiler, or runtime semantics that the Rally standard library depends on
- inheritance, flow, sleep, wake, blocker, and completion support that should live in Doctrine rather than in ad hoc Rally glue
- any changes needed so Rally's mandatory Doctrine-native standard library is clean, explicit, and maintainable

We are not fully specifying those changes yet.
We are explicitly reserving space for them because we expect they will be necessary.

Doctrine is close, but not all the way there.

### 1. A first-class runtime flow or run primitive

Doctrine currently gives us authored semantics, not an execution object.

Rally likely needs Doctrine support for something like:

- `flow`
- `start_agent`
- recursive flow calls or child flow creation
- abort/resume semantics
- a Rally standard library inheritance model for shared wake, blocker, done, and sleep conventions

### 2. A first-class runtime capability/tool layer

Doctrine's current guidance strongly prefers skills over ad hoc tools, which is good, but Rally may still need a runtime layer for:

- shell-command policy
- adapter/runtime toggles
- MCP enablement
- environment bindings
- non-skill execution capabilities

Maybe this becomes a Doctrine primitive, or maybe Rally keeps it in `flow.yaml`. That remains open.

### 3. A first-class ledger or run artifact concept

Doctrine already models outputs and trusted carriers, but Rally may want a more explicit notion of:

- append-only run ledger
- current run summary
- child-flow references
- abort/resume records
- wake/resume checkpoint records

### 4. Agent home and runtime environment binding

Rally likely needs a real way to express that an agent's runtime view is bound to:

- a home directory
- home-relative working directories
- an allowed skill set
- an allowed MCP set
- a particular run

That is runtime territory more than pure authored doctrine today.

### 5. Strong runtime enforcement of the no-side-door rule

Rally should probably verify that the materialized agent home only contains generated instruction artifacts derived from the declared `.prompt` graph, plus runtime plumbing and injected skills and MCP definitions.

### 6. Strong runtime enforcement of the no-escape rule

Rally should also verify that agents only operate inside the prepared home and only see home-local skills, MCP definitions, and assets.

## Biggest Open Questions

These questions should actively guide early implementation.

### 1. How pure should the single-file truth model be?

Provisional answer:
Use one semantic ledger file plus minimal rebuildable sidecars.

### 2. Should Rally have any database at all?

Provisional answer:
Not as source of truth in v1.
If we ever add one, it should be an index/cache over files.

### 3. Should `home/issue.md` be the only human-editable truth?

Provisional answer:
Mostly yes, but `run.yaml` and `state.yaml` will probably still be useful for compact machine summary.
`issue_history/` is also useful as archaeological backup, but not as the live truth surface.

### 4. Where should flow definitions live?

Provisional answer:
Under the Rally repo root in `flows/`, with sibling `skills/`, `mcps/`, and `runs/`, not hidden inside a DB or opaque runtime store.

### 5. Should compiled Doctrine live in the flow definition or only in the run?

Provisional answer:
Keep compiled readback in the flow definition and materialize a per-run home from it.

### 6. How much should the setup script own?

Provisional answer:
It should fully prepare home before the first agent runs.
Agents should not be doing ad hoc repo-management work that the flow could have prepared up front.

### 7. Should MCP definitions stay Codex-shaped?

Provisional answer:
Yes in v1.
Rally can treat Codex as the primary adapter and keep each MCP definition close to a single `mcp_servers.<name>` entry body instead of inventing a second schema too early.

### 8. How should recursion work?

Open question:
Child flows could either become nested run directories under a parent run or sibling runs with explicit parent references.

### 9. Do we need goals/projects as first-class concepts?

Provisional answer:
No, not in core v1.
Flows and runs are enough to start.

### 10. Do we need approvals, budgets, or governance in v1?

Provisional answer:
No.
They are Paperclip control-plane features, not core Rally runtime requirements.

### 11. How much of the agent artifact surface should be formalized?

Provisional answer:
Only `AGENTS.md` should be formalized as Rally's runtime contract.
Everything else, including `SOUL.md`, should be a Doctrine-backed convention or flow-specific generated artifact that works because `AGENTS.md` tells the agent to read it.
Do not let additional generated artifacts become a second hidden workflow control plane.

### 12. How do we prevent domain leakage from `paperclip_agents`?

Provisional answer:
Treat that repo as use-case evidence only.
Generalize patterns, never domain nouns.

## Recommended V1 Scope

Rally v1 should stay narrow.

- Codex-first runtime
- filesystem-first runs
- Doctrine-authored flows
- `.prompt`-only instruction source
- start-of-flow home setup script
- home-relative agent world with no escape
- per-agent skill allowlists
- per-agent MCP allowlists
- append-only `home/issue.md`
- handoff-time `issue_history/` backups in the run directory
- resumable session sidecars
- per-agent wake versus resume envelopes
- per-run structured trace capture
- smart terminal renderer with reasoning and tool-call toggles
- three-command operator CLI: `run`, `resume`, `archive`
- mandatory Doctrine-native Rally standard library
- explicit current owner and current artifact
- one active run per flow
- no GUI
- no DB as source of truth
- no budgets, approvals, or plugin platform

If this works well, it will prove the core thesis before we spend time on broader productization.

## Immediate Next Design Work

- define the exact schema for `flow.yaml`
- define the exact agent directory naming convention and validation rule
- define the exact schema for `run.yaml`
- define the exact CLI contract for `rally run`, `rally resume`, and `rally archive`
- define the dirty-state detection rules for `rally run`
- define the exact handoff format for `home/issue.md`
- define the exact naming scheme and retention rule for `issue_history/` snapshots
- decide whether `state.yaml` is necessary or whether `run.yaml` can absorb it
- define the exact contract for the start-of-flow home setup script
- define how per-agent runtime artifacts are materialized into home
- define the exact event schema for `logs/events.jsonl`
- define the exact renderer line format, colors, and keyboard controls
- define the exact schema for repo-root `mcps/<mcp-slug>/server.toml`
- define the exact session sidecar schema
- define the exact wake and resume message templates per runtime adapter
- define the mandatory surface of the Rally Doctrine standard library without fully authoring it here
- keep the `Required Supporting Changes In Doctrine` section current instead of routing around it
- define how Rally computes intervening agents since an agent's last wake
- define the exact adapter-args schema per runtime adapter
- define the exact activation lock format for one-active-run-per-flow
- decide what Doctrine extensions belong in Doctrine versus Rally
- define the runtime guard that rejects instruction side doors
- choose the first narrow end-to-end demo flow

## Current Design Opinion

The current best direction is:

- Rally should be a thin filesystem-native runtime on top of Doctrine.
- The control plane should be files first, not tables first.
- Paperclip should influence runtime rigor, not product shape.
- `paperclip_agents` should influence on-disk ergonomics, not framework domain.
- agent instruction content should come from `.prompt` files only, with no side doors.
- Rally should assume fixed repo-root `flows/`, `skills/`, `mcps/`, and `runs/`, not configurable workspace roots.
- each run should get one prepared home, and agents should live entirely inside it.
- each flow should have at most one active run at a time.
- the operator surface should stay small: one command to run, one to resume, one to archive.
- per-run logs and the terminal renderer should make excavation and live watching excellent.
- shared flow-ending and wake behavior should come from a mandatory Doctrine-native Rally standard library, not extra Rally end-condition config.
- when Rally needs Doctrine support to stay clean, we should add it to Doctrine and track it explicitly in this doc.
- Doctrine should remain the authored language, but Rally will need runtime concepts that Doctrine does not yet own.

That feels like the right center of gravity.
