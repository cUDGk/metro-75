# Memory + Context System Optimization Proposal

Target: cut prompt context tokens 40-55% while preserving high-importance memories.
Hard constraint: importance >= 7 entries (events, witnesses, reflections) are NEVER lost.

---

## 1. Compact format_context output (sim/memory.py:62-77)
**Header dropping + sim_time abbreviation.** Current `[Day X HH:MM] (kind) content` is ~18-22 chars of pure boilerplate per line. Drop the kind tag for low-info kinds, shorten sim_time to `D0/12:30`, and skip the `### ...:` section banners (replace with single-char prefixes `*` important / `-` recent).

```diff
-        lines = ['### Important Memories:']
-        for m in imp:
-            if m.content not in seen:
-                lines.append(f'[{m.sim_time}] ({m.kind}) {m.content}')
+        lines = []
+        for m in imp:
+            if m.content not in seen:
+                lines.append(f'*{_short_time(m.sim_time)} {m.content}')
                 seen.add(m.content)
-        lines.append('\n### Recent:')
         for m in rec:
             if m.content not in seen:
-                lines.append(f'[{m.sim_time}] ({m.kind}) {m.content}')
+                # Skip kind for low-info kinds (action/observation)
+                tag = '' if m.kind in ('action','observation') else f'({m.kind[:3]})'
+                lines.append(f'-{_short_time(m.sim_time)}{tag} {m.content}')
```
Expected token saving: **~12-18%** on the entire memory block (boilerplate is purely structural).

---

## 2. Drop low-info kinds from `recent()` retrieval (sim/memory.py:44)
`action` (importance=2) and `observation` from observe (importance=2) flood recent. They're already mirrored by `agent.recent_actions[-3:]` and `surroundings`. Filter at SQL level so they never reach prompt.

```diff
-    def recent(self, limit: int = 30) -> list[MemoryEntry]:
+    def recent(self, limit: int = 30, exclude_kinds: tuple = ('action',)) -> list[MemoryEntry]:
         with self._lock:
+            placeholders = ','.join('?' * len(exclude_kinds))
             cur = self.conn.execute(
-                'SELECT ts, sim_time, kind, content, importance FROM memory WHERE agent=? ORDER BY ts DESC LIMIT ?',
-                (self.agent_id, limit)
+                f'SELECT ts, sim_time, kind, content, importance FROM memory '
+                f'WHERE agent=? AND kind NOT IN ({placeholders}) ORDER BY ts DESC LIMIT ?',
+                (self.agent_id, *exclude_kinds, limit)
             )
```
Expected saving: **~20-25%** (action+raw-observation are the bulk of low-value entries).

---

## 3. Hot-window cache + cold-window summary (sim/memory.py, new method)
Past >1 sim-day entries with importance < 6 get LLM-summarized once into a single `kind='digest'` row, then originals are excluded from retrieval. Implement as nightly job in `tick.py` at `world.hour == 5 and world.minute == 0` (just before plan time):

```python
# new in memory.py
def consolidate_old(self, before_ts: float, llm_summarize):
    rows = self.conn.execute(
        'SELECT id, sim_time, kind, content FROM memory '
        'WHERE agent=? AND ts<? AND importance<6 AND kind!="digest"',
        (self.agent_id, before_ts)).fetchall()
    if len(rows) < 8: return
    text = '\n'.join(f'[{r[1]}]({r[2]}){r[3]}' for r in rows)
    summary = llm_summarize(text)  # ~80 chars JP
    self.add(MemoryEntry(ts=before_ts, sim_time='digest',
        kind='digest', content=summary, importance=5))
    self.conn.executemany('DELETE FROM memory WHERE id=?', [(r[0],) for r in rows])
```
**Importance >= 6 entries are physically untouched.** Saves 60-80% of low-value rows after day 2. Expected end-to-end: **~25-30%** prompt reduction by day 7.

---

## 4. Faction-relevance weighting in `important()` (sim/memory.py:53)
A "アントワーヌ・バンクスがコブラ・デヴォンの弟を殺した" memory matters infinitely more to gang_a than to civilians. Boost retrieval by (importance + faction_keyword_match * 2):

```diff
-    def important(self, limit: int = 10) -> list[MemoryEntry]:
+    def important(self, limit: int = 10, faction_keywords: list[str] = ()) -> list[MemoryEntry]:
+        # Bias toward content mentioning user's faction-keywords
+        like_clauses = ' + '.join([f"(CASE WHEN content LIKE ? THEN 2 ELSE 0 END)" for _ in faction_keywords])
+        score_expr = f"importance + ({like_clauses})" if faction_keywords else "importance"
         cur = self.conn.execute(
-            'SELECT ts, sim_time, kind, content, importance FROM memory WHERE agent=? ORDER BY importance DESC, ts DESC LIMIT ?',
-            (self.agent_id, limit)
+            f'SELECT ts, sim_time, kind, content, importance FROM memory WHERE agent=? '
+            f'ORDER BY {score_expr} DESC, ts DESC LIMIT ?',
+            (self.agent_id, *[f'%{k}%' for k in faction_keywords], limit)
         )
```
Caller in `agent.py:172` passes `faction_keywords=['ガーネット','ホーク']` etc. **No token cost change**, but lets us safely lower `important_n` from 6 → 4 because what's retrieved is more relevant. **~8% saving** via reduced N.

---

## 5. Dedup near-duplicates in `format_context` (sim/memory.py:66)
Current `seen` is exact-string match. Reuse existing `_normalize_text` from `agent.py:34` and bigram-overlap (already implemented at `agent.py:43`):

```diff
+from .agent import _normalize_text  # or move to memory.py
+
     def format_context(self, ...):
         ...
-        seen = set()
+        seen_norm = []
         for m in imp:
-            if m.content not in seen:
-                ...
-                seen.add(m.content)
+            n = _normalize_text(m.content)[:40]
+            if not any(n == s or (len(n)>10 and n in s) for s in seen_norm):
+                lines.append(...)
+                seen_norm.append(n)
```
Catches the "周囲確認: ..." / "X を念入りに調査" duplicates. Saving: **~5-8%**.

---

## 6. Conversation memory: store speaker-msg pairs once (sim/tick.py:85-90)
Every nearby agent stores `'{name}の発言を聞いた: 「{message}」'` (~60-80 chars). When 6 agents are within range, that's 6 rows × 80 chars. Compress: store only the message + speaker, drop the boilerplate prefix. The format_context can re-add `←` on rendering.

```diff
-                self.memories[other.id].add(MemoryEntry(
-                    ts=..., kind='conversation',
-                    content=f'{agent.name} の発言を聞いた: 「{message}」',
+                self.memories[other.id].add(MemoryEntry(
+                    ts=..., kind='heard',
+                    content=f'{agent.name}「{message}」',
                     importance=4 if range_tiles <= 3 else 3,
                 ))
```
Saves ~20 chars per heard line × ~5-10 per prompt = **~6-9%**.

---

## 7. Tighten prompt N defaults (sim/agent.py:172, sim/cognition.py:14,47)
Once #2-#5 land, redundancy is gone — drop N's:

| Site | Before | After |
|---|---|---|
| agent.py:172 action | recent_n=12, important_n=6 | **recent_n=8, important_n=4** |
| cognition.py:14 plan | recent_n=20, important_n=8 | **recent_n=12, important_n=6** |
| cognition.py:47 reflect | recent_n=25, important_n=8 | **recent_n=15, important_n=6** |

**~30-35%** raw line-count reduction in mem block; safe because action_kind filtering (#2) means each surviving line is higher-density.

---

## 8. Forgetting curve at write-time, NOT read-time (sim/memory.py:36)
DON'T probabilistically delete (data loss risk). Instead, downgrade importance over time only for entries where **importance < 5 AND age > 2 sim-days**. Run with #3's nightly consolidation. importance >= 5 (events, witnesses, plans, reflections) are immutable. **No prompt saving directly**, but feeds #4 ranking.

---

## Combined estimate
Stacking #1 + #2 + #3 + #5 + #6 + #7 (non-overlapping savings, geometric mean adjusted):
- Day 0-1: **~35-40%** reduction (#1+#2+#5+#6+#7)
- Day 3+: **~50-55%** reduction (above + #3 digest kicks in)

Concrete: ~6600-token reflect prompt → ~3000-3300 tokens. Action prompt: ~1800 → ~900-1100.

## What we explicitly do NOT do
- No deletion of importance >= 6 rows ever (kills "弟が殺された", witness, reflection).
- No LLM-summary on hot window (latency + risk of paraphrase drift on critical facts).
- No clustering across agents (each agent's POV must stay distinct).
