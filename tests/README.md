# tests/

Stdlib-only `unittest` tests for the M2 toolkit scripts.

## Running

From the plugin root:

```sh
cd /path/to/joharnessburg
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
- `tests/scripts/test_set_template.py` — set_template.py

Manual smoke tests (parsers require external deps):

- `markitdown_parse.py` — requires `pip install markitdown`. Smoke: run on a DOCX file, verify `doc.md` + `metadata.json` written.
- `ppx_parse.py` — requires `pip install -e /path/to/jyppx/ppx`. Smoke: run on a small PDF, verify `doc.md` + `doc.json` + `pages/` written.

## Conventions

- Tests use `tempfile.TemporaryDirectory()` for isolation — never write to the real filesystem.
- Each test runs the target script via `subprocess` (see `tests/_helpers.py`) to exercise the actual CLI interface, not the script's internal Python API.
- JSON stdout assertions are preferred over stderr text matching (stdout is the Claude-facing contract; stderr is human-facing and may change wording).
