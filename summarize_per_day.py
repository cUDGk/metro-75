"""Per-day comprehensive summary: events + dialogue + LLM narrative.

Posts each of 7 days as a separate Discord message.
"""
import sys, io, os, re, json, sqlite3, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sim import llm
from sim.diary import _post_discord

LOG_DIR = 'logs/resume_20260426_215201'


def filter_day(log_path, day):
    if not os.path.exists(log_path): return []
    out = []
    needle = f'[Day {day} '
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            if needle in line:
                out.append(line.strip())
    return out


def get_reflections_for_day(db_path, day):
    if not os.path.exists(db_path): return []
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT agent, sim_time, content FROM memory "
        "WHERE kind='reflection' AND sim_time LIKE ? ORDER BY ts",
        (f'Day {day}%',)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def extract_key_events(events):
    """Pick the most narratively important events: scripted events, plans, attacks, arrests, reflections-as-events."""
    keep = []
    for ev in events:
        if any(k in ev for k in ['[EVENT', '[PLAN]', '[REFLECT]', '攻撃', '殺害', '逮捕', '到着']):
            keep.append(ev)
    return keep[:30]


def faction_state_at_end(state_file):
    if not os.path.exists(state_file):
        return ''
    with open(state_file, encoding='utf-8') as f:
        d = json.load(f)
    by_fac = {}
    for a in d.get('agents', []):
        by_fac.setdefault(a['faction'], []).append(a)
    parts = []
    fac_names = {'police': '警察', 'gang_a': 'ガーネット', 'gang_b': 'ペルシカ',
                 'gang_c': 'コブラキラー', 'vigilante': '自警団'}
    for fac, ags in by_fac.items():
        n_alive = sum(1 for a in ags if a['status'] not in ('dead', 'arrested'))
        n_dead = sum(1 for a in ags if a['status'] == 'dead')
        n_arr = sum(1 for a in ags if a['status'] == 'arrested')
        parts.append(f"{fac_names.get(fac, fac)} {n_alive}/{len(ags)}"
                     + (f"(死{n_dead})" if n_dead else "")
                     + (f"(逮{n_arr})" if n_arr else ""))
    return ' / '.join(parts)


def generate_narrative(day, events, dialogue, reflections):
    """Use LLM to write a single-paragraph narrative summary of the day."""
    sample_e = events[-30:]
    sample_d = dialogue[-15:]
    sample_r = [f'{a}: {c[:120]}' for (a, _, c) in reflections[-10:]]

    system = ('あなたは「メトロ・トリビューン」紙の記者。**日本語のみ**で書く (英語/ロシア語禁止)。'
              '都市の犯罪ドラマを冷徹に観察。短く鋭く。')
    user = f"""Day {day} の出来事を 250〜350字 (日本語) で要約せよ。

要件:
- **日本語のみ** (英単語、ロシア語、その他言語禁止)
- 1段落、新聞コラム調
- 派閥間の動き、誰が何をしたか、街の空気
- 具体的な人名 (略称OK: ホーク, ディアス, JAP28, etc.) と場所を含めて

### Day {day} の主要 events (最大30件):
{chr(10).join(sample_e)}

### Day {day} の会話 (最大15件):
{chr(10).join(sample_d)}

### Day {day} の Reflection (最大10件):
{chr(10).join(sample_r)}

250〜350字で日本語要約。"""
    try:
        return llm.simple_prompt(system, user, max_tokens=600, temperature=0.7)
    except Exception as e:
        return f'(narrative LLM error: {e})'


def main():
    db = os.path.join(LOG_DIR, 'memory.db')
    events_path = os.path.join(LOG_DIR, 'events.log')
    dialogue_path = os.path.join(LOG_DIR, 'dialogue.log')

    for day in range(7):
        print(f'=== Day {day} ===')
        events = filter_day(events_path, day)
        dialogue = filter_day(dialogue_path, day)
        reflections = get_reflections_for_day(db, day)
        key = extract_key_events(events)

        # Faction state at end of day
        state_file = os.path.join(LOG_DIR, 'daily_state', f'day{day:02d}.json')
        fac_str = faction_state_at_end(state_file)

        narrative = generate_narrative(day, events, dialogue, reflections)
        print(f'  narrative: {narrative[:80]}...')

        # Pick top 5 events + top 5 dialogue
        sample_events = key[-8:] if key else events[-8:]
        sample_dialog = dialogue[-8:] if dialogue else []

        msg = (
            f'# 📰 Metro-75 — Day {day} 振り返り\n\n'
            f'**ナラティブ**: {narrative}\n\n'
            f'## 📌 主な出来事\n'
            + '\n'.join(f'- `{e[:180]}`' for e in sample_events) + '\n\n'
            f'## 💬 主な会話\n'
            + '\n'.join(f'- `{d[:180]}`' for d in sample_dialog) + '\n\n'
            f'## 🏁 終了時 ({fac_str})\n'
            f'events {len(events)} / dialogue {len(dialogue)} / reflection {len(reflections)}'
        )

        # Snapshot at H20 of that day
        snap_path = os.path.join(LOG_DIR, 'snapshots', f'D{day:02d}_H20.png')
        if not os.path.exists(snap_path):
            import glob
            snaps = sorted(glob.glob(os.path.join(LOG_DIR, 'snapshots', f'D{day:02d}_*.png')))
            snap_path = snaps[-1] if snaps else None

        ok = _post_discord(msg, snap_path)
        print(f'  posted: {ok} (msg {len(msg)} chars)')
        time.sleep(2)  # avoid Discord rate limit


if __name__ == '__main__':
    main()
