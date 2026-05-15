<div align="center">

# metro-75

### 60人のAIエージェントが7日間自律行動する都市犯罪ドラマ・シミュレーター

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](sim/)
[![llama.cpp](https://img.shields.io/badge/llama.cpp-Vulkan-000000?style=flat)](https://github.com/ggerganov/llama.cpp)
[![Qwen](https://img.shields.io/badge/Qwen3--30B--A3B-MoE-615CED?style=flat)](https://huggingface.co/Qwen)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

**ローカルLLMで動く250×250タイルの架空都市、25人のアクティブエージェントが派閥ドラマを自律的に紡ぐ。**

---

</div>

## 概要

米国都市部を模した250×250タイルのグリッド上で、警察・3つのギャング・自警団・市民・流れ者あわせて60人のキャラクターが7日間自律行動するシミュレーター。各エージェントは固有のペルソナ・記憶・1日の計画・4時間ごとのリフレクションを持ち、すべてローカルのQwen3-30B-A3B (MoE) で駆動される。

中央に駐車したアイスクリームトラック (実は警察の内偵車) を起点に、ガーネット内部の内通者問題、コブラキラーとの古傷、ストーン自警団による私刑、3勢力からのアントワーヌ追跡 — 4本のドラマ軸を仕掛けイベントで点火し、あとは LLM の判断に委ねる。

## 特徴

| 項目 | 内容 |
|---|---|
| 規模 | 250×250タイル / 60エージェント (アクティブ25 + NPC35) / 41ランドマーク |
| LLM | Qwen3-30B-A3B-Instruct (Q4_K_M GGUF) on llama-server, Vulkan iGPU |
| 認知層 | 行動決定 (毎sim-hour) / 計画 (毎sim-day朝) / リフレクション (4sim-hourごとstagger) |
| 記憶 | SQLite per-agent / 重要度1-10で優先選別 / 日次LLMダイジェストで圧縮 |
| 並列化 | ThreadPoolExecutor + ホストプール (semaphore-1/host) で複数LLMホストRR |
| NPC | 35人に曜日・時間ベースの行動ルーチン (LLM不使用、ルール) |
| ロギング | events.log / dialogue.log / memory.db / 4sim-hourごとPNGスナップショット / 日次state JSON |
| Discord | 各sim-day終了時に記者風日記をスナップショット添付で投稿 |
| 再開 | sim-hourごとの latest_checkpoint.json から任意のタイミングで resume 可能 |
| 性能 | 投機デコード無し / Flash Attention ON / cache_reuse / 25人で 7日 ≈ 12時間 |

## 構成

```
metro-75/
├── sim/                     # シミュレーション本体
│   ├── world.py             # 250×250タイル + ランドマーク + 時刻
│   ├── mapgen.py            # 街マップ生成 (ブロック分割・建物大小・川)
│   ├── agent.py             # AgentState + decide_action + execute_action
│   ├── cognition.py         # generate_daily_plan / reflect
│   ├── memory.py            # SQLite-backed per-agent memory + format_context
│   ├── tick.py              # メインtickループ (3-Phase並列化)
│   ├── npc_routine.py       # NPC 35人の曜日×時間ルーチン
│   ├── events.py            # Day 0 仕掛けイベント9件
│   ├── digest.py            # 日次LLMサマリで古い記憶を圧縮
│   ├── diary.py             # Discord webhook で記者日記投稿
│   ├── llm.py               # OpenAI互換 /v1/chat/completions + ホストプール
│   ├── pathfind.py          # A* (タイル種別コスト)
│   └── render.py            # PIL でタイル+エージェントPNG出力
├── personas/                # 60人のペルソナ JSON
├── map/metro.json           # 生成済み街マップ
├── run_28day.py             # メインランナー (--days N)
├── resume_run.py            # チェックポイントから再開
├── scripts/                 # セットアップ/分析/ベンチスクリプト
│   ├── add_new_personas.py  # NPC増設
│   ├── katakana_names.py    # ペルソナのカタカナ化
│   ├── render_overview.py   # マップ全景PNG生成
│   ├── dump_profiles.py     # NPCS.md再生成
│   ├── summarize_per_day.py # 日別サマリ Discord 投稿
│   ├── timeline.py          # 完走後の事件タイムライン抽出
│   ├── generate_report.py   # 統計レポート
│   ├── bench_llamaserver.py # LLM レイテンシ計測
│   └── ...                  # その他テスト・update スクリプト
└── docs/
    ├── REQUIREMENTS.md      # 技術要件まとめ
    ├── SCENARIO.md          # シナリオ設定 (相関図/Day 0 イベント)
    ├── NPCS.md              # 全60人プロフィール
    └── optimization/        # 4本の最適化分析メモ
```

## インストール

```bash
# 依存
pip install Pillow

# llama.cpp (例)
# Qwen3-30B-A3B Q4_K_M GGUF を別途用意
# https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507-GGUF
```

## 使い方

```bash
# 1. llama-server を起動 (例: speculative なし、cache_reuse あり)
llama-server.exe --port 8080 --host 0.0.0.0 \
  --model Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf \
  -ngl 999 --ctx-size 4096 --flash-attn on \
  --cache-reuse 256 --parallel 2

# 2. マップ生成 (初回のみ)
python -m sim.mapgen

# 3. 7日間シミュレーション
LLM_HOSTS=http://127.0.0.1:8080,http://127.0.0.1:8080 \
DISCORD_WEBHOOK=https://discord.com/api/webhooks/... \
python run_28day.py --days 7

# 4. 途中再開
python resume_run.py --source logs/run7day_<ts> --from-checkpoint --days 14
```

環境変数:

| 変数 | 用途 | デフォルト |
|---|---|---|
| `LLM_HOSTS` | カンマ区切りLLMホストURL (重複可で並列スロット数指定) | `http://127.0.0.1:8080` |
| `MODEL` | モデル名 (llama-serverは無視) | `default` |
| `NUM_CTX` | コンテキスト長 | `4096` |
| `DISCORD_WEBHOOK` | 日記投稿先webhook URL | (空文字、無効化) |

## ライセンス

[MIT](LICENSE)
