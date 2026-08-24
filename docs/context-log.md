# Forecast-Checker 上下文日志

## 2026-08-23

### 进展
- 每日增量抓取跑通：80 名在世目标分 9 组并行采集，新增 33 条预言 / 16 人（`collected_on=2026-08-23`）。总计 98 人 / 583 条。
- publish.sh 一条龙成功；公网 200；`check_consistency.py` 首轮 Notion 条数 13 人不一致 → `sync_notion_full.py` 全量重同步后全绿。

### 踩坑（可复用）
- **`delegate_task` 工具调用本身有 420s 硬超时**：子 agent 仍在后台跑完，但结果**不会回流**到父 agent（父侧只拿到 timeout 报错）。
  - 现象：`action='list'` 能看到 running；完成后 `live/deleg_*/task-N.log` 里有 `final | status=completed summary: ...`，但 summary 在日志里被截断成 `…(+100 chars)`，**无法从日志恢复完整结果**。
  - 解法：**给子 agent 硬性时间预算（5 分钟）+ 防循环约束（同一 query 只试 1 次，每人 ≤3 次工具调用）+ 要求 write_file 把结果落盘到约定路径**。落盘后即使父侧超时，结果也能捞回来。本次前两批 6 个子 agent 因此丢结果，只能从日志片段人工重建 3 组。
  - 另一失败模式：子 agent 触发 `loop_web_search_cap`（50 次非进展重复搜索）被 guardrail 掐断，返回一句解释而非 JSON。
- 子 agent 上下文里 `display_name` 会被 redactor 显示脱敏成 `ANONYMIZED_PERSON_N`（磁盘干净）→ 指令里明确「搜索用 id 下划线转空格推人名，忽略 ANONYMIZED 的 display_name」，且父侧合并时 display_name 一律取 `daily_targets.json` 的真值，不取子 agent 回传值。

## 2026-08-23（晚间续）

### 决策
- **Rick Keefe 归属裁定：不进 Eco，归 Forecast-Checker**。Chao 起初问「rick keefe 是不是在 kol」，核实 Notion KOL List（125 行，SSOT）+ 本地 registry 均零命中；他补充「是一个吹哨人，曝光过蜥蜴人」后确认此人是 UFO 领域，按项目边界路由到本项目。
- **入库方案选 A（Chao 单字回复「A」）**：卡片记 Rick Keefe 本人＝「记录者/枢纽节点」，backfill 收其频道内容；**受访人的主张在 summary 与 detail 里都加 `【受访人主张·经由 Rick Keefe 发布】` 前缀**，不计作他本人判断。被否：B（只收他本人言论，条目会是个位数）、C（不加他、改加受访人 Alex Collier 等）。
- **三层展示模式（Chao 明确需求，全项目统一）**：① 一句话简介 → ② 点开后 100–300 字**带结构**的内容简介 → ③ 再点下去是原始 source link。他举的反例：只写「关系会改变」，读者不知道到底改变了什么。
- **范围收敛（Chao 亲自划定）**：「最新收录」章节现有的一句话简介 + 说于/目标/收录三个时间点**都很好，只需建中间层**，不要改动已有元素。
- **4 个总条数为 0 的人保持 0**（Chao：「大概率就是零，没关系，就这样」）——不再为凑数逐视频抓取。

### 事实与配置
- 名册现状（Rick Keefe 入库后）：**99 人 / 587 条预测**，`source_url` 587/587 全覆盖。
- **detail 缺口实测**：79 条无 detail，集中在 26 人（最多一人 12 条）；508 条有 detail，中位 299 字；仅 1 条 <100 字。
- **近一年覆盖不足**：在世者近一年 <3 条的有 **34 人**，其中 **10 人 0 条**；总条数为 0 的 4 人 = `joseph_mcmoneagle` / `xiaoxiayijing` / `ezmoney` / `jinghongnews`。
- Rick Keefe 身份一手核实：美国亚利桑那图森，视频记者/纪录片导演，UFO Hypotheses 与 Under-Appreciated Science Productions 创办人；**1994 年 Alex Collier 访谈的采访者**（Alpha Draconis 爬虫人＋猎户座集团＋Zeta Reticuli 灰人叙事的原始传播源）。放 Tucson 演唱会录像的 `@rickkeefe` 是其本人小号，主频道 `@ufohypotheses`。
- 其 4 条内容日期全部取自**一手元数据**（`yt-dlp --dump-json` + WordPress public-api REST），非 SERP 摘要；4 条 source_url 全部 HTTP 200。
- 新脚本 **`scripts/add_person_to_notion.py`**：查重 + 增量 only-add，已存在则跳过不覆盖。原 `sync_notion_full.py` 会先 archive 全部行再重写，属破坏性重建，会抹掉人工编辑过的评分字段并违反「只增不删」——加人一律走新脚本。
- `data/new_people_batch5.json` 为 Rick Keefe 的新 batch 源文件，已挂进 `merge_backfill.py` 的 `_NEW_PEOPLE_FILES` 白名单。
- `daily_targets.json` 81 人（新增 `rick_keefe`），次日起自动进每日采集。
- **P1 前端改动**：`_latest_row()` 由 `<div>` 改为 `<details>`。本地产物实测：1193 个条目全部 `details` 结构、旧 `class="nl-row"` div 残留 0、有真实中间层 1014 条、降级提示 179 条、第三层出处链接 1193/1193 全覆盖。
- **CSS 折叠冲突用离线选择器模拟验证**（当日浏览器 harness 报 `inspect.signature` AttributeError 不可用）：`details.nl-row.pred-x` 的 classList 无 `pred` token，`.pred{display:flex}` 不会误伤。同时清掉了残留的旧 `.nl-row` div 规则（会造成双层 padding）。

### 进展
- Rick Keefe 全链路落地：`backfill_full.json` + Notion 99 行（人名双向一致、逐人条数一致）+ `dashboard/index.html` 99 卡片 + `daily_targets` 81 人。`check_consistency.py` 除「公网仍 98/583」一项外全绿。
- P1（最新收录中间层）已完成并本地验收。
- **尚未 push**：公网线上仍是 `bfb6de1`（08-23 10:01），实测线上 0 处 Rick Keefe。工作区未提交：`dashboard/index.html`、`index.html`、`data/backfill_full.json`、`data/daily_targets.json`、`data/new_people_batch5.json`、`scripts/build_dashboard.py`、`scripts/merge_backfill.py`、`scripts/add_person_to_notion.py`。

### 待办
- **P2**：补 79 条缺失 detail（26 人），回原文抓取写 100–300 字结构化摘要，抓不到标 status 不编造。Chao 尚未就「是否先做 1 人样板验收」给出批复。
- **P3**：34 人近一年 backfill（目标在世者近一年 ≥3 条、每条自带 detail），新数据走新 batch 文件挂 `_NEW_PEOPLE_FILES`。
- push 授权：Rick Keefe 入库 + P1 中间层均待 Chao 说「push」后走 `scripts/publish.sh`。
- Chao 截图高亮的那条（伊朗/俄罗斯/中国与特朗普格局转变）正是 79 条无 detail 之一——**它是数据缺口不是前端缺口**，P2 补完才会有真内容。

## 2026-08-22

### 决策
- **引语中文化选方案 B（Chao 亲自拍板，单字回复「B」）**：`predictions[].quote` 直接改写成中文译文，英文/外文原话另存 `quote_en` 字段备查。被否的方案 A 是「保留 quote 原话 + 新增 quote_cn」。
- Chao 事后质问「为什么会动 Forecast-Checker 这个项目里面的内容」，溯源确认该改动确由他本人授权（选 B 在前，脚本 `translate_quotes.py` 首次进 git 是 `cda7135`，在授权之后）。回滚路径已备：`quote_en` 写回 `quote` → merge_backfill → build_dashboard → publish。
- 两个项目跑完后 **push 已获明确授权**（"是的，是的，两个项目跑完后都要 push"）。

### 事实与配置
- **翻译收敛结果**：113 条 `quote` 全部中文，0 遗漏；其中 106 条带 `quote_en` 原文。无 `quote_en` 的条目 = 原文本来就是中文。
- **源语言不止英文**：实际含英语、西班牙语（Mhoni Vidente）、印尼语、俄语。主脚本 `translate_quotes.py` 的 system prompt 写死「把**英文**引语译成中文」，对非英文输入静默返回空串 → 由 `translate_quotes_multilang.py` 补漏收干净。
- **"失败"分两类**：A 类 429 限流（有错误行）；B 类模型静默返空（无异常、无错误码，只有 `{"cn": ""}`）。把 `REQ_GAP` 从 1.5s 提到 3.0s 只解决 A 类；B 类根因是 prompt 里「无法翻译就返空」的兜底被过度触发。诊断法：先打印一条失败样本的 raw response。
- **名册现状**：98 人 / 556 条预测（`data/backfill_full.json` 元数据自报与实际统计一致）。`check_consistency.py` 全绿（SSOT ↔ Notion ↔ 公网三方一致）。
- **玄学/术数类 11 人已从 Eco 迁入本项目**（commit `65951f6`，87 → 98 人），统一 `person_type = 金融玄学/术数预测`：丙午易说天下、六爻佔卦之狼眼看世界、小夏易經視角、天遁财局、易經交易攻守道、秋潤金融玄學/秋润易道、吳昌燁·太一研究院、JingHongNews 景宏资讯、Bo Polny、Raymond A. Merriman、Andrew Pancholi。Eco 侧对应人员已移出名册并留痕。
- Plai Navaracha（泰国灵媒预言家）已在本项目名册内。
- 备份文件 `*.qbak` / `*.ml.bak` / `*.retry.bak`（几十个约 1.8MB）已加入 `.gitignore`，不进 git。
- **发布链路**：Pages 入口是**根目录 `index.html`**，不是 `dashboard/index.html`；`scripts/publish.sh` 负责 `cp` + 红线扫描 + 双端 push + remote 读回。手动 commit 会漏掉 `cp`（本次实际踩过：本地重建了但公网没变）。
- **线上验证只认 curl 比对 md5**。首次读回曾显示大量英文残留，90 秒后 md5 与本地一致 —— 是 GitHub Pages CDN 缓存，差点误判发布失败。
- 受保护文件（`AGENTS.md`）写入曾连续两次被审批弹窗超时拒绝（`Silence is not consent`）。Chao 在 VM 独立 shell 将审批 timeout 调到 600 秒后一次通过。期间未绕道写入。

### 进展
- 翻译 → `merge_backfill.py` → `build_dashboard.py` 全链路重跑完成。
- 已发布双端：个人端 `1a1dd5c`（公网 Pages），内网 monorepo 同步（走 publish.sh）。线上实测 113 条引语全中文、合规扫描 0 命中。
- 文档补齐并推送：`AGENTS.md` 新增「字段语义」+「发布纪律」两节；`data/README.md` 新增「字段语义变更」整节。个人端 `26f9701`，内网 `04e31419`，公网 raw 读回已确认落地。

### 待办
- Eco 移出的 14 人中，`peter_eliades`（周期派分析师）尚未迁入本项目名册，归属待定；`sarah_bond`、`fema` 明显非预言者类，判定不迁。
- 名册纪律「只增不减」：迁入者的历史预测 backfill 尚未补全（当前 11 人多数条目来自 Eco 迁移，未做本项目口径的一年回填）。

### 用户纠正（必记）
- **「你动了别的项目的内容，通知那个项目文件夹了么」** —— 改动落在哪个项目，文档就必须写在**那个项目自己的 AGENTS.md / data README** 里。只写 ChaoWiki 不够：ChaoWiki 是给「知道去查的人」看的，AGENTS.md 才是下一个 agent 打开项目必然读到的东西。尤其**改字段语义**这种静默陷阱，不写在项目内等于埋雷。
- 派生产物纪律：只改 16 个 batch 源文件，**绝不改 `data/backfill_full.json`**（它是 merge 的派生物，会被静默覆盖）。

---

## 2026-08-24 · 每日增量抓取 cron

### 结果
- 名册 81 位在世预言者全扫（9 组 × 9 人并行）。**今日新增 55 条 / 24 人**。
- SSOT：99 人 / **648 条**（前一日 98 人 / 583 条）。新入册 1 人：`rick_keefe`（由 Notion 导出带入）。
- 双端已发布，公网 md5 与本地 `index.html` **一致**（MATCH）。`check_consistency.py` **全绿**。

### ★ 发现并修复：`merge_backfill.py` 遍历顺序导致每日增量被静默覆盖
- 现象：`batch_daily.json` 里今日有 55 条，首次 merge 后 `backfill_full.json` 只落了 **40** 条，缺 15 条；
  且所有校验（防回退、三方一致性）**全部通过**，不报错不告警。
- 根因：脚本只对 `_MERGE_APPEND = (batch_daily, batch_longrange, batch_fill)` 三个文件做追加合并，
  **其余 batch 遇到同 id 一律整体覆盖**。而 `batch_esoteric_finance.json`（玄学/术数 11 人全量）
  被排在 `batch_daily.json` **之后**，把这批人的当日新增全覆盖掉了。
- 影响面：wolfincanada / bopolny / raymondamerriman / qiurunfinancialmetaphysics / andrewpancholi。
  **08-23 也丢了**（该日 31 条 → 修复后 37 条），即事故已连续两天。
- 修复：调整遍历顺序，`batch_daily.json` 排到最后，并在代码里加警示注释。
  重跑 merge 后 648 条，今日 55 条与源文件完全对齐。
- 文档：`data/README.md` 新增「merge_backfill.py 的 batch 遍历顺序有语义」整节。

### 教训（已写进 ChaoWiki）
- **一致性断言全绿 ≠ 数据正确**。SSOT / Notion / 公网三处读的是同一份派生产物，
  上游静默丢失时三处会一致地错。必须再加一条**「源 → 派生」对账**：
  `batch_daily.json` 里某人今日条数 == `backfill_full.json` 里该人 `collected_on==今日` 条数。
- **父侧 `delegate_task` 420s 超时是每次调用的**：本轮 3 轮派发 **3/3 全超时、零结果回流**，
  但因强制落盘 `scratch/out_gN.json`，实际数据损失 0。超时后不要立刻重派——
  先 `action='list'` 看是否还 running 再 `ls`（本轮 g4/g5 是超时后又跑了 4 分钟才写出文件）。
- **`loop_web_search_cap` 是零产出头号原因**，日志显示 `status=completed` 而非 failed，
  极易误判成「这组真没新内容」。判据：completed 但约定文件不存在 = 撞 guardrail，必须重派。
  任务描述必须写死「每人最多 3-4 次调用，禁止对同一人反复换词搜索」。

### 流程备忘
- 人名权威源 = `export_targets_from_notion.py` 的导出（本地 daily_targets.json 磁盘上无 ANONYMIZED_ 污染，
  已布尔探测确认）；父侧合并时 `display_name` 一律取该导出的真值，不采信子 agent 回传。
- Notion 条数不一致时跑 `add_person_to_notion.py --update`（增量 PATCH 属性）。
  ⚠️ **2026-08-24 更正**：此处原写「跑 `sync_notion_full.py` 全量重同步即自愈」——**已作废**。
  该脚本会先 archive 全部行再重建，会抹掉人工编辑过的评分字段，违反「只增不删」铁律。
