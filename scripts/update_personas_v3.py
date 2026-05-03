"""Final pass:
- Rename Mango members (drop Japanese except JAP28). JAP28 itself simplified.
- Add gender + role to ALL 60 personas.
"""
import json, os, glob

# ===== Mango members rename (non-Japanese except JAP28) =====
MANGO_REPLACEMENTS = {
    'mango_jap28': {
        'name': 'JAP28',
        'alias': 'JAP28',
        'gender': 'male',
        'role': 'コブラキラー若頭 (経済担当)',
        'persona_overrides': {
            'backstory': '日系3世、26歳。本名は山中だが街では「JAP28」しか名乗らない。父はLA出身の元銀行員、母は日系移民3世。地元高校の数学優等生→経済犯罪に染まる。アントワーヌ・バンクス (ペルシカ Wolf) のいとこを2年前に絞めて以降、ガーネットのコブラ Set からも目を付けられている。タフ、気性は荒い、それでも金勘定だけは冷静。',
        },
    },
    'mango_boss': {
        'name': 'ジョセフ・"アンクル・ジョー"・カラブレーゼ',
        'alias': 'アンクル・ジョー',
        'gender': 'male',
        'role': 'コブラキラー親分 / カラブレーゼ商会CEO',
        'persona_overrides': {
            'backstory': '60歳、イタリア系3世。コブラキラーの親分。元証券マン (1990年代に内部取引で5年食らった)。出所後にこの街でカラブレーゼ商会というフロント企業を立てた。表向きは商社、裏ではマネロン/詐欺/高利貸し。コブラ Set との抗争はジョーが10年前に煽られた古傷から。',
        },
    },
    'mango_npc1': {
        'name': 'ケニー・"ストレイ"・ジャクソン',
        'alias': 'ストレイ',
        'gender': 'male',
        'role': 'コブラキラー用心棒・運び屋',
        'persona_overrides': {
            'backstory': '32歳、JAP28の幼馴染。アフリカ系アメリカ人。コブラキラーの運び屋兼用心棒。元プロMMAファイター、3勝5敗で引退。',
        },
    },
    'mango_npc2': {
        'name': 'ナターシャ・"クィーン"・パブロワ',
        'alias': 'クィーン',
        'gender': 'female',
        'role': 'カラブレーゼ商会会計責任者 / アンクル・ジョーの愛人',
        'persona_overrides': {
            'backstory': '34歳、ロシア系移民2世。カラブレーゼ商会の会計担当。ジョーの愛人で実質的なナンバー2。表面は完璧な経理、裏は完全な腹黒。',
        },
    },
    'mango_npc3': {
        'name': 'リッキー・"ロゴ"・ガルシア',
        'alias': 'リッキー',
        'gender': 'male',
        'role': 'カラブレーゼ商会偽装請求書担当',
        'persona_overrides': {
            'backstory': '24歳、メキシコ系2世。カラブレーゼ商会の偽装請求書担当。元会計士見習い。母は地元の家政婦、家計を支える。',
        },
    },
}

# ===== Gender + role for everyone else =====
GENDER_ROLE = {
    # Police
    'police_diaz':     ('female', '28分署 警部 (新任)'),
    'police_park':     ('female', '28分署 刑事 (内偵オペ現場指揮)'),
    'police_rivera':   ('male',   '28分署 巡査'),
    'police_hanson':   ('male',   '28分署 刑事'),
    'police_okoye':    ('female', '28分署 巡査'),
    'police_schwartz': ('male',   '28分署 部長刑事'),
    'police_npc1':     ('male',   '28分署 巡査 (パクの元相棒)'),
    'police_npc2':     ('female', '28分署 巡査 (新人)'),
    'police_npc3':     ('male',   '28分署 部長刑事 (古参)'),
    'police_npc4':     ('female', '28分署 通信指令員'),

    # Garnet
    'pm_hawk_marcus':  ('male',   'ガーネット Hawk Set リーダー'),
    'pm_hawk_tyrone':  ('male',   'ガーネット Hawk Set 二番手'),
    'pm_cobra_devon':  ('male',   'ガーネット Cobra Set 構成員 (短気・短期売り子)'),
    'pm_cobra_lisa':   ('female', 'ガーネット Cobra Set 女幹部'),
    'pm_npc1':         ('male',   'ガーネット Hawk 末端・運び屋 (19歳)'),
    'pm_npc2':         ('male',   'ガーネット Cobra 見張り'),
    'pm_npc3':         ('male',   'ガーネット末端 (17歳の新参)'),

    # Persica
    'ph_wolf_antoine': ('male',   'ペルシカ Wolf Set 構成員 (狙われる中心人物)'),
    'ph_wolf_malik':   ('male',   'ペルシカ Wolf Set リーダー'),
    'ph_fox_keisha':   ('female', 'ペルシカ Fox Set リーダー'),
    'ph_npc1':         ('male',   'ペルシカ Wolf 中堅 (アントワーヌの従兄弟)'),
    'ph_npc2':         ('female', 'ペルシカ Fox 末端・情報屋'),
    'ph_npc3':         ('male',   'ペルシカ Wolf 兵隊'),
    'ph_bear_jamaal':  ('male',   'ペルシカ Bear Set リーダー'),
    'ph_bear_kwame':   ('male',   'ペルシカ Bear Set 二番手 (元軍人)'),

    # Vigilante
    'vig_stone':       ('male',   '自警団リーダー (元軍人)'),
    'vig_rachel':      ('female', '自警団二番手'),
    'vig_npc1':        ('male',   '自警団・元軍医 (メディック)'),
    'vig_npc2':        ('female', '自警団・看護助手'),

    # Civilians
    'civ_priest':      ('male',   '神父 (セント・メアリー教会)'),
    'civ_bartender':   ('male',   'バーテンダー (オライリーズ)'),
    'civ_shopkeeper':  ('female', 'コーナーストア店主'),

    # Families — Morales (apartment_riverside)
    'fam_morales_dad':       ('male',   '父親 (建設現場 日雇い職長)'),
    'fam_morales_mom':       ('female', '母親 (クリーニング店勤務)'),
    'fam_morales_daughter':  ('female', '娘 (ジェファーソン高1年・理数系特待)'),

    # Families — Oconnell (apartment_central)
    'fam_oconnell_dad':      ('male',   '父親 (配管工 / オライリーズ常連)'),
    'fam_oconnell_wife':     ('female', '母親 (中央市場レジ係 / 噂好き)'),
    'fam_oconnell_son':      ('male',   '息子 (ジェファーソン高3年・野球部キャプテン)'),

    # Families — Park (apartment_eastside)
    'fam_park_grandma':      ('female', '祖母 (脳梗塞後遺症・半身麻痺)'),
    'fam_park_daughter':     ('female', '母親 (中央図書館司書・シングルマザー)'),
    'fam_park_kid':          ('female', '娘 (リンカーン小5年・絵が上手)'),

    # Families — Johnson (apartment_southlake)
    'fam_johnson_dad':       ('male',   '父親 (湾岸戦争退役軍人・元バス運転手)'),
    'fam_johnson_wife':      ('female', '母親 (聖歌隊長・元小学校教師)'),
    'fam_johnson_son':       ('male',   '息子 (コミュニティカレッジ生・法律志望)'),

    # Families — Silva (apartment_north_grove)
    'fam_silva_dad':         ('male',   '父親 (ガス・ノース勤務・ブラジル系)'),
    'fam_silva_wife':        ('female', '母親 (ベビーシッター)'),
    'fam_silva_kid':         ('male',   '息子 (リンカーン小2年・サッカー大好き)'),

    # Drifters
    'drift_homeless_jim':         ('male',   'ホームレス (ベトナム退役軍人)'),
    'drift_addict_riley':         ('male',   '薬物依存 (元バンドマン)'),
    'drift_tourist_emma':         ('female', 'フリーランス・ジャーナリスト (内偵車取材)'),
    'drift_truck_driver_carl':    ('male',   '長距離トラック運転手'),
    'drift_runaway_destiny':      ('female', '家出娘 (17歳)'),
    'drift_preacher_silas':       ('male',   '流浪の説教師'),
    'drift_taxi_drik':            ('male',   'タクシー運転手 (ロシア系移民2世)'),
    'drift_busker_zeke':          ('male',   'ストリート・ミュージシャン'),
}


def main():
    base = os.path.join(os.path.dirname(__file__), 'personas')

    # Step 1: Mango replacements
    for pid, repl in MANGO_REPLACEMENTS.items():
        path = os.path.join(base, f'{pid}.json')
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        d['name'] = repl['name']
        d['alias'] = repl['alias']
        d['gender'] = repl['gender']
        d['role'] = repl['role']
        if 'persona_overrides' in repl:
            d['persona'].update(repl['persona_overrides'])
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f'  M  {pid:30s} → {repl["name"]} ({repl["gender"]}, {repl["role"]})')

    # Step 2: Add gender + role to everyone else
    for pid, (gender, role) in GENDER_ROLE.items():
        path = os.path.join(base, f'{pid}.json')
        if not os.path.exists(path):
            print(f'  ! missing {pid}'); continue
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        d['gender'] = gender
        d['role'] = role
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f'  G  {pid:30s} | {gender:6s} | {role}')

    # Verify
    files = glob.glob(os.path.join(base, '*.json'))
    missing = []
    for f in files:
        with open(f, encoding='utf-8') as fh:
            d = json.load(fh)
        if 'gender' not in d:
            missing.append(d['id'])
    if missing:
        print(f'\n!! Missing gender/role for: {missing}')
    else:
        print(f'\nAll {len(files)} personas have gender + role.')


if __name__ == '__main__':
    main()
