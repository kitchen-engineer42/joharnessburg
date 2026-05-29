---
name: workerllm-runtime
description: When a produced app needs to call workerLLMs at runtime (e.g., a doc-verification check_R<id>.py asking DeepSeek for a judgment call, or a slide-renderer asking Qwen to summarize a chunk), wire it to call John's local LLM client server. Triggers on "call workerLLM", "runtime LLM call", "call DeepSeek", "call SiliconFlow", "produced app needs an LLM", or any pattern where a produced app needs reasoning beyond Claude's main API. Teaches the standalone OpenAI-compatible call shape against `$JOHN_LLM_CLIENT_URL`.
metadata:
  triggers:
    - workerllm
    - runtime llm call
    - call deepseek
    - call siliconflow
    - call qwen
    - produced app llm
    - cheap llm
    - bulk classification
    - check_r llm
---

# workerllm-runtime

When you're authoring a produced app that needs to call an LLM at runtime — NOT the layer-2 Claude session itself, but the *app's own runtime when its end-users use it* — wire it to John's local LLM client server. The client is OpenAI-compatible; same SDK that points at api.openai.com works against `$JOHN_LLM_CLIENT_URL`.

## When to use this (vs alternatives)

- **Use this skill** for standalone produced apps that need workerLLMs at runtime. Examples: a doc-verification rule's `check_R<id>.py` that asks a model for a judgment call; a slide-renderer that asks for a one-sentence summary; a chatbot's main loop.
- **Use [[platform-llm-proxy]]** instead when the produced app is destined to run INSIDE the team's hosted platform (with Bearer tokens, lock/settle/cancel credits, central key backend). That skill teaches the proxy-mediated pattern; this skill teaches the direct-API pattern. **Same OpenAI-compatible API on the wire**, so swapping is just changing `base_url`.
- **Don't use either** for in-Claude-session subagent dispatch. That's [[subagent-dispatch]] — uses the Agent tool, not LLM APIs.

## The call shape

The produced app uses the standard `openai` Python SDK pointed at the local client:

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key="not-used",  # the local client doesn't check; the workspace .env has the real keys
    base_url=os.environ.get("JOHN_LLM_CLIENT_URL", "http://localhost:8500") + "/v1",
)

resp = client.chat.completions.create(
    model="deepseek-v4-flash",  # see "Model selection" below
    messages=[
        {"role": "system", "content": "You verify loan-advertising compliance against Chinese regulation R012."},
        {"role": "user", "content": ad_text},
    ],
    response_format={"type": "json_object"},  # if you want structured output
    temperature=0.1,  # low for verification; raise for creative tasks
    max_tokens=1000,
)
verdict = resp.choices[0].message.content
```

Same shape in JavaScript with the OpenAI SDK; just point `baseURL` at the same env var.

## Model selection

| Task | Recommended | Why |
|---|---|---|
| Cheap bulk classification, simple Q&A | `deepseek-v4-flash` | Cheapest tier; fast |
| Judgment-heavy reasoning (rule verification with subtle cases) | `deepseek-v4-pro` | Strong reasoning at modest cost |
| Long-context synthesis, complex multi-step | `Qwen/Qwen3.5-397B-A17B` | MoE — large parameter count, reasonable cost |
| Vision / OCR / image understanding | `PaddlePaddle/PaddleOCR-VL-1.5` | Trained for layout + text extraction |

When a rule-skill / app needs a workerLLM call, pick the cheapest tier that's good enough. Default to `deepseek-v4-flash` for high-volume judgment calls; escalate to `-pro` only when the cheap tier produces wrong verdicts on labeled samples.

## Error patterns

- **Connection refused / timeout** at `$JOHN_LLM_CLIENT_URL`: the local server isn't running. Tell the user that their LLM client server isn't reachable at `$JOHN_LLM_CLIENT_URL` — they need to start it (or point `$JOHN_LLM_CLIENT_URL` at a running one) in a separate terminal.
- **503 from the server** with `"Provider '<name>' is not configured"`: the workspace `.env` is missing the API key for the routed provider. Tell the user which env var to set.
- **Upstream provider error (502)**: provider returned an error. Surface its message; usually a model-name typo or out-of-credit.
- **501 with "streaming not implemented"**: pass `stream=false` (default). Streaming isn't supported by this client.

## When NOT to use this skill

- For Claude's own reasoning in the layer-2 session, just use Claude's native tools (Read, Edit, Skill, etc.). The workerLLM client is for the *produced app's runtime*, not Claude's authoring time.
- For prompts that need Anthropic-specific features (extended thinking, computer use, etc.), call Anthropic's API directly from the produced app with its own API key (out of this skill's scope; the local client doesn't proxy Anthropic).
- For one-shot prompts where the latency of a local-server roundtrip matters more than the abstraction (rare).

## References

- `references/call-shape.md` — concrete snippets for the common patterns (one-shot reasoning, batch classification, vision, structured JSON output).
- `references/migration-from-platform-llm-proxy.md` — how a produced app upgrades from this skill's pattern to platform-llm-proxy's pattern when it gets deployed to the team's platform.

## Cross-references

- [[platform-llm-proxy]] — production proxy pattern (same OpenAI-compat API; different deployment).
- [[platform-model-config]] — T1-T4 tier policy + canonical env var names.
- [[subagent-dispatch]] — for layer-2 Claude session work, not produced-app runtime.
