# platform-credits — source team work

Read these in the team's existing repositories when wiring credit accounting:

- `to-skills-backend/skills/subsite-platform/credits.md` — the canonical lock/settle/cancel writeup.
- `to-skills-backend/docs-internal/custom-app-platform-integration.md` — broader integration doc (247 lines); the credits section is the load-bearing part for this skill.
- Live subsite implementations with credits wired:
  - `subsites/mathlab/server.js` — locks before each LLM call, settles on success, cancels on truncation/timeout.
  - `subsites/voteforyourapp/` — voting also costs credits; lighter touch (one charge per vote).

Patterns the team has settled (don't re-litigate):
- Idempotency keys are UUIDv4 per attempt.
- Lock TTL is platform-side; if your produced app crashes between lock and settle, the lock auto-expires and credits return to the user — but that's a fallback, not the primary path.
- `source_app_id` is hardcoded in app config; never inferred from the request.
- Recovery prompts on truncation/timeout retry the LLM call but reuse the original lock_id (a single lock can cover multiple LLM retries; only the final settle/cancel charges).
