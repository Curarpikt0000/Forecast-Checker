#!/usr/bin/env python3
"""Forecast Checker sample dashboard 构建器。仿 Eco KOL dashboard 风格(莫兰迪配色+卡片+领域分组+雷达)。
自包含单文件 HTML。redactor 无关(纯本地数据)。"""
import os, json, html
from collections import Counter

base = os.path.dirname(__file__)
data = json.load(open(os.path.join(base, "..", "data", "sample_backfill.json")))
samples = data["samples"]
DOMAINS = data["_topic_domains"]
PTYPES = data["_person_types"]

# 身份类型中文+图标+色
PTYPE_META = {
    "灵媒通灵": ("🔮", "#b48ead"),
    "占星预言": ("✨", "#ebcb8b"),
    "预言先知": ("📜", "#d08770"),
    "遥视RV": ("👁", "#88c0d0"),
    "出体OBE": ("🌌", "#81a1c1"),
    "预知研究": ("🧪", "#a3be8c"),
}
DOMAIN_COLOR = {
    "金融经济": "#ebcb8b", "地缘军事": "#bf616a", "自然灾害": "#d08770",
    "科技AI未来": "#88c0d0", "社会政治": "#b48ead", "健康疫情": "#a3be8c",
    "灵性个人": "#81a1c1", "科学意识": "#8fbcbb",
}

def esc(s): return html.escape(str(s or ""))

# ---- 领域统计(全体) ----
domain_counter = Counter()
for s in samples:
    for p in s.get("predictions", []):
        domain_counter[p["domain"]] += 1

# ---- 卡片 ----
def card(s):
    icon, color = PTYPE_META.get(s["person_type"], ("🔯", "#8892a6"))
    preds = s.get("predictions", [])
    doms = s.get("primary_domains", [])
    status = "历史复核" if not preds else ("在世" if s.get("alive") else "已故")
    dom_badges = "".join(
        f'<span class="dom-badge" style="background:{DOMAIN_COLOR.get(d,"#4c566a")}22;color:{DOMAIN_COLOR.get(d,"#8892a6")};border:1px solid {DOMAIN_COLOR.get(d,"#4c566a")}55">{esc(d)}</span>'
        for d in doms)
    if preds:
        pred_rows = "".join(
            f'<div class="pred"><span class="pdom" style="color:{DOMAIN_COLOR.get(p["domain"],"#8892a6")}">●</span>'
            f'<a href="{esc(p["source_url"])}" target="_blank" class="ptext">{esc(p["summary"])}</a>'
            f'<span class="pdate">{esc(p["date"])}</span></div>'
            for p in preds)
    else:
        pred_rows = f'<div class="pred nostatus">{esc(s.get("status",""))}</div>'
    return f'''<div class="card" style="border-left:4px solid {color}">
      <div class="card-hd"><span class=" picon">{icon}</span>
        <span class="pname">{esc(s["display_name"])}</span>
        <span class="pregion">{esc(s.get("region",""))}</span>
        <span class="pstatus st-{status}">{status}</span></div>
      <div class="ptype" style="color:{color}">{esc(s["person_type"])} · {len(preds)} 条预言</div>
      <div class="doms">{dom_badges}</div>
      <div class="preds">{pred_rows}</div>
    </div>'''

# 按身份类型分组
groups = {}
for s in samples:
    groups.setdefault(s["person_type"], []).append(s)

group_html = ""
for pt in PTYPES:
    if pt not in groups: continue
    icon, color = PTYPE_META.get(pt, ("🔯", "#8892a6"))
    cards = "".join(card(s) for s in groups[pt])
    group_html += f'''<div class="group">
      <div class="group-hd" style="color:{color}">{icon} {esc(pt)} <span class="gcount">{len(groups[pt])}</span></div>
      <div class="grid">{cards}</div></div>'''

# 领域分布条
maxd = max(domain_counter.values()) if domain_counter else 1
dom_bars = "".join(
    f'<div class="dbar-row"><span class="dbar-lbl">{esc(d)}</span>'
    f'<div class="dbar-track"><div class="dbar-fill" style="width:{domain_counter.get(d,0)/maxd*100:.0f}%;background:{DOMAIN_COLOR.get(d,"#4c566a")}"></div></div>'
    f'<span class="dbar-num">{domain_counter.get(d,0)}</span></div>'
    for d in DOMAINS)

total_preds = sum(len(s.get("predictions", [])) for s in samples)
HTML = f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Forecast Checker — 预言家看板 (Sample)</title>
<style>
:root{{--bg:#2e3440;--card:#3b4252;--card2:#434c5e;--text:#eceff4;--muted:#8892a6;--accent:#b48ead;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.5;padding:24px;max-width:1200px;margin:0 auto}}
h1{{font-size:24px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--muted);font-size:13px;margin-bottom:20px}}
.stats{{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}}
.stat{{background:var(--card);border-radius:10px;padding:12px 18px;min-width:100px}}
.stat .n{{font-size:26px;font-weight:700;color:var(--accent)}}
.stat .l{{font-size:12px;color:var(--muted)}}
.panel{{background:var(--card);border-radius:12px;padding:18px;margin-bottom:24px}}
.panel-hd{{font-size:15px;font-weight:600;margin-bottom:14px}}
.dbar-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.dbar-lbl{{width:88px;font-size:12.5px;color:var(--text);text-align:right}}
.dbar-track{{flex:1;height:16px;background:var(--card2);border-radius:8px;overflow:hidden}}
.dbar-fill{{height:100%;border-radius:8px;transition:width .4s}}
.dbar-num{{width:28px;font-size:12px;color:var(--muted);text-align:right}}
.group{{margin-bottom:28px}}
.group-hd{{font-size:17px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px}}
.gcount{{background:var(--card2);color:var(--muted);font-size:12px;padding:1px 9px;border-radius:10px;font-weight:400}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}}
.card{{background:var(--card);border-radius:10px;padding:14px 16px}}
.card-hd{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}}
.picon{{font-size:18px}}
.pname{{font-size:15.5px;font-weight:700}}
.pregion{{font-size:11.5px;color:var(--muted);background:var(--card2);padding:1px 7px;border-radius:4px}}
.pstatus{{font-size:11px;padding:1px 7px;border-radius:4px;margin-left:auto}}
.st-在世{{background:#a3be8c33;color:#a3be8c}}
.st-已故{{background:#8892a633;color:#8892a6}}
.st-历史复核{{background:#ebcb8b33;color:#ebcb8b}}
.ptype{{font-size:12px;margin-bottom:8px}}
.doms{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px}}
.dom-badge{{font-size:10.5px;padding:1px 8px;border-radius:5px}}
.preds{{display:flex;flex-direction:column;gap:7px}}
.pred{{display:flex;align-items:baseline;gap:7px;font-size:12.5px;background:var(--card2);border-radius:6px;padding:6px 9px}}
.pdom{{font-size:9px;flex-shrink:0}}
.ptext{{color:var(--text);text-decoration:none;flex:1}}
.ptext:hover{{color:var(--accent);text-decoration:underline}}
.pdate{{font-size:10.5px;color:var(--muted);flex-shrink:0}}
.nostatus{{color:var(--muted);font-style:italic}}
footer{{color:var(--muted);font-size:11px;margin-top:28px;border-top:1px solid var(--card2);padding-top:14px}}
</style></head><body>
<h1>🔮 Forecast Checker — 预言家看板</h1>
<div class="sub">灵媒 · 预言家 · 出体者 · 预知未来者 内容汇总 · <b>SAMPLE 示范</b>（6 人 / 双维度分组：身份类型 × 预言主题领域）· 2026-08-18</div>
<div class="stats">
  <div class="stat"><div class="n">{len(samples)}</div><div class="l">Sample 人物</div></div>
  <div class="stat"><div class="n">{total_preds}</div><div class="l">已 backfill 预言</div></div>
  <div class="stat"><div class="n">{len(groups)}</div><div class="l">身份类型</div></div>
  <div class="stat"><div class="n">{len([d for d in DOMAINS if domain_counter.get(d)])}</div><div class="l">覆盖主题领域</div></div>
</div>
<div class="panel"><div class="panel-hd">📊 预言主题领域分布（全体 sample）</div>{dom_bars}</div>
{group_html}
<footer>Sample 示范 · 每条预言锚真实 source_url（点击可追溯）· 全量名册 56 人待定稿后 backfill · 数据源: Eco KOL list 筛选 + web 搜集 · 绝不编造，取不到标 status</footer>
</body></html>'''

out = os.path.join(base, "..", "dashboard", "sample.html")
with open(out, "w") as f:
    f.write(HTML)
print("wrote", out, len(HTML), "chars")
