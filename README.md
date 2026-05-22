# joharnessburg

**John** — a Claude Code plugin that wraps Claude Code in skills, hooks, slash commands, and a small toolkit so it can take unstructured input (books, regulations, mixed docs) through knowledge engineering and app building in one long-running session.

Plugin slug: `joharnessburg`. Pronounced "jo-harness-burg" (the harness is in the middle), or "jo-hannesburg" if you prefer the city pun. Either's fine.

## Status

**v0.1.0 — M0 scaffold.** The plugin installs but is mostly skeleton. Skill bodies, scripts, hooks, and templates ship over M1–M7.

## Install

Three options, pick whichever fits your workflow:

```sh
# Option A — marketplace flow (recommended; mirrors how plugins like skills-analytics install):
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install joharnessburg

# Option B — clone + local install (for offline dev iteration):
git clone git@github.com:kitchen-engineer42/joharnessburg.git /path/to/clone
claude plugin install /path/to/clone

# Option C — symlink (for live editing the plugin while testing):
git clone git@github.com:kitchen-engineer42/joharnessburg.git /path/to/clone
mkdir -p ~/.claude/plugins
ln -s /path/to/clone ~/.claude/plugins/joharnessburg

# Verify (all options):
claude plugin list
# Expect: joharnessburg listed, status enabled
```

In a fresh Claude Code session after install, the `using-john` skill should be available. That's the M0 acceptance test.

## What's in this repo

```
.claude-plugin/
  plugin.json         # Claude Code plugin manifest
  marketplace.json    # Lets the repo double as a marketplace
hooks/hooks.json      # Hook declarations (auto-registered on install)
skills/               # John's meta-skills (layer-2; loaded into John-wrapped Claude Code sessions)
commands/             # Slash commands
scripts/              # Small Python toolkit (ppx wrapper, event reducer, scaffolder, etc.)
agents/               # Subagent role definitions
templates/            # Template authoring docs (templates themselves install separately)
README.md             # This file
```

## Where the design docs live

The implementation plan, spec history, design comparisons, and dev journal live in the **John workspace** — a separate directory where the plugin is developed:

- `PLAN.md` — live implementation plan (M0 → M7)
- `docs/initial_spec.md` — spec history + user replies
- `docs/architecture_and_plan.md` — draft PLAN was promoted from
- `docs/ralph_in_john_vs_original.md` — how John's ralph-loop differs from snarktank/ralph
- `docs/john_vs_open_source_harnesses.md` — fresh comparison vs 7 open-source harnesses
- `CLAUDE.md` — workspace memory
- `DEVLOG.md` — append-only dev journal

These aren't shipped in the plugin repo (they describe **building** John, not the plugin itself). If you're contributing and need the design rationale, ask the project owner for workspace access.

## License

Internal use only for now. No external distribution planned.
