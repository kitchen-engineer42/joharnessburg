---
name: platform-deploy
description: When the produced app is ready to ship to the team's hosted platform, use this skill. Triggers on "deploy", "ship", "release", "Docker", "Traefik", "container", "go live", or anywhere the user asks "how do I get this on the website?". Teaches the team's container-per-app pattern (Docker + Traefik labels → automatic {uuid}.{APP_DOMAIN_SUFFIX} URL). Does NOT do the actual deploy — calls into skills2app's existing docker_ops machinery.
metadata:
  triggers:
    - deploy
    - ship
    - release
    - docker
    - traefik
    - container
    - go live
    - publish app
---

# platform-deploy

The team's hosted platform runs each produced app as its own Docker container. Traefik watches container labels and exposes them at standard URLs. No manual Nginx config, no shared multi-tenant runtime. Follow the pattern; don't invent.

## The shape of a deployable app

A produced app is deployable when it has:

1. **A working `Dockerfile`** in the app output directory. Multi-stage where appropriate; final image small.
2. **Traefik labels** in the docker-compose or deploy manifest:
   - `traefik.enable=true`
   - `traefik.http.routers.<app-id>.rule=Host(\`<uuid>.${APP_DOMAIN_SUFFIX}\`)`
   - `traefik.http.routers.<app-id>.tls=true`
   - `traefik.http.services.<app-id>.loadbalancer.server.port=<port>`
3. **Env-var declarations** in `.env.example` — every env var the app needs, with a comment. Platform deploy reads `.env` from the platform secrets store.
4. **A health-check endpoint** at `/health` returning 200 when the app is ready. Traefik uses this to gate traffic.

## What to do in this project

1. **Build the Dockerfile early** — at the start of the deploy phase, not as an afterthought. Test locally with `docker compose up` before pushing.
2. **Use `skills2app/utils/docker_ops.py`** for the actual build + register + expose flow. Don't reimplement.
3. **Pick a non-conflicting port.** Most produced apps use 3000 (frontend) or 8000 (backend); the platform routes external traffic via Traefik on 443 → your container port.
4. **Wire the `/health` endpoint.** Even a trivial `200 OK` is enough; Traefik just needs to know the container is up.
5. **Set `app_id`** in the produced app's config — it's the slug Traefik uses + the `source_app_id` for credits + telemetry.

## What you should NOT do

- Don't deploy via manual `scp` or `rsync`. The platform's deploy flow is the only sanctioned path.
- Don't write Nginx config. Traefik handles routing automatically from labels.
- Don't share a container across apps. Each app gets its own container — isolation is a feature.
- Don't hardcode secrets in the image. Secrets come from the platform's secret store via env vars at runtime.

See `references/source.md` for source paths.
