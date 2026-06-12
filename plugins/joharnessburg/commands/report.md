---
description: Assemble a run report — the shareable postmortem of this John run (process scorecard + manifest + outcome summary + candidate lessons), privacy-scrubbed. Use when a run wraps or a milestone ships, when the user asks "how did this run go?", "make a run report", or wants evidence to send a template owner. The report is the input format for template evolution; sharing is always manual.
---

When this command fires:

1. Run the process scorecard via Bash (add `--applied-metadata ${CLAUDE_PLUGIN_ROOT}/.applied-metadata.json` when running under an applied template — that file sits at the merged plugin's root):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/process_scorecard.py"
   ```

   On `success: false` ("No .john/ directory"), tell the user there's no workspace to report on — `/john:init` first.

2. Assemble the report at `<project>/.john/reports/<YYYY-MM-DD>-run-report.md`, following the format in the `skill-evolution` skill's `references/run-report-format.md` (1 page: manifest, scorecard highlights, outcome summary, candidate lessons, deviations). Create the `reports/` directory if missing. The scorecard JSON is the evidence backbone; your judgment supplies the outcome summary and the lesson selection — pick the few lessons whose `scope_guess` is `template` or `core` and whose evidence held up.

3. **Walk the scrub-and-generalize checklist** (bottom of the format reference) over the draft — the report is built to LEAVE this project, so it must carry no corpus content, client identifiers, or local filesystem paths. Restate any lesson that fails the check so it would hold for the next corpus of the domain.

4. Show the user the report path and the highlights. Remind them: sharing is manual and theirs — typically to the template's owner as evolution evidence. Nothing is ever transmitted automatically.
