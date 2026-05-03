# Tick-loop parallelization optimization (Metro-75)

Quality bar: each agent's plan/reflect/decide cadence stays identical (still 1 plan/day, 1 reflect/4h, 1 action/h). All wins come from **flattening synchronization peaks** and **reducing sequential wall time inside Phase 3**, not from skipping work.

Pool is the binding constraint: `NUM_PARALLEL=2` → at most 2 LLM calls in flight, 14.7s each. 25-call burst = `ceil(25/2) * 14.7s = 13 * 14.7s ≈ 191s`. 50-call burst (4h-mark) = `25 * 14.7s ≈ 367s`. Anything below the pool floor is invisible; the wins below are the ones that actually move that floor.

---

## Tier 1 — high-impact, low-risk

- **`sim/tick.py:149-151` — Reflection staggering by agent-id hash.** 25 reflects fire on the same minute (`cur - last_reflect >= 240`). Replace the trigger with `cur % 240 == hash(aid) % 240` (or initialize `_last_reflect[aid] = -240 + (hash(aid) % 240)`). Each agent still reflects every 240 sim-min; the burst becomes ~1 reflect/sim-min instead of 25 in one tick. Burst 50 calls → 25 calls. **Expected: ~40% wall-time reduction at the 4-hour mark, ~10% across the whole run** (since these marks dominate today).

- **`sim/tick.py:144-146` — Plan pre-staking the night before.** All 25 plans fire at exactly `06:00`. Spread `to_plan` across 22:00–05:59 the previous sim-day, one slot per agent indexed by `hash(aid) % 480` minutes before 06:00. Same 1 plan/day per agent; the 06:00 burst dissolves into the low-traffic overnight window where it overlaps with the otherwise-idle pool. **Expected: ~5–8% on a 28-day run** (1 of every ~24 ticks today is the planning spike).

- **`sim/tick.py:163-178` — Single unified queue, drop the priority split.** Currently plans, reflects, and actions are submitted as three separate `dict` groups. The `executor.submit` calls already queue them all into one ThreadPoolExecutor; the split only matters for the *result-collection* loops in Phase 3. Submit them in a single interleaved order so a slow plan doesn't gate fast actions on the same host. Pair with `as_completed` (next item). **Expected: ~3–5%** on its own; enables the next item.

- **`sim/tick.py:182-217` — Replace `for aid in sorted(...)` with `concurrent.futures.as_completed`.** Today, Phase 3 waits for plan #1 before it touches reflect #1. Determinism is preserved by *applying* in agent-id order at the end, but **collecting** results can be order-independent: gather into `results: dict[aid → (kind, value)]` as they finish, then run a single deterministic apply pass. This is wall-clock-neutral when calls are uniform, but cuts tail latency when one agent's call is much slower (long context, retry-on-invalid-verb in `sim/agent.py:300-318`, `:328-338`). **Expected: ~5–8%** because retries happen often and they double a single agent's latency.

---

## Tier 2 — medium-impact, mild risk

- **`sim/tick.py:144` — Action-priority ordering inside the unified queue.** Submit `pending_response_to`-bearing agents first, then attackers/arresters within ≤2 tiles, then plain `walk_to`/`observe` types. Two-host pool means the *first* two submits get the freshest hosts; pending responses are the highest-narrative-value calls and benefit most from low latency. No quality drop — every agent still acts. **Expected: ~2–4%** wall time, but a real drop in "agent answered 60 sim-min after being addressed" lag.

- **`sim/agent.py:300-318` and `:328-338` — Retry budget on invalid-verb / repeat checks.** Today these are *unbounded sequential extra calls* inside a single Phase 2 future, doubling/tripling that agent's latency and starving the pool. Cap at 1 retry total (already true here), but **submit the retry as a separate future** instead of blocking the original worker. Implementation: `decide_action` returns either a finished result or a "needs-retry" payload; tick.py resubmits in a second mini-batch. **Expected: ~3–6%**, and removes the worst tail-latency outliers.

- **`run_28day.py:133-138` — Snapshot rendering off the hot path.** PIL `render()` at 4px tiles + 200×200 world walks ~160k pixels in pure Python — measurable (likely 0.3–1.0s) but it runs synchronously in the same thread that drives the tick loop, blocking the next `tick_once`. Move to a dedicated single-worker `ThreadPoolExecutor` with a 1-deep queue (drop oldest if behind). Pillow releases the GIL during `img.save`, so this is real parallelism. **Expected: ~1–2%** at current cadence (6 snaps/sim-day), more if cadence increases.

- **`sim/memory.py:36-42` — Batch memory writes per tick.** Each `Memory.add` does `INSERT + COMMIT`. In Phase 3, a single tick at the 4h-mark performs 25 reflection-inserts + 25 action-inserts + N thought-inserts + N witness-inserts → up to ~80 commits, each fsync-ed (`synchronous=NORMAL` still flushes WAL on commit). Group all writes in a single tick into one transaction (`BEGIN; …; COMMIT`) at the end of `tick_once`. WAL contention drops sharply. **Expected: ~2–4%** (Windows fsync isn't free even on SSD).

---

## Tier 3 — small / situational

- **`sim/tick.py:122-123` — `chat_broadcast` grows unbounded.** `self.chat_broadcast.append(...)` is never trimmed; `_build_snapshot` slices `[-15:]` so it's correct, but list grows over a 28-day run (~25 agents × ~50 says/day × 28 = 35k entries). Cap at `[-200:]` after each tick. **Expected: ~0.5%, but prevents memory drift**.

- **`sim/tick.py:81-93` — `broadcast_chat` is O(N) over all agents per say/whisper.** With 25 agents and ~5 says/tick at peaks, that's 125 distance checks + memory writes per tick. Pre-compute a coarse spatial bucket (`(x//16, y//16) → [agents]`) once at the start of `tick_once`, scan only neighboring buckets in `broadcast_chat`/`witness_event`. **Expected: <1% today** but matters when scaled to 50+ agents.

- **No-op: conditional reflection.** *Rejected.* User constraint: "各 agent のリフレクション回数は維持". Skipping based on event count violates that even if a "boring" agent's reflect is low-value.

- **No-op: pool size.** Out of scope — host-level concurrency (`NUM_PARALLEL=2`) is the hard ceiling. Every Tier-1/2 item above already assumes pool=2; raising it would multiply gains but is a separate decision.

---

## Combined estimate

Tier 1 alone (reflection stagger + plan stagger + as_completed): **~45–55% wall-clock reduction** on the 4h-mark ticks (the current bottleneck), **~15–20% across a full 28-day run**. Stacking Tier 2 (priority ordering + retry-as-future + async snapshot + batched commits) adds another **~7–12%**. End-to-end realistic target: **~25–30% faster wall clock** with zero quality regression.

## Race-condition / lock review

- `chat_broadcast`, `event_log`, `dialogue_log`, `agents[*]` mutations are all in Phase 3 main thread → safe.
- `Memory._lock` already serializes per-agent SQLite writes; cross-agent writes contend on the **single SQLite WAL file**, not Python locks. Batching (Tier 2 item 4) is the right fix, not finer locks.
- `_HostPool._q` is a `queue.Queue` (thread-safe).
- Reordering Phase 3 collection via `as_completed` is safe iff the **apply** order stays deterministic — Tier 1 item 4 explicitly preserves that.
