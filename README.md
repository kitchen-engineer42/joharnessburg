# joharnessburg

**John** — a Claude Code plugin that turns Claude Code into a harness for building knowledge-dense apps. Take unstructured input (books, regulations, docs, mixed media) through knowledge engineering and app building in one long-running session.

Plugin slug: `joharnessburg`. Pronounced "jo-harness-burg" (the harness is in the middle), or "jo-hannesburg" if you prefer the city pun. Either's fine.

## Status

**v0.1.0 — M0 scaffold.** The plugin installs but is mostly skeleton. Real skill bodies, scripts, hooks, and templates ship over M1–M7 (see `PLAN.md`).

## Install (local dev)

From a checkout of this repo:

```sh
# Option A: official local-path install (if supported by your Claude Code version)
claude plugin install /path/to/john

# Option B: symlink for live iteration during dev
ln -s /path/to/john ~/.claude/plugins/joharnessburg

# Verify either way:
claude plugin list   # should show 'joharnessburg'
```

In a fresh Claude Code session after install, the `using-john` skill should be available. That's the M0 acceptance test.

## What's in this repo

```
PLAN.md                    # the durable implementation plan (live document)
CLAUDE.md                  # project memory; future sessions read this first
DEVLOG.md                  # append-only dev journal
.claude-plugin/plugin.json # Claude Code plugin manifest
skills/                    # John's meta-skills (the "fat" in "thin harness, fat skills")
commands/                  # slash commands
scripts/                   # small Python toolkit (ppx wrapper, event reducer, scaffolder)
agents/                    # subagent role definitions
hooks/hooks.json           # event handlers (SessionStart, PreCompact, etc.)
templates/                 # template authoring guide + example template
docs/                      # design docs, comparisons, spec history
```

## For team members reading the source

Start with **`PLAN.md`** at the project root (the live implementation plan). Then `docs/initial_spec.md` for the user's vision and decisions, and `CLAUDE.md` for working agreements + naming conventions.

## License

Internal use only for now. No external distribution planned.
