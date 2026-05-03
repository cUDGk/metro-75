"""Metro-75 main entry: load map + personas, run simulation."""
from __future__ import annotations
import os
import sys
import json
import argparse
import time

from sim.world import World
from sim.agent import AgentState
from sim.memory import Memory
from sim.tick import Simulation
from sim.render import render
from sim.events import EVENTS_DAY0, EventScheduler

ROOT = os.path.dirname(os.path.abspath(__file__))


def load_world() -> World:
    return World.load(os.path.join(ROOT, 'map', 'metro.json'))


def load_agents(world: World) -> dict[str, AgentState]:
    agents = {}
    persona_dir = os.path.join(ROOT, 'personas')
    for fname in sorted(os.listdir(persona_dir)):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(persona_dir, fname), 'r', encoding='utf-8') as f:
            d = json.load(f)
        ag = AgentState(
            id=d['id'], name=d['name'], faction=d['faction'],
            active=d.get('active', True),
            x=d.get('x', world.width // 2), y=d.get('y', world.height // 2),
            persona=d.get('persona', {}),
        )
        agents[ag.id] = ag
    return agents


def init_memories(agents: dict[str, AgentState], db_path: str) -> dict[str, Memory]:
    mems = {}
    for aid in agents:
        mems[aid] = Memory(db_path, aid)
    return mems


def run_sim(sim_days: int = 1, snapshot_every_min: int = 60, action_interval_min: int = 30):
    world = load_world()
    agents = load_agents(world)
    active_n = sum(1 for a in agents.values() if a.active)
    print(f'Loaded world {world.width}x{world.height}, {len(agents)} agents ({active_n} active)')

    log_dir = os.path.join(ROOT, 'logs', time.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(log_dir, exist_ok=True)
    db_path = os.path.join(log_dir, 'memory.db')
    event_log_path = os.path.join(log_dir, 'events.log')
    print(f'Log dir: {log_dir}')

    memories = init_memories(agents, db_path)

    # Seed: put a scenario-level note in every agent's memory
    from sim.memory import MemoryEntry
    seed_note = (
        "It's Day 0, 06:00. The 28th Precinct has had doubled patrols for weeks under the new Captain Diaz. "
        "A white-and-pink ice cream truck has been parked on E. Jackson St for 3 days, no customers seen."
    )
    for aid, mem in memories.items():
        mem.add(MemoryEntry(
            ts=time.time(), sim_time='Day 0 05:59',
            kind='observation', content=seed_note, importance=5,
        ))

    scheduler = EventScheduler(EVENTS_DAY0, agents, memories)
    sim = Simulation(world, agents, memories, event_log_path,
                     event_scheduler=scheduler,
                     action_interval_sim_min=action_interval_min,
                     sim_minutes_per_tick=1)

    last_snapshot = -9999

    def on_progress(world, agents, events):
        nonlocal last_snapshot
        cur = world.day * 24 * 60 + world.hour * 60 + world.minute
        if cur - last_snapshot >= snapshot_every_min:
            snap = os.path.join(log_dir, f'snap_D{world.day}_H{world.hour:02d}.png')
            render(world, agents, tile_px=3, out_path=snap, title=world.time_str())
            print(f'[{world.time_str()}] snapshot → {snap}')
            last_snapshot = cur

    # Initial snapshot
    render(world, agents, tile_px=3,
           out_path=os.path.join(log_dir, 'snap_D0_H00_init.png'),
           title=world.time_str() + ' (init)')

    t0 = time.time()
    sim.run_for_sim_days(sim_days, on_progress=on_progress)
    dt = time.time() - t0
    print(f'Sim complete: {sim_days} sim-days in {dt/60:.1f} real-minutes')
    print(f'Event log: {event_log_path}')
    print(f'Memory DB: {db_path}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=1)
    ap.add_argument('--action_interval', type=int, default=30)
    ap.add_argument('--snapshot_every', type=int, default=60)
    args = ap.parse_args()
    run_sim(sim_days=args.days, snapshot_every_min=args.snapshot_every,
            action_interval_min=args.action_interval)
