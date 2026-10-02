---
title: "Rally + Doctrine - GitHub Conversion Maximization - Architecture Plan"
date: 2026-04-13
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: [aelaguiz]
doc_type: phased_refactor
related:
  - ../README.md
  - RALLY_MASTER_DESIGN_2026-04-12.md
  - research/RALLY_DOCTRINE_MARKET_LANDSCAPE_AND_POSITIONING_2026.md
  - research/RALLY_DOCTRINE_COMPETITIVE_DIFFERENTIATION.md
  - research/OPEN_SOURCE_GROWTH_PLAYBOOK_2026.md
  - ../../doctrine/README.md
  - ../../doctrine/docs/README.md
---

# TL;DR

- Outcome: Turn `rally` and `doctrine` into a sharp two-repo GitHub funnel that wins attention fast, explains the split clearly, and converts serious visitors into stars, follows, issues, discussions, installs, and contributor actions.
- Problem: Both repos already have strong technical truth, but their GitHub surfaces still read more like architecture notes than high-conversion open source products. The story is there, the proof is deeper than the landing pages show, and the funnel is weak.
- Approach: Use the research in `docs/research/` plus the current repo truth to rewrite both repos around one simple split: Doctrine is the authoring and compiler layer; Rally is the runtime and harness layer. Then rebuild the public surfaces, current proof-asset usage, GitHub metadata, launch copy, and founder-proof packaging around that split, while pulling forward the best buried proof: Codex support, Claude Code support, repo-local searchable memory, MCP handling, the Doctrine visualizer, and the VS Code extension.
- Plan: Lock positioning, CTA ladders, founder-proof usage, homepage policy, and proof-asset scope first, then rewrite README and docs surfaces, then sync GitHub-native conversion paths, then ship a coordinated launch pack that I can execute directly with repo edits and `gh`.
- Non-negotiables: No fake claims. No vague "agent platform" language. No conflict between Rally and Doctrine positioning. No founder chest-thumping without proof. No shipping-status lies, especially around adapters. No plan items that depend on new product features, a new website, or work outside surfaces I can directly change.

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-13
external_research_grounding: not started
deep_dive_pass_2: done 2026-04-13
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

If I reshape both GitHub repos around a clear two-layer story, proof-first landing pages, and GitHub-native conversion paths, then a new technical visitor should be able to understand the product split, see credible proof, and take a meaningful next action without needing outside explanation.

## 0.2 In scope

- Rewrite the GitHub-facing copy and structure for `rally` and `doctrine`.
- Tighten README, docs index, demo framing, comparison framing, quickstart flow, and contribution paths in both repos.
- Reuse and reposition the current proof assets that already ship in these repos. Do not add a new proof-asset track in this first pass.
- Update GitHub repo metadata and other GitHub-owned surfaces that I can change with `gh`, such as descriptions, homepages, topics, labels, issues, discussions, and release copy.
- Create coordinated launch copy and distribution packs that stay grounded in shipped repo truth.
- Do the internal docs cleanup needed to stop the public story from splitting across too many overlapping files.
- Package founder and operator credibility that is already externally supportable, including Cratejoy, Y Combinator, MarketZero, Zynga, PokerSkill / Fun Country, and the broader `aelaguiz` GitHub repo arc.
- Package the strongest shipped product fodder that is currently buried: `codex`, `claude_code`, repo-local searchable memory backed by QMD, allowlisted MCP handling, Doctrine workflow diagrams, and the Doctrine VS Code extension.

## 0.3 Out of scope

- New runtime or compiler features that do not already exist.
- A new website, app, hosted product, or paid campaign outside GitHub and repo-owned content.
- Any claim that needs new benchmarks, new infra, or new product work before it can be made honestly.
- Community work that depends on people outside this workspace doing follow-up before the funnel works.

## 0.4 Definition of done (acceptance evidence)

- Both repos have a clear first-screen promise, clear proof, a clean quickstart, and a clear next action.
- Rally and Doctrine cross-link cleanly without blurring their jobs.
- GitHub metadata for both repos matches the new positioning.
- Public copy, examples, and proof assets only make claims supported by shipped docs, code, or runnable demos.
- The main GitHub conversion path for each repo can be followed in under one minute by a new technical reader.
- A new technical visitor can also see, fast, why this founder is credible to build this stack.
- A new technical visitor can see, fast, that Rally already has real adapter and memory depth instead of just roadmap talk.
- The launch pack exists in-repo and can be executed directly from owned GitHub and social surfaces.

## 0.5 Key invariants (fix immediately if violated)

- No invented product claims.
- No duplicate or conflicting positioning between Rally and Doctrine.
- No new parallel public stories when one repo should own the message.
- No silent drift between README copy, docs copy, repo metadata, and shipped behavior.
- No fallback marketing fluff. If the current product cannot prove a claim, the claim does not ship.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Grab attention in the first screen.
2. Convert that attention into a deliberate GitHub action.
3. Make the Doctrine and Rally split obvious and useful.
4. Lead with proof instead of promises.
5. Use founder and operator history as earned-right proof, not vanity.
6. Only plan work I can execute directly from the repos and GitHub.
7. Pull forward the strongest shipped proof before adding any new narrative.

## 1.2 Constraints

- The repos must stay technically honest.
- The current product shape is the hard limit for public claims.
- GitHub is the main funnel surface for this plan.
- Work should prefer copy, docs, assets, metadata, and GitHub workflow changes over new product code.
- Founder claims must stay tied to official, public, or brain-grounded evidence.
- The current public README underuses or lags some live proof surfaces, so packaging work must reconcile the public story with shipped repo truth.

## 1.3 Architectural principles (rules we will enforce)

- Doctrine owns the source-authoring and compiler story.
- Rally owns the runtime, harness, and run-home story.
- Each repo gets one main promise and one main CTA ladder.
- Above-the-fold copy must explain value before deep detail.
- Proof beats abstraction in every public surface.
- Founder story only ships where it increases trust, speed, or earned right.
- Internal implementation names only ship in public copy when they help. Lead with user value first, then name things like QMD deeper in the proof ladder.

## 1.4 Known tradeoffs (explicit)

- Sharper positioning will likely narrow the audience, but it should raise conversion with the right audience.
- Moving deep design detail below the fold may reduce instant depth, but it should improve first-minute clarity.
- GitHub optimization is not a full growth system, but it is the highest-leverage surface I can directly control here.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

Both repos already have real technical depth, working commands, and strong architecture docs. Rally already states a strong runtime philosophy and shows a live demo image. Doctrine already shows the authoring-versus-runtime split clearly and has a stronger docs index. The code and docs also show more support surface than the current landing copy exploits: Rally has real `codex` and `claude_code` adapters, real repo-local searchable memory, and real MCP handling; Doctrine has real emit, flow visualization, and VS Code extension proof.

## 2.2 What’s broken / missing (concrete)

The GitHub landing path still asks too much from the reader. The core story is present, but it is not yet packed into a tight attention and conversion funnel. There is not yet a fully deliberate first-screen hook, CTA ladder, comparison capture, GitHub-native engagement setup, or shared cross-repo story that turns Doctrine and Rally into one simple system in the reader's head. There is also a second missed asset: the repos underuse founder credibility that is already publicly supportable. There is a third missed asset too: the public story underuses shipped product proof and in at least one case still talks in future tense where the repo already has real support.

## 2.3 Constraints implied by the problem

- Fixes must come from copy, structure, proof packaging, metadata, and GitHub surface work.
- The plan must respect the current shipped product truth.
- The two repos must feel linked, but not merged or confusing.

<!-- arch_skill:block:research_grounding:start -->
# 3) Research Grounding (external + internal “ground truth”)

## 3.1 External anchors (papers, systems, prior art)

- `docs/research/OPEN_SOURCE_GROWTH_PLAYBOOK_2026.md` — adopt proof-first
  README structure, copy-paste quickstarts, comparison framing, GitHub topics,
  and GitHub-native engagement paths; reject architecture-note landing pages as
  the main public funnel.
- `docs/research/RALLY_DOCTRINE_MARKET_LANDSCAPE_AND_POSITIONING_2026.md` and
  `docs/research/RALLY_DOCTRINE_COMPETITIVE_DIFFERENTIATION.md` — adopt a hard
  two-layer split: Doctrine is the authoring/compiler edge and Rally is the
  runtime/harness edge; reject vague umbrella "agent platform" language.
- `docs/research/AGENT_TOOL_POSITIONING_LANDSCAPE_APRIL_2026.md` — adopt
  sharper category language and fast proof surfaces; reject generic
  orchestration buzzwords as the main story.
- `docs/research/DOCTRINE_ARXIV_AND_OPEN_SOURCE_LAUNCH_PLAYBOOK.md` and
  `docs/research/RALLY_DOCTRINE_OPEN_SOURCE_GROWTH_STRATEGY_2026.md` — adopt
  paired launch packaging, visible proof assets, and one coordinated cross-repo
  story before broader distribution.
- Official Cratejoy and YC profile material plus the April 5, 2011 GamesBeat
  acquisition coverage — adopt these as second-layer founder-proof assets that
  earn trust fast; reject unsupported founder mythology or vanity-first copy.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors (do not reinvent):
  - `README.md` — current Rally public promise, current comparison framing, and
    the current mismatch where Claude Code support and repo-local memory are
    still described partly as future work.
  - `CONTRIBUTING.md` — current Rally contributor activation path and proof
    commands.
  - `src/rally/adapters/registry.py` — the one shipped adapter registry; today
    the supported adapter names are `codex` and `claude_code`.
  - `flows/poem_loop/flow.yaml` and `flows/software_engineering_demo/flow.yaml`
    — both shipped demo flows still default to `runtime.adapter: codex`.
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md` — current CLI contract, live
    `rally memory` commands, and the live Codex plus Claude Code runtime story.
  - `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md` — current repo-local
    searchable memory design and shipped proof for markdown-backed QMD memory.
  - `docs/RALLY_HERMES_ADAPTER_RUNTIME_GENERALIZATION_2026-04-13.md` — keeps
    the explicit truth that Hermes is not a shipped Rally adapter today.
  - `/Users/aelaguiz/workspace/doctrine/README.md` — current Doctrine public
    promise, authoring/compiler story, shipped emit proof, and workflow
    visualizer proof.
  - `/Users/aelaguiz/workspace/doctrine/docs/README.md` — the live Doctrine
    docs ladder and the repo rule that only shipped docs belong in the public
    path.
  - `/Users/aelaguiz/workspace/doctrine/editors/vscode/README.md` — the
    shipped VS Code extension proof surface.
  - `gh repo view aelaguiz/rally --json description,homepageUrl,repositoryTopics,hasDiscussionsEnabled,stargazerCount`
    — current Rally GitHub metadata surface: useful topics, public discussions
    enabled, homepage still set to `https://pokerskill.com`, and no star proof
    yet.
  - `gh repo view aelaguiz/doctrine --json description,homepageUrl,repositoryTopics,hasDiscussionsEnabled,stargazerCount`
    — current Doctrine GitHub metadata surface: good category terms, homepage
    still set to `https://pokerskill.com`, Discussions disabled, and early-star
    proof only.

- Canonical path / owner to reuse:
  - `README.md` in each repo — should own the first-contact promise, first
    proof strip, primary CTA ladder, and the sister-repo cross-link.
  - `CONTRIBUTING.md` in each repo — should own contributor activation after
    the README wins the click.
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md` and
    `/Users/aelaguiz/workspace/doctrine/docs/README.md` — should stay the deep
    technical proof and live docs ladder, not the main first-screen funnel.
  - `gh` repo metadata for `aelaguiz/rally` and `aelaguiz/doctrine` — should
    own descriptions, homepages, topics, and discussion surfaces that affect
    conversion before the README even loads.

- Existing patterns to reuse:
  - `docs/assets/poem-loop-demo-run.png` — fast Rally proof asset that already
    shows the real CLI and a real shipped flow.
  - `/Users/aelaguiz/workspace/doctrine/README.md` — already uses side-by-side
    source-versus-emitted-artifact proof and a visible workflow visualizer
    section that can be pulled higher in the funnel.
  - `/Users/aelaguiz/workspace/doctrine/docs/README.md` — already has a clean
    live-docs ladder that separates first-step docs from deeper reference.
  - `README.md` Rally sections such as `Where Rally Fits` and `What Ships
    Today` — already contain useful comparison and proof material that should be
    sharpened rather than replaced with a new narrative from scratch.

- Prompt surfaces / agent contract to reuse:
  - `src/rally/adapters/registry.py` plus the flow `runtime.adapter` fields —
    are the shipped capability contract that public copy must reflect honestly.
  - `/Users/aelaguiz/workspace/doctrine/README.md` plus Doctrine emit docs —
    already define the "author in `.prompt`, emit runtime Markdown existing
    coding-agent tools can read today" story; the plan should reuse that instead
    of inventing a new runtime claim.

- Native model or agent capabilities to lean on:
  - Rally already has a real Codex path and a real Claude Code path; the plan
    does not need hypothetical wrapper work to justify those claims.
  - Doctrine already emits `AGENTS.md`-style runtime Markdown for existing
    coding-agent tools; the public story can lean on that shipped bridge today.

- Existing grounding / tool / file exposure:
  - `gh` already gives full control over repo descriptions, topics, discussions,
    and other GitHub-owned surfaces this plan can execute directly.
  - The checked-in READMEs, docs, demo assets, and emitted proof artifacts are
    already enough to build a stronger funnel without new product work.
  - `docs/research/*`, public founder sources, the visible `aelaguiz` GitHub
    account, and GBrain company pages already provide the raw material for
    founder-proof and continuity packaging.

- Duplicate or drifting paths relevant to this change:
  - Rally README status text underclaims shipped `claude_code` support and
    shipped repo-local searchable memory relative to current code and docs.
  - The strongest proof surfaces are scattered across READMEs, deep docs,
    worklogs, source files, and repo metadata instead of laddered into one fast
    public path.
  - Both repos currently point their GitHub homepage to
    `https://pokerskill.com`, which does not yet act like a repo-specific CTA
    surface.
  - Rally has Discussions enabled while Doctrine does not, which creates an
    asymmetric GitHub conversion surface for the paired story.
  - Founder proof and adjacent-repo continuity proof currently live outside the
    repo funnel instead of inside it.

- Capability-first opportunities before new tooling:
  - Pull shipped adapter, memory, emit, visualizer, and editor proof into the
    landing path before inventing new benchmark or demo systems.
  - Reuse checked-in screenshots, emitted artifacts, and docs ladders before
    building a new website or extra design surface.
  - Use `gh`-managed metadata and GitHub-native engagement paths before adding
    off-platform launch machinery.

- Behavior-preservation signals already available:
  - `gh repo view ...` readback — verifies GitHub metadata changes after they
    land.
  - Current READMEs, live docs, and source anchors above — verify whether a new
    public claim is true before it ships.
  - `uv run pytest tests/unit -q` — stays the cheap Rally proof path if any
    public copy depends on runtime behavior touched during execution.

## 3.3 Resolved decisions and remaining implementation work

- Resolved now: this plan does not need new product work. The execution surface
  is copy, docs, assets, repo metadata, GitHub-native engagement paths, and
  launch copy that can be shipped directly from these repos.
- Resolved now: public status copy must treat `codex` and `claude_code` as live
  support, must treat Hermes as not shipped, and should lead with
  "repo-local searchable memory" before naming QMD.
- Resolved in deep-dive pass 1: Rally's primary first-contact CTA is "run the
  shipped `poem_loop` flow now," with `software_engineering_demo` and Doctrine
  as the next deeper paths.
- Resolved in deep-dive pass 1: Doctrine's primary first-contact CTA is "see
  the source-to-runtime artifact story fast, then step into the quick example
  and live docs," with Rally as the runtime handoff.
- Resolved in deep-dive pass 1: the first-pass public wording for Rally support
  is "Codex-first with live Claude Code support," and MCP support stays a trust
  detail instead of the hero claim.
- Resolved in deep-dive pass 1: the first pass should add a Rally
  `docs/README.md` live-docs hub, keep Doctrine `docs/README.md` as the
  second-click docs hub, enable Doctrine Discussions, and clear the current
  `pokerskill.com` homepage fields on both repos.
- Resolved in deep-dive pass 1: adjacent continuity proof should stay tight and
  use `langdspy` plus `codex-autoresearcher`; `arch_skill`,
  `authoring-skills`, and `rally_paper` stay out of the public funnel for now.
- Resolved in deep-dive pass 2: first-pass homepage policy is explicit. Keep
  the homepage URL blank on both repos in this pass.
- Resolved in deep-dive pass 2: first-pass GitHub interaction surfaces are
  limited to Discussions on both repos plus one coordinated launch discussion
  and one release per repo. Label taxonomies, issue templates, and checked-in
  `.github/` templates are deferred.
- Resolved in deep-dive pass 2: first-pass topic policy is shared core topics
  plus repo-specific differentiators, not identical topic lists.
- Resolved in deep-dive pass 2: the shared launch-pack owner is
  `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md`.
- Resolved in deep-dive pass 2: the first required visual proof set is the
  existing Rally `poem-loop-demo-run.png` plus Doctrine's current README images.
  No extra proof asset is part of this first pass.
- No phase-shaping decisions remain. Section 7 is now the authoritative
  execution checklist.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

- Rally's current public funnel is spread across:
  - `README.md` for first contact
  - `CONTRIBUTING.md` for contributor setup
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`,
    `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`,
    `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md`, and
    `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md` for the best
    technical proof
  - `docs/research/*` for internal research notes that sit beside live docs
    today even though they are not public-funnel docs
  - `docs/assets/poem-loop-demo-run.png` as the only checked-in Rally visual
    proof asset today
- Doctrine's current public funnel is spread across:
  - `/Users/aelaguiz/workspace/doctrine/README.md` for first contact
  - `/Users/aelaguiz/workspace/doctrine/CONTRIBUTING.md` for contributor setup
  - `/Users/aelaguiz/workspace/doctrine/docs/README.md` as the live docs hub
  - `/Users/aelaguiz/workspace/doctrine/editors/vscode/README.md` for editor
    proof
  - checked-in README assets for the source-versus-emitted-artifact story and
    the workflow visualizer
  - checked-in `.vsix` files under
    `/Users/aelaguiz/workspace/doctrine/editors/vscode/`
- GitHub header surfaces live outside the repos themselves:
  - repo descriptions
  - topics
  - homepage URL
  - Discussions enabled state
- Neither repo has a checked-in `.github/` interaction surface today, so issue,
  discussion, and release shaping are mostly repo-setting or `gh` work right
  now.
- Founder-proof and adjacent-repo continuity proof live outside the funnel
  today in public profile pages, external coverage, GBrain pages, and the wider
  `aelaguiz` GitHub account.

## 4.2 Control paths (runtime)

Current Rally public path:

1. GitHub search or direct repo link lands on the repo header.
2. The header shows a useful description and topics, but the homepage still
   points off-repo to `https://pokerskill.com`.
3. The reader enters `README.md`, sees the strong high-level story and live demo
   image, then moves through a long philosophy and comparison path before the
   main quickstart arrives.
4. The reader may then click into Doctrine, deep docs, or contributing, but the
   first-minute funnel is not yet intentionally ordered around one fast next
   action.

Current Doctrine public path:

1. GitHub search or direct repo link lands on the repo header.
2. The header shows a solid description and topics, but the homepage also still
   points to `https://pokerskill.com`.
3. The reader enters `README.md`, sees the strong hero and side-by-side proof
   image, then moves through why, what ships, example, emit, visualizer, docs,
   and VS Code sections.
4. The README is already stronger than Rally's, but it still asks the reader to
   do more sorting work than a deliberate funnel should.

Current GitHub interaction path:

1. `aelaguiz/rally` already has Discussions enabled.
2. `aelaguiz/doctrine` does not.
3. Neither repo currently uses a tight repo-header-to-README-to-discussion or
   release ladder as one coordinated conversion surface.

## 4.3 Object model + key abstractions

- Rally's current first-contact objects are:
  - hero promise
  - status paragraph
  - live demo image
  - "Where Rally Fits" comparison
  - quickstart
  - deep docs
- Doctrine's current first-contact objects are:
  - hero promise
  - source-versus-emitted-artifact proof image
  - "What Ships Today"
  - quick example
  - workflow visualizer proof
  - live docs hub
  - VS Code extension proof
- Shared cross-repo objects that matter for conversion are:
  - repo header metadata
  - sister-repo cross-links
  - founder-proof
  - adjacent-repo continuity proof
  - GitHub-native interaction surfaces such as Discussions and releases

## 4.4 Observability + failure behavior today

- Current observability is mostly manual:
  - `gh repo view ...` readback for header metadata and Discussions state
  - visible README and docs scans
  - inbound GitHub response such as stars, issues, and discussions
- The main failure mode is not missing product truth. It is poor proof
  packaging:
  - live support is buried or mismatched in Rally's README
  - Doctrine's strongest proof is present but not fully front-loaded
  - the wrong homepage URL leaks cold traffic away from both repos
  - Rally has no live docs hub like Doctrine's
  - founder and continuity proof are real but sit outside the repo funnel

## 4.5 UI surfaces (ASCII mockups, if UI work)

Rally today:

```text
[GitHub header]
  -> [Hero + status]
  -> [Live demo]
  -> [Why / comparison / philosophy]
  -> [Quickstart]
  -> [Doctrine + docs + contributing]
```

Doctrine today:

```text
[GitHub header]
  -> [Hero]
  -> [Source vs emitted proof image]
  -> [Why / ships / example]
  -> [Emit / visualizer / docs / VS Code]
  -> [Contributing]
```
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

- `README.md` in each repo becomes the first 60-second funnel and owns:
  - one clear promise
  - one primary CTA
  - one proof strip
  - one sister-repo handoff
  - one lower placement for founder and continuity proof
- Rally adds `docs/README.md` as the live second-click docs hub.
- Doctrine keeps `/Users/aelaguiz/workspace/doctrine/docs/README.md` as the
  live second-click docs hub.
- Rally keeps the current best proof docs as second-click links, not as the
  main first-screen story:
  - `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`
  - `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md`
  - `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`
  - `docs/RALLY_MASTER_DESIGN_2026-04-12.md`
- Doctrine keeps deeper language and compiler reference in its live docs hub
  and README support pages:
  - `docs/README.md`
  - `docs/LANGUAGE_REFERENCE.md`
  - `docs/EMIT_GUIDE.md`
  - `editors/vscode/README.md`
- `docs/research/*` stays internal and should not be linked as part of the
  public conversion path.
- The shared outbound copy pack should live in one checked-in doc under Rally's
  `docs/`, because this repo already owns the canonical cross-repo plan and can
  coordinate both GitHub launches from one place.
- GitHub header settings for both repos become part of the architecture:
  - repo descriptions match the first line of the README story
  - topics use shared core tags plus repo-specific differentiators
  - homepage URLs are cleared on both repos in this first pass
  - Discussions are enabled on both repos
- First-pass GitHub-native interaction surfaces are:
  - Discussions on both repos
  - one coordinated launch discussion per repo
  - one release per repo
- First-pass required visual proof stays narrow:
  - Rally uses `docs/assets/poem-loop-demo-run.png`
  - Doctrine reuses the current README hero proof image and workflow visualizer
    image
- No new checked-in `.github/` template surface is part of the first pass.
  No label taxonomy work is required in the first pass either.
  First-pass interaction shaping stays in `gh`-managed repo settings and launch
  surfaces.

## 5.2 Control paths (future)

Future Rally path:

1. GitHub header frames the repo as the runtime and harness layer.
2. README hero explains the runtime story in one sentence.
3. The next block proves what is already live now:
   - Codex-first with live Claude Code support
   - repo-local searchable memory
   - repo-local run homes
4. The primary CTA is to run the shipped `poem_loop` flow immediately.
5. The secondary CTA is to inspect `software_engineering_demo`.
6. The sister-repo CTA points to Doctrine as the authoring layer.
7. Founder and continuity proof sit below product proof, not above it.
8. Contributor and discussion CTAs come after the reader has already seen proof
   and a runnable next step.

Future Doctrine path:

1. GitHub header frames the repo as the authoring and compiler layer.
2. README hero explains the source-to-runtime artifact story in one sentence.
3. The side-by-side source-versus-emitted-artifact image lands immediately as
   the first proof surface.
4. The primary CTA is to step into the quick example and live docs.
5. The next proof strip fronts the emit path, workflow visualizer, and VS Code
   extension.
6. The sister-repo CTA points to Rally as the runtime layer.
7. Founder and continuity proof again sit below product proof.
8. Contributor and discussion CTAs come after the reader already understands
   the product split.

Future launch path:

1. The shared launch-pack doc produces GitHub release copy, pinned discussion
   copy, HN/X/Reddit drafts, and direct-share text.
2. Those surfaces all point back into the same chosen README and docs paths.

## 5.3 Object model + abstractions (future)

- Canonical owner path:
  - GitHub header metadata is owned through `gh` repo settings work
  - `README.md` is the first-contact owner in each repo
  - `docs/README.md` is the second-click docs owner in each repo
  - `CONTRIBUTING.md` is the contributor-activation owner in each repo
  - the shared launch-pack doc in Rally owns outbound copy and launch drafts
- Rally's chosen public wording is:
  - runtime and harness layer
  - Codex-first with live Claude Code support
  - repo-local searchable memory
  - MCP support as a trust detail, not the hero line
- Doctrine's chosen public wording is:
  - authoring and compiler layer
  - `.prompt` source to runtime Markdown that existing coding-agent tools can
    read today
  - emit, workflow visuals, and editor support as the proof ladder
- Founder-proof contract:
  - one short supportable proof strip in both READMEs
  - expanded founder story only in the shared launch-pack and supporting copy
- Adjacent-repo continuity contract:
  - use `langdspy` and `codex-autoresearcher`
  - exclude `arch_skill`, `authoring-skills`, and `rally_paper` from the first
    public funnel because they are not currently packaged clearly enough
- No new product code, benchmark harness, microsite, or analytics layer is part
  of the target architecture. The plan packages shipped truth; it does not add
  a second proof system.

## 5.4 Invariants and boundaries

- One clear promise per repo.
- Product proof comes before founder proof.
- No README may describe a live feature in future tense if the code and docs
  already ship it.
- No README may claim unsupported support surfaces or imply Hermes is live.
- No public path should send cold repo traffic to an unrelated website.
- `docs/research/*` does not become part of the live public docs path.
- Each repo gets one live docs hub, not multiple competing docs indexes.
- First-pass GitHub interaction work does not widen into label or template
  taxonomy work.
- The shared launch pack can aggregate copy, but it must not create a second
  product story that disagrees with the READMEs.

## 5.5 UI surfaces (ASCII mockups, if UI work)

Rally target:

```text
[GitHub header: runtime/harness]
  -> [Hero]
  -> [Live proof strip]
  -> [Run poem_loop now]
  -> [Demo image]
  -> [Where Rally fits]
  -> [Doctrine handoff]
  -> [Founder + continuity strip]
  -> [Contribute / Discuss]
```

Doctrine target:

```text
[GitHub header: authoring/compiler]
  -> [Hero]
  -> [Source vs emitted proof image]
  -> [Quick example + docs CTA]
  -> [Emit / visualizer / VS Code proof strip]
  -> [Rally handoff]
  -> [Founder + continuity strip]
  -> [Contribute / Discuss]
```
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Rally first screen | `README.md` | Hero, status line, proof order, CTA ladder, cross-links | Strong story, but quickstart and support proof land too late and Claude or memory status underclaims reality | Rewrite the first screen around one runtime promise, one live proof strip, `poem_loop` as primary CTA, and Doctrine as the sister-repo handoff | Turn README into a conversion funnel instead of an architecture essay | README owns the first 60 seconds | Manual truth check against docs and code |
| Rally status copy | `README.md` | Current status paragraph | Says Claude Code support and repo-local memory are partly next | Rewrite to "Codex-first with live Claude Code support" and live repo-local searchable memory | Remove trust-killing drift | Public support wording contract | Manual truth check against `src/rally/adapters/registry.py` and docs |
| Rally docs hub | `docs/README.md` | New file | No live docs hub exists today | Add one live docs hub that links only the right second-click docs | Doctrine already proves this pattern and Rally needs it | One docs hub for Rally | Manual docs truth check |
| Rally contribution path | `CONTRIBUTING.md` | Setup and contribution framing | Accurate but not part of a tight funnel | Tighten after README rewrite so the contributor next step is shorter and more deliberate | Lower activation friction | CONTRIBUTING owns contributor activation, not product story | Manual docs truth check |
| Doctrine contribution path | `../../doctrine/CONTRIBUTING.md` | Setup and contribution framing | Accurate but not yet aligned tightly with the planned first-minute funnel | Tighten after the README rewrite so the contributor next step matches the new paired-repo story | Lower activation friction | CONTRIBUTING owns contributor activation, not product story | Manual docs truth check |
| Rally proof docs | `docs/RALLY_CLI_AND_LOGGING_2026-04-13.md`, `docs/RALLY_QMD_AGENT_MEMORY_MODEL_2026-04-13.md`, `docs/RALLY_SOFTWARE_ENGINEERING_FLOW_SHOWCASE_2026-04-13.md`, `docs/RALLY_MASTER_DESIGN_2026-04-12.md` | Live proof surfaces | Strong proof exists but is not curated as a ladder | Curate these as second-click destinations from the new docs hub and README | Keep depth without burying first-contact clarity | Docs hub link contract | Manual docs truth check |
| Doctrine first screen | `../../doctrine/README.md` | Hero, proof ordering, CTA ladder, sister-repo handoff | Already strong, but still asks the reader to sort too much before the key CTA is obvious | Rewrite around one authoring/compiler promise, one immediate proof image, one quick-example CTA, and Rally as the runtime handoff | Make the pair legible fast | README owns the first 60 seconds | Manual truth check against live docs and examples |
| Doctrine docs hub | `../../doctrine/docs/README.md` | Live docs ladder | Good today, but not yet clearly treated as the second-click hub from README | Tighten the hub and README linkage so it is clearly the next stop after the hero and quick example | Keep docs navigation tight | Docs hub stays the second-click owner | Manual docs truth check |
| Doctrine editor proof | `../../doctrine/editors/vscode/README.md` | VS Code extension install and proof page | Strong detail page, but not yet fully packaged as a funnel proof surface | Tighten for install clarity and sync README claims with the extension proof | Faster earned-right proof | VS Code README stays the detailed install page | Manual docs truth check |
| Founder proof | `README.md`, `../../doctrine/README.md` | Founder and operator credibility placement | Proof is real but mostly outside the funnel | Add one short supportable founder strip below product proof in both repos | Earn trust without stealing the hero | Founder proof stays below product proof | Manual truth check against public sources |
| Continuity proof | `README.md`, `../../doctrine/README.md` | Adjacent public repo references | Wider GitHub account exists, but current funnel does not curate it | Add tight continuity proof using `langdspy` and `codex-autoresearcher` only | Show this work comes from a real line of tool-building | Continuity proof stays narrow | Manual truth check against repo list |
| Shared launch pack | `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md` | New file | No checked-in outbound copy pack exists | Add one shared launch-pack doc in Rally | Keep launch execution and copy iteration in one place | One shared launch-pack owner | Manual link and claim check |
| Rally header metadata | GitHub repo settings | `gh repo edit` and related `gh` commands for `aelaguiz/rally` | Description and topics are decent, homepage points at `pokerskill.com`, Discussions are already on | Rewrite description if needed, keep shared core topics plus Rally-specific differentiators, clear the homepage URL in this first pass, and keep Discussions aligned | The header is part of the funnel before README load | Repo header must match README story | `gh repo view` readback |
| Doctrine header metadata | GitHub repo settings | `gh repo edit` and related `gh` commands for `aelaguiz/doctrine` | Description and topics are decent, homepage points at `pokerskill.com`, Discussions are off | Rewrite description if needed, keep shared core topics plus Doctrine-specific differentiators, clear the homepage URL in this first pass, and enable Discussions | Make the paired GitHub funnel symmetric and cleaner | Repo header must match README story | `gh repo view` readback |
| GitHub interaction surfaces | GitHub repo settings and release surfaces | Discussions, releases, pinned discussion copy | Interaction path is not yet an intentional ladder | Add one coordinated launch discussion and one release per repo through `gh` and the shared launch pack | Convert attention inside GitHub without widening into taxonomy work | First-pass GitHub-native interaction ladder | `gh` readback and manual review |
| Visual proof assets | `docs/assets/poem-loop-demo-run.png`, existing Doctrine README assets | Demo image and proof visuals | Rally has one checked-in proof image; Doctrine already has two strong README proof images | Reuse the current asset set only in this first pass and do not add a new proof asset track | Proof should land in seconds | First-pass visual proof contract | Manual asset review |

## 6.2 Migration notes

- Canonical owner path / shared code path:
  - GitHub header metadata is owned through `gh`
  - `README.md` is the first-contact owner in each repo
  - `docs/README.md` is the second-click docs owner in each repo
  - `CONTRIBUTING.md` owns contributor activation
  - `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md` should own shared
    outbound copy once added
- Deprecated APIs (if any):
  - none; this is a public-surface refactor, not a runtime API migration
- Delete list (what must be removed; include superseded shims/parallel paths if any):
  - Rally README future-tense copy for already-live Claude Code support and
    repo-local searchable memory
  - repo header homepage links that still point cold traffic at
    `https://pokerskill.com` without serving the repo funnel
  - public links or section emphasis that promote `docs/research/*` as part of
    the live docs path
  - low-signal README sections or ordering that bury the first runnable CTA
- Capability-replacing harnesses to delete or justify:
  - do not add a microsite, benchmark harness, analytics stack, or extra demo
    app when the current READMEs, docs, assets, and GitHub surfaces can carry
    the proof
- First-pass GitHub interaction limit:
  - no checked-in `.github/` templates
  - no label taxonomy project
- Live docs/comments/instructions to update or delete:
  - `README.md`
  - `CONTRIBUTING.md`
  - new `docs/README.md`
  - `../../doctrine/README.md`
  - `../../doctrine/CONTRIBUTING.md`
  - `../../doctrine/docs/README.md`
  - `../../doctrine/editors/vscode/README.md`
- Behavior-preservation signals for refactors:
  - `gh repo view aelaguiz/rally --json ...`
  - `gh repo view aelaguiz/doctrine --json ...`
  - current source and docs anchors named in Section 3
  - manual first-screen and docs-hub scan after each rewrite

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Rally docs navigation | `docs/README.md` | Doctrine-style live docs hub | avoids Rally linking readers into a flat dated-doc list | include |
| Repo header taxonomy | `gh repo edit` on both repos | aligned descriptions, topics, and homepage stance | avoids paired-repo drift before README load | include |
| Discussions parity | `aelaguiz/doctrine` repo settings | enable Discussions to match the paired funnel | avoids asymmetric GitHub engagement paths | include |
| Header topic policy | `gh repo edit` on both repos | shared core topics plus repo-specific differentiators | avoids identical-but-wrong topic sets | include |
| Homepage policy | `gh repo edit` on both repos | clear homepage fields in this first pass | avoids leaking cold traffic away from the repos | include |
| Founder proof placement | both READMEs | short proof strip below product proof | avoids founder story crowding out the product | include |
| Continuity proof | both READMEs | use only `langdspy` and `codex-autoresearcher` | avoids noisy repo-lists and weak continuity signals | include |
| Shared launch pack | Rally `docs/` | one checked-in outbound copy owner | avoids duplicate launch drafts across repos | include |
| GitHub launch surfaces | Discussions plus releases on both repos | one coordinated discussion and one release per repo | avoids diffuse launch copy across ad hoc surfaces | include |
| `.github` templates | repo root `.github/` | checked-in issue or discussion templates | may help later, but is not required for the first conversion pass | defer |
| Broader adjacent repo set | `arch_skill`, `authoring-skills`, `rally_paper` | surface all related repos | current packaging is too weak for first-funnel use | exclude |
| External website | any new site or GitHub Pages build | off-repo landing page | out of scope and not needed for this pass | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; every phase has exit criteria + explicit verification plan (tests optional). Refactors, consolidations, and shared-path extractions must preserve existing behavior with credible evidence proportional to the risk. For agent-backed systems, prefer prompt, grounding, and native-capability changes before new harnesses or scripts. No fallbacks or runtime shims. The system must work correctly or fail loudly. The authoritative checklist names the chosen work only. It does not hold unresolved branches or "if needed" placeholders. Prefer small programmatic checks where they exist, and defer manual first-screen review to the final pass.

## Phase 1 - Land the stable public owners

* Goal:
  Create the stable second-click surfaces and shared launch-pack owner before
  rewriting the main landing pages.
* Work:
  - add `docs/README.md` in Rally as the live second-click docs hub
  - tighten `/Users/aelaguiz/workspace/doctrine/docs/README.md` only where it
    needs a clearer handoff from the new README funnel
  - add `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md` as the one
    shared outbound copy owner
  - keep `docs/research/*` out of the live public docs path
* Verification (required proof):
  - manually inspect Rally `docs/README.md` and Doctrine `docs/README.md`
    against the Section 3 and Section 5 owner model
  - verify every new docs-hub link points only at live repo docs, not research
    notes
* Docs/comments (propagation; only if needed):
  - no code comments required
  - keep doc-owner wording aligned between the new Rally docs hub, the Doctrine
    docs hub, and the shared launch pack
* Exit criteria:
  - both repos have a clear second-click docs owner
  - the launch pack has one checked-in owner path
  - no live docs path points readers into `docs/research/*`
* Rollback:
  - revert the new docs hub and launch-pack files together

## Phase 2 - Rewrite the first-contact repo surfaces

* Goal:
  Turn both repos into deliberate first-minute GitHub funnels with proof before
  depth.
* Work:
  - rewrite Rally `README.md` around the runtime and harness story, the live
    proof strip, `poem_loop` as the primary CTA, `software_engineering_demo` as
    the deeper demo, and Doctrine as the sister-repo handoff
  - rewrite Doctrine `README.md` around the authoring and compiler story, the
    source-versus-emitted-artifact proof image, the quick example and live docs
    CTA, and Rally as the runtime handoff
  - rewrite Rally's future-tense status copy so already-live Claude Code
    support and repo-local searchable memory are described honestly
  - tighten `CONTRIBUTING.md` in both repos and
    `/Users/aelaguiz/workspace/doctrine/editors/vscode/README.md` so the
    support surfaces match the new funnel
  - add the chosen founder-proof and continuity-proof strips to both READMEs
* Verification (required proof):
  - manual truth-check every new public claim against the Section 3 anchors
  - manually scan both README first screens and confirm the primary CTA is
    visible without hunting
  - if any README claim depends on live Rally runtime behavior, keep
    `uv run pytest tests/unit -q` available as the smallest proof path
* Docs/comments (propagation; only if needed):
  - update or delete stale README and contributing text in the same pass
  - do not add comments or docs outside the chosen public owners
* Exit criteria:
  - both repos explain their job in one screen
  - both repos show proof before deep docs
  - both repos cross-link cleanly without blurring the split
* Rollback:
  - revert the README and contributing edits together per repo

## Phase 3 - Sync GitHub header and engagement surfaces

* Goal:
  Make the GitHub repo header and native engagement path match the rewritten
  landing pages.
* Work:
  - draft the repo-description strings, topic edits, release copy, and launch
    discussion copy inside
    `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md` before any `gh`
    publishing step
  - update repo descriptions for `aelaguiz/rally` and `aelaguiz/doctrine`
  - update topics with shared core tags plus repo-specific differentiators
  - clear both homepage URLs
  - enable Doctrine Discussions and keep Rally Discussions aligned with the new
    story
  - create one coordinated launch discussion and one release per repo from the
    shared launch pack
* Verification (required proof):
  - `gh repo view aelaguiz/rally --json description,homepageUrl,repositoryTopics,hasDiscussionsEnabled`
  - `gh repo view aelaguiz/doctrine --json description,homepageUrl,repositoryTopics,hasDiscussionsEnabled`
  - manually inspect the created release and discussion surfaces against the
    launch pack
* Docs/comments (propagation; only if needed):
  - no checked-in `.github/` templates
  - no label taxonomy work in this phase
* Exit criteria:
  - both repo headers match the README story
  - both repos have Discussions enabled
  - each repo has one launch discussion and one release tied to the new story
* Rollback:
  - revert the `gh` metadata and launch-surface changes per repo

## Phase 4 - Final cross-repo truth pass

* Goal:
  Finish the non-GitHub launch drafts, verify the public funnel end to end, and
  leave no stale live truth behind.
* Work:
  - finish `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md` with:
    - HN, X, Reddit, and direct-share drafts
    - the short founder-story proof pack
    - the shipped-proof pack
  - reuse the existing first-pass visual proof set and do not add another asset
    in this pass
  - run a final cross-repo truth pass over README, docs hubs, contributing
    docs, VS Code README, repo headers, launch discussions, and releases
* Verification (required proof):
  - manual first-screen scan of both repos after all edits land
  - manual docs-hub scan of both repos after all edits land
  - manual link check from the launch pack into the live repo surfaces
  - final `gh repo view` readback for both repos
* Docs/comments (propagation; only if needed):
  - delete or rewrite any touched live doc text that still tells the old story
  - keep `docs/research/*` and other internal planning notes out of the public
    funnel
* Exit criteria:
  - the shared launch pack is complete across GitHub and non-GitHub launch
    surfaces
  - both repos and both repo headers tell the same story
  - no touched live doc still carries stale copy about support, proof, or CTA
* Rollback:
  - revert launch-pack and late doc edits together; do not leave a mixed old
    and new public story
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Public truth checks

- Verify every public claim against current code, docs, examples, or runnable
  commands before it ships.
- Treat `src/rally/adapters/registry.py`, Rally's live docs, Doctrine's live
  docs, and the checked-in proof assets as the main truth anchors for first
  contact copy.

## 8.2 GitHub surface checks

- Use `gh repo view` readback to confirm repo descriptions, topics, homepage
  state, and Discussions state after metadata edits.
- Manually review the created release and discussion surfaces against the
  launch-pack copy.

## 8.3 Manual funnel checks

- Manually review the first screen, quickstart, proof section, docs hub, and
  CTA ladder in both repos for scan speed and clarity.
- Treat reader confusion as a real bug if a new technical visitor still cannot
  explain the Doctrine and Rally split quickly.

## 8.4 Proof we should not add

- Do not add benchmark harnesses, analytics stacks, label taxonomy checks, or
  `.github/` template work as blockers for this first pass.

# 9) Rollout / Ops / Telemetry

- Use hard cutover. Do not keep old and new public stories alive at the same time.
- Roll out README, docs, assets, and metadata in a coordinated pass for each repo.
- Use GitHub-owned signals first: stars, watches, forks, issues, discussions, release response, and visible confusion in inbound questions.
- After the first launch cut is live, use the first visible GitHub response for
  one fast follow-up tightening pass. That follow-up lives in rollout, not in
  the authoritative implementation checklist.
- If a proof asset or CTA underperforms on first contact, tighten the copy or
  replace the asset instead of adding more abstract explanation.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, `planning_passes`, `# TL;DR`, and Sections `0` through `10`
  - cross-section agreement on outcome, owner path, execution order, deletes,
    verification, rollout, and approved exceptions
- Findings summary:
  - one phase-order bug left GitHub release and discussion publishing ahead of
    the launch-pack copy that should feed it
  - the call-site audit was missing `/Users/aelaguiz/workspace/doctrine/CONTRIBUTING.md`
    even though Section 7 and the final truth pass still required it
  - homepage policy and proof-asset scope still had leftover conditional
    branches that kept the artifact from being fully locked
- Integrated repairs:
  - moved launch-pack release and discussion drafting into Phase 3 before any
    live GitHub publishing step
  - added `/Users/aelaguiz/workspace/doctrine/CONTRIBUTING.md` to the call-site
    audit and propagation list
  - locked homepage policy to "clear both repo homepages in this first pass"
  - locked first-pass proof-asset scope to the current checked-in asset set
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

- 2026-04-13: This plan only covers work that can be executed directly through repo edits, research, copy writing, assets, and GitHub changes through `gh`.
- 2026-04-13: Doctrine and Rally will be positioned as a linked pair, but each repo will keep one clear job and one clear public promise.
- 2026-04-13: Public packaging will prefer proof-first, comparison-led, GitHub-native conversion paths over generic platform language.
- 2026-04-13: Founder and operator history is now explicitly in scope as proof packaging because it is externally supportable and materially affects trust and conversion.
- 2026-04-13: Rally support claims must distinguish what is shipped now from what is future work. `codex` and `claude_code` are live proof; Hermes is not.
- 2026-04-13: QMD is useful proof of depth, but public copy should probably lead with "repo-local searchable memory" before naming the implementation detail.
- 2026-04-13: North Star approved by the user with the current scope intact. The next explicit `arch-step` command should continue from this same doc.
- 2026-04-13: Deep-dive pass 1 chose Rally's first-contact CTA as "run the shipped `poem_loop` flow now" and Doctrine's first-contact CTA as "see the source-to-runtime artifact story fast, then step into the quick example and live docs."
- 2026-04-13: Deep-dive pass 1 chose "Codex-first with live Claude Code support" as the public Rally wording, with repo-local searchable memory as live proof and MCP support as a lower trust detail.
- 2026-04-13: Deep-dive pass 1 chose a Rally `docs/README.md` live-docs hub, Doctrine Discussions enabled, and removal of the current `pokerskill.com` homepage fields unless a repo-owned CTA URL exists.
- 2026-04-13: Deep-dive pass 1 narrowed adjacent continuity proof to `langdspy` and `codex-autoresearcher`.
- 2026-04-13: Deep-dive pass 2 made first-pass homepage policy explicit: clear both repo homepage URLs unless a repo-owned CTA page exists by implementation time.
- 2026-04-13: Deep-dive pass 2 narrowed first-pass GitHub interaction work to Discussions on both repos plus one coordinated launch discussion and one release per repo. Labels and checked-in `.github/` templates are deferred.
- 2026-04-13: Deep-dive pass 2 fixed the shared launch-pack owner to `docs/RALLY_DOCTRINE_GITHUB_LAUNCH_PACK_2026-04-13.md` and fixed the required first-pass visual proof set to existing checked-in assets.
- 2026-04-13: Phase planning made Section 7 a four-phase execution checklist: public owners, first-contact rewrites, GitHub header plus engagement sync, and final launch-pack plus truth pass.
- 2026-04-13: Phase planning moved first-response tightening into rollout follow-through so the authoritative implementation checklist stays ship-blocking only.
- 2026-04-13: Consistency repair moved launch-pack release and discussion drafting into Phase 3 so GitHub publishing no longer depends on a later phase.
- 2026-04-13: Consistency pass locked the first-pass homepage decision to clearing both repo homepages, with no repo-owned CTA replacement in this plan.
- 2026-04-13: Consistency pass locked the first-pass proof-asset scope to the current checked-in Rally and Doctrine proof assets; no new proof asset is part of this pass.
- 2026-04-13: Consistency pass added `/Users/aelaguiz/workspace/doctrine/CONTRIBUTING.md` to the authoritative call-site audit so Section 6 matches Section 7 and the final truth pass.
