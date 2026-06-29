# joharnessburg

**John** is the plugin (slash commands `/john:init`, `/john:status`, …); **joharnessburg** is the marketplace/repo it ships from — pronounced "jo-harness-burg" (the harness is in the middle), or "jo-hannesburg" if you prefer the city pun. Hence `claude plugin install john@joharnessburg`.

John wraps Claude Code in skills, hooks, slash commands, and a small toolkit so it can take unstructured input (books, regulations, mixed docs) through the **knowledge phases** (knowledge engineering) and the **app phases** (app building) in one long-running session — and produce a working **knowledge-dense app**: an app that runs a fixed mechanism over many uniform knowledge entries, where the entries come from your corpus. Produced apps **run standalone by default** (locally, `.env`-configured, no external platform assumed); templates can add platform integration.

The project's canonical vocabulary lives in [`CONTEXT.md`](CONTEXT.md); a handful of design decisions are recorded in [`docs/adr/`](docs/adr/).

> 中文版: [`README_ZH.md`](README_ZH.md)

## Install

### Claude Code

```sh
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install john@joharnessburg

# Verify
claude plugin list
# Expect: john@joharnessburg listed, status enabled
```

### Codex

This repo also ships a Codex plugin manifest and local marketplace:

- Plugin manifest: `plugins/joharnessburg/.codex-plugin/plugin.json`
- Codex marketplace: `.agents/plugins/marketplace.json`

Local development install:

```sh
codex plugin marketplace add /path/to/joharnessburg
```

Then enable `john@joharnessburg` in the Codex App plugin UI. Codex does not run Claude slash commands directly; the command equivalents are exposed as skills:

- `John: Init Workspace` — `/john:init`
- `John: Workspace Status` — `/john:status`
- `John: Endurance Goal` — `/john:endurance`
- `John: Archive Workspace` — `/john:archive`

After install, the `using-john` skill auto-loads when you start a fresh Claude Code session. That's John's orientation entry point — Claude reads it and orients itself to the harness.

## Quick start

Open a fresh Claude Code session in a project directory. John's `using-john` skill should trigger on session-start; if not, ask Claude "what is John, how do I use it here?" — that phrasing triggers it.

The natural flow for a new John project:

1. **(Optional) Apply a template** for your app family before launching the session. See [Templates](#templates) below — install at `~/.claude/plugins/joharnessburg-templates/<name>/`, run its `apply.sh`, then launch Claude with `--plugin-dir`. Skip for vanilla John.
2. **Scaffold a workspace** — in Claude Code, run `/john:init` (or just tell Claude "set up John in this dir"); in Codex, use `John: Init Workspace`. This creates `PLAN.md`, `CLAUDE.md`, `AGENTS.md`, and a `.john/` working directory in your project.
3. **Drop your inputs** into `.john/input/` (PDFs, regulations, sample documents — whatever the produced app should be built from).
4. **Tell Claude what kind of app to build**. Claude advances through the phases declared in `PLAN.md` via ralph_loop (the iterative driver), dispatches parallel subagents per phase, and ends with a working app.

Along the way the session *learns from the run* (the `skill-evolution` skill, v0.3.x): lessons are distilled into `.john/lessons/` at phase boundaries, skill invocations and phase-gate verdicts are recorded for the deterministic process scorecard (`scripts/process_scorecard.py`), and — where a template ships a scorer — the produced app's workerLLM skills can be trained with a held-out-gated edit loop during the build.

Other slash commands available after install:

- `/john:status` — current phase + progress
- `/john:report` — assemble the run report (scorecard + outcome + scrubbed lessons; the evidence a template owner aggregates — sharing is always manual)
- `/john:archive` — archive a finished workspace
- `/john:endurance` — set/clear the long-running goal (pinned into the system prompt; survives context compaction)

## Running John with dynamic workflows

John's vertical axis — fanning out hundreds-to-thousands of per-entry subagents (extract every chunk, apply every rule, render every slide) — maps directly onto Claude Code's **dynamic workflows**: Claude writes a script that runs the fan-out off its context, adversarially cross-checks the workers, and writes every result to John's event log. The `vertical-workflows` skill teaches Claude the John-shaped fan-out; you set the session up so it fires on the *right* phases and not on everything.

**Requirements:** Claude Code with dynamic-workflows support (research preview; a recent build on a paid plan), feature enabled.

**Recommended session config** (these are your moves — John reads them, it can't set them for you):

1. **Turn on ultracode.** Run `/effort ultracode` at the start of the session. This is what lets Claude *author* a workflow autonomously; John's skills then steer it to the heavy fan-out phases and keep small/coupled/interactive work inline. Ultracode is **per-session** — it resets when you start a new session, so set it each time (it needs a model that supports `xhigh` effort).
2. **Pre-seed your permission allowlist.** Workflow subagents inherit your tool allowlist; un-allowlisted Bash/web/MCP calls still prompt mid-run and will stall an unattended pipeline. Add the tools John's agents call (Read/Write/Grep/Glob/Bash + your workerLLM and ppx client calls) to your allowlist before a long run.

> **On the keyword trigger — nothing to turn off.** Claude Code's per-prompt workflow trigger is now the word **`ultracode`** (it changed from `workflow` in a mid-2026 update, with Claude using judgment so an incidental mention no longer hijacks a run). John's skills and your messages say "workflow" constantly and that no longer starts a run — so `/effort ultracode` for the session is all you need; type `ultracode` in a prompt only when you want a one-off run.

**Fallback:** none of this is required. If workflows aren't available (older Claude Code, feature off, not in ultracode), John runs the *same* fan-out as inline subagents — same events, same reducer, same `PLAN.md`, same output. Nothing below the execution line changes; you just don't get the off-context scale and the built-in cross-check. John checks availability before its first fan-out phase and tells you the recipe above if the session isn't configured.

**Endurance mode note:** if you set an endurance goal (`/john:endurance <goal>`), John assumes you've done the config above and will *not* pause a long run to re-confirm it — set up the session first, then start the run.

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

To reset: `rm -rf ~/.claude/plugins/joharnessburg-applied/<name>/` (or wipe all with `scripts/reset_john.py`) — **only when no session is using those dirs** (see the warning below). The next launch without `--plugin-dir` uses vanilla John.

### Running several sessions at once (different templates, or vanilla too)

Sessions are isolated by their `--plugin-dir`, so you can run many in parallel — different templates, with vanilla John alongside:

- **One applied dir per template.** Apply each template once to its own `~/.claude/plugins/joharnessburg-applied/<name>/`, and launch each session with `--plugin-dir` at the matching dir. Each project keeps its own `.john/` workspace, independent of which template is loaded.
- **Vanilla** launches from the plugin source itself (`claude --plugin-dir /path/to/joharnessburg/plugins/joharnessburg`), **not** from an applied dir — that also keeps `reset_john.py` from ever touching a vanilla session.
- **⚠️ Never delete or reset an applied dir while a session is using it.** A `--plugin-dir` session reads that directory **live from disk** — hooks re-run their scripts on every tool call and skills load on demand — so deleting it mid-run (a stray `reset_john.py` or `rm -rf`) breaks every live session pointed at it: hooks fail "file not found", skills stop loading. Reset only after those sessions are closed. If it happens by accident, re-apply the same template to the same path; the live session recovers on its next action (or resume it with `claude --continue --plugin-dir <path>`).

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
    templates/                  # Universal apply.sh + authoring guide (templates/README.md)
CONTEXT.md                      # The project glossary — canonical vocabulary
docs/adr/                       # Architecture decision records (short)
README.md                       # This file
README_ZH.md                    # 中文版
LICENSE                         # MIT
```

## Acknowledgments

- [@HalfMoon001](https://github.com/HalfMoon001) — heavy field-testing of John end-to-end, and the analysis behind the `job-runtime` skill ([#2](https://github.com/kitchen-engineer42/joharnessburg/issues/2)): the produced-app long-running I/O job pattern (task registry, slot leases, split queue/generation budgets, resumable progress) was specified from her testing and issue work.
- [@oubeichen](https://github.com/oubeichen) — the Codex adapter (Codex plugin manifest + local marketplace, project hooks, command-mirror skills, and the converted custom agents), and the `app_first_contracts.py` tooling behind the internal-leak guard and the display-first lens.
- [@Ruilin-mmwa](https://github.com/Ruilin-mmwa) — the status-reporting clarity fixes ([#4](https://github.com/kitchen-engineer42/joharnessburg/issues/4) / [#5](https://github.com/kitchen-engineer42/joharnessburg/pull/5)): splitting chunk-completeness severity (`incomplete_chunks` vs `chunks_missing_echo`) and surfacing phase provenance, so the read-only status surfaces stop reading as more alarming or more complete than they are.

## License

John (joharnessburg) is released under the **MIT License** — see [`LICENSE`](LICENSE). Use it, fork it, build on it freely.

Vanilla John and its companion tool Hamster are MIT. Domain-specialized variants built on top of John (e.g. KC Agent CLI) may be offered under separate commercial terms.
