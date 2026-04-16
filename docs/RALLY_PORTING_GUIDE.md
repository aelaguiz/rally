---
title: "Rally Porting Guide"
status: active
doc_type: architecture_detail
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_EXTERNAL_PROJECT_INTEGRATION_MODEL.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_CLI_AND_LOGGING.md
  - README.md
  - AGENTS.md
---

# TL;DR

## Outcome

This is the canonical guide for porting an existing agent system into Rally.
It records the durable rules, the real examples, and the common traps.

This guide is grounded in real ports, but it does not turn one port's file
names, role names, or mode names into Rally law.

The lesson is simple:
Port the job, the contracts, and the real runtime truth.
Leave the old harness shape behind.

## What A Rally Port Really Is

A Rally port is not a syntax rewrite.
It is not "take the old prompt tree and make it compile in a new repo."

A good Rally port does five things:

1. It moves runtime truth into Rally-owned surfaces like `flow.yaml`,
   `home:issue.md`, `runs/`, and flow-local setup scripts.
2. It keeps authored instructions in `.prompt` source and treats emitted
   Markdown as generated readback.
3. It gives each lane one main current artifact and says plainly when there is
   no current artifact yet.
4. It turns repeated procedure into skills or setup helpers instead of
   reteaching raw commands in every role home.
5. It uses Doctrine-owned structured outputs for JSON contracts, not
   Rally-owned raw schema files.
6. It drops source-system control planes that Rally does not need.

## Lead With The Move

Agents respond better to direct positive framing than to a wall of bans.

Say the move first:

- `Use rally issue current first, then keep going from the named current
  artifact.`
- `Write one readable note and name the current artifact.`
- `Set the next owner in final JSON when the route is clear.`

Use `do not` for the cases that really need a hard stop:

- safety rules
- one-way mistakes
- red lines where the wrong move creates drift or bad state

## Model Review Work As Review

When a lane's main job is to judge submitted work against a contract, leave a
verdict, and route the next owner, model that lane as Doctrine review law.

Reach for `review` or `review_family` first.

That keeps the important review parts in the right owner:

- the review subject
- the review contract
- the verdict fields
- basis checks and blockers
- pass and fail routing
- what stays current after accept or reject

Use ordinary agent workflow prose when the lane is producing work.
Use review law when the lane is judging work.

## Use Doctrine For JSON Outputs

When a port needs structured JSON, write that contract in Doctrine prompt
source.

Use:

- `output schema` for the JSON object
- `output shape` and `final_output` for the final response
- `review` or `review_family` when the JSON is review control
- imports and inheritance when a flow extends a shared contract

Do not add Rally-owned `.schema.json` or `.example.json` files for framework
or shipped-demo JSON.

After emit, Rally reads the package Doctrine built:

- `AGENTS.md` for human instruction readback
- `schemas/<name>.schema.json` for the JSON wire shape
- `final_output.contract.json` for final-output and review-control metadata
- optional peer files such as `SOUL.md` as compiler-owned readback, not
  Rally-owned side output

That pattern has to work for Rally users too. A user should be able to inherit
or extend the shared Rally JSON contract in their own prompt source without
copying raw JSON into their flow.

## The Real Failure Patterns

These matter more than the generic port checklist.

### 1. Do Not Build A Second State Machine Or Mode-Gate System On Top Of Rally

The first pass added a whole reducer-fed control plane:

- `flow.yaml` used `prompt_input_command` to run a reducer every turn
- shared prompt inputs defined typed route and review facts
- setup code parsed `home:issue.md` into a custom state model
- setup code fed that model back into prompts
- prompts started depending on mode gates like `waiting`, `review_mode`, or
  `active_mode`

The current cleanup deletes that stack.
That is the right direction.

Why this matters:

- Rally already has `home:issue.md`
- Rally already has notes
- Rally already ends turns with final JSON
- the latest turn result already tells the next agent who worked last and what
  happened
- a second state machine drifts, grows, and starts owning truth that Rally
  should own

Bad Rally usage examples:

- declaring a `Prompt` input that only exists because Rally ran a per-turn
  script and appended computed JSON after the compiled agent home
- parsing `home:issue.md` into fields like `selected_mode`,
  `review_basis_missing`, or `last_turn_agent` and then feeding those fields
  back into prompts as if they were first-class runtime truth
- teaching roles to "read the runtime facts" when the real truth is already in
  `home:issue.md`, the latest turn result, or a deterministic tool call

Port rule:

- if the agent can read `home:issue.md` and the latest turn result directly,
  prefer that
- do not add a special mode gate just to restate what the issue and last turn
  already say
- Rally does not support `runtime.prompt_input_command`
- expose runtime truth through files, setup, tools, or `rally issue current`
  instead of prompt-side reducers
- do not use a fake typed `Prompt` input as a disguise for a Rally-side
  reducer or summary script

### 2. Do Not Turn Deterministic Repo State Into Prompt State

One port tried to feed git and repo status back into the prompt as a JSON
summary:

- current branch
- head commit
- dirty state
- `git status --short`
- recent commit messages

That looked helpful.
It was not the Rally move.

Why this matters:

- repo state is deterministic
- Rally already has deterministic skills and repo files
- turning tool state into prompt prose adds context bloat and stale mirrors
- a role should read the repo or call the tool, not trust a hand-built summary

Bad Rally usage examples:

- a per-turn script that turns `git status` into `Demo Repo Facts`
- a `Prompt` input that mirrors branch and commit state instead of using
  `demo-git`
- grounding rules that whitelist summary keys like `demo_repo_status` or
  `current_branch` when the role can read the repo directly

Port rule:

- keep deterministic repo truth on deterministic surfaces
- use file inputs and skills for repo state
- do not feed git summaries into prompt context just because a source system
  used a reducer

### 3. Do Not Turn Notes Into A Tiny Database

The first pass taught agents to write a fenced YAML block with fields like:

- `note_kind`
- `review_mode`
- `active_mode`
- `trigger_reason`
- `publish_state`
- issue-backed artifact ids like `issue:<artifact>`

The current cleanup removes that typed note protocol from shared contracts,
shared review rules, role prompts, tests, and fixtures.

That is also the right direction.

Why this matters:

- readable notes are for humans and agents
- route truth already lives in final JSON
- current truth can be carried by `Current Artifact`, `Invalidations`, and the
  readable note body
- a YAML protocol inside the note becomes another thing to keep in sync

Port rule:

- keep notes readable first
- put route truth in final JSON
- put work truth in the note plus the named current artifact
- do not invent note-local enums and ids unless Rally truly needs them

### 4. Do Not Make The Critic A Second Workflow Engine

The first critic pass grew into a giant review machine:

- big `review_family` trees
- mode selectors
- copied gate routing
- shared input objects for producer handoff and review state
- carried mode and trigger fields in the note protocol

The current cleanup cuts that down hard.

Why this matters:

- the reviewed contract should own the real content checks
- the critic should review the current artifact and leave a readable verdict
- when the critic becomes its own engine, you duplicate route law and current
  truth in one more place

Bad Rally usage examples:

- one giant critic agent with a selector-driven `review_family` whose mode is
  derived from parsed ledger state
- `selected_mode` fields that only exist to tell the critic whether it is
  doing architect, developer, or QA review
- `review_basis_missing` checks that exist only because the graph is too vague
  to say which review should run next

The cleaner Rally move is usually simpler:

- one producer lane per real job
- one reviewer lane per real review contract
- shared review shape only where the comment contract is truly shared
- route topology that already says which reviewer should run next

Port rule:

- keep the critic focused on findings, current artifact, invalidations, and
  next owner
- let the contract own the artifact rules
- let Doctrine review law own pass-fail review behavior
- do not build a second routing VM inside critic prose
- use selector-driven `review_family` only when the runtime has one honest
  structured selector input
- do not use a selector as a patch around unclear lane ownership

### 5. Do Not Let "Read The Ledger" Turn Into "Guess From The Ledger"

Deleting the reducer layer is good.
Deleting explicit pickup truth is bad.

The clean Rally move is:

- read the newest Rally turn result directly
- read the newest explicit Rally note only when one exists
- name the main current surface in the note when a note is needed
- make the pickup summary and proof pointer explicit

That is the good version of simplification.

The bad version would be:

- delete the explicit current surface
- delete the pickup summary and proof pointer
- leave the next agent to infer mode, current file, or next step from vague
  prose

Another bad version is subtler:

- read the latest review turn result
- summarize its verdict, next owner, and findings into a new prompt JSON blob
- feed that blob back into producer prompts as `latest_critic_review`

That is still guessing from the ledger.
It just does the guessing in setup code instead of in the role.

Port rule:

- if you remove helper machinery, keep the note pickup explicit in plain prose
- if the latest turn result and latest note already tell the next agent what
  happened, do not invent a separate waiting or mode gate
- the note still has to say what is current, what changed, and what the next
  owner should read first
- do not feed a review summary back into prompt context when the real review
  turn result already exists in `home:issue.md`

### 6. Move Bootstrap Out Of Agent Doctrine

The source system had setup behavior that looked like a runtime skill.
The Rally port did better when it moved that into flow-local setup:

- bootstrap behavior moved into `flows/<flow>/setup/prepare_home.sh`
- config staging moved into another flow-local setup step
- host requirements stayed in `flows/<flow>/flow.yaml`

Why this matters:

- setup is usually not the role's live job
- bootstrap should happen before the role starts
- role homes get smaller and truer when setup leaves them

Bad Rally usage examples:

- setup already copied the last good repo state forward, but the prompt still
  got a second `carry_forward_source` summary blob
- setup already checked out the real branch, but the role was still told to
  trust injected carry-forward metadata

Port rule:

- if a skill mostly prepares the run home, make it setup
- keep runtime skills for live agent work
- keep continuity in the prepared run home, not in a second prompt fact bag

### 7. Keep One Runtime Authority For Capabilities

Many source systems use a second agent config file.
Rally uses `flows/<flow>/flow.yaml`.

That is the right move.

Why this matters:

- agents need one capability truth surface
- if prompts say one thing and config says another, the port is lying
- dead source config files linger as fake truth unless you cut them cleanly

Port rule:

- `flow.yaml` owns runtime capability truth
- prompt prose should match it
- do not keep a second live allowlist file

### 8. Do Not Call A Deletion A Win Unless The Proof Survives

The current cleanup deletes a lot:

- `issue_state.py`
- `prompt_inputs.py`
- `shared/inputs.prompt`
- note fixtures that only proved the old control plane
- tests that proved the old prompt-input pipeline

That cleanup is mostly right.
Those files were part of the extra control plane Rally did not want.
The only question is whether proof moved to the right layer.

The surviving good proof paths are:

- render verification on the real runtime entrypoint
- scaffold or smoke checks on the live flow

That still leaves an important rule.

Port rule:

- when you delete extra machinery, keep one honest proof path for the behavior
  that still matters
- prefer smoke tests, emitted-readback checks, and real run proofs over tests
  for helper machinery you are trying to delete

### 9. Simplify Law, But Keep The Real Stop Lines

The newer cleanup is right to remove a lot of overfit port machinery.
The real risk is narrower:

- remove a fake framework artifact
- and accidentally remove a real stop line with it

The answer is not to keep the old machinery.
The answer is to keep the real constraint in the smallest honest place.

Why this matters:

- later lanes still need clear scope boundaries
- missing-truth stop lines still need to be explicit
- rebuild or restart boundaries still need to be explicit
- but those things do not need a fake typed control plane wrapped around them

Port rule:

- keep the real stop lines and scope locks
- do not keep extra framework-looking machinery just because it once carried
  those rules
- put the rule in the smallest honest owner and keep moving

### 10. Compression Is Good Only When Behavior Survives

The current diff makes many role homes much shorter.
That is good only when the important behavior still survives:

- route-only turns stay explicit
- publish follow-up stays explicit
- missing-truth recovery still routes back to the lead role
- invalidations still stay visible
- metadata follow-up still stays one bounded pass at a time

Port rule:

- compress repeated prose
- do not compress away the stop lines, recovery paths, or current-truth rules

### 11. Do Not Repeat Shared Rally Law Across Three Layers

Ports often start by copying the same rule into:

- Rally stdlib
- flow-shared prompt source
- role-local prompt source

That is bad Rally usage.

Why this matters:

- repeated rules bloat always-on context
- slight wording drift creates fake conflicts
- local ports start restating Rally-owned commands that stdlib already owns
- the port becomes harder to clean up because no one surface owns the rule

Bad Rally usage examples:

- repeating the same note-writing and final-JSON law in stdlib, shared
  contracts, and each role home
- copying Rally-owned "read the ledger first" commands into every role even
  though stdlib already says it
- restating the same review pickup and handoff law in several reviewer prompts

Port rule:

- give each durable rule one owner
- if Rally stdlib already teaches the rule, add only local exceptions
- keep flow-local prose for flow-local truth, not for Rally-wide behavior

### 12. Prefer One Shared Review Shape Until Reality Forces A Split

The first port overbuilt the critic.
The newer cleanup is right to pull it back toward one shared review shape.

Why this matters:

- most review lanes want the same durable outputs: findings, current artifact,
  invalidations, and next owner
- one shared review shape is easier to keep honest
- a split should happen only when the runtime or contract truth really differs,
  not because the source system had more machinery

Port rule:

- default to one shared review shape
- split only when one lane has a real different runtime contract or stop rule
- do not rebuild a giant critic engine just to mirror the source system

### 13. Keep The Verifier On The Real Runtime Path

A render-diff harness is useful.
That matters even more after a cleanup.

If the topology changes, the verifier still needs to compile and inspect the
same path the runtime uses.

Bad cleanup:

- fewer files
- simpler verifier
- less coverage

Good cleanup:

- fewer files
- same or better coverage of the real runtime entrypoint

Port rule:

- when you simplify prompt topology, keep verifier coverage on the real runtime
  path
- do not let "generated cleanup" hide a lost proof surface

## What Good Cleanup Looks Like

Good cleanup removes Rally-foreign machinery instead of polishing it.

The important wins are concrete:

- Rally no longer supports `runtime.prompt_input_command`, so old reducer
  scripts have to go away instead of hiding behind a smaller wrapper
- prompt source stops importing special state builders and roles read the ledger
  directly
- shared contracts use one plain ledger input from `home:issue.md` instead of
  asking setup code to rebuild state first
- shared review rules delete typed note protocol baggage and keep one readable
  note shape
- `issue_state.py`, `prompt_inputs.py`, and their tests go away because the
  runtime no longer needs them
- role homes get shorter because they stop carrying a fake workflow engine
- mode gates disappear when they only restate the last note and last turn
  result

That is the Rally move:
remove the mirror runtime, keep the real handoff truth, and prove the live
path that remains.

## Use This With Doctrine

This guide overlaps with the Doctrine repo on purpose, but the ownership split
should stay clean.

Use this guide for:

- workspace shape
- `flow.yaml`
- run-home setup
- `home:issue.md`
- Rally notes and final JSON
- built-in sync
- skill packaging as Rally sees it
- where truth lives during a run

Use the Doctrine guide for:

- language features
- compiler behavior
- imports and inheritance
- workflow law
- typed outputs
- emitted build structure

If a clean port needs a new Doctrine feature, stop and name that Doctrine gap
plainly.
Do not patch around it in Rally.

# The Mental Model

## Port The Model, Not The Cargo

The source repo will usually carry a lot of baggage that belongs to its old
runtime, not to the domain.

A real port shows the difference clearly:

- the job stayed the same
- many contracts stayed the same
- most `SOUL` voice stayed the same
- the runtime shell changed a lot

That is normal.
You should expect the runtime shell to change.

## The Rally Shape

Rally wants one simple front door:

- source prompts live under `flows/<flow>/prompts/**`
- reusable helpers live under `skills/**`
- reusable MCPs live under `mcps/**`
- Rally shared prompt source lives under `stdlib/rally/**`
- runtime truth lives in `flows/<flow>/flow.yaml`
- shared run truth lives in `home:issue.md`
- build output lives under `flows/<flow>/build/**`
- run archaeology lives under `runs/<run-id>/`

If the port tries to keep a second control plane beside those surfaces, stop
and ask why that extra plane exists.

## The Front-Door Host Workflow

Most ports should start from this host-repo loop:

```bash
uv sync --dev
uv run rally run <flow>
uv run pytest -q
```

Then run the smallest real flow proof the host repo can support.

The point of this loop is simple:

- use Rally-managed build and run from the host repo
- let Rally resolve its own stdlib and built-in skills during that path
- prove the host repo as a Rally workspace

# Source To Rally Mapping

| Source shape | Rally home | Example |
| --- | --- | --- |
| family entrypoint | `flows/<flow>/prompts/AGENTS.prompt` as a thin build handle when target mode still needs one | source family entrypoint -> host flow build handle |
| role prompt or generated role home | `flows/<flow>/prompts/agents/<role>/**` plus generated readback in `flows/<flow>/build/**` | old role slug -> Rally role key |
| shared role-home shell | `flows/<flow>/prompts/shared/**` | source role-home shell -> shared contracts owner |
| shared output rules | `flows/<flow>/prompts/shared/**` | source outputs owner -> shared review owner |
| shared capability meaning | `flows/<flow>/prompts/shared/skills.prompt` or reusable `skills/**` | source skill law split into shared skill law plus local skill packages |
| runtime capability config | `flows/<flow>/flow.yaml` | second agent config file -> per-role `allowed_skills` |
| helper skill that really does bootstrap | `flows/<flow>/setup/**` | setup skill -> `prepare_home.sh` |
| recurring reusable procedure | `skills/<skill>/**` | durable reusable procedure stays a skill package |
| current shared run truth | `home:issue.md` plus Rally notes and final JSON | route-only and producer handoff state |
| generated readback | `flows/<flow>/build/**` | emitted role homes |

## Things You Usually Should Not Recreate

Do not recreate these by default:

- `paperclip_home/`
- `agent_configs.json`
- repo-local `doctrine/` trees inside the host workspace
- wrapper-command choreography from the source repo
- second handoff artifacts beside `home:issue.md`
- a second shared brief file beside `home:issue.md`
- role-local command manuals for work that should be a skill
- hand-edited build output under `flows/*/build/**`

# The Port Steps

## 1. Inventory The Real Truth Surfaces

Before you move anything, name the real owners in the source repo:

- role homes
- shared prompt shells
- contract files
- shared outputs
- skill allowlists
- setup and bootstrap logic
- product-truth files
- generated readback
- docs that explain the port direction

Typical key surfaces are:

- source prompt trees
- source role homes
- source agent config files
- source skills
- source docs that explain the old runtime shape

Do not start by copying files blindly.
Start by naming what each file owns.

## 2. Pick The Smallest Honest Rally Owner

For each source behavior, decide which Rally layer owns it now:

- flow-local prompt source
- flow-local setup
- reusable skill
- Rally stdlib
- runtime config
- generated readback only

The rule is simple:
put the behavior in the smallest layer that can honestly own it.

Bad port:

- copy the same command prose into many role homes
- keep source config and new config both live
- leave setup half in a skill and half in a shell script

Good port:

- shared skill meaning in one shared owner
- setup in one flow-local bootstrap owner
- allowlists in one `flow.yaml` owner

## 3. Make `flow.yaml` The Runtime Authority

If the source system had a separate agent config file, move that truth into
`flows/<flow>/flow.yaml`.

This is usually the biggest clean-cut move:

```json
// source agent config
{
  "agents": {
    "lead_role": {
      "desiredSkills": [
        "publish-followthrough",
        "repo-grounding"
      ]
    }
  }
}
```

became:

```yaml
# flows/<flow>/flow.yaml
agents:
  01_lead_role:
    allowed_skills: [publish-followthrough]
    allowed_mcps: []
```

That is not just a rename.
It is a tighter runtime contract.

Port rule:

- keep the allowlist in `flow.yaml`
- keep the prompt prose aligned with that allowlist
- do not keep a second live capability config beside it

## 4. Move Setup Out Of Role Prose

If the source repo used a skill or role-home prose for environment setup,
consider whether Rally should own that in `flows/<flow>/setup/**`.

The common good move is:

- bootstrap moves into `flows/<flow>/setup/prepare_home.sh`
- config staging moves into another flow-local setup step
- host requirements stay in `flows/<flow>/flow.yaml`

Why this is better:

- setup runs before the role starts
- setup becomes one real proof path
- authoring lanes stop carrying setup chatter that is not their real job

Keep a setup skill only when setup is still genuinely part of the agent's live
decision path.

## 5. Collapse Coordination Into `home:issue.md`

Rally already gives you a shared run ledger.
Use it.

Port rule:

- the opening request lives in `home:issue.md`
- Rally notes append there
- the final JSON turn result carries route, done, blocker, or sleep truth
- do not add a second handoff artifact

The clean Rally direction is:

- route truth in final JSON
- readable work truth in issue notes
- named current artifact when one exists

This change shows the pattern well.

Before, the old shape depended on a separate control-plane input:

```text
route_only RouteOnlyTurns
facts: RouteOnlyTurnFacts
handoff_output: RouteOnlyHandoffOutput
```

After, the Rally-native prompt says the agent should use the bounded shared
read path and set the next owner directly:

```text
workflow RouteOnlyTurns: "Lead Role Workflow"
    "Use rally issue current first, then open home:issue.md only when older history matters."
    "If no specialist artifact is current yet, keep the work in `home:issue.md` and say the route in the note."
    "When the route is clear, set the next owner in final JSON directly."
```

That is the right simplification.
Do not force Rally to rebuild a second workflow object when the ledger already
has the truth.

## 6. Keep One Current Artifact Per Lane

This is one of the most important rules in the whole port.

Each lane should leave one main current artifact.
If there is no real artifact yet, say that plainly.

Good examples:

- route-only turn: no specialist artifact is current yet
- intermediate lane: `home:issue.md` is current because the issue-backed
  artifact lives there
- later lane: a real catalog file becomes current

Bad example:

- note, sidecar, packet, scratch file, and output file all look equally live

The shared review rules should keep the stable fields Rally needs:

- `Current Artifact`
- `Invalidations`
- `Use Now`
- `Next Step`
- `Next Owner`

Those fields are the current-truth carrier.
Do not recreate a packet cloud around them.

## 7. Split Big Shared Handbooks Into Small Owners

Source doctrine often has broad handbook buckets.
The port should move toward smaller shared owners:

- read-first rules
- current-work rules
- handoff rules
- review rules
- skill law
- contract files per durable artifact

That split matters because it reduces drift.

Port rule:

- keep shared behavior shared
- do not let each role restate the same law in slightly different words
- do not keep giant generic appendices just because the old system had them

## 8. Prune Skills Hard

Not every source skill deserves to survive the port.

A common pattern is:

- a true follow-through skill stays
- product-grounding skills stay
- an anti-repeat helper might stay only if it still carries real behavior
- a setup skill often moves into flow setup

This is normal.

Ask of each source skill:

1. Is this still a real runtime capability?
2. Is it reusable?
3. Does it own live decision work, or only bootstrap?
4. If it disappears, what behavior are we losing?

Do not cut a skill just because the prose looks cleaner without it.
If the skill carried a real behavior, either replace that behavior or record
the gap plainly.

## 9. Keep Migration History Out Of Runtime Prompts

Runtime prompts should say what is true now.
They should not teach the history of the port.

Put migration commentary in docs like this one.
Put current instructions in prompt source.

That split is what lets the runtime stay small and current while the port guide
stays deep and example-driven.

## 10. Verify The Port At The Right Layers

Use the smallest proof that matches the change.

For a host repo port, that usually means:

1. run the flow through Rally
2. inspect generated readback
3. run host-repo tests
4. run one real smoke flow if the port is runnable

If you need readback before a full run, use Rally's managed build path or a
source-repo readback rebuild that follows the same single-copy rules.

Do not add a sync-first host step for Rally-owned built-ins.

A useful port often has a flow-local render verifier.

That script exists for a reason.
Use proof like that when the port is about rendered doctrine, not just source
text.

# Before / After Examples

## Example 1: Role Home Collapse

The source runtime home might live at:

- `source_home/agents/<role>/AGENTS.md`

The ported authored source lives at:

- `flows/<flow>/prompts/agents/<role>/AGENTS.prompt`

The flow may still keep:

- `flows/<flow>/prompts/AGENTS.prompt` as a thin build handle when Doctrine
  target mode still needs one

The generated readback lives at:

- `flows/<flow>/build/agents/<role>/AGENTS.md`

The key change is not just file location.
The key change is this:

- old shape leaned on issue plan plus comment stack plus extra control-plane
  facts
- Rally shape reads `home:issue.md`, uses readable notes, and sets owner in
  final JSON

## Example 2: Shared Output Rules Get Smaller And Sharper

The old shared output rules might live in:

- `source_prompts/common/outputs.prompt`

The Rally-native version lives in:

- `flows/<flow>/prompts/shared/review.prompt`

The durable change is:

- keep the handoff note readable
- make `Current Artifact` explicit
- make `Invalidations` explicit
- make route-only turns honest about having no specialist artifact

Do not confuse shorter with weaker.
The right question is whether the new note still preserves the real pickup
truth.

## Example 3: Setup Skill Becomes Flow Bootstrap

The source system might have a setup skill:

- `skills/<setup-skill>/SKILL.md`

The port moves that into:

- `flows/<flow>/setup/prepare_home.sh`
- `flows/<flow>/setup/<another-step>.sh`

This is the right move when setup is not the lane's live work.

## Example 4: Capability Truth Moves Into `flow.yaml`

The source system might attach desired skills through:

- `source_home/agents/agent_configs.json`

The Rally port moves that truth into:

- `flows/<flow>/flow.yaml`

That is the authoritative runtime contract.
Prompt prose should support it, not compete with it.

# What To Preserve

Simplification is good.
Flattening real behavior is not.

Preserve these behaviors when they are real:

- route-only turns as honest control turns
- one current artifact per lane
- late metadata follow-up as its own bounded pass
- exact-move proof as distinct from generic validation
- publish follow-through as distinct from "done"
- invalidations when upstream truth makes downstream work stale
- skill-first grounding for repeated procedures

Two real caution cases show up often:

- cutting an anti-repeat helper can remove real anti-repeat behavior
- removing the lead-role recovery path can make the flow read cleaner while
  losing real stuck-work handling

If a cleanup removes real behavior, either replace it or name the loss.

# Common Porting Mistakes

## Mistake: Port The Old Harness Names

Do not keep old names like `source_home`, `agent_configs.json`, or wrapper
command choreography just because they were familiar.

## Mistake: Keep Two Live Config Planes

If `flow.yaml` owns capability truth, do not keep a second live allowlist file.

## Mistake: Overbuild Mode Gates

If the next agent can use `rally issue current` and then open
`home:issue.md` only when older history matters, do not invent a special
`waiting`, `review_mode`, or `active_mode` gate just to tell it what already
happened.

## Mistake: Encode Review Work As Generic Agent Prose

If the lane's main job is review, put the pass-fail logic in `review` or
`review_family`.

Prefer:

- a declared review subject
- a declared review contract
- declared basis checks
- declared `on_accept` and `on_reject` behavior

Avoid:

- a giant critic workflow that re-explains review routing in prose
- lane-by-lane pass-fail logic spread across ordinary agent sections
- review behavior that lives mostly in note instructions instead of review law

## Mistake: Write The Rule As A Ban Instead Of A Move

Prefer:

- `Read the ledger, open the current artifact, and continue the pass.`
- `Leave one readable note with the pickup summary.`

Use a ban only when the line is a real guardrail:

- `Do not add a second handoff artifact.`
- `Do not hand-edit generated readback.`

## Mistake: Repeat Shared Command Prose Locally

If Rally stdlib or a shared skill already teaches a command path, do not copy
that command into every role home.

## Mistake: Hide Current Truth In Supporting Files

Support evidence can exist, but it should not compete with the one current
artifact.

## Mistake: Treat Generated Readback As Authored Truth

Never hand-edit `flows/*/build/**`.
Re-emit from source.

## Mistake: Move Migration Story Into Runtime Prompts

Runtime prompts are for live behavior.
This guide is for enduring port lessons.

# A Small Porting Checklist

Use this before you call a port "done":

1. `flow.yaml` owns the runtime truth.
2. `.prompt` source owns authored instructions.
3. Rally stdlib owns shared Rally command law.
4. Flow-local setup owns bootstrap behavior.
5. Reusable procedures live in skills.
6. `home:issue.md` is the only shared run ledger.
7. Each lane leaves one current artifact or says there is none.
8. Generated readback was re-emitted, not hand-edited.
9. The smallest useful proof ran.
10. Any real behavior loss is either fixed or named plainly.

# How To Keep This Guide Current

When a port teaches us a durable lesson, add it here.

Good additions:

- a repeated bad pattern that showed up in more than one flow
- a clean before/after example that teaches where a behavior belongs
- a real trap where simplification removed useful behavior
- a new proof path that makes ports safer

Bad additions:

- one-turn coaching
- local wording taste
- temporary migration notes
- stale plan history
- ungrounded theory

The rule is simple:
if a lesson should guide the next port, put it here.
If it only mattered for one edit, keep it out.
