# -*- coding: utf-8 -*-
"""Generates 30 persona JSON files (REAL RUN — fruit/animal gang names).

Factions:
- 28th Precinct Police: 10 (6 active + 4 inactive)
- "Pomegranate Mob" (gang_a, blue, NW): 7
    - Hawk set: 4 (2 active + 2 inactive)
    - Cobra set: 3 (2 active + 1 inactive)
- "Persimmon Hustlers" (gang_b, red, SE): 6
    - Wolf set: 3 (2 active + 1 inactive)
    - Fox set: 3 (1 active + 2 inactive)
- Vigilantes "Stone Group": 4 (2 active + 2 inactive)
- Civilians: 3 (all inactive)
"""
from __future__ import annotations
import json
import os, sys

ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ROOT, '..'))
from sim.world import World

MAP = World.load(os.path.join(ROOT, '..', 'map', 'metro.json'))
LM = MAP.landmarks

PERSONAS: list[dict] = []


def add(**kw):
    PERSONAS.append(kw)


# ============== POLICE (28th Precinct) ==============
px, py = LM['police_station']
add(
    id='police_diaz',
    name='Captain Maria Diaz',
    faction='police', active=True,
    x=px, y=py,
    persona={
        'backstory': '28分署の新任警部、3週間前に着任。元殺人課刑事。クリーンな経歴、政治的に上昇志向。',
        'traits': ['権威的', '慎重', '規則重視', '鋭い'],
        'values': ['法の支配', 'キャリア', '世論操作'],
        'goals': ['ギャング暴力削減', '世間注目', '署内汚職特定'],
    }
)
add(
    id='police_hanson',
    name='Det. Frank Hanson',
    faction='police', active=True,
    x=px + 2, y=py,
    persona={
        'backstory': '22年目のベテラン刑事。離婚歴あり、酒に溺れがち。地元の隅々を熟知、貸し借りが多い。',
        'traits': ['シニカル', '経験豊富', '世故', '観察眼'],
        'values': ['古参パートナーへの忠義', '実用主義'],
        'goals': ['無事に定年を迎える', '新任警部の意図を読む'],
    }
)
add(
    id='police_park',
    name='Det. Jenny Park',
    faction='police', active=True,
    x=px - 2, y=py,
    persona={
        'backstory': '麻薬課から最近異動、6年目。野心的で目が鋭い。夫は検事。',
        'traits': ['駆動的', '分析的', '原則的'],
        'values': ['正義', '証拠主義'],
        'goals': ['キャリアを作る重大事件を立件', '麻薬の供給ルート解明'],
    }
)
add(
    id='police_rivera',
    name='Officer Luis Rivera',
    faction='police', active=True,
    x=px, y=py + 2,
    persona={
        'backstory': '巡回3年目。この街で育った。家族は今もPersimmons縄張りに住んでる。',
        'traits': ['友好的', '葛藤', '街の知識豊富'],
        'values': ['家族', 'コミュニティ'],
        'goals': ['地元を守る', '幼馴染を逮捕する状況を避ける'],
    }
)
add(
    id='police_okoye',
    name='Officer Amara Okoye',
    faction='police', active=True,
    x=px + 1, y=py - 1,
    persona={
        'backstory': '巡回4年目。元アスリート、四角四面。Pomegranateメンバーを過去に3回逮捕。',
        'traits': ['身体派', '直球', '頑固'],
        'values': ['公平さ', '物理的勇気'],
        'goals': ['Pomegranateを潰す', 'いずれ刑事に昇進'],
    }
)
add(
    id='police_schwartz',
    name='Sgt. Dan Schwartz',
    faction='police', active=True,
    x=px - 1, y=py + 1,
    persona={
        'backstory': '15年目、デスクサージェント。署内の噂を握る。書類の埋蔵庫。',
        'traits': ['お喋り', '内情通', '怠惰だが有能'],
        'values': ['オフィス政治', '円滑運営'],
        'goals': ['年金まで波風立てず', '警部のご機嫌取り'],
    }
)
add(id='police_npc1', name='Officer Chen', faction='police', active=False, x=px + 3, y=py + 2)
add(id='police_npc2', name='Officer Baker', faction='police', active=False, x=px - 3, y=py - 2)
add(id='police_npc3', name='Officer Kim', faction='police', active=False, x=px + 2, y=py + 3)
add(id='police_npc4', name='Officer Bell', faction='police', active=False, x=px - 2, y=py + 3)


# ============== POMEGRANATE MOB (gang_a, NW) ==============
# Team: Pomegranate Mob (PM). Sets: Hawk Set / Cobra Set.
ax, ay = LM['gang_a_hideout']
add(
    id='pm_hawk_marcus',
    name='Marcus "Hawk" Thompson',
    faction='gang_a', active=True,
    x=ax, y=ay,
    persona={
        'backstory': 'Pomegranate Mob、Hawk Setのリーダー、38歳。22年に従兄弟が撃たれてから縄張りを統括。Hawk Setは PM の頭脳役。',
        'traits': ['計算高い', '猜疑心強い', 'カリスマ', '追い詰められたら凶暴'],
        'values': ['忠義', 'リスペクト', '縄張り'],
        'goals': ['Persimmonsから縄張り防衛', '組織内のスニッチ特定', '東への進出機会狙い'],
    }
)
add(
    id='pm_hawk_tyrone',
    name='Tyrone "T-Hawk" Jackson',
    faction='gang_a', active=True,
    x=ax + 1, y=ay,
    persona={
        'backstory': 'Hawk Setの番頭格、30歳。日々の売り捌きを管理。組織に隠してる息子がいる。',
        'traits': ['忠実', '抜け目ない', '不安持ち'],
        'values': ['(隠れた)家族', 'Marcusへの忠誠'],
        'goals': ['オペレーションを円滑に', 'いつか息子を脱出させる'],
    }
)
add(
    id='pm_cobra_devon',
    name='Devon "D-Cobra" Walker',
    faction='gang_a', active=True,
    x=ax - 1, y=ay + 1,
    persona={
        'backstory': 'Cobra Set所属、24歳、短気。ストリートで売り子。Persimmonsに弟を殺されて以来怒りが消えない。',
        'traits': ['衝動的', '攻撃的', 'Marcusに忠実'],
        'values': ['復讐', 'ストリート上の評判'],
        'goals': ['弟の復讐', 'Marcusへ価値を証明'],
    }
)
add(
    id='pm_cobra_lisa',
    name='Lisa "Lady Cobra" Watkins',
    faction='gang_a', active=True,
    x=ax, y=ay - 1,
    persona={
        'backstory': 'Cobra Setの会計係、32歳。バー経由で資金洗浄。冷静沈着。',
        'traits': ['計算高い', '慎重', '統制的'],
        'values': ['利益', '長期的生存'],
        'goals': ['資金洗浄', 'ヒートを呼ぶ街路暴力を最小化'],
    }
)
add(id='pm_npc1', name='Jamal "Talon"', faction='gang_a', active=False, x=ax + 2, y=ay)
add(id='pm_npc2', name='Rico "Strike"', faction='gang_a', active=False, x=ax - 2, y=ay + 1)
add(id='pm_npc3', name='Tiny "Fang"', faction='gang_a', active=False, x=ax + 1, y=ay + 2)


# ============== PERSIMMON HUSTLERS (gang_b, SE) ==============
# Team: Persimmon Hustlers (PH). Sets: Wolf Set / Fox Set.
bx, by = LM['gang_b_hideout']
add(
    id='ph_wolf_malik',
    name='Malik "Big Wolf" Coleman',
    faction='gang_b', active=True,
    x=bx, y=by,
    persona={
        'backstory': 'Persimmon Hustlers、Wolf Setのヘッド、41歳。古参の規律派。Marcus Thompson とは10代からの宿敵。',
        'traits': ['辛抱強い', '戦略的', '侮辱には冷酷'],
        'values': ['規律', 'Persimmons の遺産', '縄張り'],
        'goals': ['Pomegranateを東通路から押し出す', '逮捕回避', '後継者育成'],
    }
)
add(
    id='ph_wolf_antoine',
    name='Antoine "Twon Wolf" Banks',
    faction='gang_b', active=True,
    x=bx + 1, y=by,
    persona={
        'backstory': 'Wolf Set所属、26歳、闘員。暴行で4年入獄歴あり。仕事を楽しみすぎる。',
        'traits': ['残忍', '忠実', '思考鈍'],
        'values': ['Malikの命令', 'リスペクト'],
        'goals': ['拳で問題解決', '二度と刑務所には行かない'],
    }
)
add(
    id='ph_fox_keisha',
    name='Keisha "K-Fox" Morrison',
    faction='gang_b', active=True,
    x=bx - 1, y=by,
    persona={
        'backstory': 'Fox Setのリーダー、28歳。Malikの愛人で実質No.2。多くが思うより遥かに賢い。',
        'traits': ['観察力', '操作的', '過小評価される'],
        'values': ['自分のポジション', '長期戦'],
        'goals': ['Malik失脚時のトップ取り', 'リーク特定'],
    }
)
add(id='ph_npc1', name='Rasheed "Howl"', faction='gang_b', active=False, x=bx + 2, y=by)
add(id='ph_npc2', name='Jay "Bite"', faction='gang_b', active=False, x=bx - 2, y=by + 1)
add(id='ph_npc3', name='Darnell "Shadow"', faction='gang_b', active=False, x=bx, y=by + 2)


# ============== VIGILANTES (Stone Group, SW) ==============
add(
    id='vig_stone',
    name='Frank "Stone" Callahan',
    faction='vigilante', active=True,
    x=LM['apartment_0'][0], y=LM['apartment_0'][1],
    persona={
        'backstory': '元海兵隊、55歳。2年前ギャングの流れ弾で娘を喪失。Watch Group を立ち上げて何度も一線を越えてる。',
        'traits': ['規律的', '怒り', 'パラノイア', '計算的'],
        'values': ['復讐', '無辜の保護', '秩序'],
        'goals': ['娘を撃った犯人特定', '警察が動かないなら自分が落とし前', 'グループ維持'],
    }
)
add(
    id='vig_rachel',
    name='Rachel Nguyen',
    faction='vigilante', active=True,
    x=LM['apartment_0'][0] + 1, y=LM['apartment_0'][1],
    persona={
        'backstory': '29歳、市立病院の看護師。被害者を診てきてStoneに合流。内心は疑問あり。',
        'traits': ['共感的', '葛藤', '勇敢'],
        'values': ['治癒', '正義', 'Stoneの信頼'],
        'goals': ['医療面でサポート', 'グループの行き過ぎを問う'],
    }
)
add(id='vig_npc1', name='Carl', faction='vigilante', active=False, x=LM['apartment_0'][0] - 1, y=LM['apartment_0'][1])
add(id='vig_npc2', name='Maddie', faction='vigilante', active=False, x=LM['apartment_0'][0], y=LM['apartment_0'][1] + 1)


# ============== CIVILIANS ==============
add(id='civ_priest', name='Father O\'Neill', faction='civilian', active=False, x=LM['st_marys_church'][0], y=LM['st_marys_church'][1])
add(id='civ_bartender', name='Eddie at O\'Reilly\'s', faction='civilian', active=False, x=LM['o_reillys_bar'][0], y=LM['o_reillys_bar'][1])
add(id='civ_shopkeeper', name='Mr. Chen (corner store)', faction='civilian', active=False, x=LM['shop_0'][0], y=LM['shop_0'][1])


assert len(PERSONAS) == 30, f'expected 30, got {len(PERSONAS)}'
print(f'Generated {len(PERSONAS)} personas (15 active + 15 inactive)')
# Clean old persona files first
import glob
for old in glob.glob(os.path.join(ROOT, '*.json')):
    os.remove(old)
for p in PERSONAS:
    path = os.path.join(ROOT, f'{p["id"]}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(p, f, indent=2, ensure_ascii=False)
print('Wrote JSONs (gang naming: PM Hawks/Cobras, PH Wolves/Foxes)')
