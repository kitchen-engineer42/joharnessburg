# platform-llm-proxy — source team work

Reference implementations in the team's subsites:

- `subsites/mathlab/server.js` — JavaScript reference. Lock → rate-limit-check → LLM call → settle/cancel → telemetry. Battle-tested across GPT-4/Claude/Gemini.
- `subsites/lesson2slides/sso.py` — Python reference. The auth path also has the LLM-call wrapper.
- `skills2app`'s Claude backend — the recovery prompts on truncation, timeout, and tool-mismatch live here. Reusable if your produced app's LLM provider has similar failure modes.

Patterns the team has settled:
- Generous upstream timeouts (180s for reasoning models, 60s for chat).
- Recovery prompts use the format "Please continue from where you left off" for truncation, "The tool call result didn't match — please retry with corrected JSON" for tool mismatches.
- Per-user + per-app rate limit (not per-IP — users may share IPs in dev/test).
- One credit lock covers multiple LLM retries during recovery; only the final settle counts cost.

For provider routing: the platform proxies actual provider calls (Anthropic / OpenAI / DeepSeek / Qwen). Generated apps don't manage provider keys directly — see [[platform-model-config]].
