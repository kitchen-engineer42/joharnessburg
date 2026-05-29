---
name: platform-llm-proxy
description: When the produced app makes LLM calls in production, use this skill. Triggers on "LLM call", "call Claude", "call GPT", "call DeepSeek", "model API", "rate limit", "timeout", or any feature that talks to a model at runtime. Teaches the team's wrap-LLM-calls-in-credits-plus-rate-limit pattern with recovery on truncation. Does NOT ship a proxy backend; teams use the platform's existing one.
metadata:
  triggers:
    - llm call
    - call claude
    - call gpt
    - call deepseek
    - model api
    - llm proxy
    - rate limit
    - llm recovery
    - llm timeout
---

# platform-llm-proxy

Every LLM call in a produced app — for chat, vision, image-gen, embedding — flows through the same pattern: rate-limit-check → credit-lock → LLM call → settle/cancel → telemetry. This skill teaches the shape; existing subsites have battle-tested it.

**Local-dev counterpart**: for produced apps that run STANDALONE (not inside the team's platform), see [[workerllm-runtime]] — same OpenAI-compatible call shape but without lock/settle/cancel + Bearer-token plumbing. A local LLM client (reachable via `$JOHN_LLM_CLIENT_URL`) is the dev-time substitute for the production proxy; both expose `/v1/chat/completions`. Migrating a standalone app to the platform = add credits + auth wrappers, keep the SDK call.

## The standard call shape

```
async function llmCall(userId, prompt, opts) {
  // 1. rate-limit check (per-user, per-app)
  await checkRateLimit(userId, opts.model);

  // 2. credit lock — see platform-credits for full lifecycle
  const lock = await lockCredits(userId, opts.estimatedCost, idempotencyKey());

  try {
    // 3. the actual LLM call
    const result = await callProvider(opts.model, prompt, opts);

    // 4. recovery on truncation / unexpected tool mismatch
    if (truncated(result)) {
      const continued = await recoverTruncation(result, prompt, opts);
      result.text += continued.text;
      result.cost += continued.cost;
    }

    // 5. settle the actual cost
    await settleCredits(lock.id, result.cost, idempotencyKey());

    // 6. telemetry — see platform-telemetry
    emitLlmCallEvent({userId, model: opts.model, cost: result.cost, ...});

    return result;
  } catch (err) {
    await cancelCredits(lock.id, err.message, idempotencyKey());
    throw err;
  }
}
```

## What to do in this project

1. **Don't call providers directly.** All LLM calls go through this wrapper (or its server-side equivalent).
2. **Pick the right tier.** The team's `platform-model-config` skill defines tiers (T1 SOTA / T2 Sonnet / T3 DeepSeek / T4 Qwen). Choose by cost-vs-quality tradeoff for the specific operation; don't default to T1 if T3 suffices.
3. **Generous upstream timeout.** Mathlab raised theirs from 60s to 180s after a reasoning model needed it. Set per-operation, not globally.
4. **Implement recovery on truncation.** A truncated response isn't a failed call; continue the conversation with "please continue from where you left off." Counts as one logical call for credits.
5. **Wire telemetry.** Every LLM call emits a `llm_call` event with `{model, cost, latency_ms, success}`. See [[platform-telemetry]].

## What you should NOT do

- Don't bypass the proxy "just for testing". Test against a mock provider that mimics the proxy contract.
- Don't retry on transient errors without backoff. The team has hardened backoff parameters; reuse them.
- Don't truncate responses silently on your end. If the provider truncated, surface it and recover; if the user's quota truncated, surface it with a clear UX message.

See `references/source.md` for source paths.
