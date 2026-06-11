# Progress, cancellation, and the endpoint set

## The one invariant: connection independence

UI state derives from the registry, never from an open connection. Any stream the app offers is a *projection* of registry rows — convenient, disposable, reconstructible. The test: kill the browser tab mid-generation, open a new one, paste the task ID (or follow a "your jobs" list) — the page must show exactly where the job is. Reconnect is always `GET /tasks/{id}` for the snapshot, then resubscribe to deltas.

The contrast case is instructive: lesson2slides (one of the 5 reference apps) streams its whole pipeline over the submit request itself — beautiful staged SSE events, but the job lives and dies with that one connection. Its event *vocabulary* is worth copying; its coupling of job life to connection life is the first thing the registry removes.

## The endpoint set

| endpoint | purpose |
|---|---|
| `POST /tasks` | accept the input, write the row, return `{task_id}` **immediately** |
| `GET /tasks/{id}` | snapshot: status, stage, timestamps, error, download URL when ready |
| `GET /tasks/{id}/events` | SSE stream of state changes (option A) |
| `GET /tasks/{id}/logs?after_id=N` | incremental progress log (option B, polling) |
| `POST /tasks/{id}/cancel` | set the cancellation flag; returns 202 |
| `POST /tasks/{id}/requeue` | `interrupted`/`failed` → `queued` (attempts under cap) |
| `GET /tasks/{id}/download` | serve `output_path` with a sensible filename |

Submit never holds the request open for generation. It validates, writes the input to `data/tasks/<id>/input/`, inserts the row as `queued`, and returns the task ID — the browser then attaches to the progress channel as a separate, droppable connection.

## Option A — SSE

Event names mirror the state machine plus stage changes. On subscribe, send the current snapshot first, then deltas — that's what makes reconnect free:

```
event: status
data: {"status": "running", "stage": "rendering", "message": "Rendering slides"}

event: progress
data: {"stage": "rendering", "current": 12, "total": 40}

event: done
data: {"status": "succeeded", "download_url": "/tasks/a1b2c3d4e5f6/download", "size_kb": 145}

event: error
data: {"status": "failed", "message": "Renderer returned malformed HTML after 3 retries"}
```

The handler is a loop that watches the row (poll the registry every second or so, or subscribe to an in-process pub/sub the worker publishes to) and formats events. A dropped stream costs nothing: state is in the registry, the client reconnects and gets the snapshot again.

## Option B — polling

The shape a production app-builder uses, and the simpler default. The client polls with a high-water mark; the server returns status plus any progress entries it hasn't seen:

```
GET /tasks/{id}/logs?after_id=42
→ {
    "status": "running",
    "stage": "rendering",
    "logs": [
      {"id": 43, "stage": "rendering", "content": "Slide 12/40", "is_error": false, "timestamp": "..."}
    ]
  }
```

Progress entries live in a small `task_logs` table (id, task_id, stage, content, is_error, timestamp) the worker appends to. Resume-by-task-ID is inherent — any client that knows the ID can poll from `after_id=0` and replay the whole history.

## Choosing between them

- **Polling** wins on simplicity, proxy-friendliness, multi-tab behavior, and trivially correct resume. Default to it.
- **SSE** wins when one live page is watching and sub-second updates matter (token streaming, fast stage flips).
- They compose: SSE for the live page, the snapshot + logs endpoints for everything else. Both satisfy the invariant or neither is acceptable.

## Cancellation: a flag, not a kill

`POST /tasks/{id}/cancel` sets `cancel_requested = 1` and returns 202. It *requests*; it never kills.

- **Queued task**: the handler may flip it straight to `cancelled` — it holds no slot, nothing is running.
- **Running task**: the worker checks the flag **between stages** — each checkpoint is one cheap `SELECT`. On observing it, the worker marks the row `cancelled`, releases its slot, and keeps the artifacts produced so far (they're useful for "resume as a new task" flows and for debugging).

Why not kill mid-call: stage boundaries are the only places where state is consistent. Killing a thread mid-workerLLM-call leaks connections and half-written artifacts, and most HTTP clients can't abort cleanly anyway. If a single stage runs long enough that between-stages is too coarse, add checkpoints inside the stage's own loop (per page, per slide, per entry) — checkpoints are reads; they cost nothing.

## Requeue

`POST /tasks/{id}/requeue` is the recovery hook: allowed from `interrupted` and `failed`, it clears `error` and the lease, flips status back to `queued`, and lets a worker claim it fresh (the claim increments `attempts`). Enforce the attempts cap here — a task at the cap goes to `failed` with an error explaining it, instead of looping forever. Expose requeue in whatever operator surface the app has (even a plain list page of non-terminal tasks); recovery that requires a database console doesn't get used.
