"""Build a chronological timeline of events from a metro-75 run."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sys, io, os, sqlite3, re, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LOG_DIR = sys.argv[1] if len(sys.argv) > 1 else 'logs/run7day_20260429_074317'
DB = os.path.join(LOG_DIR, 'memory.db')
EVENTS_LOG = os.path.join(LOG_DIR, 'events.log')
DIALOGUE_LOG = os.path.join(LOG_DIR, 'dialogue.log')


def parse_sim_time(s: str) -> tuple[int, int, int]:
    m = re.match(r'Day (\d+)(?:\([^)]*\))?\s*(\d+):(\d+)', s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (-1, 0, 0)


def cur_min(s):
    d, h, m = parse_sim_time(s)
    return d * 1440 + h * 60 + m


def main():
    items = []  # (sim_min, sim_time_str, kind, agent, content)

    # 1. From memory.db: scripted events, reflections, witness, plan, digest
    if os.path.exists(DB):
        c = sqlite3.connect(DB)
        for r in c.execute(
            "SELECT sim_time, kind, agent, content, importance FROM memory "
            "WHERE kind IN ('event','reflection','witness','plan','digest') "
            "ORDER BY sim_time, ts").fetchall():
            sim_t, kind, agent, content, imp = r
            items.append((cur_min(sim_t), sim_t, kind, agent, content, imp))
        c.close()

    # 2. From events.log: attack/arrest/say lines
    if os.path.exists(EVENTS_LOG):
        with open(EVENTS_LOG, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                m = re.match(r'\[([^\]]+)\] ([^:]+): (.+)', line)
                if not m: continue
                sim_t, agent, content = m.group(1), m.group(2), m.group(3)
                # Pick interesting action types
                if any(k in content for k in ['攻撃', '殺害', '逮捕', '尾行', '探る', '調べる']):
                    items.append((cur_min(sim_t), sim_t, 'action', agent, content, 4))

    # Sort chronologically
    items.sort(key=lambda x: (x[0], x[2]))

    # Output as markdown
    out = ['# Metro-75 — 7日間タイムライン (時系列)']
    out.append('')
    out.append(f'Source: `{LOG_DIR}`')
    out.append('')
    cur_day = -1
    for sim_min, sim_t, kind, agent, content, imp in items:
        d = sim_min // 1440
        if d != cur_day:
            cur_day = d
            out.append('')
            out.append(f'## Day {d}')
            out.append('')
        # Strip Day N prefix from sim_t for compact display
        m = re.match(r'Day \d+(?:\([^)]*\))?\s*(\d+:\d+)', sim_t)
        t_short = m.group(1) if m else sim_t
        # Color/emoji per kind
        emoji = {
            'event': '⚡', 'witness': '👁️', 'reflection': '💭',
            'plan': '📋', 'digest': '📔', 'action': '🔸',
        }.get(kind, '•')
        # Trim content
        line = f'- `{t_short}` {emoji} **{agent[:30]}**: {content[:200]}'
        out.append(line)

    out_path = os.path.join(LOG_DIR, 'TIMELINE.md')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print(f'wrote {out_path} ({len(items)} entries)')

    # Also: filter only "事件" (attack/kill/arrest/witness)
    incidents = [x for x in items if x[2] in ('witness',) or
                 any(k in x[4] for k in ['攻撃', '殺害', '逮捕', '殺し', '撃った', '殴った'])]
    print(f'\n=== 事件 ({len(incidents)} 件) ===')
    for sim_min, sim_t, kind, agent, content, imp in incidents:
        print(f'[{sim_t}] [{kind}] {agent[:30]}: {content[:200]}')


if __name__ == '__main__':
    main()
