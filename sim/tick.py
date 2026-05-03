"""Main tick loop with planning, reflection, scripted events.

Parallelism model:
  Phase 1 (sync): identify which agents need plan/reflect/decide, snapshot world state.
  Phase 2 (parallel): submit all LLM calls via ThreadPoolExecutor, capped by host pool.
  Phase 3 (sync): apply results in deterministic order — memory writes, position updates,
                  broadcasts, witness events. No races because only main thread mutates here.
  Phase 4: advance world time.

Why this works: decide_action / generate_daily_plan / reflect only read state;
execute_action / broadcast_chat / witness_event are the only mutators and run in main thread.
"""
from __future__ import annotations
import time
import concurrent.futures as cf

from .world import World
from .agent import AgentState, decide_action, execute_action
from .memory import Memory, MemoryEntry
from .cognition import generate_daily_plan, reflect
from .events import EventScheduler
from . import llm
from .npc_routine import apply_schedules as _apply_npc_schedules


class Simulation:
    def __init__(self, world: World, agents: dict[str, AgentState],
                 memories: dict[str, Memory], event_log_path: str,
                 event_scheduler: EventScheduler | None = None,
                 action_interval_sim_min: int = 60,
                 reflect_interval_sim_min: int = 240,
                 sim_minutes_per_tick: int = 1,
                 max_workers: int | None = None,
                 dialogue_log_path: str | None = None):
        self.world = world
        self.agents = agents
        self.memories = memories
        self.event_log_path = event_log_path
        self.dialogue_log_path = dialogue_log_path
        self.event_log: list[str] = []
        self.dialogue_log: list[str] = []
        self.chat_broadcast: list[tuple[str, int, int, str, str]] = []
        self.action_interval = action_interval_sim_min
        self.reflect_interval = reflect_interval_sim_min
        self.sim_minutes_per_tick = sim_minutes_per_tick
        self._last_action: dict[str, int] = {}
        self._last_reflect: dict[str, int] = {}
        self._last_plan_day: dict[str, int] = {}
        self.scheduler = event_scheduler

        # Worker count = max(2, host pool size). Host pool semaphore caps actual LLM concurrency.
        workers = max_workers or max(2, len(llm.pool.hosts))
        self.executor = cf.ThreadPoolExecutor(max_workers=workers, thread_name_prefix='sim')
        self.workers = workers

        # NPC home positions = initial positions snapshot at start
        self.npc_home: dict[str, tuple[int, int]] = {
            aid: (a.x, a.y) for aid, a in agents.items() if not a.active
        }
        self._last_npc_update_min: int = -1

        # Stats
        self.tick_stats = {
            'total_ticks': 0,
            'llm_calls': 0,
            'llm_errors': 0,
        }

    def shutdown(self):
        self.executor.shutdown(wait=True)

    def save_event_log(self):
        if self.event_log:
            with open(self.event_log_path, 'a', encoding='utf-8') as f:
                for line in self.event_log:
                    f.write(line + '\n')
            self.event_log.clear()
        if self.dialogue_log_path and self.dialogue_log:
            with open(self.dialogue_log_path, 'a', encoding='utf-8') as f:
                for line in self.dialogue_log:
                    f.write(line + '\n')
            self.dialogue_log.clear()

    def broadcast_chat(self, agent: AgentState, message: str, range_tiles: int = 10):
        rec = (self.world.time_str(), agent.x, agent.y, agent.name, message)
        self.chat_broadcast.append(rec)
        self.dialogue_log.append(f'[{rec[0]}] ({agent.faction}) {agent.name}@({agent.x},{agent.y}): 「{message}」')
        for other in self.agents.values():
            if other.id == agent.id: continue
            dist = max(abs(other.x - agent.x), abs(other.y - agent.y))
            if dist <= range_tiles and other.active and other.status not in ('dead', 'arrested'):
                self.memories[other.id].add(MemoryEntry(
                    ts=time.time(), sim_time=self.world.time_str(),
                    kind='conversation',
                    content=f'{agent.name} の発言を聞いた: 「{message}」',
                    importance=4 if range_tiles <= 3 else 3,
                ))
                if dist <= 5 and not other.pending_response_to:
                    other.pending_response_to = agent.id
                    other.pending_response_msg = message[:120]

    def witness_event(self, actor: AgentState, victim: AgentState, kind: str, detail: str):
        for w in self.agents.values():
            if w.id in (actor.id, victim.id): continue
            wd = max(abs(w.x - actor.x), abs(w.y - actor.y))
            if wd <= 8 and w.active and w.status not in ('dead', 'arrested'):
                self.memories[w.id].add(MemoryEntry(
                    ts=time.time(), sim_time=self.world.time_str(),
                    kind='witness',
                    content=f'目撃: {actor.name} が {victim.name} を {detail}',
                    importance=8,
                ))

    def cur_minute(self) -> int:
        return self.world.day * 1440 + self.world.hour * 60 + self.world.minute

    def _build_snapshot(self, agent: AgentState) -> dict:
        nearby_agents = []
        for other in self.agents.values():
            if other.id == agent.id: continue
            if other.status == 'dead': continue
            dist = max(abs(other.x - agent.x), abs(other.y - agent.y))
            if dist <= 10:
                nearby_agents.append({
                    'id': other.id, 'name': other.name, 'alias': other.alias,
                    'faction': other.faction,
                    'x': other.x, 'y': other.y, 'status': other.status,
                })
        nearby_chat = [f'{s}: {m}' for (t, x, y, s, m) in self.chat_broadcast[-15:]
                       if max(abs(x - agent.x), abs(y - agent.y)) <= 10]
        return {'nearby_agents': nearby_agents, 'nearby_chat': nearby_chat}

    def tick_once(self):
        # Fire scripted events
        if self.scheduler:
            self.scheduler.tick(self.world)

        cur = self.cur_minute()
        self.tick_stats['total_ticks'] += 1

        # Update NPC positions/statuses by schedule (once per sim-hour)
        if cur // 60 > self._last_npc_update_min // 60:
            self._last_npc_update_min = cur
            _apply_npc_schedules(self.agents, self.world, self.npc_home)

        # Phase 1 — identify what each agent needs
        to_plan: list[AgentState] = []
        to_reflect: list[AgentState] = []
        to_act: list[AgentState] = []
        snapshots: dict[str, dict] = {}

        for aid, agent in self.agents.items():
            if not agent.active or agent.status in ('dead', 'arrested'):
                continue

            if (self.world.hour == 6 and self.world.minute == 0
                    and self._last_plan_day.get(aid) != self.world.day):
                to_plan.append(agent)
                self._last_plan_day[aid] = self.world.day  # claim slot now (avoid retries)

            # Stagger reflections per-agent so 25 reflections don't bunch at 4h-marks.
            # Phase offset = stable hash(agent_id) modulo interval.
            offset = (hash(aid) & 0xffff) % self.reflect_interval
            last_r = self._last_reflect.get(aid, -10**9)
            if (cur - offset) // self.reflect_interval > (last_r - offset) // self.reflect_interval and cur - last_r >= self.reflect_interval // 2:
                to_reflect.append(agent)
                self._last_reflect[aid] = cur

            if cur - self._last_action.get(aid, -10**9) >= self.action_interval:
                to_act.append(agent)
                self._last_action[aid] = cur
                snapshots[aid] = self._build_snapshot(agent)

        if not (to_plan or to_reflect or to_act):
            for _ in range(self.sim_minutes_per_tick):
                self.world.tick()
            return

        # Phase 2 — parallel LLM calls
        # Submit in priority order: plans first (they shape today's behavior), then reflections, then actions.
        plan_futs: dict[str, cf.Future] = {}
        reflect_futs: dict[str, cf.Future] = {}
        act_futs: dict[str, cf.Future] = {}

        for a in to_plan:
            plan_futs[a.id] = self.executor.submit(generate_daily_plan, a, self.world, self.memories[a.id])
        for a in to_reflect:
            reflect_futs[a.id] = self.executor.submit(reflect, a, self.world, self.memories[a.id])
        for a in to_act:
            snap = snapshots[a.id]
            act_futs[a.id] = self.executor.submit(
                decide_action, a, self.world, self.memories[a.id],
                snap['nearby_agents'], snap['nearby_chat'],
            )

        # Phase 3 — apply sequentially in deterministic agent-id order
        # 3a: Plans
        for aid in sorted(plan_futs):
            try:
                plan = plan_futs[aid].result()
            except Exception as e:
                plan = ''
                self.tick_stats['llm_errors'] += 1
            self.tick_stats['llm_calls'] += 1
            if plan:
                agent = self.agents[aid]
                agent.current_plan = plan
                self.memories[aid].add(MemoryEntry(
                    ts=time.time(), sim_time=self.world.time_str(),
                    kind='plan', content=f'今日の計画: {plan}', importance=6,
                ))
                self.event_log.append(f'[{self.world.time_str()}] {agent.name}: [PLAN] {plan}')

        # 3b: Reflections (reflect() writes its own MemoryEntry; we just log)
        for aid in sorted(reflect_futs):
            try:
                insight = reflect_futs[aid].result()
            except Exception as e:
                insight = ''
                self.tick_stats['llm_errors'] += 1
            self.tick_stats['llm_calls'] += 1
            if insight:
                agent = self.agents[aid]
                self.event_log.append(f'[{self.world.time_str()}] {agent.name}: [REFLECT] {insight[:120]}')

        # 3c: Actions — apply with broadcasts/witnesses
        for aid in sorted(act_futs):
            try:
                result = act_futs[aid].result()
            except Exception as e:
                result = {'thought': f'(error: {e})', 'action': 'wait'}
                self.tick_stats['llm_errors'] += 1
            self.tick_stats['llm_calls'] += 1

            agent = self.agents[aid]
            thought = result['thought']
            action = result['action']

            if thought:
                self.memories[aid].add(MemoryEntry(
                    ts=time.time(), sim_time=self.world.time_str(),
                    kind='thought', content=thought, importance=2,
                ))

            attack_target = None
            arrest_target = None
            if action.startswith('attack '):
                attack_target = self.agents.get(action[7:].strip())
            elif action.startswith('arrest '):
                arrest_target = self.agents.get(action[7:].strip())

            execute_action(agent, action, self.world, self.agents, self.event_log, self.memories[aid])

            self.memories[aid].add(MemoryEntry(
                ts=time.time(), sim_time=self.world.time_str(),
                kind='action', content=f'実行: {action}', importance=2,
            ))

            if action.startswith('say '):
                msg = action[4:].strip().strip('"\'「」')
                self.broadcast_chat(agent, msg, range_tiles=10)
            elif action.startswith('whisper '):
                tokens = action[8:].split(maxsplit=1)
                if len(tokens) == 2:
                    self.broadcast_chat(agent, tokens[1], range_tiles=3)
            elif attack_target and attack_target.status in ('injured', 'dead'):
                self.witness_event(agent, attack_target, 'attack',
                                   '殺した' if attack_target.status == 'dead' else '攻撃した')
            elif arrest_target and arrest_target.status == 'arrested':
                self.witness_event(agent, arrest_target, 'arrest', '逮捕した')

        # Advance time
        for _ in range(self.sim_minutes_per_tick):
            self.world.tick()

        if len(self.event_log) > 30 or len(self.dialogue_log) > 10:
            self.save_event_log()

    def run_for_sim_days(self, num_days: int, on_progress=None):
        target = self.world.day * 1440 + num_days * 1440
        try:
            while self.cur_minute() < target:
                self.tick_once()
                if on_progress:
                    on_progress(self.world, self.agents, self.event_log)
        finally:
            self.save_event_log()
