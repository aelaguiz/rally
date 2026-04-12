# AGENTS.md

## First Pass

- Start with `git status --short` and `rg --files flows stdlib skills mcps docs`.
- Treat `flows/`, `stdlib/`, `skills/`, `mcps/`, and `runs/` as Rally's permanent top-level shape.
- Prefer the smallest owning surface:
  - authored doctrine: `flows/*/prompts/**` and `stdlib/rally/prompts/**`
  - runtime contract: `flows/*/flow.yaml`
  - generated readback: `flows/*/build/**`
  - capability definitions: `skills/*/SKILL.md` and `mcps/*/server.toml`

## Source Of Truth

- Author agent and flow doctrine in `.prompt` files. Compiled `AGENTS.md` and other output under `flows/*/build/**` are generated readback, not hand-authored source.
- Rally owns the runtime, CLI, run structure, logs, sessions, adapter contract, and the standard library contents under `stdlib/rally/`.
- Doctrine owns generic language and compiler support. If a change would alter generic authored semantics, it belongs in Doctrine, not in Rally.
- Treat the prepared run home as the agent's whole world. Skills, MCPs, repos, artifacts, sessions, and adapter-local state belong there, not in machine-global Rally state or arbitrary filesystem escapes.
- Keep Rally-owned state inside this repo, especially under `runs/`. Do not create hidden Rally control planes under `~/.rally`, `~/.config`, or similar global locations.
- For Codex adapter work, preserve the explicit launch contract: Rally chooses `cwd`, points `CODEX_HOME` at the run home, disables ambient project-doc discovery, and injects compiled doctrine explicitly.
- Do not add side-door instruction sources, Markdown overlays, or ambient repo-doc injection outside the declared `.prompt` graph.

## Build And Verify

- Verify the smallest surface that proves the change:
  - doctrine or standard-library change: recompile the affected flow build output with the paired Doctrine compiler, then inspect the generated readback
  - runtime change: prove it through the owning `rally` CLI or run-home surface, not through an unrelated script or control plane
  - fixture change: run the fixture-local proof command from that fixture repo root
- Do not hand-edit `flows/*/build/**` to fake a compile result or to paper over missing compiler behavior.
- If the required proof surface or tool support is missing, say that plainly and stop at the real blocker.

## Loud Invariants

- Do not work around Doctrine bugs, parser gaps, compiler gaps, or missing generic authored-semantics support in Rally.
- If Rally needs Doctrine support to stay clean, stop, name the exact missing Doctrine capability, and tell the user. Co-evolve Doctrine instead of encoding a Rally-side hack.
- Do not let `paperclip_agents`, fixture repos, sample flows, or current role names turn into Rally framework primitives. They are pressure tests and examples, not framework law.
- Do not move authored instruction prose into runtime files. `flow.yaml`, `run.yaml`, logs, session sidecars, and setup scripts may control orchestration, but they do not author doctrine.
- Keep one active run per flow unless the design changes intentionally. Do not smuggle in concurrent-active-run behavior as a convenience shortcut.

## Definition Of Done

- The change lives in the correct owning layer: Doctrine source, Rally runtime, flow definition, standard library, skill, or MCP surface.
- Generated readback matches the authored source after the relevant compile step.
- The smallest relevant proof surface ran, or the exact missing proof dependency was reported.
- New docs or rules encode durable repo truth, not temporary scaffolding, deleted planning docs, or implementation shortcuts.

## Communication

- Lead with the concrete answer in plain English.
- Say exactly what changed, what you verified, and what remains blocked.
- If the correct move is "this belongs in Doctrine first," say that directly instead of presenting a workaround.

## Docs Map

- `docs/`: use the current Rally master design doc as the design source of truth and ignore stale plans or worklogs; find it with `rg --files docs | rg 'RALLY_MASTER_DESIGN'`
- `flows/*/flow.yaml`: runtime contract, adapter settings, and allowlisted skills and MCPs
- `flows/*/prompts/**`: authored flow doctrine
- `stdlib/rally/prompts/**`: Rally-owned Doctrine standard library
- `flows/*/build/**`: compiled readback only
- `flows/*/setup/*.sh`: flow-home preparation
- `skills/*/SKILL.md`: capability contracts
- `mcps/*/server.toml`: MCP definitions
