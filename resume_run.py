"""Resume metro-75 sim from a daily_state checkpoint."""
import sys, io, os, json, time, glob, signal, shutil, argparse, re, sqlite3
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from sim.world import World
from sim.agent import AgentState
from sim.memory import Memory
from sim.tick import Simulation
from sim.render import render
from sim import llm
from sim.diary import generate_diary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, help='Source run dir to copy state from')
    parser.add_argument('--from-day', type=int, default=None,
                        help='Resume from daily_state/dayNN.json (sim time = Day N 23:00)')
    parser.add_argument('--from-checkpoint', action='store_true',
                        help='Resume from latest_checkpoint.json (any sim hour)')
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--no-discord', action='store_true')
    args = parser.parse_args()
    if not args.from_checkpoint and args.from_day is None:
        parser.error('Either --from-day N or --from-checkpoint required')

    ts = time.strftime('%Y%m%d_%H%M%S')
    log_dir = os.path.join('logs', f'resume_{ts}')
    snap_dir = os.path.join(log_dir, 'snapshots')
    daily_dir = os.path.join(log_dir, 'daily_state')
    os.makedirs(snap_dir, exist_ok=True)
    os.makedirs(daily_dir, exist_ok=True)
    print(f'Resume log dir: {log_dir}')

    # Copy existing logs/snapshots/daily_state for continuity
    for fname in ['events.log', 'dialogue.log']:
        src = os.path.join(args.source, fname)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(log_dir, fname))
    for f in glob.glob(os.path.join(args.source, 'snapshots', '*.png')):
        shutil.copy(f, snap_dir)
    for f in glob.glob(os.path.join(args.source, 'daily_state', '*.json')):
        shutil.copy(f, daily_dir)

    # Pick source state: checkpoint takes priority
    new_db = os.path.join(log_dir, 'memory.db')
    shutil.copy(os.path.join(args.source, 'memory.db'), new_db)

    if args.from_checkpoint:
        ckpt_file = os.path.join(args.source, 'latest_checkpoint.json')
        with open(ckpt_file, encoding='utf-8') as f:
            state = json.load(f)
        sim_time_str = state['sim_time']
        print(f'Resuming from checkpoint: {sim_time_str}')
        # Truncate memory entries strictly past this checkpoint
        cutoff = sim_time_str  # 'Day N HH:MM'
    else:
        state_file = os.path.join(args.source, 'daily_state', f'day{args.from_day:02d}.json')
        with open(state_file, encoding='utf-8') as f:
            state = json.load(f)
        sim_time_str = state['sim_time']
        print(f'Resuming from daily_state: {sim_time_str}')
        cutoff = f'Day {args.from_day} 23:59'

    conn = sqlite3.connect(new_db)
    cur = conn.execute('DELETE FROM memory WHERE sim_time > ?', (cutoff,))
    print(f'Truncated {cur.rowcount} memory entries past {cutoff}')
    conn.commit(); conn.close()

    # World (advance clock to checkpoint)
    world = World.load('map/metro.json')
    if 'world' in state:
        # checkpoint format
        world.day = state['world']['day']
        world.hour = state['world']['hour']
        world.minute = state['world']['minute']
    else:
        m = re.match(r'Day (\d+) (\d+):(\d+)', sim_time_str)
        world.day, world.hour, world.minute = int(m.group(1)), int(m.group(2)), int(m.group(3))

    # All personas
    agents = {}
    for f in sorted(glob.glob('personas/*.json')):
        with open(f, encoding='utf-8') as fh:
            d = json.load(fh)
        agents[d['id']] = AgentState(
            id=d['id'], name=d['name'], faction=d['faction'],
            active=d.get('active', False),
            x=d['x'], y=d['y'],
            persona=d.get('persona', {}),
            alias=d.get('alias', ''),
        )

    # Override active agents from checkpoint
    state_agents = {a['id']: a for a in state['agents']}
    for aid, sa in state_agents.items():
        if aid in agents:
            a = agents[aid]
            a.x = sa['x']; a.y = sa['y']
            a.hp = sa['hp']; a.status = sa['status']
            a.inventory = sa.get('inventory', {})
            a.current_plan = sa.get('current_plan', '')
            a.recent_actions = sa.get('recent_actions', [])
            a.recent_speech = sa.get('recent_speech', [])
            # Checkpoint format includes pending_response
            if 'pending_response_to' in sa:
                a.pending_response_to = sa['pending_response_to']
                a.pending_response_msg = sa.get('pending_response_msg', '')
    print(f'Loaded {len(agents)} agents, active={sum(1 for a in agents.values() if a.active)}')

    mems = {aid: Memory(new_db, aid) for aid in agents}

    # If resuming from checkpoint, also restore Day-0 scheduler state
    scheduler = None
    if args.from_checkpoint and 'scheduler_fired' in state:
        from sim.events import EVENTS_DAY0, EventScheduler
        scheduler = EventScheduler(EVENTS_DAY0, agents, mems)
        scheduler.fired = set(state['scheduler_fired'])

    sim = Simulation(
        world=world, agents=agents, memories=mems,
        event_log_path=os.path.join(log_dir, 'events.log'),
        dialogue_log_path=os.path.join(log_dir, 'dialogue.log'),
        event_scheduler=scheduler,
        action_interval_sim_min=60,
        reflect_interval_sim_min=240,
        sim_minutes_per_tick=1,
    )
    # Restore tick-level state if checkpoint
    if args.from_checkpoint:
        sim._last_action = state.get('last_action', {})
        sim._last_reflect = state.get('last_reflect', {})
        sim._last_plan_day = state.get('last_plan_day', {})
    else:
        sim._last_plan_day = {a.id: world.day for a in agents.values()}
    print(f'Workers: {sim.workers}, hosts: {llm.OLLAMA_HOSTS}')

    print('Warming up hosts...')
    warm = llm.warmup_all()
    for h, info in warm.items():
        print(f'  {h}: {"OK" if info["ok"] else "FAIL"} ({info["sec"]}s)')

    target_min = args.days * 1440
    SNAPSHOT_EVERY = 240
    last_snapshot_min = sim.cur_minute()
    if args.from_checkpoint:
        # Mid-day checkpoint: this day's diary not yet fired
        last_day_dumped = world.day - 1
        last_diary_day = world.day - 1
    else:
        # Daily-state resume: last day already fully dumped + diaried
        last_day_dumped = world.day
        last_diary_day = world.day
    last_checkpoint_min = sim.cur_minute()
    t_start = time.time()
    last_progress = t_start

    stop_flag = {'stop': False}
    def _on_signal(sig, frame):
        print(f'\n!! signal {sig}, graceful stop...')
        stop_flag['stop'] = True
    signal.signal(signal.SIGINT, _on_signal)

    try:
        while sim.cur_minute() < target_min and not stop_flag['stop']:
            sim.tick_once()
            cur = sim.cur_minute()

            if cur // SNAPSHOT_EVERY > last_snapshot_min // SNAPSHOT_EVERY:
                last_snapshot_min = cur
                fname = f'D{world.day:02d}_H{world.hour:02d}.png'
                render(world, agents, tile_px=4,
                       out_path=os.path.join(snap_dir, fname),
                       title=world.time_str())

            # Tick-level checkpoint every sim-hour
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
                os.replace(tmp_path, ckpt_path)

            if world.day != last_day_dumped and world.hour == 23:
                ds = {
                    'sim_time': world.time_str(),
                    'agents': [
                        {'id': a.id, 'name': a.name, 'faction': a.faction,
                         'x': a.x, 'y': a.y, 'hp': a.hp, 'status': a.status,
                         'inventory': a.inventory, 'current_plan': a.current_plan,
                         'recent_actions': a.recent_actions[-5:],
                         'recent_speech': a.recent_speech[-5:]}
                        for a in agents.values() if a.active
                    ],
                }
                with open(os.path.join(daily_dir, f'day{world.day:02d}.json'), 'w', encoding='utf-8') as f:
                    json.dump(ds, f, ensure_ascii=False, indent=2)
                last_day_dumped = world.day
                sim.save_event_log()

                if not args.no_discord and world.day != last_diary_day:
                    snap_path = os.path.join(snap_dir, f'D{world.day:02d}_H20.png')
                    if not os.path.exists(snap_path):
                        snaps = sorted(glob.glob(os.path.join(snap_dir, f'D{world.day:02d}_*.png')))
                        snap_path = snaps[-1] if snaps else None
                    print(f'[{world.time_str()}] generating diary for Day {world.day}...')
                    diary = generate_diary(sim, world.day, log_dir, snap_path)
                    print(f'  diary posted={diary["posted"]} events={diary["events_count"]}')
                    last_diary_day = world.day

            if time.time() - last_progress > 60:
                pool_stats = llm.pool.stats()
                print(f'[{world.time_str()}] elapsed={int(time.time()-t_start)}s '
                      f'llm_calls={sim.tick_stats["llm_calls"]} errors={sim.tick_stats["llm_errors"]} '
                      f'pool={pool_stats["req"]}')
                last_progress = time.time()

    except KeyboardInterrupt:
        print('!! KeyboardInterrupt')
    finally:
        sim.save_event_log()
        sim.shutdown()
        render(world, agents, tile_px=4,
               out_path=os.path.join(log_dir, 'final.png'),
               title=f'FINAL {world.time_str()}')
        elapsed = int(time.time() - t_start)
        print(f'\n=== resume DONE === final={world.time_str()}, elapsed={elapsed}s')


if __name__ == '__main__':
    main()
