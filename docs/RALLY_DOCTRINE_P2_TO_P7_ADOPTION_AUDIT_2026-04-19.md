---
title: "Rally - Doctrine P2-P7 Closure Feature Adoption Audit - Architecture Plan"
date: 2026-04-19
status: active
fallback_policy: forbidden
owners: [amir]
reviewers: []
doc_type: architectural_change
related:
  # Live Doctrine fold-forward surfaces (post-closure-plan retirement 2026-04-20)
  - ../../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../../doctrine/docs/COMPILER_ERRORS.md
  - ../../doctrine/CHANGELOG.md
  - ../../doctrine/examples/140_typed_gates_symbol_reference
  - ../../doctrine/examples/141_review_case_gate_override
  - ../../doctrine/examples/142_skill_host_receipt_envelope
  - ../../doctrine/examples/143_typed_handoff_note_identity
  - ../../doctrine/examples/144_skill_binding_producer_audit_mode
  - ../../doctrine/examples/145_abstract_agent_typed_parameters
  - ../../doctrine/examples/146_declarative_project_lint_rule
  # Retired Doctrine anchor docs preserved in git only (Doctrine commits 8c3701a, 76011f2)
  - "git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md"
  - "git:../../doctrine@d629ded:docs/SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md"
  # Rally adjacent docs
  - ./RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md
  - ./RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md
---

# TL;DR

**Outcome.** Every Rally `# TODO(doctrine …)` marker reflects current Doctrine truth. Every TODO whose Doctrine-side phase has now shipped is either converted to the real syntax or retired with a dated Decision Log entry that names why the shipped shape does not fit the Rally site. Every TODO whose Doctrine-side blocker is still unshipped uses current Doctrine phase vocabulary (P2-P7) and names the specific unshipped piece. No surviving TODO claims to wait on a feature marked `Status: COMPLETE` in the Doctrine closure plan.

**Problem.** The Doctrine closure plan shipped **all** of Phases 2-7 between 2026-04-19 and 2026-04-20. That includes Phase 6 (typed abstract-agent parameters, E538/E539, example 145) and Phase 7 (declarative `rule` primitive with closed scope + assertion predicate sets, RULE001-RULE005, example 146), both of which Rally's outstanding TODOs assumed were still blocked. Rally's in-tree `TODO(doctrine …)` comments use Rally-local phase numbers (P2 / P3 / P5 / P6 / P7) written before the Doctrine phase split-and-ship, so the numbering is desynced and several TODOs imagine adoption shapes that do not match what actually landed (for example, Rally's P7 TODO wants runtime-turn rules, but Doctrine's `rule` primitive is compile-time-only for inheritance and binding invariants). Left alone, the markers rot into lies.

**Approach.** Audit-and-adopt pass, not a restructure. For each TODO site: compare the Rally-side vocabulary to the Doctrine-side phase that actually shipped, read the shipped grammar and model, then render one verdict per site — adopt, retire with Decision Log, or keep-blocked. Stay on `feat/doctrine_v5_adoption_on_perf`; no git ceremony; zero `../doctrine/` edits.

**Plan.** Seven coherent phases: (1) pin Doctrine ground truth for P2-P7 by reading shipped grammar, model, examples 140-146; (2) render per-site verdicts into Sections 5 and 6 of this plan; (3) adopt Doctrine P4 `typed_as:` where the shape fits; (4) adopt Doctrine P5 skill-binding `mode:` where the shape fits; (5) audit Doctrine P6 typed abstract parameters against Rally's shared-binding pattern; (6) audit Doctrine P7 `rule` primitive against Rally's runtime-rule prose; (7) retire or rewrite TODOs whose shipped feature does not fit, renumber still-blocked TODOs to current Doctrine vocabulary, refresh the two related Rally adoption docs.

**Non-negotiables.**
- Every `.prompt` edit round-trips through the Doctrine compiler before its phase claims completion.
- Zero edits under `../doctrine/`. If adoption requires a Doctrine change, stop and name the gap.
- Rally TODO numbering, wherever it survives, uses the **current** Doctrine phase names (P2 override gates, P3 receipt, P4 typed_as, P5 skill mode, P6 typed abstract params, P7 rule), never Rally-local pre-split numbers.
- No git operations. This plan is executed locally on the current branch.
- No scope drift into a Rally-wide sweep for "places where the new Doctrine features would fit". The unit of work is existing TODO markers, not desires.
- No prose-only replacement. If a TODO is retired, a dated Decision Log entry carries the rationale so the TODO does not re-appear in a later well-intentioned sweep.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
research_pass_1: done 2026-04-20
deep_dive_pass_1: done 2026-04-20
recommended_flow: research -> deep dive -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-20 (refreshed, pass 2)
Verdict (code): COMPLETE
Manual QA: n/a (non-blocking)

## Audit posture
Fresh re-audit against the full approved ordered plan frontier (Phases 1-7 as canonically authored — checklists and exit criteria taken from the plan, not from any narrower execution-side rewrite). Every falsifiable anchor verified directly against the tree:
- `rg 'TODO\(doctrine' flows stdlib skills` → 0 matches.
- `uv run pytest tests/unit -q` → 530 passed, 8 subtests passed.
- V5 adoption audit line 38 now reads `git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md (retired 2026-04-20 via Doctrine commit 8c3701a; fold-forward canonical surfaces are ...)` — the `git:` anchor the prior audit required.
- V5 adoption audit Closure Status rows F-9..F-13 (lines 420-424) show `Retired 2026-04-20` with grammar/model/validator/example anchors; lines 403-408 are past-tense historical with a 2026-04-20 Update block.
- V5 exemplar plan TL;DR at line 32 describes Phase 8's forward-marker outcome as fully retired by this plan; remaining `TODO(doctrine …)` mentions at lines 856 / 1057 sit inside the plan's own historical Phase 8 / Decision Log prose, which is authentic narration of that plan's write-time state, not a live claim against the current tree.
- This plan's own `related:` frontmatter (lines 22-23), §3.1 historical anchors (lines 264-265), and §2.1 prose (line 201) all cite retired Doctrine docs via `git:` anchors.

No execution-side weakening of requirements, scope, acceptance criteria, or phase obligations was found. The verdict table in §5.3 and the change map in §6.1 describe exactly the tree's current state.

## Code blockers (why code is not done)
- None.

## Reopened phases (false-complete fixes)
- None. Phase 7 — previously reopened for `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md:38` lacking a `git:` anchor on the retired Doctrine closure-plan doc — is now resolved in the tree and flips back to COMPLETE. The audit trail below records the history.

## Full-frontier sweep (Phase 1 → Phase 7, all checklists + exit criteria)
- **Phase 1 (Pin Doctrine ground truth):** COMPLETE. §3.3 G-gates resolved; §5.3 verdict table anchored; §6.1 change map complete; all anchors grounded in grammar + model + validator + example per research-reads-source rule.
- **Phase 2 (P2 override-gates retire, two sites):** COMPLETE. Both TODO blocks absent from tree (`review.prompt:69` and `review.prompt:122` no longer carry TODOs). §10 entry "Retire both P2 override-gates TODOs" anchored on `doctrine.lark:235-248` + E531/E532 + example 141.
- **Phase 3 (P4 typed_as retire):** COMPLETE. `poem_loop/shared/contracts.prompt` TODO absent. §10 entry anchored on `doctrine.lark:748-751` + `_model/io.py:246-252` + example 143.
- **Phase 4 (P5 skill-mode retire):** COMPLETE. `software_engineering_demo/AGENTS.prompt:107` TODO absent. §10 entry anchored on `doctrine.lark:706-713` + `_model/workflow.py:57-63` + example 144 + SkillMode enum + orthogonality-to-`requirement:` rationale.
- **Phase 5 (P6 typed-abstract-parameter retire, two sites):** COMPLETE. Both `AGENTS.prompt:146` / `AGENTS.prompt:153` TODOs absent. §10 entry anchored on `doctrine.lark:168` + `_model/agent.py:21-24` + example 145 (`TypedPolicyReviewer`).
- **Phase 6 (P7 rule-primitive retire):** COMPLETE. `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` TODO absent. §10 entry anchored on `doctrine.lark:86-104` + RULE001-RULE005 + example 146.
- **Phase 7 (three skill TODOs + adjacent-doc refresh + stale-anchor prose):** COMPLETE. All three skill TODOs deleted; both adjacent Rally docs refreshed to post-adoption tree; this plan's TL;DR / §1.4 / §2.1 / §10 prose repaired with `git:` anchors for retired Doctrine docs; V5 adoption audit line 38 carries the required `git:` anchor; V5 adoption audit Closure Status rows F-9..F-13 all read `Retired 2026-04-20` with grammar/model/validator/example anchors.
- **§0.4 acceptance evidence (all five items):** satisfied.
  - `rg 'TODO\(doctrine' flows stdlib skills` → 0 matches.
  - `uv run pytest tests/unit -q` → 530 passed.
  - Both adjacent Rally docs align with post-adoption tree with no live reference to retired Doctrine docs missing a `git:` anchor.
  - §10 Decision Log carries one dated entry per retired TODO, each anchored per research-reads-source rule.
  - Per-phase checklist items and exit criteria all met; no phase remains reopened.

## Historical audit trail (for traceability; previously reopened, now resolved)
- Prior gap: `RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` lines 404-406 present-tense prose about F-9..F-13 as live `# TODO(doctrine ...)` markers. **Resolved** — prose rewritten as past-tense historical ("were originally left as typed comment markers") with a 2026-04-20 Update block at line 408 describing the post-adoption tree.
- Prior gap: Same doc Closure Status rows F-9 / F-10 / F-11 / F-12 / F-13 reading `Status: Marker` with marker-site cells. **Resolved** — rows (lines 420-424) all show `Retired 2026-04-20` with grounded retirement prose pointing at §10 entries in this plan.
- Prior gap (this audit pass's entry gap): `RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md:38` citing the retired Doctrine closure plan without a `git:` anchor. **Resolved** — line 38 now reads `git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md` with a parenthetical pointing at the fold-forward destinations (`LANGUAGE_REFERENCE.md`, `COMPILER_ERRORS.md`, `examples/140-146`), matching the form used in this plan's `related:` frontmatter and §3.1.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- None.

## Next action
- Clean verdict. Hand off remaining docs cleanup and plan/worklog retirement to `$arch-docs`.
<!-- arch_skill:block:implementation_audit:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

After this plan lands, `rg 'TODO\(doctrine' flows stdlib skills` returns zero matches. Every prior Rally `TODO(doctrine …)` marker is either converted into real Doctrine syntax (and thus no longer exists as a comment) or retired with a dated Decision Log entry explaining why the shipped Doctrine feature did not fit the Rally site. No surviving `TODO(doctrine …)` comment remains in the tree.

## 0.2 In scope

**Requested behavior scope.**
Audit and resolve the following Rally TODO sites against shipped Doctrine closure-plan phases P2-P7 (all shipped between 2026-04-19 and 2026-04-20):

- `flows/poem_loop/prompts/shared/review.prompt:69` — `TODO(doctrine P2)` override gates on review_case (Doctrine P2 SHIPPED 2026-04-19)
- `flows/software_engineering_demo/prompts/shared/review.prompt:122` — `TODO(doctrine P2)` override gates on review_case (Doctrine P2 SHIPPED 2026-04-19)
- `flows/poem_loop/prompts/shared/contracts.prompt:1` — `TODO(doctrine P3)` typed_as for prose bullets (Doctrine P4 SHIPPED 2026-04-20)
- `flows/software_engineering_demo/prompts/AGENTS.prompt:107` — `TODO(doctrine P6)` skill mode binding (Doctrine P5 SHIPPED 2026-04-19)
- `flows/software_engineering_demo/prompts/AGENTS.prompt:146` — `TODO(doctrine P5)` typed abstract parameters (Doctrine P6 SHIPPED 2026-04-20)
- `flows/poem_loop/prompts/AGENTS.prompt:153` — `TODO(doctrine P5)` typed abstract parameters (Doctrine P6 SHIPPED 2026-04-20)
- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` — `TODO(doctrine P7)` rule primitive (Doctrine P7 SHIPPED 2026-04-20)
- `skills/demo-git/prompts/SKILL.prompt:10`, `skills/rally-kernel/prompts/SKILL.prompt:18`, `skills/rally-memory/prompts/SKILL.prompt:20` — three previously-"forward-marker" TODOs that pointed at an unshipped Doctrine host-slot concept. Rally no longer carries forward markers for unshipped Doctrine features: the concept was filed on the Doctrine side as a request-and-retire commit pair (`git:../../doctrine@d629ded:docs/SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md`, deleted same-day in commit `76011f2`). These three TODO comments are deleted here.

Resolve each site to one of: adopt or retire with Decision Log. No TODO survives this plan.

**Architectural convergence scope (allowed).**
- Ordinary prompt edits inside touched files: removing the obsolete TODO block, replacing it with real Doctrine syntax, or rewriting its wording and phase number.
- Renumbering still-blocked TODOs so they use current Doctrine phase vocabulary (not Rally-local pre-split numbers).
- Touching the owning flow's compiled readback under `flows/*/build/**` as a proof step after `.prompt` edits.
- Updating cross-reference mentions of the touched TODOs in `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` and `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md`.

## 0.3 Out of scope

- Any edit to `../doctrine/` grammar, model, compiler, examples, or curated skills. The Doctrine-side feature request doc under `../doctrine/docs/` is an explicit exception — it is written, not edited here, and is listed in `related:` frontmatter for traceability.
- A Rally-wide sweep for "places where the new Doctrine features would fit." The unit of work is existing TODO markers, not a tree-wide search for adoption candidates.
- Restructuring `flows/software_engineering_demo` reviews into one shared contract with per-case gate overrides. The three review roles have genuinely different gates; forcing them through one contract is a regression.
- Restructuring the poem_loop and software_engineering_demo abstract agents to move shared slot bindings (`system_context`, `ground_truth`/`issue_truth`, `primary_path`/`repo_rules`) down to each concrete agent so the abstract can declare typed abstract slots. Every concrete in both flows binds the **same** value today; typed-abstract-slot restructuring would be pure ceremony.
- Re-authoring Rally's runtime-turn rules (`RallyManagedSharedRules` prose bullets) as Doctrine `rule` declarations. Doctrine P7's `rule` primitive is compile-time-only for inheritance and binding invariants (`requires inherit`, `forbids bind`, `requires declare`); it does not carry runtime turn instructions.
- Introducing a new Rally primitive, shared skill, stdlib module, or CLI command.
- Git operations (commits, branches, pushes, PRs). This plan runs locally on `feat/doctrine_v5_adoption_on_perf`.
- Dependency upgrades, `uv.lock` edits, CI config changes.
- Renaming any other file, moving any module, or reshaping any compiled readback layout.

## 0.4 Definition of done (acceptance evidence)

- `rg 'TODO\(doctrine' flows stdlib skills` returns zero matches. Every pre-existing TODO was either converted to real Doctrine syntax (and removed as a comment) or retired with a dated Decision Log entry.
- Every prompt file touched by this plan recompiles via the Rally-paired Doctrine compiler, and the generated readback under `flows/*/build/**` reflects the edit without hand-patching.
- `uv run pytest tests/unit -q` at the Rally repo root passes after every phase.
- `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` and `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` no longer contain TODO-state claims that contradict the tree after adoption (e.g., listing `F-10 · receipt family` as a forward marker when the receipt family has shipped and the Rally site was retired). Any forward-finding in those docs that referenced the scalar / env-var / path host-slot concept is retired with a pointer to the Doctrine-side feature request.
- Decision Log (Section 10) carries one dated entry per retired TODO explaining why the shipped Doctrine feature did not fit the Rally site.
- Phase checklist items and exit criteria are satisfied for every completed phase; any reopened phase is honestly marked.

## 0.5 Key invariants (fix immediately if violated)

- **One phase vocabulary.** Rally comments and Rally docs use Doctrine's current closure-plan phase numbers (P2 override gates, P3 receipt, P4 typed_as, P5 skill mode, P6 typed abstract params, P7 rule). No silent retention of Rally-local pre-split numbering.
- **No fallback or bridge syntax.** Doctrine adoption is either real or retired, not half-landed via a second form.
- **No new parallel paths in prompt source.** Converting a TODO into real syntax must not leave the prose version next to it.
- **No silent behavior change in flow runtime.** Prompt edits that convert a TODO to real syntax must leave compiled readback functionally equivalent (same instruction semantics, same output shape, same review gates). The change is in form, not meaning, unless a Decision Log entry records an explicit behavior tweak.
- **Research and deep-dive read Doctrine source, not just the closure plan.** Every P2-P7 verdict must be grounded in the shipped Doctrine grammar (`../doctrine/grammars/doctrine.lark`), the shipped model dataclasses under `../doctrine/_model/`, the validator wiring, and the working examples 140-146 under `../doctrine/examples/`. Reading only `DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md` is not enough — the closure plan describes intent; the code describes what actually shipped. If the doc and the code disagree, the code wins, and the disagreement gets a §3 note plus a §10 Decision Log entry. Reading only (no edits to `../doctrine/`) — see the "No Doctrine-side work" rule below.
- **No Doctrine-side work.** If Rally is blocked on Doctrine, stop and name the gap plainly.
- **No git ceremony.** This plan does not commit, push, open PRs, or modify branch state.

---

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Truthfulness of in-tree TODO markers — the single most important guarantee this plan makes.
2. Rally still compiles and its tests still pass after every phase.
3. Any converted syntax is plainly readable by a future Rally contributor meeting `.prompt` files for the first time.
4. Adjacent docs (`RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md`, `RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md`) stay consistent with the post-adoption tree.

## 1.2 Constraints

- No Doctrine edits.
- No git state changes.
- Must use Doctrine features exactly as they shipped (no workaround syntax, no speculative extensions).
- Every `.prompt` change must recompile via the standard Rally build surface before the phase claims done.

## 1.3 Architectural principles (rules we will enforce)

- **One phase vocabulary.** Rally comments, Rally docs, and Doctrine docs use the same phase numbers.
- **Verdict per site, not per feature.** Each TODO comment is audited independently. "Doctrine shipped feature X" does not mean "adopt X everywhere".
- **Adopt where the shape fits; retire where it doesn't; stay blocked where the feature hasn't landed.**
- **Shape-fit over feature-availability.** A shipped Doctrine feature that does not fit the Rally site is a retire, not an adopt, even if "the feature finally landed" reads like a win.
- **No instruction laundering.** If a TODO is being retired, its removal justification lives in the Decision Log, not in added prose elsewhere.
- **Doctrine-first.** If the plan discovers a Doctrine gap, stop and name it — do not work around it in Rally.

## 1.4 Known tradeoffs (explicit)

- Doctrine shipped a lot of new surface in a short window. This plan intentionally leans into retirement of TODOs rather than aggressive adoption. Readers who expect "P2-P7 shipped, so Rally should adopt P2-P7" will find the plan under-adopts; that is by design. Shape-fit per site trumps feature availability.
- Retiring a TODO that pointed at a shipped feature can read like backsliding. The Decision Log has to carry the reasoning so later readers don't re-add the TODO.
- Rally previously carried three TODOs pointing at an unshipped Doctrine host-slot concept (scalar / env-var / path). This plan deletes those TODOs. The concept was filed on the Doctrine side as `SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md` (Doctrine commit `d629ded`) and retired same-day in commit `76011f2`; the request is reachable only via git (`git:../../doctrine@d629ded:docs/SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md`). Current v5 `host_contract:` slot families remain `{input / output / document / analysis / schema / table / final_output / receipt}`. Tradeoff: Rally loses the in-tree reminder of the three sites that wanted the scalar/env-var/path family. Accepted because (a) the retired Doctrine request still names the three Rally sites in git history, and (b) carrying forward markers for unshipped features in Rally has proven to drift into inaccurate vocabulary faster than it earns its keep.

---

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

- Doctrine's closure plan shipped **Phases 2 through 7** between 2026-04-19 and 2026-04-20. The closure-plan doc itself was retired on 2026-04-20 (Doctrine commit `8c3701a`) after all phases shipped and their durable truth folded forward to `LANGUAGE_REFERENCE.md` / `COMPILER_ERRORS.md` / `examples/140-146`; the phase status lines below reference the retired doc via its pre-retirement tree (`git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md`):
  - Phase 2 (`override gates:` on `review_case`, E531/E532) — COMPLETE 2026-04-19
  - Phase 3 (`receipt` family on `host_contract:`, E535/E536/E537) — COMPLETE 2026-04-20
  - Phase 4 (`typed_as:` on output targets, E533/E534) — COMPLETE 2026-04-20
  - Phase 5 (skill-binding `mode:` + output-shape selector drift, E543) — COMPLETE 2026-04-19
  - Phase 6 (typed abstract-agent parameters `abstract NAME: TypeRef`, E538/E539, example 145) — **COMPLETE 2026-04-20 (today)**
  - Phase 7 (declarative `rule` primitive with closed scope/assertion predicate sets, RULE001-RULE005, example 146) — **COMPLETE 2026-04-20 (today)**
- Rally carries 10 `TODO(doctrine …)` markers written before the closure-plan split and before any of those phases shipped. Sites:
  - `flows/poem_loop/prompts/shared/review.prompt:69` — `TODO(doctrine P2)` override gates
  - `flows/software_engineering_demo/prompts/shared/review.prompt:122` — `TODO(doctrine P2)` override gates
  - `flows/poem_loop/prompts/shared/contracts.prompt:1` — `TODO(doctrine P3)` typed_as for workflow prose bullets
  - `flows/software_engineering_demo/prompts/AGENTS.prompt:107` — `TODO(doctrine P6)` skill-entry mode binding
  - `flows/software_engineering_demo/prompts/AGENTS.prompt:146` — `TODO(doctrine P5)` typed abstract parameters
  - `flows/poem_loop/prompts/AGENTS.prompt:153` — `TODO(doctrine P5)` typed abstract parameters
  - `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` — `TODO(doctrine P7)` rule primitive
  - `skills/demo-git/prompts/SKILL.prompt:10`, `skills/rally-kernel/prompts/SKILL.prompt:18`, `skills/rally-memory/prompts/SKILL.prompt:20` — three TODOs pointing at an unshipped Doctrine host-slot concept that was never in the closure plan. The concept has been filed as a Doctrine-side feature request and these three comments are deleted here.

## 2.2 What's broken / missing (concrete)

**Desynced phase numbering.** Rally's TODO numbering was written against an earlier bundling of Doctrine phases. The current mapping:

| Rally TODO says | Doctrine phase today | Doctrine status |
|-----------------|----------------------|-----------------|
| P2 (override gates) | P2 | SHIPPED 2026-04-19 |
| P3 (typed_as) | P4 | SHIPPED 2026-04-20 |
| P5 (typed abstract params) | P6 | SHIPPED 2026-04-20 |
| P6 (skill mode) | P5 | SHIPPED 2026-04-19 |
| P7 (rule primitive) | P7 | SHIPPED 2026-04-20 |

A contributor grepping `TODO(doctrine P2)` in Rally expects it to align with Doctrine P2 — and that one does — but `TODO(doctrine P3)` in Rally points at `typed_as:`, which is Doctrine P4 today. The mismatch is silent and confusing.

**Shape-fit gaps.** Several TODOs imagined an adoption shape that does not match what actually shipped:

- `poem_loop/shared/review.prompt` has a single `PoemReview` with one gate set. Doctrine P2 `override gates:` narrows one gate's copy per case in a **multi-case** review_family. There is nothing to narrow.
- `software_engineering_demo/shared/review.prompt` has three separate reviews (`ArchitectReview`, `DeveloperReview`, `QaReview`) with **genuinely different** gate sets (issue_understood / requested_change_present / requirements_met per role). Collapsing them into one shared contract with per-case gate overrides buries real semantic difference.
- `poem_loop/shared/contracts.prompt` flags `typed_as:` for plain prose bullets under a workflow. Doctrine P4's `typed_as:` attaches a typed identity to `output_target_decl`, not to workflow prose. Workflow prose has no typed handoff to attach.
- `software_engineering_demo/AGENTS.prompt:107` flags skill-entry `mode:` as if it replaces Rally's `requirement: Required | Advisory`. Doctrine P5's `mode:` shipped as a separate selector governing call pattern (producer vs audit vs readonly, TBC in research); Rally's `requirement:` governs must-use vs may-use. The two concepts are orthogonal. The TODO's "replace `requirement:` with `mode:`" framing conflates them.
- `poem_loop/AGENTS.prompt:153` and `software_engineering_demo/AGENTS.prompt:146` both flag typed abstract parameters. But in both flows, **every** concrete descendant binds the **same** value for `system_context` / `ground_truth` (or `issue_truth`) / `primary_path` (or `repo_rules`). Typed abstract parameters are for cases where descendants need **different** typed bindings. Restructuring to add type annotations while all descendants still bind the same three values is ceremony without benefit.
- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` flags the `rule` primitive for lifting `RallyManagedSharedRules` prose bullets. But Doctrine P7 shipped as a compile-time enforcement primitive for **inheritance and binding invariants** (`requires inherit`, `forbids bind`, `requires declare`). Rally's shared rules are **runtime turn instructions** ("use `home:issue.md` as the shared ledger", "end the turn with the final JSON this turn declares"). They are not structural invariants a compiler can check.
- Three skill-site TODOs (`skills/demo-git`, `skills/rally-kernel`, `skills/rally-memory`) pointed at an unshipped Doctrine host-slot concept (scalar / env-var / path facts that the host runtime supplies at install time). That concept was never in the closure plan and has no Doctrine-side home. Left in Rally as "forward markers," they drift into stale vocabulary — they already use naming that does not match any shipped or planned Doctrine phase.

## 2.3 Constraints implied by the problem

- Adoption decisions have to be per-site. One-size-fits-all answers make the problem worse.
- Any conversion must stay compiler-clean on the current paired Doctrine.
- Any retired TODO must leave behind a Decision Log entry so the TODO does not re-appear in a later well-intentioned sweep.
- The plan's honest shape is **mostly retirement, with a small amount of potential adoption** (primarily the skill-binding `mode:` question, pending research). Readers expecting a broad feature-rollout should be warned in the TL;DR and in Section 1's tradeoff list.

---

# 3) Research Grounding (external + internal "ground truth")

<!-- arch_skill:block:research_grounding:start -->

_Research pass 1 completed 2026-04-20. Every P2-P7 verdict is grounded in shipped Doctrine source (grammar, model, validator, examples), not in closure-plan prose. The 2026-04-19 closure plan doc was retired 2026-04-20 in Doctrine commit `8c3701a` ("docs: retire closure plan + feeder audits after durable-truth fold-forward") after all P1-P7 features shipped and their durable truth folded forward to `LANGUAGE_REFERENCE.md`, `COMPILER_ERRORS.md`, `CHANGELOG.md`, `examples/140-146`, and curated `doctrine-learn` + `agent-linter` skill references. The short-lived `SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md` (added in `d629ded`, deleted same-day in `76011f2`) is also gone. Both retired docs are reachable only via git history; live Doctrine truth is code + fold-forward docs._

## 3.1 External anchors (papers, systems, prior art)

- `../doctrine/docs/LANGUAGE_REFERENCE.md` — **adopt**: live Doctrine language reference; the fold-forward destination for P2-P7 grammar. Use for authoring-surface look-ups when a TODO is converted to real syntax.
- `../doctrine/docs/COMPILER_ERRORS.md` — **adopt**: canonical diagnostic catalog. Confirms E531/E532 (P2), E533/E534 (P4), E535/E536/E537 (P3), E540-E543 (P5, E543 fatal on enum-only selector), E538/E539 (P6), RULE001-RULE005 (P7), plus the `RULE006-RULE099` closed-predicate reservation and `RULE100+` open-expression reservation.
- `../doctrine/examples/140_typed_gates_symbol_reference` through `../doctrine/examples/146_declarative_project_lint_rule` — **adopt**: per-phase working examples. Examples 141 (P2), 142 (P3), 143 (P4), 144 (P5), 145 (P6), 146 (P7) are the canonical authored demos for each shipped feature.
- `../doctrine/CHANGELOG.md` — **adopt for dates**: Unreleased entries confirm P1-P7 ship dates 2026-04-19 / 2026-04-20.
- `../doctrine/skills/.curated/doctrine-learn/` + `../doctrine/skills/.curated/agent-linter/` — **adopt**: curated skill references (`AL245`, `AL246`, `AL285`, `AL960`, `AL970`, `AL980`, `AL990`) encode the authoring-pattern lessons; consult when a Rally TODO's rewrite must match curated guidance.
- `git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md` — **historical anchor**: retrieves the retired closure plan at its pre-retirement state. This is how §2.1's `Status: COMPLETE` phase table citations are honestly anchored now that the live doc path is gone.
- `git:../../doctrine@d629ded:docs/SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md` — **historical anchor**: the short-lived Doctrine-side feature request Rally's three skill-site TODOs were going to point at. Deleted same-day in `76011f2`. See §3.3 G1.
- `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` + `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` — **adopt for cross-reference**: prior Rally adoption plan and audit; forward findings F-6, F-9 through F-13 name the sites this plan touches. Phase 7 of this plan refreshes their TODO-state claims.

## 3.2 Internal ground truth (code as spec)

### Authoritative behavior anchors (do not reinvent)

**Shipped Doctrine grammar — `../doctrine/doctrine/grammars/doctrine.lark`:**

- P2 override gates (lines 235-248): `review_case_gates_override_block` with `review_case_gate_add` / `review_case_gate_remove` / `review_case_gate_modify`. Only applies inside a `review_case` under a multi-case `review_family`; a single `review` declaration has nothing to override.
- P3 receipt family (lines 960-965): `package_host_receipt_slot` with `receipt_field_list_type: "list" "[" name_ref "]"`. Ties to `ReceiptHostSlot` model.
- P4 typed_as (lines 748-751): `output_target_typed_as_stmt: "typed_as" ":" name_ref`. Attaches to `output_target_decl` only; does not attach to workflow prose.
- P5 skill mode (lines 706-713): `mode_stmt: "mode" CNAME "=" expr "as" name_ref` inside `skill_entry_body_line`. Governs **call pattern** (producer vs audit).
- P6 typed abstract params (line 168): `agent_slot_abstract: "abstract" CNAME (":" name_ref)?`. Optional type annotation enabling per-descendant typed variation.
- P7 rule primitive (lines 86-104): closed scope predicates `{agent_tag | flow | role_class | file_tree}` + closed assertion predicates `{requires inherit | forbids bind | requires declare}` + `message: string`. Compile-time-only.

**Shipped Doctrine model — `../doctrine/doctrine/_model/`:**

- `_model/agent.py:21-24` — `AuthoredSlotAbstract(key: str, declared_type: NameRef | None, source_span)`.
- `_model/io.py:246-252` — `OutputTargetDecl(name, title, items, delivery_skill_ref, typed_as: NameRef | None, source_span)`.
- `_model/io.py:484-492` — `ReceiptHostSlot(key, title, fields, ... family == "receipt")`.
- `_model/rule.py:74-80` — `RuleDecl(name, title, scope: RuleScope, assertions: tuple[RuleAssertion,...], message, source_span)`.
- `_model/workflow.py:57-63` — `SkillEntry(key, target, items, binds, mode: ModeStmt | None, source_span)`.

**Shipped Doctrine validators:**

- `_compiler/validate/review_semantics.py` — E531 (removed gate not declared), E532 (added gate already declared).
- `_compiler/resolve/outputs.py` + `_compiler/compile/outputs.py` — E533 (typed_as target not document/schema/table), E534 (required typed_as missing).
- `_compiler/compile/skill_package.py` + `_compiler/resolve/addressables.py` — E535/E536/E537 (receipt slot validation).
- `_compiler/compile/output_selectors.py` — E540-E543 (E543 fatal on enum-only selector; soft-deprecation of old `mode CNAME as name_ref` form).
- `_compiler/validate/agents.py` (`_validate_typed_abstract_slot_binding`) + `_compiler/resolved_types.py` (`ResolvedTypedAgentSlot`) — E538 (inline-block binding on typed slot), E539 (wrong-family binding).
- `_compiler/validate/rules.py` (`ValidateRulesMixin`) — RULE001 (scope target does not resolve), RULE002 (assertion target does not resolve), RULE003-RULE005.

**Rally-side shape of each TODO site (all 10 sites, verbatim-anchored):**

- `flows/poem_loop/prompts/shared/review.prompt:69-72` — TODO above single concrete `review PoemReview` (gates: `brief_match` / `rationale_fit` / `finish_quality`). No `review_family` / `review_case` structure. Doctrine P2 `override gates:` has no structural target here.
- `flows/software_engineering_demo/prompts/shared/review.prompt:122-124` — TODO above three concrete reviews (`ArchitectReview` gates: `issue_understood` / `repo_plan_real` / `next_step_clear`; `DeveloperReview` gates: `requested_change_present` / `proof_recorded` / `commit_state_clear`; `QaReview` gates: `requirements_met` / `proof_real` / `finish_ready`), all inheriting from `review_family EngineeringReviewFamily`. Each review has a **distinct contract** (`ArchitectReviewContract` / `DeveloperReviewContract` / `QaReviewContract`) with **fully distinct gate names**. P2 `override gates:` narrows one shared gate's copy; it does not collapse three distinct contracts.
- `flows/poem_loop/prompts/shared/contracts.prompt:1-4` — TODO above `workflow PoemLoopSystemContext` (prose bullets under a `workflow`, not an `output_target_decl`). P4 `typed_as:` attaches to output targets only.
- `flows/software_engineering_demo/prompts/AGENTS.prompt:107-110` — TODO above skills block `RepoWorkSkills` with three entries (`rally_kernel` Required, `demo_git` Required, `repo_search` Advisory). Rally's `requirement:` and Doctrine's `mode:` are orthogonal concepts (see G4).
- `flows/software_engineering_demo/prompts/AGENTS.prompt:146-149` — TODO above `abstract agent SoftwareEngineeringRole` with slots `system_context` / `issue_truth` / `repo_rules`. **Six** concrete descendants (Architect at line 157, ArchitectReviewer at 178, Developer at 204, DeveloperReviewer at 221, QaDocsTester at 245, QaReviewer at 262) all bind **identical** values: `SoftwareEngineeringSystemContext` / `IssueLedgerGroundTruth` / `DemoRepoRules`. Zero per-descendant variation.
- `flows/poem_loop/prompts/AGENTS.prompt:153-156` — TODO above `abstract agent PoemLoopRole` with slots `system_context` / `ground_truth` / `primary_path`. **Three** concrete descendants (Muse at line 164, PoemWriter at 181, PoemCritic at 202) all bind identical values: `PoemLoopSystemContext` / `IssueLedgerGroundTruth` / `PrimaryPathRules`. Zero per-descendant variation.
- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77-79` — TODO above `workflow RallyManagedSharedRules` with four prose bullets, verbatim: (1) "Use `home:issue.md` as the shared ledger for this run.", (2) "Leave one short saved note through `Saved Run Note` only when later readers need it.", (3) "End the turn with the final JSON this turn declares.", (4) "Keep routing, `done`, `blocker`, and `sleep` in final JSON, not in notes." All four are **runtime turn behaviors**, not structural invariants; Doctrine P7 `rule` is compile-time-only.
- `skills/demo-git/prompts/SKILL.prompt:10-12` — TODO `F-6` over `skill package DemoGitSkill`; points at promoting hardcoded path `home:repos/demo_repo` into a typed host_contract scalar/path binding. Unshipped concept.
- `skills/rally-kernel/prompts/SKILL.prompt:18-21` — TODO `F-6` over `skill package RallyKernel`; points at env-vars `RALLY_CLI_BIN` / `RALLY_RUN_ID` / `RALLY_WORKSPACE_DIR`. Unshipped. Current v5 `host_contract:` accepts only `{input | output | document | analysis | schema | table | final_output | receipt}`.
- `skills/rally-memory/prompts/SKILL.prompt:20-23` — TODO `F-6` over `skill package RallyMemory`; points at env-vars `RALLY_CLI_BIN` / `RALLY_RUN_ID` / `RALLY_AGENT_SLUG`. Same unshipped concept.

`rg 'TODO\(doctrine' flows stdlib skills` confirms these 10 are the complete set — no more, no fewer.

### Canonical path / owner to reuse

- **Authoring surface (Rally-owned):** `.prompt` source under `flows/*/prompts/**`, `stdlib/rally/prompts/**`, `skills/*/prompts/**`. Sole write target for every verdict (adopt or retire).
- **Authoring surface (Doctrine-owned):** `../doctrine/grammars/doctrine.lark` + `../doctrine/_model/**` + `../doctrine/_compiler/**`. Read-only for this plan.
- **Generated readback:** `flows/*/build/**` (confirmed present at `flows/poem_loop/build/agents/muse/AGENTS.md` and `flows/software_engineering_demo/build/agents/architect/AGENTS.md`). Regenerated by compile; never hand-edited.

### Adjacent surfaces tied to the same contract family

- `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` — prior adoption plan (forward findings F-6, F-9 through F-13). Must stay in sync; Phase 7 of §7 touches it.
- `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` — prior audit companion. Same cross-reference update in Phase 7.
- `../doctrine/CHANGELOG.md` — documents ship-dates for P1-P7. Read-only adjacent surface; Rally does not write here.

### Compatibility posture (separate from `fallback_policy`)

**Clean cutover per site.** Each TODO resolves to exactly one of: (a) adopt shipped syntax (prose TODO disappears, real syntax replaces it), or (b) retire with a §10 Decision Log entry (TODO deleted, nothing bridges). No dual-form parked state. No timeboxed bridge. No silent prose coexisting with real syntax.

### Existing patterns to reuse

- Rally already uses `review_family` + inheriting `review` at `flows/software_engineering_demo/prompts/shared/review.prompt:103`. The pattern matches P2's surface shape — but the three member reviews have **distinct contracts**, not one shared contract with per-case overrides. Pattern recognition: Rally is already on the right authoring shape; P2's new feature has no structural target.
- Rally already uses `abstract agent` + concrete descendants at both `PoemLoopRole` and `SoftwareEngineeringRole`. The pattern matches P6's surface shape — but every descendant binds identical values. Pattern recognition: Rally is already on the right shape; P6 exists for per-descendant variation that Rally doesn't have.

### Prompt surfaces / agent contract to reuse

- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt` owns `RallyManagedBaseAgent` + `RallyManagedSharedRules` as the single shared carrier for the four runtime turn rules. No duplicate copies in flows. The P7 TODO sits at this shared carrier site.

### Native model or agent capabilities to lean on

- N/A. This plan changes authoring-source form, not agent behavior. No new LLM capability is needed.

### Existing grounding / tool / file exposure

- Per-phase proof tool: Rally-paired Doctrine compiler (`uv run doctrine compile …` from Rally root, or per-flow equivalent) recompiles `flows/*/build/**` from edited `.prompt` source.
- Per-phase unit gate: `uv run pytest tests/unit -q` at Rally repo root.
- Per-skill proof: the three touched skills (`skills/demo-git`, `skills/rally-kernel`, `skills/rally-memory`) have curated build mirrors under `skills/*/build/`; recompile + diff per edit.

### Duplicate or drifting paths relevant to this change

- **Stale anchors in TL;DR, §2.1, §5.3, §6.1, §7 Phase 7, §10 Decision Log.** TL;DR cites "Doctrine closure plan shipped **all** of Phases 2-7" without naming the git commit that retired the plan. §2.1 table header cites "per `doctrine/docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md`" — that path is dead. §10's `2026-04-20 - Retire the three skill-site TODOs …` entry cites `../../doctrine/docs/SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md` as the retirement anchor; that doc was deleted same-day and no live equivalent exists. `related:` frontmatter has been repaired in this research pass. The remaining prose repairs are scoped to Phase 7 of §7 ("refresh Rally adoption docs") + an honest §10 update for G1 (see §3.3).
- **Rally plan's §2.2 phase-mapping table is still accurate** in its Rally-local → Doctrine-current mapping (Rally P3 = Doctrine P4, Rally P5 = Doctrine P6, Rally P6 = Doctrine P5), and the grammar production names it anticipated all exist. No repair needed there.

### Capability-first opportunities before new tooling

- N/A. No new tooling proposed.

### Behavior-preservation signals already available

- Compiled readback under `flows/*/build/**` is the front-line preservation signal for prompt-source edits. Expected diff after each phase: TODO-comment removal or rewording only, never instruction-semantic drift.
- Curated skill mirrors under `skills/*/build/` play the same role for the three skill sites.
- Doctrine-side examples 140-146 are the end-state reference corpus; Rally's adopted syntax (if any site adopts) must match those examples' shape.

## 3.3 Decision gaps that must be resolved before implementation

Research resolved G2-G7 from repo evidence. G0 and G1 are the live gaps for user confirmation before `deep-dive` closes the verdict table in §5.3 / §6.1. G8 is a phase-plan shaping note.

**G0 — Stale-anchor repair scope.** The Rally plan's TL;DR / §2.1 / §10 prose refers to the now-retired Doctrine closure plan and scalar-host-slot request docs. `related:` frontmatter has been re-anchored in this pass. Repo evidence: both source docs are retired (`8c3701a`, `76011f2`); fold-forward destinations live at `LANGUAGE_REFERENCE.md` / `COMPILER_ERRORS.md` / `examples/140-146`. Default recommendation: treat prose repairs as Phase-7 docs-hygiene scope (same phase that already refreshes the two neighboring Rally adoption docs). The plan's falsifiable §0.1 claim is unchanged. **Answer needed:** confirm docs-hygiene in Phase 7, not a scope change.

**G1 — Retirement anchor for the three skill-site TODOs (F-6).** The Doctrine-side feature request `SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md` was deleted same-day (Doctrine `d629ded` → `76011f2`); there is no live Doctrine doc home for the scalar / env-var / path host-slot concept. The Rally plan's §10 entry currently cites that doc as the retirement anchor. Default recommendation: retire the three Rally TODOs anyway (as §5.3 / §10 propose), but rewrite the Decision Log entry to anchor on: (a) the Doctrine git-commit pair `d629ded` → `76011f2` that recorded-and-deleted the concept, and (b) the observation that current v5 `host_contract:` accepts only `{input | output | document | analysis | schema | table | final_output | receipt}`. Repo evidence supports retirement without a live Doctrine pointer. **Answer needed:** user confirmation that retirement without a live Doctrine-side request doc is acceptable, and whether Rally should file a fresh Doctrine-side request (out-of-scope for this plan, noted for follow-up) or accept that the concept is fully retired from both sides.

**G2 — P4 `typed_as:` vs workflow prose (poem_loop/contracts.prompt).** Grammar (`output_target_typed_as_stmt`, doctrine.lark:748-751) and model (`OutputTargetDecl.typed_as`, `_model/io.py:246-252`) confirm `typed_as:` attaches to `output_target_decl` only. Example 143 demonstrates: `output ReleaseNote: target: … shape: MarkdownDocument structure: … typed_as: shared.handoff.ReleaseNoteDocument`. Rally's `PoemLoopSystemContext` is a `workflow` with prose bullets — no `output_target_decl` exists at the TODO site. **Verdict locked: retire.** No answer needed.

**G3 — P2 `override gates:` vs Rally's two sites.** Grammar (`review_case_gates_override_block`, doctrine.lark:235-248) + example 141 confirm the feature targets per-case gate narrowing under a multi-case `review_family` with a **shared** contract. Evidence: poem_loop has a single concrete `review PoemReview` (not a family, not multi-case — nothing to override). software_engineering_demo has three reviews with fully distinct contracts and distinct gate name sets (`issue_understood` vs `requested_change_present` vs `requirements_met`) — there are no shared gate copies to narrow. **Verdict locked: retire both sites.** No answer needed.

**G4 — P5 `mode:` vs Rally's `requirement:` (software_engineering_demo/AGENTS.prompt:107).** Grammar (`mode_stmt`, doctrine.lark:706-713) + example 144 (producer + audit enum cases + invalid enum-only selector fixture) confirm `mode:` governs **call pattern** (producer vs audit vs readonly per SkillMode enum). Rally's `requirement: Required | Advisory` governs **frequency**. Orthogonal concepts. Evidence from `RepoWorkSkills` (AGENTS.prompt:111-120): three skill entries (`rally_kernel`, `demo_git`, `repo_search`) — all producer-shape; no genuine audit-pattern entry. Default recommendation: retire the TODO with a rewrite that documents orthogonality; do not adopt `mode:` at this site. **Answer needed:** confirm no adoption at this pass. If the user knows of a Rally site with a genuine audit-shape skill that would benefit from `mode:`, name it; otherwise this is a clean retire.

**G5 — P6 typed abstract params vs uniform bindings.** Grammar (`agent_slot_abstract` with optional `: name_ref`, doctrine.lark:168) + model (`AuthoredSlotAbstract.declared_type: NameRef | None`, `_model/agent.py:21-24`) confirm the feature exists for **per-descendant typed variation** (example 145: `TypedPolicyReviewer` with `abstract policy: AccuracyPolicy` bound to `AccuracyPolicy` by `AccuracyReviewer` and to `TonePolicy` by `ToneReviewer`). Evidence: poem_loop's three descendants all bind `{PoemLoopSystemContext, IssueLedgerGroundTruth, PrimaryPathRules}`; software_engineering_demo's six descendants all bind `{SoftwareEngineeringSystemContext, IssueLedgerGroundTruth, DemoRepoRules}`. Zero per-descendant variation in either flow. **Verdict locked: retire both sites.** No answer needed.

**G6 — P7 `rule` primitive vs runtime turn instructions.** Grammar (doctrine.lark:86-104) confirms closed predicate surface: scope `{agent_tag | flow | role_class | file_tree}`, assertions `{requires inherit | forbids bind | requires declare}`, `message: string`. Validator (`_compiler/validate/rules.py`, RULE001-RULE005) runs at compile time. Example 146 (`rule ComposersCheckUpstream … requires inherit UpstreamPoisoningInvariant`) demonstrates the intended use: compile-time structural safeguard. Rally's four `RallyManagedSharedRules` bullets are all runtime behaviors (ledger file, note discipline, turn-ending JSON, routing placement) — zero map to inheritance / binding / declaration invariants. **Verdict locked: retire.** No answer needed.

**G7 — Zero-surviving-TODOs claim.** Every pre-existing Rally TODO is either converted (removed as a comment) or retired (removed as a comment). No TODO survives; renumbering is moot. Phase 7 exit criterion: `rg 'TODO\(doctrine' flows stdlib skills` returns zero matches. **Verdict locked.** No answer needed.

**G8 — Per-phase proof signal.** Repo evidence: `uv run pytest tests/unit -q` covers Rally runtime / CLI tests, not Doctrine compile of flows. Readback under `flows/*/build/**` is the real preservation signal for prompt-source edits. Default recommendation: each phase's exit criteria should require **both** `uv run pytest tests/unit -q` clean at Rally root **and** a clean Doctrine-paired recompile of the owning flow's readback with only the expected TODO-comment diff. Deep-dive / phase-plan should bake this into §7 exit criteria. **Answer needed:** none — this is phase-plan scope.

### Updated verdict summary (9 retires locked, 1 retire-contingent-on-G4)

| Site | Feature | Verdict (post-research) |
|------|---------|-------------------------|
| poem_loop/shared/review.prompt:69 | P2 override gates | retire (G3) |
| se_demo/shared/review.prompt:122 | P2 override gates | retire (G3) |
| poem_loop/shared/contracts.prompt:1 | P4 typed_as | retire (G2) |
| se_demo/AGENTS.prompt:107 | P5 skill mode | **retire pending G4 user confirmation** |
| se_demo/AGENTS.prompt:146 | P6 typed abstract params | retire (G5) |
| poem_loop/AGENTS.prompt:153 | P6 typed abstract params | retire (G5) |
| stdlib base_agent AGENTS.prompt:77 | P7 rule | retire (G6) |
| skills/demo-git SKILL.prompt:10 | F-6 scalar host slot (unshipped) | retire pending G1 confirmation |
| skills/rally-kernel SKILL.prompt:18 | F-6 scalar host slot (unshipped) | retire pending G1 confirmation |
| skills/rally-memory SKILL.prompt:20 | F-6 scalar host slot (unshipped) | retire pending G1 confirmation |

Shape-fit across the full set came out **retire everywhere**. No adopt site survives research. This confirms the §1.4 tradeoff ("this plan intentionally leans into retirement rather than aggressive adoption") with concrete repo evidence.

<!-- arch_skill:block:research_grounding:end -->

---

# 4) Current Architecture (as-is)

<!-- arch_skill:block:current_architecture:start -->

## 4.1 On-disk structure

- **Authored prompt source (Rally-owned, write target for this plan):**
  - `flows/poem_loop/prompts/**` — 1 review site, 1 contracts site, 1 AGENTS site
  - `flows/software_engineering_demo/prompts/**` — 1 review site, 2 AGENTS sites
  - `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt` — 1 shared-rules site
  - `skills/demo-git/prompts/SKILL.prompt`, `skills/rally-kernel/prompts/SKILL.prompt`, `skills/rally-memory/prompts/SKILL.prompt` — 3 skill sites
- **Compiled readback (regenerated, never hand-edited):** `flows/poem_loop/build/**`, `flows/software_engineering_demo/build/**`, `skills/*/build/**`. Confirmed present at `flows/poem_loop/build/agents/muse/AGENTS.md` and `flows/software_engineering_demo/build/agents/architect/AGENTS.md`.
- **Doctrine-owned authoring surface (read-only for this plan):** `../doctrine/doctrine/grammars/doctrine.lark`, `../doctrine/doctrine/_model/**`, `../doctrine/doctrine/_compiler/**`, `../doctrine/examples/140-146`, `../doctrine/docs/LANGUAGE_REFERENCE.md`, `../doctrine/docs/COMPILER_ERRORS.md`.
- **Rally adjacent docs (cross-reference, touched in Phase 7):** `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md`, `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md`.

## 4.2 Control paths (runtime)

- Authored `.prompt` compiles to readback via the Rally-paired Doctrine compiler. Runtime consumes readback only.
- `TODO(doctrine …)` comments live in `.prompt` source and are stripped from compiled readback, so retirement has zero runtime effect — the proof signal for a retire edit is "no unexpected readback diff", not "runtime behavior unchanged".
- The ten TODO sites are all at authoring-shape boundaries (review declarations, contract workflows, abstract agents, skill entries, base-agent shared workflow, skill packages). They do not gate any control path; they are author hints only.

## 4.3 Object model + key abstractions

Doctrine constructs **in use at the touched Rally sites** (not a full Doctrine inventory):

- `review` — single concrete review declaration. Used at `poem_loop/shared/review.prompt` (PoemReview, 3 gates).
- `review_family` + `review` — family with inheriting concrete reviews. Used at `software_engineering_demo/shared/review.prompt` (EngineeringReviewFamily + ArchitectReview / DeveloperReview / QaReview, each with a distinct `schema` contract).
- `schema` (review contract) — gate declaration carrier. Used per-review in se_demo (`ArchitectReviewContract`, `DeveloperReviewContract`, `QaReviewContract`).
- `workflow` + prose bullets — free-form authoring for system context and shared rules. Used at `poem_loop/shared/contracts.prompt` (PoemLoopSystemContext) and `stdlib/rally/base_agent/AGENTS.prompt` (RallyManagedSharedRules).
- `abstract agent` + concrete `agent[Parent]` — role hierarchy with slot-key bindings. Used at both `PoemLoopRole` (slots `system_context` / `ground_truth` / `primary_path`; 3 concretes) and `SoftwareEngineeringRole` (slots `system_context` / `issue_truth` / `repo_rules`; 6 concretes).
- `skills` block + `skill <key>: <Pkg>` entry + `requirement: Required | Advisory` — skill-binding declaration with Rally-owned frequency field. Used at `software_engineering_demo/AGENTS.prompt:111-120` (RepoWorkSkills: rally_kernel Required, demo_git Required, repo_search Advisory).
- `skill package` — skill authoring surface with `host_contract:` for typed slots. Used at `skills/demo-git`, `skills/rally-kernel`, `skills/rally-memory`. Current v5 `host_contract:` slot families: `{input | output | document | analysis | schema | table | final_output | receipt}`. No scalar/env-var/path family.

**Shipped Doctrine P2-P7 constructs NOT yet in use at any touched Rally site** (research confirmed shape-mismatch at every candidate site):

- `review_case` under `review_family` with `override gates:` block (P2) — no Rally site has multi-case structure with shared gate copies.
- `output_target_decl` with `typed_as:` (P4) — no Rally site at a contract-workflow TODO has an `output_target_decl`.
- `host_contract:` with `receipt` family (P3) — not targeted by any surviving TODO.
- `skill_entry_body_line` with `mode:` (P5) — RepoWorkSkills entries are all producer-shape; no audit-pattern distinction present.
- `agent_slot_abstract` with `: TypeRef` annotation (P6) — every descendant in both flows binds the same values; no per-descendant typed variation.
- `rule_decl` with closed scope/assertions (P7) — RallyManagedSharedRules carries runtime turn instructions, not compile-time inheritance/binding/declaration invariants.

## 4.4 Observability + failure behavior today

- **Doctrine diagnostic codes** relevant to this plan (all shipped per `../doctrine/docs/COMPILER_ERRORS.md`):
  - P2: `E531` (gate removed from review case is not declared), `E532` (added gate already declared)
  - P3: `E535`, `E536`, `E537` (receipt slot validation)
  - P4: `E533` (typed_as target not document/schema/table), `E534` (required typed_as missing)
  - P5: `E540`-`E543` (E543 fatal on enum-only output-shape selector)
  - P6: `E538` (inline-block binding on typed slot), `E539` (wrong-family binding)
  - P7: `RULE001` (scope target unresolved), `RULE002` (assertion target unresolved), `RULE003`-`RULE005`. `RULE006`-`RULE099` reserved for future closed-predicate additions; `RULE100+` reserved for open-expression rules.
- **Rally-side failure surfaces:** `uv run pytest tests/unit -q` at Rally repo root (runtime/CLI coverage); compiled readback diff under `flows/*/build/**` (readback drift detection). Neither catches prompt-source intent drift — that responsibility sits with authoring review + the TODO markers themselves.
- **Today's silent-failure mode:** stale `TODO(doctrine …)` markers. A marker pointing at a now-shipped Doctrine phase without resolution, or at an unshipped concept that has been retired Doctrine-side, is invisible to both the compiler and `pytest`. This plan is the repair for exactly that failure mode.

## 4.5 UI surfaces (ASCII mockups, if UI work)

- N/A. No UI work.

<!-- arch_skill:block:current_architecture:end -->

---

# 5) Target Architecture (to-be)

<!-- arch_skill:block:target_architecture:start -->

## 5.1 On-disk structure (future)

Unchanged from §4.1. No new files, no deletions outside the TODO comment blocks themselves. The same 10 `.prompt` files own the edits; compiled readback under `flows/*/build/**` and `skills/*/build/**` is regenerated per phase.

## 5.2 Control paths (future)

Unchanged from §4.2. All edits are author-only. `TODO(doctrine …)` comments are stripped from compiled readback, so retirement produces no runtime effect — the proof signal is "expected readback diff only" (comment removal upstream, semantically equivalent readback downstream) plus `uv run pytest tests/unit -q` clean at Rally root.

## 5.3 Object model + abstractions (future)

Shape-fit verdict per TODO site, with the governing repo evidence. Research (§3.3) resolved G2/G3/G5/G6/G7/G8 from repo evidence; G0/G1/G4 remain as **phase-plan gates** — not structural unknowns, but user confirmations required before phase-plan can declare ready. The verdict on all 10 sites is the same outcome (retire) regardless of how the three gates resolve; the gates only govern the precise Decision Log anchoring and Phase 7 scope.

| # | Site | Shipped feature | Verdict | Locked by |
|---|------|-----------------|---------|-----------|
| 1 | `flows/poem_loop/prompts/shared/review.prompt:69` | P2 `override gates:` on `review_case` | Retire | G3 — single concrete `review PoemReview`; no multi-case `review_family` to narrow |
| 2 | `flows/software_engineering_demo/prompts/shared/review.prompt:122` | P2 `override gates:` on `review_case` | Retire | G3 — three reviews have fully distinct `schema` contracts (`issue_understood` / `requested_change_present` / `requirements_met`); no shared gate copies exist to override |
| 3 | `flows/poem_loop/prompts/shared/contracts.prompt:1` | P4 `typed_as:` on `output_target_decl` | Retire | G2 — TODO targets a `workflow` with prose bullets; grammar `output_target_typed_as_stmt` attaches to `output_target_decl` only (`doctrine.lark:748-751`, `_model/io.py:246-252`) |
| 4 | `flows/software_engineering_demo/prompts/AGENTS.prompt:107` | P5 `mode:` on `skill_entry_body_line` | Retire | G4 pending user confirm — `mode:` governs call pattern (producer/audit/readonly per SkillMode enum); Rally `requirement:` governs frequency; orthogonal. `RepoWorkSkills` entries are all producer-shape; no audit-shape skill exists at this site |
| 5 | `flows/software_engineering_demo/prompts/AGENTS.prompt:146` | P6 typed abstract params (`abstract NAME: TypeRef`) | Retire | G5 — all six descendants (`architect` / `pm` / `developer` / `reviewer` / `qa` / `ops`) bind the same three slots to the same three values; zero per-descendant type variation |
| 6 | `flows/poem_loop/prompts/AGENTS.prompt:153` | P6 typed abstract params | Retire | G5 — all three descendants (`muse` / `critic` / `editor`) bind the same three slots to the same three values; zero per-descendant type variation |
| 7 | `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` | P7 `rule` primitive (closed scope / assertions) | Retire | G6 — validator RULE001-RULE005 runs at compile time over `{requires inherit / forbids bind / requires declare}` on `{agent_tag / flow / role_class / file_tree}`; the four `RallyManagedSharedRules` bullets are runtime turn instructions (ledger file, note discipline, turn-ending JSON, routing placement). Zero map to inheritance/binding/declaration invariants |
| 8 | `skills/demo-git/prompts/SKILL.prompt:10` | Unshipped Doctrine scalar/env-var/path host-slot family | Retire | G1 pending user confirm — current v5 `host_contract:` accepts `{input / output / document / analysis / schema / table / final_output / receipt}` only; scalar-host-slot request was filed and retired same-day (Doctrine `d629ded` → `76011f2`) |
| 9 | `skills/rally-kernel/prompts/SKILL.prompt:18` | Unshipped Doctrine scalar/env-var/path host-slot family | Retire | G1 — same rationale |
| 10 | `skills/rally-memory/prompts/SKILL.prompt:20` | Unshipped Doctrine scalar/env-var/path host-slot family | Retire | G1 — same rationale |

**Phase-plan gates still requiring user answer (block "ready", not verdict):**

- **G0** — confirm stale-anchor prose repairs (TL;DR / §2.1 / §10 references to retired Doctrine docs) land in Phase 7 alongside the two neighboring Rally adoption docs, not as a scope widening.
- **G1** — confirm retirement of the three skill-site TODOs without a live Doctrine-side request doc; confirm whether Rally should file a fresh Doctrine-side feature request (out-of-scope follow-up) or accept that the concept is fully retired on both sides.
- **G4** — confirm no P5 `mode:` adoption at `RepoWorkSkills`; name any other Rally site that carries a genuine audit-shape skill if one exists.

## 5.4 Invariants and boundaries

- **Clean cutover per site.** Every affected TODO block is deleted outright. No dual-form state (old TODO + new feature) is tolerated at any site — not even transiently across phases.
- **No runtime behavior change.** Every edit is authoring-shape only. Compiled readback under `flows/*/build/**` and `skills/*/build/**` must remain semantically equivalent (comment-stripping is the only expected diff). `uv run pytest tests/unit -q` must stay clean across all Rally phases.
- **One Decision Log owner per site.** Each retired TODO earns a dated §10 entry citing: (a) the Rally site path + line, (b) the shipped Doctrine feature it was pointing at (or the unshipped concept, for F-6), (c) the specific shape-fit reason from §3.3's G-gate, (d) the grammar production / model class / validator code / example that grounds the shape-fit reasoning (per the enduring feedback rule).
- **Live-docs parity.** Rally's prior V5 exemplar plan + V5 audit docs are updated in the same phase (Phase 7) that repairs this plan's own stale-anchor prose. No cross-doc inconsistency is left behind.
- **No authoring invention beyond retirement.** This plan introduces zero new Doctrine feature adoption. Adopt decisions are out of scope by §0.3; every verdict is retire. If a future shape-fit opportunity emerges (e.g., a new Rally site with a real audit-shape skill for P5 `mode:`), it opens a new plan — it does not expand this one.
- **Zero surviving `TODO(doctrine …)` markers after Phase 7 exit.** `rg 'TODO\(doctrine' flows stdlib skills` returns zero matches; this is a Phase 7 exit criterion, not a soft goal.
- **No Doctrine edits.** `../doctrine/**` stays read-only for the whole plan. Rally does not file, stage, commit, or retire Doctrine-side docs as part of this plan.

## 5.5 UI surfaces (ASCII mockups, if UI work)

N/A. No UI work.

<!-- arch_skill:block:target_architecture:end -->

---

# 6) Call-Site Audit (exhaustive change inventory)

<!-- arch_skill:block:call_site_audit:start -->

## 6.1 Change map (table)

Ten author-only edits across seven `.prompt` files, plus two Rally adoption docs refreshed in Phase 7. Every row is a retire (comment removal) — no new Doctrine feature syntax is introduced anywhere in the tree.

| # | File | Line | Current marker | Edit | Grounded in | Expected readback diff |
|---|------|------|----------------|------|-------------|------------------------|
| 1 | `flows/poem_loop/prompts/shared/review.prompt` | 69 | `TODO(doctrine P2 override gates)` | Delete TODO comment block | G3 + grammar `review_case_gates_override_block` (`doctrine.lark:235-248`), example 141 | None (comments stripped from readback) |
| 2 | `flows/software_engineering_demo/prompts/shared/review.prompt` | 122 | `TODO(doctrine P2 override gates)` | Delete TODO comment block | G3 — three reviews, distinct `schema` contracts, distinct gate name sets | None |
| 3 | `flows/poem_loop/prompts/shared/contracts.prompt` | 1 | `TODO(doctrine P3 / typed_as)` | Delete TODO comment block | G2 + grammar `output_target_typed_as_stmt` (`doctrine.lark:748-751`), model `OutputTargetDecl.typed_as` (`_model/io.py:246-252`), example 143 | None |
| 4 | `flows/software_engineering_demo/prompts/AGENTS.prompt` | 107 | `TODO(doctrine P6 skill mode)` | Delete TODO comment block | G4 + grammar `mode_stmt` (`doctrine.lark:706-713`), example 144, SkillMode enum | None |
| 5 | `flows/software_engineering_demo/prompts/AGENTS.prompt` | 146 | `TODO(doctrine P5 typed abstract params)` | Delete TODO comment block | G5 + grammar `agent_slot_abstract` (`doctrine.lark:168`), model `AuthoredSlotAbstract.declared_type` (`_model/agent.py:21-24`), example 145 | None |
| 6 | `flows/poem_loop/prompts/AGENTS.prompt` | 153 | `TODO(doctrine P5 typed abstract params)` | Delete TODO comment block | G5 — same rationale | None |
| 7 | `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt` | 77 | `TODO(doctrine P7 rule primitive)` | Delete TODO comment block | G6 + grammar (`doctrine.lark:86-104`), validator RULE001-RULE005, example 146 | None |
| 8 | `skills/demo-git/prompts/SKILL.prompt` | 10 | `TODO(doctrine scalar host slot)` | Delete TODO comment block | G1 + current v5 `host_contract:` slot families, Doctrine commits `d629ded` → `76011f2` | None |
| 9 | `skills/rally-kernel/prompts/SKILL.prompt` | 18 | `TODO(doctrine scalar host slot)` | Delete TODO comment block | G1 — same rationale | None |
| 10 | `skills/rally-memory/prompts/SKILL.prompt` | 20 | `TODO(doctrine scalar host slot)` | Delete TODO comment block | G1 — same rationale | None |
| d1 | `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` | — | Forward findings F-9..F-13 describe pre-P6/P7 TODO state | Refresh references to post-adoption tree + current Doctrine phase status | G0 | Prose only |
| d2 | `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` | — | Same pre-adoption cross-references | Refresh references to post-adoption tree | G0 | Prose only |
| d3 | This plan's TL;DR / §1.4 / §2.1 / §10 | — | Prose still references retired Doctrine closure plan + scalar-host-slot request as live anchors | Repair prose to cite fold-forward destinations (LANGUAGE_REFERENCE.md, COMPILER_ERRORS.md, examples/140-146) + git-commit historical refs | G0 | Prose only |

## 6.2 Migration notes

**Canonical owner path.** Prompt source under `flows/*/prompts/**`, `stdlib/rally/prompts/**`, and `skills/*/prompts/**` remains the single authored source. Compiled readback under `flows/*/build/**` and `skills/*/build/**` is regenerated per phase via the Rally-paired Doctrine compiler. `../doctrine/**` stays read-only for the whole plan.

**Delete list (authoritative, all 10 TODO comment blocks plus prose edits d1/d2/d3):**

- `flows/poem_loop/prompts/shared/review.prompt:69` — P2 override-gates TODO
- `flows/software_engineering_demo/prompts/shared/review.prompt:122` — P2 override-gates TODO
- `flows/poem_loop/prompts/shared/contracts.prompt:1` — P4 typed_as TODO (comment currently mis-labels the phase as P3; delete, do not rewrite)
- `flows/software_engineering_demo/prompts/AGENTS.prompt:107` — P5 skill-mode TODO (comment currently mis-labels the phase as P6; delete, do not rewrite)
- `flows/software_engineering_demo/prompts/AGENTS.prompt:146` — P6 typed-abstract-params TODO (comment currently mis-labels the phase as P5; delete, do not rewrite)
- `flows/poem_loop/prompts/AGENTS.prompt:153` — P6 typed-abstract-params TODO (same mis-labeling; delete)
- `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` — P7 rule-primitive TODO
- `skills/demo-git/prompts/SKILL.prompt:10` — scalar host-slot TODO
- `skills/rally-kernel/prompts/SKILL.prompt:18` — scalar host-slot TODO
- `skills/rally-memory/prompts/SKILL.prompt:20` — scalar host-slot TODO

No file is deleted wholesale; no Doctrine construct is added; no `.prompt` is renamed.

**Adjacent surfaces updated in the same plan (Phase 7).** Two neighboring Rally docs plus this plan's own internal prose:

- `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md`
- `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md`
- This plan's TL;DR, §1.4 known tradeoffs, §2.1 "What exists today", §10 Decision Log prose (not the verdict entries — the stale-anchor prose that still names retired Doctrine docs as live).

**Compatibility posture: clean cutover, per site.** No shim, no bridge, no dual-form retention, no soft-deprecation period. A retired TODO is deleted outright; the Decision Log preserves the full rationale for future readers. The shape-fit analysis lives in §3.3 / §5.3 and in the Decision Log anchored to grammar + model + validator + example.

**Fallback policy.** None is required. Every edit is comment-removal in prompt source that is stripped from readback at compile time. There is no runtime-visible behavior to roll back.

**Live-docs repair list (Phase 7 owns all of these).**

- TL;DR, §1.4, §2.1, §10 prose of this plan — repair stale live-doc references per G0.
- `RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` — forward findings F-9..F-13 updated to post-adoption tree.
- `RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` — cross-references updated to match.
- §10 Decision Log entries for G1 retirements anchored on the Doctrine git-commit pair `d629ded` → `76011f2` plus the v5 `host_contract:` slot family list, per the enduring research-reads-source rule.

**Behavior-preservation signals (per-phase exit criteria).**

- `uv run pytest tests/unit -q` at Rally repo root: clean.
- Doctrine-paired recompile of the owning flow/skill: readback diff contains only comment removal (plus whitespace). No semantic change. No new diagnostic codes tripped.
- After Phase 7: `rg 'TODO\(doctrine' flows stdlib skills` returns zero matches.
- After Phase 7: cross-doc consistency check — no Rally doc under `docs/` still cites retired Doctrine docs as live references without a `git:` anchor.

**Adjacent-surface freshness check.** Before any phase starts, re-run `rg 'TODO\(doctrine' flows stdlib skills` to confirm the delete list still matches the tree; if a new TODO has appeared, stop and route to a plan addendum rather than expanding this plan silently.

<!-- arch_skill:block:call_site_audit:end -->

---

# 7) Depth-First Phased Implementation Plan (authoritative)

<!-- arch_skill:block:phase_plan:start -->

> Rule: systematic build, foundational first; each phase is a coherent self-contained unit. `Work` is explanatory. `Checklist (must all be done)` is authoritative. `Exit criteria (all required)` names the concrete done conditions fresh audit must validate. Per the enduring research-reads-source rule, every §10 Decision Log entry below anchors on Doctrine grammar + model + validator code + example — not only the retired closure plan.

## Phase 1 — Pin Doctrine ground truth for P2-P7

**Status: COMPLETE (2026-04-20)** — research pass already executed in this session; §3.3 holds the resolutions.

**Work.** Read Doctrine's shipped grammar (`../doctrine/doctrine/grammars/doctrine.lark`), model (`../doctrine/doctrine/_model/**`), validator diagnostics (`../doctrine/docs/COMPILER_ERRORS.md`), and examples 141-146 to lock each TODO site's shape-fit verdict before any Rally edits. Output lands in §3.3, §5.3, and §6.1.

**Checklist (must all be done).**

- [x] Read grammar productions governing P2-P7: `review_case_gates_override_block` (doctrine.lark:235-248), `host_contract_body_line`, `output_target_typed_as_stmt` (doctrine.lark:748-751), `mode_stmt` (doctrine.lark:706-713), `agent_slot_abstract` (doctrine.lark:168), `rule_decl` (doctrine.lark:86-104).
- [x] Read model dataclasses: `ReviewCase`, `OutputTargetDecl.typed_as` (`_model/io.py:246-252`), `SkillEntry.mode` (`_model/workflow.py:57-63`), `AuthoredSlotAbstract.declared_type` (`_model/agent.py:21-24`), `RuleDecl`.
- [x] Read validator diagnostic codes E531-E543 + RULE001-RULE005 (`../doctrine/docs/COMPILER_ERRORS.md`).
- [x] Read working examples 141 (P2), 142 (P3), 143 (P4), 144 (P5), 145 (P6), 146 (P7).
- [x] Lock 10 retire verdicts in §5.3 verdict table.
- [x] Write §6.1 change map (13 rows: 10 TODO deletes + 3 adjacent-doc/prose rows).

**Exit criteria (all required).**

- [x] §3.3 decision gaps G2/G3/G5/G6/G7/G8 resolved from repo evidence; G0/G1/G4 flagged as phase-plan user-confirmation gates governing Decision Log anchoring only (verdict is retire in every scenario).
- [x] §5.3 verdict table locked; each row cites the governing G-gate + grammar/model/validator/example anchor.
- [x] §6.1 change map enumerates every edit with expected readback diff.

## Phase 2 — Retire the P2 override-gates TODOs

**Status: COMPLETE (2026-04-20)** — both TODO blocks deleted; §10 entry appended; `make emit` + `uv run pytest tests/unit -q` clean.

**Work.** Delete both `TODO(doctrine P2)` comment blocks. `poem_loop/shared/review.prompt:69-72` marks a hypothetical future multi-case variant; poem_loop has one concrete `review PoemReview` (no family, no cases). `se_demo/shared/review.prompt:122-124` marks the idea that three reviews could share gate copies; the three reviews have fully distinct `schema` contracts and distinct gate name sets (`issue_understood` / `requested_change_present` / `requirements_met`).

**Checklist (must all be done).**

- [x] Delete TODO comment block at `flows/poem_loop/prompts/shared/review.prompt:69-72`.
- [x] Delete TODO comment block at `flows/software_engineering_demo/prompts/shared/review.prompt:122-124`.
- [x] Append §10 Decision Log entry covering both sites; anchor on G3 + grammar `review_case_gates_override_block` (`doctrine.lark:235-248`) + example 141 + the single-case / distinct-contract rationale per site.

**Exit criteria (all required).**

- [x] `rg 'TODO\(doctrine P2' flows` returns 0 matches.
- [x] `make emit` completes cleanly for both flows; readback diff under `flows/poem_loop/build/**` and `flows/software_engineering_demo/build/**` is comment-removal only (no semantic prompt drift).
- [x] `uv run pytest tests/unit -q` clean.
- [x] §10 entry present and anchored to grammar/model/validator/example per the research-reads-source rule.

## Phase 3 — Retire the P4 typed_as TODO on workflow prose

**Status: COMPLETE (2026-04-20)** — TODO block deleted; §10 entry appended; `make emit` + `uv run pytest tests/unit -q` clean.

**Work.** Delete the `TODO(doctrine P3)` block at `flows/poem_loop/prompts/shared/contracts.prompt:1-4` (comment mis-labels the phase as P3; the feature actually shipped as Doctrine P4). Doctrine's `typed_as:` attaches to `output_target_decl` only; the TODO site is a `workflow PoemLoopSystemContext` with prose bullets — no output target exists at that shape.

**Checklist (must all be done).**

- [x] Delete TODO comment block at `flows/poem_loop/prompts/shared/contracts.prompt:1-4`.
- [x] Append §10 Decision Log entry; anchor on G2 + grammar `output_target_typed_as_stmt` (`doctrine.lark:748-751`) + model `OutputTargetDecl.typed_as` (`_model/io.py:246-252`) + example 143 + workflow-vs-output-target rationale.

**Exit criteria (all required).**

- [x] `rg 'TODO\(doctrine' flows/poem_loop/prompts/shared/contracts.prompt` returns 0 matches.
- [x] `make emit` readback diff under `flows/poem_loop/build/**` is comment-removal only.
- [x] `uv run pytest tests/unit -q` clean.
- [x] §10 entry present and anchored per research-reads-source rule.

## Phase 4 — Retire the P5 skill-mode TODO

**Status: COMPLETE (2026-04-20)** — TODO block deleted; §10 entry appended; `make emit` + `uv run pytest tests/unit -q` clean.

**Work.** Delete the `TODO(doctrine P6)` block at `flows/software_engineering_demo/prompts/AGENTS.prompt:107-110` (comment mis-labels the phase as P6; skill `mode:` actually shipped as Doctrine P5). `mode:` governs call pattern (producer / audit / readonly per SkillMode enum); Rally's `requirement: Required | Advisory` governs frequency. The two concepts are orthogonal. `RepoWorkSkills` entries are all producer-shape — no audit-pattern skill exists at this site, so the adoption decision is "no adoption here" (G4 user confirmation gates Decision Log anchoring only).

**Checklist (must all be done).**

- [x] Delete TODO comment block at `flows/software_engineering_demo/prompts/AGENTS.prompt:107-110`.
- [x] Append §10 Decision Log entry; anchor on G4 + grammar `mode_stmt` (`doctrine.lark:706-713`) + model `SkillEntry.mode` (`_model/workflow.py:57-63`) + example 144 + SkillMode enum + orthogonality-to-`requirement:` rationale + all-producer-shape RepoWorkSkills fact.

**Exit criteria (all required).**

- [x] `rg 'TODO\(doctrine' flows/software_engineering_demo/prompts/AGENTS.prompt` returns only the remaining line-146 TODO (Phase 5 target).
- [x] `make emit` readback diff under `flows/software_engineering_demo/build/**` is comment-removal only.
- [x] `uv run pytest tests/unit -q` clean.
- [x] §10 entry present and anchored per research-reads-source rule.

## Phase 5 — Retire the P6 typed-abstract-parameter TODOs

**Status: COMPLETE (2026-04-20)** — both TODO blocks deleted; §10 entry appended; `make emit` + `uv run pytest tests/unit -q` clean.

**Work.** Delete both `TODO(doctrine P5)` blocks (the comment numbering is legacy Rally-local pre-split; typed abstract params actually shipped as Doctrine P6). `se_demo/AGENTS.prompt:146-149` and `poem_loop/AGENTS.prompt:153-156` both mark abstract agents whose descendants uniformly bind the same slots to the same values — zero per-descendant typed variation in either flow. Doctrine P6 is for per-descendant typed variation, not uniform binding.

**Checklist (must all be done).**

- [x] Delete TODO comment block at `flows/software_engineering_demo/prompts/AGENTS.prompt:146-149`.
- [x] Delete TODO comment block at `flows/poem_loop/prompts/AGENTS.prompt:153-156`.
- [x] Append §10 Decision Log entry covering both sites; anchor on G5 + grammar `agent_slot_abstract` (`doctrine.lark:168`) + model `AuthoredSlotAbstract.declared_type` (`_model/agent.py:21-24`) + example 145 (`TypedPolicyReviewer`) + uniform-binding-across-descendants rationale for each flow.

**Exit criteria (all required).**

- [x] `rg 'TODO\(doctrine' flows/software_engineering_demo/prompts/AGENTS.prompt flows/poem_loop/prompts/AGENTS.prompt` returns 0 matches.
- [x] `make emit` readback diffs for both flows are comment-removal only.
- [x] `uv run pytest tests/unit -q` clean.
- [x] §10 entry present and anchored per research-reads-source rule.

## Phase 6 — Retire the P7 rule-primitive TODO

**Status: COMPLETE (2026-04-20)** — TODO block deleted; §10 entry appended; `make emit` + `uv run pytest tests/unit -q` clean.

**Work.** Delete the `TODO(doctrine P7)` block at `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77-79`. Doctrine P7 `rule` is a compile-time safeguard (closed scope `{agent_tag / flow / role_class / file_tree}`, closed assertions `{requires inherit / forbids bind / requires declare}`, validated by RULE001-RULE005). The four `RallyManagedSharedRules` bullets are runtime turn instructions (ledger file location, note discipline, turn-ending JSON, routing placement) — none map to inheritance / binding / declaration invariants.

**Checklist (must all be done).**

- [x] Delete TODO comment block at `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77-79`.
- [x] Append §10 Decision Log entry; anchor on G6 + grammar (`doctrine.lark:86-104`) + validator RULE001-RULE005 + example 146 (`rule ComposersCheckUpstream`) + runtime-turn-instruction vs compile-time-invariant rationale.

**Exit criteria (all required).**

- [x] `rg 'TODO\(doctrine' stdlib/rally/prompts` returns 0 matches.
- [x] `make emit` readback diff across every flow that consumes the shared base agent is comment-removal only.
- [x] `uv run pytest tests/unit -q` clean.
- [x] §10 entry present and anchored per research-reads-source rule.

## Phase 7 — Delete three skill-site TODOs + refresh adjacent Rally docs + repair stale-anchor prose

**Status: COMPLETE (2026-04-20, audit pass 2)** — three skill TODO blocks deleted; this plan's own stale-anchor prose repaired (TL;DR, §1.4, §2.1, §10 all cite fold-forward destinations or `git:` anchors); V5 adoption-audit prose rewritten past-tense with 2026-04-20 Update block; V5 adoption-audit Closure Status rows F-9..F-13 all read `Retired 2026-04-20` with grammar/model/validator/example anchors; and V5 adoption-audit line 38 now carries the required `git:` anchor on the retired Doctrine closure plan.

**Audit trail (previously reopened, now resolved):**
- V5 adoption audit lines 404-406: present-tense prose rewritten as past-tense historical ("were originally left as typed comment markers") with a 2026-04-20 Update block at line 408 describing the post-adoption tree.
- V5 adoption audit lines 420-424: Closure Status rows F-9..F-13 all show `Retired 2026-04-20`; F-10 no longer claims "Three skills carry `# TODO(doctrine F-6):`".
- V5 adoption audit line 38: now reads `git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md (retired 2026-04-20 via Doctrine commit 8c3701a; fold-forward canonical surfaces are ...)` — matches the form in this plan's `related:` frontmatter and §3.1.

**Work.** Close out the three skill-site TODOs that pointed at an unshipped Doctrine scalar/env-var/path host-slot family (concept was filed as a Doctrine-side request and retired same-day: commits `d629ded` → `76011f2`; current v5 `host_contract:` slot families are `{input / output / document / analysis / schema / table / final_output / receipt}`). Then refresh the two neighboring Rally adoption docs so their forward findings for P5/P6/P7 and F-6 match the post-adoption tree. Finally repair this plan's own TL;DR / §1.4 / §2.1 / §10 prose so it stops citing retired Doctrine docs as if they were live (replace live refs with fold-forward destinations already listed in the plan's `related:` frontmatter + `git:` anchors for the two retired Doctrine docs).

**Checklist (must all be done).**

- [x] Delete TODO comment blocks at `skills/demo-git/prompts/SKILL.prompt:10-12`, `skills/rally-kernel/prompts/SKILL.prompt:18-21`, `skills/rally-memory/prompts/SKILL.prompt:20-23`.
- [x] Update `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` forward findings F-9..F-13 + any F-6 forward-finding to post-adoption tree (note P6/P7 shipped 2026-04-20, TODOs retired per this plan, F-6 concept retired on the Doctrine side via `d629ded` → `76011f2`).
- [x] Update `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` cross-references to match post-adoption tree.
- [x] Repair this plan's own TL;DR / §1.4 / §2.1 / §10 prose: replace live citations of the retired Doctrine closure plan and scalar-host-slot request with fold-forward destinations (LANGUAGE_REFERENCE.md / COMPILER_ERRORS.md / examples/140-146) and `git:` anchors for historical Doctrine surfaces.
- [x] Re-verify the already-drafted 2026-04-20 §10 entry ("Retire the three skill-site TODOs pointing at an unshipped Doctrine host-slot concept") anchors on Doctrine commits `d629ded` → `76011f2` + v5 `host_contract:` slot family list per G1.

**Exit criteria (all required).**

- [x] `rg 'TODO\(doctrine' flows stdlib skills` returns 0 matches across the whole tree.
- [x] Neither `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` nor `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` still cites the retired Doctrine docs without `git:` anchors, and both describe the post-adoption tree. (V5 adoption-audit line 38 now reads `git:../../doctrine@8c3701a^:docs/DOCTRINE_LANGUAGE_GAPS_ELEGANT_CLOSURE_PLAN_2026-04-19.md` with fold-forward-destination parenthetical; V5 exemplar plan's own `TODO(doctrine …)` mentions are inside historical Phase 8 / Decision Log prose, consistent with the TL;DR note at line 32 that describes that Phase 8 work as retired by this plan.)
- [x] This plan's TL;DR / §1.4 / §2.1 / §10 prose no longer cites retired Doctrine docs as live references without `git:` anchors.
- [x] `make emit` readback diff under `skills/*/build/**` is comment-removal only; no flow-side readback drift.
- [x] `uv run pytest tests/unit -q` clean.
- [x] §10 entry for the three skill-site retirements is anchored per research-reads-source rule.

<!-- arch_skill:block:phase_plan:end -->

---

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Unit tests (contracts)

- `uv run pytest tests/unit -q` at the Rally repo root after every `.prompt` or `stdlib` edit.

## 8.2 Integration tests (flows)

- Recompile each touched flow's readback via the Rally-paired Doctrine compiler. Inspect `flows/*/build/**` after recompile; the only expected diff is TODO-comment removal or rewording. No semantic prompt drift.

## 8.3 E2E / device tests (realistic)

- Not required. Rally flow behavior is not meant to change.

---

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout plan

- Local-only, on `feat/doctrine_v5_adoption_on_perf`. No push, no PR, no release.

## 9.2 Telemetry changes

- None.

## 9.3 Operational runbook

- None required. The plan does not touch runtime.

---

# 10) Decision Log (append-only)

## 2026-04-20 - Retire the three skill-site TODOs pointing at an unshipped Doctrine host-slot concept

**Context.** Three skill prompts (`skills/demo-git/prompts/SKILL.prompt`, `skills/rally-kernel/prompts/SKILL.prompt`, `skills/rally-memory/prompts/SKILL.prompt`) carried TODO comments referencing a Doctrine host-slot concept for scalar / env-var / path facts the host runtime supplies at install time. That concept was never in the Doctrine closure plan and was never a shipped or planned Doctrine phase — it was invented in Rally's exemplar-adoption audit as a forward-finding.

**Options.**
1. Keep the three TODOs as "forward markers" in Rally skill prompts.
2. Delete the three TODOs from Rally and file a Doctrine-side feature request doc that names the three skill sites and the WHY/WHAT of the ask.

**Decision.** Option 2. Rally does not carry forward markers for unshipped Doctrine features. Those markers drift into stale vocabulary faster than they earn their keep — the original wording ("F-6") already used numbering that never matched any shipped or planned Doctrine phase. The concept was filed on the Doctrine side as `SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md` (Doctrine commit `d629ded`) and retired same-day in commit `76011f2`; the request named the three Rally skill sites explicitly and is reachable via `git:../../doctrine@d629ded:docs/SCALAR_HOST_SLOT_FAMILY_REQUEST_2026-04-20.md`. Current v5 `host_contract:` slot families remain `{input / output / document / analysis / schema / table / final_output / receipt}` — no scalar/env-var/path family.

**Grounding (per enduring research-reads-source rule).** Grammar surface for `host_contract:` slot families lives in `../doctrine/doctrine/grammars/doctrine.lark` (`host_contract_body_line` production); model shape lives in `../doctrine/doctrine/_model/host_contract.py`. Neither surface has a scalar/env-var/path slot family — confirmed by reading both on 2026-04-20. The request-and-retire commit pair `d629ded` → `76011f2` is the authoritative historical record.

**Consequences.** Rally contains zero `TODO(doctrine …)` comments after this plan. If Doctrine declines the feature permanently, Rally has lost the in-tree reminder of the three sites that wanted it — but the retired request preserves that information in git history. If Doctrine ships the feature in some future closure plan, Rally will adopt it organically when it next touches those skills.

**Follow-ups.** Phase 7 of this plan deletes the three comment blocks and refreshes `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` and `docs/RALLY_DOCTRINE_V5_ADOPTION_AUDIT_2026-04-19.md` so any forward-finding that referenced the concept is retired with a pointer to the Doctrine `git:` anchor.

## 2026-04-20 - Expand scope from Doctrine P2-P5 to P2-P7 after P6/P7 shipped

**Context.** Original draft of this plan (2026-04-19) scoped to Doctrine closure-plan Phases 2-5, which were the shipped phases at that time. Phases 6 (typed abstract-agent parameters) and 7 (declarative `rule` primitive) both shipped on 2026-04-20 per the Doctrine closure plan's `Status: COMPLETE (2026-04-20)` lines at Phase 6 and Phase 7 — after the plan was drafted but before execution began.

**Options.**
1. Execute the original P2-P5 plan, defer P6/P7 adoption to a second plan.
2. Expand scope in place to cover P2-P7; rename the doc; update TL;DR, Section 0, Section 3.3, Section 5, Section 6, and Section 7.

**Decision.** Option 2. Rally has direct TODO markers for both P6 (typed abstract parameters, two sites) and P7 (rule primitive, one site). Deferring means leaving three TODO markers pointing at now-shipped features, which contradicts the plan's falsifiable claim that no surviving TODO refers to a shipped phase without rationale.

**Consequences.** Plan grows from 6 phases to 7. Phase count and Decision Log entries expand. Filename changed from `RALLY_DOCTRINE_P2_TO_P5_ADOPTION_AUDIT_2026-04-19.md` to `RALLY_DOCTRINE_P2_TO_P7_ADOPTION_AUDIT_2026-04-19.md`.

**Follow-ups.** Delete the old filename. Check `docs/RALLY_DOCTRINE_V5_EXEMPLAR_ADOPTION_PLAN_2026-04-19.md` Phase-8 references and forward findings F-9 through F-13 during Phase 7 refresh.

## 2026-04-19 - Scope this plan to TODO markers, not framework sweep

**Context.** Doctrine shipped a broad run of language features in a short window. Rally could in principle adopt them across the tree wherever they fit.

**Options.**
1. Sweep every Rally `.prompt` file for all possible adoption sites of P2-P7.
2. Audit only the sites that already carry `TODO(doctrine …)` markers and render per-site verdicts.

**Decision.** Option 2. The TODO markers are the prior authors' explicit adoption candidates; a sweep beyond them would invent scope.

**Consequences.** Some Doctrine features may be lightly under-adopted in Rally after this plan. That is acceptable and documented here.

**Follow-ups.** If a future Rally change organically lands on a site where one of these Doctrine features fits, adopt it then, one site at a time.

## 2026-04-19 - Reject restructuring software_engineering_demo reviews into a shared contract

**Context.** `flows/software_engineering_demo/prompts/shared/review.prompt` has three separate reviews (ArchitectReview, DeveloperReview, QaReview) with distinct gate sets. A TODO suggests they could collapse via `override gates:`.

**Options.**
1. Collapse into one shared contract and override gates per case.
2. Leave the three separate schemas and retire the TODO.

**Decision.** Option 2. The three reviews have genuinely different gates; forcing them through one contract would bury real semantic difference under override churn.

**Consequences.** Doctrine P2 `override gates:` has no adoption site in software_engineering_demo after this plan.

**Follow-ups.** None.

## 2026-04-20 - Reject Doctrine P6 adoption at poem_loop and software_engineering_demo abstract agents

**Context.** `PoemLoopRole` and `SoftwareEngineeringRole` each declare three slot keys (`system_context`, `ground_truth`/`issue_truth`, `primary_path`/`repo_rules`) and bind concrete values at the abstract agent level. Every descendant inherits those bindings unchanged. Doctrine P6 ships typed abstract parameters as `abstract NAME: TypeRef` on the abstract agent, with descendants binding via `name_ref` of the declared type family.

**Options.**
1. Restructure: move the three bindings out of each abstract agent, declare them as typed abstract slots on the abstract, have every concrete descendant restate the binding. Gain: type checking on the slot family. Cost: ceremony across four poem_loop descendants and six software_engineering_demo descendants, for values that are the same everywhere.
2. Retire both TODOs. Keep the shared-binding pattern as is. Document that Doctrine P6 applies when descendants need **different** typed bindings; Rally's sites do not.

**Decision.** Option 2.

**Consequences.** Doctrine P6 typed abstract parameters have no adoption site in Rally after this plan. If a future flow has a genuine per-descendant variation, adopt P6 then.

**Follow-ups.** None.

## 2026-04-20 - Reject Doctrine P7 adoption for RallyManagedSharedRules

**Context.** `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:80-86` declares `RallyManagedSharedRules` as a `workflow` with `bullets rules:` prose. Those bullets are runtime-turn instructions for every Rally-managed agent: "Use `home:issue.md` as the shared ledger", "End the turn with the final JSON this turn declares", and so on. The existing `TODO(doctrine P7)` comment imagines lifting each bullet into a typed `rule` declaration.

Doctrine P7 shipped with a **closed** predicate surface. Scope predicates: `agent_tag`, `flow`, `role_class`, `file_tree`. Assertion predicates: `requires inherit <EntityRef>`, `forbids bind <SkillRef>`, `requires declare <SlotName>`. Diagnostics: RULE001-RULE005. The primitive is compile-time-only.

**Options.**
1. Adopt by expressing a loose mapping of the runtime rules to compile-time assertions (for example, `requires inherit RallyManagedSharedRules`). This does not actually lift the runtime bullets; it only enforces that every managed agent inherits the workflow that carries them. That enforcement is already structural (the base agent is the only managed agent shape), so the rule adds ceremony, not teeth.
2. Retire the TODO. Keep the workflow prose where it is. Document that Doctrine P7 is compile-time-only for inheritance / binding / declaration invariants; Rally's runtime rules are a different thing entirely.

**Decision.** Option 2.

**Consequences.** Doctrine P7 has no adoption site in Rally after this plan. Rally's runtime-turn rules keep their workflow prose home.

**Follow-ups.** If Rally later wants compile-time enforcement of a structural invariant (for example, "every managed agent must inherit `RallyManagedSharedRules`" as a safeguard against accidental bypass), adopt P7 then, at the specific invariant site. Such adoption is out of scope for this plan's TODO-audit charter.

## 2026-04-20 - Retire both P2 override-gates TODOs (Phase 2)

**Context.** Two `TODO(doctrine P2)` comment blocks anticipated adopting Doctrine P2 `override gates:` on `review_case` once it shipped. Doctrine P2 shipped 2026-04-19 (E531/E532, example 141). Neither Rally site has the shape P2 targets.

**Grounding (per enduring research-reads-source rule).**
- Grammar: `review_case_gates_override_block` at `../doctrine/doctrine/grammars/doctrine.lark:235-248` — attaches to `review_case` under a multi-case `review_family` with a **shared** contract.
- Model: `ReviewCase` carries the override block; concrete single-declaration `review` has no case axis.
- Validator: E531 (removed gate not declared), E532 (added gate already declared) — both presume a shared-contract gate set to narrow.
- Example 141 (`141_review_case_gate_override`): two cases under one family override shared gate copy.

**Per-site repo evidence.**
- `flows/poem_loop/prompts/shared/review.prompt:69` — a single concrete `review PoemReview` (not a family, not multi-case). Nothing to narrow.
- `flows/software_engineering_demo/prompts/shared/review.prompt:122` — three reviews (`ArchitectReview`, `DeveloperReview`, `QaReview`) with fully distinct `schema` contracts (`ArchitectReviewContract`, `DeveloperReviewContract`, `QaReviewContract`) and distinct gate name sets (`issue_understood` vs `requested_change_present` vs `requirements_met`). There are no shared gate copies to override; collapsing the three into one shared contract would bury genuine semantic difference.

**Options.**
1. Restructure poem_loop to a multi-case family (manufactures ceremony without a second case) and/or collapse se_demo's three reviews into one (destroys semantic distinction).
2. Retire both TODOs.

**Decision.** Option 2.

**Consequences.** Doctrine P2 has no adoption site in Rally after this plan.

**Follow-ups.** If Rally ever ships a second `PoemReview` variant that genuinely shares most gates with the first, or introduces a review family whose members share gate copies, adopt P2 then.

## 2026-04-20 - Retire P4 typed_as TODO on workflow prose (Phase 3)

**Context.** `flows/poem_loop/prompts/shared/contracts.prompt:1` carried `TODO(doctrine P3)` hoping `typed_as:` could lift workflow prose bullets into a shared vocabulary. Doctrine `typed_as:` actually shipped as Phase 4 on 2026-04-20 (E533/E534, example 143); the comment's "P3" label predates the closure-plan split.

**Grounding (per enduring research-reads-source rule).**
- Grammar: `output_target_typed_as_stmt` at `../doctrine/doctrine/grammars/doctrine.lark:748-751` — attaches to `output_target_decl`, nothing else.
- Model: `OutputTargetDecl.typed_as` at `../doctrine/doctrine/_model/io.py:246-252` — typed identity on output targets only.
- Validator: E533 (typed_as target not `document`/`schema`/`table`), E534 (required typed_as missing).
- Example 143 (`143_typed_handoff_note_identity`): `output ReleaseNote: target: … shape: MarkdownDocument structure: … typed_as: shared.handoff.ReleaseNoteDocument`.

**Per-site repo evidence.** `PoemLoopSystemContext` at that line is a `workflow` with prose bullets — no `output_target_decl` exists at the TODO site. Doctrine P4 has no attachment point there.

**Options.**
1. Extend Doctrine P4 to attach `typed_as:` to workflow prose bullets (out of scope; requires Doctrine change).
2. Retire the TODO.

**Decision.** Option 2.

**Consequences.** Doctrine P4 adopts naturally at future Rally `output_target_decl` sites as those appear; no retroactive workflow-prose adoption.

## 2026-04-20 - Retire P5 skill-mode TODO at RepoWorkSkills (Phase 4)

**Context.** `flows/software_engineering_demo/prompts/AGENTS.prompt:107` carried `TODO(doctrine P6)` hoping skill-entry `mode:` could replace Rally's `requirement: Required | Advisory`. Doctrine skill `mode:` actually shipped as Phase 5 on 2026-04-19 (E540-E543, E543 fatal; example 144); the comment's "P6" label predates the closure-plan split.

**Grounding (per enduring research-reads-source rule).**
- Grammar: `mode_stmt` at `../doctrine/doctrine/grammars/doctrine.lark:706-713` — `"mode" CNAME "=" expr "as" name_ref` inside `skill_entry_body_line`.
- Model: `SkillEntry(key, target, items, binds, mode: ModeStmt | None, source_span)` at `../doctrine/doctrine/_model/workflow.py:57-63`.
- Validator: E540 (unknown mode binding), E543 (enum-only output-shape selector — fatal).
- Example 144 (`144_skill_binding_producer_audit_mode`): demonstrates producer + audit + readonly SkillMode enum cases.
- SkillMode enum: `{producer, audit, readonly}` govern **call pattern** — producer builds an artifact; audit checks someone else's work; readonly never writes.

**Orthogonality fact.** Doctrine `mode:` governs call pattern. Rally's `requirement: Required | Advisory` governs frequency (must-use vs may-use). The TODO's "replace `requirement:` with `mode:`" framing conflates two orthogonal concepts.

**Per-site repo evidence.** `RepoWorkSkills` (AGENTS.prompt:111-120) has three entries — `rally_kernel` (Required), `demo_git` (Required), `repo_search` (Advisory) — all producer-shape; no audit-pattern or readonly-pattern skill at the site. Adopting `mode:` here would write `mode = producer` on every entry, which is zero information.

**Options.**
1. Annotate every entry with `mode = producer` (ceremony; zero semantic content).
2. Retire the TODO.

**Decision.** Option 2.

**Consequences.** Doctrine P5 `mode:` has no adoption site in Rally's current skill-binding surfaces. `requirement:` keeps its frequency role.

**Follow-ups.** If Rally ships an audit-shape skill that validates a producer's artifact (a "checker" skill that never writes product output), adopt P5 `mode:` then, at that specific audit entry.

## 2026-04-20 - Retire both P6 typed-abstract-parameter TODOs (Phase 5)

**Context.** Two `TODO(doctrine P5)` comment blocks anticipated adopting typed abstract parameters on abstract agents once they shipped. Doctrine typed abstract params actually shipped as Phase 6 on 2026-04-20 (E538/E539, example 145); the comments' "P5" label predates the closure-plan split. Neither Rally site has the shape P6 targets.

**Grounding (per enduring research-reads-source rule).**
- Grammar: `agent_slot_abstract` with optional `: name_ref` at `../doctrine/doctrine/grammars/doctrine.lark:168`.
- Model: `AuthoredSlotAbstract.declared_type: NameRef | None` at `../doctrine/doctrine/_model/agent.py:21-24`.
- Validator: E538 (inline-block binding on typed slot), E539 (wrong-family binding).
- Example 145 (`145_abstract_agent_typed_parameters`): `TypedPolicyReviewer` declares `abstract policy: AccuracyPolicy`; `AccuracyReviewer` binds `AccuracyPolicy`; `ToneReviewer` binds `TonePolicy`. The benefit is per-descendant typed variation.

**Per-site repo evidence.**
- `flows/poem_loop/prompts/AGENTS.prompt:153` — `PoemLoopRole` has three descendants (`Muse`, `Critic`, `Editor`), all of which bind `system_context: PoemLoopSystemContext`, `ground_truth: IssueLedgerGroundTruth`, `primary_path: PrimaryPathRules`. Zero per-descendant variation.
- `flows/software_engineering_demo/prompts/AGENTS.prompt:146` — `SoftwareEngineeringRole` has six descendants, all of which bind `system_context: SoftwareEngineeringSystemContext`, `issue_truth: IssueLedgerGroundTruth`, `repo_rules: DemoRepoRules`. Zero per-descendant variation.

Typed parameters deliver value when descendants need **different** typed bindings for the same abstract slot. Uniform binding means typed parameters add ceremony without benefit.

**Options.**
1. Add `: TypeRef` annotations on every abstract slot (ceremony; every descendant still binds the same value).
2. Retire both TODOs.

**Decision.** Option 2.

**Consequences.** Doctrine P6 has no adoption site in Rally's current abstract-agent surfaces.

**Follow-ups.** If a future Rally flow introduces descendants that bind **different** typed values for the same abstract slot (e.g., per-role policy objects), adopt P6 then.

## 2026-04-20 - Retire P7 rule-primitive TODO on RallyManagedSharedRules (Phase 6)

**Context.** `stdlib/rally/prompts/rally/base_agent/AGENTS.prompt:77` carried `TODO(doctrine P7)` hoping the `rule` primitive could lift the four runtime-turn bullets in `RallyManagedSharedRules` into typed rules. Doctrine P7 shipped 2026-04-20 (RULE001-RULE005, example 146) as a compile-time safeguard for inheritance / binding / declaration invariants — a categorically different thing from runtime-turn behavior.

**Grounding (per enduring research-reads-source rule).**
- Grammar: `rule_decl` at `../doctrine/doctrine/grammars/doctrine.lark:86-104` — closed scope set `{agent_tag / flow / role_class / file_tree}`, closed assertion set `{requires inherit / forbids bind / requires declare}`, required `message: string`.
- Validator: `../doctrine/doctrine/_compiler/validate/rules.py` runs RULE001 (scope target unresolved), RULE002 (assertion target unresolved), RULE003-RULE005 at compile time. `RULE006-RULE099` are reserved for future closed-predicate additions; `RULE100+` reserved for open-expression rules.
- Example 146 (`146_declarative_project_lint_rule`): `rule ComposersCheckUpstream … requires inherit UpstreamPoisoningInvariant`. The intended use is compile-time structural safeguard.

**Per-site repo evidence.** `RallyManagedSharedRules` carries four bullets:
1. "Use `home:issue.md` as the shared ledger for this run." — runtime path convention.
2. "Leave one short saved note through `Saved Run Note` only when later readers need it." — runtime note-discipline.
3. "End the turn with the final JSON this turn declares." — runtime turn-end.
4. "Keep routing, `done`, `blocker`, and `sleep` in final JSON, not in notes." — runtime routing placement.

None of the four are inheritance, binding, or declaration invariants. They are all instructions about what the agent does **at turn execution time**, which Doctrine P7 has no vocabulary to express (and is not the problem P7 solves).

**Options.**
1. Adopt with a weak mapping (`requires inherit RallyManagedSharedRules`) — enforces structural inheritance but does not lift runtime bullets; redundant since the base agent is the only managed-agent shape.
2. Retire the TODO.

**Decision.** Option 2.

**Consequences.** Doctrine P7 has no adoption site in Rally after this plan. Rally's runtime-turn rules keep their workflow prose home.

**Follow-ups.** If Rally later wants compile-time enforcement of a structural invariant (e.g., "every managed agent must inherit `RallyManagedSharedRules`" as a safeguard against accidental bypass), adopt P7 then, at that specific invariant site. Out of scope for this TODO-audit charter.
