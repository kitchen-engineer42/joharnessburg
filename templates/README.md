# templates/

Reserved for the **template authoring guide** (lands in M5).

A "template" in John is a sibling plugin layered on top of the joharnessburg core. Templates can add new skills/scripts/commands, override core skills via `skills/_override/<name>/`, or delete core skills via `skills/_delete`. See `PLAN.md` §13 for the full design.

Examples will live at `~/.claude/plugins/joharnessburg-templates/<name>/` once we ship them — not in this directory. This directory holds documentation only.
