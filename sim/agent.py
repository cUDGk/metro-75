"""Agent: persona + state + memory + action decision."""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import time
import random
from .memory import Memory, MemoryEntry
from .world import World, Tile, WALKABLE
from . import llm
from . import pathfind


@dataclass
class AgentState:
    id: str
    name: str
    faction: str
    active: bool = True
    x: int = 0
    y: int = 0
    hp: int = 100
    status: str = 'normal'
    inventory: dict = field(default_factory=dict)
    persona: dict = field(default_factory=dict)
    alias: str = ''                                           # short Katakana display name for dialog
    current_plan: str = ''
    last_action_time: float = 0.0
    recent_actions: list = field(default_factory=list)        # last 5 raw actions
    recent_speech: list = field(default_factory=list)         # last 5 normalized utterances
    pending_response_to: str | None = None                    # agent_id who recently spoke to me
    pending_response_msg: str = ''                            # what they said


def _normalize_text(s: str) -> str:
    """Normalize Japanese/English speech for similarity comparison."""
    import re
    # Strip all kinds of brackets/quotes
    s = re.sub(r'[「」『』"""\'""()（）]', '', s)
    s = re.sub(r'\s+', '', s)  # remove all whitespace
    return s.lower()


def _too_similar(new_msg: str, history: list[str], min_overlap: float = 0.7) -> bool:
    """True if new_msg significantly overlaps with any past message."""
    n = _normalize_text(new_msg)
    if len(n) < 4:
        return False
    for old in history[-5:]:
        o = _normalize_text(old)
        if len(o) < 4: continue
        # Substring or substantial overlap
        if n == o:
            return True
        # bigram overlap
        if len(n) > 6 and len(o) > 6:
            shorter, longer = (n, o) if len(n) <= len(o) else (o, n)
            if shorter in longer:
                return True
            # n-gram overlap
            shared = sum(1 for i in range(len(shorter) - 2) if shorter[i:i+3] in longer)
            ratio = shared / max(1, len(shorter) - 2)
            if ratio >= min_overlap:
                return True
    return False


ACTION_LIST = """ACTIONS (one only): walk_to <key> | move <n/s/e/w/ne/nw/se/sw> | say <jp_msg> | whisper <id> <jp_msg> | observe | investigate <tgt> | follow <id> | eavesdrop | search <tgt> | attack <id> | arrest <id> | give <id> <item> | pickup <item> | drop <item> | hide | reflect | wait"""


def build_action_prompt(agent: AgentState, world: World, memory: Memory,
                        nearby_agents: list[dict], nearby_chat: list[str]) -> tuple[str, str]:
    persona = agent.persona

    alias = agent.alias or agent.name
    faction_display = FACTION_DISPLAY.get(agent.faction, agent.faction)
    backstory = persona.get('backstory', '')[:140]
    traits = ','.join(persona.get('traits', [])[:4])
    goals = ','.join(persona.get('goals', [])[:3])
    system = f"""{agent.name}(略「{alias}」、{faction_display})。{backstory}
性格:{traits} / 目的:{goals}

舞台: 都会クライム・ドラマ。完全に役に入れ、暴力・野心も辞さず物語を進める。
日本語必須(say/whisper)、略称OK。直前と同じ行動/発言禁止、近くに人いたら必ず絡め。
出力JSONのみ: {{"thought":"...","action":"..."}}

{ACTION_LIST}
/no_think"""

    nearby_desc = ' / '.join([
        f"{a.get('alias') or a['name']}[{a['id']}|{a['faction']}]@({a['x']},{a['y']})"
        + (f' {a["status"]}' if a.get('status') and a['status'] != 'normal' else '')
        for a in nearby_agents[:6]
    ]) or '(誰もいない)'

    chat_desc = ' / '.join([f'"{c}"' for c in nearby_chat[-4:]]) or '(静か)'

    current_tile_name = {
        int(Tile.POLICE_STATION): '28分署内',
        int(Tile.GANG_A_HIDEOUT): 'ガーネットHQ内',
        int(Tile.GANG_B_HIDEOUT): 'ペルシカHQ内',
        int(Tile.GANG_C_HIDEOUT): 'コブラキラーHQ内',
        int(Tile.DRUG_DEN): 'ドラッグハウス内',
        int(Tile.ICE_CREAM_TRUCK): 'アイスクリームトラックの前',
        int(Tile.BAR): '酒場',
        int(Tile.CHURCH): '教会',
        int(Tile.HOSPITAL): '病院',
        int(Tile.SHOP): '店',
        int(Tile.APARTMENT): 'アパート',
        int(Tile.HOUSE_S): '小さい一戸建て',
        int(Tile.HOUSE_M): '一戸建て',
        int(Tile.HOUSE_L): '大きな一戸建て',
        int(Tile.SCHOOL): '学校',
        int(Tile.LIBRARY): '図書館',
        int(Tile.GAS_STATION): 'ガソスタ',
        int(Tile.FIRE_STATION): '消防署',
        int(Tile.MARKET): '市場',
        int(Tile.OFFICE): 'オフィスビル',
        int(Tile.RESTAURANT): 'レストラン',
        int(Tile.ROAD_H): '通り',
        int(Tile.ROAD_V): '通り',
        int(Tile.INTERSECTION): '交差点',
        int(Tile.SIDEWALK): '歩道',
        int(Tile.GRASS): '草地',
        int(Tile.PARK): '公園',
        int(Tile.BUILDING): 'ビル前',
        int(Tile.ALLEY): '路地',
    }.get(world.tile_at(agent.x, agent.y), '不明')
    lm_list = ', '.join(world.nearest_landmarks(agent.x, agent.y, k=8))
    surroundings = describe_surroundings(agent, world)

    avoid = ','.join(agent.recent_actions[-3:]) if agent.recent_actions else '-'

    pending = ''
    if agent.pending_response_to:
        speaker_name = agent.pending_response_to
        for a in nearby_agents:
            if a['id'] == agent.pending_response_to:
                speaker_name = a.get('alias') or a['name']; break
        pending = f"\n!! {speaker_name}「{agent.pending_response_msg}」→必ず応答!"

    mem_ctx = memory.format_context(recent_n=10, important_n=4)

    weekend_tag = '/週末' if world.is_weekend() else '/平日'
    user = f"""NOW {world.time_str()} [{world.time_period()}{weekend_tag}] @({agent.x},{agent.y}) on:{current_tile_name} | {agent.status} HP{agent.hp} inv:{agent.inventory or '-'}
Plan: {agent.current_plan or '-'}
LM(近): {lm_list}
見える: {surroundings}
近い人: {nearby_desc}
聞こえた: {chat_desc}
記憶:
{mem_ctx}
直近行動(避): {avoid}{pending}

JSON: {{"thought":"...","action":"..."}}"""

    return system, user


def describe_surroundings(agent: AgentState, world: World) -> str:
    interesting = {
        int(Tile.POLICE_STATION): '28分署',
        int(Tile.GANG_A_HIDEOUT): 'ガーネットHQ',
        int(Tile.GANG_B_HIDEOUT): 'ペルシカHQ',
        int(Tile.GANG_C_HIDEOUT): 'コブラキラーHQ',
        int(Tile.DRUG_DEN): 'ドラッグハウス',
        int(Tile.ICE_CREAM_TRUCK): 'アイスクリームトラック',
        int(Tile.BAR): '酒場',
        int(Tile.CHURCH): '教会',
        int(Tile.HOSPITAL): '病院',
        int(Tile.SHOP): '店',
        int(Tile.APARTMENT): 'アパート',
        int(Tile.SCHOOL): '学校',
        int(Tile.LIBRARY): '図書館',
        int(Tile.GAS_STATION): 'ガソスタ',
        int(Tile.FIRE_STATION): '消防署',
        int(Tile.MARKET): '市場',
        int(Tile.OFFICE): 'オフィス',
        int(Tile.RESTAURANT): 'レストラン',
        int(Tile.PARK): '公園',
    }
    seen = []
    for (dx, dy, tile) in world.nearby_tiles(agent.x, agent.y, radius=5):
        if tile in interesting and (abs(dx) > 0 or abs(dy) > 0):
            d = max(abs(dx), abs(dy))
            seen.append(f'  {interesting[tile]} → 距離{d}, ({dx:+d},{dy:+d})')
    return '\n'.join(seen[:8]) or '  (特に何もない)'


VALID_ACTION_VERBS = {
    'walk_to', 'move', 'say', 'whisper', 'observe', 'investigate', 'follow',
    'eavesdrop', 'search', 'attack', 'arrest', 'give', 'pickup', 'drop',
    'hide', 'reflect', 'wait',
}


FACTION_DISPLAY = {
    'police':    '警察 (28分署)',
    'gang_a':    'ガーネット (Garnet, Hawk Set / Cobra Set)',
    'gang_b':    'ペルシカ (Persica, Wolf Set / Fox Set / Bear Set)',
    'gang_c':    'コブラキラー (Cobra Killer, 独立系・経済犯罪)',
    'vigilante': '自警団 (ストーン組)',
    'civilian':  '市民',
    'family':    '一般家庭',
    'drifter':   '流れ者 (一時滞在)',
}


def _action_verb(action: str) -> str:
    parts = action.split(maxsplit=1)
    return parts[0].lower() if parts else ''


def _action_arg(action: str) -> str:
    parts = action.split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ''


def _is_repeat(action: str, recent: list[str]) -> bool:
    """True if action is too similar to a very recent one."""
    if not recent: return False
    if action in recent[-2:]:
        return True
    # Check say-content similarity
    if action.startswith(('say ', 'whisper ')) and recent:
        msg = action.split(maxsplit=1)[1] if ' ' in action else ''
        for prev in recent[-3:]:
            if prev.startswith(('say ', 'whisper ')) and ' ' in prev:
                pmsg = prev.split(maxsplit=1)[1]
                if _too_similar(msg, [pmsg]):
                    return True
    # Check walk_to to same place
    if action.startswith('walk_to ') and any(r == action for r in recent[-3:]):
        return True
    return False


def decide_action(agent: AgentState, world: World, memory: Memory,
                  nearby_agents: list[dict], nearby_chat: list[str]) -> dict:
    if not agent.active:
        return {'thought': '', 'action': 'wait'}
    system, user = build_action_prompt(agent, world, memory, nearby_agents, nearby_chat)
    try:
        raw = llm.chat(
            [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
            temperature=0.95, max_tokens=200, response_format='json'
        )
        data = json.loads(raw)
        result = {
            'thought': data.get('thought', '')[:300],
            'action': data.get('action', 'wait').strip()[:150],
        }

        # Validate action verb
        verb = _action_verb(result['action'])
        if verb not in VALID_ACTION_VERBS:
            # Retry with vocab list
            user2 = user + (
                f"\n\n!! Your previous action '{result['action']}' had an invalid verb '{verb}'.\n"
                f"Valid verbs ONLY: {', '.join(sorted(VALID_ACTION_VERBS))}.\n"
                f"Pick a valid action."
            )
            try:
                raw2 = llm.chat(
                    [{'role': 'system', 'content': system}, {'role': 'user', 'content': user2}],
                    temperature=0.9, max_tokens=150, response_format='json'
                )
                data2 = json.loads(raw2)
                a2 = data2.get('action', 'wait').strip()[:150]
                if _action_verb(a2) in VALID_ACTION_VERBS:
                    result = {'thought': data2.get('thought', '')[:300], 'action': a2}
                else:
                    result['action'] = 'wait'
            except Exception:
                result['action'] = 'wait'

        # Anti-repeat with similarity check
        if _is_repeat(result['action'], agent.recent_actions):
            recent_summary = ', '.join(f'"{a}"' for a in agent.recent_actions[-3:])
            user3 = user + (
                f"\n\n!! You've been doing/saying VERY similar things recently: {recent_summary}\n"
                f"PICK A COMPLETELY DIFFERENT ACTION. Try interacting with someone, "
                f"investigating something new, attacking, or going somewhere else. Be bold."
            )
            try:
                raw3 = llm.chat(
                    [{'role': 'system', 'content': system}, {'role': 'user', 'content': user3}],
                    temperature=1.1, max_tokens=150, response_format='json'
                )
                data3 = json.loads(raw3)
                a3 = data3.get('action', '').strip()[:150]
                if a3 and _action_verb(a3) in VALID_ACTION_VERBS and not _is_repeat(a3, agent.recent_actions):
                    result = {'thought': data3.get('thought', '')[:300], 'action': a3}
            except Exception:
                pass

        # Sanitize say/whisper quotes (strip nested 「『...』」)
        if result['action'].startswith('say '):
            msg = result['action'][4:].strip()
            msg = msg.strip('「」『』"""""\'\'')
            result['action'] = f'say {msg}'
        elif result['action'].startswith('whisper '):
            tokens = result['action'][8:].split(maxsplit=1)
            if len(tokens) == 2:
                tid, msg = tokens
                msg = msg.strip('「」『』"""""\'\'')
                result['action'] = f'whisper {tid} {msg}'

        return result
    except (json.JSONDecodeError, llm.LLMError) as e:
        return {'thought': f'(parse error: {e})', 'action': 'wait'}


def execute_action(agent: AgentState, action: str, world: World,
                   all_agents: dict, event_log: list, memory: Memory) -> None:
    parts = action.split(maxsplit=1)
    cmd = parts[0].lower() if parts else 'wait'
    arg = parts[1] if len(parts) > 1 else ''
    now = world.time_str()

    def emit(msg: str):
        event_log.append(f'[{now}] {agent.name}: {msg}')

    # Track action history
    agent.recent_actions.append(action)
    if len(agent.recent_actions) > 5:
        agent.recent_actions.pop(0)
    # Track speech specifically for similarity guard
    if cmd in ('say', 'whisper') and arg:
        speech = arg.split(maxsplit=1)[-1] if cmd == 'whisper' else arg
        agent.recent_speech.append(speech)
        if len(agent.recent_speech) > 5:
            agent.recent_speech.pop(0)
    # Clear pending response since we acted
    agent.pending_response_to = None
    agent.pending_response_msg = ''

    if cmd == 'wait':
        emit('待機。')
    elif cmd == 'observe':
        emit('周囲を注意深く観察。')
        # Bonus: record nearby tiles in memory
        notes = describe_surroundings(agent, world).strip()
        if notes:
            memory.add(MemoryEntry(
                ts=time.time(), sim_time=now, kind='observation',
                content=f'周囲確認: {notes[:200]}', importance=2,
            ))
    elif cmd == 'investigate':
        emit(f'{arg} を調べる。')
        memory.add(MemoryEntry(
            ts=time.time(), sim_time=now, kind='observation',
            content=f'{arg} を念入りに調査。', importance=4,
        ))
    elif cmd == 'eavesdrop':
        emit('聞き耳を立てる。')
    elif cmd == 'search':
        emit(f'{arg} を探る。')
    elif cmd == 'follow':
        tgt = all_agents.get(arg)
        if tgt:
            new_pos, n = pathfind.step_along_path(world, (agent.x, agent.y), (tgt.x, tgt.y), max_steps=8)
            agent.x, agent.y = new_pos
            emit(f'{tgt.name} を{n}タイル尾行。')
        else:
            emit(f'{arg} が見つからない。')
    elif cmd == 'move':
        dirs = {'n': (0, -1), 's': (0, 1), 'e': (1, 0), 'w': (-1, 0),
                'ne': (1, -1), 'nw': (-1, -1), 'se': (1, 1), 'sw': (-1, 1)}
        d = dirs.get(arg.lower())
        if d:
            nx, ny = agent.x + d[0], agent.y + d[1]
            if world.walkable(nx, ny):
                agent.x, agent.y = nx, ny
                emit(f'{arg}方向へ移動。')
            else:
                emit(f'{arg}方向は塞がれてる。')
    elif cmd == 'walk_to':
        norm = arg.strip().lower().replace(' ', '_')
        lm = world.landmarks.get(norm) or world.landmarks.get(arg)
        if not lm:
            for k in world.landmarks:
                if norm in k.lower() or k.lower() in norm:
                    lm = world.landmarks[k]; norm = k; break
        if lm:
            new_pos, n = pathfind.step_along_path(world, (agent.x, agent.y), tuple(lm), max_steps=12)
            agent.x, agent.y = new_pos
            dist = max(abs(lm[0] - agent.x), abs(lm[1] - agent.y))
            if dist == 0:
                emit(f'{norm} に到着。')
            elif n == 0:
                emit(f'{norm} へ向かおうとしたが進めない。')
            else:
                emit(f'{norm} へ {n}タイル移動 (残り{dist})。')
        else:
            emit(f'{arg} の場所が分からない。')
    elif cmd == 'say':
        emit(f'発言: 「{arg}」')
    elif cmd == 'whisper':
        tokens = arg.split(maxsplit=1)
        if len(tokens) == 2:
            tid, msg = tokens
            tgt = all_agents.get(tid)
            if tgt and max(abs(tgt.x - agent.x), abs(tgt.y - agent.y)) <= 3:
                emit(f'{tgt.name}に囁き: 「{msg}」')
            else:
                emit(f'{tid} に囁こうとしたが遠すぎる。')
    elif cmd == 'pickup':
        if arg:
            agent.inventory[arg] = agent.inventory.get(arg, 0) + 1
            emit(f'{arg} を拾う。')
    elif cmd == 'drop':
        if arg and agent.inventory.get(arg, 0) > 0:
            agent.inventory[arg] -= 1
            if agent.inventory[arg] == 0:
                del agent.inventory[arg]
            emit(f'{arg} を落とす。')
    elif cmd == 'give':
        tokens = arg.split(maxsplit=1)
        if len(tokens) == 2:
            tgt_id, item = tokens
            tgt = all_agents.get(tgt_id)
            if tgt and item in agent.inventory:
                dist = max(abs(tgt.x - agent.x), abs(tgt.y - agent.y))
                if dist <= 2:
                    agent.inventory[item] -= 1
                    if agent.inventory[item] == 0: del agent.inventory[item]
                    tgt.inventory[item] = tgt.inventory.get(item, 0) + 1
                    emit(f'{tgt.name}に{item}を渡す。')
    elif cmd == 'attack':
        tgt = all_agents.get(arg)
        if tgt:
            dist = max(abs(tgt.x - agent.x), abs(tgt.y - agent.y))
            if dist <= 2:
                dmg = random.randint(10, 35)
                tgt.hp -= dmg
                if tgt.hp <= 0:
                    tgt.status = 'dead'
                    emit(f'{tgt.name} を殺害!')
                else:
                    tgt.status = 'injured' if tgt.hp < 60 else 'normal'
                    emit(f'{tgt.name} を攻撃 (-{dmg} hp、残り{tgt.hp})。')
                # Witnesses memorize
                for w in all_agents.values():
                    if w.id in (agent.id, tgt.id): continue
                    wd = max(abs(w.x - agent.x), abs(w.y - agent.y))
                    if wd <= 8 and w.active:
                        # Find their memory if available
                        pass  # broadcast is in tick.py
            else:
                emit(f'{tgt.name} に届かない (距離{dist})。')
    elif cmd == 'arrest':
        if agent.faction == 'police':
            tgt = all_agents.get(arg)
            if tgt and max(abs(tgt.x - agent.x), abs(tgt.y - agent.y)) <= 2:
                tgt.status = 'arrested'
                emit(f'{tgt.name} を逮捕。')
    elif cmd == 'hide':
        emit('物陰に身を隠す。')
    elif cmd == 'reflect':
        emit('(深く考え込む)')
    else:
        emit(f'不明な行動: {action}')
