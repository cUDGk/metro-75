"""Probe plan + reflect LLM calls directly."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
os.environ['LLM_HOSTS'] = 'http://192.168.1.7:8080'
from sim import llm

# Replicate plan prompt
system = ("JAP28(gang_c). 日系3世、26歳。本名は山中だが街では「JAP28」しか名乗らない 目的:カラブレーゼ親分の右腕として認められる,カラブレーゼ商会経由で月$50K回す,ガーネット Cobra Set との抗争を終結 or 全壊\n"
          "今日の計画を2-4個の具体目標で。場所/人物/行動を名指し、日本語のみ。\n"
          'JSON: {"plan":["...","..."]}\n/no_think')
user = "NOW Day 0(月) 06:00 @(32,217)\n昨日までの重要記憶:\n[Day 0 05:59|obs|i5] Day 0、06:00。コブラキラーは今日もカラブレーゼ商会の表で営業中。\n計画 JSON のみ:"

print('=== Plan probe ===')
for i in range(3):
    raw = llm.chat([{'role':'system','content':system},{'role':'user','content':user}],
                    max_tokens=300, temperature=0.85, response_format='json')
    print(f'attempt {i+1}: {raw[:200]}')
    try:
        d = json.loads(raw)
        print(f'  parsed: {d}')
    except Exception as e:
        print(f'  PARSE ERROR: {e}')
