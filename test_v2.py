"""V2 quality test: 5 agents, 8 sim-hours, with plan/reflect/events/JP chat."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json, time, tempfile

from sim.world import World
from sim.agent import AgentState
from sim.memory import Memory, MemoryEntry
from sim.tick import Simulation
from sim.events import EVENTS_DAY0, EventScheduler
from sim.render import render

world = World.load('map/metro.json')

ids = ['police_diaz', 'police_rivera', 'pm_cobra_devon', 'ph_wolf_malik', 'vig_stone']
agents = {}
for aid in ids:
    with open(f'personas/{aid}.json', encoding='utf-8') as f:
        d = json.load(f)
    agents[aid] = AgentState(
        id=d['id'], name=d['name'], faction=d['faction'],
        active=True, x=d['x'], y=d['y'], persona=d['persona'],
    )

# Spread them out a bit so movement testing actually moves
agents['police_rivera'].x = 130; agents['police_rivera'].y = 140  # near ice cream truck
agents['pm_cobra_devon'].x = 80; agents['pm_cobra_devon'].y = 80  # mid territory
agents['vig_stone'].x = 100; agents['vig_stone'].y = 160  # SW

log_dir = tempfile.mkdtemp(prefix='metro_v2_')
print(f'Log: {log_dir}')
db = os.path.join(log_dir, 'mem.db')
mems = {aid: Memory(db, aid) for aid in agents}

# Seed
for mem in mems.values():
    mem.add(MemoryEntry(
        ts=time.time(), sim_time='Day 0 05:59', kind='observation',
        content='Day 0、6時。アイスクリームトラックがE.Jackson通りに3日連続駐車中、客の出入りなし。署の警官倍増中。',
        importance=6,
    ))

scheduler = EventScheduler(EVENTS_DAY0, agents, mems)
sim = Simulation(world, agents, mems,
                 event_log_path=os.path.join(log_dir, 'events.log'),
                 event_scheduler=scheduler,
                 action_interval_sim_min=60,
                 reflect_interval_sim_min=240,
                 sim_minutes_per_tick=1)

t0 = time.time()
# 8 sim-hours = 480 sim-min
for i in range(480):
    sim.tick_once()
    if i % 60 == 0:
        print(f'[{world.time_str()}] +{int(time.time()-t0)}s')
sim.save_event_log()
print(f'\n=== TOTAL: {int(time.time()-t0)}s ===\n')

print('=== EVENTS ===')
with open(os.path.join(log_dir, 'events.log'), encoding='utf-8') as f:
    print(f.read())

render(world, agents, tile_px=4, out_path=os.path.join(log_dir, 'final.png'),
       title=world.time_str())
print(f'final: {log_dir}/final.png')
