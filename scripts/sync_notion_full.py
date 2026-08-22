#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 backfill_full.json 全量人物同步进 Notion DB（人物级一行）。

相对 write_full_to_notion.py 的修复：
  1. 清空/读回都做**分页**（原版 page_size=100 单次，87 行正好卡边界，
     清空会漏行、读回数字会骗人）。
  2. 「最新预言摘要」原版只写 1 条，512 条预言的信息全丢；这里改为
     写最近 N 条带日期的摘要，并把详细内容写进页面正文 block。
  3. 加 429/5xx 退避重试——Notion 限速 ~3 req/s，批量写必然撞。
  4. 写后读回校验行数与人数一致，不一致非零退出。

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
    print("缺 token", file=sys.stderr)
    sys.exit(1)

ids = json.load(open(os.path.join(ROOT, "data", "notion_ids.json")))
DB = ids["database_id"]

HEAD_N = 5          # 摘要字段里放最近几条
BODY_N = 12         # 页面正文里放最近几条详情

# Notion 的 select 字段只接受已定义的选项名，传数据里的原始值会 400。
# 数据层 rating 是数字（5 / 3 / None），Notion 侧是星号串。
RATING_OPTIONS = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
PTYPE_OK = {"灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE", "预知研究", "模型预测者"}
STATUS_OK = {"在世", "已故", "历史复核"}
DOMAIN_OK = {"金融经济", "地缘军事", "自然灾害", "科技AI未来",
             "社会政治", "健康疫情", "灵性个人", "科学意识"}


def rating_name(v):
    """把数据层 rating 映射成 Notion select 合法选项，映射不了一律「未评」。"""
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return "未评"
    return RATING_OPTIONS.get(n, "未评")


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
        except Exception as e:  # 网络抖动
            if i < tries - 1:
                time.sleep(2 ** i + 1)
                continue
            return 0, {"error": str(e)}
    return 0, {}


def query_all():
    """分页拉全部行——不能只取 100。"""
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        st, q = api("databases/" + DB + "/query", "POST", body)
        if st != 200:
            print(f"query 失败 {st}: {json.dumps(q, ensure_ascii=False)[:200]}", file=sys.stderr)
            break
        rows.extend(q.get("results", []))
        if not q.get("has_more"):
            break
        cursor = q.get("next_cursor")
    return rows


def txt(s, limit=1900):
    return [{"text": {"content": (s or "")[:limit]}}]


def main():
    data = json.load(open(os.path.join(ROOT, "data", "backfill_full.json")))
    people = data["people"] if isinstance(data, dict) else data
    total_preds = sum(len(p.get("predictions") or []) for p in people)
    print(f"源数据: {len(people)} 人 / {total_preds} 条预言")

    old = query_all()
    print(f"清空现有 {len(old)} 行...")
    for row in old:
        api("pages/" + row["id"], "PATCH", {"archived": True})
        time.sleep(0.34)

    status_map = {True: "在世", False: "已故"}
    created, failed = 0, []
    for s in people:
        preds = s.get("predictions") or []
        # 按日期倒序，最新在前
        preds_sorted = sorted(preds, key=lambda x: str(x.get("date") or ""), reverse=True)

        if not preds:
            latest = s.get("status") or s.get("note") or "历史复核·无新内容"
            status = "历史复核"
        else:
            lines = []
            for p in preds_sorted[:HEAD_N]:
                d = p.get("date") or ""
                lines.append(f"[{d}] {p.get('summary','')}" if d else p.get("summary", ""))
            latest = "\n".join(lines)
            status = status_map.get(s.get("alive", True), "在世")

        doms = [d for d in (s.get("primary_domains") or []) if d in DOMAIN_OK]
        ptype = s.get("person_type") if s.get("person_type") in PTYPE_OK else "预言先知"
        if status not in STATUS_OK:
            status = "历史复核"
        props = {
            "姓名": {"title": txt(s.get("display_name") or s["id"], 200)},
            "身份类型": {"select": {"name": ptype}},
            "主要预言领域": {"multi_select": [{"name": d} for d in doms]},
            "地区": {"rich_text": txt(s.get("region", ""), 200)},
            "状态": {"select": {"name": status}},
            "预言条数": {"number": len(preds)},
            "最新预言摘要": {"rich_text": txt(latest)},
            "评分": {"select": {"name": rating_name(s.get("rating"))}},
            "更新日": {"date": {"start": data.get("date", "2026-08-22") if isinstance(data, dict) else "2026-08-22"}},
        }
        ou = s.get("official_url", "")
        if ou and str(ou).startswith("http"):
            props["来源官网"] = {"url": ou}

        # 页面正文：逐条预言（摘要 + 详情 + 出处），这是 512 条内容真正的落点
        children = []
        bio = s.get("bio") or ""
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
        if len(preds_sorted) > BODY_N:
            children.append({"object": "block", "type": "paragraph",
                             "paragraph": {"rich_text": txt(
                                 f"（另有 {len(preds_sorted)-BODY_N} 条见 dashboard）")}})

        body = {"parent": {"database_id": DB}, "properties": props}
        if children:
            body["children"] = children[:100]   # Notion 单次 children 上限
        st, res = api("pages", "POST", body)
        if st == 200:
            created += 1
        else:
            failed.append((s["id"], st, json.dumps(res, ensure_ascii=False)[:160]))
            print(f"FAIL {s['id']} {st}", file=sys.stderr)
        time.sleep(0.34)

    print(f"\n写入完成: {created} 行, 失败 {len(failed)}")
    for f in failed:
        print("  ", f)

    back = query_all()
    print(f"读回校验: Notion {len(back)} 行 vs 源 {len(people)} 人")
    if len(back) != len(people):
        print("读回行数与源人数不一致", file=sys.stderr)
        return 1
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
