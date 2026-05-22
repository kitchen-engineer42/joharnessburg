# templates/

Reserved for the **template authoring guide** (lands in M5 of the implementation plan).

A "template" in John is a sibling plugin layered on top of joharnessburg core. Templates can:

- Add new skills, scripts, commands, agents
- Override any core skill (same-named skill under `skills/_override/<name>/` fully replaces the core one)
- Delete a core skill (name listed in `skills/_delete`)
- Append to John's CLAUDE.md via `claude_addon.md`
- Seed a starter `PLAN.md` via `plan_md_template.md`

Templates install separately at `~/.claude/plugins/joharnessburg-templates/<name>/`, not in this directory. This `templates/` directory in the joharnessburg core plugin holds documentation only — examples and the template authoring SDK.

The full template system design is documented in the implementation plan (workspace doc, not shipped in this repo). Until M5 ships, no templates exist.
