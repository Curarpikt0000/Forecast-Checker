#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOL 星级评分引擎（Wilson 置信下界法）。

Chao 2026-08-24 需求：给每个预言者 1-5 星，同时考虑「应验条数的绝对值」和「百分比」。
  「20 条中 5 条应验」比例高 → 4-5 星
  「100 条中 5 条应验」比例低 → 要调低

为什么用 Wilson 置信下界而不是裸命中率：
  裸命中率会让「1 条中 1 条」= 100% 拿满分，而「20 条中 15 条」= 75% 反而更低——
  这正是改造前看板的实际状态（ANONYMIZED_PERSON_0_37 判过 1 条碰巧中，就顶着 5 星）。
  Wilson 下界是「在 95% 置信度下，这个人的真实命中率至少是多少」，样本越小下界被压得越狠，
  天然实现了「绝对值 + 百分比」的联合评价，且无需手调魔法参数。

  hit=1  n=1   → p=1.00  下界 0.207   （样本太小，不敢给高分）
  hit=3  n=3   → p=1.00  下界 0.438
  hit=5  n=20  → p=0.25  下界 0.111
  hit=15 n=20  → p=0.75  下界 0.531   （高率+够样本，才是真高分）
  hit=5  n=100 → p=0.05  下界 0.022   （Chao 点名要压低的情形）

未评级者（judged=0）不参与 Wilson 排序，按「数据量」给 1-2 星底分（Chao 选项 B），
并在前端标注 provisional，避免与真实战绩分混淆。
"""
import json
import math
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, "..")
D = os.path.join(ROOT, "data")

Z = 1.96          # 95% 置信
MIN_JUDGED = 3    # 少于这么多条判定，视为样本不足，降级为暂定分

# ★ 评分方式：**百分位相对评分**（Chao 2026-08-24 拍板）
#
# 为什么不用绝对切点：没有人能客观说「25% 命中率」在预言领域算好还是坏——
# 任何硬编码的 0.45/0.28/0.10 门槛都是拍脑袋。改为在**所有已评级 KOL 内部**
# 按 Wilson 下界排名给星，含义变成可解释的「他在本库全部预言者中排前百分之几」。
#
# 分档比例（金字塔形，5 星稀缺）：
#   前 10%  → ★★★★★
#   10-30% → ★★★★
#   30-60% → ★★★
#   60-85% → ★★
#   后 15%  → ★
# 排序键仍是 Wilson 下界，所以「绝对值 + 百分比」的联合评价没有丢：
# 20条中5条 依然排在 100条中5条 前面，只是最终星级由相对位次决定。
PCT_CUTS = [(0.10, 5), (0.30, 4), (0.60, 3), (0.85, 2)]


def wilson_lower(hits, n, z=Z):
    """Wilson score 区间下界。n=0 时返回 0。"""
    if n <= 0:
        return 0.0
    p = hits / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (center - margin) / denom)


def sort_key(hits, n):
    """排序键 = (Wilson下界, 全错时的样本量惩罚)。

    为什么需要第二维：hits=0 时 Wilson 下界恒为 0.0，于是「0命中/8判定」和
    「0命中/3判定」并列同分。但这两者证据强度完全不同——判得越多仍然全错，
    越能确证此人不准，理应排更后面。用 -n 作次级键，让 0/10 排在 0/3 之后。
    对 hits>0 的人第二维恒为 0，不影响主排序。
    """
    lb = wilson_lower(hits, n)
    return (lb, 0.0 if hits > 0 else -n)


def volume_star(total):
    """未评级者的数据量底分（1-2 星，Chao 选 B：避免大面积空白）。"""
    if total >= 10:
        return 2
    if total >= 1:
        return 1
    return 0


def measure_person(p):
    """第一阶段：只算客观指标与排序键，不定星级（星级需全库排名后才知道）。"""
    preds = p.get("predictions", []) or []
    total = len(preds)
    hits = sum(1 for x in preds if x.get("verified") == "hit")
    misses = sum(1 for x in preds if x.get("verified") == "miss")
    judged = hits + misses
    hit_rate = (hits / judged) if judged else None
    lb = wilson_lower(hits, judged) if judged else 0.0
    return {
        "hit": hits,
        "miss": misses,
        "judged": judged,
        "pending": total - judged,
        "total_predictions": total,
        "hit_rate": round(hit_rate, 4) if hit_rate is not None else None,
        "wilson_lb": round(lb, 4),
        "_sk": sort_key(hits, judged),   # 内部排序键，不写入 SSOT
    }


def assign_stars(people_measures):
    """第二阶段：在**已评级群体内部**按 Wilson 下界百分位定星。

    people_measures: list[(key, measure_dict)]
    回写 rating / rating_provisional / rating_pct（百分位，0=最强）。

    只有 judged >= MIN_JUDGED 的人进入排名池；判定过但样本不足的封顶 3 星并标暂定；
    完全未判定的按数据量给 1-2 星底分（Chao 选项 B）。
    """
    pool = [(k, m) for k, m in people_measures if m["judged"] >= MIN_JUDGED]
    # 并列处理：同一排序键取相同百分位，避免同分不同星
    pool.sort(key=lambda kv: kv[1]["_sk"], reverse=True)
    n = len(pool)
    sk_to_pct = {}
    for i, (_, m) in enumerate(pool):
        sk_to_pct.setdefault(m["_sk"], i / n if n else 1.0)

    out = {}
    for k, m in people_measures:
        clean = {kk: vv for kk, vv in m.items() if kk != "_sk"}
        if m["judged"] >= MIN_JUDGED:
            pct = sk_to_pct[m["_sk"]]
            star = 1
            for cut, s in PCT_CUTS:
                if pct < cut:
                    star = s
                    break
            out[k] = {**clean, "rating": star, "rating_provisional": False,
                      "rating_pct": round(pct, 4)}
        elif m["judged"] > 0:
            # 判定过但不足 MIN_JUDGED：给参考位次但封顶 3 星
            ref = sum(1 for _, x in pool if x["_sk"] > m["_sk"])
            pct = ref / n if n else 1.0
            star = 1
            for cut, s in PCT_CUTS:
                if pct < cut:
                    star = s
                    break
            out[k] = {**clean, "rating": min(star, 3), "rating_provisional": True,
                      "rating_pct": round(pct, 4)}
        else:
            out[k] = {**clean, "rating": volume_star(m["total_predictions"]),
                      "rating_provisional": True, "rating_pct": None}
    return out


def rating_tooltip(r):
    """给前端用的一句话解释，鼠标悬停显示。"""
    if r["judged"] == 0:
        return (f"未评级（{r['total_predictions']} 条预言尚无到期判定）"
                f"·当前星级仅反映数据量")
    base = (f"已判定 {r['judged']} 条：命中 {r['hit']} / 落空 {r['miss']}"
            f"，命中率 {r['hit_rate']*100:.0f}%")
    if r.get("rating_pct") is not None:
        base += f"，全库排名前 {r['rating_pct']*100:.0f}%"
    if r["pending"]:
        base += f"；另有 {r['pending']} 条未到期或待判定"
    if r["rating_provisional"]:
        base += "·样本不足，暂定分"
    return base


def main():
    path = os.path.join(D, "backfill_full.json")
    data = json.load(open(path, encoding="utf-8"))

    measures = [(p["id"], measure_person(p)) for p in data["people"]]
    scored = assign_stars(measures)

    dist = {}
    prov = 0
    for p in data["people"]:
        r = scored[p["id"]]
        p.update(r)
        p["rating_tooltip"] = rating_tooltip(r)
        dist[r["rating"]] = dist.get(r["rating"], 0) + 1
        if r["rating_provisional"]:
            prov += 1
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("星级分布：")
    for s in sorted(dist, reverse=True):
        print(f"  {'★'*s}{'☆'*(5-s)} {s}星: {dist[s]} 人")
    print(f"暂定分(样本不足/未评级): {prov} 人 / {len(data['people'])}")
    real = [p for p in data["people"] if not p["rating_provisional"]]
    print(f"\n有效战绩分(judged>={MIN_JUDGED}): {len(real)} 人")
    for p in sorted(real, key=lambda x: -x["wilson_lb"])[:12]:
        print(f"  {'★'*p['rating']:5s} {p['display_name'][:26]:28s} "
              f"{p['hit']}/{p['judged']} lb={p['wilson_lb']} 前{p['rating_pct']*100:.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
