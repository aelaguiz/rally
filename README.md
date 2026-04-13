# Rally

**Rally is the filesystem-first way to build complex agent flows that actually work.**

Rally is a CLI-native runtime for multi-agent work that needs to stay stable,
inspectable, and honest under pressure. You author flows in Doctrine. Rally
prepares one run home, launches one owner at a time, keeps the live issue on
disk, records every durable note and final turn result, and routes only from
validated JSON.

The goal is simple: make serious agent work feel more like running a small,
well-built program and less like hoping a pile of prompts, tabs, and hidden
state does not drift apart.

> This README describes Rally's target v1 shape. It is the product this repo is
> building toward, not a claim that every command is fully shipped today.

## Why Rally Exists

Most agent systems are easy to demo and hard to trust.

They usually break in one of these ways:

- The source of truth is copied Markdown, so one fix misses three siblings.
- Routing lives in prose, so the runtime has to guess what "go next" means.
- State is split across a UI, a database, logs, home-dir caches, and ad hoc
  files.
- Agents can see more than you think because the runtime leaks ambient docs or
  hidden instructions.
- Parallel work starts before the system can clearly answer basic questions
  like "who owns this now?" and "what artifact is current?"

Rally picks the opposite defaults.

- Flow source lives in Doctrine `.prompt` files.
- Runtime truth lives on disk under the repo root.
- Agents end turns with one strict JSON result.
- Durable notes are allowed, but notes never control routing.
- One active run per flow is the default.
- The run home is the whole world for that run.

The result is a system you can inspect with normal tools: `cat`, `rg`, `git`,
and your editor.

## What Rally Is

Rally is:

- a flow runner
- issue-first
- CLI-first
- filesystem-first
- Doctrine-native
- repo-root-native
- adapter-aware, with Codex as the first target

Rally is not:

- a company operating system
- a task dashboard
- a database-first control plane
- a web app you need open all day
- a hidden prompt injection layer
- a vague "agent platform"

## Rally vs. Paperclip

Paperclip and Rally are related in spirit, but they are not trying to be the
same product.

Paperclip asks, "How do I run a company made of agents?"

Rally asks, "How do I run one authored flow in a way that stays stable,
inspectable, and easy to debug?"

| Area | Paperclip | Rally |
| --- | --- | --- |
| Core unit | company | flow |
| Operator surface | server, API, React UI, dashboard | CLI and files |
| State model | Postgres plus app state | repo-local files under `runs/` |
| Main metaphor | org chart, goals, budgets, governance | issue, current artifact, next owner, run |
| Execution model | heartbeats, triggers, many agents across a company | one active run per flow, one clear owner at a time |
| Product shell | multi-company control plane | narrow runtime |
| Visibility | app views and logs | `issue.md`, snapshots, state files, event logs |

### What Rally Keeps From Paperclip

These are the ideas Rally clearly loves and keeps:

- issue-centered work
- resumable sessions
- durable run lifecycle
- exact ownership changes
- strict control over who works next
- prepared working homes instead of loose ambient state
- durable notes that later turns can read
- archaeology that survives restarts

Paperclip proved that these ideas matter.
Rally keeps them, but moves them into a smaller and more inspectable shell.

### What Rally Cuts On Purpose

These are the ideas Rally treats as too heavy for its core:

- database-first state
- web UI as the main operator surface
- dashboards, boards, and company views
- org charts and company hierarchy as framework law
- budgets, cost centers, and governance layers
- marketplace or registry product ideas
- hidden global control planes under home-dir config folders
- parallel agents as a default execution model

That last point matters.
Parallel agents are not banned forever because they are bad in theory. Rally
pushes them out of the default design because concurrency multiplies confusion
fast. Rally wants honest ownership, readable history, and exact routing before
it earns more parallelism.

## The Big Bet

**Flows are code. Runs are files.**

Author the flow like software.
Run the flow like a process.
Inspect the result like a repo.

That means Rally has a very opinionated repo shape:

```text
flows/     authored flows and compiled readback
stdlib/    Rally's shared Doctrine library
skills/    reusable skill definitions
mcps/      reusable MCP definitions
runs/      all Rally-owned runtime state
```

And a very opinionated run shape:

```text
runs/BUG-17/
  run.yaml
  state.yaml
  issue_history/
  logs/events.jsonl
  home/
    issue.md
    agents/
    skills/
    mcps/
    repos/
    sessions/
```

If something important happened, Rally should leave a readable trace in that
tree.

## Why Doctrine Matters

Rally only makes sense with Doctrine.

Doctrine is the authored language for Rally flows. It is not a prompt template
tool. It is a small DSL for writing reusable agent doctrine as code and
compiling it into runtime `AGENTS.md` artifacts that existing coding agents can
consume.

Doctrine gives Rally the parts normal prompt folders do not:

- named workflows
- explicit inheritance
- typed inputs and outputs
- first-class review logic
- shared route semantics
- schema-backed final outputs
- fail-loud compile errors when the authored flow is dishonest or incomplete
- machine-readable review metadata when a flow uses Doctrine `review:`

In practice, that means humans and coding agents edit this:

```prompt
workflow ProofEngineerWorkflow: "Proof Engineer Workflow"
    flow_story: "Flow Story"
        "Write `artifacts/verification.md` and keep using it while the bug moves forward or back."

output ProofEngineerTurnResult: "Proof Engineer Turn Result"
    target: TurnResponse
    shape: rally.turn_results.RallyTurnResultJson

agent ProofEngineer:
    workflow: ProofEngineerWorkflow
    outputs: "Outputs"
        shared.outputs.VerificationReport
        shared.outputs.ProofEngineerTurnResult
    final_output: shared.outputs.ProofEngineerTurnResult
```

Doctrine compiles it into runtime readback that agents can read today.
Rally consumes that compiled output at runtime, but the `.prompt` graph stays
the source of truth.

That split is a big deal:

- authors edit structure, not giant emitted Markdown blobs
- shared rules land once
- route and final-output meaning stay typed
- Rally can read control-ready review JSON from compiler metadata
- Rally does not need to scrape prose to guess what the flow meant

## The Rally Model

Rally keeps the model small.

### 1. A Flow

A flow is a repeatable multi-agent process under `flows/<flow>/`.

Each runnable flow has:

- Doctrine source in `flows/<flow>/prompts/**`
- compiled readback in `flows/<flow>/build/**`
- runtime config in `flows/<flow>/flow.yaml`
- one start agent
- one three-letter flow code

### 2. A Run

A run is one execution of a flow.

Run IDs look like `<FLOW_CODE>-<n>`, for example `BUG-17`.

Rally keeps one active run per flow by default.
That rule is not an implementation detail. It is part of the trust model.

### 3. A Home

Each run gets one prepared home.

The home is where Rally materializes:

- compiled agent outputs
- allowlisted skills
- allowlisted MCPs
- writable repos
- sessions
- run-local artifacts

Agents should not have to guess where the world is.
Rally gives them one world and names it clearly.

### 4. An Issue Ledger

`home/issue.md` is the live semantic ledger for the run.

It starts with the operator brief.
Rally does not create a second shared brief file.
After that, Rally appends trusted runtime records in order.

The issue ledger is where later readers should look first.
It is not a side note. It is the run history.

### 5. Durable Notes

Notes are allowed and important, but they are narrow.

Notes are:

- durable context
- append-only
- written through `rally issue note`
- visible in the issue ledger

Notes are not:

- route truth
- blocker truth
- done truth
- sleep truth

That control lives only in the final turn result.

### 6. One Final Turn Result

Every Rally-managed turn ends with one strict JSON result.

That result tells Rally one of four things:

- `handoff`
- `done`
- `blocker`
- `sleep`

If the turn routes, the JSON must name the next owner key.
Not the display name. Not prose. The structural key.

This is one of Rally's most important rules:

**route from validated JSON, never from prose.**

### 7. Currentness

Rally keeps currentness typed.

At any point, the flow should be able to say either:

- this is the current artifact
- there is no current artifact

Rally does not want to reconstruct "what matters now" from chat history.

## Why Rally Should Stay Stable

Rally's stability comes from design choices, not from optimism.

- One instruction source: the declared Doctrine prompt graph.
- One turn-ending control path: the declared final JSON.
- One visible semantic ledger: `home/issue.md`.
- One active run per flow by default.
- One prepared home per run.
- One clear line between durable notes and control truth.
- One repo-local state tree under `runs/`.

Those choices make Rally slower to broaden, but much easier to trust.

## Why Rally Should Stay Inspectable

Rally treats inspectability as a feature, not as a debugging aid bolted on
later.

You should be able to answer these questions from the filesystem:

- What flow ran?
- What run is this?
- What was the original brief?
- What artifact was current?
- What note got left?
- What final result ended the last turn?
- Why did ownership move?
- What exact instruction payload did the agent see?
- What skills and MCPs were allowed?
- Can I resume this honestly?

If the answer requires opening a hidden database or clicking around a dashboard,
Rally has drifted away from its purpose.

## The Operator Surface

Rally's target operator surface is intentionally small:

```bash
rally run <flow>
rally resume <FLOW_CODE>-<n>
rally archive <FLOW_CODE>-<n>
rally issue note --run-id <FLOW_CODE>-<n>
```

That small surface is a feature.
Rally is trying to make complex flows operable without building a giant control
plane around them.
`rally run` creates the run shell under `runs/active/<run-id>/`.
If `home/issue.md` is missing or blank, Rally stops there, tells the operator
to fill in that file, and then continues through `rally resume <run-id>`.

## The Adapter Contract

Rally is adapter-aware, but adapters must stay honest.

For Codex, Rally's launch contract is explicit:

- set `cwd` on purpose
- set `CODEX_HOME` to the run home
- inject compiled Doctrine on purpose
- turn off ambient project-doc discovery
- inject `RALLY_RUN_ID` and `RALLY_FLOW_CODE`
- assemble MCP config from Rally allowlists
- require a strict final-output JSON schema

If Rally cannot prove what the agent saw, it should fail closed.

## Concepts Rally Loves

If you want the short version of the Rally taste:

- issues over chats
- files over hidden state
- runs over vague sessions
- typed outputs over prose guesses
- reviews as first-class flow steps
- current artifact over fuzzy context
- explicit routing over implied routing
- prepared homes over ambient repo state
- resumable archaeology over dashboards
- memory as markdown files plus an index, not as database truth

## Concepts Rally Finds Too Heavy

These are the things Rally resists as core framework features:

- DB-first storage
- web UI
- dashboard-first operation
- company models
- org charts
- budgets
- scheduler-heavy heartbeat systems
- registry and marketplace products
- hidden prompt overlays
- ambient project-doc bleed-through
- parallel-agent defaults

Rally may support some of these at the edges one day.
It should not need them to be useful.

## A Concrete Example

The main Rally flow today is `poem_loop`.

It is narrow on purpose:

1. A poem writer reads the opening issue from `home/issue.md`.
2. The writer drafts `artifacts/poem.md`.
3. The writer keeps short draft notes on `home/issue.md`.
4. The critic uses a Doctrine `review:` turn with one JSON review response.
5. Rally reads that review JSON, saves a review note on `home/issue.md`, and
   either routes the poem back for another draft or ends the run.

It still proves:

- explicit ownership changes
- durable artifacts
- typed currentness
- review-driven routing
- strict final turn control
- honest resume

## Future Memory, Kept Honest

Rally's memory story follows the same rules.

The target model is:

- markdown memory files under `runs/`
- QMD as a search index over those files
- repo-local config and cache paths
- explicit memory lookup and save behavior
- visible memory events in the issue ledger

Even memory does not get a side door.

## Why Open Source

Rally is trying to make agent orchestration legible.

That only works if the core ideas are inspectable by everyone:

- how flows are authored
- how runs are stored
- how routing is decided
- how adapters are constrained
- how notes, memory, and final control stay separate

Open source is not just a distribution choice here.
It is part of the trust model.

## Read Next

- [docs/RALLY_MASTER_DESIGN_2026-04-12.md](docs/RALLY_MASTER_DESIGN_2026-04-12.md)
- [docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md](docs/RALLY_PHASE_3_ISSUE_COMMUNICATION_PIVOT_2026-04-13.md)
- [docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md](docs/RALLY_PHASE_4_RUNTIME_VERTICAL_SLICE_2026-04-12.md)
- [docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md](docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md)
- [../doctrine/README.md](../doctrine/README.md)

## One-Sentence Thesis

Rally takes the hard-earned orchestration lessons from Paperclip, combines them
with Doctrine's authored flow language, throws away the company shell, and
turns the result into a narrow open source runtime for complex agent flows that
stay stable, inspectable, and real.
