---
name: spec-template-manager
description: For platform-integrated projects, use this skill when the question of "how is the produced app's spec persisted/versioned/managed?" comes up — typically during the 2skills→2app handoff or when discussing how the team's existing spec-template system relates to John's PLAN.md. Triggers on "spec template", "spec.md", "/api/spec-templates", "version a spec", "roll back spec", "admin spec API". Teaches the team's existing spec-template system AND how John's PLAN.md replaces the old spec.md handoff pattern (per spec §8.8).
metadata:
  triggers:
    - spec template
    - spec.md handoff
    - spec-templates api
    - version a spec
    - roll back spec
    - admin spec
    - how is the spec stored
---

# spec-template-manager

The team's existing `to-skills-backend` has an admin API at `/api/spec-templates` for managing spec templates: upload, version, roll back. This was the pre-John pattern — `to-skills-backend` produced a `spec.md` that `skills2app` consumed.

John replaces this handoff with a different pattern: **PLAN.md is the durable contract across the 2skills + 2app halves**, and it lives in the user's project, not in a central admin API. But the existing spec-template system still serves real purposes; this skill teaches both shapes.

## What the existing system does (and still does)

- `/api/spec-templates` — admin endpoints to upload a new spec template, version it, roll back, list. Used by the platform team for the original "3 hardcoded scenarios" pain point: adding a new scenario used to require code deploy; the API made it admin-configurable.
- Templates registered here drive the legacy `to-skills-backend → skills2app` pipeline. If the team is still running production projects through that pipeline (and they are, per CLAUDE.md), this API is still load-bearing.

## How John's PLAN.md relates

John's session-long PLAN.md is **not** the same as a `spec-template`. Differences:

- **Lifecycle**: PLAN.md is per-project, evolves continuously, never "uploaded" anywhere. Spec-templates are reusable across many projects (one template, many runs).
- **Granularity**: PLAN.md is the full project (intent + four-structures + phases + open decisions). Spec-templates are domain skeletons (e.g., "the verification scenario shape").
- **Authority**: PLAN.md is owned by the user + the session. Spec-templates are owned by the platform admins.

**Mapping**: John templates (`templates/examples/<name>/`) play roughly the role spec-templates played pre-John — they're the reusable domain scaffolds. The `/api/spec-templates` API would naturally extend to manage John templates too (upload, version, roll back) if the team chooses to host them centrally.

## What to do in this project

1. **If the project is greenfield John work**: stay PLAN.md-native. Don't try to retrofit the spec-template API into the John flow; PLAN.md is the durable contract.
2. **If the project bridges John and the legacy pipeline** (e.g., John builds knowledge, but `skills2app` builds the final app via a legacy spec-template): write the spec-template-style output as an explicit artifact of the 2skills→2app boundary. Document the bridge in PLAN.md's Log so it's visible.
3. **If extending the existing spec-template API** for John template hosting: coordinate with the platform team. The API extension is platform-team territory, not in-project work.

## What you should NOT do

- Don't bypass PLAN.md by writing a separate `spec.md`. That's the pre-John pattern John explicitly replaces (spec §8.8 Yibo's reply locked this in).
- Don't manage spec-template versions inside a produced app's runtime — that's admin tooling, not app code.
- Don't conflate "John template" with "spec template" in conversation with the user. They're related but distinct.

See `references/source.md` for source paths.
