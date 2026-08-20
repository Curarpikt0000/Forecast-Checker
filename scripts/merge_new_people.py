#!/usr/bin/env python3
"""把 data/new_people_batch{1..4}.json 的新人物合并进 SSOT data/backfill_full.json。

规则:
- 字段映射: en_name->display_name, bio_long->bio_long(新增,保留), 生成 id
- 新增 schema: person.bio_long (长背景), prediction.detail (原话详情)
- bio (短) 由 bio_long 截断生成,保持与既有 76 人一致的卡片渲染
- hit/miss/hit_rate/rating 由 predictions 的 verified 真实统计,不臆造
- collected_on 统一 = batch 文件的 _collected_on
- 幂等: 已存在同名 display_name 则跳过
- 合并前自动备份到 scratch/backups/
"""
import json, os, re, shutil, unicodedata
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSOT = os.path.join(ROOT, "data", "backfill_full.json")
BACKUP_DIR = os.path.join(ROOT, "scratch", "backups")

PERSON_TYPES = ['灵媒通灵','占星预言','预言先知','遥视RV','出体OBE','预知研究','模型预测者']
DOMAINS = ['金融经济','地缘军事','自然灾害','科技AI未来','社会政治','健康疫情','灵性个人','科学意识']


def make_id(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def short_bio(bio_long: str, limit: int = 90) -> str:
    """从长背景取第一句/前 limit 字作为卡片短简介。"""
    if not bio_long:
        return ""
    # 优先取第一个句号前的内容
    first = re.split(r"[。！？]", bio_long)[0]
    if 20 <= len(first) <= limit:
        return first + "。"
    return bio_long[:limit].rstrip("，、；,;") + "…"


def main():
    with open(SSOT, encoding="utf-8") as f:
        ssot = json.load(f)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bk = os.path.join(BACKUP_DIR, f"backfill_full.{stamp}.json")
    shutil.copy2(SSOT, bk)
    print(f"[backup] {bk}")

    existing_names = {p["display_name"] for p in ssot["people"]}
    existing_ids = {p["id"] for p in ssot["people"]}

    added_people = 0
    added_preds = 0
    skipped = []
    errors = []

    for n in (1, 2, 3, 4):
        path = os.path.join(ROOT, "data", f"new_people_batch{n}.json")
        if not os.path.exists(path):
            print(f"[warn] missing {path}")
            continue
        with open(path, encoding="utf-8") as f:
            batch = json.load(f)
        collected_on = batch.get("_collected_on")

        for src in batch["people"]:
            name = src["en_name"]
            if name in existing_names:
                skipped.append(name)
                continue

            pid = make_id(name)
            if pid in existing_ids:
                pid = pid + "_2"

            ptype = src.get("person_type")
            if ptype not in PERSON_TYPES:
                errors.append(f"{name}: 非法 person_type {ptype!r}")
                continue

            doms = [d for d in src.get("primary_domains", []) if d in DOMAINS]
            bad = [d for d in src.get("primary_domains", []) if d not in DOMAINS]
            if bad:
                errors.append(f"{name}: 丢弃非法 domain {bad}")

            preds = []
            hit = miss = 0
            for p in src.get("predictions", []):
                dom = p.get("domain")
                if dom not in DOMAINS:
                    errors.append(f"{name}: prediction 非法 domain {dom!r} -> 跳过该条")
                    continue
                v = p.get("verified")
                if v == "hit":
                    hit += 1
                elif v == "miss":
                    miss += 1
                rec = {
                    "summary": p.get("summary"),
                    "date": p.get("date"),
                    "domain": dom,
                    "source_url": p.get("source_url"),
                    "collected_on": collected_on,
                    "target_year": p.get("target_year"),
                    "verified": v,
                }
                if p.get("detail"):
                    rec["detail"] = p["detail"]
                preds.append(rec)

            total_judged = hit + miss
            hit_rate = round(hit / total_judged, 3) if total_judged else None
            rating = max(1, round(hit / total_judged * 5)) if total_judged else None

            bl = src.get("bio_long", "")
            person = {
                "id": pid,
                "display_name": name,
                "cn_name": src.get("cn_name"),
                "person_type": ptype,
                "region": src.get("region"),
                "alive": src.get("alive"),
                "primary_domains": doms,
                "official_url": src.get("official_url"),
                "bio": short_bio(bl),
                "bio_long": bl,
                "hit": hit,
                "miss": miss,
                "hit_rate": hit_rate,
                "rating": rating,
                "predictions": preds,
            }
            ssot["people"].append(person)
            existing_names.add(name)
            existing_ids.add(pid)
            added_people += 1
            added_preds += len(preds)
            print(f"  + {name:24s} {ptype:6s} preds={len(preds):2d} hit={hit} miss={miss} rating={rating}")

    ssot["_total_people"] = len(ssot["people"])
    ssot["_total_predictions"] = sum(len(p.get("predictions", [])) for p in ssot["people"])
    ssot["_last_updated"] = datetime.now().strftime("%Y-%m-%d")

    with open(SSOT, "w", encoding="utf-8") as f:
        json.dump(ssot, f, ensure_ascii=False, indent=1)

    print()
    print(f"[merge] +{added_people} people, +{added_preds} predictions")
    print(f"[total] people={ssot['_total_people']} predictions={ssot['_total_predictions']}")
    if skipped:
        print(f"[skip] already present: {skipped}")
    if errors:
        print("[errors]")
        for e in errors:
            print("  !", e)


if __name__ == "__main__":
    main()
