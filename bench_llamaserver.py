"""Benchmark the llama-server with metro-75-style production prompts."""
import sys, io, time, json, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
os.environ.setdefault('LLM_HOSTS', 'http://192.168.1.7:8080,http://192.168.1.7:8080')

from sim.world import World
from sim.agent import AgentState, build_action_prompt
from sim.memory import Memory, MemoryEntry
from sim import llm
import concurrent.futures as cf
import tempfile

print(f'Hosts: {llm.OLLAMA_HOSTS}')

# Build a realistic production prompt for JAP28
world = World.load('map/metro.json')
with open('personas/mango_jap28.json', encoding='utf-8') as f: d = json.load(f)
a = AgentState(id=d['id'], name=d['name'], faction=d['faction'], active=True,
               x=d['x'], y=d['y'], persona=d['persona'], alias=d.get('alias',''))
td = tempfile.mkdtemp()
mem = Memory(f'{td}/m.db', a.id)
for i, txt in enumerate([
    'Day 0 朝、街の空気がやや張り詰めている',
    '昨日コブラ Set のチンピラがオフィス前を通った',
    'クィーンが今日の経理ミーティングは午後3時って',
    'アンクル・ジョーから軽い挨拶あった',
    '街の南で警察パトロールが増えてる噂',
]):
    mem.add(MemoryEntry(ts=time.time(), sim_time=f'Day 0 0{6+i}:00', kind='observation',
                        content=txt, importance=4))

# Add some nearby agents
nearby = [
    {'id': 'mango_npc1', 'name': 'ストレイ', 'alias': 'ストレイ', 'faction': 'gang_c',
     'x': 35, 'y': 219, 'status': 'normal'},
    {'id': 'mango_boss', 'name': 'アンクル・ジョー', 'alias': 'アンクル・ジョー',
     'faction': 'gang_c', 'x': 33, 'y': 215, 'status': 'normal'},
]

system, user = build_action_prompt(a, world, mem, nearby, [])
print(f'\n=== Production-like prompt ===')
print(f'system: {len(system)} chars (~{len(system)//3} tokens)')
print(f'user:   {len(user)} chars (~{len(user)//3} tokens)')
print(f'total:  {len(system)+len(user)} chars (~{(len(system)+len(user))//3} tokens)')

# Warmup
print(f'\n=== Warmup ===')
t = time.time()
warm = llm.warmup_all()
for h, info in warm.items():
    print(f'  {h}: ok={info["ok"]}, sec={info["sec"]}')

# Single full-prompt call latency
print(f'\n=== Single full-prompt call ===')
def single_call(i):
    t0 = time.time()
    r = llm.chat([{'role':'system','content':system},{'role':'user','content':user}],
                 temperature=0.95, max_tokens=150, response_format='json')
    return (i, time.time()-t0, len(r), r[:80])

t = time.time()
i, dt, n, snippet = single_call(0)
print(f'  call_0: {dt:.1f}s, {n} chars')
print(f'    response: {snippet}')

# Throughput: 12 calls / 2 parallel
print(f'\n=== Throughput test: 12 calls, 2 parallel ===')
t_start = time.time()
with cf.ThreadPoolExecutor(max_workers=2) as ex:
    results = list(ex.map(single_call, range(12)))
total = time.time() - t_start
avg = sum(t for _, t, _, _ in results) / len(results)
print(f'  total wall clock: {total:.1f}s')
print(f'  avg per-call:     {avg:.1f}s')
print(f'  effective tput:   {12/total:.2f} calls/sec')

# Project 7-day run time
# 25 active × 24 sim-h × 7 days = 4200 actions
# + 25 × 7 = 175 plans
# + 25 × 6 × 7 = 1050 reflects (actually staggered, so ~1000)
# + ~7 diaries + 7 digests-per-agent = 25×7 = 175 digests + retries
total_calls = 4200 + 175 + 1000 + 175 + 200  # +200 for retries
real_secs = total_calls / (12/total)
print(f'\n=== 7-day projection ===')
print(f'  estimated total calls: ~{total_calls}')
print(f'  estimated real time:   {real_secs/3600:.1f} hours ({real_secs/60:.0f} min)')
print(f'  per sim-day:           {real_secs/3600/7:.2f} hours')
