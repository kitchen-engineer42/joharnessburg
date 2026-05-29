---
name: app-design-thinking
description: Design the runtime structure and production pipeline for the produced app — the 2app analog of [[schema-design]]. Use this skill whenever the 2skills half is complete (or nearly so), when the user mentions building the app / runtime / UX / production / deploy, when the four-structures section of PLAN.md needs its runtime + pipeline rows settled, or when [[ralph-loop]] advances out of packaging into 2app. The shape of the produced app gets decided here; downstream phases follow.
metadata:
  triggers:
    - design the app
    - app design thinking
    - runtime structure
    - production pipeline
    - how should the app work
    - design the 2app phases
    - what kind of app
    - app shape
---

# app-design-thinking

The 2skills half produced a knowledge inventory at `<project>/.claude/skills/`. Now the question is: **what app do we build with it, and how do we build it?** That's the third and fourth links of the four-structures cascade — runtime structure (how the produced app works for end-users) and production pipeline (phases that build it). This skill teaches how to settle those two structures from the knowledge already extracted.

[[schema-design]] is this skill's twin in the 2skills half — same methodology, different links in the cascade. Both teach taste, neither prescribes.

## What this skill is NOT

- **It's not picking from a closed menu of app archetypes.** The 5 subsites are examples for pattern-matching, not a catalog. Every John project should invent its own runtime + pipeline shape; templates may ship common shapes as starting points, but users always override. If the project's runtime doesn't resemble any of the 5, that's normal — invent it.
- It's not one-shot. Runtime and pipeline iterate as the produced skills reveal what the app naturally wants to be.
- It's not an alternative to the user's intent. They own the project's *what*; this skill teaches you how to translate it into *how*.

## The third structure — runtime

The runtime is how the produced app works for end-users. Pin it down by asking:

- **Who's the end-user?** (a teacher? a compliance officer? a player? a researcher?) Their context determines the runtime shape.
- **What's their input?** (a document upload? a chat? a click? nothing — they just browse?) The input shape constrains the runtime architecture.
- **What's their output?** (a verdict? a slide deck? an interactive widget? a downloadable file?) The output shape determines what the runtime must produce.
- **Is there an LLM at runtime, or only at build time?** (a static slide deck has no runtime LLM; a chat-based study companion calls a workerLLM on every user turn.) See `references/runtime-vs-buildtime-llm.md`.
- **Is the runtime stateful?** (does it remember the user across sessions? track progress? store uploads?)

Sketch the runtime in PLAN.md's four-structures section. Like schema-design's schema sketch, mark it "may evolve."

## The fourth structure — production pipeline

The production pipeline is the phases that turn the packaged skills (and any other input) into the runtime. Derive it backward from the runtime: what does the runtime need, and what phases produce each piece?

Common pipeline patterns (see `references/phase-design-for-2app.md`):

- **Scaffold** — set up the app's basic structure (framework choice, project layout, dependencies).
- **Wire core mechanics** — implement the app's central loop (rule application, game logic, slide rendering).
- **Seed content from skills** — pull knowledge entries out of `<project>/.claude/skills/` into the app's data layer.
- **Wire runtime LLM** (if applicable) — provider abstraction, system prompts, error handling.
- **Polish** — UX details, error states, edge cases.
- **Deploy** — Docker, hosting, smoke test.

Not every project needs every phase. Use the rubric in [[phase-design]] to decide; this list is a starting point, not a checklist.

## The reverse direction — runtime informs schema

Sometimes app-design-thinking reveals that the produced knowledge isn't quite shaped right for the runtime you want. (E.g., "this rule-shaped schema doesn't carry the severity field the runtime needs to color-code violations.") When that happens, [[plan-md-evolution]] takes over: append to PLAN.md's Log, surface the gap as an Open Decision, decide whether to extend the schema and re-emit affected entries, OR adapt the runtime to what the schema gives. Cascade iteration is normal; the cascade is not a one-way pipe.

**The cost tradeoff.** If the schema is already locked (you've extracted hundreds of entries against it), extending and re-emitting is expensive. Before deciding, ask the user three questions:

1. How many entries already exist? (more entries → re-emission cost grows)
2. Is the missing field mandatory at runtime, or optional? (optional → can adapt runtime cheaper)
3. Can the runtime compute the field from existing fields? (e.g., derive severity from a `category` and a fixed mapping)

If re-emission is expensive AND the runtime can adapt, adapting often wins. If re-emission is cheap OR the field is mandatory, extending the schema is right. Capture the decision in PLAN.md so future-you knows why the cascade looks the way it does.

## Working with the user

App-design-thinking is **co-authored**. Sketch options, the user picks. The runtime shape especially is a taste call — does the user want a chat app or a static page? A web app or a CLI? Don't decide unilaterally.

Practical conversation flow:

1. Confirm the project intent from PLAN.md's top.
2. Ask the four runtime questions (who, input, output, LLM-at-runtime).
3. Show 2-3 runtime sketches the user can react to (e.g., "could be a chat app or a wiki-style browser or a slide presenter").
4. Once runtime is roughly settled, derive pipeline phases.
5. Capture both in PLAN.md; mark each "may evolve."

## Reference archetypes

`references/app-archetypes.md` summarizes the 5 subsites we explored — portfolio builder, mystery detective game, lesson2slides, mathlab, voteforyourapp. Each is a different combination of runtime structure + production pipeline. They're reference shapes for pattern-matching new projects against, NOT a closed menu. Templates and projects invent their own as needed.

## When to iterate

The runtime and pipeline decisions will evolve as the project reveals itself — expect to revisit them. Signs they need updating:

- A pipeline phase produces something the runtime doesn't actually need (drop the phase).
- The runtime wants a feature whose data isn't in the schema (consult [[schema-design]] for a schema extension, OR redefine the runtime to work with what you have).
- A phase you thought would be straightforward turns out to need sub-phases (use [[plan-md-evolution]]'s subdivide pattern).

[[plan-md-evolution]] is the maintenance skill; this one is the bootstrap.

## Cross-references

- [[schema-design]] — settles format + schema (the first two cascade links); this skill picks up where that ends
- [[plan-md-authoring]] — where the four-structures section first appears
- [[plan-md-evolution]] — how to revise runtime/pipeline mid-flight
- [[phase-design]] — decision rubric for phases (applies to 2app phases too)
- [[code-quality-guardrails]] — quality discipline for produced app code
- [[ralph-loop]] — advances through the 2app phases this skill helps design
- See `references/` for: 5-subsite archetype summaries, runtime-vs-buildtime LLM patterns, common 2app phase shapes
