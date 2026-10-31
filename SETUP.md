# Forecast-Checker 接手手册（SETUP）

> 给「另一个 agent / 另一台机器」的从零到跑起来清单。**先读本文，再读 `HANDOVER.md`（项目全貌与事故索引）。**
> 目标：`git pull` → 本文 §1–§6 → 一条命令 `bash scripts/handover_selfcheck.sh` 全绿 → 建 cron → 手动跑一次验证 → 才算接手。
> 原机器上的 cron 在你验证通过之前**不要停**；两边不能同时跑（重复抓取 + 双倍烧额度），验证通过后原 cron **暂停不删**（暂停即回滚点）。

## 0. 你需要从负责人那里拿到的东西（git 里没有，也不该有）

| 东西 | 用途 | 怎么给你 | 没有它会怎样 |
|---|---|---|---|
| `NOTION_TOKEN`（+ 可选 `NOTION_VERSION`） | 读「在世」名单、写 Notion 行 | 只给你变量值，写进 `.env`；**绝不进 git、绝不在聊天里回显** | 每日第一步就停 |
| Notion 的 `database_id` / `parent_page` / `url` / `ssot_kol_list_db` | 写进 `data/notion_ids.json`（gitignore） | 同上 | 同上 |
| `data/batch_daily.json`（约 1.5MB） | 每日增量**源文件**，merge 的输入 | **公网仓库没有它**。从内部仓库 `Forecast-Checker/data/batch_daily.json` 取 | merge 因「预言数减少」报错退出 2——**安全失败，不丢数据** |
| `scripts/publish.sh`、`scripts/publish_vibe.sh`、`scripts/notion_append_new.py` | 发布一条龙 / Notion 同步 | 公网仓库 gitignore 了它们（含内部标识/Notion 坐标）。从内部仓库 `Forecast-Checker/scripts/` 取 | 无法一键发布 |
| `~/.hermes/scripts/public_push_gate.sh` | 公网 GitHub 推送闸（每 14 天放行一次） | 从原机器拷；缺它 `publish.sh` 第 3 步报错 | 第 3 步失败，但**不阻断**后面的内网同步与 Cloudflare |
| `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID` | 公网入口 `forecast-checker.pages.dev` | 写进环境变量或 **`~/.hermes/.env`**（不是项目 `.env`） | 公网入口不更新，其余端照常 |
| 你自己的 Telegram 话题（chat_id:thread_id） | cron 投递战报、上下文归档 | 你自己建 | 战报发不出来 |

> **没有内部仓库访问权限的接手方**：公网仓库 + 上表前两行就能让你读数据、改看板、跑 `build_dashboard.py`；但**每日增量与完整发布**需要 `batch_daily.json` 与 `publish.sh`，必须向负责人要。别自己重写——`publish.sh` 里每一段都对应过一次事故（见 `HANDOVER.md §14`）。

## 1. 拉代码与环境

```bash
git clone https://github.com/Curarpikt0000/Forecast-Checker.git && cd Forecast-Checker
# 2026-10-31 起该仓库匿名可 clone(曾在 9 月被风控标记 404，现已恢复，原因未知)；若又变 404 → 用有权限的账号 gh auth login 后 clone，或向负责人要内部仓库地址
python3 --version      # 需要 >= 3.10
git remote -v          # 确认 origin 是【你自己的】仓库，别推到别人的
```
系统时区必须是 **Asia/Tokyo（JST）**：cron 的 `20 13 * * *` 是按系统时区触发的。`timedatectl set-timezone Asia/Tokyo`。

## 2. 凭证（只写变量名，值向负责人要）

```bash
cat > .env <<'EOF'
NOTION_TOKEN=<向负责人要>
NOTION_VERSION=2022-06-28
EOF
chmod 600 .env
# .env 已在 .gitignore。不要 echo、不要 cat 给任何人看。
```
**Cloudflare 的两个变量（`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`）必须放进环境变量或 `~/.hermes/.env`——发布器 `publish_cf_pages.sh` 只读这两处，不读项目根的 `.env`**（放错地方的症状：发布到第 6 步报 `CREDENTIALS MISSING`，其余端正常）。`data/notion_ids.json` 的结构：
```json
{"parent_page": "<...>", "database_id": "<...>", "url": "<...>", "ssot_kol_list_db": "<...>"}
```

## 3. 补齐「公网 pull 拿不到」的文件

```bash
# 从内部仓库(或原机器)拷到对应位置，缺哪个补哪个
#   data/batch_daily.json   scripts/publish.sh   scripts/publish_vibe.sh   scripts/notion_append_new.py   scripts/check_totals.py
# 其中 check_totals.py 很小，可以自建(公网仓库历史上就没有跟踪它)：
cat > scripts/check_totals.py <<'EOF'
import json, os
d = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'backfill_full.json')))['people']
print(len(d), sum(len(p['predictions']) for p in d))
EOF
```
**绝不要**设 `FC_ALLOW_SHRINK=1` 去强行 merge 缺了 `batch_daily.json` 的状态：它会让历史每日增量从 SSOT 里永久消失。

## 4. 仓库外脚本

```bash
mkdir -p ~/.hermes/scripts
cp ops/hermes-scripts/publish_cf_pages.sh ~/.hermes/scripts/ && chmod +x ~/.hermes/scripts/publish_cf_pages.sh
cp ops/hermes-scripts/collect_forecast_checker_topic.py ~/.hermes/scripts/
# 后者依赖你本机已有的通用采集器 ~/.hermes/scripts/collect_topic_conversation.py；
# 没有的话上下文归档 cron 无法工作，但不影响每日增量，可以先不建那个 cron。
```
`publish_cf_pages.sh` 的退出码：3 源缺失 / 4 红线命中 / 5 凭证缺失 / 6 wrangler 缺失 / 7 部署失败 / 8 部署后线上实测不符。用法 `publish_cf_pages.sh <cf项目名> <html路径>`。

## 5. 创建 cron（真实快照在 `ops/cron-jobs.json`）

**只有 2 个 job；系统 crontab 里没有本项目任务。** 把 `<PROJECT_ROOT>` 换成你的绝对路径，`<HOME>` 换成你的 home。

```bash
# 默认只演练：打印将要执行的命令与 prompt 摘要，不创建任何东西
bash ops/create_cron.sh
# 确认无误后真正创建(会在你当前所在的 Telegram 话题投递；务必在你自己的话题里执行)：
APPLY=1 bash ops/create_cron.sh
# 创建前脚本会检查：本机是否已有同名 job(有就拒绝，避免重复抓取双倍烧额度)
```
上下文归档那个 job 是可选的（依赖 §4 的采集脚本和 `FC_TOPIC_THREAD`），需要时手动建，参数见 `ops/cron-jobs.json` 里它的条目。

> 说明：`hermes cron create` 的具体参数以你本机 `hermes cron create --help` 为准；上面是 2026-10-31 在原机器上验证过的形态。**`cronjob_manage` 工具没有 `model` 参数**，设模型只能用 CLI。
> `--deliver origin` 会投递到「你创建它时所在的话题」。**在你自己的话题里创建**，不要照抄原机器的 chat_id。
> **模型钉死 `claude-sonnet-5-5`。** 2026-10-03 换 `claude-haiku-4-5` 试跑当天就出事故（便宜模型把 prompt 里一句过期指令照字面执行，Notion 被清空重写到一半）。再想试便宜模型之前先读 `HANDOVER.md §6.3`。

## 6. 验证（逐条，别跳）

```bash
bash scripts/handover_selfcheck.sh            # 全绿 或 只有已知 WARN，才算环境就绪
python3 scripts/check_consistency.py          # SSOT / Notion / 公网 三处必须全绿
# 手动跑一次(不是等定时)：
bash scripts/publish.sh                       # 5 分钟左右；放后台跑，前台命令有 10 分钟上限
curl -s https://forecast-checker.pages.dev/ -o /tmp/l.html; md5sum /tmp/l.html index.html   # 必须逐字节一致
```
确认 Cloudflare 的 md5 与本地一致之后，才去**暂停**原机器上的 cron（一个一个暂停并读回，不要按名字前缀批量暂停——同一份 jobs.json 里还有别的项目的 job）。

## 7. 日常

- **验收今天的 cron**：`ls -t ~/.hermes/cron/output/<job_id>/ | head -2` + `git log -3` + `python3 scripts/check_consistency.py`。**状态标签 `ok / API calls: 0 / timeout` 不等于产出**，必须查库与提交。
- **对账红了的唯一合法修法**：缺人 `python3 scripts/add_person_to_notion.py <id…>`；条数不对 `python3 scripts/add_person_to_notion.py --update <id…>`。**永远不要跑 `scripts/sync_notion_full.py`**（先 archive 全库再重写，会抹掉人工评分，2026-10-03 出过事故）。
- **公网 GitHub 现在每两周才推一次**（2026-10-30 起；提交仍每天做，只拦 `git push`）。闸是仓库外脚本 `~/.hermes/scripts/public_push_gate.sh`，`publish.sh` 第 3 步调用它：`bash ~/.hermes/scripts/public_push_gate.sh status` 看上次推送与下次放行；手动补推用 `PUBLIC_PUSH_FORCE=1`。
  **所以「公网 GitHub 仓库里的内容比本地旧几天」是设计，不是故障**；日常看公网状态请看 `forecast-checker.pages.dev`（每天更新）。
  接手方如果没有这个闸脚本，`publish.sh` 第 3 步会直接报错——要么从原机器拷该脚本，要么把第 3 步改回直接 `git push`。
- **cron 战报里「curl 取状态码被安全扫描拦下」是常态**（近两周 12/14 次）：prompt 第 5 步的 curl 在 cron 环境里经常被拦，公网项靠 `check_consistency.py` 的公网检查顶替，不是故障。
- **每日约 15–20 位在世者因搜索超时或查无而未覆盖**（92 位里只搜到一部分），是工具限制，不是模型问题。
- 新增 / 删除 KOL、补应验判定、回查发表日、改看板的步骤：`HANDOVER.md §7`。驱动技能副本：`self-skill/forecast-checker-pipeline/SKILL.md`，把它拷到 `~/.hermes/skills/devops/` 即可被 agent 自动加载。

## 8. 接手后你应当改掉的已知问题

见 `HANDOVER.md §13`。当前未处理的有：4 人 SSOT 的 `alive` 为 `None`（Gilliland / Rense / Salla / Rosicrucian）、公网仓库缺 `check_totals.py`（§3 的自建脚本可顶替）、`AGENTS.md` 有过时说明（受保护文件，改动需负责人批准）。
