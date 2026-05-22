---
name: subsite-builder
description: When designing the produced app's overall structure for a platform-integrated project (auth + credits + telemetry wired, deployed via the team's container pipeline), use this skill as orientation. Triggers on "build a subsite", "build a custom app for the website", "produced app structure", "what does the produced app look like?", or whenever a project is heading toward the team's standard app shape. Higher-level overview that points at the focused platform-* skills.
metadata:
  triggers:
    - subsite
    - custom app
    - produced app structure
    - build for the website
    - subsite structure
    - high level app shape
---

# subsite-builder

The team has converged on a standard shape for custom apps that ship on the website. This skill is the orientation pass — it sketches the whole shape so you can see how the focused platform-* skills relate.

## The standard subsite shape

A produced app in the team's platform context is, structurally:

```
<app-output>/
├── frontend/                 # static or SPA (React, Vue, plain HTML)
│   └── (sso-client.js included)
├── backend/                  # optional; needed for priced ops or persistence
│   ├── server.js / app.py
│   ├── routes/
│   └── (Bearer-token verify, credit lock/settle, telemetry emit)
├── Dockerfile
├── docker-compose.yml        # with Traefik labels
├── .env.example              # documenting all env vars
├── README.md                 # quick start + deploy instructions
└── (assets, config, tests)
```

The frontend is always present. The backend exists only if the app does priced operations, needs user-specific persistence, or has any logic that shouldn't live client-side.

## What to do in this project

1. **Decide frontend-only vs frontend+backend** at design time (during `app-design-thinking`). Backend is necessary for: any LLM call (must go through proxy), credit-priced operations, user-saved state, anything PII-sensitive.
2. **Wire each platform concern** by consulting the focused skill:
   - Auth → [[platform-auth]]
   - Priced operations → [[platform-credits]]
   - LLM calls → [[platform-llm-proxy]]
   - Observability → [[platform-telemetry]]
   - Document parsing → [[platform-parser]]
   - Deploy → [[platform-deploy]]
   - Model choice + env config → [[platform-model-config]]
3. **Start from a reference subsite** (mathlab, lesson2slides, create-any-portfolio, voteforyourapp, mystery-detective-game). They're not templates in the John sense, but they're working starting points for app structure.
4. **Wire SSO + telemetry first.** Without them, the app is invisible to the platform; ops can't help if it breaks.
5. **Add credits last** — only after the priced operation works without auth/telemetry-related noise.

## What you should NOT do

- Don't deviate from the standard structure without a reason. Future maintenance + ops support assume the shape.
- Don't reinvent any of the platform-* skills' patterns inline; consult the skill, follow the pattern.
- Don't build a one-off auth or telemetry path "for this app only". The shared infrastructure is the value.
- Don't ship without `.env.example` and `README.md`. Ops needs both at deploy time.

See `references/source.md` for source paths + reference subsite locations.
