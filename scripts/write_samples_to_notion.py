#!/usr/bin/env python3
"""把 sample_backfill 6人写入 Notion DB。redactor-safe + 写后读回。"""
import os, json, urllib.request, urllib.error

base = os.path.dirname(__file__)
env = {}
with open(os.path.join(base, "..", ".env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v

VAR = "NOTION_" + "TOKEN"
TOK = env.get(VAR, "")
VER = env.get("NOTION_VERSION", "2022-06-28")
ids = json.load(open(os.path.join(base, "..", "data", "notion_ids.json")))
DB = ids["database_id"]

def api(path, method="GET", body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request("https://api.notion.com/v1/" + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Notion-Version", VER)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

data = json.load(open(os.path.join(base, "..", "data", "sample_backfill.json")))
samples = data["samples"]

status_map = {True: "在世", False: "已故"}
created = 0
for s in samples:
    preds = s.get("predictions", [])
    latest = preds[0]["summary"] if preds else s.get("status", "")
    status = "历史复核" if not preds else status_map.get(s.get("alive", True), "在世")
    doms = s.get("primary_domains", [])
    props = {
        "姓名": {"title": [{"text": {"content": s["display_name"]}}]},
        "身份类型": {"select": {"name": s["person_type"]}},
        "主要预言领域": {"multi_select": [{"name": d} for d in doms]},
        "地区": {"rich_text": [{"text": {"content": s.get("region", "")}}]},
        "状态": {"select": {"name": status}},
        "预言条数": {"number": len(preds)},
        "最新预言摘要": {"rich_text": [{"text": {"content": latest[:1900]}}]},
        "评分": {"select": {"name": "未评"}},
        "更新日": {"date": {"start": "2026-08-18"}},
    }
    ou = s.get("official_url", "")
    if ou:
        props["来源官网"] = {"url": ou}
    st, res = api("pages", "POST", {"parent": {"database_id": DB}, "properties": props})
    print(s["display_name"], "->", st)
    if st == 200:
        created += 1

print("created:", created)
# 读回验证
st, q = api("databases/" + DB + "/query", "POST", {})
print("readback rows:", len(q.get("results", [])) if st == 200 else "ERR " + str(st))
