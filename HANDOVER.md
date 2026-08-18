# Forecast Checker — Handover 文档

> 灵媒 / 预言家 / 出体者 / 预知未来者 内容汇总 dashboard。
> 本文档说明**数据更新逻辑**与**Dashboard 构建/展示逻辑**，供任何 agent/人接手维护。
> 最后更新：2026-08-18

---

## 1. 项目定位

汇总所有灵媒（psychic/medium）、预言家（prophet/seer）、出体体验者（OBE）、
遥视者（remote viewer）、预知研究者的**过去一年公开预言**，双维度分组可视化：
- **身份类型**（6 类）：灵媒通灵 / 占星预言 / 预言先知 / 遥视RV / 出体OBE / 预知研究
- **预言主题领域**（8 类）：金融经济 / 地缘军事 / 自然灾害 / 科技AI未来 / 社会政治 / 健康疫情 / 灵性个人 / 科学意识

当前规模：**54 人 / 199 条预言**。每条锚 `source_url` 可追溯，绝不编造。

---

## 2. 数据架构（SSOT + 更新逻辑）

### 2.1 文件结构
```
data/
├── roster_candidates.json   # 名册候选池(54人): id/display_name/category/region/bio/search_terms
├── sample_backfill.json     # 首批 6 人 sample(历史遗留,merge 会并入)
├── batch_1.json ~ batch_6.json  # 分批 backfill 的原始产物(每个是 list,一人一条)
├── backfill_full.json       # ★合并后的 SSOT(merge_backfill.py 生成),dashboard/Notion 都读它
├── notion_ids.json          # Notion DB 坐标(database_id/父页id) — 仅内部repo,不进公网
└── README.md                # 数据字典
```

### 2.2 单条人物记录 schema（backfill_full.json → people[]）
```json
{
  "id": "brandon_biggs",
  "display_name": "Brandon Biggs",
  "person_type": "预言先知",          // 6 类身份之一(决定分组)
  "region": "美国",
  "alive": true,                      // false=已故
  "years": "1911-1996",              // 仅已故者有
  "bio": "另类预警/异梦异象者",         // 卡片下方 background 简介
  "official_url": "https://...",
  "primary_domains": ["社会政治", ...], // 该人主要预言领域(多选)
  "predictions": [
    {
      "summary": "预言内容一句话",
      "date": "2024-03-15",          // 支持 2026 / 2026-03 / 2025-2030 / 约2100 等
      "domain": "社会政治",           // 8 类主题之一
      "source_url": "https://...",   // 真实可追溯
      "verified": "hit"              // hit/miss/pending(merge 自动打标)
    }
  ],
  "hit": 1, "miss": 1,              // merge 自动统计
  "hit_rate": 0.5,                  // = hit/(hit+miss),无可验证样本则 null
  "rating": 2,                      // = round(hit_rate*5),0~5星,null=待验证
  "note": "..."                    // 无预言者(历史复核类)的说明
}
```

### 2.3 数据更新流程（如何加人 / 加预言 / 重算）

**加新预言家或补预言：**
1. 编辑对应的 `data/batch_N.json`（或新建 `batch_7.json` 并在 merge 脚本的文件列表里加上）。
   - 一人一条 dict，字段见上 schema（至少 id/display_name/predictions）。
   - person_type/region/bio 可省略——merge 会从 `roster_candidates.json` 按 id 自动补。
2. 跑 `python3 scripts/merge_backfill.py`
   → 重新合并所有 batch + sample，归一化字段，**自动打 verified 标 + 算 rating**，
     写出 `data/backfill_full.json`（日期自动取当天东京时间）。
3. 跑 `python3 scripts/build_dashboard.py` → 重建 `dashboard/index.html`。
4. （可选）跑 `python3 scripts/write_full_to_notion.py` → 清空并重写 Notion DB。

**命中判定逻辑（merge_backfill.py 自动）：**
- summary 含「应验/确实/获证实/命中/成真」→ `verified=hit`
- summary 含「未发生/落空/未应验/均未/没有发生」→ `verified=miss`
- 其余（绝大多数 2026 未来预言）→ `verified=pending`（不计入评分）
- ⚠️ 命中依据是**公开报道/预言者自称**，非独立事实核验，仅供参考。

**评分口径（Chao 定）：** rating = 命中率 = hit/(hit+miss) × 5 星。
- 5 星 = 100% 命中；0 星 = 0% 命中；只有 pending（无已验证）→ rating=null 显示「待验证」。
- 当前只有 6 人有可验证记录，48 人「待验证」（预言多为未来事件）。

**⚠️ 已知 gap：** backfill 时按「2025-2026 窗口」抓取，导致部分预言家 **2024 或更早的著名命中被漏收**
（如 Brandon Biggs 的特朗普遇刺预言最初漏掉，后补回）。未来若要更公平的命中率，
需针对每个预言家补历史著名命中/落空案例。

---

## 3. Dashboard 构建 / 展示逻辑

### 3.1 构建脚本 `scripts/build_dashboard.py`
读 `data/backfill_full.json` → 生成**自包含单文件** `dashboard/index.html`（无外部依赖，可离线打开）。

**页面结构（从上到下）：**
1. **标题 + KPI 卡**：收录人物 / 追溯预言 / 有预言者 / 身份类型 / 覆盖领域
2. **顶部区（两栏）**：
   - 🎯 预言主题领域**雷达图**（SVG,8 领域,单次循环预计算几何）
   - 📊 各领域预言条数**条形图**
3. **🕰️ 预言事件时间线**（横向滚动）：所有有明确年月的预言按 年-月 桶分组排列，
   紫色高亮 2026+，每个事件点带领域色圆点 + 人名 + 可点击摘要。
4. **身份类型分组卡片区**：按 6 类身份分组，组内按预言数降序。
   每张卡片：图标 + 姓名 + **★评分**(名字后) + 地区/年份 + 状态徽章 +
   身份类型·预言条数 + **bio 背景简介** + 领域标签 + **预言列表**(按时间倒序,最新在上,
   命中✓/未中✗ 标记 + 日期 + 可点击源链接)。
5. **footer**：数据口径 + 评分说明 + 名册来源。

**关键函数：**
- `parse_date(d)` — 把多样日期字符串解析成 `(year, month)` 排序键（卡片倒序 + 时间线都用它）。
- `safe_url(u)` — 只放行 http/https，拦 `javascript:`/`data:` 等（防 XSS）。
- `radar_svg()` — 生成雷达 SVG。
- `card(s)` — 单人物卡片；预言按 `parse_date` **倒序**（最新说的在最上）。
- `timeline_html()` — 顶部时间线。

**健壮性：** 数据文件缺失/损坏/空 → 明确报错退出（不静默出错）；
person_type 不在预设 6 类也会兜底显示（不静默丢人）。

### 3.2 展示三处口径（都写在 footer,诚实标注）
- 每条预言锚真实 source_url，绝不编造。
- 历史/已故人物仅收 2026+ 预言，无则标「历史复核」。
- 评分基于公开报道/自称，非独立核验。

---

## 4. 发布（双版本 + 双 GitHub）

### 4.1 双版本
- **web 版（公网）**：GitHub Pages → https://curarpikt0000.github.io/Forecast-Checker/
  （入口是**根目录** `index.html`,是 `dashboard/index.html` 的副本）。
- **HTML 版**：`dashboard/index.html` 自包含单文件,可离线/内部分发。

### 4.2 双 GitHub 同步
- **公网端**：本仓库,推**脱敏后**内容,绝不含私有 URL/标识/密钥。
  Notion 脚本 + notion_ids.json 被 .gitignore 排除。
- **私有端**：另有一份私有仓库副本(含 Notion 脚本与私有坐标)。
- push 后从 remote 读回验证。

### 4.3 一键更新（发布新数据）
```bash
cd Forecast-Checker
python3 scripts/merge_backfill.py      # 1. 重算 SSOT
python3 scripts/build_dashboard.py     # 2. 重建 HTML
cp dashboard/index.html index.html     # 3. 更新 Pages 入口
# 4. 公网端: git add(排除notion脚本) + commit + push
# 5. 私有端: 同步副本 + push
# 6. (可选) python3 scripts/write_full_to_notion.py 刷新 Notion DB
```

---

## 5. Notion DB
- inline DB 在私有 Notion 工作区,`database_id` 见 `data/notion_ids.json`（仅私有repo,公网已排除）。
- 字段：姓名/身份类型/主要预言领域/地区/状态/预言条数/最新预言摘要/来源官网/评分/更新日。
- 写入脚本 `scripts/write_full_to_notion.py`：清空现有行 → 写全量。
  token 复用 Eco 项目 `.env` 的 `NOTION_TOKEN`,Notion-Version 2022-06-28,读 .env 时用变量名拼接绕 redactor。

---

## 6. 脚本清单
| 脚本 | 作用 | 何时跑 |
|------|------|--------|
| `merge_backfill.py` | 合并 batch+sample→SSOT,打 verified 标,算评分,动态日期 | 数据变动后 |
| `build_dashboard.py` | SSOT → 自包含 HTML dashboard | merge 之后 |
| `write_full_to_notion.py` | 清空+全量写 Notion DB | 需刷新 Notion 时 |
| `create_notion_db.py` | 首次建 Notion DB（一次性,已跑过） | 重建 DB 时 |
| `verify_notion.py` | 验证 Notion token/父页可访问 | 排障时 |
| `build_sample_dashboard.py` | 早期 6 人 sample dashboard（历史遗留） | 已弃用 |

---

## 7. 未来维护建议
- **增量更新**：不必每天全量重跑 54 人。可只针对**在世活跃预言家**（约 23 人）定期补新预言，
  已故/研究者（历史复核类）只在有 2026+ 新预言传播时才更新。
- 若要建自动化 cron：新增 batch → merge → build → 双 push，可参照 Eco/AI-News 的 cron 模式。
- 补历史著名命中（见 §2.3 gap）可提升评分公平性。
