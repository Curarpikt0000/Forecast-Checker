# 2026-10-03 Notion 被清空重写事故 + 修复流程（Haiku 试跑第二天）

## 现象
用户问「今天 cron 跑了吗」。cron 13:33 ok、SSOT 101 人/1751 条、公网一致，但 `check_consistency` 报 Notion 57 行 != 101。cron 播报自己写「Notion 超时，同步中」，并以 `[SILENT]` 收尾——**自报语气像没事**。

## 取证（只读，别先动手）
1. Notion API 查库：未归档 57 / 已归档 0；57 行 `last_edited_time` 全在同一小时（= cron 运行小时）→ 被整体重写，且无 archive 痕迹 = 清空后重写到一半断。
2. 缺失 44 人 = SSOT 里排序靠后的一批；其中 43 人有星级，1 人非暂定。
3. cron 输出里没有直接的脚本调用痕迹，只能说「高度可能」是 `sync_notion_full.py`（cron prompt 第 6 步明文建议它，与 AGENTS.md 禁令冲突）。**如实说「高度可能」，不说确定。**
4. 对照：10-01 Sonnet 同样读到那句 prompt，改用了增量 `--update`。

## 修复（用户授权「全做」后）
1. `hermes cron edit 683f038fb51c --model claude-sonnet-5-5 --provider custom`（先备份 jobs.json，读回）。
2. 修 prompt 两处（`hermes cron edit --prompt`，前后只差 4 行；读回 `after == 预期`，并确认 model/schedule/workdir/toolsets/deliver 未变）：
   - 第 5 步 `curarpikt0000.github.io/...` → `https://forecast-checker.pages.dev/`
   - 第 6 步 `sync_notion_full.py` → 「绝不跑；缺人 add_person_to_notion <id>；条数 --update」
3. 补 44 人：先落盘 `notion_restore_plan.json`（缺失者 id + 应有评分），断言人数==44 再 `add_person_to_notion.py <ids>`；0 FAIL。
4. **新建行评分默认「未评」**：再 PATCH 评分为 SSOT 星级，只动这 44 行，且已有非默认评分者跳过不覆盖。结果改 43、跳过 1（无预言者）。
5. `check_consistency` 全绿（101==101，名单双向一致，条数逐人一致）。

## 必须对用户说清的两点
- 评分是**从 SSOT 重写，不是还原**：被清空行上人工编辑过的其他字段已不可恢复；`kol_list_ssot.json` 是旧镜像不覆盖。
- 新建行正文（add_person，最多 12 条）与旧行（sync_notion_full 写的）格式可能略有差异；做文本级比对确认（见下）。

## 文本级比对（只读，验证「Notion 内容与 SSOT 一致」）
逐行取 Notion 页面 children，按 `heading_3` 切段，对每个人最近 12 条：标题 `[date] summary (domain)`、第一个 paragraph = detail[:1900]、来源链接 vs SSOT；全部用去空白归一化比较。
实测 101 行：标题 0 缺/0 多、detail 875 段一致、链接 876 一致；差异仅 6 行 bio（SSOT bio 为空）+ 1 条链接末尾斜杠（Notion 自动规范化，等价）。
注意：不能用「块数达标」当一致性证据，它只证明数量够。

## 要补全量正文时（用户已同意，待执行）
46 人需追加 873 条/约 2603 块，约 57 次 append、<1 分钟，单页无硬上限、单次 ≤100 块。
**追加非幂等**（块无唯一键）：先读页面已有 heading_3 标题集合，只追加缺失预言段；先 1 人试、读回比对再全量；**只追加不重排、不清空**（清空重写正是本次事故的做法）。旧条目会接在最新 12 条后面，整页不是严格倒序，要提前告知。

## 元教训
- 交接文档 §13-4 我已把「prompt 第 6 步与禁令冲突」标成待批准，**但没当场改 cron**；两天后换便宜模型就让它变成了真事故。**已知会毁数据的缺陷，在降级执行者之前必须先修或先封**，不能只写进文档。
- cron 自报「超时/同步中/[SILENT]」不是证据，要直接查 Notion。
- 便宜模型的失败形态=字面服从 prompt 里的危险建议；评估它时，验收第五项（一致性一次全绿）比条数更能暴露问题。
