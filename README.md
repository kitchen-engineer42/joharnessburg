# joharnessburg

**John** — a Claude Code plugin that wraps Claude Code in skills, hooks, slash commands, and a small toolkit so it can take unstructured input (books, regulations, mixed docs) through knowledge engineering and app building in one long-running session.

Plugin slug: `joharnessburg`. Pronounced "jo-harness-burg" (the harness is in the middle), or "jo-hannesburg" if you prefer the city pun. Either's fine.

## Templates (v0.1.7+ diff-script architecture)

Templates are **diffs to original John**, applied via a one-click script. `/joharnessburg-template <name>` does the whole flow: set active_template in workspace.json, run apply.sh, print the launch command.

- **Authoring guide**: [`templates/README.md`](templates/README.md) — directory anatomy, apply mechanics, switching/reset.
- **Bundled examples**: [`templates/examples/slides-from-textbook/`](templates/examples/slides-from-textbook/) (lighter — 1 override + 1 add) and [`templates/examples/doc-verification/`](templates/examples/doc-verification/) (heavier, KC-style — 2 overrides + 2 adds). Both have `apply.sh` symlinks.

Both bundled examples are **functional demonstrators**, not production-ready. The team's production templates ship separately.

## Local clients (workspace-level, outside the plugin)

The LLM + ppx clients live OUTSIDE this plugin in your John workspace at `local_clients/{llm,ppx}/`. They're standalone FastAPI servers — the team installs + launches them locally; the plugin's `parsing` + `workerllm-runtime` skills teach Claude how to call them via env-var-configured URLs (`$JOHN_LLM_CLIENT_URL`, `$JOHN_PPX_CLIENT_URL`).

When the tech team ships the production servers, swap those env vars; nothing in John changes.

### One-time setup (per machine)

Assumes you have the John workspace (which contains `local_clients/`, `setup_john.sh`, etc.) and `uv` installed (https://docs.astral.sh/uv/).

```sh
# 1. Clone the ppx engine somewhere outside the workspace
git clone https://github.com/kitchen-engineer42/ppx.git ~/code/ppx

# 2. Run the workspace setup script — creates venvs + installs both clients
cd /path/to/john-workspace
./setup_john.sh
# First run will create .env from .env.example and prompt you to fill in keys.
# Edit .env to add SILICONFLOW_API_KEY + DEEPSEEK_API_KEY, then re-run setup_john.sh.

# 3. Install the ppx engine into the ppx client's venv
cd /path/to/john-workspace/local_clients/ppx
uv pip install -e ~/code/ppx

# 4. Verify
cd /path/to/john-workspace
./setup_john.sh
# Should report: "memect-ppx is installed in the ppx client's venv."
```

### Per-session launch

```sh
cd /path/to/john-workspace
./start_john.sh
# Reports both clients' liveness; prints the env vars to export.

# Then in your Claude Code shell (or persist in your .zshrc / .bashrc):
export JOHN_LLM_CLIENT_URL=http://localhost:8500
export JOHN_PPX_CLIENT_URL=http://localhost:8501

# Launch Claude Code in your project:
cd /path/to/your-project
claude
```

To stop:

```sh
cd /path/to/john-workspace
./stop_john.sh
```

### Smoke test (verify the chain works end-to-end)

```sh
# LLM client health + provider inventory
curl -s http://localhost:8500/healthz | jq

# Actual LLM call (should return "OK" or similar)
curl -s http://localhost:8500/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"reply with just OK"}]}' | jq

# ppx client health (should say "ppx: available")
curl -s http://localhost:8501/healthz | jq
```

### Reference docs

- `local_clients/llm/README.md` — LLM client install + API contract
- `local_clients/ppx/README.md` — ppx client install + API contract
- Workspace `/skills/local-clients-builder/` — methodology for authoring clients against different providers or on-prem infra (parallel to skill-creator)
- `joharnessburg/skills/workerllm-runtime/SKILL.md` — how the plugin's skills teach Claude to call these clients

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

Copyright (C) 2026 Memect.

John (joharnessburg) is free software: you can redistribute it and/or modify it under the terms of the **GNU Affero General Public License, version 3 or (at your option) any later version**, as published by the Free Software Foundation. See [`LICENSE`](LICENSE) for the full text.

This program is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

The AGPL's network-use clause (§13) applies: if you run a modified version of John as a service over a network, you must make the modified source available to its users. This is the explicit choice — John is designed for knowledge-engineering pipelines that often run as internal services, and we want derivatives to stay open.

If the AGPL doesn't fit your use case, contact the copyright holder about a commercial license.
