# spec-template-manager — source team work

Source locations:

- `production/to-skills-backend/skills/spec-template-manager/SKILL.md` — the canonical existing skill from the legacy pipeline. Read for: the admin API endpoint shapes, the versioning semantics, the rollback flow.
- `production/to-skills-backend/` (broader) — the API implementation lives here. Endpoints under `/api/spec-templates`.

Context for John:
- Spec §8.8 (Yibo reply): "no spec.md handoff; PLAN.md is the durable contract that spans 2skills → 2app in one session." This is the architectural decision that makes John's flow different from the legacy pipeline.
- Spec §8.14 table row: this skill teaches Claude about the existing system so it knows what's there + how John's PLAN.md replaces the handoff aspect (not the template-management aspect).

The legacy pipeline and John coexist for now:
- Legacy: customer requests → admin picks a spec template → `to-skills-backend` produces `spec.md` → `skills2app` produces the app. Two separate services, with `spec.md` as the handoff.
- John: single session reads input → PLAN.md drives the knowledge-engineering half → same PLAN.md drives the app-building half. One process, no handoff file.

Both can run on the same platform. Choosing between them is project-dependent: legacy is battle-tested for the known scenarios; John is being shaken down through M6 for the broader cases.
