#!/usr/bin/env python3
"""合并所有批次 + sample 为统一 backfill_full.json。字段归一化 + 从 roster 补 bio/person_type/region。"""
import os, json, sys, re
from datetime import datetime, timezone, timedelta

base = os.path.dirname(__file__)
D = os.path.join(base, "..", "data")


def load_json(path, default=None):
    """安全读 JSON：不存在返回 default，损坏则报错退出。"""
    if not os.path.exists(path):
        if default is not None:
            return default
        sys.exit(f"[merge_backfill] 必需文件不存在: {path}")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"[merge_backfill] {os.path.basename(path)} 不是合法 JSON: {e}")


merged = {}

# sample (6人)
sample = load_json(os.path.join(D, "sample_backfill.json"), default={})
for r in sample.get("samples", []):
    if r.get("id"):
        merged[r["id"]] = r

# batches 1-6 (list each) + 增量/长线补漏(按id去重合并predictions)
_MERGE_APPEND = ("batch_daily.json", "batch_longrange.json")
for fn in ["batch_1.json", "batch_2.json", "batch_3.json", "batch_4.json", "batch_5.json", "batch_6.json", "batch_extra.json", "batch_longrange.json", "batch_daily.json"]:
    for r in load_json(os.path.join(D, fn), default=[]):
        if r.get("id"):
            # 增量/补漏文件里同 id 的记录:合并 predictions(去重),不整体覆盖已有 backfill
            if fn in _MERGE_APPEND and r["id"] in merged:
                exist = merged[r["id"]]
                seen = {p.get("summary", "") for p in exist.get("predictions", [])}
                for np_ in r.get("predictions", []):
                    if np_.get("summary") and np_["summary"] not in seen:
                        exist.setdefault("predictions", []).append(np_)
                        seen.add(np_["summary"])
            else:
                merged[r["id"]] = r
        else:
            print(f"[merge_backfill] 警告: {fn} 有记录缺 id，已跳过", file=sys.stderr)

roster = {c["id"]: c for c in load_json(os.path.join(D, "roster_candidates.json"), default={}).get("candidates", [])}
PTYPE_MAP = {"psychic_medium": "灵媒通灵", "prophet_seer": "预言先知", "remote_viewer": "遥视RV", "obe": "出体OBE", "precognition_research": "预知研究"}

out = []
# 先判 miss(覆盖所有否定形式) 再判 hit,且"应验"加否定前瞻,避免"没有应验/未应验"被误判为命中
_MISS_RE = re.compile(r"未发生|落空|未应验|未成真|未能应验|尚未应验|从未应验|没有应验|均未|没有发生|最终未")
_HIT_RE = re.compile(r"(?<![未没])(?<!没有)应验|获证实|已证实|确实.{0,4}(夺冠|应验|发生|命中)|成真")
for id_, r in merged.items():
    rc = roster.get(id_, {})
    if not r.get("person_type"):
        r["person_type"] = PTYPE_MAP.get(rc.get("category", ""), "预言先知")
    if not r.get("region"):
        r["region"] = rc.get("region", "")
    # bio：优先已有，否则用 roster 的简介（卡片下方 background 用）
    if not r.get("bio"):
        r["bio"] = rc.get("bio", "")
    # 预言字段归一化 + 逐条打 verified 状态(hit/miss/pending)
    hit = miss = 0
    for p in r.get("predictions", []):
        if "summary" not in p:
            p["summary"] = p.get("text") or p.get("content") or p.get("claim") or ""
        if "date" not in p:
            p["date"] = p.get("date_made") or ""
        for k in ["text", "content", "claim", "target_date", "source", "published_by", "date_made", "note"]:
            p.pop(k, None)
        # 命中判定：基于 backfill 记录的公开报道/自称措辞(非独立核验)
        s = p["summary"]
        if _MISS_RE.search(s):
            p["verified"] = "miss"; miss += 1
        elif _HIT_RE.search(s):
            p["verified"] = "hit"; hit += 1
        else:
            p["verified"] = "pending"
    # 评分：命中率 = hit/(hit+miss)，5星=100%。无可验证样本 → rating=None(待验证)
    r["hit"] = hit
    r["miss"] = miss
    if hit + miss > 0:
        r["hit_rate"] = round(hit / (hit + miss), 3)
        r["rating"] = int(r["hit_rate"] * 5 + 0.5)  # 标准四舍五入(避免银行家舍入,50%=3星)
    else:
        r["hit_rate"] = None
        r["rating"] = None
    # primary_domains 兜底：从 predictions 汇总
    if not r.get("primary_domains") and r.get("predictions"):
        doms = []
        for p in r["predictions"]:
            d = p.get("domain")
            if d and d not in doms:
                doms.append(d)
        r["primary_domains"] = doms
    out.append(r)

out.sort(key=lambda r: -len(r.get("predictions", [])))

# 动态日期（东京时区），不再硬编码
jst = timezone(timedelta(hours=9))
today = datetime.now(jst).strftime("%Y-%m-%d")

result = {
    "_comment": "Forecast-Checker 全量 backfill. 真实可追溯每条锚source_url, 绝不编造. 历史复核类只收2026+预言,无则note标注.",
    "_last_updated": today,
    "_total_people": len(out),
    "_total_predictions": sum(len(r.get("predictions", [])) for r in out),
    "_topic_domains": ["金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治", "健康疫情", "灵性个人", "科学意识"],
    "_person_types": ["灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE", "预知研究"],
    "people": out,
}
with open(os.path.join(D, "backfill_full.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

print("合并完成:", len(out), "人,", result["_total_predictions"], "条预言 | 日期:", today)
print("有预言:", len([r for r in out if r.get("predictions")]),
      "| 无新内容:", len([r for r in out if not r.get("predictions")]),
      "| 有bio:", len([r for r in out if r.get("bio")]))
