# description-pushiness — combat undertriggering

skill-creator's central piece of writing advice: LLMs tend to **undertrigger** skills they have available. A skill that's relevant to the current task may not be consulted because the description didn't make its applicability obvious enough.

The fix: write descriptions that are *pushy* — explicit about when to use the skill, with multiple framings, leaning into the verbs and contexts that should trigger consultation.

## Bad (passive)

```yaml
description: How to build a dashboard for internal company data.
```

The model sees this and thinks "OK, when there's clearly a dashboard task." But "clearly a dashboard task" is a subset of cases where the skill is useful. The user might say "I need to see our metrics over time" — that's a dashboard task; the model might not recognize it.

## Good (pushy)

```yaml
description: How to build a simple fast dashboard for displaying internal company data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, performance tracking, KPI displays, or wants to display ANY kind of company data — even if they don't use the word "dashboard."
```

This explicitly names the contexts in which to trigger. The model now knows that "show me our metrics" should consult this skill, even though the user didn't say "dashboard."

## Pattern

Pushy descriptions follow a structure:

1. **What** the skill does, in plain terms.
2. **When** to use it — multiple framings of the triggering context.
3. **Coverage of indirect mentions** — what users say that should trigger this even when they don't use the skill's own terminology.

## Caution

Pushiness has limits. Description that's *too* eager (e.g., "use this for any data-related task, ever") causes *overtriggering* — the skill loads when it shouldn't, wasting context on irrelevant material.

Calibrate by imagining 10 user prompts:

- For 5 that the skill is genuinely useful for, would the description trigger? (yes → good coverage)
- For 5 that the skill is irrelevant to, would the description trigger? (no → good precision)

If overtriggering, narrow the description. If undertriggering, broaden it. The skill-creator description-optimization loop (`run_loop.py`) automates this calibration if needed.

## Source

The skill-creator skill's `SKILL.md` documents this in detail. Its `run_loop.py` script does automated description optimization with a held-out test set.
