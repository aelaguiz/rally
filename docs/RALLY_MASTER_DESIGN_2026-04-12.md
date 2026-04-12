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
  - What it is not to us: a complete runtime runner or the home of the Rally standard library. Doctrine gives us authored semantics, not the full filesystem-native orchestration machine we want.

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
- `stdlib/`
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
For Codex, Rally should enforce this through the adapter launch contract rather than trusting defaults:

- set `project_doc_max_bytes = 0` so Codex does not auto-discover ambient `AGENTS.md` or `AGENTS.override.md`
- inject the compiled agent doctrine explicitly instead of relying on ambient project-doc discovery
- fail closed if Rally cannot prove what instruction surface the adapter is actually seeing

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
- adapter-local state must live in home
- agents do not escape home

No machine-global skills.
No machine-global MCP config.
No reaching out into arbitrary filesystem locations.
No assuming ambient machine state beyond what the setup step placed in home.
For Codex specifically, Rally should launch with `CODEX_HOME` pointed at the flow home.

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

### 10. Elegance And Simplicity Beat Scope-Cutting

Rally should prefer the most elegant and simple correct design, not the smallest design that can be defended in the moment.

We should not keep cutting core ideas down just because they are bigger than a narrow v1 instinct.
If a design element is central to the shape, clarity, or long-term elegance of Rally, we should preserve it and implement it cleanly instead of reflexively minimizing it away.

### 11. Doctrine Will Move With Rally

Rally will ship a mandatory Doctrine-native standard library, and we should expect to make supporting changes in Doctrine to support it cleanly.

We should not work around missing Doctrine support by pushing core Rally semantics into ad hoc runtime hacks.
If Rally needs Doctrine-native capabilities to stay clean, we should make room to add them in Doctrine.

Doctrine is still the compiler, not the Rally standard library and not the Rally runner.
Generic enabling features can move into Doctrine.
The Rally standard library itself lives in Rally.
The boundary is explicit:

- Doctrine owns generic language and compiler support
- Rally owns the standard library contents, runtime, adapter contract, CLI, logs, sessions, and run structure
- `paperclip_agents` remains use-case pressure, not framework law

### 12. No Hidden Global Rally State

Rally-owned state lives in the repo root where Rally is run.

Rally must not create its own control-plane state in hidden dot directories such as `~/.rally`, `~/.config`, or similar side locations.
An adapter that cannot keep its Rally-owned state in the flow home is not an acceptable Rally adapter.
For Codex, that means setting `CODEX_HOME` to the flow home directory.

### 13. No GUI, Board, Company, Or Registry Carryover

Rally is not a GUI product shell, a board manager, a company control plane, or a registry product.

We are keeping runtime rigor from Paperclip.
We are not carrying over the surrounding product shape.

## Working Thesis

Rally should be a filesystem-native orchestration framework for coding agents.

The key idea is simple:

- Doctrine owns authored agent and flow doctrine through `.prompt` files.
- The filesystem owns the real runtime source of truth.
- Codex CLI and similar adapters are the actual execution engines.
- Rally is the thin runtime that runs from repo root, executes a start-of-flow home-setup script, materializes the declared agent artifacts into that home, launches adapters with an explicit contract such as `cwd`, `CODEX_HOME`, disabled ambient project-doc loading, and explicit instruction injection, injects only the allowed home-local skills and MCP definitions, resumes sessions honestly, appends handoffs, and moves work from one agent to the next.

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
- repo-root-native, with fixed `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/` directories
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

## Authoritative Ownership Boundary

This section is the single source of truth for what belongs in Doctrine, what belongs in Rally, and what belongs in neither.
If another section seems to disagree, this section wins.

### Doctrine owns

Doctrine is the authoring language and compiler.
It owns generic authored semantics and generic compiler support.

- `.prompt` authoring
- imports, composition, inheritance, package/import-root behavior, and similar reusable authoring mechanics
- typed workflow semantics such as currentness, invalidation, review, route-only behavior, trust surfaces, and other generic artifact-truth law
- compilation into `AGENTS.md` and any other generated doctrine artifacts
- machine-readable emitted structures Rally may need, such as flow graphs or other generic compiler outputs
- generic final-turn contract designation and related emitted metadata when Rally needs a clean authored way to name the turn-ending response contract
- any generic enabling feature Rally needs in order to keep the design clean

Doctrine does not own Rally's standard library contents.
Doctrine enables those contents by compiling them.

### Rally owns

Rally is the runner, the runtime contract, and the operator surface.
It owns materialization, execution, observation, and recovery.

- `stdlib/rally/` and the mandatory Rally standard library contents
- repo-root layout such as `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/`
- `flow.yaml` and the runtime contract it expresses
- run creation, active-run locking, and archive behavior
- the setup script contract and prepared flow home
- `run.yaml`, `state.yaml`, `home/issue.md`, `issue_history/`, logs, sessions, and other runtime sidecars
- adapter launch details such as `cwd`, `CODEX_HOME`, config overrides, explicit instruction injection, timeout handling, and resume behavior
- skill and MCP materialization plus runtime realization checks
- CLI commands, terminal renderer behavior, archaeology surfaces, and operator-facing failure handling

Rally is allowed to express some of its shared behavior in Doctrine because the Rally standard library is Doctrine-native.
That does not move runtime ownership into Doctrine.

### `paperclip_agents` owns nothing in the framework

`paperclip_agents` is use-case pressure, not platform law.
It gives us examples, tests, and sharp requirements.
It does not get to define universal Rally primitives or universal Doctrine primitives.

### What must not happen

- Doctrine must not become the Rally runner
- Doctrine must not own repo-root runtime structure, sessions, logs, adapter launch, or CLI behavior
- Rally must not become a second compiler or a second authored instruction language
- Rally must not solve missing generic compiler support with permanent ad hoc semantic hacks if the right answer is a Doctrine feature
- proprietary `paperclip_agents` roles, domain concepts, or workflow quirks must not become framework requirements

### Decision rule

Use this test whenever ownership is unclear:

- if it changes the meaning of authored doctrine generically, it belongs in Doctrine
- if it decides when work actually runs, sleeps, wakes, resumes, retries, or is scheduled, it belongs in Rally
- if it changes how a run is materialized, launched, resumed, logged, rendered, or archived, it belongs in Rally
- if it is a shared Rally behavior expressed in Doctrine, it belongs in `stdlib/rally/`, compiled by Doctrine, and executed by Rally
- if it only exists because of a particular sample domain or a proprietary agent family, it belongs in that flow or example, not in the framework

### Version and compatibility rule

Rally should declare the Doctrine support it requires.
If that support is missing, Rally should fail loudly instead of silently degrading into a different semantic model.

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

For Rally specifically, agent timeout should be explicit, operator-visible, and terminal:

- each agent gets its own required timeout setting
- timeout is not sleep
- timeout is not a silent retry trigger
- if an agent times out, the run ends in blocker or error state with a human-readable timeout explanation

## What We Want To Keep From Doctrine

Doctrine already gives Rally a large fraction of the authored semantics we need.
Per the ownership boundary above, we should keep Doctrine focused on generic language and compiler support rather than letting it absorb Rally runtime ownership.

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

This needs to be deterministic and inspectable, and it needs to be separated from the stronger claim of full built-in tool isolation.

### 5. How to enforce adapter-side instruction isolation honestly

The no-side-door promise depends on a real adapter launch contract, not just on Rally's intent.
For Codex, that means redirecting `CODEX_HOME` into the flow home, disabling ambient project-doc discovery, and explicitly injecting compiled doctrine.

### 6. How to recover after abort, crash, or operator interruption

We need operator-driven restart semantics that do not corrupt the run ledger and do not require a background recovery control plane.

### 7. How to separate semantic truth from volatile runtime plumbing

A pure single-file dream is attractive, but process IDs, locks, and adapter session metadata are runtime plumbing. Rally needs a clean rule for what is semantic truth and what is disposable machine state.

## Built-In Turn Memory And Self-Improvement

Rally should treat memory and self-improvement as a core runtime feature, not as a special optional ability that only some agents know how to use.

The required shape is intentionally simple for now:

- Rally should support a turn-start memory check so an agent can see relevant prior learnings before continuing work
- Rally should support a turn-end learning write so reusable lessons from that turn can be kept for later turns

This is a requirement statement, not an architecture freeze.
Do not treat this note as a decision about storage model, schema, retrieval policy, ranking, or agent-facing API shape yet.
It also is not the first implementation priority; the point of documenting it now is to make sure Rally leaves room for it as a built-in system behavior.

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
  stdlib/
    rally/
      prompts/
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
- `stdlib/rally/` is the Rally-owned Doctrine standard library. It lives in this repo, not in the Doctrine compiler repo.
- `skills/` and `mcps/` are stable repo-root capability libraries, not configurable global roots.
- `runs/<run-id>` is concrete execution state.
- `runs/<run-id>/home/` is the only world agents live in.
- `runs/archive/` is where closed-out runs can move once the operator archives an issue.
- `runs/active/<flow-slug>.lock` is the simple v1 enforcement point for one active run per flow.
- `home/issue.md` starts with the operator's brief exactly as entered and then grows append-only from there.
- `issue_history/` stores full-copy backups of `home/issue.md` at handoff points so the run can be read archaeologically over time.
- numbered agent directory names make canonical flow position visible in logs, snapshots, and session records.
- `logs/` is the per-run excavatable trace mirror, separate from whatever canonical Codex session directories exist elsewhere.
- for Codex, those canonical adapter directories should also be localized under home by setting `CODEX_HOME` to the flow home
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
It is not something the Codex adapter gives us automatically by default.
Rally has to enforce it through its adapter launch contract.
This section defines the instruction-surface rule.
The later Codex adapter section is the Rally-owned implementation contract for that rule.

For Codex, the minimum required contract is:

- `CODEX_HOME=<flow-home>`
- `project_doc_max_bytes = 0`
- explicit injection of the compiled agent doctrine through Codex's explicit instructions channel
- explicit `cwd` chosen by Rally

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
For Codex, Rally should also treat home confinement as a launch policy plus runtime validation, not as something guaranteed by ambient defaults alone.

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

Potential future consideration:

- `home/issue.md` may eventually prove to be carrying too many concerns at once: operator brief, live handoff ledger, and archaeology trail.
- We are explicitly not splitting that surface right now.
- Keep the simple single-ledger model until real usage proves it is muddy.

## Mandatory Rally Standard Library

Rally should ship a mandatory standard library written in Doctrine.

Every Rally flow and every Rally agent should inherit from that standard library.
This is how Rally gets consistent runtime behavior without inventing a second non-Doctrine policy layer.
The ownership split here is intentional: the standard library is authored in Doctrine, but it lives in Rally under `stdlib/rally/` and is executed by the Rally runtime.

The important thing to specify now is that the standard library is:

- mandatory
- Doctrine-native
- inherited by all Rally agents
- the home for shared Rally runtime conventions
- stored in this repo under `stdlib/rally/`, not in the Doctrine compiler repo

We should not try to fully author that standard library in this doc.

What it should minimally define is the smallest shared Doctrine contract that keeps Rally flows disciplined without turning the standard library into a second framework inside the framework.

The first job of the standard library is not a universal artifact taxonomy.
It is a small portable currentness and handoff convention:

- productive turns emit explicit Doctrine `output` artifacts
- one artifact is explicitly current when a turn ends, or the turn uses `current none`
- that currentness is carried through a trusted handoff field
- downstream turns read declared `input` artifacts instead of reconstructing truth from prose alone

That means the standard library should start with light-touch conventions for:

- shared handoff output shape for turns that leave one current artifact
- shared handoff output shape for route-only or blocked turns that leave no current artifact
- a trusted `current_artifact` carrier field and the currentness law that uses it
- the minimal companion fields that make the handoff readable on its own, such as what changed, what to use now, and next owner

The standard library should not standardize every artifact body.
It should not bless one framework-level plan, report, or similar universal file shape.
Those concrete artifacts stay flow-owned outputs.
If a flow wants `repair_plan.md`, `verification.md`, `acceptance_verdict.md`, or something else, that is the flow's choice, not a Rally primitive.

Inputs should stay only lightly standardized.
The important rule is that if a downstream turn depends on a current artifact, it declares that artifact as an `input`.
If that artifact has meaningful shape, the flow may attach a Doctrine `document` or `schema`.
The standard library does not need a giant universal input model to make this work.

### Current Standard Library Shape

The authored Rally half of this design is now implemented in this repo.

What is done today:

- `stdlib/rally/prompts/rally/handoffs.prompt`
- `stdlib/rally/prompts/rally/currentness.prompt`
- `stdlib/rally/prompts/rally/turn_results.prompt`
- `stdlib/rally/schemas/rally_turn_result.schema.json`
- `stdlib/rally/examples/rally_turn_result.example.json`
- `flows/_stdlib_smoke/prompts/AGENTS.prompt` wired to `final_output:`

What that means:

- Rally now has one shared authored handoff/currentness surface
- Rally now has one tiny shared authored final-turn result contract surface
- the smoke flow proves the authored shape compiles with `final_output:` on concrete agents
- that authored shape was compile-checked against the local Doctrine branch carrying `final_output` support

What is not done yet:

- Rally runner-side consumption of the final turn result
- adapter-side schema injection and result dispatch
- ledger append / closeout / blocker / sleep runtime behavior

The current implemented standard library stays intentionally small.

Likely source layout:

```text
stdlib/
  rally/
    examples/
      rally_turn_result.example.json
    prompts/
      rally/
        handoffs.prompt
        currentness.prompt
        turn_results.prompt
    schemas/
      rally_turn_result.schema.json
```

With the assumed Doctrine cross-root import contract, `stdlib/rally/prompts/`
is the configured additional prompt root and `stdlib/rally/prompts/rally/` is
the actual importable package path. Future flows therefore import
`rally.handoffs`, `rally.currentness`, and `rally.turn_results`.

What those modules should roughly own:

- `handoffs.prompt`
  - the Rally-owned output target for appending a handoff or status block into the live issue ledger
  - one shared output shape for turns that leave one current artifact
  - one shared output shape for route-only, blocked, or review turns that leave no current artifact
  - the minimal shared fields: what changed, current artifact when one exists, what to use now, and next owner
  - the trusted carrier fields that downstream turns may rely on

- `currentness.prompt`
  - the reusable convention for `current artifact ... via ...`
  - the reusable convention for `current none`
  - any very small helper workflows or declarations needed so Rally flows do not hand-author the carrier pattern from scratch every time

- `turn_results.prompt`
  - the shared JSON-schema-backed final turn result shape for Rally-managed turns
  - the minimal tagged runtime outcome union Rally expects from the adapter
  - no durable handoff prose, no ledger target, and no scheduler keywords

The intended usage pattern is:

- a flow declares its own concrete artifact outputs
- that same flow declares its own `TurnResponse` final output using the shared `rally.turn_results` JSON shape
- that same flow reuses the Rally stdlib handoff output
- the producing turn carries one current artifact through the stdlib handoff carrier
- the downstream turn declares the artifact it depends on as an explicit input
- route-only or blocked turns use the stdlib no-current handoff plus `current none`

That means a flow-owned artifact might be something like an analysis note, implementation artifact, verification artifact, or acceptance artifact.
The Rally standard library does not decide that artifact's body or filename.
It only decides how the turn carries forward current truth about that artifact.

The intended authored shape should be roughly:

```text
flow-owned output artifact
  + stdlib handoff output
  + stdlib currentness convention
  = portable pickup truth for the next owner
```

That is enough structure for the first example flows.
It gives Rally strong output and pickup discipline without locking the whole framework into a giant predeclared artifact system.

### Handoffs Versus End-Of-Turn Results

Decision:
Rally will use two separate surfaces, not one overloaded lifecycle surface.

Handoffs are durable issue-ledger content for the next owner.
They live in the Doctrine-authored Rally standard library and should answer:

- what changed
- what artifact is current now when one exists
- what to use now
- who owns next

End-of-turn results are the turn-ending assistant response contract.
They are not issue-ledger prose and they are not part of the handoff/currentness contracts.
They tell Rally what runtime action to take after the agent turn ends.

Rally should still keep one tiny shared authored module for this contract so
flows do not drift.
That module is `rally.turn_results`.

The Doctrine-side feature Rally wants here is a generic authored final-output
designation such as `final_output:` that points at an existing `output`
contract.
That feature can stay generic and optional in Doctrine.
Doctrine can support both prose and JSON final outputs in general.

Rally's policy layer is stricter:

- for Rally-managed end-of-turn control, the agent must declare a final output
- that final output must resolve to a `TurnResponse` output
- that final output must be backed by a JSON schema
- Rally passes that schema to the adapter as the required final turn contract
- Rally interprets the returned JSON into runtime behavior

For Codex, this means Rally should use the adapter's existing strict JSON
final-output path rather than inventing Doctrine lifecycle keywords.
For Rally-on-Codex, JSON mode for this final turn return is required, not
optional.
Free-form final text is insufficient for end-of-turn control flow.

The minimum tagged outcome family should be:

- `handoff`
  - the turn produced a normal same-issue handoff result
  - the final JSON only says that Rally should take the handoff path
  - Rally appends the separate authored handoff block to `home/issue.md` and routes from that trusted handoff content
- `done`
  - the flow is complete
  - Rally appends a Rally-generated final closeout block and marks the run done
- `blocker`
  - the flow is ending in blocker or error state
  - Rally appends a Rally-generated blocker record and stops the run cleanly
- `sleep`
  - the flow is not done and wants the runner to wake it again later
  - Rally records the request, blocks inline in the simple model, and later wakes the same flow again

The important rule is that this surface should be machine-shaped, not
prose-shaped.
For example, sleep should carry a typed numeric duration such as seconds, not a
free-text phrase like "five minutes."

Initial required end-of-turn JSON shape:

```json
{
  "oneOf": [
    {
      "type": "object",
      "properties": {
        "kind": { "const": "handoff" }
      },
      "required": ["kind"],
      "additionalProperties": false
    },
    {
      "type": "object",
      "properties": {
        "kind": { "const": "done" },
        "summary": { "type": "string" }
      },
      "required": ["kind", "summary"],
      "additionalProperties": false
    },
    {
      "type": "object",
      "properties": {
        "kind": { "const": "blocker" },
        "reason": { "type": "string" }
      },
      "required": ["kind", "reason"],
      "additionalProperties": false
    },
    {
      "type": "object",
      "properties": {
        "kind": { "const": "sleep" },
        "reason": { "type": "string" },
        "sleep_duration_seconds": { "type": "integer", "minimum": 1 }
      },
      "required": ["kind", "reason", "sleep_duration_seconds"],
      "additionalProperties": false
    }
  ]
}
```

This should stay flow-driven.
Rally does not need extra config fields for end agents or terminal conditions,
but it does need one explicit adapter return contract for the end of each turn.
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
    timeout_sec: 1800
    allowed_skills:
      - github-access
      - publish-followthrough
    allowed_mcps:
      - db
  02_bugfix_engineer:
    timeout_sec: 1200
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
    project_doc_max_bytes: 0
```

The key point is that this file should declare runtime availability, not authored semantic preference or extra instruction prose.

Each agent entry should have a required timeout setting.
That timeout is part of the runtime contract, not an optional hint.
If an agent exceeds its timeout, Rally should stop the run and record a clear blocker or error outcome rather than trying to sleep, auto-retry, or continue ambiguously.

For Codex, the launch contract should also be explicit here rather than ambient:

- `cwd` comes from Rally
- `CODEX_HOME` points at the flow home
- ambient project-doc discovery is disabled
- compiled doctrine is injected explicitly rather than discovered implicitly

Doctrine can still say which skills are required or advisory in the prompt sense.
Rally should decide which skills are materially available in the runtime.

That means the real rule is:

- Doctrine declares semantic capability references.
- Rally declares runtime capability availability and the one setup script that prepares home.
- The adapter sees the intersection.

The agent keys in `flow.yaml` should match the numbered agent directory names.
That keeps the canonical authored order visible everywhere Rally surfaces agent identity.

There is no separate workspace root, repo ref, or skills-root config here.
The flow runs in a prepared home, and Rally itself assumes repo-root `stdlib/`, `skills/`, and `mcps/` as the authored capability libraries.

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
12. The flow eventually emits one structured final turn result such as `blocker`, `done`, or `sleep`, and Rally responds accordingly.

At a high level:

- blocker or done
  - stop the run, preserve the files, and clear active-flow state
- sleep
  - append the sleep request to `home/issue.md`, record it in logs/state, block the current runner for the requested duration, and then wake the flow again
  - if the process stops during that wait, preserve the run and let the operator decide whether to resume it later

Abort and resume should be first-class:

- abort marks the run stopped but preserves all files
- resume reloads `run.yaml`, `state.yaml`, `home/issue.md`, and any compatible `home/sessions/*.json`

Crash handling should stay explicit and operator-driven:

- Rally should not build a background reaper or auto-resume loop in the current design
- if a run stops unexpectedly, Rally should preserve the run and record the failure context in logs
- when the operator later resumes that run, Rally should append a crash note to `home/issue.md` with the last known running agent and any known failure context

## Proposed Run Logs And Trace Capture

Runner logging is a core product surface, not an afterthought.

Codex will still emit its normal canonical session directories under the configured `CODEX_HOME`, which Rally should point at the flow home.
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

The important second rule is history-backed rendering:
the terminal renderer should read from this structured event history, not just tail stdout.
That is what makes it possible to toggle tool calls and reasoning traces on and off across the visible history instead of only for future output.
This architecture leaves room for a dedicated replay command later if we want one, but that is not part of the current design.

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

Reopens an existing run because the operator chose to resume it, reloads its history, resumes any compatible agent sessions, and opens the same live renderer on top of the stored event history.
This is also the explicit recovery path after crashes or interrupted runs.
We may later allow an optional operator resume note that gets appended to `home/issue.md`, but that is not required for the core design.

### `rally archive`

Explicitly archives a stopped or completed run, moves it under `runs/archive/`, clears any stale active-flow state that should not survive archival, and leaves the repo ready for the next issue.

The point of `archive` is to make "this issue is done, set me up cleanly for the next one" an explicit operator action rather than an automatic cleanup behavior.

## Proposed Terminal Renderer

The live CLI surface should not be a dumb log tail.
It should be a smart renderer backed by the full run event history.

### Renderer behavior

- `rally run` and `rally resume` should both open the same renderer
- on startup, the renderer loads the existing run history from `logs/events.jsonl`
- after loading history, it follows live events as they arrive
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
- for Codex, Rally should point `CODEX_HOME` at the flow home so those home-local skills are the user-scope skills Codex sees for that run
- agents never rely on machine-global skills outside home

This preserves Paperclip's good runtime scoping behavior without needing Paperclip's control plane.

## Proposed MCP Model

Rally should treat MCP definitions the same way it treats skills: repo-owned, explicitly allowlisted, and materialized into home.

- repo-root `mcps/<mcp-slug>/server.toml` stores one MCP definition in a Codex-shaped TOML format
- that file should look like the body of a single `mcp_servers.<name>` entry, not a new invented config DSL
- each flow declares which MCPs each agent may use
- Rally sources those definitions from repo-root `mcps/`
- Rally materializes only the allowed MCPs into `home/mcps/`
- the Codex adapter assembles those materialized definitions into the adapter config it launches with, rather than relying on any global `~/.codex/config.toml`
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
For Codex, Rally should treat the flow home as `CODEX_HOME`, so canonical Codex session state is localized into that run instead of drifting into a global home.

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

## Codex Adapter Contract (Rally-Owned)

Because adapter invocation belongs to Rally, the Codex launch contract is a Rally-owned design surface, not a Doctrine feature.
After inspecting the local Codex code, Rally should treat this boundary as explicit and non-negotiable.

The important finding is that Codex does have useful controls, but it does not give Rally's desired isolation story by default.

Required adapter contract for the Codex adapter:

- set `CODEX_HOME` to the flow home directory, not to `~/.codex` or any other global location
- treat Codex-written files under that flow home as adapter internals, not as Rally semantic truth
- set `project_doc_max_bytes = 0` so Codex does not auto-discover ambient `AGENTS.md` or `AGENTS.override.md` files from the cwd ancestry
- choose `cwd` explicitly from Rally instead of inheriting ambient operator state
- inject the compiled agent doctrine explicitly through Codex's explicit instructions channel, rather than relying on ambient project-doc discovery
- assemble Codex MCP config explicitly from Rally's allowlisted MCP definitions
- require a strict final-turn JSON schema for Rally-managed turn completion so
  end-of-turn control flow does not depend on parsing free-form text
- fail closed if Rally cannot prove what instruction surface Codex is actually seeing

### Structured Final Turn Return

After inspecting the local Codex code, Rally should treat strict JSON final turn
returns as a real existing adapter capability, not as a future hope.

Relevant implementation notes from Codex:

- per-turn turn context already carries `final_output_json_schema`
- session updates can override that schema per turn before the turn starts
- prompt construction forwards that schema as the prompt `output_schema`
- the model request path turns that schema into strict JSON output format
- Codex validates the final return against that schema rather than relying on
  prompt prose alone
- Codex's own guardian/review path already uses this mechanism as a real shipped
  structured-output pattern

The concrete evidence in the current Codex codebase is:

- `TurnContext.final_output_json_schema` in `codex-rs/core/src/codex.rs`
- per-turn application in `new_turn_from_configuration(...)`
- prompt assembly via `Prompt { output_schema: ... }`
- request serialization that emits:
  - `text.format.name = "codex_output_schema"`
  - `text.format.type = "json_schema"`
  - `text.format.strict = true`
  - `text.format.schema = <provided schema>`
- shipped test proof in `codex-rs/core/tests/suite/json_result.rs`
- shipped production precedent in `codex-rs/core/src/guardian/prompt.rs` and
  `codex-rs/core/src/guardian/review_session.rs`

Rally should use that exact path.
It should not rely on prompt prose alone when the adapter already supports a
strict final JSON contract.

Doctrine only needs to expose the authored final-output contract cleanly.
Rally can impose the stricter policy on top:

- the generic Doctrine feature can remain optional overall
- Rally-managed turns that need machine-readable completion must declare a
  final output
- Rally requires that final output to resolve to `TurnResponse`
- Rally requires that final output to be JSON-schema-backed
- Rally passes the resolved schema into Codex as
  `final_output_json_schema`
- Codex enforces conformance at generation time
- Rally consumes the validated JSON result and maps it to `handoff`, `done`,
  `blocker`, or `sleep`

For Codex specifically, the rule should be:

- every Rally-managed turn that needs an end-of-turn result must supply
  `final_output_json_schema`
- that schema must describe the full tagged end-of-turn result union
- Rally should reject adapter output that does not satisfy the schema instead of
  trying to recover from free-form prose
- if an adapter cannot enforce an equivalent strict structured return, Rally
  should treat that adapter as missing required capability for this contract

What this means in practice:

- Rally can localize Codex state into the flow home
- Rally can disable Codex's default ambient project-doc loading
- Rally can strictly control which MCP definitions it injects
- Rally cannot casually claim that the full built-in Codex tool surface is per-agent allowlist-scoped today

Current conclusion:

- the no-side-door promise can be made much more real for instruction surfaces if Rally owns the Codex launch contract
- the no-side-door promise is weaker if Rally leaves Codex on its defaults
- full capability isolation is a stricter claim than instruction isolation and may require additional Codex support

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

## Required Supporting Changes In Doctrine

This section should be treated as a required design surface, not a maybe-later note.
We expect Rally to need supporting changes in Doctrine, and we want to make those changes instead of building permanent workarounds in Rally.
This section exists so future Rally design and implementation work has an explicit home for Doctrine-side requirements.
It is intentionally still a placeholder with direction rather than a fully authored requirement list.
Do not work around core Doctrine gaps just because this section is still incomplete.

What belongs here:

- Doctrine features Rally clearly needs for a clean design
- Doctrine parser, compiler, or generic authored-semantics support that the Rally standard library depends on
- generic final-output designation and emitted-contract support that should live in Doctrine rather than in ad hoc Rally glue
- any change needed so Rally's mandatory Doctrine-native standard library is clean, explicit, and maintainable

We are not fully specifying those changes yet.
We are explicitly reserving space for them because we expect they will be necessary.

Doctrine is close, but not all the way there.
Per the ownership boundary above, the key rule is that Doctrine changes here must stay generic compiler and language support, not Rally runtime ownership.

What does not belong here:

- repo-root layout such as `flows/`, `runs/`, `skills/`, and `mcps/`
- `flow.yaml`, `run.yaml`, `state.yaml`, `home/issue.md`, logs, sessions, or locks
- adapter launch rules such as `cwd`, `CODEX_HOME`, config overrides, MCP assembly, or explicit instruction injection
- CLI commands, terminal rendering, archive behavior, or crash recovery policy
- runtime home enforcement, no-escape checks, or other runner-side validation that belongs to Rally

### 1. Import-root and packaging support for the Rally standard library

Rally needs a reusable standard library under `stdlib/rally/`.
Doctrine should make it straightforward to import and compose that library without brittle path hacks.

Likely needs:

- package or import-root semantics that make standard-library usage clean
- stable resolution rules for shared Doctrine modules
- authoring ergonomics that do not force Rally into wrapper-only composition tricks

### 2. Generic final-output designation for authored turn completion

Rally does need a generic authored way to declare the final return contract for
a turn, but that should not mean adding scheduler keywords such as `sleep`,
`wake`, `resume`, `done`, or `blocker` directly to Doctrine.
The cleaner design is:

- Doctrine adds a generic final-output designation such as `final_output:`
  that points at an existing `output`
- that referenced output can stay ordinary prose in Doctrine generally, or
  schema-backed JSON when a host needs machine-readable structure
- Rally resolves that authored contract and applies stricter host policy on top
- the adapter returns strict JSON when Rally requires machine-readable turn
  completion
- Rally interprets the returned JSON into runtime behavior

Likely needs:

- a generic `final_output:`-style authored surface or equivalent
- support for JSON-schema-backed `TurnResponse` final outputs
- standard-library-friendly composition so Rally can reuse one shared
  end-of-turn contract across flows
- emitted machine-readable structure that lets Rally recover the authored final
  output contract and schema without scraping readback Markdown

### 3. Machine-readable emitted structures Rally can consume

Rally should not scrape human-readable Markdown to reconstruct compiler meaning.
If Rally depends on authored semantics beyond plain readback, Doctrine should emit those structures directly.

Likely needs:

- machine-readable flow graph or equivalent emitted structure
- machine-readable visibility into authored routes, currentness, review wiring, and similar generic semantics
- output formats stable enough for Rally to depend on explicitly

### 4. Capability declarations that stay authored, not runtime-wired

Rally needs a clean authored way for doctrine to refer to required or advisory capabilities, while Rally still owns actual runtime materialization.

Likely needs:

- doctrinal capability references that do not hardwire adapter-specific config
- enough structure that Rally can intersect authored requirements with runtime allowlists
- generic semantics that could serve multiple runners, not just Rally

### 5. Currentness and review extensions if Rally truly needs them

Doctrine already has strong workflow law.
If Rally standard-library patterns expose gaps there, those extensions belong here, but only if they are generic authored semantics.

Possible needs:

- additional typed carriers for current artifact or current mode
- stronger review-family or adjudication support
- other generic workflow semantics that improve more than just Rally

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
Potential future concern:
`home/issue.md` may later prove to be carrying too many jobs at once, but we are deliberately keeping the simple single-ledger model for now.

### 4. Where should flow definitions live?

Provisional answer:
Under the Rally repo root in `flows/`, with sibling `stdlib/`, `skills/`, `mcps/`, and `runs/`, not hidden inside a DB or opaque runtime store.

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
- Rally-owned standard library lives under repo-root `stdlib/`
- explicit current owner and current artifact
- one active run per flow
- no hidden global Rally state
- no GUI
- no board/company/registry product carryover
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
- define the exact source layout and import contract for `stdlib/rally/`
- define how per-agent runtime artifacts are materialized into home
- define the exact event schema for `logs/events.jsonl`
- define the exact renderer line format, colors, and keyboard controls
- define the exact schema for repo-root `mcps/<mcp-slug>/server.toml`
- define the exact session sidecar schema
- define the exact wake and resume message templates per runtime adapter
- define the exact crash-note behavior on operator-driven resume
- define the exact Codex adapter launch contract: `cwd`, `CODEX_HOME`, `project_doc_max_bytes = 0`, explicit instruction injection, and MCP config assembly
- define the exact shared end-of-turn JSON schema Rally will require from the
  adapter
- define how Doctrine's authored final-return contract maps onto adapter schema
  injection such as Codex `final_output_json_schema`
- define what capability isolation Rally can honestly promise with Codex today versus what requires Codex changes
- define the mandatory surface of the Rally Doctrine standard library without fully authoring it here
- keep the `Required Supporting Changes In Doctrine` section current instead of routing around it
- define how Rally computes intervening agents since an agent's last wake
- define the exact adapter-args schema per runtime adapter
- define the exact activation lock format for one-active-run-per-flow
- decide what Doctrine extensions belong in Doctrine versus Rally
- define the explicit Rally-to-Doctrine compatibility contract and failure mode when required compiler support is missing
- define the runtime guard that rejects instruction side doors
- choose the first narrow end-to-end demo flow

## Current Design Opinion

The current best direction is:

- Rally should be a thin filesystem-native runtime on top of Doctrine.
- The control plane should be files first, not tables first.
- Paperclip should influence runtime rigor, not product shape.
- `paperclip_agents` should influence on-disk ergonomics, not framework domain.
- agent instruction content should come from `.prompt` files only, with no side doors.
- Rally should assume fixed repo-root `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/`, not configurable workspace roots.
- each run should get one prepared home, and agents should live entirely inside it.
- Rally-owned state should live in that repo, not in hidden global directories.
- each flow should have at most one active run at a time.
- the operator surface should stay small: one command to run, one to resume, one to archive.
- per-run logs and the terminal renderer should make excavation and live watching excellent.
- built-in turn-start memory and turn-end learning should be a Rally runtime concern, not a special agent-only skill, but the exact implementation can be designed later.
- sleep can stay simple in the current design: block inline and then wake again.
- crash recovery should stay operator-driven rather than background-automated.
- shared handoff and currentness behavior should come from a mandatory
  Doctrine-native Rally standard library.
- the shared final turn result contract should live in one tiny Rally-owned
  Doctrine module such as `rally.turn_results`, separate from handoff/currentness.
- end-of-turn behavior should come from an explicit structured return contract
  that Rally passes to the adapter as a strict JSON schema, not from invented
  Doctrine lifecycle keywords.
- that standard library should live in Rally, while Doctrine stays the compiler and gains only generic enabling features.
- for Codex, instruction isolation should come from Rally controlling `CODEX_HOME`, disabling ambient project-doc loading, and explicitly injecting compiled doctrine.
- for Codex, Rally should use the existing strict final JSON-schema output path
  for end-of-turn returns.
- for Codex, JSON mode for the final turn return should be required whenever
  Rally needs machine-readable turn completion.
- full per-agent capability isolation is a stronger claim than instruction isolation and should only be promised where the adapter actually supports it.
- Rally should not carry over GUI, board, company, or registry product concepts.
- when Rally needs Doctrine support to stay clean, we should add it to Doctrine and track it explicitly in this doc.
- Rally and Doctrine need an explicit compatibility contract rather than silent semantic drift.
- Doctrine should remain the authored language, but Rally will need runtime concepts that Doctrine does not yet own.

That feels like the right center of gravity.

## Exhaustive Design Considerations And Suggested Solutions

This section is meant to be solution-forward.
It is not just a place to restate open questions.
It is the current best design judgment after deeper exploration of `../paperclip`, `../doctrine`, and `../paperclip_agents`.

### 1. Authoring Surface vs Build Output vs Live Runtime

Design consideration:
Rally needs a crisp split between authored `.prompt` source, Doctrine-emitted build output, and the live runtime home.

Suggested solution:
Treat `flows/<flow>/prompts/` as authored source, `flows/<flow>/build/agents/<agent>/` as Doctrine-owned emitted runtime, and `runs/<run-id>/home/agents/<agent>/` as the per-run live copy.
Rally should copy build output into home, not reinterpret or post-compile it into a second semantics layer.

### 2. Only `AGENTS.md` Is Formalized By Rally

Design consideration:
Rally needs one formal runtime contract, but Doctrine may emit additional generated artifacts.

Suggested solution:
Formalize only `AGENTS.md`.
Allow any other Doctrine-generated artifact to exist in build output and get copied into home, but only because Doctrine emitted it and `AGENTS.md` tells the agent to use it.
Do not prescribe artifact names, directory shapes, or conventions beyond that.

### 3. Mandatory Doctrine-Native Rally Standard Library

Design consideration:
Rally needs shared behavior, but it should come from Doctrine, not an ad hoc runtime policy layer.

Suggested solution:
Ship a mandatory Rally standard library written in Doctrine and require all Rally flows and agents to inherit from it.
That standard library should live in Rally under `stdlib/rally/`, not in the Doctrine compiler repo.
That standard library should start by owning the shared conventions for current artifact handoff, `current none` route-only handoff, trusted currentness carriers, and one tiny shared `rally.turn_results` final-output contract module.
It should not own lifecycle keywords or scheduler semantics.
Those should stay in Rally runtime behavior, not in Doctrine syntax.
It should stay light-touch.
It should not define a universal framework-level artifact family or file taxonomy.
Concrete artifacts remain flow-owned outputs.

### 4. Composition First, Inheritance Second

Design consideration:
Doctrine inheritance is powerful but sharp-edged; broad parent changes force child accounting churn.

Suggested solution:
Build the Rally standard library mostly as composable imported Doctrine modules and reusable named declarations.
Use inheritance for narrow, high-value deltas where explicit parent-child accounting is worth the cost.

### 5. Doctrine Must Gain Support Instead Of Rally Working Around It

Design consideration:
Several Rally requirements are not yet first-class in shipped Doctrine.

Suggested solution:
Treat Doctrine-side support as expected work, not as something Rally should dodge.
Keep the ownership boundary explicit:

- Doctrine gets generic compiler and authored-semantics support
- Rally keeps the runner, the runtime contract, and the Rally standard library contents
- `paperclip_agents` remains pressure and examples, not universal framework law

The likely Doctrine work is generic enabling support such as:

- package and import-root support for `stdlib/rally/`
- machine-readable emitted structures Rally can consume without scraping Markdown
- a generic `final_output:`-style authored designation or equivalent that lets
  Rally resolve one turn-ending `TurnResponse` contract and, when needed, its
  JSON schema
- currentness, review, or capability-declaration extensions if the standard library exposes real generic gaps

What should not move into Doctrine:

- run directories and runtime files
- adapter launch rules
- CLI and renderer behavior
- home confinement or no-side-door enforcement logic

### 6. One Issue, One Current Owner, Same-Issue Reassignment

Design consideration:
The strongest reusable pattern in the sample agent families is not “many agents”; it is one current owner with explicit reassignment inside the same issue.

Suggested solution:
Make linear same-issue ownership a stdlib convention.
One agent owns the issue at a time.
Lead-like behavior is route-only reassignment and process repair, not a parallel side-channel.

### 7. Canonical Agent Numbering Is Identity, Not Execution Order

Design consideration:
Numbered agents are useful for debugging and archaeology, but execution order should not be inferred from roster position.

Suggested solution:
Keep the numbered-directory convention.
Treat the number as canonical authored identity only.
Never let Rally infer real execution order from numbering, file order, or roster order.
Execution should always come from explicit routes and actual handoffs.

### 8. Handoffs Must Be Structured And Readable On Their Own

Design consideration:
The next owner should not need to reconstruct state from scattered side files.

Suggested solution:
Put the default handoff block shape in the Rally standard library.
Require Rally flows and agents to inherit that default shape, while still allowing narrow flow-specific extension where needed.
Every handoff should be self-contained enough that the next agent can continue from the issue alone.
At minimum, it should carry current artifact, what changed, what to use now, and next owner.
The handoff should carry the current artifact truth and pickup contract, not replace the artifact itself.
Downstream agents should still read declared artifact inputs rather than treating handoff prose as the full source of truth.

### 9. Currentness Must Be Typed, Not Just Described

Design consideration:
If current artifact, invalidations, active mode, or trigger reason live only in prose, drift will accumulate.

Suggested solution:
Push currentness into Doctrine-native typed carriers and outputs.
Rally should prefer one current artifact at a time.
If Rally later truly needs multiple simultaneous live artifacts, add a Doctrine-native workset or multi-current construct instead of encoding it in ad hoc runtime JSON.
The first standard-library contract here should stay small:

- one trusted `current_artifact` carrier on the shared handoff output
- one `current artifact ... via ...` or `current none` law per active turn branch
- flow-owned artifacts declared explicitly as inputs and outputs

That is enough to make current truth portable without imposing one universal artifact schema on every Rally flow.

### 10. Review Semantics Should Be Reused, Not Rebuilt

Design consideration:
Doctrine already has unusually strong review and review-family semantics.

Suggested solution:
Reuse `review` and `review_family` wherever a Rally lane is actually adjudicative.
Blocker classification, exact failing gates, carried mode, trigger reason, and deterministic next-owner review routing should come from Doctrine review semantics, not a new Rally-only mini-framework.

### 11. Skills And MCPs Need Both Declaration And Runtime Realization

Design consideration:
Configured capabilities and actually callable capabilities are not the same thing.

Suggested solution:
Keep dual surfaces:

- doctrinal capability references in agent doctrine
- runtime allowlists in Rally flow config

Then add a runtime realization check that probes the actual callable surface the run sees.
Rally should fail closed when a required capability is missing or miswired.

### 12. Timeouts Must Be Required, Per-Agent, And Terminal

Design consideration:
Long-running agents need explicit runtime bounds, and timeout behavior must be obvious instead of emergent.

Suggested solution:
Require each agent to declare its own timeout in `flow.yaml`.
Treat timeout as a terminal blocker or error condition for the run.
Do not reinterpret timeout as sleep, silent retry, or best-effort continuation.
When a timeout happens, append a human-readable timeout record to `home/issue.md`, snapshot the issue for archaeology, and stop the run cleanly.

### 13. Per-Agent Sessions Should Also Be Task-Scoped

Design consideration:
Resumable sessions are more precise when they are keyed by both agent and task/run context, not just “whatever session this agent had last.”

Suggested solution:
Persist both per-agent runtime state and per-task session state.
Resume only when the saved session still matches the run home and cwd identity.
If Rally needs timer-based wakes later, give those wakes stable synthetic task keys rather than pretending they are generic resumes.

### 14. Resume Prompting Should Be Delta-Oriented

Design consideration:
Resumed sessions should not be treated like fresh starts.

Suggested solution:
Keep separate initial-wake and resume envelopes.
The resume envelope should be small and factual:

- who resumed the agent
- which agents operated since last wake
- what changed in the issue since last checkpoint
- a directive to check the latest issue and continue following doctrine

Do not reinject the whole world on resume.

### 15. Fresh-Session Rotation Must Be A First-Class Escape Hatch

Design consideration:
Long-lived sessions become stale, bloated, or invalid.

Suggested solution:
Give Rally explicit fresh-session controls:

- force fresh session
- clear/reset session
- rotate after compaction thresholds

When a session is rotated, preserve continuity with a short human-readable handoff note rather than silently discarding history.

### 16. Sleep Can Stay Inline And Simple

Design consideration:
The current runner executes one agent at a time, so a wake queue would add complexity without buying much.

Suggested solution:
When an agent emits `sleep`, append that fact to `home/issue.md`, record the requested duration in logs/state, block the runner for that duration, and then wake the same flow again.
If the process exits during that wait, preserve the run and let the operator decide whether to resume it.
Do not build a wake queue, wake coalescer, or background scheduler in the current design.

### 17. Crash Recovery Should Stay Explicit And Operator-Driven

Design consideration:
Crashes and interruptions are normal, but automatic recovery machinery can easily become overbuilt and dishonest.

Suggested solution:
Do not build a complex startup reaper in the current design.
If a run stops unexpectedly, preserve the run, capture the failure context in logs, and let the operator choose whether to resume it.
When the operator does resume, append a crash note into `home/issue.md` with the last known running agent and known failure context.

### 18. Run Metadata, Append-Only Events, And Raw Transcript Should Stay Separate

Design consideration:
The cleanest operator/debug surface is not one giant log file.

Suggested solution:
Keep three distinct surfaces:

- run metadata in `run.yaml` / `state.yaml`
- append-only structured event history in `logs/events.jsonl`
- flattened human-readable render output in `logs/rendered.log`

This is the right shape for replay, filtering, archaeology, and exact recovery.

### 19. The Renderer Should Be History-Backed, Not A Dumb Tail

Design consideration:
If the renderer only tails stdout, toggles and deep inspection will always be shallow.

Suggested solution:
Back the renderer from the structured event log.
That is what makes whole-history toggles like `T` for tool calls and `R` for reasoning traces actually work.
The renderer should be elegant in real time, and the same architecture can support replay later if we want it.
But a separate replay command is not part of the current design requirement.

### 20. The CLI Should Stay Small But Fail Loud

Design consideration:
The operator surface should be minimal, but the runtime must not silently paper over ambiguity.

Suggested solution:
Keep the primary CLI to `run`, `resume`, and `archive`.
Make `run` conservative and fail loudly on clearly dirty or ambiguous state.
Do not auto-heal confusing state in the background.
If additional recovery verbs are needed later, they should be explicit operator commands rather than hidden fallback behavior.

### 21. Archive And Closeout Should Stay Explicit Operator Commands

Design consideration:
Closeout should not be magical or automatic.

Suggested solution:
Inspect dirty/untracked/ahead/unmerged state when the operator runs the closeout command.
Archive should preserve files, report what is dirty, clear active-flow state only when appropriate, and refuse destructive cleanup.
Never silently delete uncertain state.

### 22. Portable Structure And Ephemeral Runtime State Must Stay Separate

Design consideration:
Reusable structure and live local runtime residue are different classes of data.

Suggested solution:
Treat prompts, build output, issue history, and selected definitions as portable structure.
Treat sessions, logs, local paths, and secrets as ephemeral runtime residue that should not be exported or reused by default.

### 23. Runtime State Should Stay Bundle-Shaped Inside The Repo

Design consideration:
Paperclip is right that runtime state should be grouped coherently instead of smeared across arbitrary surfaces.

Suggested solution:
Keep Rally's authored and operator-visible runtime state in the repo-root structure: `flows/`, `skills/`, `mcps/`, and especially `runs/`.
Within `runs/<run-id>/`, keep sessions, logs, issue history, renderer state, and other runtime artifacts grouped as one excavatable bundle.
If Codex itself stores canonical session state elsewhere, Rally should record stable references back into the run rather than moving Rally's own source of truth out of the repo.

### 24. No Overlays, No Hidden Support Planes

Design consideration:
Cross-cutting reuse is real, but hidden overlay systems create side doors.

Suggested solution:
Reject Paperclip-style overlay thinking for Rally runtime instructions.
If doctrine is shared, it should be shared through `.prompt` imports and the Rally standard library, not through special support-doc activation systems.

### 25. No GUI, Board, Company, Or Registry Carryover

Design consideration:
Paperclip solves real runtime problems, but much of its product surface is outside Rally's core need.

Suggested solution:
Explicitly reject:

- multi-company control planes
- board-centric UI management
- ClipHub/template-registry product layers
- DB-first state as source of truth
- close-management UI as a prerequisite for core runtime correctness

Copy the runtime rigor, not the product shell.

### 26. Adapter Isolation Must Be Explicit And Verified

Design consideration:
The no-side-door promise only holds if the adapter launch contract really suppresses ambient instruction sources and localizes adapter state.

Suggested solution:
For the Codex adapter:

- set `CODEX_HOME` to the flow home directory, not a global location
- disable ambient project-doc discovery with `project_doc_max_bytes = 0`
- choose `cwd` explicitly from Rally
- inject compiled agent doctrine explicitly through Codex's explicit instructions channel instead of relying on ambient `AGENTS.md` discovery
- assemble MCP config explicitly from Rally's allowlisted definitions
- do not claim per-agent built-in tool isolation unless the adapter really supports it

Instruction isolation is an adapter contract.
It is not something Rally should assume from defaults.

## High-Level Roadmap

### Phase 1: Build The Rally Standard Library

Status:
the authored standard-library half of this phase is now done in this repo.

What is implemented:

- shared handoff output shape for one-current-artifact turns
- shared handoff output shape for `current none` turns
- trusted currentness carrier convention
- one tiny shared `rally.turn_results` final-output contract module
- schema and example assets for that shared final-output contract
- the import and composition pattern Rally flows use to adopt those conventions
- `_stdlib_smoke` authored with `final_output:` on concrete agents

What remains in this phase:

- Rally runner-side loading of the resolved `final_output` contract from Doctrine
- adapter-side schema injection such as Codex `final_output_json_schema`
- runtime dispatch of `handoff`, `done`, `blocker`, and `sleep`

The authored doctrine surface is now locked enough to move on to runtime wiring.
The remaining work is runtime and adapter integration, not more stdlib shape invention.

### Phase 2: Build One Placeholder Seeded-Bug Flow

Status:
the authored placeholder-flow half of this phase is now done in this repo.

What is implemented:

- `flows/placeholder_seeded_bug/flow.yaml`
- `flows/placeholder_seeded_bug/setup/prepare_home.sh`
- `flows/placeholder_seeded_bug/prompts/AGENTS.prompt`
- `flows/placeholder_seeded_bug/prompts/shared/`
- `flows/placeholder_seeded_bug/prompts/roles/`
- `flows/placeholder_seeded_bug/fixtures/briefs/seeded_bug.md`
- `flows/placeholder_seeded_bug/fixtures/tiny_issue_service/`
- `flows/placeholder_seeded_bug/build/agents/.../AGENTS.md`
- `skills/repo-search/`
- `skills/pytest-local/`
- `mcps/fixture-repo/server.toml`

What remains in this phase:

- no additional authored surfaces
- runtime execution belongs to Phase 3

After the standard library exists, build one placeholder illustrative flow around a seeded bug in a small sample repo.

The intended story is:

- the operator gives Rally a brief for a seeded bug
- Rally prepares one run home
- a lead agent shapes the work
- an engineer fixes the code
- a proof agent verifies it
- a critic accepts or rejects it
- the lead closes the run

The point of this phase is not that the full runtime already works end to end.
The point is to write the canonical placeholder flow surfaces that later runtime work must satisfy.
Those authored surfaces now exist on disk under `flows/placeholder_seeded_bug/`.

Use four generic agents with numbered directories so the authored order is obvious and the flow stays domain-neutral:

- `01_scope_lead`
  - reads the operator brief
  - decides the exact seam
  - writes `artifacts/repair_plan.md`
  - routes the work
- `02_change_engineer`
  - works in `home/repos/<sample-repo>`
  - makes the code change
  - runs small local checks
  - hands off the current basis clearly
- `03_proof_engineer`
  - runs deterministic verification
  - writes `artifacts/verification.md`
  - either clears the gate or routes back with an exact failure
- `04_acceptance_critic`
  - gives a findings-first `accept` or `changes requested` verdict
- `01_scope_lead`
  - wakes again only to finish with a clean `done` closeout

This is basically the good part of the `paperclip_agents` core-dev route, stripped of GitHub, company state, and product-specific role names.

The placeholder should be authored so later runtime work can prove all of these without changing the flow shape:

- `.prompt` is the only authored instruction source
- Doctrine emits build output from that source
- Rally copies that build output into `runs/<run-id>/home/agents/...` with no handwritten overlay docs
- `flow.yaml` is the runtime contract for numbered agents, per-agent timeouts, allowed skills, at least one allowed MCP, and explicit Codex launch settings
- `setup/prepare_home.sh` is the contract for preparing the only world the agents see, including the target repo, any needed setup artifacts, `home/issue.md`, home-local skills, and home-local MCP config
- the run keeps one live semantic ledger in `home/issue.md`, starting with the operator brief exactly as entered and appending setup notes and handoffs after that
- handoffs stay structured and durable rather than chatty, carrying fields equivalent to what changed, use now, current basis, proof location, and next owner
- one owner is active at a time, and the next owner can pick up from the run home plus the ledger without hidden state
- the flow uses real current artifacts, not just the mutable repo, with `artifacts/repair_plan.md` and `artifacts/verification.md` as the first concrete examples
- proof is independent from implementation
- critic review is findings-first and emits only `accept` or `changes requested` with an exact next owner
- Codex state is localized into the flow home, ambient project-doc discovery is disabled, and compiled doctrine is injected explicitly rather than discovered from repo ancestry
- run-local logs are good enough that one run directory explains what happened without any hidden database or dashboard
- `run`, `resume`, and `archive` later satisfy the authored flow contract rather than forcing the flow to change shape

Keep the first placeholder flow deliberately narrow:

- no GitHub publish or follow-through behavior
- no multiple target repos inside home
- no external-auth MCPs when a small local MCP is enough to exercise the path
- no sleep scheduling unless the placeholder honestly needs it
- no fancy domain logic beyond what is needed to require code change, verification, and review
- no flow-graph artifacts as part of this phase deliverable

The MVP bar remains the same in spirit:
once the runtime catches up to these two phases, someone should be able to open one run directory and understand exactly what was asked, what home was prepared, what each agent saw, what changed, what proof ran, what the critic decided, and why the run ended, without any hidden control plane.

### Phase 3: Build The First Runnable Codex Vertical Slice

Phase 3 is the first runtime phase.
Its job is to prove that Rally can actually execute the authored assets from Phase 1 and Phase 2 without changing those authored assets to fit a weaker runtime.

The core rule for this phase is:
Phase 1 and Phase 2 are inputs.
Phase 3 is the first real runner.

What Phase 3 owns:

- one real CLI entrypoint for Rally
- one real runtime package under `src/rally/`
- one real runnable Codex adapter path
- one real seeded-bug flow execution path from `run` to terminal outcome
- one-active-run-per-flow enforcement
- home preparation, home materialization, ledger append, session sidecars, and run-local logging
- `run` and `resume` as real commands
- `archive` may remain a thin follow-on command after the vertical slice lands
- Rally consumes precompiled Doctrine build output in this phase and fails loudly if required build output is missing

This phase should stay intentionally narrow:

- one adapter: Codex
- one concrete flow family: the Phase 2 seeded-bug flow
- one prepared home per run
- one active owner at a time
- no GUI
- no database
- no background scheduler
- no Doctrine compile orchestration
- no claim of stronger built-in tool isolation than Codex can actually prove

#### Checked-In Repo Structure For Phase 3

Phase 3 should create the following checked-in structure:

```text
<rally-repo-root>/
  pyproject.toml
  src/
    rally/
      __init__.py
      __main__.py
      cli.py
      flow_loader.py
      run_store.py
      issue_ledger.py
      home_materializer.py
      event_log.py
      runner.py
      adapters/
        __init__.py
        codex/
          __init__.py
          launcher.py
          result_contract.py
          session_store.py
  tests/
    unit/
      test_flow_loader.py
      test_run_store.py
      test_issue_ledger.py
      test_home_materializer.py
      test_codex_result_contract.py
    e2e/
      test_seeded_bug_happy_path.py
      test_seeded_bug_resume.py
  flows/
    _stdlib_smoke/
      ...
    placeholder_seeded_bug/
      flow.yaml
      fixtures/
        briefs/
          seeded_bug.md
        tiny_issue_service/
          ...
      setup/
        prepare_home.sh
      prompts/
        AGENTS.prompt
        shared/
          inputs.prompt
          outputs.prompt
          review.prompt
          skills.prompt
        roles/
          scope_lead.prompt
          change_engineer.prompt
          proof_engineer.prompt
          acceptance_critic.prompt
      build/
        agents/
          01_scope_lead/
            AGENTS.md
            ...
          02_change_engineer/
            AGENTS.md
            ...
          03_proof_engineer/
            AGENTS.md
            ...
          04_acceptance_critic/
            AGENTS.md
            ...
  skills/
    repo-search/
      SKILL.md
      ...
    pytest-local/
      SKILL.md
      ...
  mcps/
    fixture-repo/
      server.toml
  stdlib/
    rally/
      ...
  runs/
    active/
    archive/
```

Notes for this structure:

- `src/rally/` is the first real Rally runtime package and should stay small.
- `pyproject.toml` should expose a real CLI entrypoint so Phase 3 can run as `rally ...`.
- `flows/placeholder_seeded_bug/fixtures/tiny_issue_service/` is a phase-local sample target repo used to exercise the runtime. It is not a framework primitive.
- `flows/placeholder_seeded_bug/` is the authored flow from Phase 2 and remains the only required runnable flow in this phase.
- `flows/placeholder_seeded_bug/build/` is an input to the runner in this phase, not something Rally generates.
- `skills/repo-search/`, `skills/pytest-local/`, and `mcps/fixture-repo/` exist only to exercise allowlist materialization and adapter wiring with a tiny local surface.
- `runs/` is runtime-created state. Only placeholder directories such as `active/` and `archive/` need to exist in git.

#### Runtime-Created Run Structure For Phase 3

For one concrete run of `flows/placeholder_seeded_bug/`, Rally should create the following runtime structure:

```text
<rally-repo-root>/
  runs/
    active/
      placeholder_seeded_bug.lock
    <run-id>/
      run.yaml
      state.yaml
      logs/
        events.jsonl
        rendered.log
        agents/
          01_scope_lead.jsonl
          02_change_engineer.jsonl
          03_proof_engineer.jsonl
          04_acceptance_critic.jsonl
        adapter_launch/
          01_scope_lead.json
          02_change_engineer.json
          03_proof_engineer.json
          04_acceptance_critic.json
      issue_history/
        0001-<timestamp>-01_scope_lead-to-02_change_engineer.md
        0002-<timestamp>-02_change_engineer-to-03_proof_engineer.md
        0003-<timestamp>-03_proof_engineer-to-04_acceptance_critic.md
        0004-<timestamp>-04_acceptance_critic-to-01_scope_lead.md
      home/
        issue.md
        artifacts/
          repair_plan.md
          verification.md
        agents/
          01_scope_lead/
            AGENTS.md
            ...
          02_change_engineer/
            AGENTS.md
            ...
          03_proof_engineer/
            AGENTS.md
            ...
          04_acceptance_critic/
            AGENTS.md
            ...
        skills/
          repo-search/
            SKILL.md
            ...
          pytest-local/
            SKILL.md
            ...
        mcps/
          fixture-repo/
            server.toml
        repos/
          tiny_issue_service/
            ...
        sessions/
          01_scope_lead.json
          02_change_engineer.json
          03_proof_engineer.json
          04_acceptance_critic.json
```

Notes for this runtime structure:

- `placeholder_seeded_bug.lock` is the one-active-run-per-flow proof point for this phase.
- `run.yaml` is the stable identity surface for the run.
- `state.yaml` is the small machine-readable current-status surface.
- `logs/events.jsonl` is the merged structured event stream for the run.
- `logs/agents/*.jsonl` are filtered per-agent slices.
- `logs/adapter_launch/*.json` is the explicit proof surface for the Codex launch contract used on each turn.
- `home/issue.md` remains the live human-readable ledger.
- `issue_history/` stores full-file snapshots after each handoff append.
- `home/artifacts/repair_plan.md` and `home/artifacts/verification.md` are the first concrete current-artifact examples for this flow.
- `home/repos/tiny_issue_service/` is the writable working copy of the sample repo prepared by `setup/prepare_home.sh`.
- `home/agents/` is a per-run copy of the compiled Doctrine build output.
- `home/skills/` and `home/mcps/` are the only runtime capability surfaces Rally intentionally presents to agents.
- adapter-owned Codex residue may also appear somewhere under `home/` because `CODEX_HOME` points there, but Rally must not depend on opaque adapter-private file names to explain the run.

#### Required Behavior In Phase 3

Phase 3 should prove the following behavior end to end:

- `rally run placeholder_seeded_bug --brief-file flows/placeholder_seeded_bug/fixtures/briefs/seeded_bug.md` creates a new run directory, acquires the active-flow lock, writes the operator brief to `home/issue.md`, and runs the seeded-bug flow.
- Rally reads `flows/placeholder_seeded_bug/flow.yaml` and consumes `flows/placeholder_seeded_bug/build/agents/...` as already-compiled input.
- `setup/prepare_home.sh` runs once, prepares `home/repos/tiny_issue_service/`, and may append setup notes below the original operator brief.
- Rally copies the compiled agent build output into `home/agents/` and materializes only the allowlisted skills and MCP definitions into `home/skills/` and `home/mcps/`.
- Rally launches Codex with an explicit contract on every turn: chosen `cwd`, `CODEX_HOME=<run-home>`, ambient project-doc discovery disabled, compiled doctrine injected explicitly, and the shared final-turn JSON schema attached explicitly.
- Rally validates the final turn result against the shared `rally.turn_results` contract before using it for runtime behavior.
- On `handoff`, Rally appends to `home/issue.md`, snapshots the full ledger into `issue_history/`, updates `state.yaml`, and wakes the next owner in the same home.
- On `done` or `blocker`, Rally records the final state, preserves the run directory, and clears the active-flow lock.
- On interruption, Rally preserves the run directory and session sidecars, and `rally resume <run-id>` continues the same run rather than creating a replacement run.
- `sleep` support may exist in runner logic and unit coverage, but the seeded-bug end-to-end flow does not need to exercise `sleep` in this phase.

#### Acceptance Criteria For Phase 3

Phase 3 is complete only when all of the following are true:

1. `rally run placeholder_seeded_bug --brief-file flows/placeholder_seeded_bug/fixtures/briefs/seeded_bug.md` succeeds from a clean repo state when `flows/placeholder_seeded_bug/build/` is present.
2. During execution, Rally creates exactly one active-flow lock at `runs/active/placeholder_seeded_bug.lock`, and that lock is cleared when the run reaches `done` or `blocker`.
3. The run directory contains `run.yaml`, `state.yaml`, `logs/events.jsonl`, `home/issue.md`, `issue_history/`, `home/agents/`, `home/skills/`, `home/mcps/`, `home/repos/tiny_issue_service/`, and `home/sessions/`.
4. The original operator brief remains at the top of `home/issue.md`, and setup notes plus handoffs are appended below it rather than prepended above it.
5. The run produces `home/artifacts/repair_plan.md` and `home/artifacts/verification.md`, and those artifacts are the surfaces referenced by the seeded-bug handoffs.
6. After every handoff append, Rally writes a full-copy snapshot into `issue_history/` with a monotonic timestamped filename.
7. `logs/adapter_launch/*.json` proves that every Codex turn used Rally-chosen `cwd`, `CODEX_HOME` rooted in the run home, disabled ambient project-doc discovery, explicit compiled-doctrine injection, and an explicit final-output JSON schema.
8. Only allowlisted skills and MCP definitions appear in `home/skills/` and `home/mcps/`; repo-root entries not named in `flow.yaml` do not appear there.
9. A seeded-bug happy path completes through the authored ownership chain `01_scope_lead -> 02_change_engineer -> 03_proof_engineer -> 04_acceptance_critic -> 01_scope_lead` and ends in a terminal `done`.
10. An interrupted run after at least one handoff can be completed with `rally resume <run-id>` without changing the run id, deleting prior logs, or rewriting prior ledger history.
11. A failure path such as invalid final JSON, missing compiled build output, missing current artifact, or attempted home escape fails loudly, preserves the run directory for archaeology, and does not silently continue.
12. A canary ambient instruction source outside the compiled flow build output does not appear in the injected instruction payload or in the run-home agent surfaces, proving the no-side-door contract for this phase.
13. Rally creates no Rally-owned state outside the repo root during the run. There is no hidden Rally control plane under `~/.rally`, `~/.config`, or similar global locations.
14. Unit coverage exists for the runner branch that handles `sleep`, even though the seeded-bug end-to-end flow does not use `sleep`.

#### Explicit Non-Goals For Phase 3

Phase 3 should not widen into any of the following:

- a second runtime adapter
- a second fully supported flow family
- Doctrine compilation orchestration
- parallel-agent execution
- background wake scheduling
- archive/cleanup ergonomics beyond what is needed to preserve the finished run honestly
- GUI, board, company, registry, or plugin-platform surface area
- broad built-in tool isolation claims beyond what the Codex adapter can truly prove
