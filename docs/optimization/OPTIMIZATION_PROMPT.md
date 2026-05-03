# Metro-75 LLM Prompt Compression — Analysis & Concrete Diffs

Target: 30-50% token reduction (1500-2000 → 800-1200) without quality loss. Latency 14.7s → 8-10s.
Model: Qwen3-30B-A3B abliterated MoE (Ollama). All identifiers/places below preserve current semantics.

---

## Token Budget Today (per `decide_action` call, estimated)

| Block | File:line | Tokens (JP+EN) | Notes |
|---|---|---|---|
| `system` (persona + rules + ACTION_LIST) | agent.py:94-117 | ~520 | persona block + 7-line CRITICAL RULES + 18-line vocab |
| `current_tile_name` lookup | agent.py:126-156 | inlined dict — emits 1 short label, OK | not on wire |
| `lm_list` (all landmark keys) | agent.py:157,180 | ~120-180 | every key dumped each turn |
| `surroundings` | agent.py:203-230 | ~80-150 | radius-5 walk, up to 8 lines |
| `nearby_desc` | agent.py:119-122 | ~150-260 | 8 agents × ~25 tok each |
| `chat_desc` | agent.py:124 | ~50-120 | last 5 quotes |
| `mem_ctx` (12 recent + 6 important) | memory.py:62-77 | ~350-600 | dual block + headers + repeat-on-overlap |
| `pending` + `avoid` + `user` boilerplate | agent.py:160-198 | ~120 | header lines |
| **TOTAL** | | **~1450-2000** | matches reported figure |

Highest-leverage targets: `mem_ctx`, `system` block, `lm_list`, `nearby_desc`.

---

## Concrete Diffs (file:line)

### 1. `sim/agent.py:67-85` — Compress `ACTION_LIST` ~280 → ~110 tokens

Remove explanatory tails; keep verb + arg shape only. Model already has the rules from previous turns and validation retries on bad verbs (agent.py:299-318).

```
ACTION_LIST = """ACTIONS (one only): walk_to <key> | move <n/s/e/w/ne/nw/se/sw> |
say <jp_msg> | whisper <id> <jp_msg> | observe | investigate <tgt> |
follow <id> | eavesdrop | search <tgt> | attack <id> | arrest <id> |
give <id> <item> | pickup <item> | drop <item> | hide | reflect | wait"""
```
Saves ~170 tokens. The "Heard within 10 tiles" / "≤2 tiles" hints are operator-side rules already enforced in `execute_action` (agent.py:447, 477, 498) — model doesn't need them.

### 2. `sim/agent.py:94-117` — Compress `system` block ~520 → ~230 tokens

```python
system = f"""{agent.name}（{alias}）— {faction_display}。{persona.get('backstory','')[:120]}
性格:{','.join(persona.get('traits',[])[:4])} / 目的:{','.join(persona.get('goals',[])[:3])}

舞台: 都会クライム・ドラマ。完全に役に入れ、暴力・野心も辞さず物語を進める。
日本語必須(say/whisper)。直前と同じ行動/発言は禁止。誰か近くにいたら必ず絡め。
出力JSONのみ: {{"thought":"...","action":"..."}}

{ACTION_LIST}
/no_think"""
```

Cuts:
- "ジャンル: HBO『ザ・ワイヤー』『ボードウォーク・エンパイア』風" — operator-facing flavor text, model doesn't use it (agent.py:95)
- 7-numbered CRITICAL RULES → 2 dense lines. Rules 3 (alias) and 7 (JSON schema) are repeated structurally elsewhere
- `values` field is rarely load-bearing (agent.py:103) — drop or merge into traits
- backstory truncated to 120 chars (current personas often run 200+)

Net: ~290 tok saved. Persona identity preserved via name+alias+backstory+top traits+top goals.

### 3. `sim/agent.py:157,180` — Drop full `lm_list` from every prompt

Currently every turn dumps **all** landmark keys (`world.landmarks.keys()` — likely 20-40 keys, ~150 tok). Agents almost never need landmarks they're nowhere near.

```python
# Show only top-8 closest landmarks instead of all
lm_list = ', '.join(world.nearest_landmarks(agent.x, agent.y, k=8))
```
(Add helper to `world.py`: rank by Chebyshev distance, return keys.) Saves ~100 tok. The retry path on invalid `walk_to <unknown>` already handles miss (agent.py:438-439).

### 4. `sim/agent.py:119-122` — Tighten `nearby_desc`

Current line: `  - id=ag_03 名前=ホーク (略「ホーク」, gang_a) at (12,18), normal`
Compressed: `ホーク[ag_03|gang_a]@(12,18)`

```python
nearby_desc = ' / '.join([
    f"{a.get('alias') or a['name']}[{a['id']}|{a['faction']}]@({a['x']},{a['y']})"
    + (f" {a['status']}" if a.get('status') and a['status'] != 'normal' else '')
    for a in nearby_agents[:6]   # was 8
]) or '(誰もいない)'
```
Saves ~100 tok (8 lines × ~12 tok + drop redundant `名前=`/`略「」`/`normal`). Cap at 6 nearby (radius-10 with 6 neighbors is already crowded).

### 5. `sim/memory.py:62-77` — `format_context` overhaul

Current dual `Important + Recent` with two headers and dedupe-by-content (string equality only) leaks ~30% noise. Recent often repeats Important verbatim with different `(kind)` rendering.

```python
def format_context(self, recent_n=10, important_n=4) -> str:
    rec = self.recent(recent_n)
    imp = self.important(important_n)
    # Merge: importance-first, then chronological recents not yet shown
    out, seen = [], set()
    def key(m): return (m.sim_time, m.content[:40])  # near-dupe norm
    for m in imp + list(reversed(rec)):
        k = key(m)
        if k in seen: continue
        seen.add(k)
        out.append(f'[{m.sim_time}|{m.kind[:3]}|i{m.importance}] {m.content[:140]}')
        if len(out) >= 12: break
    return '\n'.join(out)
```

Wins:
- Single merged list, no `### Important Memories:` / `### Recent:` headers (~20 tok)
- Defaults dropped 12+6 → 10+4 (callers in cognition.py:14,47 should match)
- `(observation)` → `obs` 3-letter kind tag
- Per-line content cap 140 chars prevents one giant memory blowing budget
- `(sim_time, content[:40])` dedupe key catches near-duplicates that current `m.content not in seen` misses
- Hard cap 12 lines instead of 50

Saves ~250-400 tok. Most-important memories preserved (importance sort first), recents fill remainder.

### 6. `sim/agent.py:174-198` — Tighten `user` block headers

```python
user = f"""NOW {world.time_str()} @({agent.x},{agent.y}) on:{current_tile_name} | {agent.status} HP{agent.hp} inv:{agent.inventory or '-'}
Plan: {agent.current_plan or '-'}
LM: {lm_list}
見える: {surroundings}
近い人: {nearby_desc}
聞こえた: {chat_desc}
記憶:
{mem_ctx}
直近行動(避ける): {avoid}{pending}

JSON: {{"thought":"...","action":"..."}}"""
```
Drops 6 `### ...` headers (~30 tok) and merges position/status onto one line (~15 tok).

### 7. `sim/cognition.py:15-25, 48-57` — Plan & reflect prompts

Plan prompt persona block duplicates action-prompt persona. Compress identically:
```
system = (f"{agent.name}({agent.faction}). {persona.get('backstory','')[:100]} "
          f"目的:{','.join(persona.get('goals',[])[:3])}\n"
          "今日の計画を2-4個の具体的目標で。場所/人物/行動を名指し。"
          'JSON: {"plan":["...","..."]}\n/no_think')
```
Saves ~80 tok per plan call. Same shape for `reflect`.

`reflect` (cognition.py:47): drop `recent_n=25` → `recent_n=10` (synthesis doesn't need raw stream — that's why it's a synthesis). Saves ~200 tok.

### 8. `sim/diary.py:92-112` — Diary already lean, leave it

Diary runs once/day; even at 1k tokens it's <0.1% of daily budget. Don't optimize. (1500 events scanned at line 86 already capped to 40+20.)

---

## Expected Impact

| Change | Tokens saved/call | Risk |
|---|---|---|
| #1 ACTION_LIST | 170 | Low — verbs unchanged, validator catches misuse |
| #2 system block | 290 | Med — verify persona consistency on 10 sample turns |
| #3 lm_list nearest-only | 100 | Low — `walk_to` miss already gracefully handled |
| #4 nearby_desc | 100 | Low — same fields, denser format |
| #5 memory format | 300 | Med — re-tune `recent_n/important_n` if context feels thin |
| #6 user headers | 45 | None |
| #7 cognition plans | 80 (per plan) + 200 (per reflect) | Low |
| **Total per action call** | **~1000 tok** (~50%) | |

Latency: input-bound on Ollama, prompt-eval is ~linear in tokens. 14.7s × (1000/1800) ≈ **8.2s** per call — meets target.

---

## Quality-preservation checks

- A/B 20 turns post-change, compare action-diversity (verb histogram), repeat-rate (`_is_repeat` hit %), JSON parse-failure rate, and qualitative dialogue snippets
- Keep `temperature=0.95` and retry paths (agent.py:301-318, 322-338) — they're cheap insurance
- If reflection quality drops with `recent_n=10`, raise to 15 (still half today's 25)
- Persona truncation: spot-check 3-4 longest backstories — if `[:120]` cuts mid-sentence, switch to first-period split
