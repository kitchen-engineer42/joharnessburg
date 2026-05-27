# platform-auth — source team work

Read these in the team's existing repositories when building an auth flow:

- `to-skills-backend/skills/subsite-platform/sso.md` — the team's canonical SSO integration writeup. Read first.
- `to-skills-backend/docs-internal/sso-subsite-auth.md` — the subsite-specific patterns (cookie names, redirect flow, dev-bypass).
- Live subsites with working SSO integrations (good reference implementations):
  - `subsites/mathlab/server.js` — backend Bearer-token verification example
  - `subsites/lesson2slides/sso.py` — Python backend verification example
  - `subsites/create-any-portfolio/` — pure-frontend SSO consumption

The frontend `sso-client.js` is shipped via the team's shared CDN — don't vendor a stale copy. The team's platform team owns the canonical version.

Patterns the team has settled on (don't re-litigate):
- Bearer-token-in-header for backend calls (never URL params).
- 24-hour token TTL; clients re-introspect rather than caching.
- Dev-mode bypass via env var; see the docs above for the exact var name + flow.
