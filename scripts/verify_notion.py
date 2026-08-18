#!/usr/bin/env python3
"""验证 Notion 父页可访问性 + 列出其 child_database。redactor-safe。"""
import os, json, urllib.request, urllib.error

# 读 .env
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

def api(path):
    req = urllib.request.Request("https://api.notion.com/v1/" + path)
    req.add_header("Authorization", "Bearer " + TOK)
    req.add_header("Notion-Version", VER)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

print("token len:", len(TOK))
st, page = api("pages/" + PAGE)
print("GET page status:", st)
if st == 200:
    props = page.get("properties", {})
    title = ""
    for p in props.values():
        if p.get("type") == "title":
            title = "".join(t.get("plain_text", "") for t in p.get("title", []))
    print("page title:", title)
    # 列 children 找 child_database
    st2, ch = api("blocks/" + PAGE + "/children")
    print("GET children status:", st2)
    if st2 == 200:
        for b in ch.get("results", []):
            t = b.get("type")
            if t == "child_database":
                print("  child_database:", b["id"], b["child_database"].get("title"))
            else:
                print("  block:", t)
else:
    print("ERROR body:", json.dumps(page, ensure_ascii=False)[:400])
