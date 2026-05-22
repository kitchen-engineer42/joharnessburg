---
name: plan-md-authoring
description: How to write the initial PLAN.md at the start of a John project. The plan is the durable contract that spans 2skills knowledge engineering and 2app app building in one session; it has to be honest about what's known and what's still a judgment call.
metadata:
  triggers:
    - write PLAN.md
    - author the plan
    - design the plan
    - initialize plan
    - start of project
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

**Four structures.** This is where the user's project taste matters most. The format-of-knowledge decision shapes everything downstream — see [[schema-design]] for the methodology. Write a STARTER sketch and explicitly mark it "may evolve." Wide tunnel.

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

## What if the active template provides a `plan_md_template.md`

Use it as the skeleton. Templates have already done the four-structures thinking for their domain (doc-verification, slides-from-textbook, etc.). Fill in the project-specific blanks; don't rebuild from scratch.

## After this skill ends

[[ralph-loop]] takes over. The plan you just wrote is the contract that loop reads first every iteration.

## Cross-references

- [[plan-md-evolution]] — keeping PLAN.md current as work progresses
- [[phase-design]] — what makes a good phase
- [[schema-design]] — the methodology for the knowledge-format question
- [[ralph-loop]] — what runs against the plan
- [[subagent-dispatch]] — populating the Subagent matrix
- [[workspace-discipline]] — disk-verifiable done criteria
