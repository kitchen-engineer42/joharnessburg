# The run report — format + scrub checklist

One page. The shareable postmortem of a John run: what was built, how the run behaved, what it taught. This is the input format template owners aggregate when evolving a template — write it so a stranger who never saw your corpus can act on it. Assembled by `/john:report` at `<project>/.john/reports/<date>-run-report.md`.

## Format

```markdown
# Run report — <project name>, <date>

## Manifest
- John version: <created_by_john_version from the scorecard>
- Template: <name + version, or "vanilla John">
- Corpus: <DESCRIPTION ONLY — domain, language, rough size; never content>
- Session shape: <one line: endurance? interventions? sessions/devices>

## Process (scorecard highlights — attach or inline the JSON)
- Phases run: <n> | zero-event phases: <list or none>
- Gates: <per phase: status(claimed)> | incomplete chunks: <n>
- Fan-out: <which phases fanned out, how many subagents>
- Skill invocations: <total; notable absences — e.g. "packaging never invoked">

## Outcome (your judgment + any domain scores)
- What shipped: <one or two lines>
- Domain scores, if a scorer exists: <baseline → final, which split>
- End-user reactions, if any: <summarized — the runtime-results feedback>

## Candidate lessons (scrubbed; full ledger stays in the project)
1. [scope: template] <condition> → <lesson> (evidence: <pointer type — e.g.
   "gate verdict, extract phase">)
2. ...

## Deviations
- Skill overrides applied: <which, why, draft-or-autonomous, reported when>
- Declared skips: <e.g. "knowledge phases skipped — pre-digested corpus">
```

Short is correct. The scorecard JSON carries the detail; the report carries the judgment. Two or three well-evidenced lessons beat ten.

## The scrub-and-generalize checklist (run before the report leaves the project)

The report crosses the ring boundary — the same discipline as lesson promotion:

1. **No corpus content.** No quoted passages, clause numbers, entity names, figures from the user's documents. Grep your draft for the corpus's distinctive terms (project names, party names, document identifiers) — zero hits.
2. **No client/user identifiers.** People, companies, internal system names, repo names that aren't public.
3. **No local paths.** Nothing matching `/Users/`, `/home/`, `C:\`, or the machine's home directory. Evidence pointers become *pointer types* ("gate verdict, extract phase"), not absolute paths.
4. **Lessons generalized.** Each lesson restated so it would hold for the *next* corpus of this domain — if it only makes sense knowing this corpus, it isn't ready to leave (keep it project-scoped in the ledger instead).
5. **Scores carry their split.** A score without "on which held-out set" is noise to the aggregator.

If a lesson can't pass the checklist without losing its meaning, it stays in the ledger — that's a legitimate outcome, not a failure.
