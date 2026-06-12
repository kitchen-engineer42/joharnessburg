---
name: skill-evolution
description: Evolve the skills that do the work — capture lessons at phase boundaries into .john/lessons/, draft project-local skill overrides when guidance fights reality, and train workerLLM skills with a scored, gated edit loop when the domain has a scorer. Use this skill at every phase boundary ("what did this phase teach us?"), whenever worker output quality disappoints, when the user says "improve/optimize/train this skill or prompt", when a template ships a scorer or eval set, or when you notice a skill's guidance repeatedly mismatching the corpus. Evolution without this skill's discipline (bounded edits, held-out gates, the trainable-surface test) makes skills worse, not better — documented failure modes, not caution.
metadata:
  triggers:
    - improve the skill
    - optimize the prompt
    - train the worker skill
    - skill evolution
    - lessons learned
    - what did we learn
    - record a lesson
    - the skill is wrong
    - evolve the template
    - eval set
    - scorer
---

# skill-evolution

A skill document is not finished at authoring time — it should *earn* its content from run evidence. John structures that earning as **evolution rings**: the closer a text is to the work, the faster and more automated its evolution may be; the more meta it is, the slower and more human-gated.

- **Ring 0 — this project** (you, this skill): lessons, project-local override drafts, and the worker-skill training loop. Blast radius: this project only.
- **Ring 1 — the template**: the template's owner evolves it from accumulated run reports across projects. You *feed* Ring 1 (lessons, reports); you never edit the template itself.
- **Ring 2 — John core**: the maintainers evolve the teaching skills from cross-domain evidence. You feed it the same way. The top gate is human, permanently.

Your influence travels **upward as evidence, never as edits**. This skill teaches Ring 0: what to capture, what you may change, how to change it safely, and how to train the one class of skill where a real optimization loop applies.

## The boundary: trainable vs teaching

Before touching any skill text, classify it:

> **Could a different domain's template author have legitimately written this passage differently?** Then it's *trainable* — domain-specific "what to do", fair game for Ring-0 drafts and the training loop. **Is it true in every domain?** Then it's *teaching* — core methodology, hands off; if it's wrong, that's a `core`-scope lesson, not an edit.

In practice the trainable surface is what the template changed relative to vanilla John (its overrides, additive skills, plan skeleton, agents, worker prompts — enumerated in the applied plugin's `.applied-metadata.json`) plus anything project-local you created. When in doubt: **log a lesson, don't edit.**

A second classification, for deciding where an improvement *lands* (it shapes your lesson's `scope_guess`, and Ring 1 uses it when folding lessons in):

- **Core assets of a template** — its SKILL.md bodies, reusable scripts, the plan skeleton: things every project of this type needs. A lesson that generalizes across corpora of the domain points here.
- **Perimeter assets** — `references/` depth, worked examples, edge-case notes: useful, loaded on demand. A lesson that's real but conditional points here.
- **Ad-hoc** — judgment calls each project should make fresh. Not every lesson deserves to be institutionalized; over-folding kills the wide tunnel. It's legitimate for a lesson's destiny to be "stay project-local."

## The lessons ledger

`<project>/.john/lessons/` — one small JSON file per lesson, append-only, never edited or deleted. Format and examples: `references/lessons-ledger.md`. The non-negotiables:

1. **Conditional form.** A lesson states *when it applies*, not just what to do: `condition` + `lesson`. "Always chunk smaller" is over-generalization from one corpus; "when tables span chunk boundaries, chunk by row group" travels.
2. **Evidence pointer.** Every lesson cites what it was learned from (event files, checkpoint, gate verdict, a PLAN.md Log anchor). Un-evidenced lessons get rejected at promotion — write the pointer now, while you know it.
3. **Scope guess.** `project` / `template` / `core` — your honest estimate of where this lesson belongs. This is the promotion hint Rings 1–2 aggregate on.

**When to distill: at phase boundaries** — the same seam where [[plan-md-evolution]] runs and the user signs off. Ask: what fought reality this phase? What would I tell the next session building this kind of app? Two or three honest lessons beat ten plausible ones — a ledger full of unvalidated truisms is evolution theater, and reviewers learn to ignore it.

Raw corpus text is allowed *inside* the ledger (it's project-local). It must be scrubbed and generalized before anything leaves the project — see the care list. The export vehicle is the **run report** (`/john:report`): scorecard + manifest + outcome + the few lessons worth promoting, assembled per `references/run-report-format.md` and shared manually by the user (typically to the template's owner, as evolution evidence).

## Project-local skill overrides

When a skill's guidance actively fights this project (not just "could be better" — *fights*: you keep working around it), you may evolve it **for this project**:

1. **Draft** the override (the project's `.claude/skills/<name>/` shadows the plugin copy) as a *bounded delta* from the original — change the passages that fight, keep the rest byte-identical. Note the diff and the evidence in the draft's header comment.
2. **Apply at the next phase boundary, with the user's sign-off.** The draft rides the same seam as plan evolution — present it alongside the phase summary.
3. **Endurance-mode exception**: if the session is in endurance mode, the user is away, and the blockage is real (you cannot proceed sensibly without the change), you may apply the override autonomously — *when the reason is strong enough to write down*. Log it (ledger + PLAN.md Log) at the moment you do it.
4. **Always report** — before or after, the user hears about every override: what changed, why, the evidence. An unreported self-modification is a bug in your behavior, whatever its quality.

Never edit the merged plugin's files in `~/.claude/plugins/joharnessburg-applied/` — that copy is shared launch state, not project state.

## Training worker skills (the one real loop)

When the produced app runs a workerLLM over many items with a prompt/skill, **and the domain has a scorer** (held-out labeled slice, programmatic verifier, conformance checks), that worker skill can be *trained* during the build — a scored, bounded, gated edit loop, run as a fan-out phase on John's own machinery. The full procedure: `references/s3-loop.md`. The two-sentence version:

> Roll the frozen worker out on a scored train batch (events as the record); analyze failures and successes separately; propose a few bounded edits; accept a candidate only if it *strictly* beats the current skill on a held-out split; log rejected edits so they aren't re-proposed. Stop when accepts dry up — typical wins come from a handful of accepted edits, not a rewrite.

Whether a scorer exists — and where feedback should come from at all — is itself a design decision this skill expects you to make deliberately: `references/feedback-design.md` teaches the decision space (build-session vs app-runtime collection; corpus labels vs verifiers vs judges vs human experts). Templates that support evolution declare their feedback design and ship their scorer; your job is then instantiation, not invention.

## The care list (each item is a documented failure mode, not a courtesy)

- **Bounded deltas only — never rewrite a whole skill.** Monolithic LLM rewrites of accumulated text collapse it (drastic, measured degradation in published systems). Small edits, deterministic merges.
- **Strict gates; ties reject.** A plausible textual diagnosis can still make the actual behavior worse — roughly a quarter of generated "improvements" in published studies are negative. No gate, no edit.
- **Never optimize against a lone LLM judge.** Judges are gameable by the optimization pressure itself. Prefer judges that *verify* (grounding, citations, schema conformance) over judges that re-do the task; pair any judge with periodic ground-truth calibration.
- **You may not edit what counts you.** The process scorecard (`${CLAUDE_PLUGIN_ROOT}/scripts/process_scorecard.py`) and its rubric, the reducer's gates, the event contract — the evaluation surface is frozen to you. If the rubric seems wrong, that's a `core`-scope lesson.
- **Scrub-and-generalize before anything leaves the project.** Lessons and reports headed to a template owner must carry no corpus content, client identifiers, or local paths — state the lesson so it would be true of the *next* corpus too.
- **Don't judge skill text by how it reads.** Prose quality (clarity, structure, completeness) has zero measured correlation with whether a skill helps. What predicts utility: does it encode *why* failures happen with executable remedies, give step-level domain-specific procedures, and blacklist known-bad actions?
- **When in doubt whether a passage is teaching or trainable — log a lesson, don't edit.**

## What this skill does NOT do

- **Edit John core or template source.** Those are Rings 2 and 1; your evidence flows up, your edits don't.
- **Evolve without evidence.** No speculative "improvements" to skills that aren't measurably or demonstrably fighting the work.
- **Generic prompt-tuning.** The loop is for *worker skills with scorers*. One-off prompts, agent briefings, and PLAN.md text are maintained through their own skills, not trained.
- **Build a universal evaluator.** Feedback design is per-task; the template supplies the domain's instantiation.

## Cross-references

- [[plan-md-evolution]] — the phase-boundary seam where lessons get distilled and override drafts get signed off
- [[phase-design]] — a trainable fan-out phase declares its scorer in its done criteria
- [[event-log-and-reducer]] — events are the training loop's rollout record; gate verdicts persist for the scorecard
- [[subagent-dispatch]] / [[vertical-workflows]] — the fan-out machinery the training loop runs on
- [[workerllm-runtime]] — the worker being trained
- [[packaging]] — trained skills ship with a provenance header
- See `references/` for: the training loop procedure, feedback-collection design, the ledger format, the run-report format + scrub checklist
