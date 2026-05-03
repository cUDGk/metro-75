"""Render an overview map with landmark labels + all 30 agents at start positions."""
import sys, io, os, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont
from sim.world import World, Tile
from sim.render import COLORS, FACTION_COLORS

world = World.load('map/metro.json')

TILE_PX = 5  # 250 * 5 = 1250 px wide
W, H = world.width * TILE_PX, world.height * TILE_PX

img = Image.new('RGB', (W + 320, H + 80), (15, 15, 20))
draw = ImageDraw.Draw(img)
pixels = img.load()

# Render tiles
for y in range(world.height):
    for x in range(world.width):
        color = COLORS.get(world.tiles[y][x], (200, 0, 255))
        for py in range(TILE_PX):
            for px in range(TILE_PX):
                pixels[x * TILE_PX + px, y * TILE_PX + py] = color

# Load all personas
agents = []
for f in sorted(glob.glob('personas/*.json')):
    with open(f, encoding='utf-8') as fh:
        d = json.load(fh)
        agents.append(d)

# Draw agents (active=larger, NPC=smaller)
for d in agents:
    fill = FACTION_COLORS.get(d['faction'], (255, 255, 255))
    cx = d['x'] * TILE_PX + TILE_PX // 2
    cy = d['y'] * TILE_PX + TILE_PX // 2
    active = d.get('active', True)
    r = 7 if active else 4
    outline = (255, 255, 255) if active else (60, 60, 60)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=2)

# Landmarks: label them
# Use a font that renders Japanese (Yu Gothic ships with Windows)
JP_FONT_CANDIDATES = [
    'C:/Windows/Fonts/YuGothM.ttc',
    'C:/Windows/Fonts/meiryo.ttc',
    'C:/Windows/Fonts/msgothic.ttc',
    'C:/Windows/Fonts/YuGothR.ttc',
]
def _load_font(size):
    for p in JP_FONT_CANDIDATES:
        try: return ImageFont.truetype(p, size)
        except Exception: pass
    return ImageFont.load_default()

font_lm = _load_font(14)
font_title = _load_font(22)
font_legend = _load_font(14)

LANDMARK_LABELS = {
    'police_station': '28分署',
    'garnet_hq': 'ガーネット HQ',
    'persica_hq': 'ペルシカ HQ',
    'cobrakillers_hq': 'コブラキラー HQ',
    'drug_den_north': 'ドラッグハウス北',
    'drug_den_west': 'ドラッグハウス西',
    'ice_cream_truck': 'アイスクリームトラック',
    'oreillys_bar': 'オライリーズ酒場',
    'lucky7_bar': 'ラッキー7',
    'st_marys_church': 'セント・メアリー教会',
    'st_anns_chapel': '聖アン礼拝堂',
    'mercy_hospital': 'マーシー病院',
    'fire_station': '消防署',
    'central_library': '中央図書館',
    'jefferson_high': 'ジェファーソン高校',
    'lincoln_elementary': 'リンカーン小',
    'mings_diner': 'ミンズ・ダイナー',
    'corner_pizza': 'コーナー・ピザ',
    'sakura_sushi': '桜寿司',
    'central_market': '中央市場',
    'east_grocery': '東スーパー',
    'park_corner_store': '北角店',
    'gas_north': 'ガス北',
    'gas_south': 'ガス南',
    'gas_east': 'ガス東',
    'first_bank': '第一銀行',
    'calabrese_holdings': 'カラブレーゼ商会',
    'lawyer_office': '法律事務所',
    'corner_store_park': 'コーナーストア',
    'shop_west': '雑貨店 (西)',
    'shop_east': '雑貨店 (東)',
    'apartment_riverside': 'アパート (川沿)',
    'apartment_central': 'アパート (中央)',
    'apartment_eastside': 'アパート (東)',
    'apartment_southlake': 'アパート (南湖)',
    'apartment_north_grove': 'アパート (北森)',
    'garrison_park':   'ガリソン大公園 (25×25)',
    'east_river_park': 'イースト・リバー公園 (22×22)',
    'northwood_park':  'ノースウッド公園',
    'central_plaza':   '中央広場',
    'riverside_lawn':  'リバーサイド芝生',
}
SKIP_LANDMARKS = set()  # show all
for key, (lx, ly) in world.landmarks.items():
    if key in SKIP_LANDMARKS: continue
    # Skip generic apartment_*, shop_* if you want — keep for now
    if key.startswith(('apartment_', 'shop_')): continue
    label = LANDMARK_LABELS.get(key, key)
    x, y = lx * TILE_PX, ly * TILE_PX
    bbox = draw.textbbox((0, 0), label, font=font_lm)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    bx0, by0 = x + 10, y - th - 6
    bx1, by1 = bx0 + tw + 8, by0 + th + 6
    draw.rectangle([bx0, by0, bx1, by1], fill=(0, 0, 0), outline=(255, 255, 0))
    draw.text((bx0 + 4, by0 + 2), label, fill=(255, 255, 200), font=font_lm)
    draw.line([(x, y), (bx0, by0 + th // 2 + 3)], fill=(255, 255, 0), width=1)

# Title
draw.text((10, H + 10), f'METRO-75 / Day0 06:00 — 250x250 タイル / アクティブ {sum(1 for d in agents if d.get("active"))}人 + NPC {sum(1 for d in agents if not d.get("active"))}人',
          fill=(255, 255, 255), font=font_title)

# Legend on right side
LEGEND_X = W + 20
draw.text((LEGEND_X, 10), '勢力', fill=(255, 255, 255), font=font_title)
y = 50
faction_legend = [
    ('警察 (28分署)', FACTION_COLORS['police']),
    ('ガーネット (Garnet)', FACTION_COLORS['gang_a']),
    ('ペルシカ (Persica)', FACTION_COLORS['gang_b']),
    ('コブラキラー (Cobra Killer)', FACTION_COLORS['gang_c']),
    ('自警団 (ストーン組)', FACTION_COLORS['vigilante']),
    ('一般市民/家族', FACTION_COLORS['civilian']),
    ('流れ者 (ドリフター)', (180, 130, 200)),
]
for label, color in faction_legend:
    draw.ellipse((LEGEND_X, y, LEGEND_X + 18, y + 18), fill=color, outline=(255, 255, 255))
    draw.text((LEGEND_X + 28, y + 1), label, fill=(255, 255, 255), font=font_legend)
    y += 28

y += 10
draw.text((LEGEND_X, y), '凡例', fill=(255, 255, 255), font=font_title)
y += 35
items = [
    ('●大 = アクティブ', (255, 255, 255)),
    ('●小 = NPC/家族/流れ者', (160, 160, 160)),
    ('青建物 = 28分署', (30, 60, 170)),
    ('青タイル = ガーネット HQ', (30, 90, 200)),
    ('赤タイル = ペルシカ HQ', (200, 40, 40)),
    ('オレンジ = コブラキラー HQ', (255, 165, 50)),
    ('黄 = 学校', (220, 200, 50)),
    ('紫 = ドラッグハウス/図書館', (90, 50, 90)),
    ('クリーム = アイス屋', (255, 240, 200)),
    ('赤 = ガソスタ/消防', (200, 60, 60)),
    ('水色 = オフィス/銀行', (160, 180, 200)),
    ('白 = 病院', (240, 240, 240)),
    ('ベージュ = 教会', (220, 210, 180)),
    ('緑 = 公園/広場', (100, 180, 90)),
]
for label, color in items:
    draw.rectangle([LEGEND_X, y + 2, LEGEND_X + 16, y + 16], fill=color, outline=(255, 255, 255))
    draw.text((LEGEND_X + 24, y), label, fill=(255, 255, 255), font=font_legend)
    y += 24

out = 'overview.png'
img.save(out)
print(f'wrote {out}: {img.size}')
