#!/usr/bin/env python3
"""Forecast Checker 全量 dashboard 构建器(正式版,双发布用)。
仿 Eco KOL: 莫兰迪深色配色 + KPI + 领域雷达(SVG) + 身份类型分组卡片 + 每条预言锚source_url。
自包含单文件 HTML。"""
import os, json, html, math
from collections import Counter

base = os.path.dirname(__file__)
data = json.load(open(os.path.join(base, "..", "data", "backfill_full.json")))
people = data["people"]
DOMAINS = data["_topic_domains"]
PTYPES = data["_person_types"]

PTYPE_META = {
    "灵媒通灵": ("🔮", "#b48ead"), "占星预言": ("✨", "#ebcb8b"), "预言先知": ("📜", "#d08770"),
    "遥视RV": ("👁", "#88c0d0"), "出体OBE": ("🌌", "#81a1c1"), "预知研究": ("🧪", "#a3be8c"),
}
DOMAIN_COLOR = {
    "金融经济": "#ebcb8b", "地缘军事": "#bf616a", "自然灾害": "#d08770", "科技AI未来": "#88c0d0",
    "社会政治": "#b48ead", "健康疫情": "#a3be8c", "灵性个人": "#81a1c1", "科学意识": "#8fbcbb",
}

def esc(s): return html.escape(str(s or ""))

# 领域统计(全体预言)
domain_counter = Counter()
for s in people:
    for p in s.get("predictions", []):
        domain_counter[p["domain"]] += 1

total_people = len(people)
total_preds = sum(len(s.get("predictions", [])) for s in people)
with_pred = len([s for s in people if s.get("predictions")])
alive_n = len([s for s in people if s.get("alive") and s.get("predictions")])

# ---- SVG 雷达图(8 领域) ----
def radar_svg():
    cx, cy, R = 200, 190, 140
    n = len(DOMAINS)
    maxv = max(domain_counter.values()) if domain_counter else 1
    # 网格环
    rings = ""
    for frac in [0.25, 0.5, 0.75, 1.0]:
        pts = []
        for i in range(n):
            ang = -math.pi/2 + 2*math.pi*i/n
            pts.append(f"{cx+R*frac*math.cos(ang):.1f},{cy+R*frac*math.sin(ang):.1f}")
        rings += f'<polygon points="{" ".join(pts)}" fill="none" stroke="#4c566a" stroke-width="1" opacity="0.5"/>'
    # 轴线 + 标签
    axes = ""; labels = ""
    for i, d in enumerate(DOMAINS):
        ang = -math.pi/2 + 2*math.pi*i/n
        x, y = cx+R*math.cos(ang), cy+R*math.sin(ang)
        axes += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#4c566a" stroke-width="1" opacity="0.5"/>'
        lx, ly = cx+(R+22)*math.cos(ang), cy+(R+22)*math.sin(ang)
        anchor = "middle"
        if math.cos(ang) > 0.3: anchor = "start"
        elif math.cos(ang) < -0.3: anchor = "end"
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{DOMAIN_COLOR.get(d,"#8892a6")}" font-size="12" text-anchor="{anchor}" dominant-baseline="middle">{esc(d)} {domain_counter.get(d,0)}</text>'
    # 数据多边形
    dpts = []
    for i, d in enumerate(DOMAINS):
        ang = -math.pi/2 + 2*math.pi*i/n
        frac = domain_counter.get(d,0)/maxv if maxv else 0
        dpts.append(f"{cx+R*frac*math.cos(ang):.1f},{cy+R*frac*math.sin(ang):.1f}")
    dots = ""
    for i, d in enumerate(DOMAINS):
        ang = -math.pi/2 + 2*math.pi*i/n
        frac = domain_counter.get(d,0)/maxv if maxv else 0
        dots += f'<circle cx="{cx+R*frac*math.cos(ang):.1f}" cy="{cy+R*frac*math.sin(ang):.1f}" r="3" fill="{DOMAIN_COLOR.get(d,"#b48ead")}"/>'
    poly = f'<polygon points="{" ".join(dpts)}" fill="#b48ead" fill-opacity="0.25" stroke="#b48ead" stroke-width="2"/>'
    return f'<svg viewBox="0 0 400 400" width="100%" style="max-width:440px">{rings}{axes}{poly}{dots}{labels}</svg>'

# ---- 卡片 ----
def card(s):
    icon, color = PTYPE_META.get(s["person_type"], ("🔯", "#8892a6"))
    preds = s.get("predictions", [])
    doms = [d for d in s.get("primary_domains", []) if d]
    status = "历史复核" if not preds else ("在世" if s.get("alive") else "已故")
    yrs = f' · {esc(s.get("years",""))}' if s.get("years") else ""
    dom_badges = "".join(
        f'<span class="dom-badge" style="background:{DOMAIN_COLOR.get(d,"#4c566a")}22;color:{DOMAIN_COLOR.get(d,"#8892a6")};border:1px solid {DOMAIN_COLOR.get(d,"#4c566a")}55">{esc(d)}</span>'
        for d in doms)
    if preds:
        rows = "".join(
            f'<div class="pred"><span class="pdom" style="color:{DOMAIN_COLOR.get(p["domain"],"#8892a6")}">●</span>'
            f'<a href="{esc(p["source_url"])}" target="_blank" class="ptext">{esc(p["summary"])}</a>'
            f'<span class="pdate">{esc(p.get("date",""))}</span></div>'
            for p in preds)
        body = f'<div class="preds">{rows}</div>'
    else:
        body = f'<div class="pred nostatus">{esc(s.get("note","历史复核·无新内容"))}</div>'
    return f'''<div class="card" style="border-left:4px solid {color}">
      <div class="card-hd"><span class="picon">{icon}</span>
        <span class="pname">{esc(s["display_name"])}</span>
        <span class="pregion">{esc(s.get("region",""))}{yrs}</span>
        <span class="pstatus st-{status}">{status}</span></div>
      <div class="ptype" style="color:{color}">{esc(s["person_type"])} · {len(preds)} 条预言</div>
      <div class="doms">{dom_badges}</div>{body}
    </div>'''

groups = {}
for s in people:
    groups.setdefault(s["person_type"], []).append(s)
# 每组内有预言的排前
for g in groups.values():
    g.sort(key=lambda s: -len(s.get("predictions", [])))

group_html = ""
for pt in PTYPES:
    if pt not in groups: continue
    icon, color = PTYPE_META.get(pt, ("🔯", "#8892a6"))
    cards = "".join(card(s) for s in groups[pt])
    group_html += f'''<div class="group">
      <div class="group-hd" style="color:{color}">{icon} {esc(pt)} <span class="gcount">{len(groups[pt])}</span></div>
      <div class="grid">{cards}</div></div>'''

HTML = f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Forecast Checker — 预言家看板</title>
<style>
:root{{--bg:#2e3440;--card:#3b4252;--card2:#434c5e;--text:#eceff4;--muted:#8892a6;--accent:#b48ead;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.5;padding:24px;max-width:1240px;margin:0 auto}}
h1{{font-size:26px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--muted);font-size:13px;margin-bottom:20px}}
.stats{{display:flex;gap:14px;margin-bottom:22px;flex-wrap:wrap}}
.stat{{background:var(--card);border-radius:10px;padding:12px 18px;min-width:96px}}
.stat .n{{font-size:26px;font-weight:700;color:var(--accent)}}
.stat .l{{font-size:12px;color:var(--muted)}}
.toprow{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:24px;align-items:flex-start}}
.panel{{background:var(--card);border-radius:12px;padding:18px;flex:1;min-width:300px}}
.panel-hd{{font-size:15px;font-weight:600;margin-bottom:14px}}
.dbar-row{{display:flex;align-items:center;gap:10px;margin-bottom:8px}}
.dbar-lbl{{width:82px;font-size:12.5px;text-align:right}}
.dbar-track{{flex:1;height:15px;background:var(--card2);border-radius:8px;overflow:hidden}}
.dbar-fill{{height:100%;border-radius:8px}}
.dbar-num{{width:26px;font-size:12px;color:var(--muted);text-align:right}}
.radar-wrap{{display:flex;justify-content:center;align-items:center}}
.group{{margin-bottom:26px}}
.group-hd{{font-size:17px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px}}
.gcount{{background:var(--card2);color:var(--muted);font-size:12px;padding:1px 9px;border-radius:10px;font-weight:400}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:14px}}
.card{{background:var(--card);border-radius:10px;padding:14px 16px}}
.card-hd{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}}
.picon{{font-size:18px}}
.pname{{font-size:15.5px;font-weight:700}}
.pregion{{font-size:11px;color:var(--muted);background:var(--card2);padding:1px 7px;border-radius:4px}}
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
.nostatus{{color:var(--muted);font-style:italic;font-size:12px;background:var(--card2);border-radius:6px;padding:6px 9px}}
footer{{color:var(--muted);font-size:11px;margin-top:28px;border-top:1px solid var(--card2);padding-top:14px;line-height:1.7}}
</style></head><body>
<h1>🔮 Forecast Checker — 预言家看板</h1>
<div class="sub">灵媒 · 预言家 · 出体者 · 预知未来者 内容汇总 · 双维度分组（身份类型 × 预言主题领域）· 更新 {esc(data.get("_last_updated",""))}</div>
<div class="stats">
  <div class="stat"><div class="n">{total_people}</div><div class="l">收录人物</div></div>
  <div class="stat"><div class="n">{total_preds}</div><div class="l">追溯预言</div></div>
  <div class="stat"><div class="n">{with_pred}</div><div class="l">有预言者</div></div>
  <div class="stat"><div class="n">{len(groups)}</div><div class="l">身份类型</div></div>
  <div class="stat"><div class="n">{len([d for d in DOMAINS if domain_counter.get(d)])}</div><div class="l">覆盖领域</div></div>
</div>
<div class="toprow">
  <div class="panel"><div class="panel-hd">🎯 预言主题领域雷达</div><div class="radar-wrap">{radar_svg()}</div></div>
  <div class="panel"><div class="panel-hd">📊 各领域预言条数</div>{"".join(
    f'<div class="dbar-row"><span class="dbar-lbl">{esc(d)}</span>'
    f'<div class="dbar-track"><div class="dbar-fill" style="width:{domain_counter.get(d,0)/(max(domain_counter.values()) if domain_counter else 1)*100:.0f}%;background:{DOMAIN_COLOR.get(d,"#4c566a")}"></div></div>'
    f'<span class="dbar-num">{domain_counter.get(d,0)}</span></div>' for d in DOMAINS)}</div>
</div>
{group_html}
<footer>
  📌 每条预言锚真实 source_url（点击可追溯）· 绝不编造，取不到标 status ·
  历史/已故人物仅收录 2026 及以后预言，无新内容者标「历史复核」<br>
  名册来源：Eco KOL list 非金融预言家筛选 + web 搜集补充 · 数据源类型：灵媒/占星/预言家官网、YouTube、主流媒体报道、超心理研究论文
</footer>
</body></html>'''

out_dir = os.path.join(base, "..", "dashboard")
with open(os.path.join(out_dir, "index.html"), "w") as f:
    f.write(HTML)
print("wrote dashboard/index.html", len(HTML), "chars |", total_people, "人", total_preds, "预言")
