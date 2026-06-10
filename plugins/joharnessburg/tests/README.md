# tests/

Stdlib-only `unittest` tests for the plugin's scripts + hooks.

## Running

From the plugin directory (the nested plugin root, not the repo root):

```sh
cd /path/to/joharnessburg/plugins/joharnessburg
python3 -m unittest discover tests
```

For verbose output:

```sh
python3 -m unittest discover -v tests
```

## Coverage

Automated tests (run on every commit):

- `tests/scripts/test_init_workspace.py` — init_workspace.py
- `tests/scripts/test_workspace_status.py` — workspace_status.py
- `tests/scripts/test_archive_workspace.py` — archive_workspace.py
- `tests/scripts/test_reduce_events.py` — reduce_events.py
- `tests/scripts/test_apply_template.py` — apply_template.py (template merge + safety guards)
- `tests/scripts/test_reset_john.py` — reset_john.py (applied-dir reset + metadata guard)
- `tests/scripts/test_set_endurance.py` — set_endurance.py
- `tests/scripts/test_parse_govcn_html.py` — parse_govcn_html.py
- `tests/scripts/test_ppx_parse.py` — ppx_parse.py (HTTP client error paths, via a localhost fixture)
- `tests/scripts/test_session_start_hook.py` — SessionStart hook (contract test: asserts the documented `hookSpecificOutput.additionalContext` output shape)
- `tests/scripts/test_precompact_hook.py` — PreCompact hook
- `tests/scripts/test_post_tool_use_hook.py` — PostToolUse hook (contract test: feeds the documented `tool_output_text`/`tool_output`/`tool_response` input fields)
- `tests/scripts/test_apply_sh.py` — templates/apply.sh (bundled-copy byte-identity + registry-key resolution)
- `tests/scripts/test_consistency.py` — cross-artifact guards: every script compiles, hooks.json references existing scripts, CORE_SKILLS names real skill dirs

Manual smoke tests (parsers require external deps + a client server):

- `markitdown_parse.py` — requires `pip install markitdown` (compile-checked by `test_consistency.py`, behavior is manual-smoke). Smoke: run on a DOCX file, verify `doc.md` + `metadata.json` written.
- `ppx_parse.py` — full round-trip requires a ppx client server reachable at `$JOHN_PPX_CLIENT_URL`. Smoke: POST a small PDF, verify the returned file paths exist on disk. (Error paths are covered automatically.)

## Conventions

- Tests use `tempfile.TemporaryDirectory()` for isolation — never write to the real filesystem.
- Each test runs the target script via `subprocess` (see `tests/_helpers.py`) to exercise the actual CLI interface, not the script's internal Python API.
- JSON stdout assertions are preferred over stderr text matching (stdout is the Claude-facing contract; stderr is human-facing and may change wording).
