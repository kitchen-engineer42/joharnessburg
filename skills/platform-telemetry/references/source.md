# platform-telemetry — source team work

Reference implementations in the team's subsites:

- `subsites/mathlab/` — has `app-insight.js` wired with the standard event taxonomy. Reference implementation for the SDK init + per-LLM-call emission.
- `subsites/lesson2slides/` — similar wiring with `slide_rendered` domain-specific event.
- `subsites/create-any-portfolio/` — pure frontend; emits `session_start` + `action_completed` only.

The `app-insight.js` SDK source lives in the team's shared infrastructure — ask the platform team for the canonical version. Don't vendor a stale copy.

The team's analytics dashboard consumes:
- Standard events (session_start, llm_call, llm_fallback, action_completed, error) directly.
- Domain-specific events on demand — coordinate with the analytics team before adding new ones to the produced app.

PII handling: the SDK does NOT do PII scrubbing client-side. Don't put user names, emails, or prompt content in event payloads. `user_id` is an opaque platform ID and is safe.

Sample rates: configured via env var. Default is 100% for low-volume apps, lower for high-volume.
