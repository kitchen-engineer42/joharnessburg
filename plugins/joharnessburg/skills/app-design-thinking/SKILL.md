---
name: app-design-thinking
description: Design the ordinary-user app mechanism, normalized intent, display contract, and extraction targets before full knowledge extraction. Use this skill after parse/survey, whenever the app-type definition section needs user intent / app mechanism / display contract rows settled, when the user mentions building the app / runtime / UX / production / deploy, or when the project needs to prevent internal schema/skill/JSON terms from leaking into the final UI.
metadata:
  triggers:
    - design the app
    - app design thinking
    - app mechanism
    - build pipeline
    - how should the app work
    - design the app phases
    - what kind of app
    - app shape
---

# app-design-thinking

The app shape is not an afterthought. John's default is now app-first: after parse/probe and corpus survey, decide what ordinary end-users should see, then derive extraction targets and internal schema from that display contract.

[[schema-design]] is this skill's downstream twin: it turns the app blueprint and extraction plan into an internal knowledge schema. This skill owns the product-facing contract.

## What this skill is NOT

- **It's not picking from a closed menu of app archetypes.** The 5 reference apps are examples for pattern-matching, not a catalog. Every John project should invent its own runtime + pipeline shape; templates may ship common shapes as starting points, but users always override. If the project's runtime doesn't resemble any of the 5, that's normal — invent it.
- It's not a questionnaire. Infer obvious decisions from the user's request and corpus survey; ask only for high-impact product choices that cannot be inferred.
- It's not a place to expose internals. Public UI labels must not show schema keys, skill names, chunk IDs, raw JSON, file paths, or meaningless English variable names.
- It's not final forever. Runtime and pipeline iterate as the schema pilot and extraction reveal what the app can support.

## Inputs and outputs

Read:

- PLAN.md Project intent and any existing app-type notes.
- `<project>/.john/parsed/` or survey notes from [[parsing]].
- Any user-provided constraints in CLAUDE.md / AGENTS.md.

Write:

- `.john/brief/intent_questions.json` only if a single product-question batch is truly needed.
- `.john/brief/user_intent.json` always before schema pilot.
- `.john/contracts/app_blueprint.json` always before schema pilot.
- `.john/contracts/extraction_plan.json` always before schema pilot.

Use `${CLAUDE_PLUGIN_ROOT}/scripts/app_first_contracts.py` when available to validate or generate the standard JSON shells. The LLM supplies judgment; the script keeps wire shape stable.

## One-shot product questions

Most projects should not ask much. A Chinese book plus "make a website for ordinary readers" already implies Chinese UI, general-reader tone, guided reading, and hiding internals. Ask only when all are true:

1. Two or more product directions are plausible.
2. The choice materially changes pages, extraction targets, or runtime mechanics.
3. The user's request, existing PLAN, and corpus survey do not reveal a clear winner.
4. Guessing wrong would cause meaningful rework.

When asking, emit a single batch of at most four questions. Each question uses ordinary language, a few options, and free text. Do not require the user to answer JSON. After this batch, never ask another product-preference question; record assumptions or blockers.

## The app mechanism

The runtime is how the produced app works for end-users. Pin it down primarily by inference:

- **Who's the end-user?** (a teacher? a compliance officer? a player? a researcher?) Their context determines the runtime shape.
- **What's their input?** (a document upload? a chat? a click? nothing — they just browse?) The input shape constrains the runtime architecture.
- **What's their output?** (a verdict? a slide deck? an interactive widget? a downloadable file?) The output shape determines what the runtime must produce.
- **Is there an LLM at runtime, or only at build time?** (a static slide deck has no runtime LLM; a chat-based study companion calls a workerLLM on every user turn.) See `references/runtime-vs-buildtime-llm.md`.
- **Is the runtime stateful?** (does it remember the user across sessions? track progress? store uploads?)

Sketch the runtime in PLAN.md's app-type definition section and `.john/contracts/app_blueprint.json`. Like schema-design's schema sketch, mark it "may evolve."

## Display contract

The display contract is the public surface of the app:

- Pages and navigation the user sees.
- User-facing labels and module names.
- The language and tone of generated text.
- The content slots each page needs.
- Forbidden visible terms.

The contract must be ordinary-user friendly. For a Chinese source, default to Chinese labels. Never use raw internal names such as `chapter_id`, `schema_version`, `skill-name`, `chunk_042`, `.john/input/foo.pdf`, or JSON blobs as visible content.

## Extraction plan

After the app blueprint, write `.john/contracts/extraction_plan.json`. Each target maps one UI slot to the corpus content needed to fill it: summary, key points, plain-language explanation, relationships, quotes, citations, examples, or source references. [[schema-design]] reads this file to design the internal schema; [[knowledge-extraction]] reads it to brief extraction subagents.

## The build pipeline

The build pipeline is the phases that turn the corpus into a runtime. Derive it backward from the public app: what pages and modules must exist, what extracted content fills them, and what code/data phases produce each piece?

Common pipeline patterns (see `references/app-phase-design.md`):

- **Scaffold** — set up the app's basic structure (framework choice, project layout, dependencies).
- **Wire core mechanics** — implement the app's central loop (rule application, game logic, slide rendering).
- **Seed content from contracts and skills** — pull UI-shaped knowledge entries into the app's data layer without exposing internal skill names.
- **Wire runtime LLM** (if applicable) — provider abstraction, system prompts, error handling.
- **Polish** — UX details, error states, edge cases.
- **Deploy** — Docker, hosting, smoke test.

Not every project needs every phase. Use the rubric in [[phase-design]] to decide; this list is a starting point, not a checklist.

## Deployment posture — standalone by default

Vanilla John designs produced apps to **run standalone**: launch locally or on any host the user owns, configuration through `.env`, no assumptions about an external auth/billing/telemetry platform being present. If the project is destined for a hosted multi-tenant platform, a template supplies those integration patterns — don't invent platform coupling in a vanilla project.

## Runtime informs schema

Sometimes app-design-thinking reveals that the first internal schema is not shaped right for the runtime you want. (E.g., "the concept card needs a plain-language explanation and source quote, but the draft entry only stores a technical definition.") When that happens, [[plan-md-evolution]] takes over: append to PLAN.md's Log, decide whether to extend the schema and re-emit affected entries, OR adapt the runtime to what the schema gives. Cascade iteration is normal; the cascade is not a one-way pipe.

**The cost tradeoff.** If the schema is already locked (you've extracted hundreds of entries against it), extending and re-emitting is expensive. Before deciding, ask the user three questions:

1. How many entries already exist? (more entries → re-emission cost grows)
2. Is the missing field mandatory at runtime, or optional? (optional → can adapt runtime cheaper)
3. Can the runtime compute the field from existing fields? (e.g., derive severity from a `category` and a fixed mapping)

If re-emission is expensive AND the runtime can adapt, adapting often wins. If re-emission is cheap OR the field is mandatory for a public UI slot, extending the schema is right. Capture the decision in PLAN.md so future-you knows why the cascade looks the way it does.

## Working with the user

App-design-thinking is **co-authored**, but the agent should not outsource obvious decisions. Sketch options only for high-impact ambiguity. If the best default is clear, take it and record the assumption.

Practical conversation flow:

1. Confirm known project intent from PLAN.md and user request.
2. Read the survey results and infer language, likely audience, site form, content priorities, and hard constraints.
3. If high-impact ambiguity remains, write `.john/brief/intent_questions.json` and ask one batch of at most four ordinary-user questions with options plus free text.
4. Normalize intent to `.john/brief/user_intent.json`.
5. Write `.john/contracts/app_blueprint.json` and `.john/contracts/extraction_plan.json`.
6. Update PLAN.md's app-type definition and phases; mark contracts "may evolve after schema pilot."

## Reference archetypes

`references/app-archetypes.md` summarizes the 5 reference apps we studied — portfolio builder, mystery detective game, lesson2slides, mathlab, voteforyourapp. Each is a different combination of app mechanism + build pipeline. They're reference shapes for pattern-matching new projects against, NOT a closed menu. Templates and projects invent their own as needed.

## When to iterate

The runtime and pipeline decisions will evolve as the project reveals itself — expect to revisit them. Signs they need updating:

- A pipeline phase produces something the runtime doesn't actually need (drop the phase).
- The runtime wants a feature whose data isn't in the schema (consult [[schema-design]] for a schema extension, OR redefine the runtime to work with what you have).
- UI leak guardrails flag internal labels; revise the display contract and public rendering before shipping.
- A phase you thought would be straightforward turns out to need sub-phases (use [[plan-md-evolution]]'s subdivide pattern).

[[plan-md-evolution]] is the maintenance skill; this one is the bootstrap.

## Cross-references

- [[schema-design]] — derives internal format + schema from the display contract and extraction plan
- [[plan-md-authoring]] — where the app-type definition section first appears
- [[plan-md-evolution]] — how to revise runtime/pipeline mid-flight
- [[phase-design]] — decision rubric for phases (applies to app phases too)
- [[code-quality-guardrails]] — quality discipline for produced app code
- [[ralph-loop]] — advances through the app phases this skill helps design
- See `references/` for: 5 reference-app archetype summaries, runtime-vs-buildtime LLM patterns, common app-phase shapes
