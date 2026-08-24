#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 一年期 backfill 的入库校验器（只读，不改数据）。

背景：29 位在世预言家过去一年内容不足 3 条，由子 agent 分批抓新预言写进
data/p3_batch_N.json。这批数据是**新增预言**（不是补 detail），风险比 P2 高得多：

  ⚠️ 历史教训：上一轮出现 972 条日期错配——子 agent 把无日期内容随意标日期，
     等于伪造历史。所以日期硬校验是本脚本的第一优先级。

检查项：
  1. JSON 合法 + list 结构 + person_id 在名册内
  2. **date 必须落在 2025-08-24 .. 2026-08-24 窗口内**（越界即阻断）
  3. detail 必填且 100-500 字（100-300 是目标，300-500 只提示）
  4. domain 必须在九类白名单内（否则 Notion 写入会 400、导航栏不显示）
  5. source_url 必须 http 开头
  6. 与库中已有 summary 重复检测（防止把老观点重收一遍充数）
  7. 脱敏污染（查磁盘真字节）
  8. 疑似「detail 复述 summary」

用法：python3 scripts/verify_p3_backfill.py
退出码 0 = 可入库；非 0 = 有阻断性问题。
"""
import datetime
import glob
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
D = os.path.join(ROOT, "data")

WIN_START = datetime.date(2025, 8, 24)
WIN_END = datetime.date(2026, 8, 24)
MIN_LEN, TARGET_MAX, MAX_LEN = 100, 300, 500

DOMAIN_OK = {"金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治",
             "健康疫情", "灵性个人", "科学意识", "金融市场"}


def norm(s):
    return re.sub(r"\s+", "", (s or "").strip())


def parse_date(s):
    s = str(s or "").strip()
    for f in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def overlap_ratio(a, b):
    sa, sb = set(norm(a)), set(norm(b))
    return len(sa & sb) / len(sa) if sa else 0.0


def main():
    full = json.load(open(os.path.join(D, "backfill_full.json"), encoding="utf-8"))
    people = {p["id"]: p for p in full["people"]}
    existing = {pid: {norm(x.get("summary", "")) for x in p.get("predictions", [])}
                for pid, p in people.items()}

    files = sorted(glob.glob(os.path.join(D, "p3_batch_*.json")))
    print(f"发现 {len(files)} 个 P3 批次文件\n")

    err_json, err_pid, err_date, err_domain, err_url, err_dirty, err_nodetail = \
        [], [], [], [], [], [], []
    warn_dup, warn_short, warn_long, warn_echo = [], [], [], []
    n_ok = 0
    per_person = {}

    for f in files:
        base = os.path.basename(f)
        raw = open(f, "rb").read()
        if b"ANONYMIZED" in raw or b"REDACTED" in raw:
            err_dirty.append(base)
            continue
        try:
            blob = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            err_json.append(f"{base}: {e}")
            continue
        if not isinstance(blob, list):
            err_json.append(f"{base}: 顶层不是 list")
            continue

        for rec in blob:
            pid = rec.get("id")
            if pid not in people:
                err_pid.append(f"{base}: id={pid} 不在名册")
                continue
            for p in rec.get("predictions", []):
                s = p.get("summary", "")
                det = (p.get("detail") or "").strip()
                dt = parse_date(p.get("date"))
                dom = p.get("domain", "")
                url = p.get("source_url", "")
                tag = f"{pid}/{s[:26]}"

                # 日期硬校验 —— 最高优先级
                if dt is None:
                    err_date.append(f"{tag}: date 解析失败 ({p.get('date')!r})")
                    continue
                if not (WIN_START <= dt <= WIN_END):
                    err_date.append(f"{tag}: date={dt} 越界（窗口 {WIN_START}..{WIN_END}）")
                    continue
                if not det:
                    err_nodetail.append(f"{tag}: 缺 detail")
                    continue
                if dom not in DOMAIN_OK:
                    err_domain.append(f"{tag}: domain={dom!r} 不在九类白名单")
                    continue
                if not str(url).startswith("http"):
                    err_url.append(f"{tag}: source_url 非法")
                    continue

                if norm(s) in existing.get(pid, set()):
                    warn_dup.append(f"{tag}: 与库中已有 summary 重复")
                L = len(det)
                if L < MIN_LEN:
                    warn_short.append(f"{tag}: detail 仅 {L} 字")
                elif L > MAX_LEN:
                    warn_long.append(f"{tag}: detail {L} 字")
                if overlap_ratio(s, det) > 0.92 and L < len(s) * 2.2:
                    warn_echo.append(f"{tag}: 疑似复述 summary")

                per_person[pid] = per_person.get(pid, 0) + 1
                n_ok += 1

    print("=" * 58)
    print(f"通过校验的新预言: {n_ok} 条，覆盖 {len(per_person)} 人")

    blocking = 0
    for label, lst in [("JSON/结构错误", err_json), ("person_id 不在名册", err_pid),
                       ("⚠️ 日期越界或无法解析", err_date), ("domain 不在白名单", err_domain),
                       ("source_url 非法", err_url), ("缺 detail", err_nodetail),
                       ("脱敏污染", err_dirty)]:
        if lst:
            blocking += len(lst)
            print(f"\n❌ {label} ({len(lst)}):")
            for x in lst[:12]:
                print("   ", x)
            if len(lst) > 12:
                print(f"    ... 另有 {len(lst)-12} 条")

    for label, lst in [("与库中重复", warn_dup), ("detail 过短", warn_short),
                       ("detail 过长", warn_long), ("疑似复述", warn_echo)]:
        if lst:
            print(f"\n⚠️  {label} ({len(lst)}):")
            for x in lst[:8]:
                print("   ", x)

    # 达标情况
    print("\n" + "-" * 58)
    print("入库后各人近一年条数预估：")
    ymd = datetime.date(2025, 8, 24)
    still_short = []
    for pid, p in people.items():
        if p.get("alive") is False:
            continue
        cur = sum(1 for x in p.get("predictions", [])
                  if (parse_date(x.get("date")) or datetime.date(1900, 1, 1)) >= ymd)
        add = per_person.get(pid, 0)
        if cur + add < 3:
            still_short.append((p.get("display_name"), cur, add, cur + add))
    if still_short:
        print(f"  仍不足 3 条的 {len(still_short)} 人：")
        for nm, cur, add, tot in sorted(still_short, key=lambda x: x[3]):
            print(f"    {nm[:34]:36s} 原{cur} + 新{add} = {tot}")
    else:
        print("  ✅ 全部在世者近一年 ≥3 条")

    print("\n" + "=" * 58)
    if blocking:
        print(f"❌ 有 {blocking} 项阻断性问题，修完再入库")
        return 1
    print("✅ 无阻断性问题，可以入库")
    return 0


if __name__ == "__main__":
    sys.exit(main())
