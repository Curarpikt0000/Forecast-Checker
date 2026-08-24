# 数据字典 — Forecast Checker

本目录存放名册与 backfill 内容。每个数据文件在此登记：来源 / 抓取方式 / 口径 / 拉取日。

| 文件 | 内容 | 来源 | 抓取方式 | 口径 | 拉取日 |
|------|------|------|----------|------|--------|
| (待填) | 灵媒/预言家名册 | Eco kol_registry.json 筛选 + web 补充 | — | 非金融预言家/灵媒/出体者 | — |
| (待填) | 每人过去一年内容 | web_search / web_extract | 锚 source_url | 过去 12 个月公开表态 | — |

## 纪律
- 只增不减，绝不编造，取不到标 status。
- 每条内容锚 source_url，可追溯。
- 原始数据进内部 GitHub，个人 repo 只放脱敏后可公开内容。

---

## ⚠️ 字段语义变更 · 2026-08-22 · `quote` 现在是中文译文

**Chao 拍板方案 B**：`predictions[].quote` 的显示层要全中文。

| 字段 | 变更前 | 变更后 |
|------|--------|--------|
| `quote` | 原话（多为英文） | **中文译文** |
| `quote_en` | 不存在 | **原话原文**（新增，证据链锚点） |

### 接手 agent 必读

- **要引用原话、做证据核对、比对 source_url 页面内容 → 一律读 `quote_en`**，
  不要读 `quote`。`quote` 已是机器译文，逐字引用会与源页面对不上。
- `quote_en` 只在被翻译过的条目上存在（当前 106 条）。**没有 `quote_en` 的条目，
  说明 `quote` 本来就是中文原话**，它自己就是原文。
- 翻译由 LLM 完成（本机 :8800 代理 gpt-4o），规则：人名/机构名/货币单位/专有名词
  保留原文，忠实翻译不增不减，译文必须含中文才写入，失败保留原样绝不手写编造。

### 覆盖情况（2026-08-22）

- `backfill_full.json`：113 条 quote，**全部中文，0 遗漏**，其中 106 条带 `quote_en`。
- 源语言不止英文：另含西班牙语（Mhoni Vidente / Jimena La Torre）、
  印尼语（Denny Darko）、俄语（Pavel Globa）。

### 相关脚本

| 脚本 | 作用 |
|------|------|
| `scripts/translate_quotes.py` | 主翻译器，扫 16 个 batch 源文件里的非中文 quote |
| `scripts/translate_quotes_multilang.py` | 补漏，处理主脚本因"非英文"判定而返空的条目 |

**★ 必须改源文件，不能改 `backfill_full.json`** —— 它是 `merge_backfill.py` 的派生产物，
文件头写明"直接编辑本文件会在下次运行时被静默覆盖"。
正确顺序：改 16 个 batch 源 → `merge_backfill.py` → `build_dashboard.py`。

---

## ⚠️ merge_backfill.py 的 batch 遍历**顺序有语义** · 2026-08-24 事故

`merge_backfill.py` 里那个 batch 文件名列表不是随便排的：

- 列表里只有 `_MERGE_APPEND = (batch_daily, batch_longrange, batch_fill)` 三个文件
  是**追加合并**（同 id 时把 predictions 去重后 append）。
- **其余 batch 文件遇到同 id 会整体覆盖**掉已合并的那条人物记录，连同其 predictions。

**踩过的坑**：`batch_esoteric_finance.json`（玄学/术数 11 人）被排在 `batch_daily.json`
**之后**，于是每天增量抓到的玄学类新预言（wolfincanada / bopolny / raymondamerriman /
qiurun / andrewpancholi）在 merge 时被这个全量文件整体覆盖，**静默丢失**。
08-23 与 08-24 两天各丢十余条，`batch_daily.json` 里明明有数据，
`backfill_full.json` 里却没有——不报错、不告警，只有逐人对比才看得出来。

**规矩**：新增任何**全量** batch 文件，一律插在 `batch_daily.json` **之前**；
`batch_daily.json` 永远排最后。
自检办法：`batch_daily.json` 里某人今天的条数，必须等于 `backfill_full.json`
里该人 `collected_on == 今天` 的条数。


### 派生备份不进 git

`*.qbak` / `*.ml.bak` / `*.retry.bak` 是翻译脚本的滚动备份（每个 ~1.8MB），
已在 `.gitignore` 排除。

---

## ⚠️ 展示口径 · 2026-08-23 · 三层模式与 `detail` 字段

**Chao 明确要求：全项目所有卡片统一三层。**

| 层 | 内容 | 对应字段 |
|----|------|----------|
| 第一层 | 一句话简介（折叠时可见） | `predictions[].summary` |
| 第二层 | **100–300 字带结构的内容简介**（点开后） | `predictions[].detail`（+ `quote` / `quote_en` 原话引用） |
| 第三层 | 原始出处链接（再点下去） | `predictions[].source_url` |

他举的反例：只写「关系会改变」，读者根本不知道到底改变了什么 —— **中间层缺失即视为未完成**。

### `detail` 覆盖情况（2026-08-23 实测）

- 587 条预测中 **508 条有 `detail`**（中位 299 字，仅 1 条 <100 字），**79 条缺失**，集中在 26 人。
- `source_url` **587/587 全覆盖**。
- 缺 `detail` 的条目在页面上渲染为降级提示「暂无二次核实的详情摘要」，**不留空白、不臆造内容**。
- 源文件里目前带 `detail` 键的只有 `batch_fill.json` 与 `new_people_batch*.json` 五个；
  早期 `batch_1~6 / batch_daily / batch_esoteric_finance / batch_extra* / batch_longrange` 均无 —— 补 detail 时改的就是这些源文件。

### 近一年覆盖缺口（2026-08-23 实测）

- 在世者近一年 <3 条的有 **34 人**，其中 **10 人 0 条**。
- 总条数为 0 的 4 人：`joseph_mcmoneagle`、`xiaoxiayijing`、`ezmoney`、`jinghongnews`。
  **Chao 已裁定这 4 人保持 0 条**（「大概率就是零，没关系，就这样」），不再为凑数逐视频抓取。

### 渲染入口有两个，改一处不等于改全站

同一批预测在 `scripts/build_dashboard.py` 里有两个渲染函数：
`card()`（人物卡片区，三层早就齐全）与 `_latest_row()`（「最新收录言论」板块）。
后者原本是一行 `<div>` + 点标题直接外链，**中间层等于不存在**，2026-08-23 改为 `<details>` 补齐。
以后收到「某处显示不对」的反馈，**先 grep 出这份数据的全部渲染入口再动手**。

### 新增人员走 `add_person_to_notion.py`，不要跑 `sync_notion_full.py`

| 脚本 | 行为 | 何时用 |
|------|------|--------|
| `scripts/add_person_to_notion.py` | 查重 + **增量 only-add**，已存在则跳过不覆盖 | **加人一律走这个** |
| `scripts/sync_notion_full.py` | 先 archive 全部行再重写（破坏性重建） | 仅在明确诊断出逐行不一致时作修复用 |

全量重建会抹掉人工在 Notion 侧编辑过的评分字段，且违反「只增不删」铁律。

### 记录者 vs 受访人：`【受访人主张·经由 X 发布】` 前缀

收录「采访者 / 记录者」型人物（本项目首例：`rick_keefe`，见 `new_people_batch5.json`）时，
Chao 拍板走**方案 A**：卡片记记录者本人，受访人的主张照收，
但**在 `summary` 与 `detail` 里都加 `【受访人主张·经由 X 发布】` 前缀**，不计作他本人判断。
不加这个前缀直接 backfill，会把别人的话记到他名下，污染所有按人聚合的统计。

日期一律只取**一手元数据**（`yt-dlp --dump-json` 的 `upload_date`、站点 WordPress REST 的 post date），
**禁用搜索结果摘要里的日期与标题**（实测 SERP 会把别的频道标题串到本人名下）。
