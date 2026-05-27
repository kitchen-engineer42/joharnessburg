# subsite-builder — source team work

The canonical source is the team's existing skill at `to-skills-backend/skills/subsite-builder/SKILL.md` (with `references/{engineering,llm,config,security}.md`). Read it before designing the produced app's structure — it's the deepest authority on the team's preferred patterns.

Five reference subsites (each a different shape; pick the closest to your project):

- `subsites/mathlab/` — backend-heavy (server.js does the heavy reasoning + LLM coordination). Frontend is a thin client. Good reference for: math/logic apps, multi-turn reasoning, T1 LLM use.
- `subsites/lesson2slides/` — backend-heavy (Python). Document-in → structured-out (slides). Good reference for: knowledge-engineering output, document parsing, mixed T2/T3 LLM use.
- `subsites/create-any-portfolio/` — frontend-only. Pure client-side, no backend, no priced ops. Good reference for: lightweight tools, no-LLM apps, fast iteration.
- `subsites/voteforyourapp/` — small backend with simple priced operation (vote = 1 credit). Good reference for: minimal-credit-wiring example.
- `subsites/mystery-detective-game/` — game-style; multi-step state + LLM-driven dialogue. Good reference for: longer-session apps with persistent state.

Don't copy any of them wholesale — each was hand-built. Use them to understand structure + the platform integration patterns. Templates ([[plan-md-authoring]]'s template system) are the right level for reusable scaffolds; subsites are the inspiration source.

The four `references/` files in the team's existing subsite-builder skill:
- `engineering.md` — project structure, build, deploy
- `llm.md` — prompting conventions for produced-app LLM use
- `config.md` — env vars, secrets
- `security.md` — XSS, CSRF, internal-token-leakage checklist
