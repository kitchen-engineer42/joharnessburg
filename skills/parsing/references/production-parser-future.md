# production-parser-future — what changes when John goes to production

Layer-2 Claude doesn't need to think about this often, but it's worth knowing it exists.

## Today (v0.1.x, local dev)

`ppx_parse.py` runs jyppx in-process. The Python interpreter that runs the script imports `memect.pdf.parser` and parses the PDF locally. Works fine on a developer laptop with `pip install -e /path/to/jyppx/ppx`.

## Tomorrow (production migration)

Per spec §8.7, the tech team will replace `ppx_parse.py`'s implementation with an RPC client to the internal `PDF_PARSE_SERVER` — a hosted service that runs ppx (or a successor) at scale, with proper queuing, retries, and cache. Same script name, same CLI surface, different backend.

## Implications for layer-2 Claude

**None, mostly.** The script's CLI signature and JSON output shape are the contract; the internals are not. Don't write extraction logic that depends on:

- Specific timing (`elapsed_seconds`). Production may return faster (cache hit) or slower (queue depth) than local.
- Local file paths in the `metadata.json` (production may use object-storage paths).
- Specific backend names beyond `default` (production may have its own backend roster).

If you find yourself caring about these, you're probably over-fitting to local-dev behavior.

## Source

- Spec §8.7 user reply: *"in-process ppx for now. Company has server designated to run ppx by large batch, tech team will re-router to the server when John goes production in the future."*
- `to-skills-backend/app/pipeline/stages/doc_converter.py` (in the dev workspace) is roughly the shape the future RPC client will take.
