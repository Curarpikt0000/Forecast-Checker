---
name: forecast-checker-pipeline
description: Use when editing the Forecast-Checker KOL dashboard.
---

# Forecast-Checker 流水线纪律（接手版副本，源自运行中的 agent 技能，2026-10-31 导出）

适用：给 Forecast-Checker 看板增/删 KOL、跑流水线、同步 Notion、发布公网。
项目目录：`<PROJECT_ROOT>`｜**公网入口：https://forecast-checker.pages.dev/**（Cloudflare Pages；旧 GitHub Pages 地址因账号被风控标记已匿名 404）
**接手先读仓库根的 `SETUP.md` 与 `HANDOVER.md`**，再读项目 `AGENTS.md`（定位、双端同步、评分口径）。本技能只记 **AGENTS.md 没写、且实际咬过人的机制**。

## 流水线顺序（不可调换）
```
merge_backfill.py → apply_p4_verdicts.py → apply_p5_realdates.py
                  → compute_ratings.py → build_dashboard.py
```
`merge` 从源文件重建 SSOT，不认识后处理字段，会直接覆盖。手动重跑 merge 后三步必须补跑。

## 三个会静默吃掉你改动的门禁

### 1. verified 判定写 batch 源文件 = 白写
`merge_backfill.py`（约 245-251 行）**无条件**按 `summary` 关键词正则（`_HIT_RE`/`_MISS_RE`）重算
`verified`，源文件里写的 `hit`/`miss`/`unclear` 一律被覆盖成 `pending`；
`apply_p4_verdicts.py` 只覆盖 `pending`，不会改回来。

**人工判定的唯一正确落点 = `data/p4_verdict_*.json`**，按 `(person_id, 归一化 summary)` 精确匹配：
```json
[{"person_id": "xxx",
  "verdicts": [{"summary": "必须与 batch 里逐字一致",
                "verdict": "hit|miss|unclear",
                "verdict_reason": "...", "verdict_source": "https://..."}]}]
```

> ★ **写这类文件前必须 `read_file` 一份现成的，绝不凭直觉猜字段名。**
> 曾有人猜过 `summary_match` / `reason` / 扁平结构（无 `verdicts` 嵌套）——**三个全错**。
> 恶化点在于：`apply_p4_verdicts.py` 对认不得的 schema **不报错也不警告**，
> 整个文件被静默忽略，条目留在 `pending`，流水线全程 `exit 0` 看不出任何异常。
> 唯一发现方式 = 跑完回查库里 `verified` 实际值。**写完必验：**
> ```bash
> python3 -c "import json;ks=json.load(open('data/backfill_full.json'));\
> x=next(y for y in ks if y['id']=='<id>');\
> print([(p['verified'],len(p.get('verdict_reason') or '')) for p in x['predictions']])"
> ```
> 同类推论：本项目所有 `p4_verdict_*` / `p5_realdate_*` / `batch_*` 新建文件，
> 一律先读一份同类现成文件对齐 schema。

### 2. FC_ALLOW_SHRINK 防回退门禁（删人必踩）
`merge_backfill.py` 约 294 行：人数或条数**减少**即 `sys.exit(2)` 拒绝覆盖 SSOT。
有意删除时：`FC_ALLOW_SHRINK=1 python3 scripts/merge_backfill.py`，
发布同理 `FC_ALLOW_SHRINK=1 bash scripts/publish.sh`。

> ★ 它把原因和解法都打印在 **stderr**。**绝不要用 `>/dev/null 2>&1` 跑流水线**——
> 曾有人因此连续三轮以为「删除没生效」，去猜了三个错误根因，答案一直在被丢掉的 stderr 里。

### 3. target_year 的年份正则不认 19xx/24xx
`_YR_RE = re.compile(r"(20\d{2}|21\d{2})")`。写 `target_date: "1929"` 或 `"2486"` → `target_year` 为 `None`。
**这是常态不是 bug**（全库约 43/1390 条本就为空，历史人物皆如此），
为单个人改这个正则会波及其余数十条，不要改。

## 新增人物
1. 先查重 + 查库内既有枚举值（`person_type` / `domain` **只能复用，不新建**）。
2. 写 `data/batch_<name>.json`。
3. **两处**都要加，缺一不可（`merge_backfill.py`）：
   - `_MERGE_APPEND` 元组（否则整体覆盖同 id 记录 = 删光此人原有预言）
   - 下方加载列表，且必须排在 `batch_daily.json` **之前**
4. Preflight（当作硬门禁跑，别靠记得检查）：
   person_type/domain 已存在 ✓｜每条有 `quote_en`+`target_date`+`source_url`(http开头)+`detail`≥100字 ✓｜红线 grep clean
5. 跑流水线 → `scripts/add_person_to_notion.py <id>` → `bash scripts/publish.sh` → 验证。

> 校验脚本里**别用裸字符串匹配判断标注是否存在**（如只匹配「媒体转述」会漏掉「媒体对其理论的转述」），
> 会制造假阴性让你以为数据有错。数据没错时先怀疑校验脚本自己。

## 删除人物（违反「只增不减」铁律，必须用户明确指令）
删前先 dry-run 列名单 + 完整备份记录到 `/tmp/`，并**主动向用户指出机械规则的误伤**
（例：「已故且无 2026 条目」会连带删掉他刚要求加入的人；已故 ≠ 无新条目，
历史预言家如 Cayce/Vanga/Nostradamus 因被持续重新解读而有 2026 条目）。

**必须清理的源文件类型（漏一类就删不干净）：**
| 文件 | 匹配键 | 结构 |
|---|---|---|
| `batch_*.json` | `id` | list |
| `p4_verdict_*.json` | `person_id` | list |
| `p5_realdate_*.json` | `id` | list |
| `sample_backfill.json` | `id` | dict`{samples:[...]}` |
| `new_people_batch*.json` | **`en_name`** | list — **不带 id**，merge 用 `_mk_id(en_name)` 动态生成，按 id 匹配永远扫不到 |
| `details/<person_id>.json` | 文件名 | 单文件 |
| `roster_candidates.json` | `id` | dict`{candidates:[...]}` |
| `kol_list_ssot.json` | `id` | list |

> ⚠️ **`data/_removed_backup/` 是只读历史快照，绝不要动。**
> 用 `glob(recursive=True)` 扫 `data/` 会误改它们（我干过，靠 `/tmp` 备份还原）。

**Notion 移除**：`add_person_to_notion.py` 刻意不做 archive；`notion_ids.json` 只有 `database_id`，**不存每人 page_id**。
流程 = query database 全量 → 按 title 精确匹配 `display_name` → `PATCH {"archived": true}`（进回收站可恢复，非硬删）。

## 验证（唯一判据，不看脚本自报）
```bash
sleep 75   # GitHub Pages CDN 缓存
python3 scripts/check_consistency.py      # 三处对账须全绿
curl -s -H "Cache-Control: no-cache" "<公网URL>?cb=$(date +%s)" -o /tmp/l.html
md5sum /tmp/l.html index.html             # 必须逐字节一致
```
人名/关键词在线上出现次数也顺手 grep 一遍。正文里提到被删者的人名（如他人 bio 引用）属正常残留，不是卡片没删掉。

内联复合命令（publish + sleep + 对账 + curl）会被解析器拦下（`exit -1`）——写成 `scratch/_verify_liveN.sh` 脚本文件执行。

## 采集：同名污染
通用搜索极易被同名者污染（实测搜 Denis Simon 连续三次返回同名足病医生）。
破解 = **站点定向到其一手发表渠道**（`site:responsiblestatecraft.org ...`），而非堆砌关键词。
（同名污染的判别思路见 HANDOVER §10。）

某些站点 `web_extract` 只能取到几千字符（正文被截断）。退路：
`curl -A "Mozilla/5.0 ..."` 存 HTML → 正则抽 `<p>` 标签。别据截断正文下结论。

## 发布是**多端**的——先读 publish.sh，别凭记忆或翻聊天记录断言某端「没做」

`scripts/publish.sh` 当前是 5 段式，远不止公网一端：
```
merge/判定/星级/build → cp 到根 index.html → 红线扫描
  → ① 个人端 GitHub push（remote 读回校验）
  → ② 内部 monorepo rsync + push
  → ③ 内网 vibe   (scripts/publish_vibe.sh)
  → ④ Cloudflare Pages
```
成功一行长这样，四端各自打印自己的证据：
```
个人端已 push / 内部端已 push
vibe: deployed v10
cf[forecast-checker]: LIVE https://forecast-checker.pages.dev/ (sha …, 11345127 bytes)
```

> ★★ **一个真实发生过的判断错误**：用户问「Cloudflare 那条做了没」，执行者搜聊天记录搜不到，
> 就断言「没做，而且从没讨论过」。实际上 publish.sh 里**早就接好并在跑**。
> **聊天记录搜不到 ≠ 没做**——他同时在多 agent / 多 session / 多机器上推进同一项目。
> 判据永远是**读代码 / 跑一次看输出**，不是检索对话历史。

`check_consistency.py` 也已覆盖到公网端；四处（SSOT / Notion / 本地 / 公网）应全绿。

### 内网端脚本必须 gitignore（含内网标识）
`scripts/publish_vibe.sh`（内网静态托管发布脚本）含内部环境标识，属红线词范围，**绝不能进公网仓库**。
光靠 publish.sh 的「显式 git add 清单」保护太脆——谁写一次 `git add .` 就漏。
已加 `.gitignore` 硬防护；改动这类脚本后复验：
```bash
git check-ignore -v scripts/publish_vibe.sh          # 必须命中
git ls-tree -r origin/main --name-only | grep -ci vibe   # 公网远端必须 0
```
vibe 端失败**不阻断**整体发布（前面几端已成功），但必须 `>&2` 打 `VIBE_PUBLISH_FAILED rc=N`，不许 `|| true` 吞掉。
vibe 上传 9.9MB 必须走 `--args-file`；成功判据是响应里的 `"status":"deployed"`，不是脚本自己 echo 的话。

## 每日任务核查（用户说「今天任务跑一下 / 跑了吗」）
1. 先查今天是否已跑：`ls -lt ~/.hermes/cron/output/683f038fb51c/` + `git log --since=今天`，再 `cronjob run`。
2. 完成通知里 `API calls: 0` / `Result: ok` 是外壳标签，**不代表产出**；必须逐项核：
   - 读 output md 的 `## Response` 段（任务自报数）
   - SSOT 里 `collected_on=今天` 的条数 == 自报新增数
   - 今天的 commit、本地 HEAD == origin
   - `check_consistency.py` 全绿
   - Cloudflare `curl ?cb=` 的 md5 == 本地 index.html
   - vibe：`get_vibe_app` 的 `version` 应比上次 +1/次；**`last_activity` 不会更新，别拿它判断**
3. 写成 `scratch/_verify_runMMDD.sh` 一次跑完（内联长命令会被拦）。
4. ~~已知固定毛病：发布脚本不更新 Notion 预言条数~~ ——**2026-10-03 起已修**：publish.sh 4.5 段自动 `--update` 属性 + `notion_append_new.py` 追加正文（见 `references/publish-hardening-and-notion-append-2026-10-03.md`）。对账仍红时再手动补。
5. **对账红时的唯一合法修法**：`add_person_to_notion.py <缺的id…>`（补建）/ `--update <id…>`（改属性）。
   **永远不要 `sync_notion_full.py`**。新建行评分默认写「未评」，要再 PATCH「评分」为 SSOT 星级（⭐×rating），只动新建行。
   用 Notion API 直查行数/已归档数/`last_edited_time` 分布判断是否被清空重写（全行同一小时被改 = 重写）。
6. Notion 正文设计上每人只放最新 12 条（`BODY_N=12`），条数/最新摘要是全量；SSOT 里 >12 条的人旧条目只在 SSOT/看板。用户问「backfill 有没有进 Notion」时按属性层+正文层分别答，别笼统说有。
   `bio` 为空只有 `bio_long` 的人（alive=None 那几个）Notion 正文无 bio 段，属 SSOT 数据缺口非同步错。

## 日增 cron 换模型（★2026-10-03 Haiku 试跑已失败并回滚到 sonnet-5-5，勿再直接换）
> 结果：Haiku 照字面执行了 cron prompt 第 6 步里「Notion 不一致就跑 `sync_notion_full.py`」→ 全库先清空再重写到一半断，Notion 只剩 57 行（SSOT 101）。
> Sonnet 同样读到这句话但读了 AGENTS.md 的禁令改用增量更新。**便宜模型不会替你调和 prompt 与项目禁令的冲突。**
> 已：model 改回 sonnet-5-5；prompt 第 5 步改 pages.dev、第 6 步改为「绝不跑 sync_notion_full，缺人 add_person_to_notion <id>、条数 --update」；Notion 用 add_person 补回 44 人。
> 想再试便宜模型前：先确认 prompt 里没有任何与 AGENTS.md 禁令冲突的「自愈」指令，且 prompt 的 Notion 步骤已是增量写法。详见 `references/notion-wipe-incident-and-restore-2026-10-03.md`。

（以下为 10-01 当时的试跑记录，规程仍可复用）
### 2026-10-01 起 Haiku 4.5 试跑的原始规程
- job `683f038fb51c` 的 `model` 字段原为空 = 跟随全局默认（claude-sonnet-5-5）。**先读 jobs.json 的 model 字段**再回答「cron 用什么模型」。
- `cronjob_manage update` 工具**没有 model 参数**（传了报 No updates provided）；用 CLI：
  `~/.hermes/hermes-agent/venv/bin/hermes cron edit 683f038fb51c --model claude-haiku-4-5 --provider custom`（PATH 里没有 `hermes`），
  改前备份 `~/.hermes/cron/jobs.json`，改后读回 model/schedule/workdir/toolsets 不变。
- 本机模型代理上可选更便宜模型：claude-haiku-4-5（Sonnet 约 1/3 价）、gemini-3.5-flash、deepseek-v4p1-flash（以接手方环境实际可用为准）。本项目难点是「每条锚真读原文、detail 不扩写、quote_en 逐字」，便宜模型最易在此偷懒，所以先试 Haiku 而非跨家族。
- 试跑规程：**不要当天手动再跑**（与定时产出混在一起无法对比），让次日 13:20 定时跑自然产生。基线=Sonnet 日增 8-12 条（9/28 +7、9/29 +10、9/30 +12、10/1 +8），每天约 20/88 人因工具限制未覆盖。
  验收五项：新增条数不塌缩｜`quote_en` 归一化匹配 100%｜抽 3 条核 detail 是否真读过原文｜source_url 可开且无同名误配｜`check_consistency` 是否一次全绿。任一项不过 → 改回 sonnet-5-5。
- 真正花钱的是并行子 agent；其模型来自全局 `delegation.model`（空=跟随主模型），那是全局配置，改动须项目负责人批准。
- 执行者无法自己定时回来核对：说「完成后请告诉我，我按五项出对比」，不要承诺具体时点。

## 知识库对应条目（接手方没有该知识库则忽略本节）
通用：`knowledge/frontend/data-dashboard-publishing.md` §8.20（设计审计：检测器按次数不按问题）。
项目：`pipelines/forecast-checker/engineering-lessons.md` 第 44 条（cron `model` 为空=继承、便宜模型是实验）、
第 45 条（交接文档要实测当前状态）。归档时共享 wiki 工作树里可能有别的 agent 已暂存的文件，只提交自己写的。

## 交接文档
全项目交接文档 = 根目录 `HANDOVER.md`（2026-10-01 重写，两仓库同内容）。数字/流程以它为准；旧 `HANDOVER-2026-08-22.md`、`docs/SESSION_HANDOVER_20260824.md` 已部分过期。
它列出的未决项里，`batch_daily.json` 未跟踪、cron prompt 第 5/6 步过期、6 人 alive/bio 缺失 **已于 2026-10-03 解决**（详见 `references/publish-hardening-and-notion-append-2026-10-03.md`）；仍待办：4 人 `alive=None`（Gilliland/Rense/Salla/Rosicrucian）｜公网仓库缺 `check_totals.py`｜HANDOVER §13 文档本身待更新。

## 解读/汇报库内条目时
- **summary 可能把原文两条不同因果线并成一句**（例：Armstrong「经济下行到 2028、2029 恐慌周期」——
  前半是政策致实体衰退，后半出自其内乱模型讲社会动荡，且他同时明确「近期股市不会崩」）。
  用户追问时必须回 source_url 原文逐句核对，并主动指出自己先前转述的并句误导。
- 同一 KOL 的「股/债/实体经济」判断常方向不同（Armstrong：债市崩、股市有资本流入托底），
  别用单一方向概括。
- 「近一周颠覆性预测」类问题：按 `date`(到日)≥起点 或 `collected_on`≥起点 拉条目，
  剔除星座日运周运、同源重复，再按主题分组；标出哪些只是转述新闻/民调（非独立信号）、
  哪些已到期待判定、星级是否暂定。
- 匿名站点/符号解读型来源（如 Vigilant Citizen）可按机构型条目收，bio 写明匿名与「解读他人预测」性质；
  原文主动取消时间约束或以反问句提出的，判定一律走 p4_verdict 记 `unclear`，不替其补全方向。

## 看板 UI 现状（改 build_dashboard.py 前必知，2026-10 impeccable 两轮后）
- 图标 = 内联 SVG sprite：`_SYM` / `ICON_SPRITE` / `ico(name)`，`PTYPE_META` 值是 `(ico(...), 色)`；
  **别再往 UI 里加 emoji**（元数据标签用纯文字「说于/目标/收录/取值」）。
- 文字用色走 `tcol(color)`（`TEXT_COLOR` 浅一档同色相），图形仍用原色；`--accent-t` 是文字版强调色。
- 卡片已无左侧彩色竖条；「星级怎么算」是默认收起的 `<details class="rate-note">`。
- 手机 ≤640px：筛选行单行横滑+右缘 mask 渐隐；导航悬浮钮在**左下**（右下会挡「详情」）。
- 必须保住的交互：星级金黄 `#ffc93c`、排序/筛选 `.cbtn`、`pmClose` 展开收起、最新言论 4 种排序。
- 改版审计流程见 HANDOVER §9 的改版记录。

## 已知隐患（2026-09）
- 根目录 `index.html` 约 **9.9MB 单文件**，cron 每日全量提交进 git → 仓库快速膨胀。
  项目负责人 2026-09 明确选择**不改推送节奏**（选项乙），知情接受风险；别再反复劝。
  根治方向仍是：产物不进 git，改云端构建部署。
- **`Site not found` ≠ `File not found`**：前者是整个站点不可服务。
  判据三件套：所有路径含 `README.md` 全 404 + REST API 返回 `Not Found` + 绕缓存仍 404。
  （另有一类短暂 404 确实是部署切换期 CDN 穿透会自愈——必须用三件套区分。）
- **公网 404 的真实根因（2026-09 查实）= GitHub 账号被反滥用系统 flagged，不是仓库问题。**
  完整诊断流程、证据表、五域名探测脚本、申诉文案见
  **`references/github-account-flagged-diagnosis.md`**。
  一句话要点：**「用户登录能正常看到」不是反证，恰恰是 flagged 的特征**——
  所有者视角不受影响，只对匿名访问者隐藏。别被它带偏去查仓库设置。
  此期间内网 vibe + Cloudflare 两端仍可用，数据零损失，照常干活。
