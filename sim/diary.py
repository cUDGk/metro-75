"""End-of-day narrative diary + Discord webhook posting."""
from __future__ import annotations
import json
import os
import urllib.request
from . import llm


DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK', '')


_UA = 'Mozilla/5.0 metro-75-bot/1.0'


def _post_discord(message: str, file_path: str | None = None) -> bool:
    """Post to Discord. Optionally attach a file. Returns True on success."""
    try:
        if file_path and os.path.exists(file_path):
            boundary = '----MetroDiaryBoundary'
            body = b''
            body += f'--{boundary}\r\n'.encode()
            body += b'Content-Disposition: form-data; name="payload_json"\r\n'
            body += b'Content-Type: application/json\r\n\r\n'
            body += json.dumps({'content': message[:1990]}).encode('utf-8')
            body += b'\r\n'
            body += f'--{boundary}\r\n'.encode()
            body += f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(file_path)}"\r\n'.encode()
            body += b'Content-Type: image/png\r\n\r\n'
            with open(file_path, 'rb') as f:
                body += f.read()
            body += f'\r\n--{boundary}--\r\n'.encode()
            req = urllib.request.Request(
                DISCORD_WEBHOOK, data=body,
                headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': _UA},
            )
        else:
            data = json.dumps({'content': message[:1990]}).encode('utf-8')
            req = urllib.request.Request(
                DISCORD_WEBHOOK, data=data,
                headers={'Content-Type': 'application/json', 'User-Agent': _UA},
            )
        with urllib.request.urlopen(req, timeout=30) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f'Discord post failed: {e}')
        return False


def _filter_today(log_path: str, day: int) -> list[str]:
    """Read log file, return only lines for given sim-day."""
    if not os.path.exists(log_path): return []
    out = []
    # Lines look like '[Day 5(土) 12:34] ...' — match the day prefix incl. opening paren
    needle = f'[Day {day}('
    with open(log_path, encoding='utf-8') as f:
        for line in f:
            if needle in line:
                out.append(line.strip())
    return out


def _faction_summary(agents: dict) -> str:
    fac_names = {
        'police': '警察', 'gang_a': 'ガーネット', 'gang_b': 'ペルシカ',
        'gang_c': 'コブラキラー', 'vigilante': '自警団',
    }
    parts = []
    for fac, label in fac_names.items():
        ags = [a for a in agents.values() if a.faction == fac and a.active]
        n = len(ags)
        alive = sum(1 for a in ags if a.status not in ('dead', 'arrested'))
        dead = sum(1 for a in ags if a.status == 'dead')
        arr = sum(1 for a in ags if a.status == 'arrested')
        if n > 0:
            parts.append(f'{label}{alive}/{n}' + (f'(死{dead})' if dead else '') + (f'(逮{arr})' if arr else ''))
    return ' '.join(parts)


def generate_diary(sim, day: int, log_dir: str, snap_path: str | None = None) -> dict:
    """Generate the day's diary via LLM and post to Discord. Returns dict with content."""
    events = _filter_today(os.path.join(log_dir, 'events.log'), day)
    dialogue = _filter_today(os.path.join(log_dir, 'dialogue.log'), day)

    sample_events = events[-40:] if events else []
    sample_dialogue = dialogue[-20:] if dialogue else []

    n_dead = sum(1 for a in sim.agents.values() if a.status == 'dead')
    n_arrested = sum(1 for a in sim.agents.values() if a.status == 'arrested')

    system = ('あなたは「メトロ・トリビューン」紙のベテラン社会面記者。'
              '**日本語のみ**で書く。英語・ロシア語・中国語などは絶対に混ぜない。'
              '都市の暗部を冷徹かつ詩的に描く。日記体。短く鋭く。')
    user = f"""## Day {day} のシミュレーション・ログから「街の記者の日記」を書け

絶対ルール:
- **日本語のみ** (英単語/ロシア語/その他言語禁止)。固有名詞のカタカナ表記は OK
- 400字以内、新聞コラム風
- 具体的な人名・場所・出来事を引用、ダーク・トーン
- 派閥間の緊張、登場人物の心の動き、街の空気を読み取れ
- 「私は」一人称で、観察者の視点

### 今日の出来事 (events.log抜粋):
{chr(10).join(sample_events[-30:])}

### 今日の会話 (dialogue.log抜粋):
{chr(10).join(sample_dialogue[-15:])}

### 派閥状況: {_faction_summary(sim.agents)}

400字以内で**日本語の**記者日記を書け。"""

    try:
        narrative = llm.simple_prompt(system, user, max_tokens=600, temperature=0.85)
    except Exception as e:
        narrative = f'(diary LLM error: {e})\n\n生イベント: {len(events)}, 会話: {len(dialogue)}'

    msg = (
        f'# 📔 Metro-75 — Day {day} の記者日記\n\n'
        f'{narrative}\n\n'
        f'---\n'
        f'📊 events: **{len(events)}** / dialogue: **{len(dialogue)}** / '
        f'dead: **{n_dead}** / arrested: **{n_arrested}**\n'
        f'{_faction_summary(sim.agents)}'
    )

    ok = _post_discord(msg, snap_path)
    return {
        'day': day,
        'narrative': narrative,
        'events_count': len(events),
        'dialogue_count': len(dialogue),
        'posted': ok,
    }
