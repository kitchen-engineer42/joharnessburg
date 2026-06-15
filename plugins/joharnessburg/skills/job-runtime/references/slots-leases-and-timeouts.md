# Slots, leases, and the two budgets

## The bounded slot pool

Run at most N generations at once. Size N by what actually constrains the app — memory per job and workerLLM rate limits, almost never CPU; 2–4 is a sane default, set through `.env`. Everything queued beyond N waits as `queued` rows, which is exactly what the queue budget is for.

The default implementation is in-process: a worker loop (asyncio task or thread) that claims the oldest queued task whenever a slot is free. The claim is the part that must be atomic. In SQLite:

```sql
UPDATE tasks
SET status = 'running', started_at = ?, lease_expires_at = ?,
    attempts = attempts + 1, updated_at = ?
WHERE id = ? AND status = 'queued';
-- affected rows == 1 → you won the claim; 0 → someone else did, pick the next task
```

The `AND status = 'queued'` guard is the atomicity; never claim with a read-then-write. Because the registry is the truth, a crash can't leak a slot permanently — the lease expires and the sweeper reclaims it.

**Multi-process scale-up** (described, not prescribed): once several worker processes or hosts claim from one queue, use Postgres `FOR UPDATE SKIP LOCKED` (see `task-registry-and-states.md`), or an external slot set with an atomic check-and-add — an earlier production system guards a shared slot set with a single atomic script so a full pool can never overshoot. Whatever the mechanism, the contract is constant: *claim atomically, hold a lease, heartbeat it, let the sweeper reclaim stale ones.*

## The two budgets — separate clocks, separate verdicts

- **Queue budget** — clock starts at `queued_at`. Generous (minutes to hours, depending on the app's patience). Expiring it produces `queue_timeout`.
- **Generation budget** — clock starts at `started_at`. Sized to the pipeline: the sum of expected stage costs plus headroom. Expiring it produces `generation_timeout`.

Never merge them into one deadline. A merged timeout punishes jobs for queue depth — during a busy hour, jobs burn their whole budget waiting and get killed mid-generation when they would have succeeded; meanwhile a genuinely stuck job hides behind "well, the queue was long". The two expirations also demand different fixes — `queue_timeout` spiking means add capacity or shed load; `generation_timeout` spiking means a pipeline stage is misbehaving — so they need different labels in the registry.

Per-stage budgets within the generation budget are optional; add them when a stage has a known cost profile and overruns should be caught early rather than at the job deadline.

## The lease

A lease is how the system tells *a slow worker* from *a dead one*. On claim, the worker sets `lease_expires_at = now + lease_ttl` (120s is a reasonable ttl) and then heartbeats:

```
# side timer in the worker, independent of pipeline code
every lease_ttl / 3 seconds (plus jitter):
    UPDATE tasks SET lease_expires_at = now + lease_ttl, updated_at = now
    WHERE id = ? AND status = 'running'
```

Run the heartbeat from a side timer (a background thread or asyncio task), not from the pipeline stages themselves — a long stage, or a workerLLM retry loop inside one, then keeps the lease alive without heartbeat calls sprinkled through stage code. When the heartbeat stops — process crash, machine sleep, hard hang — the lease goes stale, and that staleness is the signal the sweeper acts on.

## The sweeper

A periodic pass (every ~60s) plus one pass at startup. Each rule maps a registry observation to a transition:

```
queued    AND queued_at        < now - queue_budget       → queue_timeout
running   AND lease_expires_at < now                      → interrupted   (worker is gone; slot reclaimed)
running   AND started_at       < now - generation_budget  → flag it       (worker is alive; see below)
succeeded AND expires_at       < now                      → expired       (delete artifacts, keep the row)
```

The third rule needs care: if the lease is fresh, the worker is *alive but overrunning* — and the sweeper can't kill an in-process worker safely any more than cancel can. So it flags (set `cancel_requested` with a timeout reason, or a dedicated column), and the worker observes the flag at its next checkpoint and exits as `generation_timeout`. The lease is what distinguishes the two cases: stale lease → dead worker → the sweeper transitions the row itself; fresh lease → slow worker → flag and let it stop at a consistent point.

**Startup orphan reset:** in the default in-process deployment, no worker survives a restart — any row still `running` at boot belongs to a previous process life. Mark them all `interrupted` immediately. (Skip this exact rule in multi-process deployments, where another worker may legitimately be mid-job; there, stale leases alone decide.)

## Interplay with workerLLM retries

[[workerllm-runtime]]'s per-call discipline nests inside this skill's budgets, smallest to largest:

```
per-call timeout × max retries  <  stage budget  <  generation budget
```

If a stage makes a 180s-timeout call with 3 retries, that stage can legitimately take ~9 minutes before it has failed — budget for that, or the generation budget will fire on jobs that were merely retrying. The side-timer heartbeat keeps the lease alive through all of it for free. And never retry the *whole job* inside the worker: job-level retry is requeue, which goes through the registry where `attempts` makes it visible and the cap makes it finite.

## Configuration

Expose the knobs through `.env` with the rest of the app's config — slot count, queue budget, generation budget, lease ttl, artifact retention. Names are the app's choice; what matters is that an external user can tune capacity and patience without touching code.
