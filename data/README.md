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

### 派生备份不进 git

`*.qbak` / `*.ml.bak` / `*.retry.bak` 是翻译脚本的滚动备份（每个 ~1.8MB），
已在 `.gitignore` 排除。
