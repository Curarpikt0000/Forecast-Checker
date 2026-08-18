#!/usr/bin/env python3
"""在 Forecast Checker 父页下建主 DB。redactor-safe。"""
import os, json, urllib.request, urllib.error

env = {}
with open(os.path.join(os.path.dirname(__file__), "..", ".env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v

VAR = "NOTION_" + "TOKEN"
TOK = env.get(VAR, "")
VER = env.get("NOTION_VERSION", "2022-06-28")
PAGE = "3c047eb5fd3c802f81e4caa5c4ae9629"

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

person_types = ["灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE", "预知研究"]
domains = ["金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治", "健康疫情", "灵性个人", "科学意识"]
status_opts = ["在世", "已故", "历史复核"]
rating_opts = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐", "未评"]

body = {
    "parent": {"type": "page_id", "page_id": PAGE},
    "title": [{"type": "text", "text": {"content": "Forecast Checker — 预言家名册"}}],
    "is_inline": True,
    "properties": {
        "姓名": {"title": {}},
        "身份类型": {"select": {"options": [{"name": x} for x in person_types]}},
        "主要预言领域": {"multi_select": {"options": [{"name": x} for x in domains]}},
        "地区": {"rich_text": {}},
        "状态": {"select": {"options": [{"name": x} for x in status_opts]}},
        "预言条数": {"number": {}},
        "最新预言摘要": {"rich_text": {}},
        "来源官网": {"url": {}},
        "评分": {"select": {"options": [{"name": x} for x in rating_opts]}},
        "更新日": {"date": {}},
    },
}

st, res = api("databases", "POST", body)
print("create DB status:", st)
if st == 200:
    print("database_id:", res["id"])
    # 找 data_source_id (2025 版才有; 2022-06-28 无, 用 database_id 即可)
    print("url:", res.get("url", ""))
    with open(os.path.join(os.path.dirname(__file__), "..", "data", "notion_ids.json"), "w") as f:
        json.dump({"parent_page": PAGE, "database_id": res["id"], "url": res.get("url", "")}, f, ensure_ascii=False, indent=1)
    print("saved data/notion_ids.json")
else:
    print("ERROR:", json.dumps(res, ensure_ascii=False)[:500])
