#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 P4 应验判定结果回填进 SSOT（data/backfill_full.json）。

数据流：
  scratch/p4/batch_N.json  →(子 agent 查证)→  data/p4_verdict_N.json  →(本脚本)→ backfill_full.json
  然后 compute_ratings.py 读 verified 字段算星级。

回填字段（写到 prediction 上）：
  verified        : "hit" / "miss" / "unclear"（原值 "pending"）
  verdict_reason  : 60-200 字判定依据
  verdict_source  : 查证所用链接

⚠️ 三条纪律
 1. **summary 精确匹配**才回填。子 agent 若擅自改了 summary，这里会报「挂载失败」而不是静默跳过
    ——P2 阶段就是靠这个机制抓到过错位。
 2. **只覆盖 verified == "pending" 的条目**。已经是 hit/miss 的（人工或早期判定）不动，
    避免自动流程推翻人工结论。
 3. 跨批重复判定同一条时，以**首个非 unclear 的判定**为准；全是 unclear 才写 unclear。
    （batch_10 的 agent 被要求倒序补做 batch_7，会产生重复，这里做确定性去重。）

用法：python3 scripts/apply_p4_verdicts.py
"""
import glob
import json
import os
import re
import sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
D = os.path.join(ROOT, "data")

VALID = {"hit", "miss", "unclear"}


def norm(s):
    return re.sub(r"\s+", "", (s or "").strip())


def main():
    path = os.path.join(D, "backfill_full.json")
    data = json.load(open(path, encoding="utf-8"))

    # 索引：(person_id, 归一化summary) -> prediction 对象
    idx = {}
    for p in data["people"]:
        for pr in p.get("predictions", []):
            idx[(p["id"], norm(pr.get("summary")))] = pr

    files = sorted(glob.glob(os.path.join(D, "p4_verdict_*.json")))
    print(f"发现 {len(files)} 个判定文件")

    # 先收集，做跨批去重（优先非 unclear）
    collected = {}
    bad_json, bad_pid, no_match, bad_verdict, dirty = [], [], [], [], []
    seen_raw = 0

    for f in files:
        base = os.path.basename(f)
        raw = open(f, "rb").read()
        if b"ANONYMIZED" in raw or b"REDACTED" in raw:
            dirty.append(base)
            continue
        try:
            blob = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            bad_json.append(f"{base}: {e}")
            continue
        if not isinstance(blob, list):
            bad_json.append(f"{base}: 顶层不是 list")
            continue

        for rec in blob:
            pid = rec.get("person_id")
            for v in rec.get("verdicts", []):
                seen_raw += 1
                verdict = v.get("verdict")
                key = (pid, norm(v.get("summary")))
                if verdict not in VALID:
                    bad_verdict.append(f"{base}: {pid}/{str(v.get('summary'))[:24]} -> {verdict!r}")
                    continue
                if key not in idx:
                    no_match.append(f"{base}: {pid}/{str(v.get('summary'))[:34]}")
                    continue
                prev = collected.get(key)
                # 去重：已有非 unclear 的判定就不被 unclear 覆盖
                if prev and prev["verdict"] != "unclear":
                    continue
                collected[key] = {
                    "verdict": verdict,
                    "reason": (v.get("verdict_reason") or "").strip(),
                    "source": (v.get("verdict_source") or "").strip(),
                }

    # 回填
    applied = Counter()
    skipped_already = 0
    for key, v in collected.items():
        pr = idx[key]
        if pr.get("verified") in ("hit", "miss"):
            skipped_already += 1
            continue
        pr["verified"] = v["verdict"]
        if v["reason"]:
            pr["verdict_reason"] = v["reason"]
        if v["source"]:
            pr["verdict_source"] = v["source"]
        applied[v["verdict"]] += 1

    print(f"\n读到判定 {seen_raw} 条，去重后 {len(collected)} 条")
    print("回填结果：")
    for k in ("hit", "miss", "unclear"):
        print(f"  {k:8s} {applied[k]}")
    print(f"  已有人工判定跳过: {skipped_already}")

    ok = True
    for label, lst in [("JSON 损坏", bad_json), ("person_id 不存在", bad_pid),
                       ("❌ summary 挂载失败", no_match), ("verdict 取值非法", bad_verdict),
                       ("脱敏污染", dirty)]:
        if lst:
            if label.startswith("❌") or label == "脱敏污染":
                ok = False
            print(f"\n{label} ({len(lst)}):")
            for x in lst[:10]:
                print("   ", x)
            if len(lst) > 10:
                print(f"    ... 另有 {len(lst)-10} 条")

    if not ok:
        print("\n有阻断性问题，未写盘")
        return 1

    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 汇总当前 SSOT 判定状态
    tot = Counter()
    for p in data["people"]:
        for pr in p.get("predictions", []):
            tot[pr.get("verified") or "pending"] += 1
    print("\n写盘后 SSOT 判定分布：")
    for k, n in tot.most_common():
        print(f"  {k:8s} {n}")
    print("\n✅ 回填完成，接着跑 scripts/compute_ratings.py 重算星级")
    return 0


if __name__ == "__main__":
    sys.exit(main())
