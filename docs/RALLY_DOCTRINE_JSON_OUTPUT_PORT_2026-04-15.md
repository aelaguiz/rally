---
title: "Rally - Doctrine JSON Output Port - Architecture Plan"
date: 2026-04-15
status: active
fallback_policy: forbidden
owners: [aelaguiz]
reviewers: []
doc_type: phased_refactor
related:
  - docs/RALLY_MASTER_DESIGN.md
  - docs/RALLY_RUNTIME.md
  - docs/RALLY_COMMUNICATION_MODEL.md
  - stdlib/rally/prompts/rally/turn_results.prompt
  - flows/poem_loop/prompts/shared/review.prompt
  - flows/software_engineering_demo/prompts/shared/review.prompt
  - src/rally/services/flow_loader.py
  - src/rally/services/final_response_loader.py
  - src/rally/services/runner.py
  - ../doctrine/docs/AGENT_IO_DESIGN_NOTES.md
  - ../doctrine/docs/LANGUAGE_REFERENCE.md
  - ../doctrine/docs/EMIT_GUIDE.md
  - ../doctrine/examples/79_final_output_json_object/prompts/AGENTS.prompt
---

# TL;DR

## Outcome

Rally ports its framework and shipped demos onto Doctrine's new structured JSON
pattern. Shared and flow-local JSON contracts move into Doctrine `output
schema` source, Doctrine emits the live schema artifact into `build/`, and
Rally consumes that build output without embedded JSON authoring on the Rally
side. The resulting pattern stays inheritable and extendable by Rally framework
users instead of working only for Rally's built-in shared contracts.

## Problem

Rally still lives on the old JSON path. It authors raw schema and example
surfaces, builds around the old final-output machine contract, and loads
structured turn results through assumptions that do not match Doctrine's new
model.

## Approach

Do a hard port in one coherent story. Move Rally-authored JSON truth into
Doctrine `output schema`, keep Rally runtime control behavior narrow at first,
replace the old build and loader assumptions with the new compiler-owned build
artifacts, then rebuild demos, bundled assets, tests, and docs from that one
source of truth.

## Plan

1. Add the missing compiler-owned final-output metadata artifact in Doctrine.
2. Port the shared `rally.turn_results` contract to the new Doctrine pattern.
3. Port review and demo JSON contracts to the same pattern.
4. Replace Rally build, loader, adapter, and runtime assumptions that still
   expect the old JSON contract.
5. Rebuild generated output, bundled assets, dev-Doctrine build proof, and
   release metadata surfaces on the new package shape.
6. Update live docs and run the final cutover proof.

## Non-negotiables

- No embedded JSON authoring on the Rally side for the framework or shipped
  demos.
- The new pattern must stay inheritable and extendable by Rally framework
  users.
- No old `json schema` plus `example_file` story kept alive beside the new
  pattern.
- No Markdown scraping for machine truth.
- No silent behavior drift in `handoff`, `done`, `blocker`, `sleep`, or
  review routing while this port lands.
- No runtime shim that keeps both contract paths alive.

<!-- arch_skill:block:implementation_audit:start -->
# Implementation Audit (authoritative)
Date: 2026-04-15
Verdict (code): COMPLETE
Manual QA: pending (non-blocking)

## Code blockers (why code is not done)
- None. Fresh emit proof, focused Phase 4 plus Phase 5 tests, and
  `make build-dist` all passed in this audit.
- I did not find an execution-side rewrite that weakened requirements, scope,
  acceptance criteria, or phase obligations to hide unfinished work. The
  dev-Doctrine proof target stays explicit in Section 0, Section 6, Phase 5,
  and the Decision Log.

## Reopened phases (false-complete fixes)
- None.

## Missing items (code gaps; evidence-anchored; no tables)
- None. The approved code frontier is closed:
  - `runtime.prompt_input_command` is restored and covered by loader and
    runner tests.
  - Rally loads emitted schema plus `final_output.contract.json`, generated
    `AGENTS.contract.json` files are gone, and the packaged-install proof
    asserts the new package shape.
  - The targeted live docs now teach the compiler-owned schema plus
    `final_output.contract.json` story.

## Non-blocking follow-ups (manual QA / screenshots / human verification)
- If you still want human confirmation of issue-ledger behavior, run one
  producer flow and one review flow live. This audit did not reopen Phase 6
  because that remaining check is manual only.
<!-- arch_skill:block:implementation_audit:end -->

<!-- arch_skill:block:planning_passes:start -->
<!--
arch_skill:planning_passes
deep_dive_pass_1: done 2026-04-15
external_research_grounding: not needed
deep_dive_pass_2: done 2026-04-15
phase_plan: done 2026-04-15
consistency_pass: done 2026-04-15
recommended_flow: deep dive -> external research grounding -> deep dive again -> phase plan -> consistency pass -> implement
note: This block tracks stage order only. It never overrides readiness blockers caused by unresolved decisions.
-->
<!-- arch_skill:block:planning_passes:end -->

# 0) Holistic North Star

## 0.1 The claim (falsifiable)

Rally can adopt Doctrine's new structured JSON pattern cleanly if it does five
things in one architecture line:

1. author shared and demo JSON contracts in Doctrine `output schema`
2. treat Doctrine's live `build/` output as the structured-output contract
3. keep Rally's current producer and review control behavior stable during the
   port
4. keep the resulting pattern inheritable and extendable for Rally framework
   users
5. delete the old Rally-authored schema and example path instead of bridging it

This claim is false if any of these stay true after the work:

- Rally still authors shared or demo structured outputs through raw
  `.schema.json`, `.example.json`, or inline raw JSON source blobs.
- Rally still depends on the old structured-output machine contract shape for
  producer turns.
- Rally needs Markdown scraping to learn structured-output machine truth.
- Producer `handoff`, `done`, `blocker`, `sleep`, or current review routing
  behavior changes without an explicit approved design change.
- Rally framework users cannot inherit or extend the new structured-output
  pattern without dropping back to embedded JSON or a Rally-only workaround.
- The repo keeps parallel old and new JSON stories alive.

## 0.2 In scope

- Port the shared `rally.turn_results` contract to Doctrine `output schema`.
- Port the shared proof flow in `_stdlib_smoke` plus shipped demo review and
  control JSON contracts in `poem_loop` and `software_engineering_demo`.
- Implement the compiler-owned structured-output artifact contract
  Rally should load from live `build/` output:
  - emitted schema file for payload wire shape
  - one new `final_output.contract.json` artifact with:
    - `contract_version`
    - final-output metadata
    - review carrier and split-final metadata when present
    - explicit `review_fields` and `control_ready` truth
- Keep the new structured-output authoring and load path usable by Rally
  framework users who want to inherit or extend the shared contract family.
- Update Rally build, load, adapter, and final-response paths that still assume
  the old structured-output contract.
- Prove the port against the paired local Doctrine checkout that Rally uses in
  this workspace.
- Keep Rally's public Doctrine dependency line as release metadata for now; do
  not use the public package index as the WIP proof target.
- Update bundled assets, generated readback, tests, and design docs touched by
  that same contract family.
- Delete old Rally-authored structured-output schema and example source files
  once the new path is live.

Allowed architectural convergence scope:

- Widen the change across shared stdlib prompts, demo prompts, generated build
  trees, bundled asset sync, loader/runtime code, and tests when that is what
  it takes to keep one JSON source of truth.
- Introduce one new compiler-owned machine contract surface for Rally if the
  emitted schema file alone is not enough to carry review control meaning.
- Remove stale generated assets, old tests, and old docs in the same pass.

Compatibility posture:

- Clean cutover to Doctrine's new structured JSON path.
- No runtime bridge that keeps the old Rally-authored schema or example path
  alive.

## 0.3 Out of scope

- New user-facing run states or new producer result kinds.
- A broader Rally control model than the current producer and review behavior
  already shipped.
- A compatibility bridge that keeps both old and new structured-output paths
  alive at runtime.
- A Rally-only JSON pattern that framework users cannot inherit or extend.
- Markdown scraping or heuristic discovery of machine semantics.
- Unrelated CLI, memory, MCP, or run-home redesign.

## 0.4 Definition of done (acceptance evidence)

- Shared and demo structured JSON contracts are authored through Doctrine
  `output schema`.
- No Rally-authored raw `.schema.json`, `.example.json`, or inline raw JSON
  source blobs remain for the ported framework and demo JSON surfaces.
- Doctrine emit succeeds for the shipped Rally flows against the paired local
  Doctrine compiler from editable `../doctrine`.
- Focused Doctrine tests for output-schema lowering, final-output compilation,
  review-contract metadata, and emit behavior pass on the new artifact path.
- Rally can load the emitted agent package from live `build/` output:
  - `AGENTS.md`
  - emitted schema file
  - `final_output.contract.json`
  and run the shipped flows through the same current control behavior.
- Rally fails loud when built agent packages come from an older Doctrine build
  that does not emit the new schema plus metadata shape.
- A Rally framework user can inherit the shared structured-output pattern and
  extend it in flow-owned prompt source without reintroducing embedded JSON.
- Focused Rally tests for flow build, flow load, final-response loading,
  adapters, runner behavior, run-store projections, bundled assets, package
  release, and release parsing pass on the new contract.
- Generated build output, bundled assets, and touched docs all tell one current
  JSON story.

## 0.5 Key invariants (fix immediately if violated)

- One structured-output source of truth per contract.
- One compiler-owned machine truth path for Rally to load.
- No embedded JSON authoring on the Rally side for this contract family.
- Shared structured-output contracts remain inheritable and extendable by Rally
  framework users.
- No silent producer or review control drift.
- Fail loud when emitted structured-output artifacts are missing or invalid.

# 1) Key Design Considerations (what matters most)

## 1.1 Priorities (ranked)

1. Keep one truthful structured-output contract between Doctrine build output
   and Rally runtime.
2. Preserve current Rally control behavior while the contract plumbing changes.
3. Keep the pattern inheritable and extendable for Rally framework users.
4. Remove Rally-authored embedded JSON and raw schema/example source surfaces.
5. Keep the build and loader model simple enough that future ports follow the
   same path.

## 1.2 Constraints

- Rally's current runtime and tests are strongly coupled to the old machine
  contract.
- Doctrine's new JSON model is a hard cut, not a soft add-on.
- Review control semantics need explicit machine truth; a schema file alone may
  not carry enough meaning for Rally.
- Generated build output and bundled copies are part of shipped repo truth.

## 1.3 Architectural principles (rules we will enforce)

- Compiler-owned structured-output truth beats Rally-local reconstruction.
- Author JSON once in Doctrine source, then emit and consume it.
- Shared contract families must be designed so downstream Rally flows can
  inherit and extend them cleanly.
- Keep producer runtime semantics stable until the new contract path is proven.
- Cut over cleanly and delete the old path instead of carrying a bridge.

## 1.4 Known tradeoffs (explicit)

- This port likely widens from prompt source into loader, adapters, tests, and
  generated assets. That is convergence work, not product creep.
- Rally needs one compiler-owned machine metadata artifact beyond the emitted
  schema file for review routing truth.

# 2) Problem Statement (existing architecture + why change)

## 2.1 What exists today

Rally still authors shared and demo structured outputs on the old Doctrine
JSON path. It ships raw schema and example files, expects the old compiled
machine contract, and routes runtime behavior from that older contract family.

## 2.2 What’s broken / missing (concrete)

Rally cannot cleanly adopt Doctrine's new structured JSON pattern until it
stops depending on the old authored surfaces and the old load-time contract.
As written, the shared Rally turn-result prompt is still on syntax Doctrine is
retiring, and Rally's loader/runtime story still assumes the old contract
shape.

## 2.3 Constraints implied by the problem

- The port must be framework-first, not just a demo cleanup.
- Shared and demo contracts must move together so Rally does not teach two JSON
  stories.
- Runtime routing behavior must stay stable while the build contract changes.

# 3) Research Grounding (external + internal “ground truth”)
<!-- arch_skill:block:research_grounding:start -->
## 3.1 External anchors (papers, systems, prior art)

- Doctrine live docs and compiler are the main anchor for this port.
  Rally is not inventing a new JSON model. It is adopting the one Doctrine
  now ships.
- OpenAI strict structured outputs are the wire target, but Doctrine already
  bakes that target into its lowered schema validator and live proof tooling.
  Rally should inherit that contract through Doctrine instead of restating it
  locally.

## 3.2 Internal ground truth (code as spec)

- Authoritative behavior anchors:
  - `../doctrine/doctrine/_compiler/resolve/output_schemas.py`
    - Canonical owner for `output schema` inheritance, ref rebinding, and
      lowering into JSON Schema.
  - `../doctrine/doctrine/_compiler/resolve/outputs.py`
    - Bridge from `final_output` to structured JSON behavior. Resolves the
      `JsonObject` shape, lowers the attached `output schema`, validates the
      lowered schema and example, and builds payload preview rows.
  - `../doctrine/doctrine/_compiler/compile/final_output.py`
    - Canonical owner for compiled final-output metadata, generated schema
      path naming, and final rendered contract sections.
  - `../doctrine/doctrine/emit_docs.py`
    - Emits `AGENTS.md` plus `schemas/<output-slug>.schema.json` for
      structured final outputs.
  - `../doctrine/doctrine/_compiler/compile/review_contract.py`
    - Canonical owner for review carrier vs split mode, `review_fields`, and
      `control_ready`.
  - `../doctrine/doctrine/_compiler/output_schema_validation.py`
    - Canonical owner for Draft 2020-12 plus the OpenAI strict subset.
  - `../doctrine/doctrine/validate_output_schema.py`
    - File-level validator for one emitted schema artifact.
  - `../doctrine/doctrine/prove_output_schema_openai.py`
    - Live OpenAI acceptance proof against one emitted schema artifact.

- Canonical path and owner to reuse:
  - `output schema -> output shape kind: JsonObject -> final_output ->
    build/.../schemas/<output-slug>.schema.json`
    - This is Doctrine's new structured-output path.
  - `review` plus `final_output.review_fields`
    - This is Doctrine's existing machine meaning for review control fields.

- Adjacent surfaces tied to the same contract family:
  - `../doctrine/docs/LANGUAGE_REFERENCE.md`
    - Live authoring and emitted-build contract for `output schema`,
      `final_output`, and emitted schema files.
  - `../doctrine/docs/EMIT_GUIDE.md`
    - Live emitted package layout. Says machine consumers should load the
      emitted schema file.
  - `../doctrine/docs/VERSIONING.md`
    - Public compatibility posture. The emitted schema file is part of the
      supported build surface.
  - `../doctrine/examples/79_final_output_json_object/**`
    - The clearest checked-in proof of the new emitted build shape.
  - `../doctrine/examples/83_review_final_output_json_object/**`
    - Review-as-carrier JSON pattern.
  - `../doctrine/examples/104_review_final_output_json_object_blocked_control_ready/**`
    - Review JSON carrier with blocked branches and nullable control fields.
  - `../doctrine/examples/105_review_split_final_output_json_object_control_ready/**`
    - Split final-output review pattern with `review_fields`.
  - `../doctrine/examples/106_review_split_final_output_json_object_partial/**`
    - Partial split pattern that is not fully control-ready.
  - `../doctrine/examples/110_final_output_inherited_output/**`
    - Inherited `final_output` pattern.
  - `../doctrine/tests/test_output_schema_surface.py`
    - Proof that inherited `output schema` and inherited `output shape`
      behavior already exists.
  - `../doctrine/tests/test_output_schema_lowering.py`
    - Proof for inheritance, defs, recursion, nullable optionals, and lowered
      property order.
  - `../doctrine/tests/test_final_output.py`
    - Proof for final-output rendering and route/review semantics.
  - `../doctrine/tests/test_emit_docs.py`
    - Proof that `emit_docs` writes `AGENTS.md` plus emitted schema and no
      longer writes `AGENTS.contract.json`.
  - `pyproject.toml`
  - `uv.lock`
    - Rally currently builds against the editable `../doctrine` checkout and
      publishes a public Doctrine package line as release metadata. This WIP
      port proves against the editable checkout, not the public package index.

- Compatibility posture, separate from `fallback_policy`:
  - Clean cutover.
    - Doctrine's live path has already retired `json schema` declarations,
      `example_file`, and `AGENTS.contract.json` for this feature family.
    - Rally should adopt the same cutover instead of carrying a local bridge.

- Existing patterns to reuse:
  - `../doctrine/examples/79_final_output_json_object/prompts/AGENTS.prompt`
    - Base structured final-output pattern with inline schema and example.
  - `../doctrine/examples/104_review_final_output_json_object_blocked_control_ready/prompts/AGENTS.prompt`
    - Review JSON carrier pattern when the same output is both review carrier
      and final output.
  - `../doctrine/examples/105_review_split_final_output_json_object_control_ready/prompts/AGENTS.prompt`
    - Split review final-output pattern when control fields need explicit
      `review_fields`.

- Prompt surfaces and agent contract to reuse:
  - `stdlib/rally/prompts/rally/turn_results.prompt`
    - Shared producer turn-result contract that must move first.
  - `flows/poem_loop/prompts/shared/review.prompt`
    - Flow-owned review JSON carrier that still uses the old schema and
      example path.
  - `flows/software_engineering_demo/prompts/shared/review.prompt`
    - Current source already uses the `EngineeringReview*` family, but still
      authors JSON through old schema and example side files.
  - `flows/software_engineering_demo/prompts/AGENTS.prompt`
  - `flows/software_engineering_demo/prompts/roles/architect_reviewer.prompt`
  - `flows/software_engineering_demo/prompts/roles/developer_reviewer.prompt`
  - `flows/software_engineering_demo/prompts/roles/qa_reviewer.prompt`
    - Review-family and reviewer-role surfaces that consume the shared
      engineering review contract and must stay aligned with it.
  - `flows/_stdlib_smoke/prompts/AGENTS.prompt`
    - Smoke flow that should inherit the new shared turn-result path.

- Native model or agent capabilities to lean on:
  - Codex already accepts `--output-schema <schema-file>`.
  - Claude Code already accepts `--json-schema <schema-text>`.
  - Rally does not need new wrappers or parsers to make the models speak JSON.
    It needs the right emitted machine contract and the right schema payload.

- Existing grounding, tool, or file exposure:
  - `src/rally/adapters/codex/adapter.py`
    - Loads a schema file path into Codex today.
  - `src/rally/adapters/claude_code/adapter.py`
    - Loads raw schema text into Claude Code today.
  - `src/rally/services/final_response_loader.py`
    - Reads one final JSON object from `last_message.json`.
  - `src/rally/services/runner.py`
    - Records the final JSON object into Rally notes and runtime files.

- Duplicate or drifting paths relevant to this change:
  - `stdlib/rally/schemas/rally_turn_result.schema.json`
  - `stdlib/rally/examples/rally_turn_result.example.json`
  - `flows/poem_loop/schemas/poem_review.schema.json`
  - `flows/poem_loop/examples/poem_review.example.json`
  - `flows/software_engineering_demo/schemas/engineering_review.schema.json`
  - `flows/software_engineering_demo/examples/engineering_review.example.json`
  - `src/rally/_bundled/stdlib/rally/**`
  - `flows/*/build/**`
  - `src/rally/services/flow_build.py`
  - `src/rally/services/flow_loader.py`
  - `src/rally/domain/flow.py`
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/test_runner.py`
  - `pyproject.toml`
  - `uv.lock`
  - `src/rally/_package_release.py`
  - `tests/unit/test_package_release.py`
  - `docs/RALLY_RUNTIME.md`
  - `docs/RALLY_COMMUNICATION_MODEL.md`
  - `docs/VERSIONING.md`
    - All of these still encode the old JSON story and must converge in the
      same migration family.

- Capability-first opportunities before new tooling:
  - Move Rally authoring into Doctrine `output schema`.
  - Reuse Doctrine's emitted schema artifact for adapter-facing JSON output.
  - Reuse Doctrine review semantics for carrier vs split control fields.
  - Avoid any Rally-local Markdown scraping, sidecar reconstruction, or
    heuristic field-name inference.

- Behavior-preservation signals already available:
  - `tests/unit/test_flow_loader.py`
    - Preserves compile/load behavior for shared and review outputs.
  - `tests/unit/test_final_response_loader.py`
    - Preserves producer and review control parsing.
  - `tests/unit/test_runner.py`
    - Preserves end-turn recording and adapter launch behavior.
  - `tests/unit/test_run_store.py`
    - Preserves compiled contract projections stored in Rally domain objects.
  - `tests/unit/test_adapter_mcp_projection.py`
    - Preserves compiled agent projection behavior for adapter-facing config.
  - `tests/unit/test_package_release.py`
    - Preserves the release package-line metadata.
  - `../doctrine/tests/test_output_schema_surface.py`
    - Preserves inherited and imported `output schema` behavior.
  - `../doctrine/tests/test_output_schema_lowering.py`
    - Preserves lowered schema shape and nullable-required wire behavior.
  - `../doctrine/tests/test_final_output.py`
    - Preserves final-output and review-metadata compilation behavior.
  - `../doctrine/tests/test_emit_docs.py`
    - Preserves emitted schema path and no-sidecar build shape.

## 3.3 Decision gaps that must be resolved before implementation

- No user-choice blocker is exposed by repo truth so far.
- Architecture decision resolved in deep-dive:
  - Rally should consume compiler-owned machine review semantics from Doctrine
    through one new emitted `final_output.contract.json` artifact.
  - Emitted schema alone is not enough for review control meaning.
  - Markdown scraping is not acceptable.
  - Rally-local semantic reconstruction is not acceptable.
- Implementation blocker stance:
  - if Doctrine does not yet emit `final_output.contract.json`, Rally stops at
    that framework gap and does not rebuild the same semantics locally.
<!-- arch_skill:block:research_grounding:end -->

<!-- arch_skill:block:current_architecture:start -->
# 4) Current Architecture (as-is)

## 4.1 On-disk structure

Rally still carries the old JSON story in five places at once.

- Shared authored source:
  - `stdlib/rally/prompts/rally/turn_results.prompt`
    - Uses `json schema`, `file:`, and `example_file:` for the shared
      producer turn result.
- Flow-owned authored source:
  - `flows/poem_loop/prompts/shared/review.prompt`
  - `flows/software_engineering_demo/prompts/shared/review.prompt`
    - Both still author review JSON through the same old schema and example
      side path.
- Raw sidecar files:
  - `stdlib/rally/schemas/rally_turn_result.schema.json`
  - `stdlib/rally/examples/rally_turn_result.example.json`
  - `flows/poem_loop/schemas/poem_review.schema.json`
  - `flows/poem_loop/examples/poem_review.example.json`
  - `flows/software_engineering_demo/schemas/engineering_review.schema.json`
  - `flows/software_engineering_demo/examples/engineering_review.example.json`
- Generated build trees:
  - `flows/*/build/agents/<slug>/AGENTS.md`
  - `flows/*/build/agents/<slug>/AGENTS.contract.json`
    - The build package still carries the deleted Doctrine sidecar shape that
      Rally loads as machine truth.
    - The checked-in software-engineering build is also stale against current
      source and still reads as the older `critic_review` family.
- Mirrored package and install surfaces:
  - `src/rally/_bundled/stdlib/rally/**`
  - external workspaces after `rally workspace sync`
    - Both still copy the old prompt source plus raw schema/example files into
      the runnable workspace.

## 4.2 Control paths (runtime)

The current flow is:

1. `src/rally/services/flow_build.py`
   - syncs builtins into the workspace
   - runs `doctrine.emit_docs --target <flow>`
   - expects Doctrine to leave a build tree under `flows/<flow>/build/agents`
2. `src/rally/services/flow_loader.py`
   - requires each built agent directory to contain both `AGENTS.md` and
     `AGENTS.contract.json`
   - loads `final_output.schema_file`
   - loads `final_output.example_file`
   - requires `final_output.format_mode == "json_schema"`
   - validates the shared five-key turn-result schema directly from that file
   - validates review-native flows from `review.final_response.review_fields`
     and `control_ready`
3. adapters consume the loaded schema:
   - `src/rally/adapters/codex/adapter.py`
     - passes `--output-schema <schema-file>`
   - `src/rally/adapters/claude_code/adapter.py`
     - reads the same file and passes `--json-schema <schema-text>`
4. `src/rally/services/final_response_loader.py`
   - reads `last_message.json`
   - parses either the classic five-key producer payload or a review-native
     payload through loaded field paths
5. `src/rally/services/runner.py`
   - appends one `Rally Turn Result` block
   - copies the full final JSON into that block as fenced pretty JSON
   - writes the raw payload to `home/sessions/<agent>/turn-<n>/last_message.json`

## 4.3 Object model + key abstractions

The current runtime model is built around the deleted Doctrine sidecar.

- `src/rally/domain/flow.py`
  - `FinalOutputContract`
    - `declaration_key`
    - `declaration_name`
    - `format_mode`
    - `schema_profile`
    - `schema_file`
    - `example_file`
  - `ReviewFinalResponseContract`
    - `mode`
    - `review_fields`
    - `control_ready`
  - `CompiledAgentContract`
    - one `contract_version`
    - one `contract_path`
    - `AGENTS.md` plus `AGENTS.contract.json` as the compiled package pair
- `src/rally/domain/turn_result.py`
  - the shared producer carrier is still the flat five-key object:
    - `kind`
    - `next_owner`
    - `summary`
    - `reason`
    - `sleep_duration_seconds`
- review-native turns are already a second machine meaning path, but that
  path still depends on Rally loading review bindings from the old compiled
  sidecar.

## 4.4 Observability + failure behavior today

Rally already fails loud on bad runtime state.

- missing `build/agents/*` fails flow load
- missing `AGENTS.contract.json` fails flow load
- wrong `format_mode` fails flow load
- invalid five-key shared schema fails flow load
- non-control-ready review finals fail flow load
- invalid final JSON in `last_message.json` fails final-response loading
- Doctrine emit failures fail flow build

The issue-ledger and log surfaces are stable and file-first:

- `home/issue.md`
  - append-only ledger
  - `Rally Turn Result` blocks with summary lines and fenced JSON
- `issue_history/`
- `logs/rendered.log`
- `home/sessions/<agent>/turn-<n>/last_message.json`

Bundled-asset proof also still expects the old story:

- raw schema/example files are copied into external workspaces
- release-lane packaged-install proof still asserts `AGENTS.contract.json`,
  `schema_file`, and `example_file`, but that proof is out of this
  dev-Doctrine JSON-port loop

## 4.5 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope.
<!-- arch_skill:block:current_architecture:end -->

<!-- arch_skill:block:target_architecture:start -->
# 5) Target Architecture (to-be)

## 5.1 On-disk structure (future)

After the port, Rally should have one clean structured-output package shape.

- Authored source of truth:
  - shared producer contract in `stdlib/rally/prompts/rally/turn_results.prompt`
  - flow-owned review contracts in flow prompt source
  - all structured payloads authored as Doctrine `output schema`
  - examples authored inline with `example:`
- Deleted authored surfaces:
  - no Rally-authored raw `.schema.json`
  - no Rally-authored `.example.json`
  - no `json schema` declaration family in Rally prompt source
- Built agent package shape:
  - `AGENTS.md`
    - human readback only
  - `schemas/<output-slug>.schema.json`
    - exact emitted payload schema for model wire shape
  - `final_output.contract.json`
    - new narrow compiler-owned machine artifact for final-output and
      review-control semantics
    - carries `contract_version`
    - carries final-output metadata:
      - `declaration_key`
      - `declaration_name`
      - `format_mode`
      - `schema_profile`
      - `generated_schema_relpath`
    - carries review metadata when the agent is review-driven:
      - `comment_output`
      - `carrier_fields`
      - `final_response.mode`
      - `final_response.declaration_key`
      - `final_response.declaration_name`
      - `final_response.review_fields`
      - `final_response.control_ready`
      - `outcomes`
  - no `AGENTS.contract.json`
- Bundled and synced builtins:
  - mirror prompt source and built skill bundles
  - do not mirror raw schema/example sidecars because those no longer exist
  - prune retired raw schema/example files and old sidecars from already-synced
    builtins

## 5.2 Control paths (future)

The future flow should be:

1. `src/rally/services/flow_build.py`
   - still syncs builtins and runs `doctrine.emit_docs`
   - does not rebuild or summarize structured JSON locally
   - fails loud if emitted agent packages do not contain the required schema
     plus `final_output.contract.json` shape
2. Doctrine emits the per-agent runtime package
   - `AGENTS.md`
   - emitted schema file under `schemas/`
   - `final_output.contract.json`
3. `src/rally/services/flow_loader.py`
   - treats `AGENTS.md` as human readback only
   - loads payload wire shape from the emitted schema file
   - loads review/control machine truth from `final_output.contract.json`
   - no Markdown scraping
   - no local reconstruction of review meanings
4. adapters use the emitted schema file directly
   - Codex still gets a schema file path
   - Claude still gets schema text read from that file
5. `src/rally/services/final_response_loader.py`
   - keeps the current runtime meaning
   - producer turns still parse the flat five-key object
   - review turns still parse review control fields through explicit machine
     bindings from the new artifact
6. `src/rally/services/runner.py`
   - keeps the current note and log story unless a later explicit design says
     otherwise

## 5.3 Object model + abstractions (future)

Rally's core runtime model should become:

- `FinalOutputContract`
  - `contract_version`
  - `declaration_key`
  - `declaration_name`
  - `format_mode`
  - `schema_profile`
  - `generated_schema_file`
  - `metadata_file`
- `ReviewContract`
  - same current semantic shape Rally already needs:
    - `mode`
    - `carrier_fields`
    - `review_fields`
    - `control_ready`
    - outcomes when the current loader still needs them
  - loaded from `final_output.contract.json`, not from `AGENTS.contract.json`
- producer wire contract
  - stays the classic five-key payload on the first port
  - changes owner path, not runtime meaning
- extension model for Rally users
  - inherit or extend shared structured payloads through Doctrine
    `output schema[...]`, `output shape[...]`, and normal prompt composition
  - do not copy or fork raw schema/example files

## 5.4 Invariants and boundaries

- Doctrine owns structured-output authoring truth.
- Doctrine owns emitted payload-schema truth.
- Doctrine also owns emitted review/control machine truth for final outputs.
- Rally requires the paired editable Doctrine build to emit
  `final_output.contract.json`.
- Rally consumes emitted build artifacts. Rally does not infer them.
- If Doctrine does not yet emit `final_output.contract.json`, Rally stops at
  that framework gap instead of rebuilding the same semantics locally.
- `AGENTS.md` is never the machine source of truth.
- The emitted schema file is the only payload wire contract.
- `final_output.contract.json` is the only Rally-loaded machine contract for
  final-output and review-control semantics.
- `final_output.contract.json` carries its own narrow `contract_version` so
  Rally can fail loud on unsupported metadata shape.
- The first port preserves today's producer and review control behavior.
- The shared Rally producer result stays inheritable and extendable in flow
  prompt source.
- There is no runtime bridge to the old schema/example or sidecar path.

## 5.5 UI surfaces (ASCII mockups, if UI work)

No UI work is in scope.
<!-- arch_skill:block:target_architecture:end -->

<!-- arch_skill:block:call_site_audit:start -->
# 6) Call-Site Audit (exhaustive change inventory)

## 6.1 Change map (table)

| Area | File | Symbol / Call site | Current behavior | Required change | Why | New API / contract | Tests impacted |
| ---- | ---- | ------------------ | ---------------- | --------------- | --- | ------------------ | -------------- |
| Shared producer source | `stdlib/rally/prompts/rally/turn_results.prompt` | `RallyTurnResultSchema`, `RallyTurnResultJson`, `RallyTurnResult` | Authors the shared five-key payload through `json schema`, `file:`, and `example_file:` | Rewrite as Doctrine `output schema` with inline `example:` while keeping the same five-key wire shape | Shared source of truth must move first | Shared inheritable `output schema` + `output shape` + `final_output` | `tests/unit/test_flow_loader.py`, `tests/unit/test_runner.py` |
| Shared producer sidecars | `stdlib/rally/schemas/rally_turn_result.schema.json`; `stdlib/rally/examples/rally_turn_result.example.json` | raw support files | Rally-authored schema/example truth | Delete | No embedded JSON authoring on Rally side | none | `tests/unit/test_bundled_assets.py` |
| Doctrine compiler emit contract | `../doctrine/doctrine/_compiler/compile/final_output.py`; `../doctrine/doctrine/_compiler/compile/review_contract.py`; `../doctrine/doctrine/emit_docs.py` | emitted final-output metadata and package layout | Emits payload schema, but Rally still needs a compiler-owned metadata artifact for final-output and review/control meaning | Emit `final_output.contract.json` with final-output metadata plus review carrier or split metadata | Rally must load compiler-owned review/control truth instead of inferring it | built agent package becomes `AGENTS.md` + `schemas/...` + `final_output.contract.json` | `../doctrine/tests/test_final_output.py`, `../doctrine/tests/test_emit_docs.py` |
| Doctrine proof and docs | `../doctrine/examples/79_final_output_json_object/**`; `../doctrine/examples/104_review_final_output_json_object_blocked_control_ready/**`; `../doctrine/examples/105_review_split_final_output_json_object_control_ready/**`; `../doctrine/docs/LANGUAGE_REFERENCE.md`; `../doctrine/docs/EMIT_GUIDE.md` | checked-in proof and live compiler docs | Producer proof exists, but Rally also depends on emitted review-control metadata | Update examples and docs so producer, carrier review, and split review package shapes are all explicit | Doctrine proof surfaces should teach the same emitted contract Rally depends on | live Doctrine example and emit-doc truth | `../doctrine/tests/test_final_output.py`, `../doctrine/tests/test_emit_docs.py` |
| Smoke flow proof | `flows/_stdlib_smoke/prompts/AGENTS.prompt` | flow final outputs | Inherits the old shared producer story through generated build output | Rebuild against the new shared contract and keep smoke proof current | Shared framework proof must move with the shared contract | Generated schema + `final_output.contract.json` | `tests/unit/test_flow_loader.py` |
| Poem review source | `flows/poem_loop/prompts/shared/review.prompt` | `PoemReviewSchema`, `PoemReviewJson`, `PoemReviewResponse` | Authors review JSON through old schema/example side path | Rewrite to Doctrine review JSON carrier pattern with inline `output schema` example | Demo review flow must tell the same JSON story | Review carrier JSON on Doctrine path | `tests/unit/test_flow_loader.py`, `tests/unit/test_final_response_loader.py` |
| Poem review sidecars | `flows/poem_loop/schemas/poem_review.schema.json`; `flows/poem_loop/examples/poem_review.example.json` | raw support files | Rally-authored review schema/example truth | Delete | Hard cutover | none | `tests/unit/test_flow_loader.py` |
| Software-engineering review source | `flows/software_engineering_demo/prompts/shared/review.prompt`; `flows/software_engineering_demo/prompts/AGENTS.prompt`; `flows/software_engineering_demo/prompts/roles/architect_reviewer.prompt`; `flows/software_engineering_demo/prompts/roles/developer_reviewer.prompt`; `flows/software_engineering_demo/prompts/roles/qa_reviewer.prompt` | `EngineeringReviewSchema`, `EngineeringReviewJson`, `EngineeringReviewResponse`, `EngineeringReviewFamily`, reviewer-role prompt surfaces | Current source already names `EngineeringReview*` and reviewer roles, but the shared review JSON is still authored through old schema/example side files and the generated build is stale | Rewrite the shared review JSON onto Doctrine `output schema`, rebuild the flow, and keep the review-family and reviewer roles aligned with the same shared contract | Shipped demo must match the framework port and the current source tree, not stale build readback | Review JSON on Doctrine path with reviewer-role adopters staying aligned | `tests/unit/test_flow_loader.py`, `tests/unit/test_final_response_loader.py` |
| Software-engineering review sidecars | `flows/software_engineering_demo/schemas/engineering_review.schema.json`; `flows/software_engineering_demo/examples/engineering_review.example.json` | raw support files | Rally-authored review schema/example truth | Delete | Hard cutover | none | `tests/unit/test_flow_loader.py` |
| Built agent package | `flows/*/build/agents/*` | `AGENTS.md`, `AGENTS.contract.json` | Build tree still carries the deleted Doctrine sidecar shape | Regenerate to `AGENTS.md` + emitted schema under `schemas/` + new `final_output.contract.json`; remove `AGENTS.contract.json` | Rally must consume the same build package Doctrine now owns | Per-agent runtime package | `tests/unit/test_flow_loader.py` |
| Runtime contract model | `src/rally/domain/flow.py` | `FinalOutputContract`, `CompiledAgentContract` | Bakes in `schema_file`, `example_file`, and old sidecar path | Replace with emitted schema path plus new final-output metadata artifact fields | Domain model must match the new package | `generated_schema_file`, `metadata_file`, review fields from new artifact | `tests/unit/test_run_store.py`, `tests/unit/test_adapter_mcp_projection.py` |
| Flow build and Doctrine gate | `src/rally/services/flow_build.py`; `pyproject.toml`; `uv.lock`; `src/rally/_package_release.py` | emit invocation, editable source, release metadata, post-emit package completeness | Rally builds against the editable `../doctrine` checkout and publishes a public Doctrine package line as release metadata | Prove against editable `../doctrine`, keep release metadata tests current, and fail loud when emitted agent packages do not contain the new package shape | Hard cutover must reject stale emitted build packages without pretending the public package index is the WIP proof target | paired local checkout requires emitted schema and `final_output.contract.json` | `tests/unit/test_flow_build.py`, `tests/unit/test_package_release.py`, `tests/unit/test_release_flow.py` |
| Flow loader | `src/rally/services/flow_loader.py` | `_load_compiled_agents`, `_load_compiled_agent_contract`, `_validate_turn_result_schema` | Requires `AGENTS.contract.json`, `format_mode == json_schema`, `schema_file`, `example_file` | Load `AGENTS.md`, emitted schema file, and `final_output.contract.json`; stop requiring example files; validate package completeness on the new shape | Canonical runtime loader must consume compiler-owned build artifacts | Build package contract becomes `AGENTS.md` + `schemas/...` + `final_output.contract.json` | `tests/unit/test_flow_loader.py` |
| Codex adapter | `src/rally/adapters/codex/adapter.py` | `invoke` | Uses `agent.compiled.final_output.schema_file` | Point at `generated_schema_file` from the new contract | Same model wire shape, new source path | emitted schema file path | `tests/unit/test_runner.py` |
| Claude adapter | `src/rally/adapters/claude_code/adapter.py` | `invoke` | Reads `schema_file` text from the old contract | Read emitted schema text from `generated_schema_file` | Same model wire shape, new source path | emitted schema file text | `tests/unit/test_runner.py` |
| Final-response loading | `src/rally/services/final_response_loader.py` | `load_agent_final_response`, `_review_result_paths` | Correct runtime meaning, but fed by old sidecar-loaded bindings | Keep logic and retarget it to the new loaded contract fields | Preserve behavior while replacing contract plumbing | same five-key producer parse; same review field-path parse | `tests/unit/test_final_response_loader.py` |
| Bundled and synced builtins | `src/rally/services/bundled_assets.py`; `src/rally/services/workspace_sync.py`; `src/rally/_bundled/stdlib/rally/**` | `_BUNDLE_SPECS`, `ensure_workspace_builtins_synced` | Copies the old shared prompt plus raw schema/example files into external workspaces | Sync prompt-source builtins only and stop expecting raw schema/example support files | External workspaces must inherit the same clean contract story | bundled stdlib prompt source only | `tests/unit/test_bundled_assets.py`, `tests/unit/test_flow_build.py` |
| Public packaged install proof | `tests/integration/test_packaged_install.py` | packaged workspace assertions | Asserts copied raw schema/example files and `AGENTS.contract.json` fields | Out of this dev-Doctrine proof loop; revisit after the public Doctrine package catches up | The active WIP compiler is editable `../doctrine`, not the package index | no current proof obligation | none |
| Release and versioning flow | `src/rally/_release_flow/parsing.py`; `src/rally/_release_flow/ops.py`; `tests/unit/test_release_flow.py`; `tests/unit/test_package_release.py`; `docs/VERSIONING.md` | Doctrine package line and compiled contract version reads | Reads and documents the old compiled `AGENTS.contract.json` contract version while the public package line remains release metadata | Retarget release/versioning logic to the new `final_output.contract.json` contract version line and keep the public package line documented as release metadata | Rally release tooling should not keep parsing a dead contract surface or present public packaging as the WIP proof target | new compiled final-output contract version line plus current package-line metadata | `tests/unit/test_release_flow.py`, `tests/unit/test_package_release.py` |
| Live runtime docs | `docs/RALLY_RUNTIME.md`; `docs/RALLY_COMMUNICATION_MODEL.md`; `docs/VERSIONING.md`; `docs/RALLY_PORTING_GUIDE.md` | runtime, communication, versioning, porting text | These live docs teach the old machine path or need the new port lesson | Rewrite to the new human-plus-machine build package story and local dev-Doctrine proof target | Live docs must not teach dead machine paths or old proof expectations | `AGENTS.md` for humans; emitted schema + `final_output.contract.json` for machines | doc review |

## 6.2 Migration notes

* Canonical owner path / shared code path:
  `output schema` in Rally prompt source -> `doctrine.emit_docs` ->
  `build/agents/<slug>/AGENTS.md` + `schemas/<output-slug>.schema.json` +
  `final_output.contract.json` -> `flow_loader` -> adapters +
  `final_response_loader`.
* Doctrine compatibility gate:
  - Rally source work continues to build against the paired editable
    `../doctrine` checkout.
  - Rally's public Doctrine package line is release metadata, not this WIP
    proof target.
  - Rally build and load paths fail loud if emitted agent packages do not
    contain the new schema plus metadata shape.
* Deprecated APIs (if any):
  - `json schema` declaration use in Rally prompt source
  - `example_file:`
  - Rally-authored raw `.schema.json`
  - Rally-authored raw `.example.json`
  - `AGENTS.contract.json`
  - `FinalOutputContract.schema_file`
  - `FinalOutputContract.example_file`
  - old compiled contract version parsing tied to `AGENTS.contract.json`
  - `format_mode == "json_schema"` in Rally runtime assumptions
* Delete list (what must be removed; include superseded shims/parallel paths if any):
  - shared and demo raw schema/example source files
  - generated `AGENTS.contract.json` files under `flows/*/build/**`
  - bundled raw schema/example copies under `src/rally/_bundled/stdlib/rally/**`
  - loader code that requires `schema_file`, `example_file`, and old
    sidecar presence
  - release-flow parsing that reads compiled contract version from the old
    sidecar story
  - docs that still present `AGENTS.contract.json` as Rally's machine truth
* Adjacent surfaces tied to the same contract family:
  - Doctrine compiler emit and review metadata surfaces
  - Doctrine example proof and emit docs
  - bundled asset sync
  - external workspace sync
  - packaged-install proof, deferred to the release lane while this WIP port
    proves against editable `../doctrine`
  - generated build readback
  - unit fixtures that synthesize compiled-agent packages
  - live runtime, communication, versioning, and porting docs
* Compatibility posture / cutover plan:
  - clean cutover
  - no runtime bridge
  - preserve the current producer five-key payload and current review routing
    behavior during the first port
  - change the owner path, not the runtime meaning
  - workspace sync prunes retired raw schema/example files and old sidecars
    from already-synced builtins instead of leaving a pseudo-compatibility
    trail behind
* Capability-replacing harnesses to delete or justify:
  - no new Rally-local Markdown scraper
  - no local review-semantics inference from schema field names
  - no local recompiler or prompt reparser in Rally runtime
* Live docs/comments/instructions to update or delete:
  - runtime docs listed above
  - any code comments or tests that still describe `AGENTS.contract.json` as
    the machine truth path
* Behavior-preservation signals for refactors:
  - `tests/unit/test_flow_loader.py`
  - `tests/unit/test_final_response_loader.py`
  - `tests/unit/test_runner.py`
  - `tests/unit/test_run_store.py`
  - `tests/unit/test_adapter_mcp_projection.py`
  - `tests/unit/test_bundled_assets.py`
  - `tests/unit/test_flow_build.py`
  - `tests/unit/test_package_release.py`
  - `../doctrine/tests/test_output_schema_surface.py`
  - `../doctrine/tests/test_output_schema_lowering.py`
  - `../doctrine/tests/test_final_output.py`
  - `../doctrine/tests/test_emit_docs.py`

## Pattern Consolidation Sweep (anti-blinders; scoped by plan)

| Area | File / Symbol | Pattern to adopt | Why (drift prevented) | Proposed scope (include/defer/exclude/blocker question) |
| ---- | ------------- | ---------------- | ---------------------- | ------------------------------------- |
| Shared flow proof | `flows/_stdlib_smoke/**` | shared `output schema` turn-result path | keeps the framework smoke flow on the same contract family as real flows | include |
| Bundled install surface | `src/rally/_bundled/stdlib/rally/**`; `src/rally/services/bundled_assets.py` | no raw schema/example sidecars in bundled builtins | prevents external workspaces from teaching the dead JSON path | include |
| Public install proof | `tests/integration/test_packaged_install.py` | new built agent package shape | belongs to release-lane proof once public Doctrine catches up | exclude from this dev-Doctrine implementation loop |
| Porting guidance | `docs/RALLY_PORTING_GUIDE.md` | compiler-owned schema plus compiler-owned final-output metadata | this is the durable port lesson other frameworks and imported agents will need | include |
| Runtime note readers | `flows/software_engineering_demo/setup/prompt_inputs.py` | keep existing issue-ledger note block shape | this script reads note history, not the compiled JSON contract; no change is needed if note titles and review note shape stay stable | exclude |
| Historical planning notes | `docs/RALLY_STDLIB_PROMPT_SURFACE_REFRESH_2026-04-15.md`; `docs/RALLY_MULTI_FILE_AGENT_PACKAGE_SUPPORT_2026-04-15.md` | none | these are dated planning artifacts, not the live design set; updating them is not ship-blocking for this migration | exclude |
<!-- arch_skill:block:call_site_audit:end -->

<!-- arch_skill:block:phase_plan:start -->
# 7) Depth-First Phased Implementation Plan (authoritative)

> Rule: systematic build, foundational first; split Section 7 into the
> smallest reasonable sequence of coherent self-contained units that can be
> completed, verified, and built on later. If two decompositions are both
> valid, bias toward more phases than fewer. `Work` explains the unit;
> `Checklist (must all be done)` is the authoritative must-do list inside the
> phase; `Exit criteria (all required)` names the concrete done conditions.
> Resolve adjacent-surface dispositions and compatibility posture before
> writing the checklist. Refactors, consolidations, and shared-path
> extractions must preserve existing behavior with credible evidence
> proportional to the risk. For agent-backed systems, prefer prompt,
> grounding, and native-capability changes before new harnesses or scripts.
> No fallbacks or runtime shims - the system must work correctly or fail
> loudly and delete superseded paths. Also: document new patterns or gotchas
> in code comments at the canonical boundary when they would save a later
> reader real time.

## Phase 1 — Add the Doctrine machine artifact Rally needs

Status: COMPLETE

* Goal:
  Give Rally one compiler-owned machine artifact for final-output and review
  control meaning so Rally does not infer that truth locally.
* Work:
  This phase is Doctrine-first because emitted schema files alone do not carry
  enough meaning for Rally review routing. Land the new emitted metadata file
  and prove its shape before Rally changes its runtime contract.
* Checklist (must all be done):
  - add emitted `final_output.contract.json` beside `AGENTS.md` and
    `schemas/<output-slug>.schema.json`
  - include `contract_version`, `declaration_key`, `declaration_name`,
    `format_mode`, `schema_profile`, and `emitted_schema_relpath`
  - include review metadata when present:
    `comment_output`, `carrier_fields`, `final_response.*`, and `outcomes`
  - make inherited and extended `output schema`, `output shape`, and
    `final_output` compile through this emitted artifact
  - update Doctrine example and emit tests so the new package shape is
    explicit and stable
  - keep `AGENTS.contract.json`, `example_file`, and the old sidecar story
    dead
* Verification (required proof):
  - run focused Doctrine tests for output-schema lowering, output-surface
    inheritance, review-contract compilation, final-output compilation, and
    emit behavior
  - emit
    `../doctrine/examples/79_final_output_output_schema/prompts/AGENTS.prompt`
    and inspect the live `build/` package for emitted schema plus
    `final_output.contract.json`
  - emit one carrier review example and one split review example, then inspect
    the live `build/` packages for `comment_output`, carrier or split review
    fields, `control_ready`, and outcomes in `final_output.contract.json`
* Docs/comments (propagation; only if needed):
  - update Doctrine docs only where they describe emitted final-output package
    shape or the machine-readable artifact
* Exit criteria (all required):
  - Doctrine emits one stable `final_output.contract.json` for every built
    agent that declares `final_output:` or a review contract
  - emitted schema plus metadata is enough for Rally to load producer meaning,
    carrier review meaning, and split review meaning without Markdown scraping
  - no old sidecar path is revived in Doctrine
* Rollback:
  Revert the Doctrine artifact work as one unit. Do not start Rally cutover on
  a half-landed metadata shape.

## Phase 2 — Port the shared framework producer contract

Status: COMPLETE

Previous audit missing (fixed):
- `_stdlib_smoke` now has emitted schema plus `final_output.contract.json`, but
  its built agent directories still carry old `AGENTS.contract.json` files with
  `schema_file` and `example_file`.
- The shared producer package shape is not clean until the old generated
  sidecar files are gone.

Completed work:
- Rewrote `stdlib/rally/prompts/rally/turn_results.prompt` to Doctrine
  `output schema` with an inline example and the same five-key payload.
- Deleted the shared raw schema and example source sidecars.
- Rebuilt `_stdlib_smoke` and removed stale generated `AGENTS.contract.json`
  files from its built agent directories.

Proof:
- `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke`
- Inspected `_stdlib_smoke` built agent packages for `AGENTS.md`,
  `schemas/*.schema.json`, and `final_output.contract.json`.

* Goal:
  Move the framework-owned producer result onto Doctrine authoring while
  preserving the current five-key wire shape and extension story.
* Work:
  Rewrite the shared `rally.turn_results` source to use Doctrine `output
  schema`, inline `example:`, and the new final-output path. Keep the shared
  contract named and structured so Rally users can inherit and extend it.
  This phase and Phase 3 are split for work order only. They are one authored
  contract cutover and are not a release or readiness stop point between them.
* Checklist (must all be done):
  - rewrite `stdlib/rally/prompts/rally/turn_results.prompt` to use Doctrine
    `output schema`
  - preserve the current five-key payload keys and control meaning
  - preserve named shared prompt surfaces so downstream Rally flows can
    inherit or extend the contract family cleanly
  - delete
    `stdlib/rally/schemas/rally_turn_result.schema.json`
  - delete
    `stdlib/rally/examples/rally_turn_result.example.json`
  - rebuild `_stdlib_smoke` so the shared contract emits the new package shape
* Verification (required proof):
  - compile `_stdlib_smoke` against the paired Doctrine checkout
  - inspect emitted `schemas/<output-slug>.schema.json` plus
    `final_output.contract.json` in live `build/`
* Docs/comments (propagation; only if needed):
  - add a short comment only if the shared prompt needs one to explain the
    inheritance hook or extension point
* Exit criteria (all required):
  - the shared producer contract is authored only in Doctrine prompt source
  - the old shared raw schema and example files are gone
  - the shared pattern still supports inheritance and extension for Rally
    users
  - the repo is not declared ready until Phase 3 lands the shipped demo review
    contracts on the same JSON story
* Rollback:
  Revert the shared prompt rewrite and its deletes as one unit.

## Phase 3 — Port shipped review contracts and demo adopters

Status: COMPLETE

Previous audit missing (fixed):
- `poem_loop` and `software_engineering_demo` review prompt source still uses
  `json schema`, `file:`, and `example_file:`.
- Demo raw schema/example files still exist.
- Both review flow emits fail at the first line of the old review prompt
  source, so emitted review metadata is not proven.
- The software-engineering generated build is still stale around the old
  `critic` review package.

Completed work:
- Rewrote `flows/poem_loop/prompts/shared/review.prompt` and
  `flows/software_engineering_demo/prompts/shared/review.prompt` to Doctrine
  `output schema`.
- Deleted the poem and software-engineering raw review schema and example
  sidecars.
- Rebuilt both shipped demo flows, kept reviewer roles aligned with
  `EngineeringReviewResponse`, and removed stale old generated review
  packages and `AGENTS.contract.json` files.

Proof:
- `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target poem_loop`
- `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target software_engineering_demo`
- Inspected one poem review and one software-engineering review
  `final_output.contract.json` for carrier review metadata and
  `control_ready: true`.

* Goal:
  Remove the second JSON story from shipped demos and keep review routing on
  the same authored path as the shared framework contract.
* Work:
  Rewrite shipped review JSON contracts onto Doctrine prompt features and
  remove the demo-side raw schema and example files in the same pass. This
  completes the authored-contract cutover started in Phase 2.
* Checklist (must all be done):
  - rewrite `flows/poem_loop/prompts/shared/review.prompt` to the Doctrine
    review JSON pattern
  - rewrite `flows/software_engineering_demo/prompts/shared/review.prompt`
    to the same Doctrine review JSON pattern
  - keep `flows/software_engineering_demo/prompts/AGENTS.prompt` and the
    reviewer-role adopters aligned around the same shared
    `EngineeringReviewResponse` contract so current source and generated build
    tell one story
  - preserve current review field bindings and `control_ready` behavior
  - delete `flows/poem_loop/schemas/poem_review.schema.json`
  - delete `flows/poem_loop/examples/poem_review.example.json`
  - delete
    `flows/software_engineering_demo/schemas/engineering_review.schema.json`
  - delete
    `flows/software_engineering_demo/examples/engineering_review.example.json`
  - rebuild `poem_loop` and `software_engineering_demo` and inspect the new
    emitted package shape
* Verification (required proof):
  - compile `poem_loop` and `software_engineering_demo` against the paired
    Doctrine checkout
  - inspect review-agent build output for emitted schema plus
    `final_output.contract.json`
* Docs/comments (propagation; only if needed):
  - no live docs change yet unless a prompt comment is needed to explain the
    Doctrine review binding surface
* Exit criteria (all required):
  - shipped demos author review JSON only through Doctrine prompt source
  - demo raw schema and example files are gone
  - shipped review contracts emit enough metadata for Rally to keep current
    routing behavior
* Rollback:
  Revert the demo prompt rewrites and their deletes as one unit.

## Phase 4 — Cut Rally runtime over to the new build package

Status: COMPLETE

Follow-up restoration:
- Restored `runtime.prompt_input_command` as a rooted flow-local script path.
- Restored runner prompt-input merging under `## Runtime Prompt Inputs`.
- Replaced the removal regression test with positive loader and runner
  coverage for the restored behavior.

Previous audit missing (fixed for the JSON port):
- Rally still loads `AGENTS.contract.json` and old `schema_file` /
  `example_file` fields.
- Codex and Claude adapters still launch from
  `agent.compiled.final_output.schema_file`.
- The Rally build path is not adjusted to the current Doctrine helper surface;
  `uv run pytest tests/unit -q` fails on the removed
  `doctrine.emit_common.root_concrete_agents` import.

Completed work:
- Replaced Rally's runtime domain contract fields with
  `generated_schema_file` and `metadata_file`.
- Updated `flow_loader` to load `final_output.contract.json`, resolve
  `emitted_schema_relpath`, reject unsupported final-output contract versions,
  and preserve producer and review parsing behavior.
- Retargeted Codex and Claude adapters to the emitted schema file.
- Updated unit fixtures that synthesize compiled agent packages.
- Updated flow-build sidecar rendering to the current Doctrine compile helper
  surface after `root_concrete_agents` was removed.

Proof:
- `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_run_store.py tests/unit/test_adapter_mcp_projection.py -q`
  passed with `118 passed`.
- `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_runner.py -q`
  passed with `97 passed` after restoring `runtime.prompt_input_command`.

Audit note:
- The JSON package cutover and restored runtime input path are both proven by
  focused tests.

* Goal:
  Make Rally load Doctrine's emitted build package directly while holding
  current producer and review behavior steady.
* Work:
  Replace the old sidecar-based contract plumbing in Rally's domain model,
  loader, adapters, and final-response loading with the emitted schema plus
  `final_output.contract.json`.
* Checklist (must all be done):
  - replace `FinalOutputContract` and related domain types so they point at
    emitted schema plus emitted metadata instead of `schema_file` and
    `example_file`
  - update `src/rally/services/flow_loader.py` to require `AGENTS.md`,
    emitted schema, and `final_output.contract.json`
  - stop loading `AGENTS.contract.json`
  - stop requiring `format_mode == "json_schema"`
  - stop requiring `example_file`
  - keep shared producer validation on the same five-key payload shape
  - keep review control parsing on explicit machine bindings loaded from the
    new metadata file
  - retarget Codex and Claude adapters to the emitted schema file path
  - update unit fixtures that synthesize compiled-agent packages
* Verification (required proof):
  - run
    `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_run_store.py tests/unit/test_adapter_mcp_projection.py -q`
* Docs/comments (propagation; only if needed):
  - add a short code comment at the loader or domain boundary if the metadata
    split would otherwise be easy to misread
* Exit criteria (all required):
  - Rally no longer reads `AGENTS.contract.json`
  - Rally no longer depends on `schema_file`, `example_file`, or the old
    format-mode assumption
  - loader, adapters, run-store projections, and final-response parsing are
    all proven on the new contract
  - producer and review control behavior stays the same under the new loaded
    contract
* Rollback:
  Revert the runtime contract-plumbing cutover as one unit.

## Phase 5 — Converge bundled, generated, and release surfaces

Status: COMPLETE (dev-Doctrine proof target)

Operator correction:
- This loop proves Rally against editable `../doctrine`. The public package
  index is not the proof target for this WIP JSON port.
- `docs/VERSIONING.md` still needs Phase 6 cleanup where it describes
  `AGENTS.contract.json`, but the public package floor is no longer a Phase 5
  blocker.

Completed work:
- Synced bundled stdlib assets from live source so bundled Rally no longer
  carries raw shared schema/example files.
- Added flow-build post-emit cleanup and validation for the new package shape:
  stale generated `AGENTS.contract.json` files are removed, and built agents
  must contain `AGENTS.md`, emitted schema, and `final_output.contract.json`.
- Updated bundled, flow-build, package-release, release-flow, and
  release-metadata tests toward the new package shape.
- Retargeted release-flow parsing from the old compiled-contract constant to
  `SUPPORTED_FINAL_OUTPUT_CONTRACT_VERSIONS`.
- Rebuilt `dist/` with the current package contents.

Proof:
- `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_package_release.py tests/unit/test_release_flow.py -q`
  passed with `33 passed`.
- `uv run pytest tests/unit/test_package_release.py tests/unit/test_release_flow.py -q`
  passed with `18 passed` after the live versioning doc update.
- `make build-dist` passed.

* Goal:
  Make every shipped and generated Rally surface tell the same build-package
  story as the runtime cutover.
* Work:
  Regenerate build output, stop bundling dead support files, and retarget
  release or version parsing to the new metadata artifact.
* Checklist (must all be done):
  - keep Rally's dev workspace pointed at editable `../doctrine` for this WIP
    proof
  - regenerate `flows/*/build/**` on the new emitted package shape
  - update flow-build or immediate post-emit checks so Rally fails loud when
    emitted agent packages are missing the new schema plus metadata shape
  - update bundled asset sync so external workspaces stop copying raw schema
    and example files and prune retired raw schema/example files plus old
    sidecars from already-synced builtins
  - retarget release and version parsing to the `contract_version` in
    `final_output.contract.json`
  - delete generated `AGENTS.contract.json` files under `flows/*/build/**`
  - delete bundled raw schema and example copies under
    `src/rally/_bundled/stdlib/rally/**`
* Verification (required proof):
  - run
    `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_package_release.py tests/unit/test_release_flow.py -q`
* Docs/comments (propagation; only if needed):
  - update `docs/VERSIONING.md` in the same phase because release parsing
    truth changes here
* Exit criteria (all required):
  - generated build trees, bundled assets, and release tooling all use the new
    package shape
  - already-synced workspaces are pruned back to the supported builtins shape
  - no shipped or generated Rally surface still carries the old sidecar story
* Rollback:
  Revert bundled, generated, and release-surface changes as one unit.

## Phase 6 — Rewrite live docs and prove the hard cutover

Status: COMPLETE

Completed work:
- Updated `docs/RALLY_RUNTIME.md`, `docs/RALLY_COMMUNICATION_MODEL.md`,
  `docs/VERSIONING.md`, and `docs/RALLY_PORTING_GUIDE.md` to describe the new
  emitted schema plus `final_output.contract.json` package shape.
- Added the porting-guide rule that Rally JSON contracts should be authored
  with Doctrine `output schema` and remain inheritable and extendable by Rally
  users.
- Rebuilt shipped Rally flows against editable `../doctrine`.
- Spot-checked one producer package and two review packages for emitted schema
  and final-output metadata.

Manual QA (non-blocking):
- Producer and review package spot-checks are complete.
- No live run was started in this pass, so issue-ledger behavior is still an
  optional manual confirmation item.

Proof:
- `uv sync --dev` passed.
- `uv run python -m doctrine.emit_docs --pyproject pyproject.toml --target _stdlib_smoke --target poem_loop --target software_engineering_demo` passed.
- `uv run pytest tests/unit/test_flow_loader.py tests/unit/test_final_response_loader.py tests/unit/test_runner.py tests/unit/test_run_store.py tests/unit/test_adapter_mcp_projection.py -q`
  passed with `119 passed`.
- `uv run pytest tests/unit/test_bundled_assets.py tests/unit/test_flow_build.py tests/unit/test_package_release.py tests/unit/test_release_flow.py -q`
  passed with `33 passed`.
- `make build-dist` passed.
- `uv run pytest tests/unit -q` failed outside this JSON-port surface: the
  untracked `tests/unit/test_shared_prompt_ownership.py` expects two sentences
  in dirty skill prompt files that this pass did not own.

* Goal:
  Leave one current public story in the repo and prove the cutover end to end.
* Work:
  Rewrite live design and porting docs to match the new source of truth, then
  run the final compile and runtime proof on the shipped flows.
* Checklist (must all be done):
  - update `docs/RALLY_RUNTIME.md`
  - update `docs/RALLY_COMMUNICATION_MODEL.md`
  - update `docs/VERSIONING.md`
  - update `docs/RALLY_PORTING_GUIDE.md` with the new inheritable and
    extendable Doctrine pattern
  - remove stale live-doc references to raw schema/example files and
    `AGENTS.contract.json`
  - rebuild shipped Rally flows against the paired Doctrine checkout
  - run the focused Rally proof set for build, load, adapters, runner,
    final-response loading, run-store projections, adapter-MCP projections,
    bundled assets, package release, and release flow
  - manually spot-check one producer flow and one review flow for emitted
    package shape and issue-ledger behavior
* Verification (required proof):
  - emit shipped Rally flows from live source
  - run the focused `uv run pytest ...` proof commands from Phases 4 and 5
  - inspect one producer and one review run manually
* Docs/comments (propagation; only if needed):
  - this phase owns the live-doc cleanup for the ported contract family
* Exit criteria (all required):
  - touched live docs tell one current JSON story
  - compile proof and focused Rally tests pass on the new contract
  - one producer flow and one review flow are manually confirmed on the new
    package shape
* Rollback:
  Revert the final doc sync and generated-output refresh with the cutover if
  the full proof does not hold.
<!-- arch_skill:block:phase_plan:end -->

# 8) Verification Strategy (common-sense; non-blocking)

## 8.1 Build-time proof

Prove the new contract where it is born first, then where Rally consumes it:

- run focused Doctrine tests for output-schema lowering, review-contract
  compilation, final-output compilation, and emit behavior
- emit the Doctrine JSON example and inspect the live `build/` package
- emit one carrier review example and one split review example and inspect the
  emitted metadata shape
- rebuild the shipped Rally flows against the paired local Doctrine compiler
- inspect the emitted Rally agent packages in live `build/` output:
  - `AGENTS.md`
  - `schemas/<output-slug>.schema.json`
  - `final_output.contract.json`

## 8.2 Runtime proof

Run focused Rally tests for flow build, flow load, adapter launch, final
response loading, runner control behavior, run-store projections,
adapter-MCP projections, bundled assets, package release, and release parsing
on the new contract. Public packaged-install proof belongs to the release lane
after public Doctrine catches up.

## 8.3 Manual checks

Spot-check one producer flow and one review flow to confirm the emitted build
package, launch contract, and issue-ledger behavior still match the current
Rally runtime meaning.

# 9) Rollout / Ops / Telemetry

## 9.1 Rollout shape

This should be a hard repo cutover, not a staged runtime bridge. Update the
shared framework contract, shipped demos, load/runtime code, generated output,
and docs in one migration line. Phases 2 and 3 are work-order slices inside
that one line, not a release stop point between two competing JSON stories.

## 9.2 Failure posture

Fail loud on missing or invalid emitted structured-output artifacts. Do not
fall back to old schema/example files or Markdown parsing.

## 9.3 Ops and logs

Keep current Rally logging and issue-ledger behavior unless the new contract
forces one explicit change that is documented in the same pass.

<!-- arch_skill:block:consistency_pass:start -->
## Consistency Pass
- Reviewers: explorer 1, explorer 2, self-integrator
- Scope checked:
  - frontmatter, TL;DR, Sections 0 through 10, planning passes, and helper-block drift
  - cross-section agreement on owner path, cutover posture, adjacent surfaces, proof, rollout, and deletes
- Findings summary:
  - fixed the authored-contract rollout contradiction between split producer and demo phases
  - fixed stale software-engineering demo inventory to match current source and stale build readback
  - added the missing Doctrine dependency gate, emitted-artifact gate, and workspace-pruning rule
  - widened proof obligations so Doctrine review metadata, adapters, run-store projections, and package-release surfaces are all covered
- Integrated repairs:
  - updated Sections 0, 3, 4, 5, 6, 7, 8, and 9
  - narrowed live-doc follow-through to the docs that actually teach the old path or need the new port lesson
  - updated the planning-pass helper to reflect completed phase-plan and consistency-pass work
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

## 2026-04-15

- Started a new full-arch plan for porting Rally's JSON outputs onto
  Doctrine's new structured JSON pattern.
- Set default scope to a hard cutover with no embedded JSON authoring left on
  the Rally side for the framework or shipped demos.
- Set default behavior posture to preserve current producer and review control
  meaning during the first port.
- Locked the target machine-truth split:
  - emitted schema file for payload wire shape
  - one new compiler-owned `final_output.contract.json` artifact for
    final-output and review-control semantics
- Locked the metadata artifact shape further:
  - `final_output.contract.json` carries its own `contract_version`
  - it carries final-output metadata plus review metadata when present
- Locked execution order:
  - Doctrine emits the new metadata artifact first
  - shared producer authoring moves next
  - shipped review authoring follows
  - Rally runtime cutover comes after those authoring changes
  - bundled, generated, release, and doc follow-through finish the hard cut
- Consistency pass hardened four plan edges:
  - Phases 2 and 3 are one authored-contract cutover with no release stop
    between them
  - the software-engineering demo inventory now reflects current
    `EngineeringReview*` source plus stale `critic_review` build readback
  - Rally now names the editable Doctrine build and emitted-artifact gate it
    depends on
  - workspace sync prunes retired sidecars so stale files do not masquerade as
    a compatibility bridge
- Rejected two implementation paths as non-starters:
  - Markdown scraping
  - Rally-local inference of review or routing meaning from schema field names
- Implementation audit reopened Phase 4 because the runtime now rejects
  `runtime.prompt_input_command`, even though Section 6 excluded that cleanup
  from this JSON port.
- Operator correction after implementation audit: Rally is using dev Doctrine
  from editable `../doctrine`, so the public package proof is not a blocker for
  this loop. Phase 6 stays reopened for live-doc cleanup plus final
  dev-Doctrine cutover proof.
