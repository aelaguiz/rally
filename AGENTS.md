# AGENTS.md

## First Pass

- Start with `git status --short` and `rg --files flows stdlib skills mcps docs`.
- Treat `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/` as Rally's fixed top-level folders.
- Use the smallest owner for each change:
  - prompt source: `flows/*/prompts/**` and `stdlib/rally/prompts/**`
  - runtime config: `flows/*/flow.yaml`
  - generated readback: `flows/*/build/**`
  - capability definitions: `skills/*/SKILL.md` and `mcps/*/server.toml`

## Setup And Tests

- Sync the Rally repo Python env with `uv sync --dev`.
- Run Rally unit tests with `uv run pytest tests/unit -q`.
- When you change a prepared fixture repo that has its own `pyproject.toml` and `uv.lock`, run that repo's tests from that repo root with `uv run pytest`.
- Do not use bare `python -m pytest` or install `pytest` into the global Python.

## Thin Harness, Sharp Context

- Rally is a thin harness. Its main job is to load the right context, keep the working set small, expose exact tools, and enforce safety.
- Put reusable judgment and repeated procedure in `.prompt` source and `skills/**`, not in runtime glue or repeated prose.
- Put exact execution in CLI commands, setup scripts, helper code, and tests. Do not push deterministic work into narrative prompt text.
- Treat every always-on line as context cost. Give each durable rule one owner. If `stdlib/rally/**`, a skill, a review law, docs, or runtime facts already own it, point to it or inherit it instead of repeating it.
- Prefer direct facts over summaries. If the agent can read `home:issue.md`, the current artifact, git status, or the exact test result, do not add another prose layer that retells it.
- Keep always-on framework rules separate from on-demand depth. Use prompt imports, shared skills, runtime facts, and the docs map as routing tools instead of copying long reference prose into every turn.
- If a best practice should come for free to framework users, land it in Rally-owned shared layers such as `stdlib/rally/**`, Rally runtime, shared skills, or shared docs. Do not hide framework law in one sample flow.
- Root `AGENTS.md` is for framework truth only. Do not smuggle one flow's use case, product rules, or one-turn coaching into repo-wide instructions.
- Before you add a rule, ask: is this real repo truth, the smallest honest owner, new information, and worth the prompt budget on every run?

## Source Of Truth

- Write agent and flow instructions in `.prompt` files. Files under `flows/*/build/**` are generated readback, not hand-written source.
- Rally owns the runtime, CLI, run layout, logs, sessions, adapter rules, and the shared library under `stdlib/rally/`.
- Doctrine owns the general language, compiler, and emitted build output. Treat it as a general framework, not a Rally extension point.
- Every time you write or edit a `.prompt` file, stop and check whether Doctrine already has a built-in way to express the change.
- Prefer Doctrine features such as imports, inheritance, abstract agents, shared inputs or outputs, reviews, workflow laws, and typed outputs over copied prose or Rally-only prompt patterns.
- When a role's main job is review, model it with Doctrine `review` or `review_family` first.
- Use ordinary agent workflow prose for producer work, not for pass-fail review law.
- Use rooted Rally paths in authored source: `home:`, `flow:`, `workspace:`, and `host:`. Rally internals may also use `stdlib:`.
- Do not use bare relative paths in `flow.yaml`, prompt `path:` fields, or MCP path values. In shell commands from the prepared home, plain paths like `repos/demo_repo` are fine.
- Doctrine still owns prompt support-file resolution. Keep prompt `file:` and `example_file:` values in the current compiler-safe form. If rooted support-file paths are missing, stop and discuss the Doctrine gap.
- `home:issue.md` is the only shared run input and note file Rally sanctions by default. Do not add an external brief flag, stdin brief path, or a second shared brief, handoff, or note sidecar unless a flow clearly owns that extra file.
- Rally ends each turn with notes plus one final JSON result. Do not add a second handoff path or another turn-ending return path.
- Keep lasting notes on Rally-owned tools such as the Rally kernel skill and `rally issue note`. Keep route, done, blocker, and sleep truth only in `rally.turn_results`.
- If `stdlib/rally/**` already gives the agent a command, do not repeat that command in flow-local or skill-local prose. Add only local commands or local exceptions.
- Do not add side-door instruction sources or Markdown overlays outside the declared `.prompt` graph.
- Treat the prepared run home as the whole working world. Skills, MCPs, repos, artifacts, sessions, and adapter-local state belong there, not in machine-global Rally state or random filesystem paths.
- Keep Rally-owned state in this repo, especially under `runs/`. Do not create hidden control planes under `~/.rally`, `~/.config`, or similar paths.
- For Codex adapter work, keep the launch rules exact: Rally sets `cwd`, points `CODEX_HOME` at the run home, sets `RALLY_RUN_ID` and `RALLY_FLOW_CODE`, turns off ambient project-doc discovery, and injects compiled prompt output directly.
- Never edit `../doctrine` during Rally work unless the user clearly asks for Doctrine changes in this thread.
- Do not stage, commit, test, clean up, or "just fix" `../doctrine` without that discussion.
- If Rally is blocked on missing Doctrine support, stop in Rally and name the missing framework feature first.

## Framework Design Rules

- Keep Rally CLI-first and filesystem-first. New operator-visible behavior should land in `rally` or repo files, not in a GUI, dashboard, or DB-only path.
- Prefer front-door Rally paths. Notes, logs, history, and similar runtime behavior should flow through Rally-owned CLI and run files such as `home:issue.md` and `issue_history/`, not ad hoc scripts or direct adapter state.
- Fail loud on dirty or unclear runtime state. Do not add silent retries, hidden cleanup, or background auto-heal behavior when Rally can stop with a clear blocker.
- Keep the operator surface small and explicit. Add a new command or runtime path only when it matches a real operator action or proof path.
- Keep one active run per flow unless the design changes on purpose. Do not slip in concurrent active runs as a shortcut.
- Keep run archaeology bundled under `runs/<run-id>/`. If a reader needs to understand a run, the useful files should live there.
- Keep the harness thin. Do not add a second state machine, shadow resolver, or extra control plane when Rally already has a clean runtime truth path.
- Put repeated framework lessons where proper Rally use inherits them. That usually means Rally stdlib, Rally runtime, shared skills, or the canonical docs, not one sample flow.
- Push hard on modular code. Favor small files, small functions, and clear module seams over big mixed-purpose files.
- Build reusable parts with one job each. Hide adapter details, file-format details, and one-off glue inside the owning module instead of leaking them across the repo.
- Treat a non-generated file near or above 1,000 lines as a design smell. Split it before it turns into a catch-all file, and do not add new 1k+ monstrosities.

## Build And Verify

- Prove the smallest proof path that matches the change:
  - prompt or standard-library change: recompile the affected flow build output with the paired Doctrine compiler, then inspect the generated readback
  - runtime change: prove it through the owning `rally` CLI or run-home path
  - fixture change: run the fixture-local proof command from that fixture repo root with `uv run pytest`, unless that fixture says otherwise
- Do not hand-edit `flows/*/build/**` to fake a compile result or cover up missing compiler behavior.
- If the needed proof path or tool support is missing, say that plainly and stop at the real blocker.

## Hard Rules

- Do not patch around Doctrine bugs, parser gaps, compiler gaps, or missing generic language support in Rally.
- Do not do instruction laundering. That means turning turn-local user coaching into repo rules, shared prompts, or skills.
- Add a new always-on rule only when it is stable repo truth or the user clearly asked to make it repo policy.
- Before you add a new instruction line, ask: is this repo truth, or is it feedback for this one turn?
- Do not repeat command paths or framework rules across root `AGENTS.md`, Rally stdlib, flow-local prompts, skills, and docs. Pick one owner, then delete the copies.
- Do not make Rally "smarter" by fattening the harness. If the system needs more judgment, improve prompt source, review law, a skill, setup, or deterministic tooling instead.
- Maximize Doctrine usage in prompt files. Double-check every `.prompt` edit before you finish. If Doctrine can express the shape cleanly, use Doctrine instead of a local workaround.
- If Rally needs Doctrine support to stay clean, stop, name the exact missing Doctrine feature, and tell the user.
- Describe Doctrine gaps in framework terms: language rules, compile-time metadata, emitted build structure, route rules, or similar reusable features.
- Do not bring back separate handoff artifacts, prose-routed handoffs, or a second turn-ending control path in Rally docs, stdlib, skills, or runtime design.
- Do not bake Rally flow names, role names, run-home layout, or adapter assumptions into Doctrine.
- Do not let fixture repos, sample flows, or current role names turn into Doctrine primitives. They are pressure tests and examples, not framework law.
- Do not move prompt instruction prose into runtime files. `flow.yaml`, `run.yaml`, logs, session sidecars, and setup scripts may run the system, but they do not author instructions.
- When a port exposes a durable cross-flow lesson or repeated bad behavior, add it to `docs/RALLY_PORTING_GUIDE.md` instead of burying it in one flow.

## Definition Of Done

- The change lives in the right layer: Doctrine source, Rally runtime, flow definition, shared library, skill, or MCP surface.
- Generated readback matches the edited source after the compile step.
- The smallest useful proof ran, or the exact missing proof dependency was reported.
- For `.prompt` changes, you re-checked that the result uses Doctrine features as far as they fit cleanly. If a missing Doctrine feature blocks the clean version, name that blocker plainly.
- New docs and rules capture lasting repo truth, not temporary scaffolding, deleted plans, or implementation shortcuts.
- If you changed communication or runtime design docs, keep the Rally master design, the matching phase docs, and the focused CLI/logging doc aligned in the same pass when they touch the same topic.
- Changed instructions stay lean. No copied command manuals, no repeated framework rules, and no extra narrative layer over primary facts.
- Framework-wide best practices land in Rally-owned shared layers so proper Rally use inherits them by default.
- If a change adds always-on prose, you checked that it earns its context cost and does not crowd out task context.

## Plain English

- Hard rule: write prompt source, skills, and `AGENTS.md` files at about a 7th-grade reading level.
- Before you finish any `.prompt`, `SKILL.md`, or `AGENTS.md` edit, read the new prose again and simplify it.
- Prefer short sentences, concrete nouns, and active voice.
- Prefer positive framing. Tell the agent what to do before you list what to avoid.
- Keep `do not` lines for hard guardrails, safety rules, and one-way mistakes.
- Keep scope straight when you write instructions.
- Keep literal code tokens exact, but rewrite the words around them so a new reader does not have to decode Rally jargon.
- If you must keep a literal token such as `handoff`, `next_owner`, or `current none`, explain it in plain English right away.
- Rewrite words like `surface`, `contract`, `semantics`, `currentness`, `durable`, `structural`, `orchestration`, and `invariant` unless they are literal code or schema terms.
- Good: `Read \`home:issue.md\`, then open the current file and keep going.`
- Bad: `Do not miss the latest issue note or current file.`
- Good: `Leave a note if a later reader needs context.`
- Bad: `Preserve durable context for downstream turns.`
- Good: `Check the test result.`
- Bad: `Inspect the proof surface.`

## Communication

- Lead with the plain answer.
- Say exactly what changed, what you checked, and what is still blocked.
- If the right move is "Doctrine first," say that directly instead of offering a workaround.
- When Rally is blocked on Doctrine, say whether the gap is in authored language, compiler behavior, or emitted build output, and describe it as a general Doctrine feature.

## Docs Map

- `PRINCIPLES.md`: framework design rules for harness scope, context budget, resolvers, and the latent versus deterministic split; read it before widening Rally
- `docs/`: use the current Rally master design doc as the main design source. Ignore stale plans and worklogs. Find it with `rg --files docs | rg 'RALLY_MASTER_DESIGN'`
- `docs/RALLY_CLI_AND_LOGGING.md`: focused command, issue-ledger, snapshot, and logging detail; use it when CLI shape, run logs, renderer rules, or recovery paths change
- `docs/RALLY_COMMUNICATION_MODEL.md`: communication model; keep it aligned with the master doc when notes, end-turn control, or harness env rules change
- `docs/RALLY_RUNTIME.md`: runtime detail; keep it aligned with the master doc when runtime scope, proof paths, or launch rules change
- `docs/RALLY_PORTING_GUIDE.md`: canonical porting rules and examples for bringing existing agent systems into Rally; add durable port lessons there
- `flows/*/flow.yaml`: runtime config, adapter settings, and allowlisted skills and MCPs (skill tier model in `docs/SKILL_SCOPING.md`)
- `flows/*/prompts/**`: prompt source
- `stdlib/rally/prompts/**`: Rally-owned shared prompt source; use `turn_results.prompt` as the shared final-result rule
- `flows/*/build/**`: generated readback only
- `flows/*/setup/*.sh`: flow-home setup
- `skills/*/SKILL.md`: skill rules
- `mcps/*/server.toml`: MCP definitions
