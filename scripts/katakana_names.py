"""Convert all 30 persona names to Katakana. IDs stay English (code-stable)."""
import json, os

# Map: id -> (display name in katakana, short alias used in dialog)
NAMES = {
    # Police (28分署)
    'police_diaz':     ('キャプテン・マリア・ディアス', 'ディアス'),
    'police_park':     ('刑事ジェニー・パク',          'パク'),
    'police_rivera':   ('巡査ルイス・リベラ',         'リベラ'),
    'police_hanson':   ('刑事フランク・ハンソン',     'ハンソン'),
    'police_okoye':    ('巡査アマラ・オコエ',         'オコエ'),
    'police_schwartz': ('部長ダン・シュワルツ',       'シュワルツ'),
    'police_npc1':     ('巡査デヴィッド・チェン',     'チェン'),
    'police_npc2':     ('巡査リサ・タナカ',           'タナカ'),
    'police_npc3':     ('部長フランク・ウォレス',     'ウォレス'),
    'police_npc4':     ('通信員ジャネット・リベラ=コール', 'ジャネット'),

    # Pomegranate Mob (PM, 略: ポメ)
    'pm_hawk_marcus':  ('マーカス・"ホーク"・トンプソン', 'ホーク'),
    'pm_hawk_tyrone':  ('タイロン・"T-ホーク"・ジャクソン', 'T-ホーク'),
    'pm_cobra_devon':  ('デヴォン・"コブラ"・ウォーカー', 'コブラ'),
    'pm_cobra_lisa':   ('リサ・"レディ・コブラ"・ワトキンス', 'レディ・コブラ'),
    'pm_npc1':         ('トレイ・"スリム"・コールマン', 'スリム'),
    'pm_npc2':         ('リース・"アイズ"・マザーズ',  'アイズ'),
    'pm_npc3':         ('ジュニア・"J-ロック"・ブッカー', 'J-ロック'),

    # Persimmon Hustlers (PH, 略: パシ)
    'ph_wolf_antoine': ('アントワーヌ・"ツワン・ウルフ"・バンクス', 'アントワーヌ'),
    'ph_wolf_malik':   ('マリク・"ビッグ・ウルフ"・コールマン', 'マリク'),
    'ph_fox_keisha':   ('キーシャ・"K-フォックス"・モリソン', 'キーシャ'),
    'ph_npc1':         ('デイモン・"D-ブロック"・リーヴス', 'D-ブロック'),
    'ph_npc2':         ('タシャ・"T-バード"・ホイットモア', 'タシャ'),
    'ph_npc3':         ('マーカス・"リル-M"・ホロウェイ', 'リル-M'),

    # Vigilante (Stone Group, 略: ストーン組)
    'vig_stone':       ('フランク・"ストーン"・キャラハン', 'ストーン'),
    'vig_rachel':      ('レイチェル・グエン',           'レイチェル'),
    'vig_npc1':        ('マーカス・"ドク"・ブレナン',  'ドク'),
    'vig_npc2':        ('マリソル・オルテガ',         'マリソル'),

    # Civilians
    'civ_priest':      ('パトリック・オニール神父',   'オニール神父'),
    'civ_bartender':   ('エディ・"クワイエット"・マーフィー', 'エディ'),
    'civ_shopkeeper':  ('パク・ヘジン婦人',          'ヘジン婦人'),
}


def main():
    base = os.path.join(os.path.dirname(__file__), 'personas')
    for pid, (full, alias) in NAMES.items():
        p = os.path.join(base, f'{pid}.json')
        if not os.path.exists(p):
            print(f'! missing {pid}'); continue
        with open(p, encoding='utf-8') as f:
            d = json.load(f)
        d['name'] = full
        d['alias'] = alias
        # Keep original English name for reference
        d['name_en'] = d.get('name_en') or d.get('name')
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f'  {pid:30s} → {full}  (会話略: {alias})')

if __name__ == '__main__':
    main()
