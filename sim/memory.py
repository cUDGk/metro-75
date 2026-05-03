"""Simple memory: SQLite-backed event log per agent."""
from __future__ import annotations
import sqlite3
import json
import time
from dataclasses import dataclass


@dataclass
class MemoryEntry:
    ts: float
    sim_time: str  # "Day 0 06:15"
    kind: str      # 'observation', 'action', 'thought', 'conversation', 'plan', 'reflection'
    content: str
    importance: int = 1  # 1-10, used for retrieval weighting


class Memory:
    def __init__(self, db_path: str, agent_id: str):
        self.db_path = db_path
        self.agent_id = agent_id
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT, ts REAL, sim_time TEXT,
                kind TEXT, content TEXT, importance INTEGER
            )
        ''')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_agent_ts ON memory (agent, ts)')
        self.conn.commit()
        self._lock = __import__('threading').Lock()

    def add(self, entry: MemoryEntry):
        with self._lock:
            self.conn.execute(
                'INSERT INTO memory (agent, ts, sim_time, kind, content, importance) VALUES (?, ?, ?, ?, ?, ?)',
                (self.agent_id, entry.ts, entry.sim_time, entry.kind, entry.content, entry.importance)
            )
            self.conn.commit()

    def recent(self, limit: int = 30) -> list[MemoryEntry]:
        # Exclude low-information action/observation noise from recent stream;
        # those are already tracked in agent.recent_actions and `surroundings`.
        with self._lock:
            cur = self.conn.execute(
                "SELECT ts, sim_time, kind, content, importance FROM memory "
                "WHERE agent=? AND kind NOT IN ('action','observation') "
                "ORDER BY ts DESC LIMIT ?",
                (self.agent_id, limit)
            )
            rows = cur.fetchall()
        return [MemoryEntry(ts=r[0], sim_time=r[1], kind=r[2], content=r[3], importance=r[4]) for r in reversed(rows)]

    def important(self, limit: int = 10) -> list[MemoryEntry]:
        with self._lock:
            cur = self.conn.execute(
                'SELECT ts, sim_time, kind, content, importance FROM memory WHERE agent=? ORDER BY importance DESC, ts DESC LIMIT ?',
                (self.agent_id, limit)
            )
            rows = cur.fetchall()
        return [MemoryEntry(ts=r[0], sim_time=r[1], kind=r[2], content=r[3], importance=r[4]) for r in rows]

    def format_context(self, recent_n: int = 10, important_n: int = 4, max_lines: int = 12) -> str:
        """Compact merged context: importance-first, then chronological recents.
        Single line per memory, short tag, content capped to 140 chars,
        near-duplicate removal via (sim_time, content[:40]) key."""
        rec = self.recent(recent_n)
        imp = self.important(important_n)
        out, seen = [], set()
        # imp first (important wins), then recent oldest→newest
        for m in imp + list(rec):
            k = (m.sim_time, m.content[:40])
            if k in seen: continue
            seen.add(k)
            out.append(f'[{m.sim_time}|{m.kind[:3]}|i{m.importance}] {m.content[:140]}')
            if len(out) >= max_lines: break
        return '\n'.join(out)
