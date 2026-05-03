"""Metro-75 simulation runner. All logs saved + daily Discord diary.

Usage:
  OLLAMA_HOSTS=http://127.0.0.1:11434,http://192.168.1.7:11434 python run_28day.py [--days N]
"""
import sys, io, os, json, time, glob, signal, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from sim.world import World
from sim.agent import AgentState
from sim.memory import Memory, MemoryEntry
from sim.tick import Simulation
from sim.events import EVENTS_DAY0, EventScheduler
from sim.render import render
from sim import llm
from sim.diary import generate_diary
from sim.digest import digest_all_active


# ===== CONFIG =====
SNAPSHOT_EVERY_SIM_MIN = 4 * 60   # every 4 sim-hours = 6/day
DAILY_DUMP = True                  # daily JSON state dump
ACTION_INTERVAL_SIM_MIN = 60       # agents act once per sim-hour
REFLECT_INTERVAL_SIM_MIN = 240     # reflection every 4 sim-hours
SIM_MIN_PER_TICK = 1


def load_agents(personas_dir: str = 'personas') -> dict[str, AgentState]:
    agents = {}
    for f in sorted(glob.glob(os.path.join(personas_dir, '*.json'))):
        with open(f, encoding='utf-8') as fh:
            d = json.load(fh)
        agents[d['id']] = AgentState(
            id=d['id'], name=d['name'], faction=d['faction'],
            active=d.get('active', False),
            x=d['x'], y=d['y'],
            persona=d.get('persona', {}),
            alias=d.get('alias', ''),
        )
    return agents


def seed_memories(agents: dict, mems: dict, world: World):
    """Inject Day 0 06:00 grounding memories per faction."""
    seeds = {
        'police': 'Day 0、06:00。アイスクリームトラックの監視オペは順調に3日目。今朝、ディアス警部から全員巡回倍増の通達。FBI連携の話あり。',
        'gang_a': 'Day 0、06:00。最近、警察の巡回が明らかに増えてる。中央のアイスクリームトラックも違和感。ガーネット内部はピリピリしてる。',
        'gang_b': 'Day 0、06:00。警察の動きが活発。中央のアイスクリームトラックが3日駐車してて客ゼロ — 何かある。',
        'gang_c': 'Day 0、06:00。コブラキラーは今日もカラブレーゼ商会の表で営業中。ガーネット Cobra Set との緊張は依然続く。',
        'vigilante': 'Day 0、06:00。街がざわついてる。警察の動きも、ギャングの動きも、何か来そうな予感。',
    }
    for aid, agent in agents.items():
        if not agent.active: continue
        seed = seeds.get(agent.faction, 'Day 0、06:00。いつもの朝。')
        mems[aid].add(MemoryEntry(
            ts=time.time(), sim_time='Day 0 05:59',
            kind='observation', content=seed, importance=5,
        ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=28, help='Number of sim-days to run')
    parser.add_argument('--no-discord', action='store_true', help='Skip Discord diary posting')
    args = parser.parse_args()
    num_sim_days = args.days

    ts = time.strftime('%Y%m%d_%H%M%S')
    log_dir = os.path.join('logs', f'run{num_sim_days}day_{ts}')
    os.makedirs(log_dir, exist_ok=True)
    snap_dir = os.path.join(log_dir, 'snapshots')
    daily_dir = os.path.join(log_dir, 'daily_state')
    os.makedirs(snap_dir, exist_ok=True)
    os.makedirs(daily_dir, exist_ok=True)

    print(f'=== Metro-75 {num_sim_days}-day run ===')
    print(f'Log dir: {log_dir}')
    print(f'Hosts: {llm.OLLAMA_HOSTS}')
    print(f'Model: {llm.MODEL_NAME}')

    # Warm up all LLM hosts in parallel
    print(f'Warming up {len(llm.OLLAMA_HOSTS)} hosts...')
    warm = llm.warmup_all()
    for host, info in warm.items():
        print(f'  {host}: {"OK" if info["ok"] else "FAIL"} ({info["sec"]}s) — {info["msg"]}')
    if not all(v['ok'] for v in warm.values()):
        print('!! some hosts failed warmup. continue anyway.')

    # World + agents
    world = World.load('map/metro.json')
    agents = load_agents()
    n_total = len(agents)
    n_active = sum(1 for a in agents.values() if a.active)
    print(f'Loaded {n_total} agents ({n_active} active)')

    db = os.path.join(log_dir, 'memory.db')
    mems = {aid: Memory(db, aid) for aid in agents}
    seed_memories(agents, mems, world)

    scheduler = EventScheduler(EVENTS_DAY0, agents, mems)

    sim = Simulation(
        world=world, agents=agents, memories=mems,
        event_log_path=os.path.join(log_dir, 'events.log'),
        dialogue_log_path=os.path.join(log_dir, 'dialogue.log'),
        event_scheduler=scheduler,
        action_interval_sim_min=ACTION_INTERVAL_SIM_MIN,
        reflect_interval_sim_min=REFLECT_INTERVAL_SIM_MIN,
        sim_minutes_per_tick=SIM_MIN_PER_TICK,
    )
    print(f'Workers: {sim.workers}, host pool: {len(llm.pool.hosts)}')

    # Graceful shutdown
    stop_flag = {'stop': False}
    def _on_signal(sig, frame):
        print(f'\n!! signal {sig}, requesting graceful stop after current tick...')
        stop_flag['stop'] = True
    signal.signal(signal.SIGINT, _on_signal)

    target_min = num_sim_days * 1440
    last_snapshot_min = -1
    last_day_dumped = -1
    last_diary_day = -1
    last_checkpoint_min = -1
    t_start = time.time()
    last_progress = t_start

    try:
        while sim.cur_minute() < target_min and not stop_flag['stop']:
            sim.tick_once()
            cur = sim.cur_minute()

            # Snapshot every 4 sim-hours
            if cur // SNAPSHOT_EVERY_SIM_MIN > last_snapshot_min // SNAPSHOT_EVERY_SIM_MIN:
                last_snapshot_min = cur
                fname = f'D{world.day:02d}_H{world.hour:02d}.png'
                render(world, agents, tile_px=4,
                       out_path=os.path.join(snap_dir, fname),
                       title=world.time_str())

            # Tick-level checkpoint every sim-hour (overwrite latest_checkpoint.json)
            if cur // 60 > last_checkpoint_min // 60:
                last_checkpoint_min = cur
                ckpt = {
                    'sim_time': world.time_str(),
                    'world': {'day': world.day, 'hour': world.hour, 'minute': world.minute},
                    'agents': [
                        {'id': a.id, 'x': a.x, 'y': a.y, 'hp': a.hp, 'status': a.status,
                         'inventory': a.inventory, 'current_plan': a.current_plan,
                         'recent_actions': a.recent_actions[-5:],
                         'recent_speech': a.recent_speech[-5:],
                         'pending_response_to': a.pending_response_to,
                         'pending_response_msg': a.pending_response_msg}
                        for a in agents.values() if a.active
                    ],
                    'last_action': dict(sim._last_action),
                    'last_reflect': dict(sim._last_reflect),
                    'last_plan_day': dict(sim._last_plan_day),
                    'scheduler_fired': sorted(sim.scheduler.fired) if sim.scheduler else [],
                }
                ckpt_path = os.path.join(log_dir, 'latest_checkpoint.json')
                tmp_path = ckpt_path + '.tmp'
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(ckpt, f, ensure_ascii=False)
                os.replace(tmp_path, ckpt_path)  # atomic write

            # Daily state dump + diary at end of each sim-day.
            # Fire at 23:01+ so the 23:00 action cycle is already written to memory.
            if DAILY_DUMP and world.day != last_day_dumped and world.hour == 23 and world.minute >= 1:
                state = {
                    'sim_time': world.time_str(),
                    'agents': [
                        {
                            'id': a.id, 'name': a.name, 'faction': a.faction,
                            'x': a.x, 'y': a.y, 'hp': a.hp, 'status': a.status,
                            'inventory': a.inventory,
                            'current_plan': a.current_plan,
                            'recent_actions': a.recent_actions[-5:],
                            'recent_speech': a.recent_speech[-5:],
                        }
                        for a in agents.values() if a.active
                    ],
                }
                with open(os.path.join(daily_dir, f'day{world.day:02d}.json'), 'w', encoding='utf-8') as f:
                    json.dump(state, f, ensure_ascii=False, indent=2)
                last_day_dumped = world.day

                # Flush logs so diary can read them
                sim.save_event_log()

                if not args.no_discord and world.day != last_diary_day:
                    snap_path = os.path.join(snap_dir, f'D{world.day:02d}_H20.png')
                    if not os.path.exists(snap_path):
                        # fallback: latest snapshot
                        snaps = sorted(glob.glob(os.path.join(snap_dir, f'D{world.day:02d}_*.png')))
                        snap_path = snaps[-1] if snaps else None
                    print(f'[{world.time_str()}] generating diary for Day {world.day}...')
                    diary = generate_diary(sim, world.day, log_dir, snap_path)
                    print(f'  diary posted={diary["posted"]}, events={diary["events_count"]}, dialogue={diary["dialogue_count"]}')
                    last_diary_day = world.day

                # Memory digest: fold low-importance entries from this day
                print(f'[{world.time_str()}] digesting Day {world.day} memories...')
                digest_stats = digest_all_active(agents, mems, world.day)
                folded = sum(s.get('entries_folded', 0) for s in digest_stats.values())
                print(f'  digested {len([s for s in digest_stats.values() if s.get("entries_folded",0)>0])} agents, {folded} entries folded')

            # Progress every 60 sec real time
            if time.time() - last_progress > 60:
                pool_stats = llm.pool.stats()
                print(f'[{world.time_str()}] elapsed={int(time.time()-t_start)}s '
                      f'llm_calls={sim.tick_stats["llm_calls"]} errors={sim.tick_stats["llm_errors"]} '
                      f'pool={pool_stats["req"]}')
                last_progress = time.time()

    except KeyboardInterrupt:
        print('!! KeyboardInterrupt — saving and exiting')

    finally:
        sim.save_event_log()
        sim.shutdown()

        # Final snapshot
        render(world, agents, tile_px=4,
               out_path=os.path.join(log_dir, 'final.png'),
               title=f'FINAL {world.time_str()}')

        elapsed = int(time.time() - t_start)
        summary = {
            'final_sim_time': world.time_str(),
            'days_completed': world.day + (world.hour / 24.0),
            'real_seconds': elapsed,
            'real_hours': round(elapsed / 3600, 2),
            'llm_calls': sim.tick_stats['llm_calls'],
            'llm_errors': sim.tick_stats['llm_errors'],
            'pool_stats': llm.pool.stats(),
            'agents_alive': sum(1 for a in agents.values() if a.active and a.status != 'dead'),
            'agents_dead': sum(1 for a in agents.values() if a.status == 'dead'),
            'agents_arrested': sum(1 for a in agents.values() if a.status == 'arrested'),
        }
        with open(os.path.join(log_dir, 'SUMMARY.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f'\n=== DONE ===')
        print(f'final: {world.time_str()}, elapsed: {elapsed}s ({elapsed/3600:.2f}h)')
        print(f'llm_calls: {summary["llm_calls"]}, errors: {summary["llm_errors"]}')
        print(f'logs: {log_dir}')


if __name__ == '__main__':
    main()
