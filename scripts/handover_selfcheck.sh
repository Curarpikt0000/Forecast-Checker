#!/bin/bash
# handover_selfcheck.sh — 接手方第一条命令。只读，不改任何东西、不写 Notion、不调用付费 API。
# 用法: bash scripts/handover_selfcheck.sh [--no-net]
#   --no-net: 跳过所有需要网络/凭证的检查(Notion、公网)，用于只 git pull 后的离线体检
# 退出码: 0=可接手  1=有 FAIL(必须先修)  2=只有 WARN(可接手但有降级)
# 每一项失败都会打印「为什么重要」和「怎么修」，不需要再翻文档。
cd "$(dirname "$0")/.." || exit 1
ROOT="$(pwd)"
NET=1; [ "${1:-}" = "--no-net" ] && NET=0
PASS=0; FAIL=0; WARN=0
ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ✗ FAIL  $1"; echo "      为什么: $2"; echo "      怎么修: $3"; FAIL=$((FAIL+1)); }
warn() { echo "  ! WARN  $1"; echo "      影响: $2"; echo "      建议: $3"; WARN=$((WARN+1)); }
PY=python3

echo "== 1. 基础环境 =="
command -v $PY >/dev/null && ok "python3 可用 ($($PY --version 2>&1))" || bad "没有 python3" "整条流水线是 Python" "安装 python3.10+"
$PY - <<'PYEOF' >/dev/null 2>&1 && ok "Python 版本 >= 3.10" || bad "Python 版本过低" "脚本用了新语法" "升级到 3.10+"
import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)
PYEOF
command -v git >/dev/null && ok "git 可用" || bad "没有 git" "发布与备份靠 git" "安装 git"
command -v rsync >/dev/null && ok "rsync 可用" || warn "没有 rsync" "publish.sh 第 4 步(内部端同步)会失败，其余照常" "安装 rsync，或接手方没有内部仓库就忽略"
command -v curl >/dev/null && ok "curl 可用" || warn "没有 curl" "验证公网 md5 要用" "安装 curl"
[ "$(TZ=Asia/Tokyo date +%Z)" = "JST" ] && ok "TZ=Asia/Tokyo 可用(cron 用东京时间)" || warn "无法取东京时区" "collected_on 日期会错位" "装 tzdata"
SYSTZ=$(date +%Z); [ "$SYSTZ" = "JST" ] && ok "系统时区是 JST" || warn "系统时区是 $SYSTZ 不是 JST" "cron 的 13:20 是按系统时区算的；时区不对会在错误时点触发" "timedatectl set-timezone Asia/Tokyo"

echo "== 2. 仓库完整性(只 pull 公网仓库能拿到的东西) =="
for f in AGENTS.md HANDOVER.md SETUP.md ops/cron-jobs.json scripts/merge_backfill.py scripts/apply_p4_verdicts.py scripts/apply_p5_realdates.py scripts/compute_ratings.py scripts/build_dashboard.py scripts/check_consistency.py scripts/export_targets_from_notion.py scripts/add_person_to_notion.py data/backfill_full.json; do
  [ -f "$f" ] && ok "有 $f" || bad "缺 $f" "接手必需文件" "git pull；若仍缺说明公网仓库没跟踪它，找负责人从内部仓库取"
done
[ -f scripts/check_totals.py ] && ok "有 scripts/check_totals.py" || warn "缺 scripts/check_totals.py(公网仓库历史上就没跟踪它)" "cron 第 5 步调用它，缺则该步报错" "自建: 见 SETUP.md §3 的 2 行脚本，或从内部仓库取"
[ -f index.html ] && ok "有根目录 index.html(Pages 入口)" || bad "缺 index.html" "公网入口文件" "跑 build_dashboard.py 后 cp dashboard/index.html index.html"

echo "== 3. 只存在于内部仓库/本机的关键文件(公网 pull 拿不到) =="
if [ -f data/batch_daily.json ]; then
  SZ=$(wc -c < data/batch_daily.json); [ "$SZ" -gt 100000 ] && ok "data/batch_daily.json 在(${SZ}字节)" || warn "data/batch_daily.json 太小(${SZ}字节)" "可能是空壳；merge 会因防回退断言拒绝，不会丢数据但无法每日合并" "从内部仓库 Forecast-Checker/data/batch_daily.json 取回真文件"
else bad "缺 data/batch_daily.json" "每日增量的源文件；缺它时 merge_backfill 会报「预言数减少」退出码 2" "★绝不要设 FC_ALLOW_SHRINK=1 硬 merge(历史增量会永久消失)。从内部仓库 Forecast-Checker/data/batch_daily.json 取，或向负责人要"; fi
[ -f scripts/publish.sh ] && ok "有 scripts/publish.sh" || bad "缺 scripts/publish.sh" "发布一条龙；它被公网仓库 gitignore(含内网标识)" "从内部仓库 Forecast-Checker/scripts/publish.sh 取"
[ -f scripts/notion_append_new.py ] && ok "有 scripts/notion_append_new.py" || warn "缺 scripts/notion_append_new.py" "每日 Notion 页面正文追加会被跳过(publish.sh 里有存在性判断，不会报错)" "从内部仓库取"
[ -f data/notion_ids.json ] && ok "有 data/notion_ids.json" || bad "缺 data/notion_ids.json" "Notion 坐标，gitignore 且不在公网" "向负责人要 database_id，按 SETUP.md §4 重建"

echo "== 4. 凭证(只检查变量名在不在，绝不打印值) =="
if [ -f .env ]; then
  for k in NOTION_TOKEN; do grep -q "^$k=." .env && ok ".env 有 $k" || bad ".env 缺 $k" "Notion 读写必需" "向负责人要，写入 .env，绝不进 git"; done
  grep -q "^NOTION_VERSION=" .env && ok ".env 有 NOTION_VERSION" || warn ".env 没有 NOTION_VERSION" "脚本默认 2022-06-28" "不处理也行"
else bad "没有 .env" "所有 Notion 脚本读它" "按 SETUP.md §2 创建"; fi
[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || grep -qs "^CLOUDFLARE_API_TOKEN=." ~/.hermes/.env 2>/dev/null && ok "找到 CLOUDFLARE_API_TOKEN(环境变量或 ~/.hermes/.env)" || warn "没找到 CLOUDFLARE_API_TOKEN" "publish.sh 第 6 步(Cloudflare 公网入口)会失败，其余端照常。★发布器只读环境变量和 ~/.hermes/.env，不读项目 .env" "写进 ~/.hermes/.env，见 SETUP.md §2"
[ -n "${CLOUDFLARE_ACCOUNT_ID:-}" ] || grep -qs "^CLOUDFLARE_ACCOUNT_ID=." ~/.hermes/.env 2>/dev/null && ok "找到 CLOUDFLARE_ACCOUNT_ID(环境变量或 ~/.hermes/.env)" || warn "没找到 CLOUDFLARE_ACCOUNT_ID" "同上" "SETUP.md §2"

echo "== 5. 仓库外依赖(不在 git 里，接手方要自备) =="
[ -x "$HOME/.hermes/scripts/publish_cf_pages.sh" ] && ok "有 ~/.hermes/scripts/publish_cf_pages.sh" || warn "缺 ~/.hermes/scripts/publish_cf_pages.sh" "Cloudflare 发布器；缺则公网入口不更新" "cp ops/hermes-scripts/publish_cf_pages.sh ~/.hermes/scripts/ && chmod +x"
[ -f "$HOME/.hermes/scripts/collect_forecast_checker_topic.py" ] && ok "有 ~/.hermes/scripts/collect_forecast_checker_topic.py" || warn "缺 collect_forecast_checker_topic.py" "上下文归档 cron 依赖它(不影响每日增量)" "cp ops/hermes-scripts/collect_forecast_checker_topic.py ~/.hermes/scripts/，并设 FC_TOPIC_THREAD"
[ -f "$HOME/.hermes/scripts/public_push_gate.sh" ] && ok "有 ~/.hermes/scripts/public_push_gate.sh(公网 GitHub 每两周推一次的闸)" || warn "缺 ~/.hermes/scripts/public_push_gate.sh" "publish.sh 第 3 步调用它；缺则该步报错(不阻断后面的内网同步与 Cloudflare)" "从原机器拷，或把 publish.sh 第 3 步改回直接 git push"
command -v wrangler >/dev/null || command -v npx >/dev/null && ok "有 wrangler 或 npx(Cloudflare 部署)" || warn "没有 wrangler/npx" "Cloudflare 部署需要" "npm i -g wrangler"
HERMES="$(command -v hermes || ls $HOME/.hermes/hermes-agent/venv/bin/hermes 2>/dev/null)"
[ -n "$HERMES" ] && ok "找到 hermes CLI" || bad "找不到 hermes CLI" "建 cron 要用；没有它整个每日自动化无法重建" "安装 Hermes Agent；cron 管理工具本身没有 model 参数，必须用 CLI"

echo "== 6. 数据自洽(只读 SSOT) =="
$PY - <<'PYEOF'
import json, sys, collections
try:
    S = json.load(open('data/backfill_full.json'))['people']
except Exception as e:
    print('  ✗ FAIL  无法读取 SSOT:', e); sys.exit(3)
P = [q for p in S for q in p['predictions']]
print(f"  ✓ SSOT 可读: {len(S)} 人 / {len(P)} 条预言")
al = collections.Counter(repr(p.get('alive')) for p in S)
print(f"  · alive 分布: {dict(al)}  (None 的人看板状态徽章不准，不影响采集)")
miss = [p['id'] for p in S if not p.get('predictions')]
print(f"  · 无预言的人: {miss}")
bad = [q for q in P if not q.get('source_url')]
print(('  ✓' if not bad else '  ✗ FAIL') + f" 每条预言都有 source_url ({len(bad)} 条缺)")
nd = sum(1 for q in P if not q.get('detail'))
print(f"  · 无 detail 的条目 {nd} (历史上约 20 条来自 YouTube Shorts/付费墙，属已知)")
PYEOF
[ $? -eq 3 ] && FAIL=$((FAIL+1))
$PY -m py_compile scripts/merge_backfill.py scripts/build_dashboard.py scripts/compute_ratings.py 2>/dev/null && ok "关键脚本可编译" || bad "关键脚本编译失败" "流水线跑不起来" "看 py_compile 报错"

echo "== 7. 推送目标(只看配置，不推送) =="
git remote -v 2>/dev/null | head -2 | sed 's/^/  · /'
git remote get-url origin >/dev/null 2>&1 && ok "git 有 origin" || warn "没有 origin" "publish.sh 个人端 push 会失败" "git remote add origin <你的仓库>"

if [ $NET -eq 1 ]; then
echo "== 8. 联网检查(只读) =="
$PY scripts/check_consistency.py 2>&1 | tail -12 | sed 's/^/  | /'
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 https://forecast-checker.pages.dev/ 2>/dev/null)
[ "$CODE" = "200" ] && ok "公网入口 forecast-checker.pages.dev 返回 200" || warn "公网入口返回 $CODE" "可能是网络或站点问题" "稍后重试；确认 Cloudflare 项目名是否变更"
fi

echo "== 9. 本机 cron 现状(只读 jobs.json) =="
JF="$HOME/.hermes/cron/jobs.json"
if [ -f "$JF" ]; then
$PY - "$JF" <<'PYEOF'
import json, sys
j = json.load(open(sys.argv[1])); jobs = j['jobs'] if isinstance(j, dict) else j
mine = [x for x in jobs if x.get('name') in ('Forecast-Checker daily increment', 'forecast-checker-context-distill')]
if not mine: print('  ! WARN  本机还没有本项目的 cron —— 这是接手的第一件事，按 SETUP.md §5 创建')
for x in mine:
    flag = '✓' if x.get('enabled') and x.get('last_status') in ('ok', None) else '!'
    print(f"  {flag} {x['name']}: {x['schedule']['expr']} model={x.get('model')} enabled={x.get('enabled')} last={x.get('last_status')} streak={x.get('failure_streak')}")
    if x['name'] == 'Forecast-Checker daily increment':
        if x.get('model') != 'claude-sonnet-5-5': print('    ! 模型不是 claude-sonnet-5-5；便宜模型 2026-10-03 试跑出过事故，改前读 HANDOVER §6.3')
        p = x.get('prompt') or ''
        if 'sync_notion_full' in p and '绝不' not in p: print('    ✗ prompt 里有 sync_notion_full 且没有「绝不」—— 这是 10-03 事故的根因，必须先改')
        else: print('    ✓ prompt 里没有诱导跑 sync_notion_full 的句子')
        if 'github.io' in p: print('    ! prompt 里仍有已失效的 github.io 地址')
PYEOF
else warn "找不到 $JF" "本机不是 Hermes 环境" "先安装 Hermes Agent"; fi

echo
echo "=============================="
echo "通过 $PASS  失败 $FAIL  警告 $WARN"
if [ $FAIL -gt 0 ]; then echo "结论: 还不能接手 —— 先修上面标 ✗ 的项"; exit 1
elif [ $WARN -gt 0 ]; then echo "结论: 可以接手，但有降级(见 ! WARN)"; exit 2
else echo "结论: 可以接手"; exit 0; fi
