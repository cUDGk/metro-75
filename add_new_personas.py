"""Add Mango Mob (incl JAP28), Peach Bear Set 3rd set, families, drifters."""
import json, os

# ===== Mango Mob (gang_c, 通称コブラキラー) =====
MANGO = {
    'mango_jap28': {
        'name': 'タツミ "JAP28" 山中',
        'alias': 'JAP28',
        'faction': 'gang_c', 'active': True, 'x': 32, 'y': 217,
        'persona': {
            'backstory': '日系3世、26歳。マンゴー団 (通称コブラキラー) の若頭。父はLA出身の元銀行員、母は和歌山系。地元高校の数学優等生→経済犯罪に染まる。Antoine Banks (桃団 Wolf) のいとこを2年前に絞めて以降、ザクロ団のコブラ Set からも目を付けられている。タフ、気性は荒い、それでも金勘定だけは冷静。',
            'traits': ['短気', 'タフ', '計算高い', '日系の誇り', '無謀'],
            'values': ['金', 'マンゴー団の独立', '言葉より数字'],
            'goals': ['ジョセフ・タカハシ親分の右腕として認められる', '架空会社経由で月$50K回す', 'コブラ Set との抗争を終結 or 全壊', '日系コミュニティを巻き込まない'],
        },
    },
    'mango_boss': {
        'name': 'ジョセフ "アンクル・ジョー" 高橋',
        'alias': 'アンクル・ジョー',
        'faction': 'gang_c', 'active': True, 'x': 33, 'y': 215,
        'persona': {
            'backstory': '60歳、マンゴー団の親分。元証券マン (1990年代に内部取引で5年食らった)。出所後にこの街でマンゴー・ホールディングスというフロント企業を立てた。表向きは商社、裏ではマネロン/詐欺/高利貸し。コブラ Set との抗争はジョーが10年前に煽られた古傷から。',
            'traits': ['沈着', '老獪', '体調不良', '非情'],
            'values': ['組の存続', '金の流れ', '日系の体面'],
            'goals': ['JAP28に組を引き継がせる', 'コブラ Set への決着', 'FBI捜査の遮断'],
        },
    },
    'mango_npc1': {
        'name': 'ケニー "ストレイ" 中島',
        'alias': 'ストレイ',
        'faction': 'gang_c', 'active': False, 'x': 35, 'y': 219,
        'persona': {
            'backstory': '32歳、JAP28の幼馴染。マンゴー団の運び屋兼用心棒。元プロMMAファイター、3勝5敗で引退。',
            'traits': ['筋肉質', 'ぶっきらぼう', '忠実', '後先考えない'],
            'values': ['JAP28との義理', '金', '酒場の喧嘩'],
            'goals': ['JAP28を護衛', 'ザクロのコブラを潰す', '金で家を買う'],
        },
    },
    'mango_npc2': {
        'name': 'メアリー "クィーン" 林',
        'alias': 'クィーン',
        'faction': 'gang_c', 'active': False, 'x': 30, 'y': 215,
        'persona': {
            'backstory': '34歳、マンゴー・ホールディングスの会計担当。台湾系2世。ジョーの愛人で実質的なナンバー2。表面は完璧な経理、裏は完全な腹黒。',
            'traits': ['冷徹', '頭脳派', '美貌', '本音を見せない'],
            'values': ['数字', '権力', 'ジョー後の自分のポジション'],
            'goals': ['帳簿の完璧管理', 'JAP28の上に立つ', '裏切り者を内部で見つける'],
        },
    },
    'mango_npc3': {
        'name': 'リッキー "リッキー・ロゴ" 朴',
        'alias': 'リッキー',
        'faction': 'gang_c', 'active': False, 'x': 42, 'y': 207,
        'persona': {
            'backstory': '24歳、韓国系。マンゴー・ホールディングスの偽装請求書担当。元会計士見習い。母はヘジン婦人 (角の店主) の遠い親戚。',
            'traits': ['真面目', '小心', '金持ちごっこ', '優秀'],
            'values': ['母への仕送り', '金', '安全'],
            'goals': ['足を洗うタイミングを伺う', '韓国系コミュニティとの繋がり維持', '逮捕されない'],
        },
    },
}

# ===== Peach 3rd set: Bear Set =====
PEACH_BEAR = {
    'ph_bear_jamaal': {
        'name': 'ジャマール "ベア" ライト',
        'alias': 'ベア',
        'faction': 'gang_b', 'active': False, 'x': 215, 'y': 215,
        'persona': {
            'backstory': '桃団 Bear Set のリーダー、35歳。マリク (Wolf) より年上。Bear Set は元プロボクサー/格闘家系の用心棒部隊で人数は少ないが筋金入り。',
            'traits': ['筋肉', '統率力', '沈着', '保守的'],
            'values': ['桃団内の調和', 'Bear Set 隊員', '伝統的な街の掟'],
            'goals': ['Wolf Set と Fox Set の対立調停', 'Bear Set の人数増強', '若手の暴走抑止'],
        },
    },
    'ph_bear_kwame': {
        'name': 'クワメ "アイアン" ジョーンズ',
        'alias': 'アイアン',
        'faction': 'gang_b', 'active': False, 'x': 219, 'y': 213,
        'persona': {
            'backstory': '桃団 Bear Set 二番手、29歳。元軍隊 (アフガン3年)、PTSD気味だがその分使える戦闘員。ジャマールの右腕。',
            'traits': ['静か', '戦闘的', 'PTSD', '寡黙'],
            'values': ['ジャマールの命令', '実戦経験', '酒'],
            'goals': ['Bear Set の出番を作る', '心の安らぎ', '抗争で活躍'],
        },
    },
}

# ===== Families (5 units, 15 people) =====
FAMILIES = {
    # Apartment riverside (51, 121)
    'fam_morales_dad': {
        'name': 'ヘクター・モラレス',
        'alias': 'ヘクター',
        'faction': 'family', 'active': False, 'x': 51, 'y': 121,
        'persona': {'backstory': 'メキシコ系移民2世、42歳。建設現場の日雇い職長。妻と中学生の娘と3歳の息子と暮らす。', 'traits': ['誠実', '寡黙', '家族第一'], 'values': ['家族', '労働', '近所付き合い'], 'goals': ['家族を養う', '子供を進学させる', '日雇いから正社員へ']},
    },
    'fam_morales_mom': {
        'name': 'マリア・モラレス',
        'alias': 'マリア・モラレス',
        'faction': 'family', 'active': False, 'x': 51, 'y': 122,
        'persona': {'backstory': '38歳、近所のクリーニング店勤務。ヘクターの妻。教会に毎週通う。', 'traits': ['信心深い', '節約家', '心配性'], 'values': ['家族', '神', '近所の評判'], 'goals': ['家計安定', '娘を大学へ', '息子を健康に育てる']},
    },
    'fam_morales_daughter': {
        'name': 'ソフィア・モラレス',
        'alias': 'ソフィア',
        'faction': 'family', 'active': False, 'x': 50, 'y': 121,
        'persona': {'backstory': '13歳、ジェファーソン高 (jefferson_high) 1年生。理数系特待。', 'traits': ['真面目', '内気', '好奇心'], 'values': ['勉強', '友達', '将来'], 'goals': ['奨学金', '大学進学', 'プログラマーになる']},
    },
    # Apartment central (101, 181)
    'fam_oconnell_dad': {
        'name': 'ショーン・オコンネル',
        'alias': 'ショーン',
        'faction': 'family', 'active': False, 'x': 101, 'y': 181,
        'persona': {'backstory': 'アイルランド系3世、49歳。オライリーズ酒場の常連、配管工。妻は5年前に病死、再婚した。', 'traits': ['酒好き', '気のいい', '昔気質'], 'values': ['ビール', '昔の街', '常連仲間'], 'goals': ['仕事で生活', '酒場の常連を続ける', '再婚生活を保つ']},
    },
    'fam_oconnell_wife': {
        'name': 'パトリシア "パティ" オコンネル',
        'alias': 'パティ',
        'faction': 'family', 'active': False, 'x': 102, 'y': 181,
        'persona': {'backstory': '46歳、ショーンの再婚相手。中央市場 (central_market) のレジ係。元ウェイトレス。', 'traits': ['賑やか', '世話焼き', '噂好き'], 'values': ['家庭', '街の噂', '仲間'], 'goals': ['市場の店長になる', '街の出来事を全部知る', 'ショーンの飲酒控えさせる']},
    },
    'fam_oconnell_son': {
        'name': 'コナー・オコンネル',
        'alias': 'コナー',
        'faction': 'family', 'active': False, 'x': 100, 'y': 181,
        'persona': {'backstory': '17歳、リンカーン小→ジェファーソン高3年。野球部キャプテン。父の昔気質に反発しがち。', 'traits': ['若さ', '野心', '反抗'], 'values': ['野球', '友情', '自由'], 'goals': ['大学野球で奨学金', '街を出る', 'プロ目指す']},
    },
    # Apartment eastside (171, 101)
    'fam_park_grandma': {
        'name': 'パク・ヘソン婦人',
        'alias': 'ヘソン婦人',
        'faction': 'family', 'active': False, 'x': 171, 'y': 101,
        'persona': {'backstory': '76歳、韓国系1世。ヘジン婦人 (角の店主) の姉。脳梗塞経験あり、半身麻痺。娘の家で同居。', 'traits': ['頑固', '伝統的', '体弱い'], 'values': ['家族', '韓国食', '故郷'], 'goals': ['娘に迷惑かけない', '孫を見守る', '安らかな最期']},
    },
    'fam_park_daughter': {
        'name': 'パク・ジヨン',
        'alias': 'ジヨン',
        'faction': 'family', 'active': False, 'x': 172, 'y': 101,
        'persona': {'backstory': '45歳、シングルマザー。中央図書館 (central_library) の司書。離婚済み。母 (ヘソン) と娘の3人暮らし。', 'traits': ['知的', '真面目', '疲労'], 'values': ['娘の教育', '母の介護', '本'], 'goals': ['母を介護', '娘を進学', '節約しつつ生きる']},
    },
    'fam_park_kid': {
        'name': 'パク・ミナ',
        'alias': 'ミナ',
        'faction': 'family', 'active': False, 'x': 170, 'y': 101,
        'persona': {'backstory': '11歳、リンカーン小5年生。明るい、絵が上手。祖母の介護を手伝う。', 'traits': ['素直', '芸術肌', '優しい'], 'values': ['絵', '家族', '友達'], 'goals': ['イラストレーターになる', '祖母を喜ばせる', '友達と楽しく過ごす']},
    },
    # Apartment southlake (201, 171)
    'fam_johnson_dad': {
        'name': 'マーカス・"パパ・J"・ジョンソン',
        'alias': 'パパ・J',
        'faction': 'family', 'active': False, 'x': 201, 'y': 171,
        'persona': {'backstory': '54歳、退役軍人 (湾岸戦争)。元バス運転手、引退済み。妻と暮らす。',
            'traits': ['誠実', '愛国心', '頑固'], 'values': ['国', '街', '昔'], 'goals': ['年金生活', '孫を見たい', '街の治安維持']},
    },
    'fam_johnson_wife': {
        'name': 'グレース・ジョンソン',
        'alias': 'グレース',
        'faction': 'family', 'active': False, 'x': 202, 'y': 171,
        'persona': {'backstory': '52歳、教会 (st_marys_church) の聖歌隊長。元小学校教師。', 'traits': ['信心深い', '世話焼き', '声が大きい'], 'values': ['教会', '若い世代', '聖歌'], 'goals': ['聖歌隊員増', '若者の道を正す', '夫の機嫌を取る']},
    },
    'fam_johnson_son': {
        'name': 'タイリーク・ジョンソン',
        'alias': 'タイ',
        'faction': 'family', 'active': False, 'x': 200, 'y': 171,
        'persona': {'backstory': '22歳、コミュニティカレッジ生 (法律志望)。父の影響で警察への憧れあり、しかし街の友達はギャング寄り、揺れている。', 'traits': ['迷い', '正義感', '葛藤'], 'values': ['家族', '正義', '街の友'], 'goals': ['弁護士か警官になる', '友人を切らない', '父に認められる']},
    },
    # Apartment north_grove (131, 61)
    'fam_silva_dad': {
        'name': 'ラファエル・シルバ',
        'alias': 'ラファエル',
        'faction': 'family', 'active': False, 'x': 131, 'y': 61,
        'persona': {'backstory': 'ブラジル系1世、39歳。ガス・ノース (gas_north) で働く。子供2人、妻と4人家族。', 'traits': ['陽気', '社交的', '怠惰寄り'], 'values': ['家族', 'サッカー', 'ビール'], 'goals': ['子供を養う', '休日にサッカー', 'ブラジル帰国の貯金']},
    },
    'fam_silva_wife': {
        'name': 'カミラ・シルバ',
        'alias': 'カミラ',
        'faction': 'family', 'active': False, 'x': 132, 'y': 61,
        'persona': {'backstory': '36歳、ベビーシッター。近所の子供を預かる。明るい性格、街の子供事情に詳しい。', 'traits': ['世話好き', '陽気', '観察力'], 'values': ['子供', '近所', '家族'], 'goals': ['子供達を守る', '近所の異変を察知', '自分の子も大きく']},
    },
    'fam_silva_kid': {
        'name': 'ガブリエル・シルバ',
        'alias': 'ガビ',
        'faction': 'family', 'active': False, 'x': 130, 'y': 61,
        'persona': {'backstory': '8歳、リンカーン小2年生。サッカー大好き。ヘソン婦人の家に時々遊びに行く。', 'traits': ['元気', '純粋', 'お喋り'], 'values': ['友達', 'サッカー', 'お菓子'], 'goals': ['プロサッカー選手', 'ミナと友達のまま', 'お菓子をたくさん食べる']},
    },
}

# ===== Drifters (8 transient characters) =====
DRIFTERS = {
    'drift_homeless_jim': {
        'name': '"ジム" ジョナサン・カーター',
        'alias': 'ジム',
        'faction': 'drifter', 'active': False, 'x': 95, 'y': 95,
        'persona': {'backstory': '58歳、ホームレス。退役軍人 (ベトナム末期)、PTSD と酒で家庭崩壊。アンクル・ジョーが20年前は同僚だった。', 'traits': ['寡黙', '観察力', '酒'], 'values': ['酒', '昔', '物陰'], 'goals': ['一日を生きる', '酒場の残飯', '昔を思い出す']},
    },
    'drift_addict_riley': {
        'name': 'ライリー・"スクラッチ"・モーガン',
        'alias': 'スクラッチ',
        'faction': 'drifter', 'active': False, 'x': 191, 'y': 51,
        'persona': {'backstory': '28歳、薬物依存症。元バンドマン、ベース。Drug Den 周辺をうろつく。母は街の外、絶縁状態。', 'traits': ['震え', '懇願', '芸術センス'], 'values': ['次の一服', '音楽', '生存'], 'goals': ['ハイになる', '楽器を質屋から取り戻す', '母に電話する勇気']},
    },
    'drift_tourist_emma': {
        'name': 'エマ・ホワイトフィールド',
        'alias': 'エマ',
        'faction': 'drifter', 'active': False, 'x': 125, 'y': 80,
        'persona': {'backstory': '24歳、フリーランスのジャーナリスト。アイスクリームトラックの噂を聞きつけて取材に来た。3日後には街を出る予定。', 'traits': ['好奇心', '若さ', '無謀'], 'values': ['スクープ', 'キャリア', '正直'], 'goals': ['内偵車の真相を掴む', '記事を売る', '無事に街を出る']},
    },
    'drift_truck_driver_carl': {
        'name': 'カール・ヘンダーソン',
        'alias': 'カール',
        'faction': 'drifter', 'active': False, 'x': 162, 'y': 42,
        'persona': {'backstory': '46歳、長距離トラック運転手。ガス・ノースで給油、明日には次の街へ。家庭はオハイオ。', 'traits': ['実直', '寡黙', '常識人'], 'values': ['家族', '燃料', '時間'], 'goals': ['納期を守る', '安全運転', '帰宅']},
    },
    'drift_runaway_destiny': {
        'name': 'デスティニー・"ベイビー"・スミス',
        'alias': 'ベイビー',
        'faction': 'drifter', 'active': False, 'x': 86, 'y': 146,
        'persona': {'backstory': '17歳、家出娘。実家は西の街、父の暴力から逃れて来た。オライリーズの裏で寝てる。', 'traits': ['警戒', '強がり', '孤独'], 'values': ['自由', '帰らない', '生存'], 'goals': ['西海岸まで行く', 'バーで小銭稼ぐ', '誰にも見つからない']},
    },
    'drift_preacher_silas': {
        'name': 'サイラス・"プリーチャー"・ボイド',
        'alias': 'プリーチャー',
        'faction': 'drifter', 'active': False, 'x': 157, 'y': 87,
        'persona': {'backstory': '63歳、流浪の説教師。教会の前で聖書を朗読する。教団なしのフリーランス。', 'traits': ['熱狂', '弁舌', '哀しみ'], 'values': ['信仰', '言葉', '魂の救済'], 'goals': ['街の罪人を救う', '次の街へ', '神に近づく']},
    },
    'drift_taxi_drik': {
        'name': 'ドリク・"D"・ペトロフ',
        'alias': 'D',
        'faction': 'drifter', 'active': False, 'x': 162, 'y': 122,
        'persona': {'backstory': '34歳、ロシア系移民2世。タクシー運転手。第一銀行 (first_bank) 前で客待ち。街全体を知ってる。', 'traits': ['寡黙', '観察力', '苦労人'], 'values': ['客', '時間', '家族 (本国)'], 'goals': ['日銭を稼ぐ', '本国の家族に送金', '車を整備']},
    },
    'drift_busker_zeke': {
        'name': 'ザイク・"ストリングス"・ハーパー',
        'alias': 'ストリングス',
        'faction': 'drifter', 'active': False, 'x': 132, 'y': 152,
        'persona': {'backstory': '29歳、ストリート・ミュージシャン。ギター1本で中央市場 (central_market) の前で弾く。先週この街に来た、来月には別の街へ。', 'traits': ['芸術肌', '人懐こい', '自由'], 'values': ['音楽', '旅', '小銭'], 'goals': ['今日のチップ', 'いいフレーズを思いつく', '次の街でも上手くやる']},
    },
}


def main():
    base = os.path.join(os.path.dirname(__file__), 'personas')
    all_new = {**MANGO, **PEACH_BEAR, **FAMILIES, **DRIFTERS}
    for pid, data in all_new.items():
        path = os.path.join(base, f'{pid}.json')
        d = {'id': pid, **data}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f'  + {pid:30s} → {data["name"]} ({data["faction"]})')
    print(f'\nTotal new personas: {len(all_new)}')


if __name__ == '__main__':
    main()
