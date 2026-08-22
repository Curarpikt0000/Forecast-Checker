#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把子 agent 产出的 data/details/fill_*.json 转成 merge_backfill.py 认得的
增量预言源文件 data/batch_fill.json。

背景 / 为什么需要这一步：
  data/details/*.json 的语义是「给已存在的预言条目挂 detail」，merge_backfill.py
  用 summary 精确匹配，匹配不上就记 orphan 警告——它不会新增预言条目。
  而 fill_*.json 是「为条数过少的人新增预言条目」，结构也不同
  （people[].items[] 而非 details[]），直接放进 details/ 会全部报 orphan。

  因此这里转成 batch_fill.json，并把该文件名挂进 merge_backfill.py 的
  _MERGE_APPEND 白名单，让它走「按 id 合并 predictions 且按 summary 去重」的路径。

铁律：data/backfill_full.json 是派生产物，绝不直接写；SSOT 是源文件 + 白名单。
"""
import json
import os
import sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
D = os.path.abspath(D)

# 预言条目在 SSOT 中的字段：summary/date/domain/source_url/quote/collected_on/detail
FIELDS = ("summary", "date", "domain", "source_url", "quote", "detail", "record_type")


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default if default is not None else {}


def main():
    details_dir = os.path.join(D, "fill_raw")
    fill_files = sorted(
        fn for fn in os.listdir(details_dir)
        if fn.startswith("fill_") and fn.endswith(".json")
    )
    if not fill_files:
        print("没有 fill_*.json，无事可做")
        return 0

    # 现有 SSOT，用来跨文件去重（避免把已有 summary 再加一遍）
    #
    # 【关键】必须减去 batch_fill.json 自身已贡献的条目，否则：
    #   第一次跑 -> 写出 61 条 -> merge 进 SSOT -> 第二次跑时这 61 条已在 SSOT 里
    #   -> 全被判为「重复」-> batch_fill.json 被覆盖成只剩新的几条 -> 源文件缩水。
    # 本脚本必须可重复执行且结果幂等：以「SSOT 减去本文件既有贡献」为去重基准。
    ssot = load(os.path.join(D, "backfill_full.json"), default={})
    people = ssot.get("people", ssot) if isinstance(ssot, dict) else ssot
    prev_fill = load(os.path.join(D, "batch_fill.json"), default=[])
    prev_by_pid = {
        r["id"]: {x.get("summary", "") for x in (r.get("predictions") or [])}
        for r in prev_fill if r.get("id")
    }
    have = {}
    for p in people:
        sums = {x.get("summary", "") for x in (p.get("predictions") or [])}
        have[p["id"]] = sums - prev_by_pid.get(p["id"], set())

    out = {}       # pid -> {"id":pid,"predictions":[...]}
    stats = []
    seen_global = {}

    for fn in fill_files:
        blob = load(os.path.join(details_dir, fn), default={})
        n_add = n_dup = n_bad = 0
        for per in blob.get("people", []):
            pid = per.get("person_id")
            if not pid:
                n_bad += 1
                continue
            if pid not in have:
                print(f"[convert] 警告: {fn} 的 person_id={pid} 不在名册中，跳过", file=sys.stderr)
                n_bad += 1
                continue
            seen = seen_global.setdefault(pid, set(have[pid]))
            for it in (per.get("items") or []):
                s = (it.get("summary") or "").strip()
                if not s:
                    n_bad += 1
                    continue
                if s in seen:
                    n_dup += 1
                    continue
                # 必须有可追溯出处，否则不收 —— 绝不编造
                if not (it.get("source_url") or "").strip():
                    print(f"[convert] 警告: {fn}/{pid} 条目缺 source_url，已丢弃: {s[:30]}", file=sys.stderr)
                    n_bad += 1
                    continue
                rec = {k: it[k] for k in FIELDS if it.get(k)}
                rec["summary"] = s
                rec.setdefault("collected_on", blob.get("_collected_on", ""))
                out.setdefault(pid, {"id": pid, "predictions": []})["predictions"].append(rec)
                seen.add(s)
                n_add += 1
        stats.append((fn, n_add, n_dup, n_bad))

    rows = list(out.values())
    dst = os.path.join(D, "batch_fill.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)

    for fn, a, d, b in stats:
        print(f"  {fn:26} 新增 {a:3}  重复跳过 {d:3}  丢弃 {b:3}")
    total = sum(len(r["predictions"]) for r in rows)
    print(f"\n[convert] 写出 {dst}")
    print(f"[convert] {len(rows)} 人 / {total} 条新增预言")
    print("[convert] 提醒: batch_fill.json 必须挂进 merge_backfill.py 的 _MERGE_APPEND 白名单")
    return 0


if __name__ == "__main__":
    sys.exit(main())
