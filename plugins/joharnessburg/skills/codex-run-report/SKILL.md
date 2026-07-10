---
name: codex-run-report
description: Generate John's process scorecard, auditor manifests, and shareable run report from a Codex project using John's provider-neutral scripts. Use when the user asks for a John report, run report, scorecard, provenance manifest, self-evaluation manifest, or evidence for template evolution while working in Codex.
---

# Codex run report

Run the deterministic report pipeline from the initialized project root:

```sh
python3 "<john-plugin>/scripts/process_scorecard.py"
python3 "<john-plugin>/scripts/emit_manifests.py"
```

Then follow the shared report scrub-and-generalize contract in John's
`skill-evolution` guidance before writing a shareable Markdown report under
`.john/reports/`. Do not infer Codex skill-invocation counts: the scorecard
marks Claude Skill-tool telemetry as unsupported on Codex while still counting
both `.claude/skills/` and `.agents/skills/` outputs.

Use the JSON fields for evidence. Keep provider execution details separate from
the provider-neutral event, checkpoint, lesson, and produced-skill results.
