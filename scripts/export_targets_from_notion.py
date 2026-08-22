#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Notion DB 导出每日采集目标 —— Notion 是人名的权威源（Chao 2026-08-22 指定）。

为什么必须从 Notion 取人名，而不是从本地文件：
  本地 JSON 经过多轮 agent 读写，人名有被 redactor 占位符污染的风险
  （2026-08-22 实测：detail 正文里 2 处第三方人名被写成 ANONYMIZED_ 占位符）。
  Notion DB 的「姓名」是人工可见、可校对的权威值，用它驱动每日采集，
  可保证「每天都用准确的人名去抓取」。

产出 data/daily_targets.json，供 daily cron 采集使用。

筛选规则：
  - 状态 = 「在世」才进采集（已故 / 历史复核 不进每日更新）
  - 姓名含 ANONYMIZED_ 的一律拒绝并 FAIL —— 绝不用被脱敏的人名去搜索

用法：
    python3 scripts/export_targets_from_notion.py
    python3 scripts/export_targets_from_notion.py --dry-run   # 只看差异不写文件
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, ".."))


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
    while True:                       # 必须分页，page_size 上限 100
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


def plain(prop, kind):
    if not prop:
        return ""
    if kind in ("title", "rich_text"):
        arr = prop.get(kind) or []
        return "".join(x.get("text", {}).get("content", "") for x in arr).strip()
    if kind == "select":
        return (prop.get("select") or {}).get("name", "") or ""
    if kind == "url":
        return prop.get("url") or ""
    if kind == "number":
        return prop.get("number")
    return ""


def main():
    dry = "--dry-run" in sys.argv
    rows = notion_rows()
    print(f"Notion DB: {len(rows)} 行")

    # SSOT 里取 existing_summaries（避免采集重复条目）与 id 映射
    data = json.load(open(os.path.join(ROOT, "data", "backfill_full.json"), encoding="utf-8"))
    people = data["people"] if isinstance(data, dict) else data
    by_name = {(p.get("display_name") or p["id"]): p for p in people}

    targets, skipped, dirty = [], [], []
    for r in rows:
        props = r["properties"]
        name = plain(props.get("姓名"), "title")
        status = plain(props.get("状态"), "select")
        ptype = plain(props.get("身份类型"), "select")
        url = plain(props.get("来源官网"), "url")

        if not name:
            skipped.append(("(无姓名)", status))
            continue
        # 绝不用被脱敏的人名去搜索
        if "ANONYMIZED_" in name:
            dirty.append(name)
            continue
        if status != "在世":
            skipped.append((name, status or "(空)"))
            continue

        p = by_name.get(name, {})
        targets.append({
            "id": p.get("id") or name,
            "display_name": name,                      # 权威人名，来自 Notion
            "person_type": ptype or p.get("person_type"),
            "official_url": url or p.get("official_url", ""),
            "existing_summaries": [x.get("summary") for x in (p.get("predictions") or [])],
        })

    if dirty:
        print(f"\n拒绝 {len(dirty)} 个含 ANONYMIZED_ 的姓名 —— 请先在 Notion 修正为真名", file=sys.stderr)
        return 1

    unmatched = [t["display_name"] for t in targets if t["id"] == t["display_name"]]
    print(f"在世可采集: {len(targets)} 人")
    print(f"跳过（非在世）: {len(skipped)} 人")
    if unmatched:
        print(f"注意 {len(unmatched)} 人在 SSOT 中未按 display_name 匹配到, id 回退为姓名: {unmatched[:5]}")

    # 与现有文件比差异
    dst = os.path.join(ROOT, "data", "daily_targets.json")
    try:
        old = json.load(open(dst, encoding="utf-8"))
        old_ids = {x["id"] for x in old.get("targets", [])}
    except Exception:
        old_ids = set()
    new_ids = {t["id"] for t in targets}
    added, removed = sorted(new_ids - old_ids), sorted(old_ids - new_ids)
    if added:
        print(f"新增 {len(added)}: {added}")
    if removed:
        print(f"移除 {len(removed)}: {removed}")
    if not added and not removed:
        print("与现有 daily_targets 一致，无变化")

    if dry:
        print("\n--dry-run，未写文件")
        return 0

    out = {
        "_comment": "每日采集目标。SSOT = Notion DB 的「姓名」字段（人名权威源，Chao 2026-08-22 指定）。"
                    "本文件由 scripts/export_targets_from_notion.py 生成，请勿手工编辑；"
                    "增删人物请改 Notion，再重跑本脚本。只收「状态=在世」者。",
        "_generated_from": "notion",
        "_count": len(targets),
        "targets": targets,
    }
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n已写出 {dst}（{len(targets)} 人）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
