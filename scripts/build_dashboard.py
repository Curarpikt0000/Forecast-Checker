#!/usr/bin/env python3
"""Forecast Checker 全量 dashboard 构建器(正式版,双发布用)。
仿 Eco KOL: 莫兰迪深色配色 + KPI + 领域雷达(SVG) + 身份类型分组卡片 + bio背景 + 每条预言锚source_url。
自包含单文件 HTML。"""
import os, json, html, math
from collections import Counter

base = os.path.dirname(__file__)
DATA_PATH = os.path.join(base, "..", "data", "backfill_full.json")
try:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    raise SystemExit(f"[build_dashboard] 数据文件不存在: {DATA_PATH} — 先跑 merge_backfill.py")
except json.JSONDecodeError as e:
    raise SystemExit(f"[build_dashboard] backfill_full.json 不是合法 JSON: {e}")

people = data.get("people", [])
if not people:
    raise SystemExit("[build_dashboard] backfill_full.json 里没有 people 数据，中止")
DOMAINS = data.get("_topic_domains", [])
PTYPES = data.get("_person_types", [])

PTYPE_META = {
    "灵媒通灵": ("🔮", "#b48ead"), "占星预言": ("✨", "#ebcb8b"), "预言先知": ("📜", "#d08770"),
    "遥视RV": ("👁", "#88c0d0"), "出体OBE": ("🌌", "#81a1c1"), "预知研究": ("🧪", "#a3be8c"),
}
DOMAIN_COLOR = {
    "金融经济": "#ebcb8b", "地缘军事": "#bf616a", "自然灾害": "#d08770", "科技AI未来": "#88c0d0",
    "社会政治": "#b48ead", "健康疫情": "#a3be8c", "灵性个人": "#81a1c1", "科学意识": "#8fbcbb",
}
DEFAULT_COLOR = "#8892a6"
GRID = "#4c566a"


def esc(s):
    return html.escape(str(s or ""))


def safe_url(u):
    """只放行 http/https 链接，其余(javascript:/data: 等)返回空，防 XSS 注入。"""
    u = str(u or "").strip()
    return esc(u) if u.lower().startswith(("http://", "https://")) else ""


import re
_MONTH_RE = re.compile(r"(\d{4})(?:[-/](\d{1,2}))?")

def parse_date(d):
    """把多样的 date 字符串解析成可排序的 (year, month) 元组。
    支持: 2026 / 2026-03 / 2025-12-23 / 2025-2030 / 约2100 / 2020s后期 / 2050/2075-2080。
    取第一个能识别的年份；无月份按 0；完全无法解析返回 (0,0)（排最后）。"""
    m = _MONTH_RE.search(str(d or ""))
    if not m:
        return (0, 0)
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else 0
    if month < 1 or month > 12:
        month = 0
    return (year, month)


# 领域统计(全体预言)
domain_counter = Counter()
for s in people:
    for p in s.get("predictions", []):
        dom = p.get("domain")
        if dom:
            domain_counter[dom] += 1

total_people = len(people)
total_preds = sum(len(s.get("predictions", [])) for s in people)
with_pred = len([s for s in people if s.get("predictions")])
maxv = max(domain_counter.values()) if domain_counter else 1


# ---- SVG 雷达图(8 领域) — 单次循环预计算所有几何 ----
def radar_svg():
    cx, cy, R = 200, 190, 140
    n = len(DOMAINS)
    if n == 0:
        return ""
    axes = []
    labels = []
    dpts = []
    dots = []
    for i, d in enumerate(DOMAINS):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        col = DOMAIN_COLOR.get(d, DEFAULT_COLOR)
        # 轴线
        ax, ay = cx + R * cos_a, cy + R * sin_a
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="{GRID}" stroke-width="1" opacity="0.5"/>')
        # 标签
        lx, ly = cx + (R + 22) * cos_a, cy + (R + 22) * sin_a
        anchor = "start" if cos_a > 0.3 else ("end" if cos_a < -0.3 else "middle")
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{col}" font-size="12" text-anchor="{anchor}" dominant-baseline="middle">{esc(d)} {domain_counter.get(d, 0)}</text>')
        # 数据点
        frac = domain_counter.get(d, 0) / maxv if maxv else 0
        px, py = cx + R * frac * cos_a, cy + R * frac * sin_a
        dpts.append(f"{px:.1f},{py:.1f}")
        dots.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{col}"/>')
    # 网格环
    rings = []
    for frac in (0.25, 0.5, 0.75, 1.0):
        pts = []
        for i in range(n):
            ang = -math.pi / 2 + 2 * math.pi * i / n
            pts.append(f"{cx + R * frac * math.cos(ang):.1f},{cy + R * frac * math.sin(ang):.1f}")
        rings.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="{GRID}" stroke-width="1" opacity="0.5"/>')
    poly = f'<polygon points="{" ".join(dpts)}" fill="#b48ead" fill-opacity="0.25" stroke="#b48ead" stroke-width="2"/>'
    return (f'<svg viewBox="0 0 400 400" width="100%" style="max-width:440px">'
            f'{"".join(rings)}{"".join(axes)}{poly}{"".join(dots)}{"".join(labels)}</svg>')


# ---- 卡片 ----
def card(s):
    icon, color = PTYPE_META.get(s.get("person_type", ""), ("🔯", DEFAULT_COLOR))
    preds = s.get("predictions", [])
    doms = [d for d in s.get("primary_domains", []) if d]
    status = "历史复核" if not preds else ("在世" if s.get("alive") else "已故")
    yrs = f' · {esc(s.get("years", ""))}' if s.get("years") else ""
    bio = s.get("bio", "")
    bio_html = f'<div class="pbio">{esc(bio)}</div>' if bio else ""
    # 评分星级(放名字后面)：rating=命中率*5(0~5)，None=待验证
    rating = s.get("rating")
    if rating is not None:
        stars = "★" * rating + "☆" * (5 - rating)
        hr = s.get("hit_rate")
        pct = f'{hr*100:.0f}%' if hr is not None else ""
        rating_html = f'<span class="prating" title="命中率 {pct}（命中{s.get("hit",0)}/未命中{s.get("miss",0)}，基于公开报道自称记录）">{stars}</span>'
    else:
        rating_html = '<span class="prating pending" title="暂无已验证的应验/未应验记录">待验证</span>'
    dom_badges = "".join(
        f'<span class="dom-badge" style="background:{DOMAIN_COLOR.get(d, GRID)}22;color:{DOMAIN_COLOR.get(d, DEFAULT_COLOR)};border:1px solid {DOMAIN_COLOR.get(d, GRID)}55">{esc(d)}</span>'
        for d in doms)
    if preds:
        # 按预言时间倒序：最后说出的排最上
        preds = sorted(preds, key=lambda p: parse_date(p.get("date", "")), reverse=True)
        rows = []
        for p in preds:
            url = safe_url(p.get("source_url"))
            dom = p.get("domain", "")
            txt = esc(p.get("summary", ""))
            # 有合法 url 才做成链接，否则纯文本（防坏链/注入）
            inner = f'<a href="{url}" target="_blank" rel="noopener" class="ptext">{txt}</a>' if url else f'<span class="ptext">{txt}</span>'
            v = p.get("verified")
            vmark = '<span class="pv-hit" title="公开报道/自称已应验">✓</span>' if v == "hit" else ('<span class="pv-miss" title="已证未应验">✗</span>' if v == "miss" else "")
            rows.append(
                f'<div class="pred"><span class="pdom" style="color:{DOMAIN_COLOR.get(dom, DEFAULT_COLOR)}">●</span>'
                f'{inner}{vmark}<span class="pdate">{esc(p.get("date", ""))}</span></div>')
        body = f'<div class="preds">{"".join(rows)}</div>'
    else:
        body = f'<div class="pred nostatus">{esc(s.get("note", "历史复核·无新内容"))}</div>'
    return f'''<div class="card" style="border-left:4px solid {color}">
      <div class="card-hd"><span class="picon">{icon}</span>
        <span class="pname">{esc(s.get("display_name", ""))}</span>{rating_html}
        <span class="pregion">{esc(s.get("region", ""))}{yrs}</span>
        <span class="pstatus st-{status}">{status}</span></div>
      <div class="ptype" style="color:{color}">{esc(s.get("person_type", ""))} · {len(preds)} 条预言</div>
      {bio_html}
      <div class="doms">{dom_badges}</div>{body}
    </div>'''


# 分组：先按 PTYPES 顺序，再兜底任何不在 PTYPES 的类型(防静默丢人)
groups = {}
for s in people:
    groups.setdefault(s.get("person_type", "其他"), []).append(s)
for g in groups.values():
    g.sort(key=lambda s: -len(s.get("predictions", [])))
ordered_types = [pt for pt in PTYPES if pt in groups] + [pt for pt in groups if pt not in PTYPES]

group_html = ""
for pt in ordered_types:
    icon, color = PTYPE_META.get(pt, ("🔯", DEFAULT_COLOR))
    cards = "".join(card(s) for s in groups[pt])
    group_html += f'''<div class="group">
      <div class="group-hd" style="color:{color}">{icon} {esc(pt)} <span class="gcount">{len(groups[pt])}</span></div>
      <div class="grid">{cards}</div></div>'''

dbars = "".join(
    f'<div class="dbar-row"><span class="dbar-lbl">{esc(d)}</span>'
    f'<div class="dbar-track"><div class="dbar-fill" style="width:{domain_counter.get(d, 0) / maxv * 100:.0f}%;background:{DOMAIN_COLOR.get(d, GRID)}"></div></div>'
    f'<span class="dbar-num">{domain_counter.get(d, 0)}</span></div>' for d in DOMAINS)

covered_domains = len([d for d in DOMAINS if domain_counter.get(d)])

# ---- 顶部时间线：所有有明确年月的预言事件，按时间轴排列 ----
# 收集 (year, month, person, summary, domain)，只要能解析出年份的
_tl_events = []
for s in people:
    for p in s.get("predictions", []):
        y, mo = parse_date(p.get("date", ""))
        if y == 0:
            continue
        _tl_events.append((y, mo, s.get("display_name", ""), p.get("summary", ""), p.get("domain", ""), safe_url(p.get("source_url"))))
# 时间正序（早→晚）
_tl_events.sort(key=lambda e: (e[0], e[1]))

# 按 年-月 桶分组
from collections import OrderedDict
_buckets = OrderedDict()
for y, mo, person, summ, dom, url in _tl_events:
    label = f"{y}" if mo == 0 else f"{y}-{mo:02d}"
    _buckets.setdefault(label, []).append((person, summ, dom, url))

def timeline_html():
    if not _buckets:
        return ""
    items = []
    for label, evs in _buckets.items():
        # 该时间点是否含 2026+（重点高亮）
        yr = int(label[:4])
        hot = " tl-hot" if yr >= 2026 else ""
        ev_html = "".join(
            f'<div class="tl-ev">'
            f'<span class="tl-dot" style="background:{DOMAIN_COLOR.get(dom, DEFAULT_COLOR)}"></span>'
            f'<span class="tl-person">{esc(person)}</span>'
            f'{"<a href=" + chr(34) + url + chr(34) + " target=" + chr(34) + "_blank" + chr(34) + " rel=" + chr(34) + "noopener" + chr(34) + " class=" + chr(34) + "tl-txt" + chr(34) + ">" + esc(summ) + "</a>" if url else "<span class=" + chr(34) + "tl-txt" + chr(34) + ">" + esc(summ) + "</span>"}'
            f'</div>'
            for person, summ, dom, url in evs)
        items.append(
            f'<div class="tl-node{hot}"><div class="tl-time">{esc(label)}'
            f'<span class="tl-cnt">{len(evs)}</span></div><div class="tl-evs">{ev_html}</div></div>')
    return f'<div class="timeline">{"".join(items)}</div>'

tl_span = ""
if _buckets:
    first, last = next(iter(_buckets)), list(_buckets)[-1]
    tl_span = f"{first} → {last}，{len(_tl_events)} 个可定位事件"


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
.prating{{font-size:12px;color:#ebcb8b;letter-spacing:1px;cursor:help}}
.prating.pending{{color:var(--muted);font-size:10px;letter-spacing:0;font-style:italic;background:var(--card2);padding:1px 6px;border-radius:4px}}
.pv-hit{{color:#a3be8c;font-size:10px;flex-shrink:0}}
.pv-miss{{color:#bf616a;font-size:10px;flex-shrink:0}}
.pregion{{font-size:11px;color:var(--muted);background:var(--card2);padding:1px 7px;border-radius:4px}}
.pstatus{{font-size:11px;padding:1px 7px;border-radius:4px;margin-left:auto}}
.st-在世{{background:#a3be8c33;color:#a3be8c}}
.st-已故{{background:#8892a633;color:#8892a6}}
.st-历史复核{{background:#ebcb8b33;color:#ebcb8b}}
.ptype{{font-size:12px;margin-bottom:6px}}
.pbio{{font-size:11.5px;color:var(--muted);background:var(--card2);border-radius:6px;padding:6px 9px;margin-bottom:8px;line-height:1.5}}
.doms{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px}}
.dom-badge{{font-size:10.5px;padding:1px 8px;border-radius:5px}}
.preds{{display:flex;flex-direction:column;gap:7px}}
.pred{{display:flex;align-items:baseline;gap:7px;font-size:12.5px;background:var(--card2);border-radius:6px;padding:6px 9px}}
.pdom{{font-size:9px;flex-shrink:0}}
.ptext{{color:var(--text);text-decoration:none;flex:1}}
a.ptext:hover{{color:var(--accent);text-decoration:underline}}
.pdate{{font-size:10.5px;color:var(--muted);flex-shrink:0}}
.nostatus{{color:var(--muted);font-style:italic;font-size:12px;background:var(--card2);border-radius:6px;padding:6px 9px}}
footer{{color:var(--muted);font-size:11px;margin-top:28px;border-top:1px solid var(--card2);padding-top:14px;line-height:1.7}}
.timeline{{display:flex;gap:0;overflow-x:auto;padding:6px 2px 14px;margin-bottom:6px}}
.tl-node{{flex:0 0 240px;border-left:2px solid var(--card2);padding:0 12px 4px 12px;position:relative}}
.tl-node::before{{content:"";position:absolute;left:-6px;top:2px;width:10px;height:10px;border-radius:50%;background:var(--muted)}}
.tl-node.tl-hot{{border-left-color:var(--accent)}}
.tl-node.tl-hot::before{{background:var(--accent)}}
.tl-time{{font-size:13px;font-weight:700;color:var(--text);margin-bottom:8px;display:flex;align-items:center;gap:6px}}
.tl-hot .tl-time{{color:var(--accent)}}
.tl-cnt{{font-size:10px;font-weight:400;color:var(--muted);background:var(--card2);padding:0 6px;border-radius:8px}}
.tl-evs{{display:flex;flex-direction:column;gap:6px}}
.tl-ev{{font-size:11px;background:var(--card);border-radius:6px;padding:5px 7px;line-height:1.4}}
.tl-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.tl-person{{font-weight:600;color:var(--text);margin-right:4px}}
.tl-txt{{color:var(--muted);text-decoration:none}}
a.tl-txt:hover{{color:var(--accent);text-decoration:underline}}
</style></head><body>
<h1>🔮 Forecast Checker — 预言家看板</h1>
<div class="sub">灵媒 · 预言家 · 出体者 · 预知未来者 内容汇总 · 双维度分组（身份类型 × 预言主题领域）· 更新 {esc(data.get("_last_updated", ""))}</div>
<div class="stats">
  <div class="stat"><div class="n">{total_people}</div><div class="l">收录人物</div></div>
  <div class="stat"><div class="n">{total_preds}</div><div class="l">追溯预言</div></div>
  <div class="stat"><div class="n">{with_pred}</div><div class="l">有预言者</div></div>
  <div class="stat"><div class="n">{len(groups)}</div><div class="l">身份类型</div></div>
  <div class="stat"><div class="n">{covered_domains}</div><div class="l">覆盖领域</div></div>
</div>
<div class="toprow">
  <div class="panel"><div class="panel-hd">🎯 预言主题领域雷达</div><div class="radar-wrap">{radar_svg()}</div></div>
  <div class="panel"><div class="panel-hd">📊 各领域预言条数</div>{dbars}</div>
</div>
<div class="panel" style="margin-bottom:24px">
  <div class="panel-hd">🕰️ 预言事件时间线 <span style="font-size:11px;color:var(--muted);font-weight:400">（{esc(tl_span)}，紫色=2026及以后，横向滚动）</span></div>
  {timeline_html()}
</div>
{group_html}
<footer>
  📌 每条预言锚真实 source_url（点击可追溯）· 绝不编造，取不到标 status ·
  历史/已故人物仅收录 2026 及以后预言，无新内容者标「历史复核」<br>
  ⭐ 评分 = 命中率（命中 ✓ ÷（命中+未命中 ✗）× 5 星）；分母仅计已可验证的预言，绝大多数 2026 未来预言为「待验证」不计分；
  命中/未命中依据 <b>公开报道或预言者自称</b>的应验记录，非独立事实核验，仅供参考<br>
  名册来源：Eco KOL list 非金融预言家筛选 + web 搜集补充 · 数据源类型：灵媒/占星/预言家官网、YouTube、主流媒体报道、超心理研究论文
</footer>
</body></html>'''

out_dir = os.path.join(base, "..", "dashboard")
with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(HTML)
print("wrote dashboard/index.html", len(HTML), "chars |", total_people, "人", total_preds, "预言")
