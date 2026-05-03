"""Procedural US neighborhood generator (v2): varied buildings + multi-landmark.

250x250 grid:
- Main avenues (5 tiles wide) every 50 tiles
- Side streets (2 tiles wide) every 10 tiles
- Sidewalks adjacent to all roads
- Mid-sized blocks (~8x8) filled with varied buildings (small house / medium / large / apartment / office / etc)
- Multiple landmarks of varied types and sizes scattered across the city
- Two large public parks + many small green patches
"""
from __future__ import annotations
import random
from .world import World, Tile


# Landmark spec: (tile_type, name, center_x, center_y, size_w, size_h)
LANDMARKS_SPEC = [
    # ===== Faction HQs =====
    (Tile.POLICE_STATION, 'police_station',  125, 125,  8, 8),
    (Tile.GANG_A_HIDEOUT, 'garnet_hq',        32,  32,  6, 6),  # ガーネット HQ (ザクロ系)
    (Tile.GANG_B_HIDEOUT, 'persica_hq',      217, 217,  6, 6),  # ペルシカ HQ (桃系)
    (Tile.GANG_C_HIDEOUT, 'cobrakillers_hq',  32, 217,  5, 5),  # コブラキラー HQ (マンゴー系)
    # ===== Scenario-key =====
    (Tile.ICE_CREAM_TRUCK, 'ice_cream_truck',146, 131,  2, 3),  # ice cream truck (suspicious, parked 3 days)
    # ===== Underworld =====
    (Tile.DRUG_DEN, 'drug_den_north',        191,  51,  4, 4),
    (Tile.DRUG_DEN, 'drug_den_west',          61,  61,  4, 4),
    # ===== Civic =====
    (Tile.HOSPITAL, 'mercy_hospital',        187, 117, 10, 8),
    (Tile.FIRE_STATION, 'fire_station',      102, 102,  6, 5),
    (Tile.LIBRARY, 'central_library',        152, 162,  6, 6),
    (Tile.SCHOOL, 'jefferson_high',           62, 132, 10, 8),
    (Tile.SCHOOL, 'lincoln_elementary',      172,  92,  8, 6),
    (Tile.CHURCH, 'st_marys_church',         157,  87,  6, 6),
    (Tile.CHURCH, 'st_anns_chapel',           42, 152,  4, 4),
    # ===== Commercial =====
    (Tile.BAR, 'oreillys_bar',                86, 146,  4, 3),
    (Tile.BAR, 'lucky7_bar',                 192, 192,  4, 3),
    (Tile.RESTAURANT, 'mings_diner',         122,  92,  4, 3),
    (Tile.RESTAURANT, 'corner_pizza',         92, 162,  3, 3),
    (Tile.RESTAURANT, 'sakura_sushi',         52, 192,  4, 3),
    (Tile.MARKET, 'central_market',          132, 152,  6, 5),
    (Tile.MARKET, 'east_grocery',            202, 142,  4, 4),
    (Tile.MARKET, 'park_corner_store',        72,  72,  3, 3),
    (Tile.GAS_STATION, 'gas_north',          162,  42,  4, 4),
    (Tile.GAS_STATION, 'gas_south',           62, 192,  4, 4),
    (Tile.GAS_STATION, 'gas_east',           212,  82,  4, 4),
    (Tile.OFFICE, 'first_bank',              162, 122,  6, 4),
    (Tile.OFFICE, 'calabrese_holdings',       42, 207,  5, 4),  # Cobra Killer front company
    (Tile.OFFICE, 'lawyer_office',           112, 122,  4, 4),
    (Tile.SHOP, 'corner_store_park',         144, 127,  3, 3),  # next to ice cream truck
    (Tile.SHOP, 'shop_west',                  82,  82,  3, 3),
    (Tile.SHOP, 'shop_east',                 182,  82,  3, 3),
    # ===== Apartments (taller residential) =====
    (Tile.APARTMENT, 'apartment_riverside',   51, 121,  6, 8),
    (Tile.APARTMENT, 'apartment_central',    101, 181,  6, 8),
    (Tile.APARTMENT, 'apartment_eastside',   171, 101,  6, 8),
    (Tile.APARTMENT, 'apartment_southlake',  201, 171,  6, 8),
    (Tile.APARTMENT, 'apartment_north_grove',131,  61,  6, 8),
]

# Big public parks: (name, x, y, w, h)
BIG_PARKS = [
    ('garrison_park',    165, 165, 25, 25),  # SE huge park (25x25)
    ('east_river_park',   55, 165, 22, 22),  # SW big park (22x22)
    ('northwood_park',    55,  85, 20, 16),  # NW medium-large
    ('central_plaza',    115,  60, 18, 14),  # central market plaza
    ('riverside_lawn',   165,  45, 14, 14),  # NE lawn
]


def _paint_rect(tiles, x: int, y: int, w: int, h: int, tile_type: int, width: int, height: int,
                only_grass: bool = True):
    """Paint a rect. By default only overwrites GRASS tiles (preserves roads/sidewalks)."""
    for dy in range(h):
        for dx in range(w):
            xx, yy = x + dx, y + dy
            if 0 <= xx < width and 0 <= yy < height:
                if only_grass:
                    if tiles[yy][xx] == int(Tile.GRASS):
                        tiles[yy][xx] = tile_type
                else:
                    tiles[yy][xx] = tile_type


def _place_in_lot(tiles, lx: int, ly: int, lw: int, lh: int, tile_type: int,
                  width: int, height: int, margin: int = 1):
    """Place a building centered in a lot with `margin` tiles of grass yard around it.
    Building shrinks if lot is too small. Only paints over grass."""
    if lw <= 0 or lh <= 0: return
    sw = max(1, lw - 2 * margin)
    sh = max(1, lh - 2 * margin)
    sx = lx + (lw - sw) // 2
    sy = ly + (lh - sh) // 2
    _paint_rect(tiles, sx, sy, sw, sh, tile_type, width, height, only_grass=True)


def _is_road(t: int) -> bool:
    return t in (int(Tile.ROAD_H), int(Tile.ROAD_V), int(Tile.INTERSECTION))


def _carve_river(tiles, width, height, rng):
    """Sinusoidal river along eastern edge, with bridges where main avenues cross."""
    import math
    river_width = 7
    base_x = 232
    amp = 10
    period = 90
    river_path = []
    for y in range(height):
        cx = int(base_x + amp * math.sin(2 * math.pi * y / period))
        river_path.append(cx)
        for dx in range(-river_width // 2, river_width // 2 + 1):
            xx = cx + dx
            if 0 <= xx < width:
                tiles[y][xx] = int(Tile.WATER)
    # Restore road crossings as bridges (INTERSECTION) plus 1-tile bridge above/below
    for y in range(1, height - 1):
        cx = river_path[y]
        for dx in range(-river_width // 2 - 1, river_width // 2 + 2):
            xx = cx + dx
            if 0 <= xx < width:
                # If a road would have been here originally, the row above/below has road tiles
                if any(_is_road(tiles[ny][xx]) for ny in (y - 2, y + 2) if 0 <= ny < height):
                    if tiles[y][xx] == int(Tile.WATER):
                        tiles[y][xx] = int(Tile.INTERSECTION)


def _carve_highway(tiles, width, height):
    """4-lane highway along south edge."""
    hwy_y = height - 8
    hwy_height = 6
    for yy in range(hwy_y, hwy_y + hwy_height):
        if 0 <= yy < height:
            for x in range(width):
                tiles[yy][x] = int(Tile.ROAD_H)


def _suburbanize_outskirts(tiles, width, height, rng):
    """Convert outer ring buildings to grass/park to feel less urban."""
    margin = 25
    for y in range(height):
        for x in range(width):
            in_outskirt = (x < margin or x >= width - margin
                           or y < margin or y >= height - margin)
            if in_outskirt:
                t = tiles[y][x]
                if t in (int(Tile.HOUSE_S), int(Tile.HOUSE_M), int(Tile.HOUSE_L),
                         int(Tile.BUILDING)):
                    if rng.random() < 0.6:
                        tiles[y][x] = int(Tile.PARK if rng.random() < 0.4 else Tile.GRASS)


def _densify_downtown(tiles, width, height, rng):
    """Downtown core (center ~60x60) biased to OFFICE/MARKET."""
    cx, cy = width // 2, height // 2
    radius = 35
    for y in range(max(0, cy - radius), min(height, cy + radius)):
        for x in range(max(0, cx - radius), min(width, cx + radius)):
            d = max(abs(x - cx), abs(y - cy))
            if d > radius: continue
            t = tiles[y][x]
            if t in (int(Tile.HOUSE_S), int(Tile.HOUSE_M), int(Tile.HOUSE_L)):
                if rng.random() < 0.5:
                    tiles[y][x] = int(Tile.OFFICE if rng.random() < 0.7 else Tile.BUILDING)


def generate(seed: int = 42, width: int = 250, height: int = 250) -> World:
    rng = random.Random(seed)
    tiles = [[int(Tile.GRASS) for _ in range(width)] for _ in range(height)]
    landmarks: dict = {}

    # ---- 1. Street grid ----
    main_spacing = 50      # main avenue every 50 tiles
    main_width = 5
    side_spacing = 10
    side_width = 2

    main_xs = list(range(main_spacing // 2, width, main_spacing))
    main_ys = list(range(main_spacing // 2, height, main_spacing))

    # Main horizontal avenues
    for ym in main_ys:
        for yy in range(ym - main_width // 2, ym - main_width // 2 + main_width):
            if 0 <= yy < height:
                for x in range(width):
                    tiles[yy][x] = int(Tile.ROAD_H)
    # Main vertical avenues (intersect at crosses)
    for xm in main_xs:
        for xx in range(xm - main_width // 2, xm - main_width // 2 + main_width):
            if 0 <= xx < width:
                for y in range(height):
                    if tiles[y][xx] == int(Tile.ROAD_H):
                        tiles[y][xx] = int(Tile.INTERSECTION)
                    else:
                        tiles[y][xx] = int(Tile.ROAD_V)

    def near_main(coord: int, mains: list[int]) -> bool:
        return any(abs(coord - m) <= main_width for m in mains)

    # Side horizontal streets
    for ys in range(side_spacing, height, side_spacing):
        if near_main(ys, main_ys): continue
        for yy in range(ys, ys + side_width):
            if 0 <= yy < height:
                for x in range(width):
                    if tiles[yy][x] == int(Tile.GRASS):
                        tiles[yy][x] = int(Tile.ROAD_H)
                    elif tiles[yy][x] == int(Tile.ROAD_V):
                        tiles[yy][x] = int(Tile.INTERSECTION)
    # Side vertical streets
    for xs in range(side_spacing, width, side_spacing):
        if near_main(xs, main_xs): continue
        for xx in range(xs, xs + side_width):
            if 0 <= xx < width:
                for y in range(height):
                    if tiles[y][xx] == int(Tile.GRASS):
                        tiles[y][xx] = int(Tile.ROAD_V)
                    elif tiles[y][xx] == int(Tile.ROAD_H):
                        tiles[y][xx] = int(Tile.INTERSECTION)

    # ---- 2. Sidewalks adjacent to roads ----
    for y in range(height):
        for x in range(width):
            if _is_road(tiles[y][x]):
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and tiles[ny][nx] == int(Tile.GRASS):
                            tiles[ny][nx] = int(Tile.SIDEWALK)

    # ---- 3. Big parks (placed FIRST so buildings don't overwrite) ----
    for name, x, y, w, h in BIG_PARKS:
        for dy in range(h):
            for dx in range(w):
                xx, yy = x + dx, y + dy
                if 0 <= xx < width and 0 <= yy < height and not _is_road(tiles[yy][xx]):
                    tiles[yy][xx] = int(Tile.PARK)
        landmarks[name] = (x + w // 2, y + h // 2)

    # ---- 4. Find building blocks (rectangles of free GRASS surrounded by roads/sidewalks) ----
    # Strategy: scan in 10x10 chunks (matching side_spacing). For each chunk, find the inner free area.
    block_areas = []  # (x0, y0, w, h)
    visited = [[False] * width for _ in range(height)]

    for cy_start in range(0, height, side_spacing):
        for cx_start in range(0, width, side_spacing):
            # Find bounding box of contiguous GRASS within this chunk
            xs_in_chunk = []
            ys_in_chunk = []
            for yy in range(cy_start, min(cy_start + side_spacing, height)):
                for xx in range(cx_start, min(cx_start + side_spacing, width)):
                    if tiles[yy][xx] == int(Tile.GRASS) and not visited[yy][xx]:
                        xs_in_chunk.append(xx)
                        ys_in_chunk.append(yy)
                        visited[yy][xx] = True
            if xs_in_chunk:
                x0, x1 = min(xs_in_chunk), max(xs_in_chunk)
                y0, y1 = min(ys_in_chunk), max(ys_in_chunk)
                w = x1 - x0 + 1
                h = y1 - y0 + 1
                if w >= 3 and h >= 3:
                    block_areas.append((x0, y0, w, h))

    # ---- 5. Fill blocks: subdivide into lots, place buildings with grass yard margin ----
    for (x0, y0, bw, bh) in block_areas:
        # Tiny block: single small house
        if bw < 5 or bh < 5:
            _place_in_lot(tiles, x0, y0, bw, bh, int(Tile.HOUSE_S), width, height, margin=1)
            continue

        roll = rng.random()

        if roll < 0.06:
            # Pocket park
            _paint_rect(tiles, x0, y0, bw, bh, int(Tile.PARK), width, height)
            continue

        # Pick lot pattern based on block dimensions
        if bw <= 8 and bh <= 8:
            # Single-lot block: medium or large house with yard
            tile_type = rng.choices(
                [int(Tile.HOUSE_M), int(Tile.HOUSE_L), int(Tile.HOUSE_S),
                 int(Tile.OFFICE), int(Tile.BUILDING)],
                weights=[35, 30, 15, 10, 10],
            )[0]
            margin = 2 if tile_type == int(Tile.HOUSE_S) else 1
            _place_in_lot(tiles, x0, y0, bw, bh, tile_type, width, height, margin=margin)
        else:
            # Larger block: pick lot subdivision
            split = rng.random()
            if split < 0.30:
                # 2 lots (split along longer axis)
                if bw >= bh:
                    half = bw // 2
                    _place_in_lot(tiles, x0,        y0, half,      bh,
                                  int(Tile.HOUSE_M), width, height, margin=1)
                    _place_in_lot(tiles, x0 + half, y0, bw - half, bh,
                                  int(Tile.HOUSE_M), width, height, margin=1)
                else:
                    half = bh // 2
                    _place_in_lot(tiles, x0, y0,        bw, half,
                                  int(Tile.HOUSE_M), width, height, margin=1)
                    _place_in_lot(tiles, x0, y0 + half, bw, bh - half,
                                  int(Tile.HOUSE_M), width, height, margin=1)
            elif split < 0.55:
                # 4 lots (2x2)
                hw, hh = bw // 2, bh // 2
                for (sx, sy, sw, sh) in [
                    (x0,      y0,      hw,      hh),
                    (x0 + hw, y0,      bw - hw, hh),
                    (x0,      y0 + hh, hw,      bh - hh),
                    (x0 + hw, y0 + hh, bw - hw, bh - hh),
                ]:
                    _place_in_lot(tiles, sx, sy, sw, sh,
                                  int(Tile.HOUSE_S), width, height, margin=1)
            elif split < 0.75:
                # Big single building (apartment / office / warehouse)
                tile_type = rng.choices(
                    [int(Tile.APARTMENT), int(Tile.OFFICE), int(Tile.HOUSE_L),
                     int(Tile.BUILDING)],
                    weights=[35, 30, 25, 10],
                )[0]
                _place_in_lot(tiles, x0, y0, bw, bh, tile_type, width, height, margin=1)
            else:
                # 3 lots row (long block)
                if bw >= bh:
                    third = bw // 3
                    for i in range(3):
                        sx = x0 + i * third
                        sw = (bw - 2 * third) if i == 2 else third
                        _place_in_lot(tiles, sx, y0, sw, bh,
                                      int(Tile.HOUSE_M), width, height, margin=1)
                else:
                    third = bh // 3
                    for i in range(3):
                        sy = y0 + i * third
                        sh = (bh - 2 * third) if i == 2 else third
                        _place_in_lot(tiles, x0, sy, bw, sh,
                                      int(Tile.HOUSE_M), width, height, margin=1)

    # ---- 5b. Outskirt suburbanization ----
    _suburbanize_outskirts(tiles, width, height, rng)
    # ---- 5c. Downtown densification ----
    _densify_downtown(tiles, width, height, rng)
    # ---- 5d. River carve (after buildings, before landmarks) ----
    _carve_river(tiles, width, height, rng)
    # ---- 5e. Southern highway ----
    _carve_highway(tiles, width, height)

    # ---- 6. Stamp landmarks (overrides any building underneath) ----
    for spec in LANDMARKS_SPEC:
        tile_type, name, cx, cy, w, h = spec
        x0 = cx - w // 2
        y0 = cy - h // 2
        # Don't overwrite roads
        for dy in range(h):
            for dx in range(w):
                xx, yy = x0 + dx, y0 + dy
                if 0 <= xx < width and 0 <= yy < height and not _is_road(tiles[yy][xx]):
                    tiles[yy][xx] = int(tile_type)
        landmarks[name] = (cx, cy)

    return World(width=width, height=height, tiles=tiles, landmarks=landmarks)


if __name__ == '__main__':
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    w = generate(seed=7)
    out = os.path.join(os.path.dirname(__file__), '..', 'map', 'metro.json')
    w.save(out)
    print(f'saved {out}: {w.width}x{w.height}, {len(w.landmarks)} landmarks')
    for name, pos in sorted(w.landmarks.items()):
        print(f'  {name}: {pos}')
