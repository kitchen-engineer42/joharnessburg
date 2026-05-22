---
name: platform-auth
description: When the produced app needs to authenticate users via the team's SSO system, use this skill. Triggers whenever the user mentions "auth", "login", "SSO", "session", "permissions", "Bearer token", "who's logged in", or designs any feature that depends on user identity. Teaches the standard team pattern (sso-client.js + Bearer token verify); does NOT ship the auth backend (the platform already runs it).
metadata:
  triggers:
    - sso
    - auth
    - login
    - bearer token
    - session
    - user identity
    - permissions
    - who is logged in
---

# platform-auth

The team's existing subsites authenticate users via a shared SSO. When you produce an app for the website, follow that same pattern — don't roll your own login flow.

## The pattern in two lines

- **Frontend**: include `sso-client.js` (the team's existing client). It manages session cookies, redirects unauthenticated users to the platform's login, and exposes the current user to the produced app via a documented JS API.
- **Backend** (if the produced app has one): every endpoint that needs user identity verifies the incoming Bearer token against the platform's introspection endpoint. The user object hangs off the verified token.

## What to do in this project

1. **Decide if auth applies.** Single-user local apps (a Markdown-to-HTML converter that runs in the browser) don't need auth. Multi-user apps consuming platform features (credits, history, saved-state, leaderboards) do.
2. **For frontends**: include `sso-client.js` from the team's CDN or vendor folder. Wire the `onUserChange` callback. Gate any UI that requires identity behind `user != null`.
3. **For backends**: verify Bearer tokens at the request-handler boundary. Never decode tokens client-side and trust them server-side; always introspect.
4. **For local dev**: the team's SSO has a dev-mode bypass — see `subsite-platform/sso.md` for how to set it up so you can iterate without a live login flow.

## What you should NOT do

- Don't implement password storage, MFA, or session management yourself. The platform owns this.
- Don't fork `sso-client.js` to "fix something". File a request with the platform team; the client is shared infrastructure.
- Don't pass user IDs in URL params for authentication. URLs leak (logs, browser history). Always use Bearer tokens in headers.

## When the platform isn't available

If the produced app is meant to ship standalone (external customers, no platform integration), set the template flag `platform_integrated: false` and skip this skill entirely. Use a different auth strategy (Clerk, Auth0, custom) — but that's a different skill, out of scope for John core.

See `references/source.md` for paths into the team's existing implementations.
