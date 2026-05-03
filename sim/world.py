"""World state: 250x250 tile map + resources."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
import json
import random


class Tile(IntEnum):
    """Logical tile types (visual rendering is separate)."""
    GRASS = 0
    ROAD_H = 1        # horizontal road
    ROAD_V = 2        # vertical road
    INTERSECTION = 3
    SIDEWALK = 4
    BUILDING = 5      # generic building wall
    BUILDING_DOOR = 6
    PARK = 7
    PARKING = 8
    WATER = 9
    # Faction / landmark buildings
    POLICE_STATION = 10
    GANG_A_HIDEOUT = 11    # ザクロ団 (Pomegranate Mob)
    GANG_B_HIDEOUT = 12    # 桃団 (Peach Hustlers)
    DRUG_DEN = 13
    ICE_CREAM_TRUCK = 14   # 内偵車 (police undercover)
    BAR = 15
    CHURCH = 16
    HOSPITAL = 17
    SHOP = 18
    APARTMENT = 19
    ALLEY = 20             # narrow passage
    # Extended landmarks
    GANG_C_HIDEOUT = 21    # マンゴー団 (Cobra Killer)
    SCHOOL = 22
    LIBRARY = 23
    GAS_STATION = 24
    FIRE_STATION = 25
    MARKET = 26
    OFFICE = 27
    RESTAURANT = 28
    HOUSE_S = 29           # small detached house
    HOUSE_M = 30           # medium house
    HOUSE_L = 31           # large house


# Walkable tiles — includes landmark buildings so agents can start inside and exit
WALKABLE = {
    Tile.GRASS, Tile.ROAD_H, Tile.ROAD_V, Tile.INTERSECTION, Tile.SIDEWALK,
    Tile.PARK, Tile.PARKING, Tile.BUILDING_DOOR, Tile.ALLEY,
    # Landmark buildings — treated as accessible
    Tile.POLICE_STATION, Tile.GANG_A_HIDEOUT, Tile.GANG_B_HIDEOUT, Tile.GANG_C_HIDEOUT,
    Tile.DRUG_DEN, Tile.ICE_CREAM_TRUCK, Tile.BAR, Tile.CHURCH,
    Tile.HOSPITAL, Tile.SHOP, Tile.APARTMENT,
    Tile.SCHOOL, Tile.LIBRARY, Tile.GAS_STATION, Tile.FIRE_STATION,
    Tile.MARKET, Tile.OFFICE, Tile.RESTAURANT,
    Tile.HOUSE_S, Tile.HOUSE_M, Tile.HOUSE_L,
}


@dataclass
class World:
    width: int
    height: int
    tiles: list[list[int]]             # [y][x] = Tile value
    landmarks: dict = field(default_factory=dict)  # name -> (x, y)
    day: int = 0
    hour: int = 6                      # sim hour of day (0-23)
    minute: int = 0                    # 0-59

    def tile_at(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return Tile.WATER  # out of bounds = blocked

    def walkable(self, x: int, y: int) -> bool:
        return self.tile_at(x, y) in WALKABLE

    def nearby_tiles(self, x: int, y: int, radius: int = 5):
        """Return list of (dx, dy, tile) for tiles within Chebyshev radius."""
        out = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    out.append((dx, dy, self.tiles[ny][nx]))
        return out

    def nearest_landmarks(self, x: int, y: int, k: int = 8) -> list[str]:
        """Return up to k landmark keys nearest to (x,y) by Chebyshev distance."""
        ranked = sorted(
            self.landmarks.items(),
            key=lambda kv: max(abs(kv[1][0] - x), abs(kv[1][1] - y)),
        )
        return [name for name, _ in ranked[:k]]

    def tick(self):
        """Advance time by 1 sim-minute."""
        self.minute += 1
        if self.minute >= 60:
            self.minute = 0
            self.hour += 1
            if self.hour >= 24:
                self.hour = 0
                self.day += 1

    # Day 0 = Monday convention (weekday 0 = Mon, 6 = Sun)
    _WEEKDAY_JP = ['月', '火', '水', '木', '金', '土', '日']

    def weekday(self) -> int:
        return self.day % 7

    def weekday_jp(self) -> str:
        return self._WEEKDAY_JP[self.weekday()]

    def is_weekend(self) -> bool:
        return self.weekday() in (5, 6)

    def time_period(self) -> str:
        h = self.hour
        if h < 5: return '深夜'
        if h < 7: return '早朝'
        if h < 10: return '朝'
        if h < 12: return '午前'
        if h < 14: return '昼'
        if h < 17: return '午後'
        if h < 19: return '夕方'
        if h < 22: return '夜'
        return '夜更け'

    def time_str(self):
        return f"Day {self.day}({self.weekday_jp()}) {self.hour:02d}:{self.minute:02d}"

    def to_dict(self):
        return {
            'width': self.width, 'height': self.height,
            'tiles': self.tiles, 'landmarks': self.landmarks,
            'day': self.day, 'hour': self.hour, 'minute': self.minute,
        }

    def save(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path: str) -> 'World':
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
        return cls(**d)
