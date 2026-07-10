# parser-backend-swapping — the URL is the contract

The John-equipped build agent doesn't need to think about this often, but it's worth knowing the boundary exists.

## Today (local default)

`ppx_parse.py` is a thin HTTP client that POSTs to a local **ppx-client server** (FastAPI). The server wraps `memect-ppx` (the `ppx` parser engine) and runs at `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`).

The server lives outside the plugin (workspace tooling, not shipped with John) and is reached via `$JOHN_PPX_CLIENT_URL` — your local ppx client server. Launch it with the client's `scripts/start.sh`. Engine install: `uv pip install -e /path/to/ppx` (see `github.com/kitchen-engineer42/ppx`).

> *Terminology note*: `ppx` is the parser engine; `jyppx` is a separate builder project (at `github.com/memect/jyppx`) that uses ppx as a library to produce tailored parsers per corpus. John's `ppx_parse.py` talks to ppx (via the local client), not to jyppx.

## Swapping the backend

Any hosted parse service that speaks the same HTTP contract can replace the local server — point `$JOHN_PPX_CLIENT_URL` at it and restart the coding runtime. Same script name, same CLI surface, same JSON output shape, different backend. No code change in John.

## Implications for the John-equipped agent

**None, mostly.** The script's CLI signature and JSON output shape are the contract; the internals are not. Don't write extraction logic that depends on:

- Specific timing (`elapsed_seconds`). A hosted backend may return faster (cache hit) or slower (queue depth) than local.
- Local file paths in the `metadata.json` (a hosted backend may use object-storage paths).
- Specific backend names beyond `default` (a hosted deployment may have its own backend roster).

If you find yourself caring about these, you're probably over-fitting to local-dev behavior.
