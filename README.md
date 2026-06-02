# joharnessburg

**John** — a Claude Code plugin that wraps Claude Code in skills, hooks, slash commands, and a small toolkit so it can take unstructured input (books, regulations, mixed docs) through knowledge engineering and app building in one long-running session.

Plugin name: `john` (so its slash commands are `/john:init`, `/john:status`, etc.). It's distributed through the `joharnessburg` marketplace — pronounced "jo-harness-burg" (the harness is in the middle), or "jo-hannesburg" if you prefer the city pun. Hence `claude plugin install john@joharnessburg`.

> 中文版: [`README_ZH.md`](README_ZH.md)

## Install

```sh
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install john@joharnessburg

# Verify
claude plugin list
# Expect: john@joharnessburg listed, status enabled
```

After install, the `using-john` skill auto-loads when you start a fresh Claude Code session. That's John's orientation entry point — Claude reads it and orients itself to the harness.

## Quick start

Open a fresh Claude Code session in a project directory. John's `using-john` skill should trigger on session-start; if not, ask Claude "what is John, how do I use it here?" — that phrasing triggers it.

The natural flow for a new John project:

1. **(Optional) Apply a template** for your app family before launching the session. See [Templates](#templates) below — install at `~/.claude/plugins/joharnessburg-templates/<name>/`, run its `apply.sh`, then launch Claude with `--plugin-dir`. Skip for vanilla John.
2. **Scaffold a workspace** — run `/john:init` (or just tell Claude "set up John in this dir"). This creates `PLAN.md`, `CLAUDE.md`, and a `.john/` working directory in your project.
3. **Drop your inputs** into `.john/input/` (PDFs, regulations, sample documents — whatever the produced app should be built from).
4. **Tell Claude what kind of app to build**. Claude advances through the phases declared in `PLAN.md` via ralph_loop (the iterative driver), dispatches parallel subagents per phase, and ends with a working app.

Other slash commands available after install:

- `/john:status` — current phase + progress
- `/john:archive` — archive a finished workspace
- `/endurance` — re-enter long-running mode if the session has gone idle

## Running John with dynamic workflows

John's vertical axis — fanning out hundreds-to-thousands of per-entry subagents (extract every chunk, apply every rule, render every slide) — maps directly onto Claude Code's **dynamic workflows**: Claude writes a script that runs the fan-out off its context, adversarially cross-checks the workers, and writes every result to John's event log. The `vertical-workflows` skill teaches Claude the John-shaped fan-out; you set the session up so it fires on the *right* phases and not on everything.

**Requirements:** Claude Code with dynamic-workflows support (research preview; a recent build on a paid plan), feature enabled.

**Recommended session config** (these are your moves — John reads them, it can't set them for you):

1. **Turn off the workflow keyword trigger.** In `/config`, switch off **Workflow keyword trigger**. Otherwise the mere word "workflow" — common in John's own prose and your messages — fires a workflow you didn't intend. Turning it off makes workflow use deliberate.
2. **Turn on ultracode.** Run `/effort ultracode` at the start of the session. This is what lets Claude *author* a workflow autonomously (no keyword needed); John's skills then steer it to the heavy fan-out phases and keep small/coupled/interactive work inline. Ultracode is **per-session** — it resets when you start a new session, so set it each time (it needs a model that supports `xhigh` effort).
3. **Pre-seed your permission allowlist.** Workflow subagents inherit your tool allowlist; un-allowlisted Bash/web/MCP calls still prompt mid-run and will stall an unattended pipeline. Add the tools John's agents call (Read/Write/Grep/Glob/Bash + your workerLLM and ppx client calls) to your allowlist before a long run.

**Fallback:** none of this is required. If workflows aren't available (older Claude Code, feature off, not in ultracode), John runs the *same* fan-out as inline subagents — same events, same reducer, same `PLAN.md`, same output. Nothing below the execution line changes; you just don't get the off-context scale and the built-in cross-check.

## Upgrade

```sh
claude plugin marketplace update joharnessburg
claude plugin update john@joharnessburg
# Restart Claude Code for the new version to take effect.
```

> Note: `claude plugin install` is a no-op when the plugin is already installed. Use `claude plugin update <plugin>@<marketplace>` for upgrades. Auto-update is OFF by default for third-party marketplaces; enable via the `/plugin` UI → Marketplaces → joharnessburg → Enable auto-update if you want it on.

## Prerequisites

- **Python 3.10+** — the plugin's toolkit scripts use stdlib only; system Python is fine.
- For **non-PDF document parsing** (`markitdown_parse.py`): `pip install markitdown`.
- For **PDF parsing**: an external `local_clients/ppx/` FastAPI server wrapping `memect-ppx`. See [Local clients](#local-clients) below.
- For **workerLLM calls at runtime**: an external `local_clients/llm/` FastAPI server. Also under [Local clients](#local-clients).

Both parser dependencies are optional. The plugin installs and `using-john` loads regardless; parser scripts fail loud with install instructions when invoked without their deps.

## Templates

Templates **specialize John for a family of apps**. A template is a *diff against original John* that purpose-builds the harness for one kind of pipeline (overriding some skills, adding new ones, shipping a starter `PLAN.md` skeleton).

The three-step flow:

```sh
# 1. Install the template (copy or symlink into user-scope template dir)
cp -R /path/to/your-template ~/.claude/plugins/joharnessburg-templates/your-template

# 2. Apply it (produces a merged plugin at ~/.claude/plugins/joharnessburg-applied/<name>/)
~/.claude/plugins/joharnessburg-templates/your-template/apply.sh

# 3. Launch Claude with the merged plugin
cd /path/to/your-project
claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/your-template
```

The merged plugin IS John for that session — all template skills load equally with the core ones; there's no second-class "template layer." Which template is loaded is fixed at session start; to switch, exit and relaunch with a different `--plugin-dir`. Multiple applied templates can coexist (parallel Claude sessions can use different ones).

To reset: `rm -rf ~/.claude/plugins/joharnessburg-applied/<name>/` (or wipe all with `~/.claude/plugins/joharnessburg-applied/`). The next launch without `--plugin-dir` uses vanilla John.

**Where to find templates**: This plugin ships no bundled examples — that keeps John's runtime focused on the one template you load (or none). Reference examples (functional demonstrators of the diff format) live in the companion tool **Hamster** ([github.com/kitchen-engineer42/hamster](https://github.com/kitchen-engineer42/hamster)) under `examples/`. Real production templates ship separately from your team.

To author your own template, see [`plugins/joharnessburg/templates/README.md`](plugins/joharnessburg/templates/README.md) for the diff-script architecture, directory anatomy, and `apply.sh` mechanics. For a guided, Claude-driven authoring experience, use Hamster — it ships skills + a methodology that walk Claude Code through building a template from raw inputs.

## Local clients

For LLM calls + PDF parsing, John talks to **external FastAPI servers** that you run alongside the plugin. They live OUTSIDE the plugin (workspace-level) so you can swap providers without changing John itself.

The plugin's `parsing` + `workerllm-runtime` skills teach Claude to call them via env-var-configured URLs:

- `$JOHN_LLM_CLIENT_URL` (default `http://localhost:8500`) — workerLLM client (wraps SiliconFlow + DeepSeek today).
- `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`) — PDF parser client (wraps `memect-ppx`, the `ppx` parser engine at [github.com/kitchen-engineer42/ppx](https://github.com/kitchen-engineer42/ppx)).

When your team ships its own production servers (on-prem or different providers), swap these env vars — nothing inside John changes.

### One-time setup (per machine)

Prerequisite: [`uv`](https://docs.astral.sh/uv/) installed. Get the John workspace bundle (which contains `local_clients/` + `setup_john.sh`) — contact the project owner for access if you don't already have it.

```sh
# 1. Clone the ppx engine outside the workspace
git clone https://github.com/kitchen-engineer42/ppx.git ~/code/ppx

# 2. Run the workspace setup script — creates venvs + installs both clients
cd /path/to/john-workspace
./setup_john.sh
# First run will create .env from .env.example; fill in SILICONFLOW_API_KEY + DEEPSEEK_API_KEY.

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

# Then in your Claude Code shell (or persist in .zshrc / .bashrc):
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
- `plugins/joharnessburg/skills/workerllm-runtime/SKILL.md` — how the plugin teaches Claude to call these clients

## What's in this repo

```
.claude-plugin/
  marketplace.json              # Marketplace catalog (this repo is also a marketplace)
plugins/
  joharnessburg/                # The plugin itself
    .claude-plugin/
      plugin.json               # Claude Code plugin manifest
    hooks/hooks.json            # Hook declarations (auto-registered on install)
    skills/                     # John's meta-skills (loaded into John-wrapped Claude Code sessions)
    commands/                   # Slash commands
    scripts/                    # Small Python toolkit (ppx wrapper, event reducer, apply_template, etc.)
    agents/                     # Subagent role definitions
    templates/                  # Universal apply.sh + authoring guide (templates/README.md); plus any promoted templates
README.md                       # This file
README_ZH.md                    # 中文版
LICENSE                         # AGPL-3.0-or-later
```

## License

Copyright (C) 2026 kitchen-engineer42.

John (joharnessburg) is free software: you can redistribute it and/or modify it under the terms of the **GNU Affero General Public License, version 3 or (at your option) any later version**, as published by the Free Software Foundation. See [`LICENSE`](LICENSE) for the full text.

This program is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

The AGPL's network-use clause (§13) applies: if you run a modified version of John as a service over a network, you must make the modified source available to its users. This is the explicit choice — John is designed for knowledge-engineering pipelines that often run as internal services, and we want derivatives to stay open.

If the AGPL doesn't fit your use case, contact the copyright holder about a commercial license.
