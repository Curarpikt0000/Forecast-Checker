# Forecast Checker

> Telegram topic: 与 Eco and Volatility Checker 平行的项目
> 目录名 kebab-case：`Forecast-Checker`

## 全局规则
> 本项目遵守 workspace 全局规则：~/uberhermes/Generalrule/antigravity/general-global-rule.md
> 通用规范与踩坑教训：~/Projects/ChaoWiki/
> 五阶段 workflow：EXPLORE → PLAN → EXECUTE → VERIFY → LEARN

## 项目定位
**灵媒 / 预言家 / 出体者 / 预知未来者 内容汇总 dashboard**。
汇总所有灵媒（psychic/medium）、预言家（prophet/seer）、出体体验者（astral projection / OBE）、
以及声称能预见未来的人（remote viewer / precognition）过去一年发表的预测内容，
以卡片 / 雷达图 / 时间线等形式可视化呈现。

参照 **Eco and Volatility Checker 的 KOL 部分** 作为呈现范式：
- 每人一张卡片（含 domain / sector 分类、观点演变时间线 year_timeline、锚 source_url）
- 分组 / 雷达 / 时间轴等多维展现
- 只增不删的名册纪律，每条内容锚可追溯出处

## 人选来源
1. **种子名单**：从 Chao 的 KOL list（Eco 项目 `data/kol_registry.json`，SSOT=Notion KOL List DB）
   筛出所有 **非金融领域的预言家 / 灵媒 / 另类预测者**
   （domain=预测 / sector=Alternative，如 Craig Hamilton-Parker 英国通灵预言家、
   Baba Vanga 传承、David Icke 等通灵/占星/末日预言者）。
2. **网上补充**：web 搜集更多灵媒 / 预言家 / remote viewer / 预知者，扩充名册。
3. **定稿后 backfill**：每人过去一年发表内容，每条锚 source_url。

## 名册纪律（沿用 Eco KOL 铁律）
- **只增不减**，SSOT = 名册文件 + Notion（如启用）。
- 另类预言类不按可交易/严格方向归类，作 **民间预期 / 情绪传播度信号**，不与分析师 KOL 混同判断标准。
- **绝不编造**：内容取不到标 status，不臆造预测/日期/出处。
- 每条预测锚 `source_url`，可追溯。

## 双 GitHub 同步（两端）
- **个人端**：`Curarpikt0000/Forecast-Checker`（公网，任何人免登录访问）——
  推**脱敏后**内容，**绝不含任何内网 URL / 内部标识 / 内部数据**。
- **内部端**：公司内部 monorepo 的 `Forecast-Checker/` 子目录（IP 允许，含真实数据）。
- **同步纪律**：改完同步到内部 monorepo 子目录再 commit；
  push 走内部凭证；commit message 禁括号；`-c commit.gpgsign=false`；push 后从 remote 读回验证。
- 内部 monorepo 下 `git add` 用完整相对路径带 `Forecast-Checker/` 前缀，禁 `git add .`。

## 发布（双版本）
- **web 版**：GitHub Pages 公网（https://curarpikt0000.github.io/Forecast-Checker/）。
- **HTML 版**：自包含单文件 HTML dashboard（可离线/内部分发）。
- 发公网前必剥离所有内网 URL；纯公开内容本身可放。

## 目录结构
```
AGENTS.md          # 本文件：项目定位 + 全局规则引用 + 双端同步说明
README.md
.gitignore         # 排除 .venv/ .env / data 缓存 / __pycache__ / scratch/
src/               # 主逻辑（fetch / build / dashboard）
data/              # 名册 + backfill 内容 + data/README 数据字典
scripts/           # 运行脚本
dashboard/         # dashboard 产物
docs/              # context-log 等
scratch/           # 临时（gitignore 排除，不进 git）
```

## 数据字典
- `data/README.md`：每个数据文件标来源 / 抓取方式 / 口径 / 拉取日。

## ⚠️ 字段语义：`quote` 是中文译文，`quote_en` 才是原话（2026-08-22，Chao 拍板方案 B）
- 显示层要求全中文 → `predictions[].quote` 已被翻译成中文。
- **要引用原话 / 核对 source_url 页面 → 读 `quote_en`**，不要读 `quote`（机器译文，逐字引用会与源页面对不上）。
- 无 `quote_en` 的条目 = `quote` 本来就是中文原话。
- 当前：113 条 quote 全中文、0 遗漏，106 条带 `quote_en`。源语言含英/西/印尼/俄语。
- 脚本：`scripts/translate_quotes.py`（主）+ `scripts/translate_quotes_multilang.py`（补漏非英文）。
- ★ **只改 16 个 batch 源文件，绝不改 `backfill_full.json`**（它是 merge 的派生产物，会被静默覆盖）。
  顺序：改源 → `merge_backfill.py` → `build_dashboard.py`。
- 详见 `data/README.md` 的「字段语义变更」节。

## 发布：走 `scripts/publish.sh`，不要手动 commit
- Pages 入口是**根目录 `index.html`**，不是 `dashboard/index.html`；publish.sh 负责 `cp`。
  手动 commit 会漏掉这一步 → 本地重建了但公网没变（2026-08-22 实际踩过）。
- publish.sh 一条龙：merge → build → cp → IP 红线扫描 → 个人端 push（remote 读回校验）→ 内网 monorepo 同步 push。
- 验证线上是否真更新：**curl 线上 URL 比对 md5**，不看脚本自报。GitHub Pages 有 CDN 缓存，
  首次 curl 可能拿到旧版（曾因此误判发布失败），等 60-90s 复验。

## 待办进度
- [x] 骨架结构 + 双 GitHub 同步
- [ ] 筛 KOL list 非金融预言家 / 灵媒
- [ ] 网上补充名册
- [ ] 名单定稿
- [ ] backfill 过去一年内容
- [ ] dashboard 设计与构建
- [ ] 双发布（web + HTML）
