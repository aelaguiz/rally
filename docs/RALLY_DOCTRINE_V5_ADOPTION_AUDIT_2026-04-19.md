# Rally Doctrine v5.0 Adoption Audit — 2026-04-19

Plain answer: Rally is already a strong Doctrine user. It uses `abstract agent`,
`review_family`, `skill package`, grouped `inherit`, typed `output schema`,
`route field`, and `schema ... gates:` correctly in most places. But v5.0
broke two patterns Rally still carries, and several review and schema blocks
have quiet duplication that newer Doctrine primitives would remove. The top
two findings are breaking; the rest are craft.

## What changed in Doctrine today

Doctrine shipped v5.0 on 2026-04-19 (CHANGELOG `4.1 -> 5.0`). Five changes
matter for Rally:

1. **Enum-typed field form is canonical.** Field bodies must use
   `type: <EnumName>` backed by a top-level `enum` declaration. The old
   `type: string` + `enum:` form is gone and now raises `E320`. Finding
   `AL950` exists to flag the old shape.
2. **Typed `gates:` block is canonical.** Contract shapes should live in a
   `schema ... gates:` block; reviews reference them with `contract.<GATE>`.
   Finding `AL245` flags inline-prose gate IDs.
3. **Per-gate `accept` lines are canonical.** Review `contract_checks:` should
   name each gate, not collapse to `contract.passes`. Finding `AL450` flags
   that coarse roll-up.
4. **`review_family` + cases** is the first-class way to express N similar
   reviews. Finding `AL270` flags parallel workflows that should collapse.
5. **Forward plan (P2–P7):** per-case `override gates:`, typed handoff
   identity (`typed_as:`), `host_contract:` receipts, skill `mode` binding,
   typed abstract parameters, and declarative cross-agent `rule`s are
   landing over the next release cuts. Rally should author with those shapes
   in mind but not block on them.

Evidence sources:

- `../doctrine/CHANGELOG.md`
- `../doctrine/docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md`
- `../doctrine/docs/AGENTS_MD_RENDER_OF_TYPED_CONTRACTS_2026-04-19.md`
- `../doctrine/docs/LAYERED_AUTHORING_LANGUAGE_GAPS_2026-04-19.md`
- `../doctrine/docs/LAYERED_AUTHORING_EXAMPLE_MISTAKES_2026-04-19.md`
- `../doctrine/docs/AUTHORING_FRICTION_AUDIT_2026-04-18.md`
- `../doctrine/skills/agent-linter/` (45 findings, latest `AL950`)
- `../doctrine/skills/doctrine-learn/` (Phase 8 teaching update)

## Priority tiers

| Tier | Meaning |
|---|---|
| **Ship Now** | Doctrine v5.0 breaks this pattern. Fix before next compile. |
| **Plan For** | Shipped today, clear Doctrine form, improves readback and reuse. |
| **Wait For** | Awaits Doctrine P2–P7. Author with intent, do not block. |

---

## Ship Now (v5.0 breaking)

### F-1 · Stdlib carriers use deprecated `type: string` + `enum:` form · `AL950`

Both Rally-owned shared carriers declare enums inline inside field bodies.
Doctrine v5.0 raises `E320` on this exact shape.

**Evidence:**

- `stdlib/rally/prompts/rally/turn_results/AGENTS.prompt:10-16` — `field kind`
  uses `type: string` + `enum:` for the four values `handoff | done | blocker
  | sleep`.
- `stdlib/rally/prompts/rally/review_results/AGENTS.prompt:9-13` — `field
  verdict` uses `type: string` + `enum:` for `accept | changes_requested`.

**Blast radius:** every flow inherits both schemas. Once Rally bumps Doctrine
past v4.1 the whole repo fails to compile.

**Fix sketch:** declare two top-level enums in the same files and type the
fields against them.

```
enum RallyTurnKind: "Rally Turn Kind"
    handoff: "Hand the turn to the next owner."
    done: "End the flow cleanly."
    blocker: "Stop and report a blocker."
    sleep: "Wait, then wake the same role."

# later, inside BaseRallyTurnResultSchema:
    field kind: "Kind"
        type: RallyTurnKind
        note: "Turn result kind."
```

Do the same for `ReviewVerdict` (`accept`, `changes_requested`). Once these
land, `AL950` will pass across all flows because they already inherit the
fields with `inherit {kind, ...}`.

---

### F-2 · Reviews roll up to `contract.passes` · `AL450`

Every Rally review accepts on the coarse `contract.passes` expression.
v5.0 teaching treats this as hidden prose drift: the emitted review names a
multi-gate contract but the check cannot tell which gate actually blocked.

**Evidence:**

- `flows/software_engineering_demo/prompts/shared/review.prompt:124` — `accept "The architect review contract passes." when contract.passes`
- `flows/software_engineering_demo/prompts/shared/review.prompt:141` — same shape on `DeveloperReview`
- `flows/software_engineering_demo/prompts/shared/review.prompt:158` — same shape on `QaReview`
- `flows/poem_loop/prompts/shared/review.prompt:84` — same shape on `PoemReview`
- `flows/_stdlib_smoke/prompts/AGENTS.prompt:206` — same shape on the smoke review

**Fix sketch:** spell each gate on its own line. Example for `ArchitectReview`:

```
    contract_checks: "Contract Checks"
        accept "The architect named the real issue."     when contract.issue_understood
        accept "The plan uses the real repo and branch." when contract.repo_plan_real
        accept "Developer has one clear next step."      when contract.next_step_clear
```

This unlocks two v5.0 wins: the emitted gate readback gets exact per-gate
copy, and downstream tooling (including the agent-linter) can line up prose
with the typed gate name.

---

## Plan For (shipped today, adoption work)

### F-3 · Poem review uses `workflow` as a contract carrier · `AL245` flavor

Poem review declares its contract as a `workflow`, not as a `schema ...
gates:` block. Doctrine v5.0 teaching makes the schema+gates form canonical
because only it emits typed `contract.<gate>` refs.

**Evidence:**

- `flows/poem_loop/prompts/shared/review.prompt:27-35` — `workflow
  PoemReviewContract` with three step slots (`brief_match`, `rationale_fit`,
  `finish_quality`).

**Fix sketch:** lift the three steps to typed gates.

```
schema PoemReviewContract: "Poem Review Contract"
    sections:
        summary: "Summary"
            "Summarize whether the poem is ready to keep."

    gates:
        brief_match: "Brief Match"
            "Check the poem fits the asked type and subject."
        rationale_fit: "Rationale Fit"
            "Check the poem matches the writer's stated reason."
        finish_quality: "Finish Quality"
            "Accept only when the poem feels finished."
```

Pair this with F-2 so `PoemReview.contract_checks` names each gate.

---

### F-4 · Eight-line `review_fields` block copy-pasted four times · `AL200` / `AL220`

Every reviewer agent redeclares the full `review_fields:` mapping, which is
already named in the `review_family`. The binding is identical across all
four reviewer agents.

**Evidence (all four are byte-identical):**

- `flows/software_engineering_demo/prompts/AGENTS.prompt:183-191` — `ArchitectReviewer.final_output.review_fields`
- `flows/software_engineering_demo/prompts/AGENTS.prompt:224-232` — `DeveloperReviewer.final_output.review_fields`
- `flows/software_engineering_demo/prompts/AGENTS.prompt:265-273` — `QaReviewer.final_output.review_fields`
- `flows/poem_loop/prompts/AGENTS.prompt:211-219` — `PoemCritic.final_output.review_fields`

The same eight-field shape is *also* declared in:

- `flows/software_engineering_demo/prompts/shared/review.prompt:107-115`
  (`EngineeringReviewFamily.fields`)
- `flows/poem_loop/prompts/shared/review.prompt:70-78`
  (`PoemReview.fields`)

**Fix sketch:** push the bindings into one shared Doctrine decl and let
reviewer agents reference it without re-spelling. Two candidate paths:

1. **Best case:** if Doctrine exposes `final_output.review_fields:
   EngineeringReviewFamily` (bind by reference), switch to that. Worth a
   quick read of the v5.0 `review_family` docs to confirm.
2. **If not supported yet:** name the gap in a Doctrine issue (the honest
   Rally move per AGENTS.md). Until then, at minimum lift the eight-line
   block to a single shared decl `EngineeringReviewFields` / `PoemReviewFields`
   (typed shape or named alias) that each agent binds once.

This is the single highest-signal cleanup in the repo.

---

### F-5 · Turn-result schema scaffold duplicated three times · `AL220`

The three work roles (Architect, Developer, QaDocsTester) each declare a
near-identical `output schema ... [BaseRallyTurnResultSchema]` that only
differs in the one `route field next_route:` member.

**Evidence:**

- `flows/software_engineering_demo/prompts/AGENTS.prompt:12-23` — `ArchitectTurnResultSchema`
- `flows/software_engineering_demo/prompts/AGENTS.prompt:43-54` — `DeveloperTurnResultSchema`
- `flows/software_engineering_demo/prompts/AGENTS.prompt:74-85` — `QaDocsTurnResultSchema`

Each is ~12 lines with the same `inherit {...}` footer and the same
`nullable` + `note:` style on the route field.

**Fix sketch (shipped Doctrine):** extract the shared shape once. Only the
route target member truly varies.

```
# One shared schema. Each role schema only adds its route member.
output schema WorkRoleTurnResultSchema[turn_results.BaseRallyTurnResultSchema]:
    inherit {kind, summary, reason, sleep_duration_seconds, agent_issues}
```

Each child schema adds its own `route field next_route:` but keeps the tail
short. If your Doctrine version lets a child add a `route field` after a
parent `inherit`, this collapses most of the duplication.

**Forward (P6):** when typed abstract parameters land, `WorkRoleTurnResult`
becomes one parameterized shape with `route_target: AgentRef` and each
concrete schema binds its target. Note the opportunity in comments and wait.

---

### F-6 · Skills lack `host_contract:` · `AL930`

Three Rally skill packages depend on host env vars and paths but bind them
through prose, not a typed `host_contract:`. v4.1 made `host_contract:` the
canonical slot for skill-host coupling; v5.0 P3 will add typed receipts on
top of it.

**Evidence:**

- `skills/rally-kernel/prompts/SKILL.prompt:20-23` — Bash hard-rule literally
  spells `$RALLY_CLI_BIN`, `$RALLY_RUN_ID`, `$RALLY_WORKSPACE_DIR`.
- `skills/rally-memory/prompts/SKILL.prompt:20-26` — same pattern with
  `$RALLY_CLI_BIN`, `$RALLY_RUN_ID`, `$RALLY_AGENT_SLUG`.
- `skills/demo-git/prompts/SKILL.prompt:7-9` — hard-codes
  `home:repos/demo_repo` in prose.

**Fix sketch:** declare a `host_contract:` on each skill with typed slots the
host binds at install time.

```
skill package RallyKernel: "Rally Kernel"
    host_contract:
        cli_bin: "Path to rally CLI binary."
        run_id: "Active Rally run id."
        workspace_dir: "Active Rally workspace root."
```

Once the code paths use `RallyKernel.cli_bin` etc. in prose instead of
`$RALLY_CLI_BIN`, the compiler enforces that Rally's runtime actually
provides those host values.

---

### F-7 · rally-learn lacks v5.0 finding coverage · `AL110` adjacent

The Rally-owned teaching skill has 14 reference files but none of them
mention v5.0 typed-gate canonical, `AL450`, `AL950`, or the enum-typed field
pattern. A framework user onboarding through `rally-learn` will learn last
release's Doctrine, not current.

**Evidence:**

- `skills/rally-learn/prompts/refs/turn_results_and_routing.prompt:2-5` —
  teaches the verdict contract but not enum-typed verdict fields.
- `skills/rally-learn/prompts/refs/porting_anti_patterns.prompt` — lists
  porting mistakes but no link to the canonical v5.0 review-gate shape.
- `skills/rally-learn/prompts/refs/flow_authoring.prompt:70-95` — teaches
  `abstract agent` and schema inheritance, silent on `review_family` cases
  and typed gates.

**Fix sketch:** one small additive pass across 3–4 refs. Add:

1. A short "Typed gates" row in `authoring_patterns.prompt` pointing at
   `../doctrine/skills/doctrine-learn/prompts/refs/reviews.prompt`.
2. An anti-pattern row in `porting_anti_patterns.prompt` for `contract.passes`
   (point at `AL450`).
3. An anti-pattern row for `type: string` + `enum:` (point at `AL950`).
4. A short "enum-typed fields" example in `turn_results_and_routing.prompt`
   once F-1 lands (so teaching matches stdlib truth).

Don't re-document Doctrine here. Keep rally-learn pointing at canonical
doctrine-learn refs (AGENTS.md principle: "point to it or inherit it").

---

### F-8 · Software-engineering demo has three parallel review contracts · `AL270` flavor

The demo declares three separate `schema ...ReviewContract` blocks with the
same outer shape (one `summary` section plus three gates). Today's Doctrine
cannot express the "same contract, per-case gate delta" shape cleanly (that
is P2). But when P2 ships, these three schemas collapse into one contract
plus three `review_case:` blocks with `override gates:`.

**Evidence:**

- `flows/software_engineering_demo/prompts/shared/review.prompt:28-73` — three
  contract schemas, same structure.

**Fix sketch (today):** leave as-is, but add a short source comment marking
the target shape so the next author seeing P2 ship knows the intent:

```
# TODO(Doctrine P2): collapse into one contract + per-case override gates.
# Waiting on `override gates:` in `review_case`.
```

---

## Wait For (Doctrine P2–P7 forward)

These are durable Rally wins once the Doctrine features land. Note the intent
now; do not block shipping on them.

### F-9 · Typed handoff identity for cross-turn reopen (P4 · `typed_as:`)

Rally's `RallyPreviousTurnOutput` input reopens the prior turn's JSON by
target identity (`output: PoemReviewFinalResponse`). When P4 lands, each
producer output can declare `typed_as: MuseHandoff` and the consumer input
binds a typed field, not a prose "re-read the prior JSON". That will drop
copy-paste field notes in Muse→PoemWriter and Architect→Developer handoffs.

**Evidence:**

- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:18-21` — the shared
  `RallyPreviousTurnOutput` input.
- `flows/poem_loop/prompts/AGENTS.prompt:11-21` — `PreviousMuseTurn` and
  `PreviousPoemReview` repeat the reopen pattern.

### F-10 · Typed skill receipts (P3 · `host_contract:` receipt family)

`rally-memory` and `rally-kernel` return observable state (saved note id,
memory id). Right now that state is prose. P3 adds typed `receipt` on
`host_contract:`, so calls like `RallyMemory.save` can return
`RallyMemory.receipt.saved_id` that downstream agents consume typed.

### F-11 · Skill mode binding (P5 · `mode` on skill binding)

`rally-memory` has four modes (`search`, `use`, `save`, `refresh`). Today
they are taught as prose bullets in `SKILL.prompt:33-38`. When P5 ships,
authors bind the mode through a typed enum slot, the audit agent-linter
validates valid mode combos, and compile errors catch wrong mode wiring.

### F-12 · Typed abstract parameters for N-role flows (P6)

The three work-role turn-result schemas (F-5), the three reviewer agents
(SED), and the three review contracts (F-8) all look like the "one abstract
shape, N typed concretes" pattern P6 is built for. When P6 ships, one
parameterized `abstract output schema WorkRoleTurnResult[route_target:
AgentRef]` replaces three near-identical children.

### F-13 · Declarative cross-agent rules (P7 · `rule` primitive)

Rally invariants ("every managed agent inherits `RallyManagedBaseAgent`",
"every reviewer agent ships `review_fields:`") are framework truth that
today rides on prose in `AGENTS.md` and stdlib comments. P7's `rule` with
scope + assertion is the typed home for those invariants. Worth a follow-up
doc (`RALLY_DOCTRINE_RULES.md`) once P7 ships.

---

## Suggested landing order

1. **F-1** (enum-typed stdlib carriers) — unblocks the Doctrine floor bump.
2. **F-2** (per-gate accepts) — same PR as F-1; both touch shared reviews.
3. **F-3** (poem_loop schema+gates) — matches F-2 shape across flows.
4. **F-7** (rally-learn v5.0 refresh) — teach what stdlib now does.
5. **F-4** (shared review_fields decl) — biggest DRY win; check Doctrine
   support first, file a gap note if missing.
6. **F-5** (shared work-role turn-result schema) — medium DRY win.
7. **F-6** (skill `host_contract:`) — can ship standalone, unlocks P3 later.
8. **F-8** leave with comment until P2 ships.
9. **F-9 – F-13** — track as durable notes; revisit as Doctrine phases ship.

## Non-findings worth naming

Things I looked for and did not find:

- **No AL100 oversized role homes.** Every concrete agent fits on one screen.
- **No AL280 skeleton duplication.** Both flows hoist shared shape into
  `abstract agent RallyManagedBaseAgent` correctly.
- **No AL140 planning-doc scaffolding in roles.** Sequences live in dedicated
  workflow blocks, not agent bodies.
- **No AL510 missing handoff artifact.** Every producer turn wires its final
  output through a typed `route field` on the schema.
- **No AL320 host-namespace jargon.** stdlib uses plain English.
- **No AL700 reading-level drift.** stdlib and flow prompts stay at target.

Rally is, on balance, an exemplary Doctrine user. The findings above turn a
"very good" implementation into a v5.0 exemplar.

---

## Closure Status — 2026-04-19

Ship Now / Plan For findings (F-1 through F-8) landed in the Doctrine v5
exemplar adoption PR on branch `feat/doctrine_v5_adoption_on_perf`. Forward
findings (F-9 through F-13) left as typed comment markers at the P2–P7
landing sites, tracked as `# TODO(doctrine ...)` comments in Rally source.

| Finding | Status | Landed / marker site |
|---|---|---|
| F-1 · Enum lift in stdlib (`AL950`) | Landed | `stdlib/rally/prompts/rally/turn_results/AGENTS.prompt` (`RallyTurnKind`), `stdlib/rally/prompts/rally/review_results/AGENTS.prompt` (`ReviewVerdict`). |
| F-2 · Per-gate review rejects (`AL450`) | Landed | `flows/software_engineering_demo/prompts/shared/review.prompt` + `flows/poem_loop/prompts/shared/review.prompt`. Per-gate rejects across every gate plus final `accept "..." when contract.passes`. |
| F-3 · Poem `workflow` → `schema ... gates:` (`AL245`) | Landed | `flows/poem_loop/prompts/shared/review.prompt:PoemReviewContract`. Added `sections:` + `gates:` blocks. Signals added in `flows/poem_loop/prompts/shared/inputs.prompt:PoemDraftFile`. |
| F-4 · `review_fields` shorthand (`AL200` / `AL220`) | Landed (Doctrine gap named) | `review_family.fields:` in both shared review prompts. Doctrine v5 has no `final_output.review_fields: <SharedDecl>` binding, so each reviewer agent restates the shorthand. Propagation comment added at both families. |
| F-5 · Shared work-role turn-result schema (`AL220`) | Landed | `flows/software_engineering_demo/prompts/shared/turn_results.prompt:WorkRoleTurnResultSchema`. Three role schemas inherit the shared parent. |
| F-6 · `host_contract:` on skills (`AL930`) | Landed as forward markers | `skills/rally-kernel/prompts/SKILL.prompt`, `skills/rally-memory/prompts/SKILL.prompt`, `skills/demo-git/prompts/SKILL.prompt` carry `# TODO(doctrine F-6):` comments. Doctrine v5.0 only accepts the typed host_contract slot family (input/output/document/analysis/schema/table/final_output/receipt); env-var/scalar facts wait on a future slot family. |
| F-7 · rally-learn v5 refresh (`AL110` adjacent) | Landed | `skills/rally-learn/prompts/refs/turn_results_and_routing.prompt` (enum-typed section + cross-link), `authoring_patterns.prompt` (typed-gates row), `porting_anti_patterns.prompt` (AL450 + AL950 rows). |
| F-8 · Parallel review contracts (`AL270`) | Landed | Three engineering review contracts share one `EngineeringReviewFamily` with the shared `review_fields:` shorthand; per-gate signals live on the flow-local `IssueLedger`. |
| F-9 · `typed_as:` handoff identity (P4) | Marker | `flows/poem_loop/prompts/shared/contracts.prompt:PoemLoopSystemContext` (P3 prose lift marker stands in; typed-handoff marker continues to track the forward plan). |
| F-10 · `host_contract:` receipt family (P3) | Marker | Three skills carry `# TODO(doctrine F-6):` — same marker covers receipt family adoption. |
| F-11 · Skill `mode` binding (P5) | Marker | `flows/software_engineering_demo/prompts/AGENTS.prompt:RepoWorkSkills`. |
| F-12 · Typed abstract parameters (P6) | Marker | `flows/software_engineering_demo/prompts/AGENTS.prompt:SoftwareEngineeringRole` + `flows/poem_loop/prompts/AGENTS.prompt:PoemLoopRole`. |
| F-13 · Declarative cross-agent `rule` (P7) | Marker | `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:RallyManagedSharedRules`. |

**Compile evidence.** `make emit` clean across all three flows, five skill
targets. `uv run pytest tests/unit -q` → 530 passed, 8 subtests passed.
`uv lock` clean.

**Pin note.** Doctrine is still published at v4.0.1; the v5 canonical forms
used here live on the editable `../doctrine` install. Rally's
`pyproject.toml` pin stays at `doctrine-agents>=4.0.0,<5` until Doctrine
cuts a v5.0.0 release. The editable install satisfies the pin for local
development.
