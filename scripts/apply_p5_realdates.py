#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 P5 回源核实到的真实发表日期回填进 SSOT。

背景（Chao 2026-08-24 指出）：
  「最新言论」板块原本按 collected_on（本项目抓取入库日）分档，那是"我什么时候抓到的"，
  不是"他什么时候说的"。改用 date（发表日）后发现 52 条 date 被错填成了**预言目标年**
  （2027/2030/2050…），证据是 date 与 target_year 完全相同且都在未来。

  Chao 追加要求：「你还是应该首先回查一下 crawl 当时那个网站上有没有 post 日期？
  YouTube 上面应该是有日期的吧？如果所有的都找不到，再用月份或 crawling date 也没关系，
  但你必须先去查。」→ 于是派子 agent 回 source_url 逐条核实。

回填规则：
  1. summary 精确匹配才回填（挂载键，差一字报阻断性错误而非静默跳过）
  2. 只覆盖那些 date 落在未来的错误条目；正常条目一律不动
  3. real_date 为空的保持原样，另标 date_status=unverified，前端归入「发表日待考」
  4. 回填后校验：新日期必须 ≤ 今天，且不得等于 target_year（否则说明又抓成目标年了）

用法：python3 scripts/apply_p5_realdates.py
"""
import datetime
import glob
import json
import os
import re
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
D = os.path.join(ROOT, "data")
TODAY = datetime.date(2026, 8, 24)


def norm(s):
    return re.sub(r"\s+", "", (s or "").strip())


def parse(s):
    raw = str(s or "").strip()
    for f in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.datetime.strptime(raw, f).date()
        except ValueError:
            pass
    return None


def main():
    path = os.path.join(D, "backfill_full.json")
    data = json.load(open(path, encoding="utf-8"))

    idx = {}
    for p in data["people"]:
        for pr in p.get("predictions", []):
            idx[(p["id"], norm(pr.get("summary")))] = pr

    files = sorted(glob.glob(os.path.join(D, "p5_realdate_*.json")))
    print(f"发现 {len(files)} 个回源核实文件")

    applied = Counter()
    no_match, still_future, eq_target, blank = [], [], [], []
    dirty = []

    for f in files:
        base = os.path.basename(f)
        raw = open(f, "rb").read()
        if b"ANONYMIZED" in raw or b"REDACTED" in raw:
            dirty.append(base)
            continue
        for rec in json.load(open(f, encoding="utf-8")):
            key = (rec.get("person_id"), norm(rec.get("summary")))
            if key not in idx:
                no_match.append(f"{base}: {rec.get('person_id')}/{str(rec.get('summary'))[:30]}")
                continue
            pr = idx[key]
            rd = (rec.get("real_date") or "").strip()
            if not rd:
                # 查不到：如实标记，不猜测、不用 collected_on 顶替
                pr["date_status"] = "unverified"
                pr["date_note"] = (rec.get("date_evidence") or "").strip()[:200]
                blank.append(f"{rec.get('person_id')}: {str(rec.get('summary'))[:34]}")
                applied["blank"] += 1
                continue
            dt = parse(rd)
            if dt is None:
                no_match.append(f"{base}: real_date 解析失败 {rd!r}")
                continue
            if dt > TODAY:
                still_future.append(f"{rec.get('person_id')}: {rd}")
                continue
            ty = str(pr.get("target_year") or "")
            if ty and rd == ty:
                # 又抓成目标年了，拒绝回填
                eq_target.append(f"{rec.get('person_id')}: real_date={rd} == target_year")
                continue
            pr["date"] = rd
            pr["date_precision"] = rec.get("date_precision") or "day"
            pr["date_evidence"] = (rec.get("date_evidence") or "").strip()[:240]
            pr["date_status"] = "verified"
            applied[pr["date_precision"]] += 1

    print("\n回填结果：")
    for k in ("day", "month", "year", "blank"):
        if applied[k]:
            print(f"  {k:7s} {applied[k]}")

    blocking = 0
    for label, lst in [("❌ summary 挂载失败", no_match), ("脱敏污染", dirty)]:
        if lst:
            blocking += len(lst)
            print(f"\n{label} ({len(lst)}):")
            for x in lst[:10]:
                print("   ", x)
    for label, lst in [("⚠️ 回填日期仍在未来（已拒绝）", still_future),
                       ("⚠️ real_date 等于 target_year（已拒绝）", eq_target),
                       ("查不到发表日（标 unverified）", blank)]:
        if lst:
            print(f"\n{label} ({len(lst)}):")
            for x in lst[:8]:
                print("   ", x)

    if blocking:
        print("\n有阻断性问题，未写盘")
        return 1

    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 复核：全库还有多少条 date 在未来
    fut = 0
    for p in data["people"]:
        for pr in p.get("predictions", []):
            dt = parse(pr.get("date"))
            if dt and dt > TODAY:
                fut += 1
    print(f"\n写盘后全库 date 仍在未来的条目: {fut}")
    print("✅ 回填完成，接着重跑 build_dashboard.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
