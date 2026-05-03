"""Higher-level cognition: daily plan + reflection."""
from __future__ import annotations
import json
import time
from .agent import AgentState
from .world import World
from .memory import Memory, MemoryEntry
from . import llm


def generate_daily_plan(agent: AgentState, world: World, memory: Memory) -> str:
    """Run at start of each sim-day. Sets agent.current_plan based on persona + recent memory."""
    persona = agent.persona
    mem_ctx = memory.format_context(recent_n=12, important_n=6)
    backstory = persona.get('backstory', '')[:100]
    goals = ','.join(persona.get('goals', [])[:3])
    system = (f"{agent.name}({agent.faction})。{backstory} 目的:{goals}\n"
              "今日の計画を2-4個の具体目標で。場所/人物/行動を名指し、日本語のみ。\n"
              'JSON: {"plan":["...","..."]}\n/no_think')
    user = f"NOW {world.time_str()} @({agent.x},{agent.y})\n昨日までの重要記憶:\n{mem_ctx}\n計画 JSON のみ:"
    for attempt in range(2):
        try:
            raw = llm.simple_prompt(system, user, max_tokens=300, response_format='json',
                                    temperature=0.85 if attempt == 0 else 0.5)
            d = json.loads(raw)
            bullets = d.get('plan', [])
            if isinstance(bullets, list) and bullets:
                return ' / '.join(str(b)[:80] for b in bullets[:4])
            if not isinstance(bullets, list):
                return str(bullets)[:200]
        except json.JSONDecodeError:
            continue  # retry once with lower temp
        except Exception:
            return ''
    return ''


def reflect(agent: AgentState, world: World, memory: Memory) -> str:
    """Run periodically. Generates a high-importance synthesis stored in memory."""
    mem_ctx = memory.format_context(recent_n=12, important_n=6)
    backstory = agent.persona.get('backstory', '')[:100]
    goals = ','.join(agent.persona.get('goals', [])[:3])
    system = (f"{agent.name}({agent.faction})。{backstory} 目的:{goals}\n"
              "最近の出来事から1-2の鋭い洞察を抽出。誰を信頼?何が変わった?直感は?\n"
              "**日本語のみ** (英語/ロシア語禁止)、カタカナ可。\n"
              'JSON: {"insight":"1文・80字・日本語","trust_changes":"誰を信頼/不信・日本語"}\n/no_think')
    user = f"NOW {world.time_str()} 今日の計画: {agent.current_plan or '-'}\n最近:\n{mem_ctx}\n短く反省。JSON のみ:"
    for attempt in range(2):
        try:
            raw = llm.simple_prompt(system, user, max_tokens=180, response_format='json',
                                    temperature=0.8 if attempt == 0 else 0.5)
            d = json.loads(raw)
            insight = d.get('insight', '')
            trust = d.get('trust_changes', '')
            if insight:
                memory.add(MemoryEntry(
                    ts=time.time(), sim_time=world.time_str(),
                    kind='reflection', content=f'{insight} | trust: {trust}',
                    importance=8,
                ))
            return insight
        except json.JSONDecodeError:
            continue
        except Exception:
            return ''
    return ''
