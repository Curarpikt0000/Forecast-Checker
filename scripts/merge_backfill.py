#!/usr/bin/env python3
"""合并所有批次 + sample 为统一 backfill_full.json。字段归一化。"""
import os, json

base = os.path.dirname(__file__)
D = os.path.join(base, "..", "data")

merged = {}

# sample (6人)
for r in json.load(open(os.path.join(D, "sample_backfill.json")))["samples"]:
    merged[r["id"]] = r

# batches 1-5 (list each)
for fn in ["batch_1.json", "batch_2.json", "batch_3.json", "batch_4.json", "batch_5.json", "batch_6.json"]:
    p = os.path.join(D, fn)
    if not os.path.exists(p):
        continue
    for r in json.load(open(p)):
        merged[r["id"]] = r

roster = {c["id"]: c for c in json.load(open(os.path.join(D, "roster_candidates.json")))["candidates"]}
PTYPE_MAP = {"psychic_medium": "灵媒通灵", "prophet_seer": "预言先知", "remote_viewer": "遥视RV", "obe": "出体OBE", "precognition_research": "预知研究"}

out = []
for id_, r in merged.items():
    if not r.get("person_type"):
        r["person_type"] = PTYPE_MAP.get(roster.get(id_, {}).get("category", ""), "预言先知")
    if not r.get("region"):
        r["region"] = roster.get(id_, {}).get("region", "")
    for p in r.get("predictions", []):
        if "summary" not in p:
            p["summary"] = p.get("text") or p.get("content") or p.get("claim") or ""
        if "date" not in p:
            p["date"] = p.get("date_made") or ""
        for k in ["text", "content", "claim", "target_date", "source", "published_by", "date_made", "note"]:
            p.pop(k, None)
    if not r.get("primary_domains") and r.get("predictions"):
        doms = []
        for p in r["predictions"]:
            d = p.get("domain")
            if d and d not in doms:
                doms.append(d)
        r["primary_domains"] = doms
    out.append(r)

out.sort(key=lambda r: -len(r.get("predictions", [])))

result = {
    "_comment": "Forecast-Checker 全量 backfill. 真实可追溯每条锚source_url, 绝不编造. 历史复核类只收2026+预言,无则note标注.",
    "_last_updated": "2026-08-18",
    "_total_people": len(out),
    "_total_predictions": sum(len(r.get("predictions", [])) for r in out),
    "_topic_domains": ["金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治", "健康疫情", "灵性个人", "科学意识"],
    "_person_types": ["灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE", "预知研究"],
    "people": out,
}
with open(os.path.join(D, "backfill_full.json"), "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

print("合并完成:", len(out), "人,", result["_total_predictions"], "条预言")
withpred = [r for r in out if r.get("predictions")]
nopred = [r for r in out if not r.get("predictions")]
print("有预言:", len(withpred), "| 无新内容:", len(nopred))
