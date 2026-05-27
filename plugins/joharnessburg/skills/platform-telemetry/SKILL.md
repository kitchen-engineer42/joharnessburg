---
name: platform-telemetry
description: When the produced app needs to emit observability events for the team's analytics + monitoring (session starts, LLM calls, fallbacks, completed actions, errors), use this skill. Triggers on "logging", "tracing", "analytics", "instrument", "track event", "app insight", or any feature where the operations team needs visibility. Teaches the standard event taxonomy + SDK init; uses the team's `app-insight.js` library.
metadata:
  triggers:
    - logging
    - tracing
    - analytics
    - telemetry
    - track event
    - app insight
    - instrument
    - monitoring
---

# platform-telemetry

Produced apps emit structured events via the team's `app-insight.js` SDK. Use the standard event taxonomy so the analytics + operations dashboards stay coherent across all the apps John ships.

## The standard event taxonomy

Every produced app should emit at least these events:

- `session_start` — `{user_id, app_id, session_id}`. Emitted on first user interaction.
- `llm_call` — `{user_id, model, prompt_tokens, completion_tokens, cost_credits, latency_ms, success}`. Emitted per LLM call (post-recovery; one event per logical call).
- `llm_fallback` — `{user_id, primary_model, fallback_model, reason}`. Emitted when [[platform-llm-proxy]] falls back to a cheaper tier.
- `action_completed` — `{user_id, action_name, duration_ms, outcome}`. App-specific action names; pick a short closed vocabulary at design time.
- `error` — `{user_id, error_type, error_message, stack_trace_hash}`. Emit on every uncaught error; the stack trace itself goes to a separate log channel (PII-scrubbing happens upstream).

Domain-specific events are fine on top of these (e.g., `slide_rendered` for slides apps, `rule_checked` for verification apps), but the five above are the lingua franca.

## What to do in this project

1. **At app init**: call `appInsight.init({app_id, user_id})`. The SDK reads env config (telemetry endpoint, sample rate) automatically.
2. **Per LLM call**: emit `llm_call` AFTER the call settles (so cost is accurate). The [[platform-llm-proxy]] wrapper should do this for you if you're using it.
3. **Per major user action**: emit `action_completed` with a meaningful `action_name`. Document the vocabulary in the produced app's README.
4. **Errors**: emit `error` with the type (string enum) + message (no PII). Stack traces flow through a separate channel.

## What you should NOT do

- Don't emit events synchronously in the request path. `appInsight.emit` is fire-and-forget; back-pressure handled inside the SDK.
- Don't put PII in event payloads. `user_id` is fine (it's an opaque ID); names, emails, prompt content are not.
- Don't invent new event names without coordinating with the analytics team. Decide your domain vocabulary at design time; add to it deliberately.
- Don't roll your own telemetry library. Use `app-insight.js` so the dashboards work.

See `references/source.md` for the SDK source location + example wirings.
