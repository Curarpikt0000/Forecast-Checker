# Forecast Checker — HANDOVER

> 灵媒 / 预言家 / 出体者 / 预知者 / 模型预测者 的公开预言汇总看板。
> 本文档是**唯一的全量交接文档**：读完它，任何 agent 或人都能接手每日运行、排障、加减人、改看板。
> 状态截至 **2026-10-01**。数字以 `python3 scripts/check_consistency.py` 实测为准，不以本文为准。
>
> 旧文档：`HANDOVER-2026-08-22.md`（54 人时代）、`docs/SESSION_HANDOVER_20260824.md`（P1-P5 阶段脉络、评分推导）。
> 它们没有被废弃，但**数字和部分流程已过期**；冲突时以本文为准。
> 本文取代的是旧 `HANDOVER.md`（2026-08-18 版，54 人 / 199 条，评分口径已被推翻）。

---

## 0. 一页纸状态

| 项 | 当前值 |
|---|---|
| 名册 | **101 人**（在世 88 / 已故 9 / `alive` 字段缺失 4，见 §13-7） |
| 预言条数 | **2055 条**；三层结构 `detail` 覆盖 2031/2055 |
| 应验判定 | hit 45 / miss 71 / unclear 131 / pending 1808（未到期，不计分） |
| 星级 | 101 人有星；**仅 18 人是真实战绩分**（已判定 ≥3 条），其余为「暂定」 |
| 星级分布 | 5★ 4 人 / 4★ 3 人 / 3★ 20 人 / 2★ 40 人 / 1★ 33 人 / 0 星 1 人（无预言） |
| 身份类型 | 预言先知 23 / 占星预言 19 / 灵媒通灵 16 / 模型预测者 14 / 金融玄学/术数 11 / 遥视RV 10 / 预知研究 6 / 出体OBE 2 |
| 领域（条） | 社会政治 409 / 灵性个人 387 / 金融市场 289 / 金融经济 250 / 地缘军事 242 / 科技AI未来 235 / 自然灾害 129 / 科学意识 71 / 健康疫情 43 |
| 每日自动化 | 1 个 agent cron，每天 **13:20 JST**，模型 **claude-sonnet-5-5**（Haiku 试跑 2026-10-03 已终止，见 §6.3） |
| 一致性 | SSOT ↔ Notion ↔ 公网：全绿（2026-10-31 实测）；Notion 页面正文每日追加新增预言 |
| **公网入口** | **https://forecast-checker.pages.dev/**（Cloudflare Pages，每天更新） |
| ⚠ GitHub Pages | 个人账号被 GitHub 风控标记，**匿名访问全站 404**，已申诉（2026-09-19），等待回复。**push 不受影响** |
| **公网 GitHub 推送节奏** | **每 14 天一次**（2026-10-30 起；提交仍每天做，闸脚本 `~/.hermes/scripts/public_push_gate.sh`）。公网仓库比本地旧是设计，不是故障 |
| **接手入口** | **先读 `SETUP.md`**，再跑 `bash scripts/handover_selfcheck.sh` |

**三条最重要的话**
1. **流水线顺序不可调换**：`merge → p4 判定 → p5 发表日 → 算星级 → build`。merge 会从源文件重建 SSOT，不认识后处理字段，少一步线上就退回「无判定、无星级、日期错乱」。
2. **新增 batch 文件必须进 `merge_backfill.py` 的白名单（两处）**，否则整体覆盖同 id 记录 = 静默删掉此人全部历史预言。
3. **便宜模型会把过期指令照字面执行**：2026-10-03 Haiku 4.5 试跑当天就按 cron prompt 里一句过期话清空了 Notion（见 §6.3、§14）。**任何「禁止」都必须写进 prompt 本身**，不能指望执行者去翻 AGENTS.md。

---

## 1. 项目是什么

汇总全球灵媒（psychic/medium）、预言家（prophet）、占星师、遥视者、出体体验者、预知研究者、金融术数预测者、AI/科技「模型预测者」的**公开预言**，按人建卡，三层展示：

1. **一句话 summary** + 元信息（说于 / 目标 / 收录日期）
2. **100-300 字 detail**：基于原始出处写的结构化展开（具体标的/事件/数字/时间点 + 依据 + 出处形态）
3. **原始 `source_url`** 可点击追溯

并对**已到期**的预言做应验判定，给每人 1-5 星战绩分。

**定位**：另类预言类作为「民间预期 / 情绪传播度信号」，**不与分析师 KOL 混同判断标准**。玄学/通灵/另类预测者归本项目；纯金融分析师归姊妹项目 Eco-and-Volatility-Checker。

**它不是什么**：不是对预言真伪的独立事实核验。应验判定依据是公开报道与可检验的结局，表述模糊的一律 `unclear`，不强判。

---

## 2. 仓库与发布通道

### 2.1 两个仓库
| 仓库 | 内容 | 注意 |
|---|---|---|
| **个人公网仓库** `Curarpikt0000/Forecast-Checker` | 脱敏后的代码 + SSOT + 看板 | **绝不含**内网标识、密钥、Notion 坐标 |
| **公司内部 monorepo** 的 `Forecast-Checker/` 子目录 | 公网内容的全量镜像 + 公网端被排除的私人脚本/数据 | 由 `publish.sh` 第 4 步 rsync 同步 |

### 2.2 四个发布出口（`scripts/publish.sh` 一条龙，幂等）
| 步 | 出口 | 说明 |
|---|---|---|
| 3 | 个人公网仓库 | 红线扫描 → 显式清单 `git add` → commit → push → **读回 remote HEAD 校验** |
| 4 | 内部 monorepo | rsync（`--delete`，排除 `.git/ .venv/ scratch/ __pycache__/ .env`）→ commit → push |
| 5 | 内网静态托管 | 失败**不阻断**，但响亮报 `…_PUBLISH_FAILED`（内部专用，见内部补充文档） |
| 6 | **Cloudflare Pages** | `forecast-checker.pages.dev`；调用仓库**之外**的通用发布器；自带红线扫描 + 内容指纹幂等 + 部署后匿名 curl 比对 |

**验证线上有没有真更新：curl 线上 URL 比对 md5**，不看脚本自报。
**换发布通道的完成定义**不是「新地址能打开」，而是「下一次自动日更之后新地址也变了」（2026-09-21 实际踩过：CF 站建了但没接进 publish.sh，线上停在旧快照）。

### 2.3 Pages 入口
入口是**根目录 `index.html`**（`dashboard/index.html` 的副本），不是 `dashboard/index.html`。`publish.sh` 负责 `cp`。手动 commit 会漏掉这一步——2026-08-22 踩过。

---

## 3. 目录地图

```
AGENTS.md            项目规则（受保护文件，改动需审批）
HANDOVER.md          本文
README.md
index.html           ★公网入口（≈10MB 单文件，自包含，无外部依赖）
dashboard/index.html 构建产物，与 index.html 同内容
scripts/             见 §5
data/
  backfill_full.json ★SSOT（派生产物！由 merge 从下列源文件重建，禁手改）
  batch_*.json       人物源文件：list，一人一条 dict（见 §4）
  p3_batch_1..10     一年期回补（给已有人物追加预言）
  p4_verdict_*.json  应验判定（人工/子 agent 判，见 §7.4）
  p5_realdate_*.json 回源核实的真实发表日
  new_people_batch*  新增人物批
  details/<id>.json  detail 文本（merge 时按 summary 精确匹配挂载）
  roster_candidates.json  名册候选池
  daily_targets.json 当日采集目标（每天由 export 脚本重新生成）
  batch_daily.json   ★每日增量源文件，约 1.2MB，【仅内部仓库跟踪（publish.sh 强制添加），公网仓库不含】
  notion_ids.json    Notion 坐标，gitignore，只在内部端
  _removed_backup/   删人前的滚动备份，gitignore
docs/                context-log、SESSION_HANDOVER_20260824、github-flagged-recovery
src/                 空（.gitkeep），主逻辑都在 scripts/
scratch/             临时，gitignore，不进 git
```

### 3.1 gitignore 里「有意不进公网」的东西
- Notion 私人脚本：`verify_notion.py create_notion_db.py write_*_to_notion.py build_ssot_kol_list.py fix_ssot_bio_*.py`（含 page id 坐标）
- `data/kol_list_ssot.json`（Notion 镜像）、`data/notion_ids.json`、`data/_removed_backup/`
- `scripts/publish.sh`、`scripts/publish_vibe.sh`（含内部环境标识）、`data/batch_daily.json`
- `.cf_last_sha256_*`、`.wrangler/`（本机状态）

> ⚠ `publish.sh` 本身被公网仓库 gitignore。**接手方从公网仓库 pull 不会得到它**，需要从内部仓库取（§12）。

---

## 4. 数据模型

### 4.1 SSOT `data/backfill_full.json`
顶层：`_total_people / _total_predictions / _topic_domains(9) / _person_types(8) / people[]`

**person 字段**：`id display_name person_type region alive years bio official_url primary_domains predictions[]` + 自动算出的 `hit miss pending judged hit_rate wilson_lb rating rating_pct rating_provisional rating_tooltip total_predictions`

**prediction 字段**：`summary detail date date_precision date_status date_evidence date_note target_date target_year domain source_url quote quote_en quote_source record_type collected_on verified verdict_reason verdict_source`

### 4.2 一条新人物源文件长什么样（照抄，别猜字段）
```json
[{
  "id": "brenda_denzler",
  "display_name": "Brenda Denzler",
  "person_type": "预知研究",
  "region": "美国",
  "alive": true,
  "years": "",
  "official_url": "https://orcid.org/0000-0003-4611-2991",
  "bio": "……背景简介……",
  "predictions": [{
    "summary": "一句话",
    "date": "2025",
    "domain": "科学意识",
    "source_url": "https://…",
    "quote": "中文译文",
    "quote_en": "原话（必须是原文逐字）",
    "collected_on": "2026-09-19",
    "detail": "100-300字，基于 source_url 真实内容",
    "target_date": "2035",
    "verified": "pending"
  }]
}]
```
**参考实现**：`data/batch_denzler.json`、`data/batch_vigilant_citizen.json`。

### 4.3 字段语义（容易搞反）
- **`quote` 是中文译文，`quote_en` 才是原话**。要引用/核对出处读 `quote_en`；无 `quote_en` 的条目 = `quote` 本来就是中文原话。
- **`date` = KOL 实际发表日**，不是抓取日。`collected_on` 才是抓取入库日。分档用 `date`。
- **`target_date/target_year` = 预言指向的目标时间点**，不是发表时间。判断不出就留空，**绝不猜**。
- `date_precision ∈ day/month/year`；发表日查不到的**绝不用 `collected_on` 顶替**，留空标 `date_status=unverified`，前端归「发表日待考」。
- `verified ∈ hit/miss/unclear/pending`；pending = 未到期。

### 4.4 枚举（改动需联动三处）
- 身份类型 8 类、领域 9 类。新增任何一类，必须**同时**：① Notion DB 的 select 加选项 ② `build_dashboard.py` 的 `PTYPE_META`/`DOMAIN_COLOR` 加配色与图标 ③ `merge_backfill.py` 的 `_person_types/_topic_domains` 加枚举。否则新人物不出现在导航且 Notion 写入 400。`check_consistency.py` 会前置拦截。

---

## 5. 脚本清单

### 5.1 流水线（`publish.sh` 内按此顺序）
| 顺序 | 脚本 | 作用 |
|---|---|---|
| 1 | `merge_backfill.py` | 从 `data/*.json` 源文件**重建** SSOT；detail 挂载；**防回退断言**（人数/条数只增不减，`FC_ALLOW_SHRINK=1` 才允许缩） |
| 2 | `apply_p4_verdicts.py` | 把 `p4_verdict_*.json` 回填进 SSOT；内置 summary 精确匹配 + 跨批去重 + 不覆盖已有人工判定 |
| 3 | `apply_p5_realdates.py` | 回填真实发表日；日期必须 ≤ 今天且 ≠ target_year，否则拒绝 |
| 4 | `compute_ratings.py` | Wilson 下界 → 百分位定星（§8） |
| 5 | `build_dashboard.py` | SSOT → 自包含单文件 HTML（约 1475 行，纯标准库） |

### 5.2 守门与校验（阻断性，不是警告）
| 脚本 | 拦什么 |
|---|---|
| `check_consistency.py` | SSOT ↔ Notion ↔ 公网 三方人数与逐人条数一致 + 枚举在 Notion 白名单内。`--no-web` 跳过公网 |
| `verify_p2_details.py` | detail 键错位、长度越界、脱敏污染、detail 复述 summary |
| `verify_p3_backfill.py` | **日期越界（第一优先级）**、domain 白名单、重复、detail 必填 |
| `check_totals.py` | 输出 `<人数> <条数>`（cron 第 5 步用） |

### 5.3 采集与人工操作
| 脚本 | 作用 |
|---|---|
| `export_targets_from_notion.py` | **每日第一步**：从 Notion 取「状态=在世」者 → `data/daily_targets.json`。姓名含 `ANONYMIZED_` 一律拒绝并非零退出 |
| `add_person_to_notion.py` | **唯一允许的 Notion 写入**。`<id>…` 新建；`--update [id…]` 只改属性（条数/最新摘要/更新日） |
| `remove_people.py` | 删人：源 batch + details + SSOT + 镜像 + Notion(标「已移出」不物理删)，先备份，`--dry` 预演 |
| `sync_notion_full.py` | ⛔ **禁用**：先 archive 全库再重写，会抹掉人工评分 |
| `export_active_targets.py` | ⛔ 已废弃：读本地文件，人名有被脱敏占位符污染的风险 |

### 5.4 日常增量的辅助脚本（仓库里有，但个人公网仓库未跟踪，见 §13-3）
`apply_daily_new.py collect_daily_groups.py harvest_delegation.py ingest_daily.py merge_daily_out.py qc_today.py report_day.py aggregate_daily_out.py make_daily_*.py` 等。它们是历史上各轮日更的辅助脚本，**当前 cron 主流程不依赖它们**（cron prompt 只调用 §6.2 里列出的脚本）。

---

## 6. 每日自动化

### 6.1 Cron 一览
| job | 时间(JST) | 类型 | 模型 | 作用 |
|---|---|---|---|---|
| `Forecast-Checker daily increment` | **每天 13:20** | agent，工作目录=项目根；工具集 web/terminal/file/delegation；投递=原话题 | claude-sonnet-5-5 | 采集 → 合并 → 发布 → 对账 → 播报 |
| `forecast-checker-context-distill` | 每天 06:15 | agent + 脚本（`collect_forecast_checker_topic.py`） | claude-sonnet-5-5 | 把当天本项目对话压缩归档到 `docs/context-log.md`（只存本地，不推送） |

> 同工作目录的 cron 共用目录锁；别再给本目录加长任务，排班避开 13:20 前后。

### 6.2 日增 job 的流程（完整 prompt 见附录 A）
1. `python3 scripts/export_targets_from_notion.py` → `daily_targets.json`（当前 88 条）。**非零退出（占位符）→ 立即停止并报告**。
2. `delegate_task` 并行，**每批 ≤3 个子 agent，单个 timeout ≤300s**；子 agent 超时/报错的人记入失败清单，**主 agent 绝不 retry**。每人搜过去约 7 天新预言，对照 `existing_summaries` 去重。
3. 汇总写入 `data/batch_daily.json`（先读旧内容合并，**旧条目 `collected_on` 不改**，只给今天新增的打今天日期）。
4. `bash scripts/publish.sh`（**2026-10-03 起内含两步 Notion 同步**：`add_person_to_notion.py --update` 同步属性，`notion_append_new.py` 把当天新增预言追加进各人页面正文；两步失败都只报错不阻断）
5. `python3 scripts/check_totals.py` + 公网 200 检查
6. `python3 scripts/check_consistency.py`，**全绿才算收工**
7. 播报：**全流程只在「开始」和「结束」各发 1 条**（防 Telegram flood）；结束时按身份类型分组罗列所有新增条目 + 「今日重点」。无新增则一行「今日无新预言」。

**近两周实际运行情况（2026-10-17 至 10-30，读 `~/.hermes/cron/output/` 得出，日增 job 累计运行 80 次、`failure_streak=0`）：**
- 日新增 2–20 条（10-19 +13，10-20 +8，10-21 +6，10-22 +10，10-23 +17，10-24 +3，10-25 +20，10-26 +7，10-27 +8，10-28 +2，10-29 +7，10-30 +14）。
- **第 5 步 `curl` 取状态码在 12/14 次里被安全扫描拦下**，实际由 `check_consistency.py` 的公网项顶替。这是常态，**不是故障**；但这意味着 prompt 第 5 步这句话目前是失效的，接手方可以删掉。
- 5/14 次有子 agent 超时；3/14 次有人姓名被脱敏成占位符而被跳过；2/14 次 92 位在世者只搜到 15–17 位（工具限制）。
- 战报格式：开始 1 条 + 结束 1 条，结束时按身份类型分组罗列所有新增条目。

### 6.3 模型试跑（2026-10-01 起，**2026-10-03 已终止并改回 Sonnet 5.5**）
- 此前 cron 的 `model` 字段为空，实际跟随全局默认 `claude-sonnet-5-5`。
- 2026-10-01 改 `claude-haiku-4-5` 试跑；10-02 的新增（+7 条）看起来正常；**10-03 出事**：cron prompt 第 6 步有一句早已过期的「Notion 不一致就跑 `sync_notion_full.py`」，Haiku 照字面执行，Notion 被清空重写到一半，只剩 57/101 行（缺 44 人，其中 43 人有星级评分）。同一句话 Sonnet 手里没出事——它会去读 AGENTS.md 的禁令。
- **验收第五项（`check_consistency` 一次全绿）一票否决**。教训：试跑期间不能只看新增条数，破坏性副作用（行数、归档数、最后编辑时间）要单独验；cron 的最终播报会把 FAIL 描述成「同步中」，对账只看 `check_consistency` 原始输出。
- 处置：① 改回 Sonnet 5.5 ② prompt 里把那句改成「⛔ 绝不跑 `sync_notion_full.py`」并修掉 github.io 地址 ③ `add_person_to_notion.py` 补回 44 人，评分按 SSOT 星级重写。**被清掉的那 44 行若有人工编辑过的字段无法恢复**，只能确认星级与 SSOT 一致。
- 改回命令（已执行）：`hermes cron edit 683f038fb51c --model claude-sonnet-5-5 --provider custom`；模型切换只能用 CLI，cron 管理工具没有 `model` 参数。**再次尝试便宜模型之前，先确认 prompt 里没有任何「靠执行者自己判断别做某事」的句子。**

### 6.4 cron 环境铁律
- **禁用 `python3 -c` / `bash -c`**（安全 guard 会 BLOCK）；需要 inline 逻辑就写成脚本文件。取日期用 `TZ=Asia/Tokyo date +%F`。
- `execute_code` 被禁，一律 terminal + python3。
- `delegate_task` 的 `tasks` 传干净中文，不带 `\uXXXX` 转义。
- 子 agent 的 `child_timeout_seconds=900` 是全局配置，**超时会吞光全部成果**：任务书必须硬性要求「每完成 N 条立即 write_file 覆盖写同一文件」。

---

## 7. 日常操作手册

### 7.1 验收今天的 cron 有没有跑好
```bash
cd <PROJECT_ROOT>
ls -t ~/.hermes/cron/output/683f038fb51c/ | head -2           # 最新输出
git log -3 --format='%h %ad %s' --date=format:'%m-%d %H:%M'   # 有没有当天提交
python3 scripts/check_consistency.py                           # 必须全绿
```
**状态标签（`unknown / timeout / API calls: 0`）不等于零产出**，必须查库、查提交验证。

### 7.2 新增一个 KOL（顺序严格）
1. **先核身份**：同名不同人极常见。找到官网/ORCID/出版物等能唯一锚定的证据。
2. **读真实原文**：每条预言必须真读过 `source_url`，**detail 绝不允许由 summary 凭空扩写**。
3. **建源文件** `data/batch_<name>.json`（schema 照 §4.2，抄 `batch_denzler.json`）。
4. **挂白名单——`merge_backfill.py` 里有两处，两处都要加**（`_MERGE_APPEND` 元组 与下方 `for fn in [...]` 列表），且**插在 `batch_daily.json` 之前**。
5. **引文校验**：`quote_en` 必须是原文逐字。**用归一化匹配**（去空白/标点再比），防 PDF 首字下沉把 `From` 拆成 `F rom` 造成假阴性。
6. **判定文件** `data/p4_verdict_<name>.json`：**先 `read_file` 抄 `p4_verdict_krishnamurti.json` 的 schema**（嵌套 `{person_id, verdicts:[{summary, verdict, verdict_reason, verdict_source}]}`）。字段名靠猜会静默不生效（2026-09-28 踩过）。
7. 跑流水线五步（§5.1），或直接 `bash scripts/publish.sh`。
8. `python3 scripts/add_person_to_notion.py <id>` 建 Notion 行。
9. `python3 scripts/check_consistency.py` 全绿。

**姓名权威源 = Notion DB 的「姓名」字段**（项目负责人 2026-08-22 指定）。本地人名经多轮 agent 读写，有被脱敏占位符污染的先例。

### 7.3 删除 KOL
```bash
python3 scripts/remove_people.py --dry <id>   # 先预演
python3 scripts/remove_people.py <id>         # 自动备份到 data/_removed_backup/<ts>/
```
只改 SSOT 不行：`merge` 会把人塞回来。Notion 侧只标「已移出」，不物理删（只增不减铁律）。

### 7.4 补应验判定
到期条（`target_date/target_year` 已过）才判。三档 `hit/miss/unclear`，**表述模糊一律 unclear**。子 agent 任务书里给**实测分布锚点**（如「前一批约 unclear 60% / miss 27% / hit 13%，这个比例是健康的」）能抑制「为好看而多判 hit」。**id 与人名一律从输入文件复制，不要手打**（曾把 `maria_shaw` 写成不存在的 id，3 条被静默丢弃）。

**已到期未判定（待办）**：Mhoni 的 9/21 地震预言、Bo Polny 的 9/24 预言。

### 7.5 回查发表日
有效手段：① `<meta property="article:published_time">` / JSON-LD `datePublished` ② 403 页 → Wayback CDX 快照读 meta ③ YouTube 反爬挡住 yt-dlp → innertube `/youtubei/v1/player` 取 `microformat.playerMicroformatRenderer.publishDate` ④ 博客找 HTML 属性（如 `data-unix-time`）或站点 archive 列表。**查不到的留空，不顶替。**

### 7.6 Notion 条数对不上
2026-10-03 起 `publish.sh` 已自动同步属性与页面正文，正常不会再对不上。若仍报：
```bash
python3 scripts/add_person_to_notion.py --update <id> [<id> …]   # 只改属性
python3 scripts/notion_append_new.py                              # 只追加缺失的预言到页面正文（幂等；--dry-run 只算不写）
```
**绝不要**跑 `sync_notion_full.py`（先 archive 全库再重写，会抹掉人工评分——2026-10-03 因此出过事故，见 §6.3）。缺人用 `add_person_to_notion.py <id>` 补建（新建行评分默认写「未评」，要再按 SSOT 把星级 PATCH 回去）。
Notion 页面正文的约定：每人页面 = 全部预言，**最新 12 条在前、更旧的追加在后（不严格倒序）**；想严格倒序就得清空重写，那正是出事的做法，不要做。脚本会报告「陈旧块」（SSOT 里已改写过 summary 的旧条在 Notion 留下的旧标题），**只报告不删除**。

### 7.7 只改看板 UI
只重跑最后一步即可：`python3 scripts/build_dashboard.py`，然后 `bash scripts/publish.sh`。改前备份 `build_dashboard.py`。**任何新增进公网的文件，必须同时加进 `publish.sh` 的红线扫描清单和 `git add` 清单**（两处各写各的列表，只加一处 = 新文件绕过安全门，2026-08-24 实际发生过）。

---

## 8. 星级评分口径（项目负责人 2026-08-24 拍板）

`scripts/compute_ratings.py`：
```
判定池 = 只取「已到期」预言；未到期不计入
→ 每人算 Wilson 95% 置信下界
→ 排序键 = (wilson_lb, -judged 若 hits=0 否则 0)
→ 在 judged>=3 的群体内按百分位定星：
     前10%=5★ / 10-30%=4★ / 30-60%=3★ / 60-85%=2★ / 其余=1★
→ judged 1-2 条：给参考位次但封顶 3★ + 标「暂定」
→ judged = 0 ：按预言总量给 1-2★ 数据量底分 + 标「暂定」
```
**为什么这样设计（改前务必理解）**
1. 用百分位不用绝对切点：没人能客观说「25% 命中率」在预言领域算好算坏，任何硬编码门槛都是拍脑袋。
2. 排序键是二元组：`hits=0` 时 Wilson 下界恒为 0，「0中/8判」与「0中/3判」会并列；判得越多仍全错越能确证不准。
3. 同时吃「应验绝对值」与「百分比」：20 条中 5 条排在 100 条中 5 条之前；1 条中 1 条不给满分。
4. 旧公式 `rating = 命中率×5` 是坏的：「判过 1 条碰巧中」= 5★。

**多数人星级偏低是真实战绩，不是评分故障**——这句话看板上也写了，别「修」它。

---

## 9. 看板结构（`build_dashboard.py`）

**章节锚点**：`sec-top`（总览）/ `sec-latest`（最新言论）/ `sec-cards`（KOL 卡片，按 8 类身份分组）/ `sec-radar`（领域雷达）/ `sec-timeline`（事件时间线）——**页面自上而下就是这个顺序**（2026-10-03 起；此前雷达和时间线在卡片之前）。左侧固定导航 + 滚动高亮，窄屏变悬浮菜单按钮。

**「最新言论」**：按**发表日（月粒度）**分档：本月 / 近 3 月 / 近 1 年 / 发表日待考。
- 为什么是月粒度：`date` 精度只有约 33% 到日、38% 到月、28% 到年，做「当天/一周」是假精确。
- 为什么不按**抓取日**：项目 8/18 才开始采集，所有 `collected_on` 挤在最近 7 天，「过去一周」必然等于「过去一个月」等于全量。这是用错字段，不是计数 bug。
- 4 种排序（说于最新/最早/星级/人名）+ 身份类型与领域两组筛选；共存逻辑是**搬 DOM、不重建节点**。

**人物卡片**：星级金黄色（`#ffc93c`）；顶部有「评分高到低」排序和「4★及以上 / 3★及以上」筛选；展开其余预言后有底部「收起」按钮（`pmClose`）。

**改版记录**
- 2026-09-04：星级改金黄；加排序与筛选。
- **2026-10-01 impeccable 设计审计两轮**：检测器问题 33190 → 68 处。
  - 第一轮（字号/对比度/语义）：所有功能文字 ≥11px；详情正文 13px、限宽 72ch；次要灰提亮到 ≥4.5:1；身份类型色增加「文字用浅一档」（图形仍用原色）；去星级光晕；空心星提亮；分组标题改真 h2，加 `<main>`、键盘焦点样式、`prefers-reduced-motion`。
  - 第二轮（图标/竖条/手机）：emoji 图标全部换成一套内联 SVG sprite（15 个，描边继承文字色）；去掉卡片与预言行的彩色左边框（2874 处）；元数据标签直接写文字（「说于/目标/收录」）；星级说明默认折叠；手机端筛选区单行横滑（右缘渐隐）、导航按钮改左下悬浮、触屏点击区加大。
  - 残留 68 处中 57 处是时间线弹层里的分类圆点，检测器当成文字，属**误报**；另有 1.3 万个 ★☆ 是星级本体，也被计为「emoji」，属**误报**。
  - **2026-10-03 版块重排（已做）**：把「雷达」「时间线」挪到卡片之后，人物卡片第一组从约 2286px 提前到约 1229px；侧栏同步（概览：总览/最新言论；分组浏览：卡片；图表：雷达/时间线）。验证：桌面 + 手机无横向溢出、0 个 JS 报错、星级排序与 4★ 筛选正常。
- **约束**：保持**单文件自包含架构**（项目负责人明确「最好保留现在方式」）。单文件 >500MB 绝不容忍；当前约 10MB。

---

## 10. 数据纪律（铁律，违反过的都有事故记录）

1. **只增不删**。删人走 `remove_people.py`；Notion 只标「已移出」。
2. **绝不编造**。搜不到/查不到就留空标 status——**这是合格行为，不是失败**。曾因子 agent 随意标日期造成 972 条错配。
3. **`quote_en` 必须是原话**；引文核验一律归一化匹配。
4. **detail 必填且必须真读过 source_url**；抓不到实质内容就不输出这条（宁缺毋滥）。
5. **历史/已故人物仅收录 2026 及以后预言**；无新内容者标「历史复核」。
6. **记录者 vs 主体**：采访者发布的受访人主张，summary 加「【受访人主张·经由 X 发布】」前缀。
7. **不自行增删名册**，任何新增须负责人确认。匿名站点（如 Vigilant Citizen）按机构型收录。
8. **转述 KOL 观点不得把两条线并成一句**：曾把 Armstrong 的「实体经济下行」与「内乱恐慌周期」合写成一句被纠正。他的框架是**主权债危机 ≠ 股市危机**。
9. **一次性手工判定必须落成 `data/p4_verdict_*.json`**，不要只改 SSOT（会被 merge 覆盖）。
10. 红线关键词（个人公网端禁止出现）：见 `publish.sh` 第 2 步的正则。密钥一律只写变量名。

---

## 11. 环境与凭证

**只列变量名，绝不写值，绝不进 git。**

| 位置 | 变量/依赖 | 用途 |
|---|---|---|
| 项目根 `.env` | `NOTION_TOKEN`、`NOTION_VERSION` | 所有 Notion 脚本；**Notion 脚本禁止硬编码 page id**，一律从 gitignore 的 `data/notion_ids.json` 读 |
| 发布器环境 | `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID` | Cloudflare Pages 部署（发布器在仓库**之外**，见 §12-4） |
| 脚本可选 | `FC_ALLOW_SHRINK=1` | 允许 merge 缩减记录数（有意删人时） |
| git 凭证 | 个人端走 `gh` OAuth；内部端走证书会话 | 开 2FA 不影响 push |

**Python**：纯标准库即可跑全部流水线（`json/urllib/re/datetime/glob/pathlib/…`）。venv 里仅有 `yt-dlp`（采集用）。Python 3.11。**不借用其他项目的 venv。**

**本机浏览器自动化不可用**（浏览器 daemon 起不来）：采集一律 `web_extract`/`curl`/`yt-dlp`。需要渲染实测时，系统自带 headless Chromium + Playwright 可用。

---

## 12. 接手步骤（从零开始）

**完整逐步清单在仓库根的 [`SETUP.md`](SETUP.md)，本节只写要点。**

1. `git pull`，然后 `bash scripts/handover_selfcheck.sh`（只读，一条命令查：环境、仓库完整性、内部仓库独有文件、凭证变量名、仓库外依赖、数据自洽、公网一致性、本机 cron 现状；每个 ✗ 都带「为什么」和「怎么修」）。
2. 补齐公网 pull 拿不到的文件（`data/batch_daily.json`、`scripts/publish.sh`、`scripts/publish_vibe.sh`、`scripts/notion_append_new.py`）：从内部仓库 `Forecast-Checker/` 取。**缺 `batch_daily.json` 时 `merge_backfill.py` 报「预言数减少」退出码 2、不覆盖 SSOT——是安全失败；绝不要设 `FC_ALLOW_SHRINK=1` 硬 merge。**
3. 仓库外脚本：`ops/hermes-scripts/`（`publish_cf_pages.sh`、`collect_forecast_checker_topic.py`，已脱敏，拷到 `~/.hermes/scripts/`）；另需 `public_push_gate.sh`（公网 GitHub 每两周推一次的闸，从原机器拷）。
4. Cloudflare 两个变量放环境变量或 `~/.hermes/.env`（**发布器不读项目 `.env`**）。
5. 建 cron：`bash ops/create_cron.sh`（默认演练；`APPLY=1` 才真建；本机已有同名 job 则拒绝）。**模型钉 `claude-sonnet-5-5`。**
6. 先手动 `bash scripts/publish.sh` 跑一次，`check_consistency` 全绿、Cloudflare md5 与本地一致后，才**逐个暂停**原机器的 cron（不要按名字前缀批量暂停）。
7. **两边不能同时跑**：重复抓取 + 双倍烧额度。

**交接包清单**：`SETUP.md`（逐步手册）｜`HANDOVER.md`（本文）｜`ops/cron-jobs.json`（2 个 cron 的真实 prompt/模型/排班）｜`ops/create_cron.sh`｜`ops/hermes-scripts/`｜`self-skill/forecast-checker-pipeline/`（驱动技能副本，拷到 `~/.hermes/skills/devops/` 即被自动加载）｜`scripts/handover_selfcheck.sh`。

---

## 13. 已知问题与待办

### 需要决策 / 高优先
1. ~~`data/batch_daily.json` 未被任何仓库跟踪~~ **已解决（2026-10-03）**：`publish.sh` 对内部仓库 `git add -f` 跟踪它，已从内部仓库远端读回核对（1261984 字节，与本地一致）。公网仓库仍不含（本就不该）。
2. **GitHub 个人账号 flagged**：匿名访问 `github.com/Curarpikt0000/*` 全部 404，名下 8 个仓库同样。所有者登录正常、push 正常、计费正常。2026-09-19 已向 GitHub 申诉，等待回复；`docs/github-flagged-recovery.md` 有操作清单与英文文案。**申诉期间不改推送策略，cron 继续每天推。** 公网入口已改走 Cloudflare。
3. **个人公网仓库缺脚本**：cron prompt 调用 `scripts/check_totals.py`，该文件**未被公网仓库跟踪**（内部仓库有）。**仍未处理。**
4. ~~cron prompt 两处过期~~ **已解决（2026-10-03）**：第 5 步地址改 `https://forecast-checker.pages.dev/`；第 6 步改为「⛔ 绝不跑 `sync_notion_full.py`」。同日 `publish.sh` 内含 Notion 属性与正文同步，不再靠手动补。**注意**：这两处就是 §6.3 事故的根因，现已堵住。

### 本轮（2026-10-31）交接时发现、未处理的
- **cron prompt 第 5 步的 `curl` 在 cron 环境里 12/14 次被安全扫描拦下**，该步实际失效，靠 `check_consistency` 公网项顶替。改 prompt 属生产流程改动，**待负责人批准**。
- **92 位在世者每天只搜到约 15–20 位。2026-10-31 查到一个高度可疑的原因：子 agent 看到的姓名被显示层脱敏成占位符，于是按 prompt 里「姓名含 ANONYMIZED_ 就跳过」的规则把真人当成占位符跳过。**
  证据（只有一半）：当天 cron 自报「最后一批约 40 人里 20 人因显示名被脱敏成占位符被跳过」；而 `data/daily_targets.json` **磁盘上 `ANONYMIZED_` 出现 0 次**、92 人全是真名。即磁盘干净、占位符只出现在子 agent 读到的内容里（脱敏是显示层，不是文件里的字节）。
  **没有直接看到子 agent 实际收到的内容，所以只是高度可疑，不是定论。** 当天 cron 自己也把「今日无新预言」标注为「采集覆盖偏薄，没有新预言不等于确实没有」。
  影响：「每天无新预言」或「新增偏少」的结论不可全信。建议接手后先在一次手动跑里让子 agent 把它实际收到的名单原样回报出来核对；改 cron prompt 属生产流程改动，**待负责人批准**。
- **项目根目录曾有 15 个 2026-10-03 子 agent 遗留散文件**（报告与中间 JSON），已移到 `scratch/old-root-files/`（不删，gitignore）。`data/` 下另有 3 个 `batch_daily.json.bak-*` 手工备份未清。
- **工作区仍有 4 个非本轮改动的未提交文件**（`.gitignore`、`data/fill_raw/*.json`、`data/roster_candidates.json`、`docs/context-log.md`），不是看板改动，没碰。

### 数据质量
5. **每天约 20/88 人没搜到**：YouTube 频道页读不出、Facebook 基本不可读、按名字搜常命中同名无关的人、搜索后端多次超时。David Icke / Craig Hamilton-Parker / Rudy Baldwin 这类主要在这些平台日更的人最容易漏。
6. **疑似已故仍标在世**：Larry Dossey（讣告 2026-08-25）在 Notion 仍标「在世」；另有一位疑似 2026-07-22 去世。需核实后改状态。
7. **4 人 SSOT 的 `alive` 为 `None`**（`james_gilliland jeff_rense michael_salla rosicrucian_order_amorc`）：另有 6 人（Hevenly/Puthoff/Geller/Turchin/Tegmark/Yudkowsky）已于 2026-10-03 补齐——`merge_backfill.py` 现在同 id 已存在时会补 `alive`，roster 没 bio 时退回 `bio_long` 首句。剩下这 4 人未处理，卡片状态徽章不准。
8. 3 条发表日查不到的条目留空；17 条无正文源的 detail（YouTube Shorts / 付费墙）等新源。
9. 502+ 条未到期预言到期后需滚动判定（cron 可按 `target_date` 挑）。

### 内容待决（负责人未答）
- ~~Armstrong 中期选举条目拆写~~ 已做：9/23《The Midterm Disaster》拆成 3 条（中期选举 / 2028 前经济下滑 / 2032 政体瓦解），原话均核对为原文逐字子串。~~9/8《European Revolution 2026》5 条~~ 核实库里早已入库。
- Armstrong 在 Notion 页面里有 1 个「陈旧块」（拆写前的旧标题），脚本只报告不删，是否手动清除待定。
- Vigilant Citizen 的 `person_type`（现暂用「预言先知」，3 条全判 unclear——原文取消了时间约束，且是反问句，不替它补方向）。
- 卡片左侧竖条与 emoji 已按推荐方案改完；版块顺序已重排（§9）。

### 文档/规则
- `AGENTS.md` 里有过时说明（仍写 GitHub Pages 为公网入口、「99 人」等）；它是**受保护文件**，改动需审批，攒批一次提交。
- 公网 git 历史里仍有早期的 Notion DB ID（清除需 `git filter-repo` + force push，不可逆，**未授权**；风险评估：光有 DB ID 没有 token 访问不了，非密钥级）。

---

## 14. 事故与教训索引（每条都是真实发生过的）

| 日期 | 事故 | 根因 / 修法 |
|---|---|---|
| 08-21 | 11 人/84 条次日消失 | 只写进派生产物、未挂白名单，merge 重建时覆盖 → 加**防回退断言** |
| 08-22 | SSOT 98 / Notion 87 / 公网 87 三处脱节 | 新枚举不在 Notion select 白名单，静默漏同步 → `check_consistency.py` |
| 08-22 | detail 里第三方人名变 `ANONYMIZED_` 占位符 | agent 读写链的脱敏污染 → 人名权威源改 Notion + 导出脚本拒绝占位符 |
| 08-23 | 每日新增缺 detail 层 | cron prompt 的输出 schema 漏了 `detail` 字段 → 已补 |
| 08-24 | publish 把 116 条判定冲回 14 条 | `publish.sh` 只有 merge→build，漏了 p4/p5/ratings → 五步写进脚本 |
| 08-24 | 玄学类人物的每日新增被覆盖丢失（两天各十余条） | `batch_esoteric_finance.json` 排在 `batch_daily` 之后且不在白名单 → 新 batch 一律插在 daily 之前 |
| 08-24 | 新增脚本绕过红线扫描 | git add 清单与扫描清单各写一份 → 两处必须同步 |
| 08-24 | `verify_notion.py` 硬编码父页 id 且被公网追踪 | 改读配置 + `git rm --cached` |
| 08-24 | 子 agent 超时吞掉全部成果 | 任务书必须要求增量落盘 |
| 09-19 | 公网 404，误判「仓库 private」 | 实为账号被 flagged；排除过代理/证书/Uber 内网拦截（对照 6 个其他账号全 200） |
| 09-21 | CF 站建好了但没接进 publish.sh，线上停在旧快照 | 换通道的完成定义 = 下一次日更之后新地址也变 |
| 09-21 | 发布脚本在内部仓库也被忽略（rsync 同步了公网 `.gitignore`） | 内部端对这类文件要 `git add -f` |
| 09-28 | 判定文件字段名靠猜，静默不生效 | 照现有文件抄 schema |
| 10-01 | 模型字段为空，「cron 用什么模型」说不清 | 钉死到 job 上 |
| **10-03** | **换 Haiku 试跑当天清空 Notion（57/101 行，缺 44 人）** | cron prompt 里一句过期的「跑 `sync_notion_full.py`」被照字面执行；Sonnet 会读 AGENTS.md 禁令所以没出事 → 禁令必须写进 prompt 本身；改回 Sonnet、prompt 改成「绝不跑」、`add_person_to_notion.py` 补回 44 行 |

---

## 附录 A：每日增量 cron 的 prompt 全文（路径已占位符化）

> 创建 cron 时用下面这段。`<PROJECT_ROOT>` 换成你的项目绝对路径。
> 本附录是 **2026-10-03 修订后**的 prompt：第 5 步地址已改 Cloudflare，第 6 步已明令禁止 `sync_notion_full.py`（§13-4）。

````text
你是 Forecast-Checker 项目的【每日增量抓取执行器】。工作目录 <PROJECT_ROOT>。这是一个灵媒/预言家/出体者/预知者/模型预测者的预言看板项目,历史 backfill 已完成。你的任务:每天只抓【在世活跃预言家】的【新预言】,追加去重,重算并双发布。绝不编造,每条锚真实 source_url。

## 步骤

1. 先跑 `python3 scripts/export_targets_from_notion.py` 生成 data/daily_targets.json。**人名权威源 = Notion DB 的「姓名」字段**(Chao 2026-08-22 指定),只收「状态=在世」者,含 id/display_name/person_type/official_url/existing_summaries。用 read_file 读它。
   - 该脚本若因姓名含 ANONYMIZED_ 占位符而非零退出,**立即停止当日采集并报告**——绝不用被脱敏的人名去搜索,须先在 Notion 把该人姓名改回真名。
   - 旧脚本 export_active_targets.py 读本地文件,已废弃不再使用(本地人名有被 redactor 污染的风险)。

2. 用 delegate_task 并行(每批最多3个子agent,每个agent处理若干人)搜集这些人【过去约7天】的新公开预言。

**⚠️ delegate_task 硬约束（防 Telegram flood,2026-09-08 加）**:
- 每个子 agent 单次 timeout 上限 300 秒(不是默认的 420)
- 子 agent 若 timeout 或返回 error,该批次的这些人直接记入失败清单跳过,**主 agent 绝不 retry**
- 每批 delegate_task 完成后主 agent **不发消息**,继续下一批
- 全流程仅在【开始】和【结束】各发 1 条消息(见播报规则)

给每个子agent的指令:
   - 用 web 搜每人最近新说法(官网/YouTube/媒体报道)
   - 主题领域只能从九类选:金融经济/地缘军事/自然灾害/科技AI未来/社会政治/健康疫情/灵性个人/科学意识/金融市场
   - 对照该人的 existing_summaries 去重,只收真正的新预言(不是已有的)
   - 真实可追溯,绝不编造。找不到新的就返回空
   - 每条输出 JSON: {"id":"...","display_name":"...","predictions":[{"summary":"一句话","detail":"100-300字结构化详情","date":"预言发表的年月如2026-08","target_date":"这条预言指向的目标时间点,如2027或2026-11,判断不出就留空","domain":"...","source_url":"http..."}]}
   - ⭐**`detail` 字段必填(Chao 2026-08-23 硬要求:看板必须是三层结构)**:100-300字,基于 source_url 页面真实内容写的结构化展开,不是把 summary 换句话说。要交代清楚:他到底说了什么(具体标的/事件/数字/时间点)、依据是什么、上下文出处形态(视频/文章/讲座)。反面例子:summary 写"关系会改变"而 detail 只写"他认为关系将改变"——读者仍然不知道改变了什么,这种直接判为不合格。
   - **detail 绝不允许由 summary 凭空扩写**。必须真的读了 source_url 的内容。如果页面打不开或没有实质信息,就**不要输出这条预言**(宁缺毋滥),或输出时把 detail 留空字符串,由前端优雅降级——绝不编造细节充数。
   - **target_date 很重要**:是「他预测的事情将发生在什么时候」,不是发表时间。正文里说"2028年大选""未来9到12个月"就据此填年份;完全判断不出就留空字段,绝不猜测编造。
   - 严格只输出 JSON 数组

3. 汇总所有子agent返回的新预言。把有新预言的人写进 data/batch_daily.json(list格式,一人一条,只含 id/display_name/predictions,只放新增的)。用 write_file。
   - **每条新预言必须加 `"collected_on": "<今天日期YYYY-MM-DD>"`**(东京时区,用 `date +%F` 取)。这是「找到该数据源的时间」,dashboard 的「最新收录言论」板块靠它分档,漏了这条就不会出现在当天板块里。
   - 注意:如果 batch_daily.json 已存在,要先 read_file 读出旧内容,合并(同id的predictions累加去重)再写回,不要覆盖丢失历史增量。**旧条目已有的 collected_on 不要改动**,只给今天新增的条目打今天的日期。

4. 跑 `bash scripts/publish.sh` — 它会 merge(自动去重+算命中评分+补collected_on/target_year+动态日期) → build dashboard → IP红线扫描 → 个人端push公网 → 内部端rsync+push。看它输出确认成功。

5. 验证:`python3 scripts/check_totals.py` 确认预言总数(输出格式: `<total_people> <total_predictions>`)。curl -s -o /dev/null -w "%{http_code}" https://forecast-checker.pages.dev/ 确认公网 200。

6. **一致性守门(必跑,不可跳过)**:`python3 scripts/check_consistency.py`。它比对 GitHub SSOT / Notion DB / 公网 dashboard 三处的人数与逐人预言条数,并校验 person_type 与 domain 是否都在 Notion select 白名单内。
   - 全绿才算今天收工。
   - 若报 `person_type/domain 不在白名单`:说明有新类别进来,必须**先**在 Notion DB 加 select 选项、在 scripts/build_dashboard.py 的 PTYPE_META/DOMAIN_COLOR 加配色、在 scripts/merge_backfill.py 的 _person_types/_topic_domains 加枚举,然后重跑 merge+build,否则新人物不会出现在导航栏且 Notion 写入会 400。
   - 若报 Notion 行数/条数不一致:⛔ **绝不跑 `sync_notion_full.py`**(它先清空全库再重写,会抹掉人工评分;2026-10-03 曾因此把 Notion 清到只剩 57 行)。缺人就跑 `python3 scripts/add_person_to_notion.py <缺失的person_id ...>` 补建(只增不删);条数对不上就跑 `python3 scripts/add_person_to_notion.py --update <person_id ...>` 只改属性。新建行评分默认「未评」属正常,不要手改。然后重跑本断言。
   - 若只有公网一项 FAIL 且刚 push 不久,等 1-2 分钟重试(GitHub Pages 有延迟)。

## ⚠️ 播报总原则（硬约束,防 Telegram flood,2026-09-08 加）

**全流程只在【开始】+【结束】各发 1 条**,绝对不发:
- delegate_task 每批完成
- Step 1/3/4/5/6 的执行状态
- 中间进度报告
- 爬取过程流水账

具体:
- **【开始】** (Step 1 结束后): 发 1 行 `Forecast-Checker 开始今日增量抓取,共 N 位在世预言家...`
- **【结束】** (Step 6 全绿后): 按下方原规则播报
- **【硬失败】** (Step 1/4/5/6 fail): 发 1 行 `Forecast-Checker Step X 失败: <一句话原因>`,不发 traceback

## 播报规则(Chao 讨厌流水账,但要求新增内容够详细)
**无新增**:只回一行「Forecast-Checker 今日无新预言,平稳。总计仍 N人/M预言」。

**有新增**:先一句话总述「今日新增 N 条预言,涉及 X 位预言家」,然后**按身份类型分类罗列所有新增条目**(不是只挑2条)。身份类型八类:🔮灵媒通灵 / ✨占星预言 / 📜预言先知 / 👁遥视RV / 🌌出体OBE / 🧪预知研究 / 📊模型预测者 / ☯金融玄学·术数预测。

每个类型下,每条新增按这个格式(一条一行,信息密度高但不啰嗦):
`**人名**（地区）— 预言内容一句话 · 🎯目标 <target_date或"未明"> · 🗣说于 <date> · [源](url)`

分类罗列之后,再加一段「**今日重点**」,用 2-3 句点出最值得注意的(重大地缘/金融拐点/时间点临近/多人指向同一事件的共振),说清为什么值得注意。

最后附总计和公网链接。

排版要求:用 Telegram markdown,类型标题加粗,条目用 `-` 起头。整体控制在合理长度,新增少时自然短,新增多时按类型分组不会显得杂乱。

## 铁律
- **禁用 `python3 -c "..."` 和 `bash -c "..."`(cron 环境有 hermes 安全 guard,任何 shell-level -c/-e 会被 BLOCKED)**。任何需要 inline eval 的地方写成脚本文件(见 scripts/check_totals.py 模式),或用 `terminal(command="<原始命令>", ...)` 直接给命令(terminal 工具已在 workdir 里 shell,不需要 bash -c 包装)。**同理不要用 `python3 -c` 取时区日期,直接 `TZ=Asia/Tokyo date +%F`**。
- execute_code 被禁,一律用 terminal + python3。
- 绝不编造预言和时间点,取不到就是没有/留空。
- collected_on 必须是真实的今天日期,不许回填假的历史日期。
- 个人端绝不含内网标识/密钥(publish.sh 有红线扫描守卫)。
- delegate_task 的 tasks 传干净中文文本对象,不要带 \uXXXX 转义。
````
