#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Forecast-Checker 各源文件里英文 quote 译成中文（Chao 2026-08-22 选方案 B）。

为什么改源文件而不改 backfill_full.json:
  backfill_full.json 是 merge_backfill.py 的**派生产物**, 文件头明确写着
  "直接编辑本文件会在下次运行时被静默覆盖"。所以必须改源文件, 再重跑 merge。

诚实边界:
  - 原始英文原话**不丢**: 写入 quote_en 字段备查(证据链可追溯)。
  - 只翻译, 不改变原意, 不补充原文没有的信息。
  - 人名/机构名/货币单位/专有名词保留英文原文。
  - 翻译失败保留英文原样, 绝不手写编造。
  - 已是中文的 quote 一律不动。

用法:
  python3 scripts/translate_quotes.py --dry-run
  python3 scripts/translate_quotes.py
"""
import argparse
import glob
import json
import os
import shutil
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
API = "http://127.0.0.1:8800/v1/chat/completions"
MODEL = "gpt-4o"
REQ_GAP = 1.5      # 上游 429 限流; 串行+限速是实测最优, 勿改并发

# merge_backfill.py 的白名单(保持一致, 漏改的文件等于没改)
SRC_FILES = [
    "batch_1.json", "batch_2.json", "batch_3.json", "batch_4.json",
    "batch_5.json", "batch_6.json", "batch_extra.json", "batch_extra2.json",
    "batch_longrange.json", "batch_daily.json", "batch_fill.json",
    "batch_esoteric_finance.json",
    "new_people_batch1.json", "new_people_batch2.json",
    "new_people_batch3.json", "new_people_batch4.json",
]

SYS = (
    "你是中英翻译。把预言家/分析师的英文预测引语翻译成简体中文。\n"
    "规则:\n"
    "1. 人名、机构名、货币单位、专有名词保留英文原文"
    "(如 Martin Armstrong / EU / $11,000 原样保留)。\n"
    "2. 忠实翻译, 不增不减, 不做解释和评论。\n"
    "3. 保留原文的年份、数字、百分比。\n"
    "4. 只返回 JSON: {\"cn\": \"中文译文\"}\n"
    "5. 若原文已是中文或无法翻译, 返回 {\"cn\": \"\"}。"
)


def is_cn(s):
    return any("\u4e00" <= c <= "\u9fff" for c in str(s or ""))


def llm(text, retries=5):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": text}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }).encode()
    last = None
    for a in range(retries):
        try:
            req = urllib.request.Request(
                API, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.loads(r.read().decode())
            return d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last = e
            time.sleep(min(2 ** a, 16))
    raise RuntimeError(f"LLM 失败: {last}")


def warmup():
    for _ in range(30):
        try:
            b = json.dumps({"model": MODEL,
                            "messages": [{"role": "user", "content": "ok"}],
                            "max_tokens": 4}).encode()
            req = urllib.request.Request(
                API, data=b, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                json.loads(r.read().decode())
            return True
        except Exception:
            time.sleep(2)
    return False


def iter_preds(obj):
    """源文件有两种形状: 顶层 list, 或 {people:[...]}。统一产出 prediction dict。"""
    people = obj.get("people") if isinstance(obj, dict) else obj
    if not isinstance(people, list):
        return
    for p in people:
        if not isinstance(p, dict):
            continue
        for pr in (p.get("predictions") or []):
            if isinstance(pr, dict):
                yield p.get("display_name") or p.get("name") or "?", pr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    # 收集待翻译
    todo = []          # (path, obj, pred)
    loaded = {}
    for fn in SRC_FILES:
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            print(f"! 源文件缺失(跳过): {fn}")
            continue
        obj = json.load(open(p, encoding="utf-8"))
        loaded[p] = obj
        for name, pr in iter_preds(obj):
            q = (pr.get("quote") or "").strip()
            if q and not is_cn(q):
                todo.append((p, pr, name))

    print(f"扫描 {len(loaded)} 个源文件, 英文 quote 待翻译: {len(todo)} 条")
    if a.limit:
        todo = todo[:a.limit]

    if a.dry_run:
        for p, pr, name in todo[:8]:
            print(f"  [{name}] {(pr.get('quote') or '')[:76]}")
        print("(dry-run, 未写入)")
        return

    if not todo:
        print("无需翻译")
        return

    warmup()
    ok = fail = 0
    for i, (p, pr, name) in enumerate(todo, 1):
        src = (pr.get("quote") or "").strip()
        try:
            res = json.loads(llm(src))
            cn = str(res.get("cn") or "").strip()
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(todo)}] 失败: {str(e)[:56]}", flush=True)
            time.sleep(REQ_GAP)
            continue
        if cn and is_cn(cn):
            pr.setdefault("quote_en", src)   # 原话备查, 证据链不丢
            pr["quote"] = cn
            ok += 1
        else:
            fail += 1
        if i % 20 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] 成功 {ok} / 失败 {fail}", flush=True)
            for path, obj in loaded.items():
                shutil.copy(path, path + ".qbak")
                json.dump(obj, open(path, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
        time.sleep(REQ_GAP)

    for path, obj in loaded.items():
        shutil.copy(path, path + ".qbak")
        json.dump(obj, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    print(f"\n完成: 成功 {ok} / 失败 {fail}")
    print("下一步: python3 scripts/merge_backfill.py 重建 backfill_full.json")
    sys.exit(0)


if __name__ == "__main__":
    main()
