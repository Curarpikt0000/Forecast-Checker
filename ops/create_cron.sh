#!/bin/bash
# create_cron.sh — 从 ops/cron-jobs.json 创建「每日增量」cron。默认只演练(DRY-RUN)，APPLY=1 才真创建。
# 安全闸: ①本机已有同名 job 则拒绝(重复抓取会双倍烧额度、还会争同一个工作目录锁) ②模型固定读快照(sonnet-5-5)
# 在【你自己的】Telegram 话题里执行：--deliver origin 会投递到「创建它时所在的话题」。
set -u
cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
H="$(command -v hermes || echo $HOME/.hermes/hermes-agent/venv/bin/hermes)"
[ -x "$H" ] || { echo "找不到 hermes CLI: $H"; exit 1; }
JOB="Forecast-Checker daily increment"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
python3 - "$ROOT" "$TMP" <<'PYEOF' || exit 1
import json, sys
root, out = sys.argv[1], sys.argv[2]
j = [x for x in json.load(open('ops/cron-jobs.json'))['jobs'] if x['name'] == 'Forecast-Checker daily increment'][0]
open(out, 'w', encoding='utf-8').write(j['prompt'].replace('<PROJECT_ROOT>', root).replace('<HOME>', __import__('os').path.expanduser('~')))
open(out + '.meta', 'w').write(json.dumps({k: j[k] for k in ('schedule_cron', 'model', 'provider')}))
PYEOF
SCHED=$(python3 -c "import json;print(json.load(open('$TMP.meta'))['schedule_cron'])")
MODEL=$(python3 -c "import json;print(json.load(open('$TMP.meta'))['model'])")
PROV=$(python3 -c "import json;print(json.load(open('$TMP.meta'))['provider'])")
rm -f "$TMP.meta"
echo "将创建: name=\"$JOB\" schedule=\"$SCHED\" model=$MODEL provider=$PROV workdir=$ROOT deliver=origin"
echo "prompt 共 $(wc -c < "$TMP") 字符; 首行: $(head -1 "$TMP" | cut -c1-70)…"
# 校验 prompt 里没有任何残留占位符、也没有诱导跑 sync_notion_full 的句子
grep -q '<PROJECT_ROOT>\|<HOME>' "$TMP" && { echo "✗ prompt 里还有未替换的占位符"; exit 1; }
if grep -q 'sync_notion_full' "$TMP" && ! grep -q '绝不' "$TMP"; then echo "✗ prompt 含 sync_notion_full 且无「绝不」(10-03 事故根因)，拒绝"; exit 1; fi
echo "✓ prompt 校验通过(无占位符残留；Notion 步骤是只增不删写法)"
# 重复检查
if "$H" cron list 2>/dev/null | grep -qF "$JOB"; then echo "✗ 本机已有同名 job「$JOB」—— 拒绝重复创建。要重建请先 hermes cron remove，并确认原 job 已暂停"; exit 2; fi
echo "✓ 本机没有同名 job"
if [ "${APPLY:-0}" != "1" ]; then echo; echo "【演练模式】未创建任何东西。确认无误后: APPLY=1 bash ops/create_cron.sh"; exit 0; fi
"$H" cron create "$SCHED" "$(cat "$TMP")" --name "$JOB" --workdir "$ROOT" --deliver origin --model "$MODEL" --provider "$PROV" && echo "✓ 已创建" || { echo "✗ 创建失败"; exit 3; }
echo "读回: "; "$H" cron list 2>/dev/null | grep -F -A3 "$JOB" | head -8
