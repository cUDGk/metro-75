"""NPC daily/weekly routines (rule-based, no LLM).

Each NPC has a schedule: list of (start_h, end_h, location_key, status).
Locations resolve to world.landmarks coordinates.
'home' is a special key meaning the NPC's initial position.
'wander' picks a random landmark from a small per-faction list.

Called from tick_once each sim-hour for NPCs only (active=False).
"""
from __future__ import annotations
import random
from .world import World


# Generic schedule templates -------------------------------------------------
def _t(*ranges):
    """Helper: build a schedule list from (start, end, location, status) tuples."""
    return list(ranges)


WORK_FAMILY_PARENT_WEEKDAY = _t(
    (0, 6, 'home', 'sleeping'),
    (6, 7, 'home', 'morning_routine'),
    (7, 18, '__work__', 'working'),
    (18, 19, '__commute__', 'commuting'),
    (19, 22, 'home', 'home'),
    (22, 24, 'home', 'sleeping'),
)
WORK_FAMILY_PARENT_WEEKEND = _t(
    (0, 9, 'home', 'sleeping'),
    (9, 13, 'home', 'home'),
    (13, 17, 'central_plaza', 'leisure'),
    (17, 22, 'home', 'home'),
    (22, 24, 'home', 'sleeping'),
)

KID_SCHOOL_WEEKDAY = _t(
    (0, 7, 'home', 'sleeping'),
    (7, 8, 'home', 'morning_routine'),
    (8, 15, '__school__', 'studying'),
    (15, 18, 'central_plaza', 'play'),
    (18, 21, 'home', 'home'),
    (21, 24, 'home', 'sleeping'),
)
KID_SCHOOL_WEEKEND = _t(
    (0, 9, 'home', 'sleeping'),
    (9, 12, 'home', 'home'),
    (12, 17, 'garrison_park', 'play'),
    (17, 21, 'home', 'home'),
    (21, 24, 'home', 'sleeping'),
)

ELDERLY_HOME_WEEKDAY = _t(
    (0, 7, 'home', 'sleeping'),
    (7, 22, 'home', 'home'),
    (22, 24, 'home', 'sleeping'),
)
ELDERLY_HOME_SUNDAY = _t(
    (0, 7, 'home', 'sleeping'),
    (7, 9, 'home', 'morning_routine'),
    (9, 12, 'st_marys_church', 'praying'),
    (12, 22, 'home', 'home'),
    (22, 24, 'home', 'sleeping'),
)

DRIFTER_WANDER = _t(
    (0, 6, 'home', 'sleeping'),
    (6, 12, '__wander_morning__', 'wandering'),
    (12, 18, '__wander_day__', 'wandering'),
    (18, 24, '__wander_evening__', 'wandering'),
)

POLICE_NPC_DAY = _t(
    (0, 8, 'home', 'sleeping'),
    (8, 17, 'police_station', 'on_duty'),
    (17, 22, 'home', 'home'),
    (22, 24, 'home', 'sleeping'),
)
POLICE_NPC_NIGHT = _t(  # alternating shift
    (0, 8, 'police_station', 'on_duty'),
    (8, 17, 'home', 'sleeping'),
    (17, 24, 'police_station', 'on_duty'),
)

GANG_NPC_DAY = _t(
    (0, 10, 'home', 'sleeping'),
    (10, 18, 'home', 'on_duty'),  # at HQ
    (18, 23, 'oreillys_bar', 'social'),
    (23, 24, 'home', 'home'),
)

PRIEST_DAILY = _t(
    (0, 6, 'home', 'sleeping'),
    (6, 21, 'st_marys_church', 'on_duty'),
    (21, 24, 'home', 'sleeping'),
)

BARTENDER = _t(
    (0, 4, 'oreillys_bar', 'on_duty'),
    (4, 12, 'home', 'sleeping'),
    (12, 16, 'home', 'home'),
    (16, 24, 'oreillys_bar', 'on_duty'),
)

SHOPKEEPER = _t(
    (0, 7, 'home', 'sleeping'),
    (7, 9, 'home', 'morning_routine'),
    (9, 21, 'corner_store_park', 'on_duty'),
    (21, 22, 'home', 'commuting'),
    (22, 24, 'home', 'sleeping'),
)


# NPC-specific work locations. For parents/workers, where they work.
NPC_WORK = {
    'fam_morales_dad': 'central_market',     # construction nearby
    'fam_morales_mom': 'corner_store_park',  # cleaning
    'fam_oconnell_dad': 'oreillys_bar',      # plumber, hangs at bar
    'fam_oconnell_wife': 'central_market',   # cashier
    'fam_park_daughter': 'central_library',  # librarian
    'fam_johnson_dad': 'home',                # retired
    'fam_johnson_wife': 'st_marys_church',   # choir leader
    'fam_silva_dad': 'gas_north',            # gas station attendant
    'fam_silva_wife': 'home',                # babysitter (home-based)
}

NPC_SCHOOL = {
    'fam_morales_daughter': 'jefferson_high',
    'fam_oconnell_son': 'jefferson_high',
    'fam_park_kid': 'lincoln_elementary',
    'fam_johnson_son': 'central_library',  # college, study at library
    'fam_silva_kid': 'lincoln_elementary',
}


# ===== Per-NPC schedule assignment =====
ROUTINE = {
    # Police NPCs (4)
    'police_npc1': {'weekday': POLICE_NPC_DAY, 'weekend': POLICE_NPC_DAY},
    'police_npc2': {'weekday': POLICE_NPC_NIGHT, 'weekend': POLICE_NPC_NIGHT},
    'police_npc3': {'weekday': POLICE_NPC_DAY, 'weekend': POLICE_NPC_DAY},
    'police_npc4': {'weekday': POLICE_NPC_DAY, 'weekend': POLICE_NPC_NIGHT},
    # Civilians (3)
    'civ_priest': {'weekday': PRIEST_DAILY, 'weekend': PRIEST_DAILY},
    'civ_bartender': {'weekday': BARTENDER, 'weekend': BARTENDER},
    'civ_shopkeeper': {'weekday': SHOPKEEPER, 'weekend': SHOPKEEPER},
    # Family parents
    'fam_morales_dad':    {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': WORK_FAMILY_PARENT_WEEKEND},
    'fam_morales_mom':    {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': WORK_FAMILY_PARENT_WEEKEND},
    'fam_oconnell_dad':   {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': WORK_FAMILY_PARENT_WEEKEND},
    'fam_oconnell_wife':  {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': WORK_FAMILY_PARENT_WEEKEND},
    'fam_johnson_dad':    {'weekday': ELDERLY_HOME_WEEKDAY, 'weekend': ELDERLY_HOME_WEEKDAY, 'sunday': ELDERLY_HOME_SUNDAY},
    'fam_johnson_wife':   {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': ELDERLY_HOME_SUNDAY},
    'fam_park_daughter':  {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': WORK_FAMILY_PARENT_WEEKEND},
    'fam_park_grandma':   {'weekday': ELDERLY_HOME_WEEKDAY, 'weekend': ELDERLY_HOME_WEEKDAY, 'sunday': ELDERLY_HOME_SUNDAY},
    'fam_silva_dad':      {'weekday': WORK_FAMILY_PARENT_WEEKDAY, 'weekend': WORK_FAMILY_PARENT_WEEKEND},
    'fam_silva_wife':     {'weekday': ELDERLY_HOME_WEEKDAY, 'weekend': ELDERLY_HOME_WEEKDAY},
    # Family kids
    'fam_morales_daughter': {'weekday': KID_SCHOOL_WEEKDAY, 'weekend': KID_SCHOOL_WEEKEND},
    'fam_oconnell_son':     {'weekday': KID_SCHOOL_WEEKDAY, 'weekend': KID_SCHOOL_WEEKEND},
    'fam_park_kid':         {'weekday': KID_SCHOOL_WEEKDAY, 'weekend': KID_SCHOOL_WEEKEND},
    'fam_johnson_son':      {'weekday': KID_SCHOOL_WEEKDAY, 'weekend': KID_SCHOOL_WEEKEND},
    'fam_silva_kid':        {'weekday': KID_SCHOOL_WEEKDAY, 'weekend': KID_SCHOOL_WEEKEND},
    # Drifters (8) — all wander
    'drift_homeless_jim':       {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_addict_riley':       {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_tourist_emma':       {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_truck_driver_carl':  {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_runaway_destiny':    {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_preacher_silas':     {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_taxi_drik':          {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
    'drift_busker_zeke':        {'weekday': DRIFTER_WANDER, 'weekend': DRIFTER_WANDER},
}


WANDER_LOCATIONS = {
    'morning':   ['central_plaza', 'corner_store_park', 'mings_diner', 'gas_north'],
    'day':       ['central_market', 'central_library', 'east_grocery', 'st_marys_church'],
    'evening':   ['oreillys_bar', 'lucky7_bar', 'corner_pizza', 'sakura_sushi'],
}


def _resolve_location(world: World, agent_id: str, agent_x0: int, agent_y0: int,
                      key: str, hour: int, rng: random.Random) -> tuple[int, int]:
    """Resolve a schedule location key to (x, y)."""
    if key == 'home':
        return (agent_x0, agent_y0)  # use initial position as home
    if key == '__work__':
        work = NPC_WORK.get(agent_id, 'home')
        if work == 'home': return (agent_x0, agent_y0)
        lm = world.landmarks.get(work)
        return tuple(lm) if lm else (agent_x0, agent_y0)
    if key == '__school__':
        school = NPC_SCHOOL.get(agent_id, 'jefferson_high')
        lm = world.landmarks.get(school)
        return tuple(lm) if lm else (agent_x0, agent_y0)
    if key == '__commute__':
        # midway between home and work — placeholder, just use home for simplicity
        return (agent_x0, agent_y0)
    if key.startswith('__wander_'):
        period = key.replace('__wander_', '').rstrip('_')  # 'morning', 'day', 'evening'
        choices = WANDER_LOCATIONS.get(period, ['central_plaza'])
        choice = rng.choice(choices)
        lm = world.landmarks.get(choice)
        return tuple(lm) if lm else (agent_x0, agent_y0)
    # Direct landmark key
    lm = world.landmarks.get(key)
    return tuple(lm) if lm else (agent_x0, agent_y0)


def apply_schedules(agents: dict, world: World, home_positions: dict[str, tuple[int, int]]):
    """Update NPC positions/statuses based on world.day, world.hour, weekday.
    home_positions: {agent_id: (x0, y0)} initial positions to use as 'home'.
    """
    rng = random.Random(world.day * 24 + world.hour)  # deterministic per sim-hour
    weekday = world.weekday()  # 0-6
    is_sunday = (weekday == 6)
    is_weekend = world.is_weekend()
    cur_h = world.hour

    for aid, agent in agents.items():
        if agent.active or agent.status in ('dead', 'arrested'):
            continue
        rt = ROUTINE.get(aid)
        if not rt:
            continue
        # Pick schedule list for today
        if is_sunday and 'sunday' in rt:
            schedule = rt['sunday']
        elif is_weekend:
            schedule = rt.get('weekend', rt['weekday'])
        else:
            schedule = rt['weekday']

        # Find current activity
        for (start_h, end_h, loc_key, status) in schedule:
            if start_h <= cur_h < end_h:
                home_x, home_y = home_positions.get(aid, (agent.x, agent.y))
                new_x, new_y = _resolve_location(world, aid, home_x, home_y, loc_key, cur_h, rng)
                agent.x, agent.y = new_x, new_y
                agent.status = status if status not in ('dead', 'arrested') else agent.status
                break
