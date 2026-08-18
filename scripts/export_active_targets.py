#!/usr/bin/env python3
"""导出每日增量抓取的目标名单(在世+活跃)及各人已有预言摘要(供去重)。
cron agent 每天先跑这个拿到 targets.json,再据此搜新预言,避免重复收录。"""
import os, json, sys

base = os.path.dirname(__file__)
SSOT = os.path.join(base, "..", "data", "backfill_full.json")
if not os.path.exists(SSOT):
    sys.exit(f"[export_active_targets] SSOT 不存在: {SSOT}")
with open(SSOT, encoding="utf-8") as f:
    data = json.load(f)

targets = []
for p in data.get("people", []):
    # 只抓在世 + 有预言(活跃)；已故/历史复核类只在有 2026+ 新预言时手动加,不进每日
    if not p.get("alive") or not p.get("predictions"):
        continue
    targets.append({
        "id": p["id"],
        "display_name": p["display_name"],
        "person_type": p.get("person_type", ""),
        "official_url": p.get("official_url", ""),
        # 已有预言摘要(截断)供 agent 去重比对
        "existing_summaries": [pr.get("summary", "")[:60] for pr in p.get("predictions", [])],
    })

out = {
    "_comment": "每日增量抓取目标(在世活跃)。agent 据 existing_summaries 去重,只收真正的新预言。",
    "_count": len(targets),
    "targets": targets,
}
out_path = os.path.join(base, "..", "data", "daily_targets.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"导出 {len(targets)} 个在世活跃目标 -> data/daily_targets.json")
