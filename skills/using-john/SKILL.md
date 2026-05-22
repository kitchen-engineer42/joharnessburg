---
name: using-john
description: Top-level orientation for John (joharnessburg) — read this first when working in a Claude Code session where the John plugin is loaded and the user wants you to do knowledge-dense app building. M0 stub; full body lands in M1.
---

# using-john

You are working inside a Claude Code session where the **joharnessburg** plugin is loaded — the John harness for taking unstructured input through knowledge engineering and app building in one long-running session.

This is an **M0 stub**. The real orientation skill — covering the workspace shape `<user-project>/.john/`, the 2skills + 2app halves, ralph-loop, endurance mode, subagent dispatch, the event-log + reducer pattern, and what to expect at each phase — lands in M1.

For now, the only operational guidance:

- If the user's project doesn't yet have a `PLAN.md` at the project root or a `.john/` directory, John hasn't been initialized for this project yet. Suggest they run `/joharnessburg-init` (also still a stub at M0).
- If `PLAN.md` and `.john/` already exist in this project, that's the durable plan and working state — read those first to understand what's been done and what's next.
- All other skills John ships (ralph-loop, plan-md-authoring, phase-design, etc.) are stubs at M0. They'll load but won't have substantive bodies until M1 or later.

Tell the user M0 is in place but no substantive workflow is wired up yet, and ask which milestone they want to pick up.
