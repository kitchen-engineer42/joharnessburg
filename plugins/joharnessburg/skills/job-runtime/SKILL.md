---
name: job-runtime
description: When a produced app accepts an input and runs an expensive generation job the end-user waits on — upload → queued → staged generation → progress → download — build the job runtime instead of letting the job live and die inside one HTTP request. Use this skill whenever a produced app has generation taking more than a few seconds, a progress bar, a job queue, an upload-then-download flow, cancellation, or anything an end-user might refresh the page during. Triggers on "background job", "task queue", "progress tracking", "cancel the job", "resume after refresh", "download the result". This is the produced app's own runtime — NOT John's session endurance ([[context-management]]) and NOT build-time fan-out ([[vertical-workflows]]).
metadata:
  triggers:
    - job queue
    - background job
    - long generation
    - upload and generate
    - progress tracking
    - task status
    - cancel job
    - download artifact
    - resume task
    - sse progress
---

# job-runtime

Some produced apps have the I/O shape: an end-user submits an input, the app runs an expensive generation job — often minutes of staged workerLLM calls — and the user eventually downloads an artifact. The naive build runs that job inside the HTTP request that submitted it. It works in a demo and fails in use, three ways:

1. **The job dies with the request.** Browser disconnect, laptop sleep, a flaky proxy — and minutes of generation are gone.
2. **Refresh loses everything.** There's no task ID to come back to; the user's only option is to start over.
3. **A stuck job eats capacity forever.** One hung generation holds its slot until someone restarts the server.

This skill teaches the runtime that prevents all three: a persistent task registry as the single source of truth, a bounded worker pool with leases, and endpoints whose state derives from the registry rather than from any open connection.

## When this applies (and when it doesn't)

Apply it when generation is expensive enough that an end-user waits on it — multi-stage pipelines, anything past a few seconds, anything with a progress bar. Skip it when it isn't:

- **Static-output apps** (the mechanism ran at build time; the runtime just serves files) have no jobs to manage.
- **Instant request/response** (one workerLLM call, an answer in a couple of seconds) should stay a plain inline call per [[workerllm-runtime]].

The gray zone is a single 5–30 second call. The deciding question: would a user plausibly refresh, navigate away, or submit twice while waiting? If yes, give the job a task ID and a registry row; the rest of the machinery can stay minimal.

## Not [[vertical-workflows]], not the event log

John has two kinds of long parallel work, and they live at different layers. Provider-native scale-out plus [[event-log-and-reducer]] orchestrates *build-time* work: subagents fanning out inside the John session to build the app, coordinating through `.john/events/`. The job runtime ships *inside the produced app* and serves its end-users at app runtime — where the build agent, its subagents, and the event log don't exist. Don't reach for build-session orchestration in produced-app code, and don't build a tasks table to coordinate build-time subagents. Same instinct, different layer, different machinery.

## The shape of the runtime

Every long-running I/O app reduces to the same five pieces:

1. **A task registry** — a `tasks` table (SQLite by default) holding status, stage, paths, timestamps, lease. Every fact about a job lives in a row, not in process memory; everything else is a projection of it.
2. **A bounded worker pool** — N slots; workers claim queued tasks atomically and heartbeat a lease while running.
3. **A progress channel** — SSE or polling, either way projecting registry state to the browser so reconnect-by-task-ID always works.
4. **Control endpoints** — cancel, requeue, download. Cancellation is a flag the worker observes between stages, not a kill.
5. **A sweeper** — a periodic pass that enforces the budgets: queued too long → `queue_timeout`; lease expired → `interrupted` (recoverable, slot freed); ran too long → `generation_timeout`; artifacts past retention → `expired`.

The decisions to make consciously, each detailed in a reference:

- **Registry store** — SQLite default; when Postgres earns its keep → `references/task-registry-and-states.md`
- **The state set** — keep the status enum closed and small; stage detail goes in a free-form `stage` column, not new statuses → same reference
- **Slot count and the two budgets** — queue-wait budget and active-generation budget are separate clocks, never merged → `references/slots-leases-and-timeouts.md`
- **Progress channel** — SSE vs polling rubric, payload contracts → `references/progress-and-cancellation.md`
- **Cancellation checkpoints** — where the worker observes the flag → same reference
- **Recovery posture** — `interrupted` is not `failed`; it's inspectable and requeueable → both references
- **Retention windows** — artifacts expire on a clock; registry rows survive for audit → `references/task-registry-and-states.md`

## Composes with [[workerllm-runtime]]

The stages inside a job call workerLLMs using the standard call shape — nothing about it changes. What this skill adds is the budget nesting: per-call timeout × retries must fit inside the stage's share of the generation budget, and the generation budget must exceed the sum of the stage budgets with headroom. Run the lease heartbeat from a side timer so a stage's retry loop keeps the lease alive without sprinkling heartbeat calls through pipeline code.

## Standalone by default

The default runtime is a SQLite file next to the app, an in-process worker (a thread or asyncio task), and budgets configured through `.env`. No Redis, no message broker, no hosted job service — an external user must be able to clone, configure `.env`, and run. The references describe multi-process scale-ups (Postgres `SKIP LOCKED`, an atomic external slot set) as escalations to reach for when the app actually outgrows one process, not as the starting point. Hosted-platform job orchestration — shared queues, metered slots, platform-managed retention — is template territory, same posture as [[workerllm-runtime]]: design the app so the registry contract stays put and only the claim/slot mechanism moves.

## References

- `references/task-registry-and-states.md` — the tasks-table DDL, the state machine and who moves each transition, recoverable-interrupted semantics, artifact layout and retention.
- `references/progress-and-cancellation.md` — the connection-independence invariant, SSE and polling contracts, the endpoint set, cancellation checkpoints, requeue.
- `references/slots-leases-and-timeouts.md` — the bounded pool, atomic claims, the lease heartbeat, the two budgets and why they're separate, the sweeper.

## Cross-references

- [[app-design-thinking]] — where the runtime shape gets decided; if the app mechanism has end-users waiting on expensive generation, this skill supplies the runtime pattern.
- [[workerllm-runtime]] — the call shape for the LLM work inside job stages.
- [[code-quality-guardrails]] — QC checks that catch missing pieces of this pattern before ship.
- [[vertical-workflows]] / [[event-log-and-reducer]] — the *build-time* analogs; see the layer disambiguation above.
- [[context-management]] — John's own long-session endurance, which this skill is deliberately not about.
