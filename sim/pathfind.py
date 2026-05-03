"""A* pathfinding with terrain costs (roads cheap, grass expensive, buildings blocked)."""
from __future__ import annotations
import heapq
from .world import World, Tile, WALKABLE


# Cost per tile type (lower = preferred)
TILE_COST = {
    int(Tile.ROAD_H): 1,
    int(Tile.ROAD_V): 1,
    int(Tile.INTERSECTION): 1,
    int(Tile.SIDEWALK): 1,
    int(Tile.PARKING): 2,
    int(Tile.PARK): 2,
    int(Tile.GRASS): 4,
    int(Tile.ALLEY): 2,
    int(Tile.BUILDING_DOOR): 2,
    # Landmark buildings (interior, slightly expensive but passable)
    int(Tile.POLICE_STATION): 2,
    int(Tile.GANG_A_HIDEOUT): 2,
    int(Tile.GANG_B_HIDEOUT): 2,
    int(Tile.DRUG_DEN): 2,
    int(Tile.ICE_CREAM_TRUCK): 2,
    int(Tile.BAR): 2,
    int(Tile.CHURCH): 2,
    int(Tile.HOSPITAL): 2,
    int(Tile.SHOP): 2,
    int(Tile.APARTMENT): 2,
}

NEIGHBORS = [(0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1)]


def _heur(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))  # Chebyshev


def find_path(world: World, start: tuple[int, int], goal: tuple[int, int],
              max_iter: int = 50000) -> list[tuple[int, int]] | None:
    """A* path from start to goal. Returns list of (x, y) including start and goal, or None."""
    if start == goal:
        return [start]
    if not world.walkable(*goal):
        # Allow goal even if a "building" landmark; WALKABLE includes them already.
        # If still blocked (e.g. WATER), bail.
        return None

    open_heap = []
    heapq.heappush(open_heap, (0, start))
    came_from = {start: None}
    g_score = {start: 0}
    iter_count = 0
    while open_heap:
        iter_count += 1
        if iter_count > max_iter:
            return None
        _, cur = heapq.heappop(open_heap)
        if cur == goal:
            # Reconstruct
            path = [cur]
            while came_from[cur] is not None:
                cur = came_from[cur]
                path.append(cur)
            path.reverse()
            return path
        for dx, dy in NEIGHBORS:
            nx, ny = cur[0] + dx, cur[1] + dy
            if nx < 0 or ny < 0 or nx >= world.width or ny >= world.height:
                continue
            tile = world.tile_at(nx, ny)
            if tile not in WALKABLE:
                continue
            cost = TILE_COST.get(tile, 5)
            tentative = g_score[cur] + cost
            n = (nx, ny)
            if tentative < g_score.get(n, 1 << 30):
                g_score[n] = tentative
                came_from[n] = cur
                heapq.heappush(open_heap, (tentative + _heur(n, goal), n))
    return None


def step_along_path(world: World, start: tuple[int, int], goal: tuple[int, int],
                    max_steps: int = 10) -> tuple[tuple[int, int], int]:
    """Compute path and return (final_position, steps_taken). Empty path → stays at start."""
    path = find_path(world, start, goal)
    if not path or len(path) <= 1:
        return start, 0
    # Walk up to max_steps along the path
    pos = path[min(max_steps, len(path) - 1)]
    return pos, min(max_steps, len(path) - 1)
