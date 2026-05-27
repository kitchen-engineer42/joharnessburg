---
name: platform-credits
description: When the produced app performs priced operations (LLM calls, image generation, document parsing, PDF conversion, anything the platform charges users for), use this skill. Triggers on "credits", "billing", "quota", "rate limit", "is this priced?", or any feature that consumes platform resources. Teaches the lock/settle/cancel idempotency pattern; does NOT implement the credit backend (the platform owns it).
metadata:
  triggers:
    - credits
    - billing
    - quota
    - rate limit
    - usage cost
    - priced operation
    - lock and settle
    - idempotency key
---

# platform-credits

Any operation the platform charges for follows the **lock → execute → settle/cancel** pattern, with idempotency keys to make every step safely retryable. Don't reinvent this — the team has hardened it across multiple subsites.

## The lifecycle of one priced operation

1. **Lock**: call `/internal/credits/lock` with `{user_id, operation, estimated_cost, idempotency_key}` BEFORE doing the priced work. The platform verifies the user has the credits and reserves them. Returns a `lock_id`.
2. **Execute**: do the priced work — call the LLM, generate the image, parse the PDF. Pass `lock_id` + `source_app_id` so the platform can trace the work back to the lock.
3. **Settle on success**: call `/internal/credits/settle` with `{lock_id, actual_cost, idempotency_key}`. The platform finalizes the charge.
4. **Cancel on failure**: call `/internal/credits/cancel` with `{lock_id, reason, idempotency_key}`. The reserved credits return to the user.

## Idempotency keys are mandatory

Every call MUST include an `idempotency_key` (UUIDv4 is fine). The platform stores recent keys; retrying a settle/cancel with the same key is a no-op. Without this, network retries double-charge users.

## What to do in this project

1. **Audit priced ops at design time** (during phase-design, not later). For each priced operation in the produced app, write down: estimated_cost, idempotency boundary (where retry is safe), failure modes.
2. **Wire the three calls** around each priced operation. Don't skip cancel on failure — that strands credits in escrow.
3. **Pass `source_app_id`** so the platform's billing dashboard groups usage by app. Hardcoded in the produced app's config.
4. **Test the retry path locally**. The team's dev environment has a credit sandbox; use it.

## What you should NOT do

- Don't perform the priced operation BEFORE the lock. If the lock fails (user out of credits), the work was wasted.
- Don't skip the cancel call on failure. Even if your error handler is messy, the cancel must fire.
- Don't reuse idempotency keys across operations. One key per attempt.
- Don't track credits client-side. The platform is the source of truth.

See `references/source.md` for paths into the team's docs + example implementations.
