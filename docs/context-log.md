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

---

## 2026-08-25

### 事实与配置
- **中文化能扛住每日 cron 重跑，已实证**。Chao 8/23 晚追问「这两个改了没有 / 是不是同步的」，
  当场复核：当天 10:01 的每日增量 `bfb6de1` 重跑过一遍 publish 全链路，
  线上 113 条引语仍是**全中文、0 条英文**，公网 md5 与本地 `index.html` 一致。
  原因是翻译写在**源 batch 文件**里，不是写在派生产物 `backfill_full.json` 上——
  cron 每天 merge/build 都从源文件重建，所以译文是持久的。
  （反过来说：任何只改派生产物的修补都会在次日 cron 后静默消失。）
- **本轮归档时实测 SSOT**（`data/backfill_full.json`）：99 人 / 764 条预言，
  其中带 `quote` 的 **117 条、全部含中文、0 遗漏**，带 `quote_en` 原文的 **110 条**。
- 交接文档 `docs/SESSION_HANDOVER_20260824.md` 已建（commit `994700c`，08-24 20:21），
  同一 commit 把 `docs/context-log.md` 纳入 git 追踪，并把 `AGENTS.md` 精简为纯规则。
- 工作区当前无未提交改动（`git status --porcelain` 为空）。

### 待办
- `AGENTS.md` 第 69 行与 `data/README.md` 第 30/37 行仍写「113 条 quote / 106 条 quote_en」，
  实际已增至 **117 / 110**（08-24 每日增量带来的自然增长）。数字口径待同步更新。

---

## 2026-08-26

### 决策
- **名册唯一真源改为 Notion「SSOT KOL List」**（Chao 指令）。代码永远只读这张表，
  加人删人只改 Notion；本地 `data/kol_list_ssot.json` 是 `--pull` 生成的**单向镜像**。
- **切断跨项目依赖**：本项目不再读取任何其他项目 / 其他 agent 的数据。
  早期「种子名单取自 Eco 项目 `kol_registry.json`」的说法**作废**（种子早已落地本项目自有数据）；
  `scripts/import_esoteric_from_eco.py` 定性为 2026-08-22 一次性迁移脚本，
  不在 publish.sh 流水线内，**保留仅作溯源、禁止再运行**。
- **`kol_list_ssot.json` 与三个 Notion 脚本只留内部端**：该镜像顶层 `_notion_db` 是私人工作区
  database id，已加 `.gitignore`；`build_ssot_kol_list.py` / `fix_ssot_bio_alive.py` /
  `fix_ssot_bio_round2.py` 同理。`data/_removed_backup/`（删人滚动备份）也只留内部端。
- Chao 回「可以发布」→ 执行发布。

### 事实与配置
- **4 人移出名册**：`elon_musk` / `ilya_sutskever` / `masayoshi_son` / `sam_altman`
  （`person_type=模型预测者`）。Notion 侧**行保留、状态置「已移出」**，不是物理删除——
  镜像 `count=99 / active_count=95`（`synced_at` 2026-08-26 16:01 JST）。
  本地派生产物按 active 重建：SSOT 由 99 人降为 **95 人**，其 `data/details/*.json` 一并删除。
- **发布已完成**：commit `2a30768`（08-26 19:15），SSOT 实测 **95 人 / 786 条预言**。
  线上 md5 与本地 `index.html` 一致；被移出 4 人在线上 HTML 0 命中。
- **星级分布**（本次重算）：5★ 4 人 / 4★ 3 人 / 3★ 18 人 / 2★ 24 人 / 1★ 44 人 / 未定级 2 人；
  `rating_provisional=true` 共 **78 人**（judged<3），有效战绩仅 17 人。

### 进展（发布前拦下的三个真缺陷）
1. **`git add data/details/*.json` 是 shell glob，匹配不到「已删除」的文件** →
   本地删干净、发布也「成功」，但公网仓库里那些 detail 仍在线可访问，**全程零报错**。
   改为 `git add -A data/details/`，本次实际提交了 5 个删除（含 2 个带 `p2_` 前缀的变体，
   变体命名容易漏，别只盯主文件名）。
2. **镜像类数据文件差点带内部标识进公网**（见上「决策」第三条）。
3. **新脚本绕过安全门**：`remove_people.py` 不在 publish.sh 的红线扫描清单，也不在 git add 清单。
   两处都补上——这是 AGENTS.md 第 7 条同一个坑第二次犯。

### 一次误报（核实后放行）
- 红线扫描在 `index.html` 里扫出 2 个 UUID 格式串。`git show HEAD:index.html` 证明
  **线上早就有这两个**，上下文是第三方播客平台的公开 URL 路径段 → **误报，放行**，未据此声称污染。
  同批另一处「764」是 URL 里的数字而非人数统计，同样靠看上下文才没误改。

### 待办
- `AGENTS.md` 第 23 行那条过时依赖说明（「种子名单来自 Eco 项目 `kol_registry.json`」）仍未删——
  它是 protected 文件，两次触发审批弹窗均超时被拒。需 Chao 在场时同轮触发。

---

## 2026-08-27

### 事实与配置
- **归档时实测 SSOT**（`data/backfill_full.json`）：95 人 / **786 条预言**；
  带 `quote` 的 **107 条**、带 `quote_en` 的 **117 条**。
- **`data/details/` 已删干净**：git HEAD 追踪列表与本地目录逐文件 diff 为空。
- **工作区有 3 处未提交改动**：`.gitignore`（新增 ignore 项）、`data/README.md`
  （新增「名册 SSOT」与「跨项目依赖已切断」两节）、`docs/context-log.md`（本文件）。

### 待办
- ★ **翻译管道对每日增量无覆盖，已实证**：17 条预言**只有 `quote_en` 原文、`quote` 为空**，
  全部是 `collected_on=2026-08-26` 的当日新增。原因是 `scripts/translate_quotes.py`
  **不在 publish.sh 流水线里**（流水线只有 merge → p4 → p5 → ratings → build），
  属一次性提质脚本，每日 cron 抓进来的新条目不会被翻译。
  受影响 id：`amanda_grace` / `nir_ben_artzi_israel`（4 条）/ `harry_dent` / `uri_geller` /
  `raymondamerriman`（2 条）/ `rudy_baldwin_philippines` / `betsey_lewis` / `harold_puthoff` /
  `primate_ayodele` / `bopolny` / `stephan_schwartz`（2 条）/ `andrewpancholi`。
  修法方向：把翻译作为一步挂进流水线（只处理 `quote` 为空且有 `quote_en` 的增量条目），
  否则「显示层全中文」会随每日增量持续退化。
- **文档数字口径全线过时**，需一次性对齐到 95 人 / 786 条 / quote 107 / quote_en 117：
  `AGENTS.md` 第 69 行（写「113 条 quote / 106 条 quote_en」）、
  `data/README.md` 未提交版本里仍写「99 人 / 764 条预言」。

---

## 2026-08-28

> 本节归档的对话实际发生在 2026-08-27 22:1x JST（归档任务于 08-28 06:16 运行）。

### 决策
- **Chao 指示新增名册人物**：Predictive History（江学勤 / jiangxueqin），
  频道 `https://www.youtube.com/@PredictiveHistory`，他明确说「他的 comment 大多数可以从这里找到」，
  即以该频道为主要内容锚源。
- **只认 Chao 给的那个频道**：搜索中另有 `@PredictiveHistory-official`、
  `@predictivehistoryanalysis`、`Predictive History TV` 等二传/搬运频道，一律不采信。
- **尚未动名册**：EXPLORE 完成后停在待批状态，`data/` 未写入任何该人物记录，
  抓取产物只落 `/tmp/ph`（videos/streams/shorts jsonl + all.json）。

### 事实与配置
- 频道身份：`UC11aHtNnc5bEPLI4jf6mnYg`，约 280 万订阅，本人官方频道。
- **三 tab 全枚举实测**：`/videos` 177 + `/shorts` 0 + `/streams` 12 = **189 个视频，去重后仍 189**。
  shorts 的 0 是硬事实——yt-dlp 报 `This channel does not have a shorts tab`，不是抓取失败。
- **内容形态与名册现有人物差异极大**：全部为 41~316 分钟长篇讲座
  （Dante 系列 12 集、Game Theory 系列 29 集、地缘政治 Meet-Up、Emergency Discussion），
  **没有短视频，没有一句话式预测**，预测埋在数小时讲座里。
- **字幕现状**：官方字幕为空 `[]`，**只有自动字幕**（机器转录）。
  → 按本项目字段语义，机器转录句子严格说不等于原话，直接充当 `quote_en` 有风险。
- `--flat-playlist` **不返回上传日**，189 条元数据全无时间戳，按「近一年」筛选需另取日期。
- 人物背景：江学勤，1976 年生，中国出生的加拿大籍教育者/评论者，有英文维基条目；
  频道命题源自阿西莫夫《基地》的「心理史学」（psycho-history）。
- 抓取工具：本次借用 Eco 项目 venv 里已装的 yt-dlp 二进制（**未读写 Eco 任何数据**），
  按血缘纪律拟给本项目装独立 yt-dlp。
- 本项目 08-27 有两次每日增量提交：`cd0e2a2`（10:07）、`912bdbb`（10:15）。

### 待办
- **等 Chao 拍板两件事，未定不开工**：
  1. `person_type` 归类——最贴近的是「模型预测者」（Armstrong / Turchin 一档），
     但他自我定位偏思辨（「探索心理史学是否可能」）。
  2. `predictions[]` 抽取方案 —— A：只抽近一年、带明确时间点且可判定的断言（已推荐）；
     B：189 个视频全量通抽（量极大，Dante 系列产不出可判定预测）；
     C：先只建人物卡、`predictions: []` 留空。
- 若走 A，需明确这批 `quote_en` 标注来源为自动字幕、在 detail 里写明，不冒充精确引用。
- 上一节列的两项待办仍未动：翻译管道未挂进 publish.sh 流水线（17 条 `quote` 为空）、
  文档数字口径未对齐到 95 人 / 786 条。

---

## 2026-08-30

> 本节归档的对话实际发生在 2026-08-29 JST（归档任务于 08-30 06:15 运行）。

### 决策
- **Chao 明确要求：整体 crawl 每天都跑，不能只在工作日跑。**（原话「整体的那个你的 crawl
  应该是每天都 run，而不是只有工作日」）—— 属对调度口径的直接纠正。
- Chao 以「继续」授权**补跑当日缺失的 Forecast-Checker 每日增量**（09:25 那次因链路中断失败）。

### 事实与配置
- **08-29 增量已补齐并落地**（非 cron 自述，逐项查过真实产物）：
  - git 提交 `2091601 Daily increment: refresh predictions and dashboard 2026-08-29`。
  - 当日新增 **21 条预言 / 涉及 15 人**（`collected_on=2026-08-29` 实测计数）。
  - 新增最多者按真实 id：`martin_armstrong` 5 条、`amanda_grace` 2 条、`sundeep_kochar` 2 条。
    ⚠️ 聊天层显示的人名被 redactor 脱敏替换过（曾显示成无关真人姓名），**以 id 为准**。
  - 现状总量：**95 人 / 868 条预言**。
  - 公网 https://curarpikt0000.github.io/Forecast-Checker/ 返回 200；
    一致性守门全绿（SSOT / Notion / 公网三处人数条数一致，`data/` 下无 `ANONYMIZED_` 残留）。
- ★ **修正上一节的待办判断：翻译缺口没有随每日增量扩大。**
  实测 `quote` 为空而有 `quote_en` 的仍是 **17 条，且全部 `collected_on=2026-08-26`**，
  08-27 / 08-28 / 08-29 三天增量**一条都没新增缺口**。
  原因是每日增量条目的字段集为
  `collected_on / date / detail / domain / source_url / summary / target_date / target_year / verified`
  ——**根本不产出 `quote` / `quote_en`**（21 条里带 quote 的 0 条、带 quote_en 的 0 条、带 detail 的 21 条）。
  所以缺口是 08-26 那一批的历史遗留，不是持续退化中的管道漏洞。
  全库当前：`quote` 107 条、`quote_en` 117 条。
- 工作区仍有 3 处未提交改动：`.gitignore`、`data/README.md`、`docs/context-log.md`（本文件）。

### 待办
- 仍未动：**Predictive History（江学勤 / jiangxueqin）尚未进名册** —— `data/` 下
  grep `jiangxueqin` / `PredictiveHistory` 命中 0，`backfill_full.json` 中该人 0 条记录。
  待 Chao 拍板 `person_type` 归类与 `predictions[]` 抽取方案（A/B/C）后才开工。
- 仍未动：**17 条只有 `quote_en`、`quote` 为空**（全部 08-26 那批）需补中文译文。
  受影响 id：`amanda_grace` / `andrewpancholi` / `betsey_lewis` / `bopolny` / `harold_puthoff` /
  `harry_dent` / `nir_ben_artzi_israel` / `primate_ayodele` / `raymondamerriman` /
  `rudy_baldwin_philippines` / `stephan_schwartz` / `uri_geller`。
- 仍未动：**文档数字口径过时** —— `AGENTS.md` 第 69 行仍写「113 条 quote / 106 条 quote_en」、
  `data/README.md` 仍写「99 人 / 764 条预言」，实际为 **95 人 / 868 条 / quote 107 / quote_en 117**。
