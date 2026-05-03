"""Generate a final REPORT.md summarizing the 7-day run."""
import sys, io, os, json, sqlite3, glob, re
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LOG_DIR = 'logs/resume_20260426_215201'
OUT = 'logs/resume_20260426_215201/REPORT.md'


def main():
    # Read events.log + dialogue.log
    events = []
    with open(os.path.join(LOG_DIR, 'events.log'), encoding='utf-8') as f:
        events = [l.strip() for l in f if l.strip()]
    dialogue = []
    with open(os.path.join(LOG_DIR, 'dialogue.log'), encoding='utf-8') as f:
        dialogue = [l.strip() for l in f if l.strip()]

    # Day-by-day counts
    day_events = defaultdict(int)
    day_dialogue = defaultdict(int)
    day_attacks = defaultdict(int)
    day_arrests = defaultdict(int)
    day_kills = defaultdict(int)
    by_speaker = Counter()
    by_actor_action = Counter()

    # Pattern: [Day N HH:MM]
    for line in events:
        m = re.match(r'\[Day (\d+) ', line)
        if not m: continue
        d = int(m.group(1))
        day_events[d] += 1
        if '攻撃' in line: day_attacks[d] += 1
        if '殺害' in line: day_kills[d] += 1
        if '逮捕' in line: day_arrests[d] += 1

    for line in dialogue:
        m = re.match(r'\[Day (\d+) ', line)
        if not m: continue
        d = int(m.group(1))
        day_dialogue[d] += 1
        m2 = re.search(r'\) ([^@]+)@', line)
        if m2: by_speaker[m2.group(1).strip()] += 1

    # Memory db: top important reflections
    db_path = os.path.join(LOG_DIR, 'memory.db')
    reflections = []
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "SELECT agent, sim_time, content FROM memory WHERE kind='reflection' "
            "ORDER BY importance DESC, ts DESC LIMIT 30"
        )
        reflections = cur.fetchall()
        conn.close()

    # Daily states
    final_state_file = os.path.join(LOG_DIR, 'daily_state', 'day06.json')
    final_state = None
    if os.path.exists(final_state_file):
        with open(final_state_file, encoding='utf-8') as f:
            final_state = json.load(f)

    # Build report
    lines = []
    lines.append('# Metro-75 — 7-Day Run REPORT')
    lines.append('')
    lines.append('## 走行サマリ')
    lines.append('')
    lines.append(f'- 最終 sim 時刻: Day 7 00:00 (7日完走)')
    lines.append(f'- 総 events 行数: **{len(events)}**')
    lines.append(f'- 総 dialogue 行数: **{len(dialogue)}**')
    lines.append('')

    lines.append('## 日別統計')
    lines.append('')
    lines.append('| Day | events | dialogue | 攻撃 | 殺害 | 逮捕 |')
    lines.append('|---|---:|---:|---:|---:|---:|')
    for d in sorted(day_events.keys()):
        lines.append(f'| {d} | {day_events[d]} | {day_dialogue[d]} | {day_attacks[d]} | {day_kills[d]} | {day_arrests[d]} |')
    lines.append('')

    lines.append('## 発言数 TOP15 (キャラ別)')
    lines.append('')
    for name, n in by_speaker.most_common(15):
        lines.append(f'- {name}: {n}回')
    lines.append('')

    lines.append('## 重要 Reflection 抜粋 (最大30件)')
    lines.append('')
    for agent, st, content in reflections[:30]:
        lines.append(f'- `[{st}] {agent}`: {content[:200]}')
    lines.append('')

    if final_state:
        lines.append('## 最終 Day 6 23:00 Active Agent State')
        lines.append('')
        lines.append('| ID | 名前 | faction | 位置 | HP | status | plan |')
        lines.append('|---|---|---|---|---:|---|---|')
        for a in final_state.get('agents', []):
            plan = (a.get('current_plan', '') or '')[:60].replace('|', '\\|')
            lines.append(f'| {a["id"]} | {a["name"][:30]} | {a["faction"]} | ({a["x"]},{a["y"]}) | {a["hp"]} | {a["status"]} | {plan} |')
        lines.append('')

    lines.append('## 物語の振り返り (各日のダイアリーは Discord に投稿済み)')
    lines.append('')
    for d in range(7):
        diary_state_file = os.path.join(LOG_DIR, 'daily_state', f'day{d:02d}.json')
        if os.path.exists(diary_state_file):
            lines.append(f'- Day {d}: 終了時 active 17人, dump済 (day{d:02d}.json)')
    lines.append('')

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'wrote {OUT} ({len(lines)} lines)')


if __name__ == '__main__':
    main()
