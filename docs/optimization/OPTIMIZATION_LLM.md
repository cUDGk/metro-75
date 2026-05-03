# LLM Client / Host Pool 最適化提案 (Metro-75)

**現状ベースライン**: ミニPC (Radeon 780M, UMA 48GB, qwen3:30b-a3b) のみ稼働、`OLLAMA_NUM_PARALLEL=2`、pool に URL 2回投入で 2 スロット、本番 ~14.7s/call。
**ターゲット**: 質を落とさず壁時計を 30〜55% 短縮。
**制約**: 主PC (RX 6600) には触れない。`sim/llm.py`/`sim/tick.py` は本提案では編集しない。

---

## 提案 1: Host Affinity (KV cache locality) — 期待 25〜40% 短縮

### 観察
- `_HostPool` は単一 `queue.Queue`。`tick_once` は agent A の plan/reflect/decide を毎日異なるホストへ流す可能性が高い。
- Agent A の system prompt (persona) は ~1.2KB 固定。Ollama は `num_parallel` slot ごとに直前リクエストの prefix KV を保持するが、別 host または同 host でも別 slot に当たるとフル prefill。
- agent.py:94-117 の system prompt + ACTION_LIST は完全固定。プロンプト全体の 60〜70% (~700-900 tokens) が cacheable 共通領域。

### 提案 (sim/llm.py:51 周辺の差分案)

```python
# 既存:
# pool = _HostPool(OLLAMA_HOSTS)

# 案: hash(agent_id) で sticky 割り当て、ただし全 host BUSY 時は generic queue へフォールバック
class _HostPool:
    def __init__(self, hosts):
        # 物理 host ごとに独立 BoundedSemaphore (capacity = slots/host)
        self._slots: dict[str, queue.Queue] = {h: queue.Queue() for h in set(hosts)}
        for h in hosts:
            self._slots[h].put(h)   # URL を slots回 enqueue (NUM_PARALLEL と同数)
        self._all = list(self._slots.keys())
    def acquire_for(self, key: str | None, timeout: float | None = None) -> str:
        if key:
            preferred = self._all[hash(key) % len(self._all)]
            try:
                return self._slots[preferred].get(timeout=0.05)  # 短いnon-block
            except queue.Empty:
                pass
        # フォールバック: 任意の空きスロット
        ...

def chat(messages, *, route_key: str | None = None, ...):
    host = pool.acquire_for(route_key)
```

呼び出し側 (sim/cognition.py:34, sim/agent.py:287, 307, 329) に `route_key=agent.id` を追加。

### 期待効果
- prefill が共通 prefix 分スキップされる。30B-A3B の prefill は ~3-5s/call の比重なので、cache hit で **2.0〜2.5s短縮 = 14.7s → 12〜13s (-15〜18%)**。
- さらに同 agent の plan→reflect→decide が連続して同 host に当たれば、persona prefix に加え memory_context の前半も部分一致 → **追加 5〜10%**。
- 追加コスト: ホスト数=1 (現状) では効果ゼロ、**主PC追加時に効く**。今すぐ単独で 14.7s を変えるわけではないので、優先度は中。

---

## 提案 2: Mini PC `OLLAMA_NUM_PARALLEL=3` 試行 — 期待 0〜30% スループット改善

### メモリ評価
- qwen3:30b-a3b (a3b = active 3B MoE): 重み ~18GB、active params 分の compute KV が parallel ごとに増える。
- num_ctx=4096、Q4_K_M モデルで KV cache は ~4096 * 2 (K+V) * head_dim * n_kv_heads * 2bytes ≈ **layer 数 64 想定で ~1.0-1.5 GB / slot**。
- UMA 48GB → OS/その他 8GB を引いて 40GB。18GB + 1.2GB×3 = ~21.6GB。**安全圏内**。

### コマンド (ミニPC 上で)

```bash
ssh user@192.168.1.7
sudo systemctl edit ollama   # or env file
# Environment="OLLAMA_NUM_PARALLEL=3"
# Environment="OLLAMA_KEEP_ALIVE=24h"
# Environment="OLLAMA_FLASH_ATTENTION=1"   # 780M Vulkan で動くか要検証
sudo systemctl restart ollama
```

ホスト側 (主PC):
```bash
# OLLAMA_HOSTS にミニPC URL を 3回入れる (現状2回 → 3回)
OLLAMA_HOSTS=http://192.168.1.7:11434,http://192.168.1.7:11434,http://192.168.1.7:11434 python run_28day.py
```

### 期待効果
- a3b は active param が 3B しかなく、780M でも compute ボトルネックは弱い。**メモリ帯域** (UMA は DDR5 共有 = ~80GB/s) がネック。
- num_parallel=2→3 で **per-slot レイテンシは 1.3〜1.5x 悪化、合計スループットは 1.3〜1.5x 改善**。tick_once は 4-9 並列 LLM 呼び出しなので、3 slot で待ち時間が減る分のほうが大きい。
- リスク: メモリ帯域飽和で per-call 時間が悪化、VRAM swap 発生。**まず smoke test (test_short.py を 3 slot で計測) してから本番投入**。

---

## 提案 3: Connection Pool / Keep-Alive — 期待 1〜3% (small but free)

### 現状の問題
- `urllib.request.urlopen` は毎呼び出し新規 TCP/HTTP 接続。LAN 経由 (192.168.1.7) で RTT ~1ms × handshake = ~3-5ms/call。本番で 24,000 calls/日 → 累計 1〜2 分。
- `Connection: close` がデフォルト。

### 提案 (sim/llm.py:58 差分案)

```python
import http.client
from urllib.parse import urlparse

# モジュールレベル: host -> HTTPConnection
_conn_cache: dict[str, http.client.HTTPConnection] = {}
_conn_lock = threading.Lock()

def _get_conn(host: str) -> http.client.HTTPConnection:
    with _conn_lock:
        c = _conn_cache.get(host)
        if c is None:
            u = urlparse(host)
            c = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=300)
            _conn_cache[host] = c
        return c

def _post_chat(host: str, body: dict, timeout: int = 300) -> str:
    conn = _get_conn(host)
    conn.request('POST', '/api/chat', json.dumps(body),
                 {'Content-Type': 'application/json', 'Connection': 'keep-alive'})
    resp = conn.getresponse()
    raw = resp.read()
    if resp.status >= 400:
        # 接続を閉じて作り直す (HTTP error 後の再利用は危険)
        conn.close(); _conn_cache.pop(host, None)
        raise urllib.error.HTTPError(host, resp.status, raw.decode(errors='replace'), {}, None)
    return json.loads(raw.decode('utf-8'))['message']['content']
```

注意: `HTTPConnection` はスレッドセーフでない。**ホスト=スロット 1:1 (capacity=1) なら問題ない** が、num_parallel=N にする場合は per-slot connection が必要 (host pool が URL に slot index を埋め込む形にする)。

### 期待効果
- 14.7s/call の中で誤差レベル。が、`OLLAMA_KEEP_ALIVE=24h` と組み合わせると **モデル再ロードの偶発を排除** できるので、安定化メリットが大きい。

---

## 提案 4: Speculative Decoding (主PC を draft 担当) — 期待 2〜4x、ただし主PC解禁前提

ユーザの llm-exp-chatcache 結果 (4.38x@Qwen2.5/3) を踏まえると最大級のリターン。**ただし**:
- Ollama は speculative decoding 未対応 (2026-04 時点で実験的、`OLLAMA_USE_SPECULATIVE` 等の正式 flag なし)。
- 移行先は `llama-server` 直叩き。`/v1/chat/completions` (OpenAI 互換) を使えば `_post_chat` の URL とペイロード形を差し替えるだけで済む (4-6 行)。
- 主PC で `llama-server -m qwen2.5-0.5b-instruct-q4.gguf --port 8081` を draft model として走らせ、ミニPC 側で `--model qwen3-30b-a3b -md http://主PC:8081`。
- **ただしこれは主PC稼働を前提にする提案**。今回は触らない方針なので **保留メモ** として記載のみ。

### 移行コスト見積もり
- `sim/llm.py` 変更 ~30 行 (URL/payload/レスポンスパース)。
- スクリプト (run_28day.py) の env 更新。
- llama-server CLI 起動スクリプト (両 PC)。
- **smoke test 比較: Ollama 14.7s → llama-server単体 ~13s (cache_prompt + KV reuse) → +draft 4-6s**。

主PC解禁後の優先度は最高。

---

## 提案 5: Batch API — 不採用

Ollama に bona fide batch エンドポイント無し (2026-04)。`/api/chat` の `stream=false` を複数スレッドから同時に叩くのが現状の最適。複数 agent を 1 リクエストにまとめると system prompt が干渉して質劣化リスク。**KISS: 採用しない**。

---

## 提案 6: Timeout 短縮 — 期待 0% (耐障害性 trade-off)

現 300s。本番 14.7s/call で 95p ≈ 30s 想定。**timeout=60s に短縮** すると hang したホストを早く failover できる。ただし 30B モデルのコールドロード時は 90-120s かかる場合あり、`warmup_all()` 後なら 60s でも安全。

```python
# sim/llm.py:76 デフォルトを変更
def chat(..., timeout: int = 90) -> str:
```

---

## 推奨優先順位 (主PC触らない前提)

1. **提案 2 (NUM_PARALLEL=3)**: 実装ゼロ、ssh + restart のみ。smoke test → 良ければ即本番。**最大のリターン**。
2. **提案 3 (keep-alive + KEEP_ALIVE=24h)**: 安定化メリット大、コード ~20 行。
3. **提案 1 (host affinity)**: 主PC追加時に最大化、現状の単一ホストでは効果ゼロなので保留可。
4. **提案 6 (timeout 短縮)**: 1行修正。

主PC解禁時に **提案 4 (speculative)** を最優先で実装。

---

## 検証コマンド

```bash
# smoke before/after
cd C:/Users/user/Desktop/metro-75
OLLAMA_HOSTS=http://192.168.1.7:11434,http://192.168.1.7:11434,http://192.168.1.7:11434 \
  python test_short.py 2>&1 | tee logs/smoke_3par.log

# llm.calls / 秒 を測る (tick_stats を grep)
python -c "from sim import llm; import time
t=time.time(); [llm.simple_prompt('hi','ping',max_tokens=8) for _ in range(20)]
print(f'{20/(time.time()-t):.2f} req/s')"
```

質劣化チェックは logs/dialogue.log を 50 行 diff (parallel=2 vs 3) で目視。
