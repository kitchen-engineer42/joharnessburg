---
name: plan-md-authoring
description: How to write the initial PLAN.md at the start of a John project. Use this skill whenever the user has just run /john:init, when there is no PLAN.md yet, or when the user says "let's start a new project" / "design the plan" / "what should we build." PLAN.md is the durable contract that spans knowledge engineering (knowledge phases) and app building (app phases) in ONE session — get it right at the top or every phase pays for it.
metadata:
  triggers:
    - write PLAN.md
    - author the plan
    - design the plan
    - initialize plan
    - start of project
    - start a new project
    - no plan yet
    - what should we build
    - design the app-type definition
---

# plan-md-authoring

You are writing PLAN.md for the first time on a new John project. After this, [[plan-md-evolution]] takes over — this skill is just the bootstrap.

The plan is not a recipe. It's a **wide-tunnel agreement** between you and the user about what's being built, how the work decomposes into phases, and where the open decisions are. Too narrow and you'll regret it in two phases when the corpus surprises you. Too loose and you'll re-derive everything every iteration.

## When to start writing

After `/john:init` has scaffolded `<project>/.john/` and put the user's input materials in `<project>/.john/input/`. Before you've decided on a knowledge schema.

The plan starts from the user's request and what the corpus reveals. Prefer judgment over questionnaires: infer what is obvious, ask only for high-impact product choices where two or more plausible directions would materially change the app.

John's default questioning budget is strict:

- At most **one** product-question batch for the whole project.
- At most **four** questions in that batch; most projects should ask zero to two.
- Each question is ordinary-user language with a few options plus free text. Do not ask about schema fields, skill names, chunking, JSON, or implementation internals.
- User input may be natural language. The fixed JSON lives in `.john/brief/` and `.john/contracts/`, not in the user's reply.
- After the batch is used, do not ask more product-preference questions. Record assumptions or blockers instead.

## The skeleton

PLAN.md has these sections in this order. Some come from your conversation with the user; some you fill in as the project progresses.

```markdown
# PLAN.md — <project name>

## Project intent
<what the produced app does, who uses it, what it consumes, what success looks like>

## Intent and display contracts
- Intent question budget: one batch maximum, four questions maximum.
- Intent questions, if needed: .john/brief/intent_questions.json
- Normalized user intent, always required before schema pilot: .john/brief/user_intent.json
- Public app blueprint, always required before schema pilot: .john/contracts/app_blueprint.json
- UI-driven extraction plan, always required before schema pilot: .john/contracts/extraction_plan.json

## Knowledge inventory (from the knowledge phases)
<initial: pointer to .john/input/ and a one-line corpus profile
 over time: pointer to <project>/.claude/skills/ once the knowledge phases ship>

## App-type definition
- User intent: <derived from request + survey + optional one-shot product-question batch>
- App mechanism: <how the produced app works for end-users>
- Display contract: <public pages, navigation, labels, modules, forbidden visible terms>
- Extraction targets: <what each UI slot needs from the corpus>
- Knowledge format/schema: <internal representation derived from extraction targets; expect to iterate>
- Build pipeline: <the rest of this doc — phases that build the app>

## Phases
### Phase 1: <name>
- Intent: <one sentence>
- Subagent assignments: <if vertical fan-out, what's the unit?>
- Execution: <Workflow yes/no; if yes: worker agent + cross-check agent + model — see [[vertical-workflows]]>
- Skills to invoke: <[[skill-1]], [[skill-2]]>
- Required artifacts (disk-verifiable): <paths the engine can check>
- Done criteria: <observable conditions; not "feels finished">

### Phase 2: ...
...

## Subagent matrix
<for any phase with vertical fan-out, the list of work units and current state.
 may be empty at first, fills in as phases hit fan-out points>

## Open decisions
<things you want the user to weigh in on before you barrel forward>

## Log
<append-only, most recent first. dated entries:
 - phase advances ("Phase 2 done, X artifacts produced")
 - decisions you made and why
 - blockers you wrote to "Open decisions"
 - user instructions received mid-flight>
```

## What goes in each section — the taste calls

**Project intent.** Specific enough to disambiguate ("a study companion that helps ordinary readers understand this Chinese book"), wide enough not to overfit ("a Next.js SPA with React 19 and Tailwind 4" is too narrow at intent-time). The intent should still make sense if you change app mechanism later.

**Intent and display contracts.** This section records the app-first discipline. The agent first infers from the user's request, existing PLAN content, and corpus survey. If a product choice cannot be inferred and would materially change the app, emit `.john/brief/intent_questions.json` and ask the user once. Whether or not a question batch was needed, produce `.john/brief/user_intent.json`, `.john/contracts/app_blueprint.json`, and `.john/contracts/extraction_plan.json` before schema pilot.

**Knowledge inventory.** Initially just a pointer + one-line profile of the corpus: "10 PDFs, ~2000 pages total, financial regulations in Chinese." Don't speculate about what'll come out yet. After the knowledge phases ship, this becomes a pointer to the produced skills.

**App-type definition.** The default cascade is app-first: user intent -> app mechanism -> display contract -> extraction targets -> internal knowledge format/schema -> build pipeline. [[app-design-thinking]] owns the display contract; [[schema-design]] turns it into an internal schema after the corpus survey. Two cheap commitments worth writing in here from day one: the extraction phase opens with a **schema pilot** (diverse sample before mass extraction — [[schema-design]]), and entries carry a **`schema_version`** field so later schema changes stay detectable and migratable.

This section is the user's project taste applied, but do not push routine choices back to them. Wide tunnel — sketch loose, iterate as the corpus reveals itself. The cascade's order matters: public user experience first, then extraction and schema.

**Phases.** This is the build pipeline. The default starter is now parse/probe -> survey -> infer intent -> optional one-shot question batch -> app blueprint -> extraction plan -> schema pilot -> full extraction -> rewrite/package -> app build -> UI leak guardrails. The user or active template can override, but vanilla John should not return to schema-first planning.

**Subagent matrix.** Often empty at PLAN.md authoring time. Fills in when a phase hits fan-out. For a large uniform fan-out, note whether the phase runs as a dynamic workflow ([[vertical-workflows]]) or inline dispatch ([[subagent-dispatch]]) — the work units and event paths are the same either way.

**Open decisions.** Before the one-shot product-question batch, use this section only for high-impact product choices. After the batch is used, do not keep accumulating product questions; move uncertainties into assumptions, or mark a true blocker if the project cannot proceed without external state.

**Log.** Append-only. Most recent first. Real reverse-chronological dev log. After every phase advance, after every meaningful decision, write a line.

## How long should PLAN.md be at start

For most projects: 200-500 lines at initial write. By project end (after several phases have completed), it grows to 800-2000 lines because the Log accumulates and Subagent matrix fills.

If your initial PLAN.md is under 100 lines, you probably haven't asked enough questions. If it's over 1000, you're over-specifying — push back to the user.

## Anti-patterns

- **Turning bootstrap into a questionnaire.** The agent should choose the best default when the request and corpus make it obvious. Ask only when the choice is high-impact and genuinely ambiguous.
- **Asking twice about product taste.** One product-question batch is the maximum. Later uncertainty becomes assumptions or blockers.
- **Locking down phases that depend on extracted knowledge.** You don't know yet what the corpus contains. Write the early phases concretely; mark later phases as TBD or sketch-only.
- **Exposing internals as user-facing design.** Public labels must not show schema keys, skill names, chunk IDs, raw JSON, file paths, or meaningless English variable names in a non-English project.
- **Copying KC's 7 phases or a predecessor's 5 stages verbatim into PLAN.md.** They were designed for specific app types. John is general. Take the pattern (a small number of named phases with clear done-criteria), drop the specifics.
- **Omitting "Done criteria."** Without observable conditions, you can't tell when a phase is done. Disk-verifiable artifacts are the gold standard ([[workspace-discipline]]).

## The conversation with the user

PLAN.md is co-authored, but co-authoring is not abdication. The taste calls belong to the user when their preference materially changes the product; the agent owns routine defaults and inferred decisions.

A workable conversation flow (adapt freely):

1. **Capture known intent.** Echo back what you understood from `/john:init`, the user's framing, and any existing project memory.
2. **Check for an active template.** A template is active if the session launched with `claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>/` — its parent dir being `joharnessburg-applied/` is the signal. If so, `$CLAUDE_PLUGIN_ROOT/templates-active/plan_md_template.md` (if shipped by the template) is your skeleton; `/john:init` automatically uses it on workspace scaffold. Otherwise, you're sketching from scratch — confirm with the user.
3. **Survey before schema.** Parse/probe enough of the corpus to identify language, genre, structure, likely audience, and likely app form.
4. **Infer first, ask only if needed.** If a high-impact product choice remains genuinely ambiguous, write `.john/brief/intent_questions.json` with at most four ordinary-user questions, each with options and free text, then ask the single batch.
5. **Persist contracts.** Normalize the result into `.john/brief/user_intent.json`, then write `.john/contracts/app_blueprint.json` and `.john/contracts/extraction_plan.json`. These fixed JSON files are the source of truth for schema and extraction.
6. **Sketch phases.** Use the app-first pipeline as the default. Later app phases can remain TBD if they depend on pilot results.

After the first PLAN.md write, [[plan-md-evolution]] takes over — keep PLAN.md current as work proceeds.

## The knowledge → app boundary within one PLAN.md

PLAN.md spans both halves of John in one document. Phases 1-N typically handle knowledge engineering (producing artifacts in `<project>/.claude/skills/`); phases N+1 to M typically handle app building (producing the deliverable app). The boundary is natural — it's where the *Knowledge inventory* section transitions from "pointer to .john/input/" to "pointer to .claude/skills/". Keep the Knowledge inventory live: update it when the knowledge phases ship, so the app phases inherit the produced skills as their starting context.

## After this skill ends

[[ralph-loop]] takes over. The plan you just wrote is the contract that loop reads first every iteration.

## Cross-references

- [[plan-md-evolution]] — keeping PLAN.md current as work progresses
- [[phase-design]] — what makes a good phase
- [[schema-design]] — the methodology for the knowledge-format question
- [[ralph-loop]] — what runs against the plan
- [[subagent-dispatch]] — populating the Subagent matrix
- [[vertical-workflows]] — running a fan-out phase as one workflow run
- [[workspace-discipline]] — disk-verifiable done criteria
