# Migration: workerllm-runtime → platform-llm-proxy

When a produced app moves from local/standalone to the team's hosted platform, the LLM-call code changes very little. The HTTP contract is OpenAI-compatible on both sides.

## What stays the same

- The `openai` SDK import + usage.
- The chat-completions API shape (messages, temperature, max_tokens, etc.).
- Model names (the production proxy advertises the same model IDs we use locally).
- Error semantics for most cases (connection errors, upstream errors, etc.).

## What changes

1. **`base_url`** — points at the production proxy URL instead of `localhost:8500`. Read from `JOHN_LLM_CLIENT_URL` if the produced app is John-aware, or from `LLM_PROXY_BASE_URL` if it follows [[platform-model-config]]'s tier conventions.

2. **Auth** — the production proxy uses Bearer tokens (per [[platform-auth]]). Pass the user's token instead of a dummy key:
   ```python
   client = OpenAI(
       api_key=user_bearer_token,  # from request.headers["Authorization"]
       base_url=os.environ["LLM_PROXY_BASE_URL"],
   )
   ```

3. **Credit lifecycle** — the production proxy expects calls to be wrapped in lock/settle/cancel per [[platform-credits]]. Add:
   ```python
   lock = lock_credits(user_id, estimated_cost, idempotency_key())
   try:
       resp = client.chat.completions.create(...)
       settle_credits(lock.id, resp.usage.total_tokens, idempotency_key())
   except Exception:
       cancel_credits(lock.id, "...", idempotency_key())
       raise
   ```
   The lock/settle/cancel endpoints are part of the platform, separate from the LLM proxy.

4. **Telemetry** — emit `llm_call` events per [[platform-telemetry]]. The local workerllm-runtime skill doesn't require this; production does.

5. **Recovery on truncation** — the production proxy may surface truncation differently. See [[platform-llm-proxy]] for the recovery prompt pattern.

## The migration path

For a produced app that needs to work both standalone and in-platform:

1. Make the LLM-call code accept a config object with `{base_url, api_key, with_credits: bool, with_telemetry: bool}`.
2. Set `with_credits=False, with_telemetry=False` when running locally; `=True` when in platform.
3. The same `client.chat.completions.create(...)` call works in both modes.

For an app that starts in-platform-only, just follow [[platform-llm-proxy]] from day one. The local-client workflow is for development + apps that target external customers.
