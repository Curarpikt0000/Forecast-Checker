# 2026-10-03 批准的五件事：publish.sh 现状与可复用做法

> 这些改动已落地。SKILL.md 正文里「发布脚本不更新 Notion 条数」「batch_daily 未跟踪」两处**已过期**，以本文为准。

## publish.sh 现在的段落（顺序）
merge→判定→日期→星级→build→cp 根 index.html→红线扫描→①个人端 push→②内部 monorepo rsync+push（含 `git add -f data/batch_daily.json`）
→**③ 4.5：`add_person_to_notion.py --update`（只 PATCH 属性）→ `notion_append_new.py`（只追加正文）**
→④ vibe→⑤ Cloudflare。4.5 两步失败都只 `>&2` 报 `NOTION_UPDATE_FAILED` / `NOTION_APPEND_FAILED`，不阻断发布。

## 三个会咬人的点
1. **只追加正文不够**：Notion「预言条数」属性不会跟着变，`check_consistency` 立刻报「预言条数不一致」。
   正文追加与属性 `--update` 必须成对接进流程（我第一次只接了追加，Armstrong 128 对 130 红了才补）。
2. **rsync 会把公网端 .gitignore 带到内部端**：凡是「公网要忽略、内部要备份」的文件（batch_daily.json、publish*.sh、notion 脚本），内部端必须 `git add -f`，否则两边都不跟踪、VM 一丢就没。验证用内部端 `git ls-files` + 从远端 `git show origin/<分支>:路径` 读回字节数，不看本地。
3. **新增的 Notion 脚本含 page id**：同步写进 `.gitignore`，并复验 `git ls-files scripts/<name>` 为 0。

## notion_append_new.py 的设计（可复用于任何「Notion 页面正文跟随 SSOT」）
- 幂等靠「先读页面已有 heading_3 标题集合（去空白归一化），只写缺失的」；块无唯一键，重跑不查重会重复。
- 只追加、不删、不改；SSOT 里改过 summary 的旧条会在 Notion 留「陈旧块」→ 只报告不处理（删块属不可逆，留给用户）。
- 新块 ID 追加写入 `data/notion_append_log.jsonl`（只含 page_id/块数）以便回滚。
- 先 `--dry-run`（全库 0 条待追加才算与现状一致）再接进流水线。
- URL 比对要归一化：Notion 会把 `:`→`%3A`、在 `?129774` 后补 `=`。

## merge_backfill.py 两处补丁
- 同 id 已由别的批次建过时，`alive` 也要补（只补空）：否则 SSOT 里 alive=None，状态徽章不准。
- roster 也无 bio 时，退回 `bio_long` 首句（按「。」切）。
- 改完不要单独跑 merge；走完整流水线后对比「人数/条数/星级变化/消失的人」，应只有预期差异。

## 版块顺序调整（卡片提前）
用 `scratch/imp/_reorder.py` 式做法：按 `id="sec-*"` 锚点切块再重组，每块断言命中 1 次；侧栏 `top_items` 与页面顺序同步（图表单独成组放最后）。
量法：Playwright 量各 `sec-*` 的 `top`，第一组卡片 `.group-hd` 应 ≲1300px。回归必查：评分排序、4★ 筛选(7 人)、无横向溢出、0 个 JS 报错。

## 条目拆写（一条 summary 塞多条因果线）
拆前 `batch_daily.json` 备份；每条新 `quote_en` 必须是原文逐字子串（归一化后 `in`）；断言原条命中唯一；新条补 `collected_on`/`target_date`/`domain`/detail≥100 字。
拆完 Notion 里会留 1 个旧标题陈旧块（见上）。

## 入册判据补充：不收「不可证伪理论的提出者」
已故（1992）新纪元作家 + 2026 年只有别人写的综述：全文按句筛 will/predict/by 20xx/within 类句式，零个预测 → 不收、不建空卡。
入册资格（有无不可替代的位置）与评分资格（有无可证伪断言）是两道门，都过不了才不收。给用户的后路：有原始链接就只看其中有无带时间点的论断。
