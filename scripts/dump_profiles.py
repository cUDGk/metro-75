"""Dump all 30 personas + scenario into a single readable Markdown file."""
import sys, io, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

files = sorted(glob.glob('personas/*.json'))
factions = {}
for f in files:
    with open(f, encoding='utf-8') as fh:
        d = json.load(fh)
    factions.setdefault(d['faction'], []).append(d)

faction_order = ['police', 'gang_a', 'gang_b', 'gang_c', 'vigilante', 'civilian', 'family', 'drifter']
faction_titles = {
    'police':    '警察 — 28分署 (法執行)',
    'gang_a':    'ザクロ団 (Pomegranate Mob) — Hawk Set / Cobra Set',
    'gang_b':    '桃団 (Peach Hustlers) — Wolf Set / Fox Set / Bear Set',
    'gang_c':    'マンゴー団 (通称コブラキラー) — 独立系・経済犯罪。日系系',
    'vigilante': '自警団 (ストーン組) — 元軍人の私的執行者',
    'civilian':  '市民 (主要NPC: 神父・バーテン・店主)',
    'family':    '家族 (アパート住人)',
    'drifter':   '流れ者 (一時滞在: ホームレス・記者・タクシー・etc)',
}

total = sum(len(v) for v in factions.values())
active = sum(1 for v in factions.values() for a in v if a.get('active'))
lines = []
lines.append(f'# Metro-75 — 全 {total}人 NPC リスト')
lines.append('')
lines.append(f'**アクティブ**: {active}人 (LLM 駆動・自律行動)  /  **NPC**: {total - active}人 (背景キャラ・固定座標)')
lines.append('')
lines.append('シナリオ詳細は `SCENARIO.md` 参照、要件・技術構成は `REQUIREMENTS.md` 参照。')
lines.append('')
lines.append('')
lines.append('---')
lines.append('')

for fac in faction_order:
    if fac not in factions: continue
    lines.append(f'## {faction_titles[fac]}')
    lines.append('')
    agents = sorted(factions[fac], key=lambda a: (not a.get('active'), a['id']))
    for d in agents:
        active_mark = '★ ACTIVE' if d.get('active') else '— NPC'
        gender_disp = {'male': '男', 'female': '女', 'other': 'その他'}.get(d.get('gender', ''), '?')
        lines.append(f'### `{d["id"]}` {d["name"]} [{active_mark}]')
        lines.append('')
        if d.get('alias'):
            lines.append(f'- **略称**: {d["alias"]}')
        lines.append(f'- **性別**: {gender_disp} / **役割**: {d.get("role", "—")}')
        lines.append(f'- **位置**: ({d["x"]}, {d["y"]})')
        p = d.get('persona', {})
        lines.append(f'- **背景**: {p.get("backstory", "—")}')
        lines.append(f'- **性格**: {", ".join(p.get("traits", []))}')
        lines.append(f'- **価値観**: {", ".join(p.get("values", []))}')
        lines.append(f'- **目的**: {", ".join(p.get("goals", []))}')
        lines.append('')
    lines.append('')

with open('NPCS.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'wrote NPCS.md ({len(lines)} lines)')
