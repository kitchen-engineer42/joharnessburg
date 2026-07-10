# John

> 中文版: [`README_ZH.md`](README_ZH.md)

John turns unstructured source material into a working knowledge-dense app. It keeps knowledge engineering and app building in one durable run, coordinates large per-entry fan-outs, and leaves auditable events and checkpoints on disk.

Use either **Claude Code or Codex**. Both are recommended runtimes over the same John plugin, skills, scripts, hooks, workspace state, and template format.

## Install and update

### Claude Code

Install and verify:

```sh
claude plugin marketplace add kitchen-engineer42/joharnessburg
claude plugin install john@joharnessburg
claude plugin list
```

Then run `/reload-plugins` in an active session, or start a fresh Claude Code session.

Update and verify:

```sh
claude plugin marketplace update joharnessburg
claude plugin update john@joharnessburg
claude plugin list
```

Run `/reload-plugins` or start a fresh session after the update.

### Codex

Install and verify:

```sh
codex plugin marketplace add kitchen-engineer42/joharnessburg
codex plugin add john@joharnessburg
codex plugin list
```

Restart Codex or start a new task so the plugin reloads. Open `/hooks`, inspect John's hook definition, and trust it only after review; installing the plugin does not trust its hooks automatically.

Update and verify:

```sh
codex plugin marketplace upgrade joharnessburg
codex plugin add john@joharnessburg
codex plugin list
```

`codex plugin add` is idempotent and refreshes the installed plugin from the upgraded marketplace snapshot. Review `/hooks` again if the definition changed, then restart Codex or start a new task.

## Quick start

Open your project in either runtime, initialize John with an optional input file or directory, confirm the generated `PLAN.md`, then describe the app you want. John advances through the knowledge and app phases while `.john/events/`, `.john/checkpoints/`, and `.john/runs/` preserve durable evidence.

| Operation | Claude Code | Codex |
|---|---|---|
| Initialize | `/john:init <input-path>` | “Use `init-workspace` to initialize John from `<input-path>`.” |
| Status | `/john:status` | “Use `workspace-status` to show the John workspace status.” |
| Run report | `/john:report` | “Use `codex-run-report` to generate the John run report.” |
| Endurance goal | `/john:endurance <goal>` | “Use `endurance-goal` to set `<goal>`.” |
| Archive | `/john:archive [label]` | “Use `archive-workspace` to archive this John workspace.” |

John initializes both `CLAUDE.md` and `AGENTS.md`, plus byte-identical project skill trees under `.claude/skills/` and `.agents/skills/` when knowledge is packaged.

## Scale-out execution

- **Claude Code:** `vertical-workflows` can author Claude dynamic workflows for large uniform fan-outs. When unavailable, the same work runs through inline subagent waves.
- **Codex:** `codex-vertical-workflows` uses native subagent waves and the durable `.john/runs/` ledger for retries, reconciliation, status, and cancellation.

Both paths emit the same events, pass the same extraction audits, reduce into the same checkpoints, and continue through the same `PLAN.md`.

## Templates

A John template is a version-pinned diff that specializes the shared harness for one app family. Install it as a regular directory, apply it once, and use the resulting merged plugin; the same applied output serves both providers.

```sh
cp -R /path/to/template ~/.claude/plugins/joharnessburg-templates/<name>
~/.claude/plugins/joharnessburg-templates/<name>/apply.sh
```

For **Claude Code**, launch the printed path:

```sh
claude --plugin-dir ~/.claude/plugins/joharnessburg-applied/<name>
```

For **Codex**, activate that same merged plugin in the target project:

```sh
python3 ~/.claude/plugins/joharnessburg-applied/<name>/scripts/activate_codex_template.py \
  --merged-plugin ~/.claude/plugins/joharnessburg-applied/<name> \
  --project-root /path/to/project
```

Follow the printed steps: add the project-local marketplace, install the applied listing, verify it with `codex plugin list`, disable vanilla `john@joharnessburg` for that project, inspect and trust the applied hooks through `/hooks`, and restart Codex. Activation prepares project-local files only; it does not change personal marketplace or global plugin state automatically.

Do not delete an applied directory while a live session is using it. See the [template authoring guide](plugins/joharnessburg/templates/README.md) for the format and [Hamster](https://github.com/kitchen-engineer42/hamster) for dual-provider examples and a guided authoring workflow.

## Prerequisites and optional services

- Python 3.10+ for John's standard-library toolkit.
- Optional `markitdown` for non-PDF conversion.
- Optional PPX-compatible service at `$JOHN_PPX_CLIENT_URL` for high-fidelity PDFs.
- Optional OpenAI-compatible workerLLM service at `$JOHN_LLM_CLIENT_URL` for produced apps that need runtime model calls.

John installs and runs without the optional services. They are external URL contracts, not package dependencies.

## Hook trust

[`hooks/hooks.json`](plugins/joharnessburg/hooks/hooks.json) is John's sole hook declaration. Hooks execute the bundled scripts with the active coding session's permissions. Review this file and the referenced scripts before trusting an unfamiliar fork. Codex users must review and trust the current definition through `/hooks`; plugin installation or enablement alone is not trust.

## Repository layout

```text
.claude-plugin/marketplace.json       Claude marketplace
.agents/plugins/marketplace.json      Codex marketplace
plugins/joharnessburg/
  .claude-plugin/plugin.json          Claude manifest
  .codex-plugin/plugin.json           Codex manifest
  hooks/                              shared hook declaration
  skills/                             shared + provider adapter skills
  commands/                           Claude slash commands
  agents/                             canonical Markdown agents
  codex/agents/                       generated Codex agents
  scripts/                            deterministic toolkit
  templates/                          apply script and authoring guide
CONTEXT.md                            canonical vocabulary
```

## Credits

John is maintained by [kitchen-engineer42](https://github.com/kitchen-engineer42), with contributions and field evidence from [@HalfMoon001](https://github.com/HalfMoon001), [@oubeichen](https://github.com/oubeichen), [@Ruilin-mmwa](https://github.com/Ruilin-mmwa), and [@AnselKocen](https://github.com/AnselKocen).

## License

MIT. See [`LICENSE`](LICENSE).
