"""Short smoke test: 3 agents, 5 sim-hours (10 decisions each at 30-min interval)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json, time, os, tempfile

from sim.world import World
from sim.agent import AgentState
from sim.memory import Memory, MemoryEntry
from sim.tick import Simulation
from sim.render import render

world = World.load('map/metro.json')

# Pick 3 test agents
ids = ['police_diaz', 'kings_marcus', 'vig_stone']
agents = {}
for aid in ids:
    with open(f'personas/{aid}.json', encoding='utf-8') as f:
        d = json.load(f)
    agents[aid] = AgentState(
        id=d['id'], name=d['name'], faction=d['faction'],
        active=True, x=d['x'], y=d['y'], persona=d['persona'],
    )

log_dir = tempfile.mkdtemp(prefix='metro_test_')
print(f'Log dir: {log_dir}')
db = os.path.join(log_dir, 'mem.db')
mems = {aid: Memory(db, aid) for aid in agents}

# Seed
for mem in mems.values():
    mem.add(MemoryEntry(
        ts=time.time(), sim_time='Day 0 05:59', kind='observation',
        content="Ice cream truck on E Jackson St, 3 days parked, no customers.",
        importance=5,
    ))

sim = Simulation(world, agents, mems,
                 event_log_path=os.path.join(log_dir, 'events.log'),
                 action_interval_sim_min=30, sim_minutes_per_tick=1)

# Run 5 sim-hours = 300 sim-min = 10 decisions per agent
t0 = time.time()
for i in range(300):
    sim.tick_once()
    if i % 60 == 0:
        print(f'[{world.time_str()}] (+{time.time()-t0:.0f}s)')
sim.save_event_log()
print(f'\nTotal: {time.time()-t0:.0f}s')

print('\n=== Event log ===')
with open(os.path.join(log_dir, 'events.log'), encoding='utf-8') as f:
    print(f.read())

# Render final state
render(world, agents, tile_px=3, out_path=os.path.join(log_dir, 'final.png'),
       title=world.time_str())
print(f'\nFinal render: {log_dir}/final.png')
