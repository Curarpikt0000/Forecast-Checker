#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增量把 backfill_full.json 里指定 id 的人物写进 Notion DB（只增不删）。

为什么不用 sync_notion_full.py：那个脚本会先 archive 掉现有全部行再全量重写，
属破坏性重建，会丢掉 Notion 上人工编辑过的字段（评分等），也违反「只增不删」铁律。
本脚本只做：查该人是否已存在 -> 不存在则 create，存在则跳过并提示（不覆盖）。

用法： python3 scripts/add_person_to_notion.py <person_id> [<person_id> ...]
铁律：token 只从 .env 读，绝不硬编码、绝不打印。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")

env = {}
with open(os.path.join(ROOT, ".env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v

TOK = env.get("NOTION_" + "TOKEN", "")
VER = env.get("NOTION_VERSION", "2022-06-28")
if not TOK:
    sys.exit("缺 token")

DB = json.load(open(os.path.join(ROOT, "data", "notion_ids.json")))["database_id"]

BODY_N = 12
HEAD_N = 5
RATING_OPTIONS = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
PTYPE_OK = {"灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE", "预知研究",
            "模型预测者", "金融玄学/术数预测"}
DOMAIN_OK = {"金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治",
             "健康疫情", "灵性个人", "科学意识", "金融市场"}


def api(path, method="GET", body=None, tries=4):
    for i in range(tries):
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            "https://api.notion.com/v1/" + path, data=data, method=method)
        req.add_header("Authorization", "Bearer " + TOK)
        req.add_header("Notion-Version", VER)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            code = e.code
            try:
                payload = json.loads(e.read())
            except Exception:
                payload = {}
            if code in (429, 500, 502, 503, 504) and i < tries - 1:
                time.sleep(2 ** i + 1)
                continue
            return code, payload
        except Exception as e:
            if i < tries - 1:
                time.sleep(2 ** i + 1)
                continue
            return 0, {"error": str(e)}
    return 0, {}


def query_all():
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        st, q = api("databases/" + DB + "/query", "POST", body)
        if st != 200:
            sys.exit(f"query 失败 {st}: {json.dumps(q, ensure_ascii=False)[:200]}")
        rows.extend(q.get("results", []))
        if not q.get("has_more"):
            break
        cursor = q.get("next_cursor")
    return rows


def title_of(row):
    return "".join(t["plain_text"] for t in row["properties"]["姓名"]["title"])


def txt(s, limit=1900):
    return [{"text": {"content": (s or "")[:limit]}}]


def build(s):
    preds = s.get("predictions") or []
    preds_sorted = sorted(preds, key=lambda x: str(x.get("date") or ""), reverse=True)
    if not preds:
        latest = s.get("status") or s.get("note") or "历史复核·无新内容"
    else:
        latest = "\n".join(
            (f"[{p.get('date')}] {p.get('summary','')}" if p.get("date") else p.get("summary", ""))
            for p in preds_sorted[:HEAD_N])

    alive = s.get("alive", True)
    if str(alive).lower() == "false":
        status = "已故"
    elif not preds and (s.get("status") or "").strip():
        status = "历史复核"
    else:
        status = "在世"

    doms = [d for d in (s.get("primary_domains") or []) if d in DOMAIN_OK]
    ptype = s.get("person_type") if s.get("person_type") in PTYPE_OK else "预言先知"
    props = {
        "姓名": {"title": txt(s.get("display_name") or s["id"], 200)},
        "身份类型": {"select": {"name": ptype}},
        "主要预言领域": {"multi_select": [{"name": d} for d in doms]},
        "地区": {"rich_text": txt(s.get("region", ""), 200)},
        "状态": {"select": {"name": status}},
        "预言条数": {"number": len(preds)},
        "最新预言摘要": {"rich_text": txt(latest)},
        "评分": {"select": {"name": "未评"}},
        "更新日": {"date": {"start": time.strftime("%Y-%m-%d")}},
    }
    ou = s.get("official_url", "")
    if ou and str(ou).startswith("http"):
        props["来源官网"] = {"url": ou}

    children = []
    bio = s.get("bio_long") or s.get("bio") or ""
    if bio:
        children.append({"object": "block", "type": "paragraph",
                         "paragraph": {"rich_text": txt(bio)}})
    for p in preds_sorted[:BODY_N]:
        head = f"[{p.get('date','')}] {p.get('summary','')} ({p.get('domain','')})"
        children.append({"object": "block", "type": "heading_3",
                         "heading_3": {"rich_text": txt(head, 1900)}})
        if p.get("detail"):
            children.append({"object": "block", "type": "paragraph",
                             "paragraph": {"rich_text": txt(p["detail"])}})
        if p.get("source_url"):
            children.append({"object": "block", "type": "paragraph",
                             "paragraph": {"rich_text": [{
                                 "text": {"content": "来源", "link": {"url": p["source_url"]}}}]}})
    return props, children[:100]


def main(ids):
    data = json.load(open(os.path.join(ROOT, "data", "backfill_full.json")))
    people = {p["id"]: p for p in data["people"]}
    rows = query_all()
    existing = {title_of(r): r["id"] for r in rows}
    print(f"Notion 现有 {len(existing)} 行")

    # --update 模式：更新已存在行的属性（预言条数/最新摘要/更新日），不新建、不 archive。
    # P3 一年期 backfill 后各人 predictions 数量变了，Notion 的「预言条数」必须跟着走，
    # 否则 check_consistency.py 的逐人条数断言会 FAIL。
    # ⚠️ 只 PATCH properties，绝不碰 children、绝不 archive —— 人工编辑过的评分字段
    #    在 properties 里会被覆盖，所以「评分」字段在 update 模式下显式剔除。
    update_mode = "--update" in ids
    ids = [x for x in ids if not x.startswith("--")]
    if update_mode and not ids:
        ids = list(people.keys())

    ok = skipped = updated = 0
    for pid in ids:
        s = people.get(pid)
        if not s:
            print(f"  跳过 {pid}: 不在 backfill_full.json")
            continue
        name = s.get("display_name") or pid
        if name in existing:
            if not update_mode:
                print(f"  已存在，跳过不覆盖: {name}")
                skipped += 1
                continue
            props, _ = build(s)
            props.pop("评分", None)          # 保留人工评分，不覆盖
            st, res = api(f"pages/{existing[name]}", "PATCH", {"properties": props})
            if st == 200:
                updated += 1
            else:
                print(f"  FAIL(update) {name} {st} {json.dumps(res, ensure_ascii=False)[:160]}")
            time.sleep(0.34)
            continue
        props, children = build(s)
        body = {"parent": {"database_id": DB}, "properties": props}
        if children:
            body["children"] = children
        st, res = api("pages", "POST", body)
        if st == 200:
            ok += 1
            print(f"  已写入: {name}  page_id={res['id']}")
        else:
            print(f"  FAIL {name} {st} {json.dumps(res, ensure_ascii=False)[:200]}")
        time.sleep(0.34)

    after = {title_of(r) for r in query_all()}
    print(f"新建 {ok} 行 / 更新 {updated} 行 / 跳过 {skipped}；Notion 现共 {len(after)} 行")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("用法: add_person_to_notion.py <person_id> [...] | --update [person_id ...]")
    sys.exit(main(sys.argv[1:]))
