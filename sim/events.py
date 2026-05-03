# -*- coding: utf-8 -*-
"""Scripted inciting events. Injected into target agents' memories at sim time.

SCENARIO: アイスクリームトラックは 28分署の内偵車 (3日前から駐車中)。
パク刑事中心にガーネット/ペルシカの動きを監視。ギャング側は違和感を持ち始めてる。
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from .memory import MemoryEntry


@dataclass
class ScriptedEvent:
    sim_minute: int
    targets: list[str]
    importance: int
    description: str


# Day 0 events — ice-cream-truck-as-undercover framing
EVENTS_DAY0 = [
    ScriptedEvent(
        sim_minute=8 * 60,
        targets=['pm_cobra_devon'],
        importance=8,
        description='アイスクリームトラックの様子はやっぱりおかしい。3日連続駐車、客ゼロ、運転手は無線らしき仕草を時々する。誰がやってるか知らんが、絶対にアイス売ってない。',
    ),
    ScriptedEvent(
        sim_minute=10 * 60,
        targets=['police_rivera'],
        importance=7,
        description='アイスクリームトラックの2ブロック東に黒のセダン。エンジン切らずに2人乗り、こっちを観察してる。署のじゃない、ギャング系か?何かを監視してるのは確か。',
    ),
    ScriptedEvent(
        sim_minute=11 * 60,
        targets=['police_diaz'],
        importance=8,
        description='FBIから連絡: 内偵オペの継続承認、明朝6時に支援要請面会。トラック内のパクからは「ガーネットとペルシカ双方が動き始めた、もう数日もたない」との報告。',
    ),
    ScriptedEvent(
        sim_minute=13 * 60,
        targets=['vig_stone'],
        importance=8,
        description="オライリーズ酒場の片隅でチンピラ2人が囁いてた: 「ホークがガキ売ってやがる」。真偽は不明だが、自警団として動かないわけにいかない。",
    ),
    ScriptedEvent(
        sim_minute=14 * 60,
        targets=['ph_wolf_malik', 'ph_fox_keisha'],
        importance=7,
        description='コブラ・デヴォン (ガーネット Cobra Set) がアイスクリームトラックの周りを嗅ぎ回ってた。彼らもあのトラックの正体を疑ってる。何か起きそう。',
    ),
    ScriptedEvent(
        sim_minute=16 * 60,
        targets=['pm_hawk_marcus'],
        importance=9,
        description='匿名電話: 「ガーネットの中にポリと通じてる奴がいる。誰か特定はまだ。心当たりは?」 弟分の誰かか、コブラの誰か。アイスクリームトラックの件も気になる。',
    ),
    ScriptedEvent(
        sim_minute=18 * 60,
        targets=['police_park'],
        importance=8,
        description='トラック内の長距離レンズで撮影成功: アントワーヌ・バンクス (ペルシカ Wolf Set) が拳銃を別の男に手渡す現場をクリアに記録。これだけで起訴可能、だがオペ全体を成立させるにはまだ早い。',
    ),
    ScriptedEvent(
        sim_minute=20 * 60,
        targets=['pm_cobra_devon'],
        importance=9,
        description='ストリートの情報源から: 弟マーカスを殺ったのはアントワーヌ・バンクス (ペルシカ Wolf) で確定。ようやく名前が分かった。明日にでも仕留めたい。',
    ),
    ScriptedEvent(
        sim_minute=22 * 60,
        targets=['vig_stone', 'vig_rachel'],
        importance=10,
        description='2年前にストーンの娘リリーを撃ったのもアントワーヌ・バンクス (ペルシカ Wolf) の可能性が極めて高い。情報源は信用できる元軍の友人。法で裁けないなら自分でケリをつけるしかない。',
    ),
]


class EventScheduler:
    def __init__(self, events: list[ScriptedEvent], agents: dict, memories: dict):
        self.events = sorted(events, key=lambda e: e.sim_minute)
        self.agents = agents
        self.memories = memories
        self.fired: set[int] = set()

    def tick(self, world):
        cur = world.day * 1440 + world.hour * 60 + world.minute
        for i, ev in enumerate(self.events):
            if i in self.fired: continue
            if cur < ev.sim_minute: continue
            targets = self.agents.keys() if ev.targets == ['ALL'] else ev.targets
            for tid in targets:
                mem = self.memories.get(tid)
                if mem:
                    mem.add(MemoryEntry(
                        ts=time.time(), sim_time=world.time_str(),
                        kind='event', content=ev.description,
                        importance=ev.importance,
                    ))
            self.fired.add(i)
            print(f'[EVENT @ {world.time_str()}] {ev.description[:80]}... → {targets}')
