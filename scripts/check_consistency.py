#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三处一致性断言：GitHub SSOT / Notion DB / 公网 dashboard。

为什么需要：2026-08-22 出现过三处脱节——SSOT 98 人、Notion 87 行、公网 87 卡片。
成因是 daily cron 与手工同步交错，加上新增人物的枚举值不在 Notion select 白名单里
（person_type=金融玄学/术数预测、domain=金融市场），静默漏同步而无人发现。

本脚本把「三处必须一致」变成可执行断言，任何一处对不上就非零退出。
挂进 daily cron 后即为守门员。

用法：
    python3 scripts/check_consistency.py            # 全量检查
    python3 scripts/check_consistency.py --no-web   # 跳过公网（刚 push 未生效时）
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, ".."))
PUB_URL = "https://curarpikt0000.github.io/Forecast-Checker/"

# Notion select 字段白名单——新增身份/领域时必须同时在 Notion 建选项，
# 否则写入会 400。这里做前置校验，避免同步到一半才发现。
PTYPE_OK = {"灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE",
            "预知研究", "模型预测者", "金融玄学/术数预测"}
DOMAIN_OK = {"金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治",
             "健康疫情", "灵性个人", "科学意识", "金融市场"}

fails = []
warns = []


def fail(msg):
    fails.append(msg)
    print(f"  FAIL {msg}")


def ok(msg):
    print(f"  OK   {msg}")


def load_env():
    env = {}
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k] = v
    return env


def notion_rows():
    env = load_env()
    tok = env.get("NOTION_" + "TOKEN", "")
    ver = env.get("NOTION_VERSION", "2022-06-28")
    db = json.load(open(os.path.join(ROOT, "data", "notion_ids.json")))["database_id"]
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{db}/query",
            data=json.dumps(body).encode(), method="POST")
        req.add_header("Authorization", "Bearer " + tok)
        req.add_header("Notion-Version", ver)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=45) as r:
            q = json.loads(r.read())
        rows.extend(q.get("results", []))
        if not q.get("has_more"):
            break
        cursor = q.get("next_cursor")
    return rows


def main():
    skip_web = "--no-web" in sys.argv

    # ---- 1) SSOT ----
    data = json.load(open(os.path.join(ROOT, "data", "backfill_full.json"), encoding="utf-8"))
    people = data["people"] if isinstance(data, dict) else data
    n_people = len(people)
    n_preds = sum(len(p.get("predictions") or []) for p in people)
    src_cnt = {(p.get("display_name") or p["id"]): len(p.get("predictions") or []) for p in people}
    print(f"\n[1] SSOT: {n_people} 人 / {n_preds} 条")

    # ---- 2) 枚举白名单校验（防止再次静默漏同步）----
    print("\n[2] 枚举白名单")
    bad_pt = sorted({p.get("person_type") for p in people} - PTYPE_OK - {None})
    doms = set()
    for p in people:
        doms |= {d for d in (p.get("primary_domains") or [])}
        doms |= {x.get("domain") for x in (p.get("predictions") or [])}
    bad_dom = sorted(doms - DOMAIN_OK - {None, ""})
    if bad_pt:
        fail(f"person_type 不在白名单: {bad_pt} — 需先在 Notion select 与 dashboard 加选项")
    else:
        ok(f"person_type 全部合法 ({len(PTYPE_OK)} 类)")
    if bad_dom:
        fail(f"domain 不在白名单: {bad_dom} — 需先在 Notion multi_select 加选项")
    else:
        ok(f"domain 全部合法 ({len(DOMAIN_OK)} 类)")

    # ---- 3) 本地 dashboard ----
    print("\n[3] 本地 dashboard")
    for rel in ("dashboard/index.html", "index.html"):
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            fail(f"{rel} 不存在")
            continue
        h = open(path, encoding="utf-8").read()
        cards = len(re.findall(r'id="pc\d+"', h))
        preds = h.count('class="pred pred-x"')
        if cards == n_people and preds == n_preds:
            ok(f"{rel}: {cards} 卡片 / {preds} 条")
        else:
            fail(f"{rel}: {cards} 卡片 / {preds} 条，应为 {n_people} / {n_preds}")

    # ---- 4) Notion ----
    print("\n[4] Notion DB")
    try:
        rows = notion_rows()
        names = []
        mism = []
        for r in rows:
            t = r["properties"].get("姓名", {}).get("title", [])
            nm = t[0]["text"]["content"] if t else "(空)"
            names.append(nm)
            num = r["properties"].get("预言条数", {}).get("number")
            if nm in src_cnt and num != src_cnt[nm]:
                mism.append((nm, num, src_cnt[nm]))
        if len(rows) == n_people:
            ok(f"行数 {len(rows)} == SSOT {n_people}")
        else:
            fail(f"行数 {len(rows)} != SSOT {n_people}")
        only_git = sorted(set(src_cnt) - set(names))
        only_ntn = sorted(set(names) - set(src_cnt))
        if only_git:
            fail(f"仅在 SSOT 有 {len(only_git)} 人: {only_git[:6]}")
        if only_ntn:
            fail(f"仅在 Notion 有 {len(only_ntn)} 人: {only_ntn[:6]}")
        if not only_git and not only_ntn:
            ok("人物名单双向一致")
        if mism:
            fail(f"预言条数不一致 {len(mism)} 人: {mism[:6]}")
        else:
            ok("预言条数逐人一致")
        dup = len(names) - len(set(names))
        if dup:
            fail(f"Notion 重复姓名 {dup} 个")
        probe = [n for n in names if n.startswith("probe-")]
        if probe:
            fail(f"Notion 残留探针行 {len(probe)} 个")
    except Exception as e:
        fail(f"Notion 查询失败: {e}")

    # ---- 5) 公网 ----
    print("\n[5] 公网 dashboard")
    if skip_web:
        warns.append("已跳过公网检查 (--no-web)")
        print("  SKIP （--no-web）")
    else:
        try:
            req = urllib.request.Request(PUB_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                h = r.read().decode("utf-8", "ignore")
            cards = len(re.findall(r'id="pc\d+"', h))
            preds = h.count('class="pred pred-x"')
            if cards == n_people and preds == n_preds:
                ok(f"{cards} 卡片 / {preds} 条 == SSOT")
            else:
                fail(f"公网 {cards} 卡片 / {preds} 条，应为 {n_people} / {n_preds}（GitHub Pages 可能有 1-2 分钟延迟）")
        except Exception as e:
            fail(f"公网抓取失败: {e}")

    print("\n" + "=" * 46)
    for w in warns:
        print(f"WARN {w}")
    if fails:
        print(f"一致性断言: {len(fails)} 项 FAIL")
        return 1
    print("一致性断言: 全绿 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
