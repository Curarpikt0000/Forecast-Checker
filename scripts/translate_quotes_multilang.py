#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补漏: translate_quotes.py 剩下的**非英文**引语(Chao 2026-08-22)。

为什么需要这个脚本:
  主脚本 SYS 写死"把**英文**预测引语翻译成简体中文", 模型遇到
  西班牙语(Mhoni Vidente / Jimena La Torre)、印尼语(Denny Darko)、
  俄语(Pavel Globa) 一律判为"非英文 -> 无法翻译", 返回 {"cn": ""},
  主脚本记为失败。这里改成**多语种**且禁止返空的 prompt。

诚实边界: 与主脚本一致 —— 只译不改意, 人名/机构名/货币单位保留原文,
  原话写入 quote_en 备查, 译文校验必须含中文才写入, 失败保留原样,
  绝不手写编造。
"""
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
REQ_GAP = 3.0

SRC_FILES = [
    "batch_1.json", "batch_2.json", "batch_3.json", "batch_4.json",
    "batch_5.json", "batch_6.json", "batch_extra.json", "batch_extra2.json",
    "batch_longrange.json", "batch_daily.json", "batch_fill.json",
    "batch_esoteric_finance.json",
    "new_people_batch1.json", "new_people_batch2.json",
    "new_people_batch3.json", "new_people_batch4.json",
]

SYS = (
    "你是多语种翻译。把用户给的文本翻译成简体中文。\n"
    "输入语言可能是英语、西班牙语、印尼语、俄语、葡萄牙语等任意语言"
    "——不论哪种语言都必须翻译。\n"
    "规则:\n"
    "1. 人名、地名、机构名、货币单位、专有名词保留原文\n"
    "   (如 Ciudad de Mexico / $11,000 原样保留)。\n"
    "2. 忠实翻译, 不增不减, 不做解释和评论。\n"
    "3. 保留原文的年份、数字、百分比和省略号。\n"
    "4. **禁止返回空字符串**。任何非中文输入都要给出中文译文。\n"
    "5. 只返回 JSON: {\"cn\": \"中文译文\"}"
)


def is_cn(s):
    return any("\u4e00" <= c <= "\u9fff" for c in str(s or ""))


def llm(text, retries=6):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYS},
                     {"role": "user", "content": text}],
        "temperature": 0.2,
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
            time.sleep(min(2 ** a, 20))
    raise RuntimeError(f"LLM 失败: {last}")


def iter_preds(obj):
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
    todo, loaded = [], {}
    for fn in SRC_FILES:
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            continue
        obj = json.load(open(p, encoding="utf-8"))
        loaded[p] = obj
        for name, pr in iter_preds(obj):
            q = (pr.get("quote") or "").strip()
            if q and not is_cn(q):
                todo.append((p, pr, name))

    print(f"待补漏(非中文引语): {len(todo)} 条", flush=True)
    if not todo:
        print("无需补漏")
        return

    ok = fail = 0
    for i, (p, pr, name) in enumerate(todo, 1):
        src = (pr.get("quote") or "").strip()
        try:
            cn = str(json.loads(llm(src)).get("cn") or "").strip()
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(todo)}] 失败: {str(e)[:56]}", flush=True)
            time.sleep(REQ_GAP)
            continue
        if cn and is_cn(cn):
            pr.setdefault("quote_en", src)   # 原话备查, 证据链不丢
            pr["quote"] = cn
            ok += 1
            print(f"  [{i}/{len(todo)}] OK [{name}]", flush=True)
        else:
            fail += 1
            print(f"  [{i}/{len(todo)}] 空译文, 保留原文 [{name}]", flush=True)
        if i % 5 == 0 or i == len(todo):
            for path, obj in loaded.items():
                shutil.copy(path, path + ".ml.bak")
                json.dump(obj, open(path, "w", encoding="utf-8"),
                          ensure_ascii=False, indent=2)
        time.sleep(REQ_GAP)

    for path, obj in loaded.items():
        shutil.copy(path, path + ".ml.bak")
        json.dump(obj, open(path, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    print(f"\n完成: 成功 {ok} / 失败 {fail}")
    print("下一步: python3 scripts/merge_backfill.py")
    sys.exit(0)


if __name__ == "__main__":
    main()
