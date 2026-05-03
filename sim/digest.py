"""End-of-day memory digest: compress yesterday's low-importance memories
into a 1-2 line summary per agent. Preserves important memories (i>=6).

Trigger: at sim Day N 23:30 (after diary), digest Day N's low-importance entries.
"""
from __future__ import annotations
import sqlite3
import time
import re
from .memory import MemoryEntry, Memory
from . import llm


# Don't ever fold these — they're load-bearing for the narrative.
PRESERVE_KINDS = {'plan', 'reflection', 'event', 'digest'}
PRESERVE_IMPORTANCE_MIN = 6


def _fetch_foldable(conn: sqlite3.Connection, agent_id: str, day: int) -> list[tuple]:
    """Return (id, sim_time, kind, content, importance) rows for Day N's
    low-importance entries that can be folded into a digest.
    sim_time format: 'Day N(曜日) HH:MM' — match by 'Day N(' prefix."""
    pattern = f'Day {day}(%'
    placeholders = ','.join(f"'{k}'" for k in PRESERVE_KINDS)
    sql = (
        f"SELECT id, sim_time, kind, content, importance "
        f"FROM memory WHERE agent=? AND sim_time LIKE ? "
        f"AND importance < ? AND kind NOT IN ({placeholders}) "
        f"ORDER BY ts ASC"
    )
    cur = conn.execute(sql, (agent_id, pattern, PRESERVE_IMPORTANCE_MIN))
    return cur.fetchall()


def _summarize_with_llm(agent_name: str, day: int, entries: list[tuple]) -> str:
    """LLM-summarize a day's worth of low-importance memories into 2-3 short bullets."""
    if not entries:
        return ''
    lines = []
    for _id, sim_t, kind, content, _imp in entries[:80]:  # cap at 80 entries to bound prompt
        # Strip the "Day N HH:MM" sim_time prefix; keep just HH:MM
        m = re.match(r'Day \d+(?:\([^)]*\))? (\d+:\d+)', sim_t)
        t = m.group(1) if m else sim_t
        lines.append(f'{t}|{kind[:3]} {content[:120]}')

    sys = (f'{agent_name}視点で Day {day} を 2-3 個の短い箇条書きにまとめろ。各40字以内。'
           '日本語のみ。重要な人/場所/感情のみ、雑多は省略。'
           'JSON: {"digest":["...","..."]}\n/no_think')
    usr = f'Day {day}:\n' + '\n'.join(lines[:40]) + '\n\nJSON のみ:'
    import json as _json
    for attempt in range(2):
        try:
            raw = llm.simple_prompt(sys, usr, max_tokens=300,
                                    temperature=0.4 if attempt == 0 else 0.2,
                                    response_format='json')
            data = _json.loads(raw)
            bullets = data.get('digest', [])
            if isinstance(bullets, list) and bullets:
                return ' / '.join(str(b)[:80] for b in bullets[:3])
        except _json.JSONDecodeError:
            continue
        except Exception:
            break
    return f'Day {day}: {len(entries)}件の行動 (要約失敗)'


def digest_day(memory: Memory, agent_name: str, day: int) -> dict:
    """Fold Day N's low-importance memories into a single digest entry.
    Returns {entries_folded, digest_text}.
    """
    with memory._lock:
        rows = _fetch_foldable(memory.conn, memory.agent_id, day)
    if not rows:
        return {'entries_folded': 0, 'digest_text': ''}

    digest_text = _summarize_with_llm(agent_name, day, rows)
    if not digest_text:
        return {'entries_folded': 0, 'digest_text': ''}

    fold_ids = [r[0] for r in rows]
    with memory._lock:
        memory.conn.execute(
            'INSERT INTO memory (agent, ts, sim_time, kind, content, importance) VALUES (?, ?, ?, ?, ?, ?)',
            (memory.agent_id, time.time(), f'Day {day} 23:59', 'digest',
             f'Day {day}総括: {digest_text}', 5)
        )
        # Delete folded entries (originals replaced by digest)
        placeholders = ','.join('?' for _ in fold_ids)
        memory.conn.execute(
            f'DELETE FROM memory WHERE id IN ({placeholders})',
            fold_ids
        )
        memory.conn.commit()

    return {'entries_folded': len(fold_ids), 'digest_text': digest_text}


def digest_all_active(agents: dict, memories: dict, day: int) -> dict:
    """Run digest_day for every active agent. Returns per-agent stats."""
    stats = {}
    for aid, agent in agents.items():
        if not agent.active or agent.status in ('dead', 'arrested'):
            continue
        try:
            r = digest_day(memories[aid], agent.name, day)
            stats[aid] = r
        except Exception as e:
            stats[aid] = {'error': str(e)}
    return stats
