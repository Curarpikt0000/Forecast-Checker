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

# ---- 顶部时间线：2020-2030 月刻度横轴，预言点上下交替分布 + 引线 + 原话 ----
# 定位年份取「预言指向的目标年」：优先 date 的年月；若正文(summary/quote)提到比 date 更远的
# 未来年份(2027+)，则用该远年份定位(如"约2030年北约转型"date虽标2025,应落在2030)。
# 无月份的预言也纳入(靠折叠防堆叠)，月份缺失时归到该年 6 月居中。
import re as _re_tl
_FUTURE_YR = _re_tl.compile(r"(20[2-9]\d)")

def _tl_locate(p):
    y, mo = parse_date(p.get("date", ""))
    # 正文里的未来年份
    txt = (p.get("summary", "") or "") + " " + (p.get("quote", "") or "")
    body_years = [int(v) for v in _FUTURE_YR.findall(txt) if 2020 <= int(v) <= 2035]
    # 若正文有比 date 更远的年份,改用最远的那个(预言真正指向的时间)
    if body_years:
        far = max(body_years)
        if far > (y or 0):
            return far, 0        # 用远年份,月份未知
    return y, mo

_tl_events = []
for s in people:
    for p in s.get("predictions", []):
        y, mo = _tl_locate(p)
        if y < 2020 or y > 2030:   # 时间轴范围 2020-2030
            continue
        _tl_events.append({
            "y": y,
            "mo": mo if mo else 6,   # 无月份归到年中 6 月
            "person": s.get("display_name", ""),
            "summary": p.get("summary", ""),
            "quote": p.get("quote", ""),
            "domain": p.get("domain", ""),
            "url": safe_url(p.get("source_url")),
            "approx": mo == 0,       # 标记月份是近似的
        })
_tl_events.sort(key=lambda e: (e["y"], e["mo"]))

def timeline_html():
    if not _tl_events:
        return ""
    Y0, Y1 = 2020, 2030
    total_months = (Y1 - Y0 + 1) * 12
    month_w = 26
    W = total_months * month_w
    BOX_W = 150
    LAYER_H = 46
    GAP = 8
    MAX_LAYERS = 3          # 每侧最多显示层数,超出折叠

    def month_x(y, mo):
        return ((y - Y0) * 12 + (mo - 1)) * month_w + month_w / 2

    from collections import defaultdict
    # 按 (月idx, 侧) 分组,同月同侧超过 MAX_LAYERS*可容纳数 的折叠
    evs = sorted(_tl_events, key=lambda e: (e["y"], e["mo"]))
    # 先按月分桶,同月内交替上下
    by_month = defaultdict(list)
    for e in evs:
        by_month[(e["y"], e["mo"])].append(e)

    up_layers = []
    down_layers = []
    placed = []           # (e, x, side, layer)
    hidden = defaultdict(list)   # (mi, side) -> [e,...] 折叠隐藏的事件

    for (y, mo), month_evs in sorted(by_month.items()):
        x = month_x(y, mo)
        x0, x1 = x - BOX_W / 2, x + BOX_W / 2
        mi = (y - Y0) * 12 + (mo - 1)
        up_cnt = down_cnt = 0
        for k, e in enumerate(month_evs):
            side = "up" if k % 2 == 0 else "down"
            side_layers = up_layers if side == "up" else down_layers
            # 找不重叠的层
            lyr = -1
            for li, spans in enumerate(side_layers):
                if all(x1 + GAP <= s0 or x0 - GAP >= s1 for (s0, s1) in spans):
                    lyr = li
                    break
            if lyr == -1:
                side_layers.append([])
                lyr = len(side_layers) - 1
            # 超过 MAX_LAYERS 的折叠隐藏
            if lyr >= MAX_LAYERS:
                hidden[(mi, side, x)].append(e)
            else:
                side_layers[lyr].append((x0, x1))
                placed.append((e, x, side, lyr))

    n_up = max((len(l) for l in [up_layers]), default=1)
    up_layer_ct = min(len(up_layers), MAX_LAYERS) or 1
    axis_y = 20 + up_layer_ct * LAYER_H + 30

    dots = []
    axis_ticks = []
    for m in range(total_months):
        x = m * month_w + month_w / 2
        yr = Y0 + m // 12
        mo = m % 12 + 1
        if mo == 1:
            axis_ticks.append(f'<line x1="{x:.0f}" y1="{axis_y-7}" x2="{x:.0f}" y2="{axis_y+7}" stroke="#88909e" stroke-width="1.5"/>')
            axis_ticks.append(f'<text x="{x:.0f}" y="{axis_y+24}" fill="#c8cdd6" font-size="13" font-weight="700" text-anchor="middle">{yr}</text>')
        else:
            axis_ticks.append(f'<line x1="{x:.0f}" y1="{axis_y-3}" x2="{x:.0f}" y2="{axis_y+3}" stroke="#5a6373" stroke-width="0.6"/>')

    MONTHS_CN = ["", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
    box_h = 40

    def box_svg(e, x, py, box_y):
        col = DOMAIN_COLOR.get(e["domain"], DEFAULT_COLOR)
        mtag = f'{e["y"]}年{MONTHS_CN[e["mo"]]}'
        date_html = f'<span class="tldate" style="color:{col}">{mtag}</span>'
        label = esc(e["person"]) + "：" + esc(e["summary"][:20])
        quote = esc(e["quote"][:50]) if e["quote"] else ""
        q_html = f'<div class="tlq">“{quote}”</div>' if quote else ""
        full = esc(f'{mtag} · ' + e["person"] + "：" + e["summary"] + (("  原话:" + e["quote"]) if e["quote"] else ""))
        inner = (f'<div class="tlbox" style="border-left:3px solid {col}" title="{full}">'
                 f'<div class="tlp">{date_html} {label}</div>{q_html}</div>')
        if e["url"]:
            inner = f'<a href="{e["url"]}" target="_blank" rel="noopener" style="text-decoration:none">{inner}</a>'
        return (f'<line x1="{x:.0f}" y1="{axis_y}" x2="{x:.0f}" y2="{py:.0f}" stroke="{col}" stroke-width="1" opacity="0.4"/>'
                f'<circle cx="{x:.0f}" cy="{py:.0f}" r="4" fill="{col}"/>'
                f'<foreignObject x="{x-BOX_W/2:.0f}" y="{box_y:.0f}" width="{BOX_W}" height="{box_h}" class="tlfo">{inner}</foreignObject>')

    for e, x, side, lyr in placed:
        dist = 22 + lyr * LAYER_H
        py = axis_y - dist if side == "up" else axis_y + dist
        box_y = py - box_h - 5 if side == "up" else py + 5
        dots.append(box_svg(e, x, py, box_y))

    # 折叠组:在第 MAX_LAYERS 层位置放一个 "+N" 徽章,checkbox hack 展开
    cid = 0
    extra_html = []   # 展开区(HTML,放 SVG 外)
    for (mi, side, x), hev in hidden.items():
        cid += 1
        dist = 22 + MAX_LAYERS * LAYER_H
        py = axis_y - dist if side == "up" else axis_y + dist
        by = py - 20 if side == "up" else py
        badge = (f'<foreignObject x="{x-30:.0f}" y="{by:.0f}" width="60" height="20" class="tlfo">'
                 f'<label class="tlmore" for="tlm{cid}">+{len(hev)} 更多</label></foreignObject>')
        dots.append(badge)

    n_down_ct = min(len(down_layers), MAX_LAYERS) or 1
    svg_h = axis_y + 30 + n_down_ct * LAYER_H + 30
    axis_line = f'<line x1="0" y1="{axis_y}" x2="{W}" y2="{axis_y}" stroke="#88909e" stroke-width="2"/>'
    svg = (f'<svg width="{W}" height="{svg_h:.0f}" viewBox="0 0 {W} {svg_h:.0f}" '
           f'style="min-width:{W}px">{axis_line}{"".join(axis_ticks)}{"".join(dots)}</svg>')

    # 折叠展开区:每个折叠组一个隐藏 checkbox + 展开列表(点 +N 徽章显示)
    cid = 0
    panels = []
    for (mi, side, x), hev in hidden.items():
        cid += 1
        yr = Y0 + mi // 12
        mo = mi % 12 + 1
        rows = []
        for e in hev:
            col = DOMAIN_COLOR.get(e["domain"], DEFAULT_COLOR)
            q = f' — “{esc(e["quote"][:60])}”' if e["quote"] else ""
            txt = f'<span style="color:{col}">●</span> {esc(e["person"])}：{esc(e["summary"])}{q}'
            rows.append(f'<a href="{e["url"]}" target="_blank" rel="noopener" class="tlmrow">{txt}</a>' if e["url"] else f'<div class="tlmrow">{txt}</div>')
        panels.append(
            f'<input type="checkbox" id="tlm{cid}" class="tlmchk">'
            f'<div class="tlmpanel"><div class="tlmhd">{yr}年{MONTHS_CN[mo]} · 其余 {len(hev)} 条预言</div>{"".join(rows)}</div>')

    return f'<div class="tl-scroll">{svg}</div><div class="tlmore-wrap">{"".join(panels)}</div>'

tl_span = ""
if _tl_events:
    tl_span = f"2020–2030 月刻度，{len(_tl_events)} 个事件（点=预言,颜色=领域,上下交替,点下为原话）"


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
.tl-scroll{{overflow-x:auto;overflow-y:visible;padding:10px 0 14px;background:var(--bg)}}
.tlfo{{overflow:visible}}
.tlbox{{background:var(--card2);border-radius:5px;padding:4px 7px;font-size:9.5px;line-height:1.3;height:100%;overflow:hidden;transition:all .12s;cursor:pointer;position:relative}}
.tlbox:hover{{overflow:visible;height:auto;min-height:100%;z-index:999;box-shadow:0 4px 16px rgba(0,0,0,.6);background:#4a5568;transform:scale(1.04)}}
.tldate{{font-weight:700;font-size:9px}}
.tlp{{color:var(--text);font-weight:600;margin-bottom:2px}}
.tlq{{color:var(--muted);font-style:italic;font-size:8.5px;line-height:1.25}}
.tlbox:hover .tlp,.tlbox:hover .tlq{{white-space:normal}}
foreignObject a:hover .tlbox{{background:#4a5568}}
.tlmore{{display:block;background:var(--accent);color:#fff;font-size:9px;font-weight:700;text-align:center;border-radius:9px;padding:2px 0;cursor:pointer;line-height:1.4}}
.tlmore:hover{{background:#c9a0c4}}
.tlmore-wrap{{margin-top:10px}}
.tlmchk{{display:none}}
.tlmpanel{{display:none;background:var(--card);border-radius:8px;padding:12px 14px;margin-bottom:8px}}
.tlmchk:checked + .tlmpanel{{display:block}}
.tlmhd{{font-size:13px;font-weight:700;color:var(--accent);margin-bottom:8px}}
.tlmrow{{display:block;font-size:12px;color:var(--text);text-decoration:none;padding:4px 0;border-bottom:1px solid var(--card2);line-height:1.5}}
a.tlmrow:hover{{color:var(--accent)}}
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
