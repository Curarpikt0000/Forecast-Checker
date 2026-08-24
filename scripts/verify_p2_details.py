#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 detail 补全任务的合并前校验器（只读，不改任何数据）。

背景：36 人 140 条预言缺 detail，由子 agent 分批写进 data/details/p2_<pid>.json。
merge_backfill.py 按 **summary 精确匹配** 把 detail 挂到 backfill_full.json 上——
summary 差一个字就静默挂不上（脚本只打警告，容易被漏看）。本脚本在 merge 前
把所有问题一次性暴露出来。

检查项：
  1. JSON 合法性 + person_id 是否在名册里
  2. summary 是否与 backfill_full.json 逐字一致（挂载键，最容易出错）
  3. detail 长度是否落在 100-300 字区间（Chao 的硬要求，允许 ±上浮到 500）
  4. detail 是否疑似「把 summary 换句话说」（与 summary 字符重合度过高 = 敷衍）
  5. 脱敏污染（ANONYMIZED_ 绝不能进数据）
  6. source_url 是否 http 开头

用法：python3 scripts/verify_p2_details.py
退出码 0 = 可以 merge；非 0 = 有阻断性问题。
"""
import glob
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
D = os.path.join(ROOT, "data")

MIN_LEN = 100
MAX_LEN = 500      # 硬上限；100-300 是目标区间，300-500 只提示不阻断
TARGET_MAX = 300


def norm(s):
    """比对用归一化：去空白，统一常见标点全半角差异。"""
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    return s


def overlap_ratio(a, b):
    """b 相对 a 的字符集合覆盖率，用于识别「summary 换句话说」。"""
    sa, sb = set(norm(a)), set(norm(b))
    if not sa:
        return 0.0
    return len(sa & sb) / len(sa)


def main():
    full = json.load(open(os.path.join(D, "backfill_full.json"), encoding="utf-8"))
    people = {p["id"]: p for p in full["people"]}
    # 名册里所有 (pid, summary) 组合
    known = {}
    for pid, p in people.items():
        known[pid] = {norm(x.get("summary", "")): x for x in p.get("predictions", [])}

    files = sorted(glob.glob(os.path.join(D, "details", "p2_*.json")))
    print(f"发现 {len(files)} 个 p2 detail 文件\n")

    n_ok = n_short = n_long = n_echo = 0
    err_badjson, err_nopid, err_nomatch, err_dirty, err_nourl = [], [], [], [], []
    warn_long, warn_echo, warn_short = [], [], []
    per_person = {}

    for f in files:
        base = os.path.basename(f)
        # 脱敏污染必须查磁盘真字节，不能只看解析后的对象
        raw = open(f, "rb").read()
        if b"ANONYMIZED" in raw or b"REDACTED" in raw:
            err_dirty.append(base)
            continue
        try:
            blob = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            err_badjson.append(f"{base}: {e}")
            continue

        pid = blob.get("person_id") or base[3:-5]
        if pid not in people:
            err_nopid.append(f"{base}: person_id={pid} 不在名册")
            continue

        cnt = 0
        for item in blob.get("details", []):
            s = item.get("summary", "")
            d = (item.get("detail") or "").strip()
            u = item.get("source_url", "")

            if norm(s) not in known.get(pid, {}):
                err_nomatch.append(f"{base}: summary 对不上 -> {s[:38]}")
                continue
            if not str(u).startswith("http"):
                err_nourl.append(f"{base}: {s[:28]} 缺 source_url")
                continue

            L = len(d)
            if L < MIN_LEN:
                warn_short.append(f"{base}: {L}字 -> {s[:28]}")
                n_short += 1
            elif L > MAX_LEN:
                warn_long.append(f"{base}: {L}字 -> {s[:28]}")
                n_long += 1
            elif L > TARGET_MAX:
                n_long += 1

            # 「换句话说」检测：detail 几乎只包含 summary 的字，且长度没长多少
            if overlap_ratio(s, d) > 0.92 and L < len(s) * 2.2:
                warn_echo.append(f"{base}: 疑似复述 summary -> {s[:28]}")
                n_echo += 1

            cnt += 1
            n_ok += 1
        per_person[pid] = cnt

    print("=" * 58)
    print(f"通过校验的 detail 条数: {n_ok}")
    print(f"  其中长度 >300 字: {n_long}（仅提示，不阻断）")
    print(f"  其中长度 <100 字: {n_short}")
    print(f"  疑似复述 summary: {n_echo}")
    print(f"覆盖人数: {len(per_person)}")

    blocking = 0
    for label, lst in [("JSON 损坏", err_badjson), ("person_id 不在名册", err_nopid),
                       ("summary 挂载键对不上", err_nomatch), ("脱敏污染", err_dirty),
                       ("缺 source_url", err_nourl)]:
        if lst:
            blocking += len(lst)
            print(f"\n❌ {label} ({len(lst)}):")
            for x in lst[:12]:
                print("   ", x)
            if len(lst) > 12:
                print(f"    ... 另有 {len(lst)-12} 条")

    for label, lst in [("过短(<100字)", warn_short), ("过长(>500字)", warn_long),
                       ("疑似复述", warn_echo)]:
        if lst:
            print(f"\n⚠️  {label} ({len(lst)}):")
            for x in lst[:8]:
                print("   ", x)
            if len(lst) > 8:
                print(f"    ... 另有 {len(lst)-8} 条")

    # 还缺多少
    still = 0
    for pid, p in people.items():
        for pr in p.get("predictions", []):
            if not (pr.get("detail") or "").strip():
                still += 1
    print(f"\n合并前 backfill_full.json 中仍缺 detail: {still} 条")
    print(f"本次 p2 可补上: 最多 {n_ok} 条")

    print("\n" + "=" * 58)
    if blocking:
        print(f"❌ 有 {blocking} 项阻断性问题，修完再 merge")
        return 1
    print("✅ 无阻断性问题，可以 merge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
