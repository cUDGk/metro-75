"""Render tile map + agents to a PNG using Pillow (simple, portable)."""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import os
from .world import World, Tile


# Simple color palette (tile type → RGB)
COLORS: dict[int, tuple[int, int, int]] = {
    int(Tile.GRASS): (78, 155, 75),
    int(Tile.ROAD_H): (60, 60, 60),
    int(Tile.ROAD_V): (60, 60, 60),
    int(Tile.INTERSECTION): (80, 80, 80),
    int(Tile.SIDEWALK): (180, 180, 175),
    int(Tile.BUILDING): (130, 100, 90),
    int(Tile.BUILDING_DOOR): (160, 110, 60),
    int(Tile.PARK): (100, 180, 90),
    int(Tile.PARKING): (100, 100, 100),
    int(Tile.WATER): (70, 130, 180),
    int(Tile.POLICE_STATION): (30, 60, 170),
    int(Tile.GANG_A_HIDEOUT): (30, 90, 200),   # blue Crips
    int(Tile.GANG_B_HIDEOUT): (200, 40, 40),   # red Bloods
    int(Tile.DRUG_DEN): (90, 50, 90),
    int(Tile.ICE_CREAM_TRUCK): (255, 240, 200),
    int(Tile.BAR): (180, 110, 50),
    int(Tile.CHURCH): (220, 210, 180),
    int(Tile.HOSPITAL): (240, 240, 240),
    int(Tile.SHOP): (180, 160, 80),
    int(Tile.APARTMENT): (110, 80, 70),
    int(Tile.ALLEY): (50, 45, 40),
    int(Tile.GANG_C_HIDEOUT): (255, 165, 50),    # mango orange
    int(Tile.SCHOOL): (220, 200, 50),            # yellow
    int(Tile.LIBRARY): (140, 100, 160),          # purple
    int(Tile.GAS_STATION): (200, 60, 60),        # red
    int(Tile.FIRE_STATION): (220, 80, 40),       # orange-red
    int(Tile.MARKET): (180, 140, 80),            # tan
    int(Tile.OFFICE): (160, 180, 200),           # light blue
    int(Tile.RESTAURANT): (210, 130, 90),        # warm orange
    int(Tile.HOUSE_S): (140, 110, 95),           # warm brown small
    int(Tile.HOUSE_M): (155, 120, 90),           # medium
    int(Tile.HOUSE_L): (170, 130, 85),           # large
}

FACTION_COLORS = {
    'police': (20, 50, 200),
    'vigilante': (220, 180, 20),
    'gang_a': (50, 160, 255),
    'gang_b': (255, 60, 60),
    'gang_c': (255, 140, 0),    # mango orange (independent)
    'civilian': (200, 200, 200),
    'family': (180, 200, 220),
    'drifter': (180, 130, 200),
}


def render(world: World, agents: dict, tile_px: int = 3, out_path: str = 'map.png',
           highlight_landmarks: bool = True, title: str | None = None):
    W, H = world.width * tile_px, world.height * tile_px
    img = Image.new('RGB', (W, H + 40 if title else H), (20, 20, 25))
    pixels = img.load()
    # Render tiles
    for y in range(world.height):
        for x in range(world.width):
            color = COLORS.get(world.tiles[y][x], (200, 0, 255))  # magenta = unknown
            for py in range(tile_px):
                for px in range(tile_px):
                    pixels[x * tile_px + px, y * tile_px + py] = color
    draw = ImageDraw.Draw(img)
    # Agents as circles
    for ag in agents.values():
        if ag.status == 'dead':
            fill = (60, 60, 60)
        else:
            fill = FACTION_COLORS.get(ag.faction, (255, 255, 255))
        cx, cy = ag.x * tile_px + tile_px // 2, ag.y * tile_px + tile_px // 2
        r = max(2, tile_px)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=(0, 0, 0))
    # Title bar at bottom
    if title:
        try:
            font = ImageFont.truetype('arial.ttf', 18)
        except Exception:
            font = ImageFont.load_default()
        draw.text((10, H + 5), title, fill=(255, 255, 255), font=font)
    img.save(out_path)


def render_quick(world: World, agents: dict, out_path: str = 'map_snapshot.png'):
    """Small preview with 3px tiles."""
    title = f'{world.time_str()}  |  agents: ' + ', '.join(
        f"{a.faction[0].upper()}{sum(1 for x in agents.values() if x.faction == a.faction)}"
        for a in list(agents.values())[:1]
    ) if agents else world.time_str()
    render(world, agents, tile_px=3, out_path=out_path, title=world.time_str())
