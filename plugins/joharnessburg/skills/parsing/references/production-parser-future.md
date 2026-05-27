# production-parser-future — what changes when John goes to production

Layer-2 Claude doesn't need to think about this often, but it's worth knowing it exists.

## Today (v0.1.7+, local dev)

`ppx_parse.py` is a thin HTTP client that POSTs to a local **ppx-client server** (FastAPI). The server wraps `memect-ppx` (the `ppx` parser engine) and runs at `$JOHN_PPX_CLIENT_URL` (default `http://localhost:8501`).

The server lives outside the plugin at `/Users/mac/Desktop/john/local_clients/ppx/` (workspace tooling, not shipped with John). Install + launch with `local_clients/ppx/scripts/start.sh`. Engine install: `uv pip install -e /path/to/ppx` (see `github.com/kitchen-engineer42/ppx`).

> *Terminology note*: `ppx` is the parser engine; `jyppx` is a separate builder project (at `github.com/memect/jyppx`) that uses ppx as a library to produce tailored parsers per corpus. John's `ppx_parse.py` talks to ppx (via the local client), not to jyppx.

## Tomorrow (production migration)

Per spec §8.7, the tech team will swap the URL `JOHN_PPX_CLIENT_URL` to point at an internal `PDF_PARSE_SERVER` — a hosted service with proper queuing, retries, and cache. Same script name, same CLI surface, same HTTP contract, different backend. The local-client server already mimics the production server's HTTP shape, so the swap is just an env-var change.

## Implications for layer-2 Claude

**None, mostly.** The script's CLI signature and JSON output shape are the contract; the internals are not. Don't write extraction logic that depends on:

- Specific timing (`elapsed_seconds`). Production may return faster (cache hit) or slower (queue depth) than local.
- Local file paths in the `metadata.json` (production may use object-storage paths).
- Specific backend names beyond `default` (production may have its own backend roster).

If you find yourself caring about these, you're probably over-fitting to local-dev behavior.

## Source

- Spec §8.7 user reply: *"in-process ppx for now. Company has server designated to run ppx by large batch, tech team will re-router to the server when John goes production in the future."*
- `to-skills-backend/app/pipeline/stages/doc_converter.py` (in the dev workspace) is roughly the shape the future RPC client will take.
