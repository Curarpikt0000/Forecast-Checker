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

# ---- 收录时间(collected_on) ----
# 口径:每条预言"被本项目抓取入库"的真实日期,不是预言发表日,更不是编造值。
# 来源优先级: ①条目自带 collected_on(每日增量写入当天) ②所属 batch 文件在 git 里的
# 首次提交日(=当初 backfill 落库那天,真实可追溯) ③都拿不到则留空,前端显示"—",绝不臆造。
import subprocess

_collect_cache = {}

def file_collected_on(fn):
    """取 batch 文件在 git 的首次提交日(YYYY-MM-DD)。非 git/未提交返回 None。"""
    if fn in _collect_cache:
        return _collect_cache[fn]
    day = None
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%ad", "--date=short", "--", f"data/{fn}"],
            cwd=os.path.join(base, ".."), capture_output=True, text=True, timeout=15)
        lines = [x.strip() for x in out.stdout.splitlines() if x.strip()]
        if lines:
            day = lines[-1]          # 最后一行 = 最早那次提交
    except Exception:
        day = None
    _collect_cache[fn] = day
    return day


def stamp_collected(rec, fn):
    """给一条人物记录里的每条预言补 collected_on(已有的不覆盖)。"""
    day = file_collected_on(fn)
    for p in rec.get("predictions", []):
        if not p.get("collected_on") and day:
            p["collected_on"] = day
    return rec


# sample (6人)
sample = load_json(os.path.join(D, "sample_backfill.json"), default={})
for r in sample.get("samples", []):
    if r.get("id"):
        merged[r["id"]] = stamp_collected(r, "sample_backfill.json")

# batches 1-6 (list each) + 增量/长线补漏(按id去重合并predictions)
_MERGE_APPEND = ("batch_daily.json", "batch_longrange.json", "batch_fill.json")
# ⚠️ 顺序有意义：batch_daily.json 是每日增量，必须排在**所有**全量 batch 之后。
# 2026-08-24 事故：batch_esoteric_finance.json 排在 batch_daily.json 之后且不在
# _MERGE_APPEND 里，导致 wolfincanada/bopolny/raymondamerriman/qiurun/andrewpancholi
# 等玄学类人物的每日新增被整体覆盖静默丢失（08-23、08-24 两天各丢十余条）。
# 新增全量 batch 文件时，一律插在 batch_daily.json **之前**。
for fn in ["batch_1.json", "batch_2.json", "batch_3.json", "batch_4.json", "batch_5.json", "batch_6.json", "batch_extra.json", "batch_extra2.json", "batch_longrange.json", "batch_esoteric_finance.json", "batch_fill.json", "batch_daily.json"]:
    for r in load_json(os.path.join(D, fn), default=[]):
        if r.get("id"):
            stamp_collected(r, fn)
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

# new_people_batch*.json — 2026-08 增补人物（schema 不同：en_name/cn_name，无 id，带 bio_long/detail）
# 这些文件是 SSOT 源，必须挂在此白名单里；只写 backfill_full.json 会被本脚本重建时覆盖。
_NEW_PEOPLE_FILES = ["new_people_batch1.json", "new_people_batch2.json",
                     "new_people_batch3.json", "new_people_batch4.json",
                     "new_people_batch5.json"]


def _mk_id(en_name):
    """en_name -> snake_case id，与老数据 id 风格一致。"""
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (en_name or "").strip().lower())
    return s.strip("_")


for fn in _NEW_PEOPLE_FILES:
    blob = load_json(os.path.join(D, fn), default={})
    for r in blob.get("people", []):
        en = r.get("en_name")
        if not en:
            print(f"[merge_backfill] 警告: {fn} 有记录缺 en_name，已跳过", file=sys.stderr)
            continue
        pid = r.get("id") or _mk_id(en)
        cn = r.get("cn_name")
        rec = {
            "id": pid,
            "display_name": f"{cn} {en}" if cn and cn != en else en,
            "person_type": r.get("person_type"),
            "region": r.get("region"),
            "alive": r.get("alive"),
            "official_url": r.get("official_url"),
            "bio_long": r.get("bio_long"),
            "primary_domains": r.get("primary_domains") or [],
            "predictions": r.get("predictions") or [],
        }
        stamp_collected(rec, fn)
        if pid in merged:
            # 同 id 已存在：合并 predictions 去重，并补齐 bio_long
            exist = merged[pid]
            seen = {p.get("summary", "") for p in exist.get("predictions", [])}
            for np_ in rec["predictions"]:
                if np_.get("summary") and np_["summary"] not in seen:
                    exist.setdefault("predictions", []).append(np_)
                    seen.add(np_["summary"])
            if rec.get("bio_long") and not exist.get("bio_long"):
                exist["bio_long"] = rec["bio_long"]
        else:
            merged[pid] = rec

# data/details/<person_id>.json — 预言级 detail 源文件（SSOT，见 data/details/README.md）
# 按 summary 精确匹配挂到对应预言上；匹配不上的记警告，不静默丢弃。
_DETAILS_DIR = os.path.join(D, "details")
_det_applied = _det_orphan = 0
if os.path.isdir(_DETAILS_DIR):
    for fn in sorted(os.listdir(_DETAILS_DIR)):
        if not fn.endswith(".json"):
            continue
        blob = load_json(os.path.join(_DETAILS_DIR, fn), default={})
        pid = blob.get("person_id") or fn[:-5]
        rec = merged.get(pid)
        if not rec:
            print(f"[merge_backfill] 警告: details/{fn} 的 person_id={pid} 不在名册中", file=sys.stderr)
            continue
        by_sum = {p.get("summary", ""): p for p in rec.get("predictions", [])}
        for d in blob.get("details", []):
            s, txt = d.get("summary", ""), (d.get("detail") or "").strip()
            if not txt:
                continue
            tgt = by_sum.get(s)
            if tgt is None:
                _det_orphan += 1
                print(f"[merge_backfill] 警告: details/{fn} 有 summary 匹配不上: {s[:40]}", file=sys.stderr)
                continue
            tgt["detail"] = txt
            if d.get("source_url") and not tgt.get("source_url"):
                tgt["source_url"] = d["source_url"]
            _det_applied += 1
    print(f"[merge_backfill] detail 挂载: {_det_applied} 条成功, {_det_orphan} 条未匹配")

roster = {c["id"]: c for c in load_json(os.path.join(D, "roster_candidates.json"), default={}).get("candidates", [])}
PTYPE_MAP = {"psychic_medium": "灵媒通灵", "prophet_seer": "预言先知", "remote_viewer": "遥视RV", "obe": "出体OBE", "precognition_research": "预知研究"}

out = []
# 先判 miss(覆盖所有否定形式) 再判 hit,且"应验"加否定前瞻,避免"没有应验/未应验"被误判为命中
_MISS_RE = re.compile(r"未发生|落空|未应验|未成真|未能应验|尚未应验|从未应验|没有应验|均未|没有发生|最终未")
_HIT_RE = re.compile(r"(?<![未没])(?<!没有)应验|获证实|已证实|确实.{0,4}(夺冠|应验|发生|命中)|成真")
_YR_RE = re.compile(r"(20\d{2}|21\d{2})")
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
        # target_date 是「预言指向的目标时间点」,过去被误删,现在保留
        for k in ["text", "content", "claim", "source", "published_by", "date_made", "note"]:
            p.pop(k, None)
        # 目标年 target_year:①显式 target_date 的年 ②正文提到的最远未来年(比发表年更远才算)
        # ③都没有则回落到发表年(=预言说的就是当下/近期)。用于卡片和「最新言论」板块展示。
        _ty = None
        _td = str(p.get("target_date") or "")
        _m = _YR_RE.search(_td)
        if _m:
            _ty = int(_m.group(1))
        else:
            _say_yr = _YR_RE.search(str(p.get("date") or ""))
            _say_yr = int(_say_yr.group(1)) if _say_yr else None
            _body = f'{p.get("summary","")} {p.get("quote","")}'
            _cands = [int(v) for v in _YR_RE.findall(_body) if 2020 <= int(v) <= 2100]
            if _cands and (_say_yr is None or max(_cands) > _say_yr):
                _ty = max(_cands)
            elif _say_yr:
                _ty = _say_yr
        if _ty:
            p["target_year"] = _ty
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
    "_comment": "【自动生成，勿手工编辑】本文件由 scripts/merge_backfill.py 从 data/ 下的源文件按白名单重建。"
                "新增数据必须建源文件并挂进脚本白名单（_NEW_PEOPLE_FILES 或 batch 列表），"
                "直接编辑本文件会在下次运行时被静默覆盖。真实可追溯每条锚source_url, 绝不编造。",
    "_generated_by": "scripts/merge_backfill.py",
    "_last_updated": today,
    "_total_people": len(out),
    "_total_predictions": sum(len(r.get("predictions", [])) for r in out),
    "_topic_domains": ["金融经济", "地缘军事", "自然灾害", "科技AI未来", "社会政治", "健康疫情", "灵性个人", "科学意识", "金融市场"],
    "_person_types": ["灵媒通灵", "占星预言", "预言先知", "遥视RV", "出体OBE", "预知研究", "模型预测者", "金融玄学/术数预测"],
    "people": out,
}

# ── 防回退断言：记录数只增不减 ────────────────────────────────
# 2026-08-21 事故：11 人/84 条只写进派生产物未挂白名单，次日 cron 重建时被静默覆盖。
# 静默数据丢失比构建失败危险得多——失败会被发现，丢失不会。
_OUT_PATH = os.path.join(D, "backfill_full.json")
_ALLOW_SHRINK = os.environ.get("FC_ALLOW_SHRINK") == "1"
if os.path.exists(_OUT_PATH):
    try:
        _prev = json.load(open(_OUT_PATH, encoding="utf-8"))
        _prev_people = len(_prev.get("people", []))
        _prev_preds = sum(len(r.get("predictions", [])) for r in _prev.get("people", []))
    except Exception as e:
        print(f"[merge_backfill] 警告: 旧文件无法解析，跳过回退检查: {e}", file=sys.stderr)
        _prev_people = _prev_preds = -1
    if _prev_people >= 0:
        _new_people, _new_preds = len(out), result["_total_predictions"]
        if (_new_people < _prev_people or _new_preds < _prev_preds) and not _ALLOW_SHRINK:
            print("=" * 62, file=sys.stderr)
            print("[merge_backfill] 中止：检测到数据回退，拒绝覆盖 SSOT", file=sys.stderr)
            print(f"  人数  {_prev_people} -> {_new_people}", file=sys.stderr)
            print(f"  预言数 {_prev_preds} -> {_new_preds}", file=sys.stderr)
            print("  多半是某个源文件没挂进白名单，或源文件读取失败。", file=sys.stderr)
            print("  确属有意删除时：FC_ALLOW_SHRINK=1 重跑。", file=sys.stderr)
            print("=" * 62, file=sys.stderr)
            sys.exit(2)
        if _ALLOW_SHRINK and (_new_people < _prev_people or _new_preds < _prev_preds):
            print(f"[merge_backfill] 注意: 已按 FC_ALLOW_SHRINK=1 放行缩减 "
                  f"人数{_prev_people}->{_new_people} 条数{_prev_preds}->{_new_preds}", file=sys.stderr)

with open(_OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)

print("合并完成:", len(out), "人,", result["_total_predictions"], "条预言 | 日期:", today)
print("有预言:", len([r for r in out if r.get("predictions")]),
      "| 无新内容:", len([r for r in out if not r.get("predictions")]),
      "| 有bio:", len([r for r in out if r.get("bio")]))
