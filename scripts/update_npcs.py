"""Fill in personas for all 15 NPCs + reframe scenario events.

NEW SCENARIO PREMISE:
- アイスクリームトラックは **28分署の内偵車** (3日前から駐車中)
- Park 刑事中心に PM/PH の動きを監視
- ギャング側は「客が来ない」「同じ場所」で違和感を持ち始めてる
- Diaz 警部はオペ引継ぎ、慎重に
- Pomegranate 内部に警察協力者 (Marcus が嗅ぎつけ始める)
- Stone は事情を知らずに動く

Day 0 イベントもこの設定に合わせて書き換え。
"""
import json
import os

NPCS = {
    # ===== Police NPCs (4) =====
    'police_npc1': {
        'name': 'Officer David Chen',
        'faction': 'police', 'active': False, 'x': 128, 'y': 127,
        'persona': {
            'backstory': '巡査5年目、Park刑事の元相棒。アイスクリームトラック内偵オペのサポート要員。妻と2歳の娘あり。',
            'traits': ['実直', '忠実', '現場主義', '家庭思い'],
            'values': ['仲間を守る', '家族', '現場の判断'],
            'goals': ['内偵成功', 'Park をバックアップ', '無事帰宅'],
        },
    },
    'police_npc2': {
        'name': 'Officer Lisa Tanaka',
        'faction': 'police', 'active': False, 'x': 124, 'y': 128,
        'persona': {
            'backstory': '配属2年目、巡査。28分署で唯一の日系。地元高校から警察学校。',
            'traits': ['若い', '熱心', '不器用', '正義感'],
            'values': ['公平', '努力', '上司の信頼'],
            'goals': ['現場経験', '部署で認められる', '昇進'],
        },
    },
    'police_npc3': {
        'name': 'Sergeant Frank Wallace',
        'faction': 'police', 'active': False, 'x': 126, 'y': 124,
        'persona': {
            'backstory': '20年ベテランの部長刑事、皮肉屋。Diaz が来る前は実質的な署長代行。',
            'traits': ['シニカル', '実用主義', '老獪', '頑固'],
            'values': ['経験', '署のルーチン', '現場の常識'],
            'goals': ['退職まで波風立てない', 'Diaz の暴走抑制', '若手指導'],
        },
    },
    'police_npc4': {
        'name': 'Dispatcher Janet Rivera-Cole',
        'faction': 'police', 'active': False, 'x': 125, 'y': 126,
        'persona': {
            'backstory': '通信指令員10年。署内の全無線を聞いている。Rivera 巡査とは姓が同じだが他人。',
            'traits': ['冷静', '記憶力', '皮肉', '節度'],
            'values': ['正確さ', '中立', '情報管理'],
            'goals': ['シフト無事終了', '通信ミスゼロ', '緊急対応'],
        },
    },
    # ===== Pomegranate Mob NPCs (3) =====
    'pm_npc1': {
        'name': 'Trey "Slim" Coleman',
        'faction': 'gang_a', 'active': False, 'x': 34, 'y': 34,
        'persona': {
            'backstory': 'PM Hawk Set の運び屋。19歳。Marcus に拾われた。母は薬中で施設、弟は里親家庭。',
            'traits': ['若い', 'がむしゃら', '従順', '神経質'],
            'values': ['Marcus への忠誠', '弟への仕送り', 'Set 内昇格'],
            'goals': ['Marcus に認められる', '弟の学費', '生き延びる'],
        },
    },
    'pm_npc2': {
        'name': 'Reese "Eyes" Mathers',
        'faction': 'gang_a', 'active': False, 'x': 30, 'y': 30,
        'persona': {
            'backstory': 'Cobra Set の見張り役。元軍属だが除隊処分歴。Devon と幼馴染。',
            'traits': ['観察力', '寡黙', '冷静', '残酷'],
            'values': ['Devon との絆', 'プロ意識', '裏切り者の処分'],
            'goals': ['内偵者の特定', 'PH への報復準備', 'Devon を支える'],
        },
    },
    'pm_npc3': {
        'name': 'Junior "J-Roc" Booker',
        'faction': 'gang_a', 'active': False, 'x': 36, 'y': 30,
        'persona': {
            'backstory': '17歳、PM 入団3ヶ月の最年少。Marcus に憧れてる。学校はドロップアウト寸前。',
            'traits': ['若い', '威勢', '無謀', '見栄っ張り'],
            'values': ['名声', '兄貴分の認可', 'ストリートのリスペクト'],
            'goals': ['初仕事で認められる', 'Marcus の右腕', '銃を手に入れる'],
        },
    },
    # ===== Persimmon Hustlers NPCs (3) =====
    'ph_npc1': {
        'name': 'Damon "D-Block" Reeves',
        'faction': 'gang_b', 'active': False, 'x': 215, 'y': 215,
        'persona': {
            'backstory': 'Wolf Set の中堅、Antoine の従兄弟。28歳。元プロボクサー(2勝3敗)。',
            'traits': ['筋肉質', '短気', '家族主義', '直情'],
            'values': ['Antoine の血縁', 'PH の縄張り', '面子'],
            'goals': ['Antoine を護衛', 'PM への先制攻撃', 'Wolf Set 主導権'],
        },
    },
    'ph_npc2': {
        'name': 'Tasha "T-Bird" Whitmore',
        'faction': 'gang_b', 'active': False, 'x': 219, 'y': 219,
        'persona': {
            'backstory': 'Fox Set の末端、Keisha の妹分。22歳、看護学校中退。情報屋気質。',
            'traits': ['機転', '人懐こい', '計算高い', '若い'],
            'values': ['Keisha の信頼', '情報の対価', '生存'],
            'goals': ['情報網拡大', '上位昇格', '足を洗う準備'],
        },
    },
    'ph_npc3': {
        'name': 'Marcus "Lil-M" Holloway',
        'faction': 'gang_b', 'active': False, 'x': 213, 'y': 219,
        'persona': {
            'backstory': 'PH 兵隊、26歳。Wolf Set の鉄砲玉的役割。前科2犯、暴行・強盗。',
            'traits': ['粗暴', '従順', '寡黙', '忍耐'],
            'values': ['命令に従う', 'PH の名', '酒'],
            'goals': ['指示通り動く', '上の覚え良くする', '今夜の酒場行き'],
        },
    },
    # ===== Vigilante NPCs (2) =====
    'vig_npc1': {
        'name': 'Marcus "Doc" Brennan',
        'faction': 'vigilante', 'active': False, 'x': 95, 'y': 165,
        'persona': {
            'backstory': '元軍医、Stone の元上官。50代後半、退役後は街の野戦医。Stone の自警活動を医療面で支える。',
            'traits': ['冷静', '医者気質', '哲学的', '責任感'],
            'values': ['命の重さ', '友情', '医師倫理'],
            'goals': ['Stone を歯止めしつつ支える', '怪我人の治療', '不必要な殺しを防ぐ'],
        },
    },
    'vig_npc2': {
        'name': 'Rachel\'s friend - Marisol Ortega',
        'faction': 'vigilante', 'active': False, 'x': 105, 'y': 158,
        'persona': {
            'backstory': 'Rachel の高校時代からの親友、24歳。看護助手。自警団に巻き込まれた格好だが熱心。',
            'traits': ['純粋', '熱心', '他人事に動く', '迷い'],
            'values': ['Rachel との友情', '若い世代を守る', '正義'],
            'goals': ['Rachel をサポート', '街の子を救う', 'Stone の信頼を得る'],
        },
    },
    # ===== Civilians (3) =====
    'civ_priest': {
        'name': "Father Patrick O'Neill",
        'faction': 'civilian', 'active': False, 'x': 157, 'y': 87,
        'persona': {
            'backstory': 'St.Marys教会の神父、20年駐在。地区の良心、ギャングも警察も告解に来る。秘密を山ほど持ってる。',
            'traits': ['寛容', '聞き役', '謎めいた', '信仰深い'],
            'values': ['告解の秘密厳守', '地域の魂', '神'],
            'goals': ['街の対立を和らげる', '若者を救う', '中立保持'],
        },
    },
    'civ_bartender': {
        'name': 'Eddie "Quiet" Murphy',
        'faction': 'civilian', 'active': False, 'x': 99, 'y': 145,
        'persona': {
            'backstory': "O'Reilly's Bar のバーテン、12年勤務。元アイルランド系移民、義父から店を継いだ。あらゆる派閥の客を見てきた。",
            'traits': ['寡黙', '聞き上手', '中立', '皮肉'],
            'values': ['店の商売', '客の話の対価', 'プライバシー'],
            'goals': ['店を平和に営業', '面倒事は早めに察知', '酒の品揃え維持'],
        },
    },
    'civ_shopkeeper': {
        'name': 'Mrs. Hye-jin Park',
        'faction': 'civilian', 'active': False, 'x': 144, 'y': 127,
        'persona': {
            'backstory': 'コーナーストア店主、韓国系1世。アイスクリームトラックの真向かい。3日連続駐車に最初に気づいた人物。',
            'traits': ['注意深い', '心配性', '人情', '独立心'],
            'values': ['店の商売', '近所の安全', '家族 (息子はNYで医者)'],
            'goals': ['店を平和に営業', '異変を警察に報告', 'いつか帰国'],
        },
    },
}


def main():
    base = os.path.join(os.path.dirname(__file__), 'personas')
    for npc_id, data in NPCS.items():
        path = os.path.join(base, f'{npc_id}.json')
        d = {
            'id': npc_id,
            **data,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f'updated {npc_id}: {data["name"]}')


if __name__ == '__main__':
    main()
