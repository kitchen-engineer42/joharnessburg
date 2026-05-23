# joharnessburg

**John** — a Claude Code plugin that wraps Claude Code in skills, hooks, slash commands, and a small toolkit so it can take unstructured input (books, regulations, mixed docs) through knowledge engineering and app building in one long-running session.

Plugin slug: `joharnessburg`. Pronounced "jo-harness-burg" (the harness is in the middle), or "jo-hannesburg" if you prefer the city pun. Either's fine.

## Status

**v0.1.7 — Local-client architecture + template diff-scripts + audit-driven cleanup.** Major architecture refactor on top of v0.1.6:

- **External local-client servers** (workspace-level, outside the plugin): FastAPI HTTP servers at `/Users/mac/Desktop/john/local_clients/{llm,ppx}/` wrap SiliconFlow + DeepSeek (OpenAI-compatible) and `memect-ppx`. John talks to them via env vars (`$JOHN_LLM_CLIENT_URL`, `$JOHN_PPX_CLIENT_URL`). When the tech team deploys production servers, swap the URLs — no code changes in John.
- **Template diff-script architecture**: templates are now diffs applied via `apply_template.py` (one-click), not session-time overlays. Result: a merged plugin dir at `~/.claude/plugins/joharnessburg-applied/<name>/` that the user launches with `claude --plugin-dir <path>`. After merge, template content IS John — no second-class layer.
- **New skill** `workerllm-runtime/` teaches produced apps how to call the LLM client.
- **JSON discipline** added to all 3 agent prompts (full-width quotes / `json.dumps()` to avoid the ~10% defect rate observed in M6).
- **Reducer quarantine**: `reduce_events.py` now moves malformed events to `_quarantine/` rather than silently skipping; counts surfaced.
- **ppx ↔ jyppx terminology** sweep: 23 mentions across 13 files reconciled. `ppx_parse.py` now writes `"parser": "ppx"` (was `"jyppx"` — soft schema break in v0.1.7).
- **Bug fixes**: TOCTOU race in PreCompact hook, silent-fallback in markitdown_parse.py, hardcoded path in set_template.py, --force docstring in init_workspace.py, is_dir guard in workspace_status.py.

**64 unit tests green** (53 v0.1.6 + 6 apply_template + 5 reset_john tests). Plugin loads with 8 core meta-skills + 6 2skills phase skills + 3 2app phase skills + 9 platform-integration skill stubs + new `workerllm-runtime` skill (27 total) + 7 toolkit scripts + 2 new template-system scripts (apply_template, reset_john) + 5 slash commands + 3 hooks + 3 agents + 2 example templates with one-click `apply.sh`. M7 (handoff docs) still ahead.

## Templates (v0.1.7+ diff-script architecture)

Templates are **diffs to original John**, applied via a one-click script. `/joharnessburg-template <name>` does the whole flow: set active_template in workspace.json, run apply.sh, print the launch command.

- **Authoring guide**: [`templates/README.md`](templates/README.md) — directory anatomy, apply mechanics, switching/reset.
- **Bundled examples**: [`templates/examples/slides-from-textbook/`](templates/examples/slides-from-textbook/) (lighter — 1 override + 1 add) and [`templates/examples/doc-verification/`](templates/examples/doc-verification/) (heavier, KC-style — 2 overrides + 2 adds). Both have `apply.sh` symlinks.

Both bundled examples are **functional demonstrators**, not production-ready. The team's production templates ship separately.

## Local clients (workspace-level, outside the plugin)

The LLM + ppx clients live OUTSIDE this plugin at `/Users/mac/Desktop/john/local_clients/{llm,ppx}/`. They're standalone FastAPI servers. The team is expected to install + launch them locally; the plugin's parsing skill + workerllm-runtime skill teach Claude how to call them. See:

- `local_clients/llm/README.md` — install + launch the LLM proxy
- `local_clients/ppx/README.md` — install + launch the ppx server
- Workspace `/skills/local-clients-builder/` — methodology for building your own clients (different providers, on-prem, etc.)

## Prerequisites

- **Python 3.10+** (the toolkit scripts use stdlib only; system Python is fine).
- For non-PDF document parsing (`markitdown_parse.py`): `pip install markitdown`.
- For PDF parsing: v0.1.7+ uses an out-of-plugin **ppx-client server** (FastAPI) that wraps `memect-ppx` (the `ppx` parser engine — repo at `github.com/kitchen-engineer42/ppx`). The plugin's `scripts/ppx_parse.py` is a thin HTTP client to that server; install the server from `/Users/mac/Desktop/john/local_clients/ppx/` and launch with `scripts/start.sh`. The ppx engine itself must be installed (`uv pip install -e /path/to/ppx`); jyppx is a separate builder project that uses ppx as a library and is NOT required to drive John.

Both parser dependencies are optional. The plugin installs and `using-john` loads regardless; the parser scripts fail loud with install instructions when invoked without their deps.

## Install + upgrade

First-time install:

```sh
# Option A — marketplace flow (recommended):
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install joharnessburg@joharnessburg

# Verify
claude plugin list
# Expect: joharnessburg@joharnessburg listed, status enabled
```

Upgrade from an earlier version (v0.1.x → v0.1.7):

```sh
claude plugin marketplace update joharnessburg
claude plugin update joharnessburg@joharnessburg
# Restart Claude Code for the new version to take effect.
```

> Note: `claude plugin install` is a no-op when the plugin is already installed. Use `claude plugin update <plugin>@<marketplace>` for upgrades. Auto-update is OFF by default for third-party marketplaces; enable via `/plugin` UI → Marketplaces → joharnessburg → Enable auto-update.

In a fresh Claude Code session after install, the `using-john` skill should load. That's the M0 acceptance test.

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
