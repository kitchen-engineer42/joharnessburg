# The task registry and the state machine

The registry is the one invariant everything else hangs on: **every fact about a job lives in a registry row, not in process memory.** Progress streams, status pages, cancellation, recovery — all of them read or write the row. If the process dies, the rows are still there; that's what makes recovery possible at all.

## The tasks table

SQLite is the right default: one file next to the app, zero operational surface, and WAL mode handles a worker plus request handlers comfortably.

```sql
PRAGMA journal_mode=WAL;   -- request handlers read while the worker writes

CREATE TABLE IF NOT EXISTS tasks (
    id               TEXT PRIMARY KEY,             -- uuid4().hex[:12] is plenty
    status           TEXT NOT NULL DEFAULT 'queued',
    stage            TEXT,                         -- free-form: 'extracting', 'rendering', ...
    source_path      TEXT,                         -- the input as received
    output_path      TEXT,                         -- set on success; what download serves
    error            TEXT,                         -- set on failure; shown to the user
    cancel_requested INTEGER NOT NULL DEFAULT 0,   -- the cancellation flag workers observe
    attempts         INTEGER NOT NULL DEFAULT 0,   -- incremented per worker claim
    created_at       TEXT NOT NULL,
    queued_at        TEXT,                         -- the queue budget's clock
    started_at       TEXT,                         -- the generation budget's clock
    finished_at      TEXT,
    updated_at       TEXT NOT NULL,
    lease_expires_at TEXT,                         -- heartbeat target; stale = worker is gone
    expires_at       TEXT,                         -- artifact retention deadline
    metadata         TEXT                          -- JSON: original filename, options, user key...
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
```

Timestamps as ISO-8601 UTC strings keep SQLite simple; switch to native types on Postgres.

## The state machine

| status | meaning | terminal? |
|---|---|---|
| `queued` | accepted, input saved, waiting for a slot | no |
| `running` | a worker holds a slot; `stage` says where it is | no |
| `succeeded` | `output_path` is ready to download | yes |
| `failed` | generation raised; `error` says why | yes |
| `cancelled` | user cancelled while queued or between stages | yes |
| `queue_timeout` | waited past the queue budget without ever starting | yes |
| `generation_timeout` | ran past the generation budget | yes |
| `interrupted` | the runtime lost the worker (crash, stale lease) | no — requeueable |
| `expired` | retention sweep deleted the artifacts | yes |

Who moves each transition matters as much as the arrows — three actors touch the table, and keeping their writes disjoint is what keeps the machine honest:

| transition | moved by | when |
|---|---|---|
| (new) → `queued` | API handler | submit accepted, input written to disk |
| `queued` → `running` | worker | atomic claim won; sets `started_at`, `lease_expires_at`, `attempts += 1` |
| `queued` → `cancelled` | API handler | cancel on a queued task — immediate, it holds no slot |
| `queued` → `queue_timeout` | sweeper | `queued_at` older than the queue budget |
| `running` → `succeeded` / `failed` | worker | the pipeline finished or raised |
| `running` → `cancelled` | worker | observed `cancel_requested` at a checkpoint |
| `running` → `generation_timeout` | worker (flagged by sweeper) | overran the generation budget; observed like a cancel |
| `running` → `interrupted` | sweeper | lease expired — the worker is gone; slot reclaimed |
| `interrupted` / `failed` → `queued` | API handler (requeue) | operator or user requeues; `attempts` under the cap |
| `succeeded` → `expired` | sweeper | `expires_at` passed; artifacts deleted, row kept |

**Keep the status enum closed; keep `stage` open.** The tempting mistake is one status per pipeline stage. A production app-builder grew an eleven-status enum that way, and every sweep, UI conditional, and metric had to enumerate all eleven. Stages vary per app; lifecycle states don't. The enum above is the lifecycle; `stage` carries the app-specific detail (`extracting`, `planning`, `rendering`, …) and nothing has to enumerate its values.

## `interrupted` is recoverable, not failed

`interrupted` means *the runtime lost the worker*, not *the job is bad* — a deploy restarted the process, the machine slept, a stage hung past its lease. Keep it distinct from `failed` so it can be inspected and requeued rather than silently retried or silently dropped. The worker increments `attempts` on every claim; enforce a cap (3 is a sane default) at requeue time, after which the task goes to `failed` with an explanatory `error`. Whether to *auto*-requeue interrupted tasks at startup is an app decision — for cheap idempotent jobs, do it; for expensive ones, leave them visible for a human (or the submitting user) to requeue.

## When Postgres earns its keep

Move when there are multiple worker *processes* (or hosts) claiming from the same queue, or when write contention outgrows WAL. The schema carries over; the claim becomes:

```sql
UPDATE tasks SET status = 'running', started_at = now(), ...
WHERE id = (
  SELECT id FROM tasks WHERE status = 'queued'
  ORDER BY queued_at LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

`SKIP LOCKED` is the whole point — concurrent claimers never block or double-claim. Don't start here; one process and SQLite cover the default deployment.

## Artifact layout and retention

Keep everything a job touches under one directory keyed by task ID:

```
data/tasks/<task_id>/
├── input/           # the upload, byte-for-byte as received
├── prompts/         # what was actually sent to workerLLMs
├── intermediates/   # per-stage outputs (extracted text, the plan, ...)
├── output/          # the final artifact(s) the download endpoint serves
└── debug/           # stage logs, timings, a postmortem bundle
```

Persist prompts and intermediates *as the job runs*, not only on success — when a job fails at stage four, they're the difference between a postmortem and a shrug.

Retention: on success, set `expires_at` (somewhere between 24 hours and 7 days fits most apps; make it an `.env` knob). The sweeper deletes the task directory and marks the row `expired` — the row itself survives, so history, metrics, and "where did my deck go?" support questions keep working after the bytes are gone. Run that sweep at startup and then periodically, never only at startup: a long-lived process otherwise never cleans up.
