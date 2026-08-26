"""remove_people.py — 从 Forecast-Checker 名册彻底移除指定人物。

为什么不能只删 backfill_full.json
---------------------------------
`backfill_full.json` 是 **merge_backfill.py 从 data/batch_*.json 源文件重建的派生产物**
（见 AGENTS.md「流水线顺序不可调换」）。只删它，下次 publish.sh 一跑 merge 就把人塞回来。
所以必须：源 batch 文件 → details 文件 → 派生 SSOT → Notion，四处同删。

删除范围（按 id 精确匹配，绝不模糊匹配姓名）
-------------------------------------------
  1. data/batch_*.json            源文件里的人物条目
  2. data/details/<id>.json       该人的 detail 文件（含 p2_/p3_ 等前缀变体）
  3. data/backfill_full.json      派生 SSOT
  4. data/kol_list_ssot.json      本地 SSOT 镜像
  5. Notion「SSOT KOL List」       标记为「已移出」而非物理删除（遵守只增不减铁律，留痕可追溯）

安全
----
- 先备份到 data/_removed_backup/<timestamp>/，可回滚。
- --dry 预演，打印每个文件会删几条，不写盘。
- 删完自动跑 merge → 校验人数，确认没被 merge 重新塞回来。

用法::

    python3 scripts/remove_people.py --ids masayoshi_son ilya_sutskever --dry
    python3 scripts/remove_people.py --ids masayoshi_son ilya_sutskever
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
BACKUP_ROOT = os.path.join(DATA, "_removed_backup")

sys.path.insert(0, HERE)


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _dump(p, d):
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)


def _people_of(doc):
    """batch / backfill / targets 等文件的人物列表在不同 key 下，统一取出。

    ★2026-08-26 踩坑：本项目的数据文件有**三种 schema**，只认一种会漏删，
    导致 merge_backfill.py 把已删的人重新塞回来（实测 ilya_sutskever 复活）：
      - backfill_full.json / batch_*.json : key='people'，人物有 'id'
      - new_people_batch3.json            : key='people'，**没有 id**，靠 en_name/cn_name
      - daily_targets.json                : key='targets'，人物有 'id'
      - p4_verdict_*.json                 : 顶层 list，人物键叫 'person_id'
    """
    if isinstance(doc, list):
        return doc, None
    for key in ("people", "kols", "persons", "items", "targets"):
        if isinstance(doc.get(key), list):
            return doc[key], key
    return [], None


def _matches(entry, ids, names):
    """判断一条人物记录是否命中要删的目标。

    id 字段有三种叫法（id / person_id）；new_people_* 里干脆没有 id，
    只能用 en_name / cn_name / display_name 兜底匹配。
    """
    if not isinstance(entry, dict):
        return False
    for k in ("id", "person_id", "kol_id"):
        if entry.get(k) in ids:
            return True
    for k in ("en_name", "cn_name", "display_name", "name"):
        v = (entry.get(k) or "").strip().lower()
        if v and v in names:
            return True
    return False


def remove_from_json(path, ids, names, dry):
    try:
        doc = _load(path)
    except Exception:
        return 0
    people, key = _people_of(doc)
    if not people:
        return 0
    keep = [p for p in people if not _matches(p, ids, names)]
    n = len(people) - len(keep)
    if n and not dry:
        if key:
            doc[key] = keep
            for cnt_key in ("count", "_count"):
                if isinstance(doc.get(cnt_key), int):
                    doc[cnt_key] = len(keep)
        else:
            doc = keep
        _dump(path, doc)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", required=True, help="要移除的人物 id（精确匹配）")
    ap.add_argument("--names", nargs="*", default=[],
                    help="兜底姓名（用于 new_people_* 这类无 id 的文件，大小写不敏感）")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    ids = set(args.ids)
    names = {n.strip().lower() for n in args.names if n.strip()}

    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_ROOT, ts)

    # 目标文件：所有源文件 + 派生 SSOT + 本地镜像
    # ★2026-08-26 踩坑：初版只扫 batch_*.json，漏了 new_people_batch3.json /
    #   daily_targets.json / p4_verdict_*.json —— merge_backfill.py 会从这些文件
    #   把已删的人**重新塞回来**（实测 ilya_sutskever 删完 merge 后复活）。
    #   所以必须把 data/ 下所有可能含人物条目的 json 都扫一遍，别靠文件名前缀假设。
    patterns = ["batch_*.json", "new_people_*.json", "daily_targets.json",
                "p4_verdict_*.json", "p5_*.json", "fill_*.json"]
    targets = []
    for pat in patterns:
        targets += glob.glob(os.path.join(DATA, pat))
    targets += [os.path.join(DATA, "backfill_full.json"),
                os.path.join(DATA, "kol_list_ssot.json")]
    targets = sorted({t for t in targets
                      if os.path.exists(t) and not t.endswith((".bak", ".qbak"))})

    print(f"目标 id: {sorted(ids)}")
    print(f"扫描 {len(targets)} 个文件\n")

    if not args.dry:
        os.makedirs(backup, exist_ok=True)

    total = 0
    for t in targets:
        n = remove_from_json(t, ids, names, dry=True)   # 先探测
        if not n:
            continue
        if not args.dry:
            shutil.copy(t, os.path.join(backup, os.path.basename(t)))
            remove_from_json(t, ids, names, dry=False)
        print(f"  {os.path.relpath(t, ROOT):<46} 移除 {n} 条")
        total += n

    # details 文件
    det_removed = []
    for pid in ids:
        for pat in (f"{pid}.json", f"p2_{pid}.json", f"p3_{pid}.json", f"*_{pid}.json"):
            for f in glob.glob(os.path.join(DATA, "details", pat)):
                det_removed.append(os.path.relpath(f, ROOT))
                if not args.dry:
                    shutil.copy(f, os.path.join(backup, os.path.basename(f)))
                    os.remove(f)
    for f in sorted(set(det_removed)):
        print(f"  {f:<46} 删除 detail")

    print(f"\n合计移除 {total} 条人物记录 + {len(set(det_removed))} 个 detail 文件")
    if args.dry:
        print("[dry] 未写盘")
    else:
        print(f"备份: {os.path.relpath(backup, ROOT)}")
    return ids


if __name__ == "__main__":
    main()
