# The lessons ledger — format

`<project>/.john/lessons/` — one JSON file per lesson, append-only. Lessons are **immutable**: never edit or delete one; if a lesson turns out wrong, write a new lesson that supersedes it (and says so). Promotion or rejection happens downstream (run reports, template changelogs) — never by mutating the ledger.

## File

`/.john/lessons/<utc-timestamp>-<slug>.json` — timestamp first so the ledger reads chronologically; short slug for humans.

## Schema

```json
{
  "schema_version": 1,
  "created_at": "2026-06-12T08:30:00+00:00",
  "phase": "extract",
  "condition": "when the corpus's tables span chunk boundaries",
  "lesson": "chunk by row group, not by character count — workers extracted half-rows as entries",
  "evidence": [
    ".john/events/extract/sub-7f2-complete.json",
    ".john/checkpoints/extract/gates/20260612T082100Z.json",
    "PLAN.md Log 2026-06-12 (chunking re-run)"
  ],
  "scope_guess": "template",
  "author": "main",
  "supersedes": null
}
```

Field notes:

- **condition** — the applicability context, always. A lesson without a condition is an over-generalization waiting to misfire on the next corpus. If you can't state when it applies, you haven't finished learning it.
- **lesson** — imperative, specific, one or two sentences. The three properties that make skill text useful apply to lessons too: name the failure mechanism, be step-level concrete, and call out the action to avoid.
- **evidence** — pointers, not prose: event files, gate verdicts, checkpoint paths, PLAN.md Log anchors, transcript references. *A lesson without evidence gets rejected at promotion* — the pointer is cheap now and unrecoverable later.
- **scope_guess** — `project` | `template` | `core`. Your honest estimate of where the lesson belongs (use the trainable-vs-teaching test and the core/perimeter/ad-hoc classification from the skill body). This is a *hint* for upstream aggregation, not a routing guarantee.
- **author** — `main`, a subagent id, or `user` (when the user told you something worth keeping). Subagents may write lessons directly during fan-out; same append-only, one-file-per-writer safety as the event log.
- **supersedes** — filename of an earlier lesson this one corrects, or null.

## Discipline

- **Distill at phase boundaries** — the seam where you and the user already review. Mid-phase, jot candidates in your notes; write ledger entries when the phase's evidence is complete.
- **Few and honest beats many and plausible.** Two lessons with real evidence move a template; ten truisms train reviewers to skip the ledger (evolution theater).
- **Corpus text is allowed here** — the ledger is project-local. The scrub-and-generalize gate applies when a lesson is *exported* (run report, shared with a template owner): restate it so it carries no corpus content, client identifiers, or local paths, and would hold for the next corpus of the domain.
- **PLAN.md is not the ledger.** PLAN.md's Log records *what happened to the plan*; the ledger records *what the work taught us*. Log entries may reference lesson files; don't duplicate content across both.
