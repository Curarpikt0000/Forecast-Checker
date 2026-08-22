#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接收从 Eco-and-Volatility-Checker 迁来的 11 位【金融玄学/术数/占星】预测者。

背景(2026-08-22, Chao 决定):
  2026-08-20 Hermes 在 Eco 项目自行新建 sector "Cycles & Esoteric Forecasting" 塞入 23 人,
  属越界(Forecast-Checker 的 AGENTS.md 已规定通灵/占星/末日预言者归本项目)。
  Chao 裁定: 技术分析派 12 人留 Eco, 玄学/术数派 11 人迁入本项目。

输入:
  Eco 侧导出 scratch/cycle_split_esoteric.json (名册条目)
  Eco 侧 data/kol/backfill/<slug>.json        (已回填历史, source 均经 curl 实访验证)

输出:
  data/batch_esoteric_finance.json  —— 新源文件, 需同时挂进 merge_backfill.py 白名单
  (绝不直接写 data/backfill_full.json, 那是派生产物, 会被每日 cron 重建冲掉)

字段映射(Eco KOL 格式 → Forecast-Checker 格式):
  display_name        → display_name
  id                  → id
  forecast_school     → forecast_school (保留, 说明其术数流派)
  bio/institution     → bio
  source_url          → official_url
  history[].date      → predictions[].date
  history[].comments  → predictions[].summary
  history[].source    → predictions[].source_url
"""
import json
import os
import re

ECO = "/home/user/Projects/Eco-and-Volatility-Checker"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ECO, "scratch", "cycle_split_esoteric.json")
BACKFILL_DIR = os.path.join(ECO, "data", "kol", "backfill")
OUT = os.path.join(HERE, "data", "batch_esoteric_finance.json")


def slug(name, kid):
    if kid:
        return kid
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main():
    exp = json.load(open(SRC, encoding="utf-8"))
    people = exp["kols"]
    out = []
    stats = []

    for k in people:
        name = k.get("display_name")
        kid = k.get("id") or slug(name, None)

        # 找回填文件: 先按 id, 再按 slug
        preds = []
        for cand in (kid, slug(name, None)):
            p = os.path.join(BACKFILL_DIR, f"{cand}.json")
            if os.path.exists(p):
                bf = json.load(open(p, encoding="utf-8"))
                for h in bf.get("history", []):
                    if not h.get("source"):
                        continue          # 无出处的不迁(铁律: 每条必须可追溯)
                    preds.append({
                        "summary": h.get("comments", ""),
                        "date": h.get("date", ""),
                        "domain": "金融市场",
                        "source_url": h["source"],
                    })
                break

        out.append({
            "id": kid,
            "display_name": name,
            "person_type": "金融玄学/术数预测",
            "region": k.get("forecast_region") or "",
            "alive": True,
            "official_url": k.get("source_url") or "",
            "forecast_school": k.get("forecast_school") or "",
            "bio": k.get("bio") or k.get("institution") or "",
            "primary_domains": ["金融市场"],
            "predictions": preds,
            "_migrated_from": "Eco-and-Volatility-Checker kol_registry (2026-08-22)",
        })
        stats.append((name, kid, len(preds)))

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"✓ 写入 {OUT}")
    print(f"  共 {len(out)} 人, 预测条目合计 {sum(s[2] for s in stats)}\n")
    for n, i, c in stats:
        flag = "" if c else "   ← 0 条(Eco 侧回填时公开检索即无带日期内容)"
        print(f"  {c:2d} 条  {n}  [{i}]{flag}")
    print("\n⚠️ 还需把 batch_esoteric_finance.json 挂进 scripts/merge_backfill.py 的白名单")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
