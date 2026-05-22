# platform-model-config — source team work

Source locations:

- `production/skills2app/utils/llm_key_backends/` — the team's key-acquisition + env-injection machinery. Reuse for produced apps.
- Live subsite examples that demonstrate tier choice in practice:
  - `subsites/mathlab/server.js` — uses T1 (SOTA) for the reasoning step, T2 for explanations.
  - `subsites/lesson2slides/` — uses T2 for slide generation; falls back to T3 for batch.
  - `subsites/voteforyourapp/` — uses T3 (cheap) for vote classification.

Tier-selection examples:
- **Schema design** (1-shot, high-stakes): T1.
- **Per-chunk knowledge extraction** (fan-out): T3 — workerLLM-friendly.
- **Slide generation** (creative, structured): T2.
- **Rule verification** (deterministic + LLM hybrid): T2 if subtle judgment needed; T3 if mostly deterministic.
- **Bulk classification** (label N short texts): T3 or T4.

Env var conventions are managed by the team's platform infra; the canonical list lives in the platform docs (ask platform team for the latest). The four names above (`LLM_MODEL_CHAT`, `LLM_MODEL_VISION`, `LLM_MODEL_IMAGE_GEN`, `LLM_PROXY_BASE_URL`) are the load-bearing ones produced apps reference.

For local-LLM (T4): the team's local-llm bridge runs on-prem Qwen + smaller models. Documented in `to-skills-backend/docs-internal/local-llm-bridge.md` (if present); otherwise ask the platform team.
