---
name: platform-model-config
description: When choosing which LLM model to call from a produced app, or wiring model-key acquisition, use this skill. Triggers on "which model", "model tier", "T1/T2/T3", "model config", "LLM_MODEL_CHAT", "model env vars", "key backend". Teaches the team's tier policy + standard env var names. Does NOT manage API keys (the platform's key backend does that).
metadata:
  triggers:
    - which model
    - model tier
    - t1
    - t2
    - t3
    - t4
    - model config
    - llm_model_chat
    - llm_model_vision
    - llm_model_image_gen
    - model selection
    - api keys
---

# platform-model-config

The team segments LLMs into tiers by capability + cost. Match the tier to the operation; don't default to the top tier "because it's better."

## The tiers

- **T1 — SOTA** (Claude Opus 4.x, GPT-5, Gemini Ultra). For: complex multi-step reasoning, schema design, hard rule extraction, long-context synthesis. Expensive. Reserve for operations where wrong-answer cost is high.
- **T2 — Capable** (Claude Sonnet 4.x, GPT-5 mini, Gemini Pro). For: most LLM work in produced apps — generation, summarization, structured extraction with clear schemas. Default tier.
- **T3 — Cheap+Fast** (DeepSeek Chat, GPT-5 nano). For: high-volume tasks where T2 is overkill — classifying short text, simple Q&A on known content, format conversions. WorkerLLM territory.
- **T4 — Local** (Qwen 7B, smaller). For: cost-floor operations where even T3 is too expensive — bulk pre-filtering, simple keyword extraction. Run on local hardware via the team's local-llm bridge.

## Standard env vars

The team uses these env var names consistently across produced apps:

- `LLM_MODEL_CHAT` — the model used for general chat-completion calls.
- `LLM_MODEL_VISION` — the model used for image/document understanding.
- `LLM_MODEL_IMAGE_GEN` — the model used for image generation (DALL-E / Imagen).
- `LLM_PROXY_BASE_URL` — the URL of the platform's LLM proxy (see [[platform-llm-proxy]]).

Set these in `.env.example` with comments explaining the tier choice. Production values come from the platform's secret store; don't hardcode.

## What to do in this project

1. **At design time** (during `app-design-thinking`), list every LLM operation in the produced app + assign a tier. Operations that don't justify T1 should pick T2; operations where T3 suffices should pick T3.
2. **At code time**, read model names from env vars, never hardcode. Future tier swaps shouldn't require code changes.
3. **At deploy time**, the platform's key backend (`skills2app/utils/llm_key_backends/`) provisions API keys per app. Your container doesn't manage keys directly — the proxy does.
4. **For workerLLM-style fan-out** (per spec §8.3): templates pick T3/T4 explicitly. Don't apply John core's default tier to workerLLM tasks.

## What you should NOT do

- Don't default to T1 for everything. Costs add up; users notice the bill.
- Don't hardcode model names in source. Env vars only.
- Don't manage API keys in the produced app. The platform owns them.
- Don't bypass the proxy "to save a round trip". Proxy + tier policy is how the platform tracks cost; bypassing it breaks billing.

See `references/source.md` for source paths.
