# platform-deploy — source team work

Source locations:

- `skills2app/utils/docker_ops.py` — the team's canonical container build + Traefik registration flow. Reuse for produced apps.
- Live subsite examples with working deploy configs (study these for label syntax):
  - `subsites/mathlab/Dockerfile` + `docker-compose.yml`
  - `subsites/lesson2slides/Dockerfile`
  - `subsites/create-any-portfolio/Dockerfile`

The platform's Traefik setup is managed by the platform team. Don't modify Traefik config directly; just emit the right labels and Traefik picks them up.

Pattern conventions:
- App slug = `<uuid>` (UUIDv4, generated at deploy time, stable across redeploys for the same app).
- Domain suffix `${APP_DOMAIN_SUFFIX}` is env-injected (`.app.team-domain.com` or similar).
- Each app's container has access to the platform's internal services (credits API, telemetry endpoint, SSO introspection) via Docker network DNS — no external networking config needed.
- Rolling deploys: the platform handles zero-downtime container swaps when redeploying. Your `/health` endpoint just needs to start returning 200 before the swap.

For dev iteration: `docker compose up` locally produces the same shape as platform deploy. The Traefik labels are ignored locally; routing happens via published ports.
