---
name: plan-md-authoring
description: How to write the initial PLAN.md at the start of a John project. Use this skill whenever the user has just run /joharnessburg-init, when there is no PLAN.md yet, or when the user says "let's start a new project" / "design the plan" / "what should we build." PLAN.md is the durable contract that spans 2skills knowledge engineering and 2app app building in ONE session — get it right at the top or every phase pays for it.
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
    - design the four structures
---

# plan-md-authoring

You are writing PLAN.md for the first time on a new John project. After this, [[plan-md-evolution]] takes over — this skill is just the bootstrap.

The plan is not a recipe. It's a **wide-tunnel agreement** between you and the user about what's being built, how the work decomposes into phases, and where the open decisions are. Too narrow and you'll regret it in two phases when the corpus surprises you. Too loose and you'll re-derive everything every iteration.

## When to start writing

After `/joharnessburg-init` has scaffolded `<project>/.john/` and put the user's input materials in `<project>/.john/input/`. Before you've parsed anything. Before you've decided on a knowledge schema.

The plan should be **written through a conversation with the user**, not generated unilaterally. If you find yourself filling in sections without asking, stop and ask. You only get one chance to shape a project at the top — don't waste it on assumptions.

## The skeleton

PLAN.md has these sections in this order. Some come from your conversation with the user; some you fill in as the project progresses.

```markdown
# PLAN.md — <project name>

## Project intent
<what the produced app does, who uses it, what it consumes, what success looks like>

## Knowledge inventory (from 2skills)
<initial: pointer to .john/input/ and a one-line corpus profile
 over time: pointer to <project>/.claude/skills/ once the 2skills half ships>

## Four structures (per spec §4)
- Format of knowledge: <facts? rules? stories? wiki? mixed? — initial guess, may evolve>
- Schema of knowledge: <starter sketch; expect to iterate>
- Runtime structure: <how the produced app works for end-users>
- Production pipeline: <the rest of this doc — phases that build the app>

## Phases
### Phase 1: <name>
- Intent: <one sentence>
- Subagent assignments: <if vertical fan-out, what's the unit?>
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

**Project intent.** Specific enough to disambiguate ("a study companion that quizzes the user on chapter content"), wide enough not to overfit ("a study companion" alone is fine; "a Next.js SPA with React 19 and Tailwind 4" is too narrow at intent-time — that's a runtime decision). The intent should still make sense if you change runtime structure later.

**Knowledge inventory.** Initially just a pointer + one-line profile of the corpus: "10 PDFs, ~2000 pages total, financial regulations in Chinese." Don't speculate about what'll come out yet. After 2skills half ships, this becomes a pointer to the produced skills.

**Four structures.** Per spec §4, format / schema / runtime / production-pipeline are a **cascade** — each constrains the next. [[schema-design]] teaches the cascade methodology in depth (and the corpus-survey step that grounds it); your job in this section is to *apply* the cascade, not re-explain it. Sketch each structure for *this* project with the user, and explicitly mark each "may evolve."

This section is the user's project taste applied. Wide tunnel — sketch loose, iterate as the corpus reveals itself. The cascade's order matters: settle format first, derive schema, derive runtime, derive pipeline. Reversing the order over-fits.

**Phases.** This is the production pipeline. For 2skills, John suggests a starter (parse → survey → schema-design → chunk → extract → rewrite → package, see [[phase-design]]) but the user or active template can override. For 2app, phases come from your conversation about the runtime structure. Don't try to nail every phase at start — leave the last few as "TBD: decide after phase N" if you genuinely don't know yet.

**Subagent matrix.** Often empty at PLAN.md authoring time. Fills in when a phase hits fan-out. See [[subagent-dispatch]].

**Open decisions.** Be brave about putting stuff here. "Open decisions" is the user's chance to weigh in; if you suppress your uncertainty, you'll guess wrong and waste a phase.

**Log.** Append-only. Most recent first. Real reverse-chronological dev log. After every phase advance, after every meaningful decision, write a line.

## How long should PLAN.md be at start

For most projects: 200-500 lines at initial write. By project end (after several phases have completed), it grows to 800-2000 lines because the Log accumulates and Subagent matrix fills.

If your initial PLAN.md is under 100 lines, you probably haven't asked enough questions. If it's over 1000, you're over-specifying — push back to the user.

## Anti-patterns

- **Filling in everything without asking.** PLAN.md is a co-authored doc. The first draft can be your sketch, but the user must approve before phases start running.
- **Locking down phases that depend on extracted knowledge.** You don't know yet what the corpus contains. Write the early phases concretely; mark later phases as TBD or sketch-only.
- **Specifying runtime details before the four-structures conversation has settled.** Choosing React vs vanilla before deciding format-of-knowledge is putting the cart before the horse.
- **Copying KC's 7 phases or pdf2skills's 5 stages verbatim into PLAN.md.** They were designed for specific app types. John is general. Take the pattern (a small number of named phases with clear done-criteria), drop the specifics.
- **Omitting "Done criteria."** Without observable conditions, you can't tell when a phase is done. Disk-verifiable artifacts are the gold standard ([[workspace-discipline]]).

## The conversation with the user

PLAN.md is co-authored. Do NOT fill in everything unilaterally. The taste calls — what the project actually is, what shape the runtime takes, what schema makes sense — belong to the user. You're sketching options, not deciding for them.

A workable conversation flow (adapt freely):

1. **Confirm project intent.** Echo back what you understood from `/joharnessburg-init` and the user's framing. If anything's ambiguous, ask before sketching.
2. **Ask about templates.** "Is there an active template (`/joharnessburg-template <name>`), or are we sketching from scratch?" If a template is active, read its `plan_md_template.md` — that's your skeleton. Fill in the project-specific blanks rather than rebuilding.
3. **Drive the four-structures conversation.** For 2app especially: ask about the runtime shape (what's the produced app, who uses it, how do they interact?) — that drives schema and format decisions backward, and pipeline decisions forward.
4. **Sketch phases.** For 2skills the suggested pipeline ([[phase-design]] documents it) is a decent default; for 2app, phases emerge from the runtime decision.
5. **Show the draft, ask for taste corrections.** Don't commit to disk until the user has read and approved the four-structures section and the first 2-3 phases.

After the first PLAN.md write, [[plan-md-evolution]] takes over — keep PLAN.md current as work proceeds.

## The 2skills → 2app boundary within one PLAN.md

PLAN.md spans both halves of John in one document. Phases 1-N typically handle knowledge engineering (producing artifacts in `<project>/.claude/skills/`); phases N+1 to M typically handle app building (producing the deliverable app). The boundary is natural — it's where the *Knowledge inventory* section transitions from "pointer to .john/input/" to "pointer to .claude/skills/". Keep the Knowledge inventory live: update it when the 2skills half ships, so 2app phases inherit the produced skills as their starting context.

## After this skill ends

[[ralph-loop]] takes over. The plan you just wrote is the contract that loop reads first every iteration.

## Cross-references

- [[plan-md-evolution]] — keeping PLAN.md current as work progresses
- [[phase-design]] — what makes a good phase
- [[schema-design]] — the methodology for the knowledge-format question
- [[ralph-loop]] — what runs against the plan
- [[subagent-dispatch]] — populating the Subagent matrix
- [[workspace-discipline]] — disk-verifiable done criteria
