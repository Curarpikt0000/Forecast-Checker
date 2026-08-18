# Forecast Checker

灵媒 / 预言家 / 出体者 / 预知未来者 内容汇总 dashboard。

汇总所有灵媒（psychic/medium）、预言家（prophet/seer）、出体体验者（astral projection / OBE）、
以及声称能预见未来的人（remote viewer / precognition）过去一年发表的预测内容，
以卡片 / 雷达图 / 时间线等形式可视化呈现。呈现范式参照 Eco and Volatility Checker 的 KOL 部分。

## 状态
项目初始化中。详见 `AGENTS.md`。

## 结构
- `src/` — 主逻辑
- `data/` — 名册 + backfill 内容 + 数据字典
- `scripts/` — 运行脚本
- `dashboard/` — dashboard 产物
- `docs/` — 文档

## 发布
- web 版：GitHub Pages 公网
- HTML 版：自包含单文件

## 合规
- 内容为公开的灵媒/预言家公开表态，无 Uber 内部数据。
- 个人 repo 推送前剥离所有内网标识。
