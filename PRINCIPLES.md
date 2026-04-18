# Rally Principles

This file distills Garry Tan's "Thin Harness, Fat Skills" into Rally's
framework rules.
Rally is a framework, so these rules govern the harness itself.
They are not flow-specific product rules.

## Core Idea

Rally should win by architecture, not by stuffing more prose around the model.
The harness should give the model the right context at the right time without
drowning it in noise.

## Principles

### 1. Keep The Harness Thin

- Rally owns the turn loop, files, context loading, capability projection,
  session continuity, and safety.
- Rally does not own most domain judgment or repeated work procedure.

### 2. Treat Context Like A Scarce Resource

- Every always-on line costs attention.
- Repetition is not harmless. It wastes tokens, changes salience, and creates
  conflicts.
- Give each durable rule one owner.

### 3. Put Reusable Judgment In Skills And Prompt Source

- Skills teach process, not the task itself.
- If the same kind of work will happen again, codify it instead of reteaching
  it in prose.
- The best upgrades are shared and inherited.

### 4. Use Resolvers, Not Giant Preload Blobs

- Load the right doc, skill, or fact when the task calls for it.
- Prefer pointers and routing over huge always-on handbooks.
- Keep deep knowledge available on demand, not in the prompt by default.

### 5. Push Exact Work Down Into Deterministic Tooling

- Exact parsing, status checks, tests, queries, compilation, and file
  transforms should be deterministic.
- Tools should be narrow, fast, and purpose-built.
- Do not hide deterministic work inside long model-written prose.

### 6. Keep Judgment In Latent Space

- Synthesis, tradeoffs, review, contradiction handling, and diarization belong
  with the model.
- Use the model to read many artifacts and produce a short structured judgment
  when that judgment cannot be reduced to a query.

### 7. Prefer Direct Facts Over Summaries

- If Rally can show the model the current artifact, git status, test result, or
  ledger entry, do that.
- Do not add another narrative layer that retells the same facts.

### 8. Make Good Use Inherit The Right Defaults

- If a best practice should come for free, land it in Rally-owned shared layers
  such as stdlib, runtime, shared skills, or canonical docs.
- Do not rely on one sample flow to teach framework law.

### 9. Make The System Learn

- One-off work should stay one-off only once.
- If the same need comes back, turn it into a skill, shared prompt rule, setup
  helper, or deterministic tool.
- The system should improve by codifying lessons, not by growing more harness
  prose.

## Decision Tests

Before you add anything, ask:

- Is this runtime wiring, or is it really a skill?
- Is this exact and repeatable, or does it require judgment?
- Does this reduce context, or add more always-on text?
- Should every Rally user inherit this, or only one flow?
- If a better model shipped tomorrow, would this still belong in the harness?

## Failure Signs

Rally is drifting when:

- the same rule appears in `AGENTS.md`, stdlib, skills, and flow prompts
- runtime facts get retold as prose summaries
- one sample flow carries framework law
- deterministic work sits in latent prompts
- the harness grows second state machines or shadow control planes
- skill count grows without a resolver story
- tools are slow, generic, or too broad for the job

## Direction

Push intelligence up into skills.
Push execution down into deterministic tools.
Keep the harness thin.
Keep context sharp.
Make the best path the default path.
