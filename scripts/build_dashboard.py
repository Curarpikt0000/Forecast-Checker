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
    "模型预测者": ("📊", "#5e81ac"),
    # 2026-08-22 从 Eco-and-Volatility-Checker 迁入的金融玄学/术数派（Chao 裁定）
    "金融玄学/术数预测": ("☯", "#c9a227"),
}
DOMAIN_COLOR = {
    "金融经济": "#ebcb8b", "地缘军事": "#bf616a", "自然灾害": "#d08770", "科技AI未来": "#88c0d0",
    "社会政治": "#b48ead", "健康疫情": "#a3be8c", "灵性个人": "#81a1c1", "科学意识": "#8fbcbb",
    "金融市场": "#d3a625",
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
# 人物卡片锚点：用 people 列表序号生成确定性 id（不能用 hash()，每次运行都变会让 git diff 抖动）。
# 「最新收录」列表里的人名靠这张表跳到对应卡片。
_PANCHOR = {}
for _pi, _ps in enumerate(people):
    _pnm = _ps.get("display_name", "")
    if _pnm and _pnm not in _PANCHOR:
        _PANCHOR[_pnm] = f"pc{_pi + 1}"


def card(s):
    icon, color = PTYPE_META.get(s.get("person_type", ""), ("🔯", DEFAULT_COLOR))
    preds = s.get("predictions", [])
    doms = [d for d in s.get("primary_domains", []) if d]
    status = "历史复核" if not preds else ("在世" if s.get("alive") else "已故")
    yrs = f' · {esc(s.get("years", ""))}' if s.get("years") else ""
    bio = s.get("bio", "")
    bio_long = (s.get("bio_long") or "").strip()
    # 人物背景板块：有长背景则做成可展开(第一级=短简介,点开=完整背景);
    # 老数据只有短 bio 时优雅降级为纯文本,不出现空的展开箭头。
    if bio_long and bio_long != bio.strip():
        # bio_long 通常以短 bio 原句开头（11/11 人如此），展开层若照抄会读到重复两遍。
        # 这里在渲染层剥掉重复前缀，只展示"增量背景"；数据层 SSOT 保持完整不动。
        _b = bio.strip()
        extra = bio_long
        if _b and bio_long.startswith(_b):
            extra = bio_long[len(_b):].lstrip(" 　，,。;；、\n\t")
        if not extra:
            extra = bio_long
        bio_html = (f'<details class="pbio-wrap"><summary class="pbio-sum">'
                    f'<span class="pbio-txt">{esc(bio)}</span>'
                    f'<span class="pbio-more">人物背景</span></summary>'
                    f'<div class="pbio-full">{esc(extra)}</div></details>')
    elif bio:
        bio_html = f'<div class="pbio">{esc(bio)}</div>'
    else:
        bio_html = ""
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
        # ---- 卡片两个明确时间点 ----
        # ①卡片取值时间 = 该人所有预言里最新的收录入库日(真实,无则显示 —)
        # ②预测目标时间点 = 该人预言指向的目标年跨度(单一年份则只显一个)
        _cols = sorted({p.get("collected_on") for p in preds if p.get("collected_on")})
        _cv = _cols[-1] if _cols else "—"
        _tys = sorted({p["target_year"] for p in preds if p.get("target_year")})
        if _tys:
            _tv = str(_tys[0]) if len(_tys) == 1 else f"{_tys[0]}–{_tys[-1]}"
        else:
            _tv = "—"
        ctimes = (f'<div class="ctimes">'
                  f'<span class="ct ct-collect" title="本卡片数据最近一次抓取入库的真实日期">📥 取值 {esc(_cv)}</span>'
                  f'<span class="ct ct-target" title="该预言家预言所指向的目标时间点跨度">🎯 预测目标 {esc(_tv)}</span>'
                  f'</div>')
        rows = []
        for p in preds:
            url = safe_url(p.get("source_url"))
            dom = p.get("domain", "")
            txt = esc(p.get("summary", ""))
            v = p.get("verified")
            vmark = '<span class="pv-hit" title="公开报道/自称已应验">✓ 已核实</span>' if v == "hit" else ('<span class="pv-miss" title="已证未应验">✗ 未应验</span>' if v == "miss" else "")
            # 元数据下沉到正文下方一条小字带，正文独占整宽
            metas = []
            if p.get("date"):
                metas.append(f'<span class="pm pm-said" title="发表时间">🗣 {esc(p.get("date", ""))}</span>')
            if p.get("target_year"):
                metas.append(f'<span class="pm pm-target" title="这条预言指向的目标时间点">🎯 {esc(str(p["target_year"]))}</span>')
            if dom:
                metas.append(f'<span class="pm pm-dom" style="color:{DOMAIN_COLOR.get(dom, DEFAULT_COLOR)}">{esc(dom)}</span>')
            metabar = f'<div class="pmetabar">{"".join(metas)}{vmark}</div>' if (metas or vmark) else ""
            head = (f'<span class="pdot" style="background:{DOMAIN_COLOR.get(dom, DEFAULT_COLOR)}"></span>'
                    f'<span class="ptext">{txt}</span>')
            # 第三级：单条点开 = 具体说了什么(detail 原文要点) + 原话引用 + 出处链接
            detail = (p.get("detail") or "").strip()
            quote = (p.get("quote") or "").strip()
            src_link = f'<a href="{url}" target="_blank" rel="noopener" class="pd-src">查看原始出处 ↗</a>' if url else '<span class="pd-src pd-nosrc">无可用出处链接</span>'
            inner = ""
            if detail:
                inner += f'<div class="pd-detail">{esc(detail)}</div>'
            if quote:
                inner += f'<div class="pd-quote">“{esc(quote)}”</div>'
            if not inner:
                # 无 detail 的老数据：展开区优雅降级，展示已有信息而非空白
                bits = []
                if p.get("date"):
                    bits.append(f'发表于 {esc(p.get("date", ""))}')
                if p.get("target_year"):
                    bits.append(f'指向 {esc(str(p["target_year"]))} 年')
                if dom:
                    bits.append(f'领域：{esc(dom)}')
                tail = "；".join(bits)
                inner = (f'<div class="pd-detail pd-thin">暂无二次核实的详情摘要。'
                         f'{("本条信息：" + tail + "。") if tail else ""}可点下方出处链接查看原始报道。</div>')
            # 所有行统一为可展开 <details>，绝不混用长得一样但点不开的行
            rows.append(f'<details class="pred pred-x"><summary class="pred-sum">'
                        f'<span class="pred-main">{head}{metabar}</span>'
                        f'<span class="pd-more">详情</span></summary>'
                        f'<div class="pd-body">{inner}{src_link}</div></details>')
        # 第二级：默认只露最新 2 条，其余折叠（按时间倒序，最后说出的在最上）
        HEAD_N = 2
        if len(rows) > HEAD_N:
            visible = "".join(rows[:HEAD_N])
            hidden = "".join(rows[HEAD_N:])
            more = (f'<details class="pmore"><summary class="pmore-sum">'
                    f'▾ 展开其余 {len(rows) - HEAD_N} 条 · 共 {len(rows)} 条按时间倒序</summary>'
                    f'<div class="preds pmore-list">{hidden}</div></details>')
            body = ctimes + f'<div class="preds">{visible}</div>' + more
        else:
            body = ctimes + f'<div class="preds">{"".join(rows)}</div>'
    else:
        body = f'<div class="pred nostatus">{esc(s.get("note", "历史复核·无新内容"))}</div>'
    return f'''<div class="card" id="{_PANCHOR.get(s.get("display_name", ""), "")}" style="border-left:4px solid {color}">
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
_nav_groups = []          # 侧栏「身份类型」条目: (锚点id, 图标, 名称, 颜色, 人数)
for _gi, pt in enumerate(ordered_types):
    icon, color = PTYPE_META.get(pt, ("🔯", DEFAULT_COLOR))
    cards = "".join(card(s) for s in groups[pt])
    # 锚点 id 用序号,确定性(不能用 hash():字符串 hash 每次运行都变,会让 id 和 git diff 抖动)
    _gid = f"g{_gi + 1}"
    _nav_groups.append((_gid, icon, pt, color, len(groups[pt])))
    group_html += f'''<div class="group" id="{_gid}">
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

# ---- 🆕 最新收录言论：按 collected_on(真实入库日) 分当天/近7天/近30天三档 ----
# collected_on 口径:该条预言被本项目抓取入库的真实日期(历史条目取 batch 文件 git 首次提交日,
# 每日增量取 cron 抓取当天)。无该字段的条目不进本板块,不猜测。
from datetime import datetime as _dt, timezone as _tz, timedelta as _td

_JST = _tz(_td(hours=9))
_TODAY = _dt.now(_JST).date()


def _pdate(s):
    try:
        return _dt.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


_latest = []
for s in people:
    for p in s.get("predictions", []):
        c = _pdate(p.get("collected_on"))
        if not c:
            continue
        _latest.append({
            "age": (_TODAY - c).days,
            "collected": c.isoformat(),
            "person": s.get("display_name", ""),
            "ptype": s.get("person_type", ""),
            "region": s.get("region", ""),
            "summary": p.get("summary", ""),
            "domain": p.get("domain", ""),
            "said": p.get("date", ""),
            "target": p.get("target_year"),
            "url": safe_url(p.get("source_url")),
            "anchor": _PANCHOR.get(s.get("display_name", ""), ""),
        })
_latest.sort(key=lambda e: (e["age"], e["person"]))

_BUCKETS = [("d1", "当天", 0), ("d7", "过去一周", 7), ("d30", "过去一个月", 30)]


def _latest_row(e):
    col = DOMAIN_COLOR.get(e["domain"], DEFAULT_COLOR)
    icon, _ = PTYPE_META.get(e["ptype"], ("🔯", DEFAULT_COLOR))
    txt = esc(e["summary"])
    inner = (f'<a href="{e["url"]}" target="_blank" rel="noopener" class="nl-txt">{txt}</a>'
             if e["url"] else f'<span class="nl-txt">{txt}</span>')
    tgt = f'<span class="nl-t nl-target" title="预言指向的目标时间点">🎯 目标 {e["target"]}</span>' if e["target"] else ""
    said = f'<span class="nl-t" title="预言发表时间">🗣 说于 {esc(e["said"])}</span>' if e["said"] else ""
    # 人名可点：跳到该人卡片并自动展开其全部言论（倒序）
    if e["anchor"]:
        nm = (f'<a class="nl-name nl-jump" href="#{e["anchor"]}" '
              f'onclick="return goPerson(\'{e["anchor"]}\')" '
              f'title="跳到该人物卡片并展开全部言论">{esc(e["person"])}</a>')
    else:
        nm = f'<span class="nl-name">{esc(e["person"])}</span>'
    return (f'<div class="nl-row" data-pt="{esc(e["ptype"])}" data-dom="{esc(e["domain"])}">'
            f'<div class="nl-hd"><span class="nl-ic">{icon}</span>{nm}'
            f'<span class="nl-type" style="color:{col}">{esc(e["ptype"])}</span>'
            f'<span class="nl-dom" style="background:{col}22;color:{col};border:1px solid {col}55">{esc(e["domain"])}</span>'
            f'<span class="nl-reg">{esc(e["region"])}</span></div>'
            f'<div class="nl-body">{inner}</div>'
            f'<div class="nl-times">{said}{tgt}'
            f'<span class="nl-t nl-collect" title="本项目抓取入库的真实日期">📥 收录 {e["collected"]}</span></div>'
            f'</div>')


def _filter_bar():
    """身份类型 / 领域 两排筛选按钮。计数按当前全量 _latest 统计，点击后前端按 data 属性过滤。"""
    pt_cnt, dom_cnt = {}, {}
    for e in _latest:
        if e["ptype"]:
            pt_cnt[e["ptype"]] = pt_cnt.get(e["ptype"], 0) + 1
        if e["domain"]:
            dom_cnt[e["domain"]] = dom_cnt.get(e["domain"], 0) + 1
    pts = [p for p in PTYPES if p in pt_cnt] + [p for p in pt_cnt if p not in PTYPES]
    dms = [d for d in DOMAINS if d in dom_cnt] + [d for d in dom_cnt if d not in DOMAINS]
    pb = ['<button class="fb on" data-k="pt" data-v="" onclick="nlFilter(\'pt\',\'\')">全部 '
          f'<span class="nl-cnt">{len(_latest)}</span></button>']
    for p in pts:
        ic, cl = PTYPE_META.get(p, ("🔯", DEFAULT_COLOR))
        pb.append(f'<button class="fb" data-k="pt" data-v="{esc(p)}" style="--fc:{cl}" '
                  f'onclick="nlFilter(\'pt\',\'{esc(p)}\')">{ic} {esc(p)} '
                  f'<span class="nl-cnt">{pt_cnt[p]}</span></button>')
    db = ['<button class="fb on" data-k="dom" data-v="" onclick="nlFilter(\'dom\',\'\')">全部 '
          f'<span class="nl-cnt">{len(_latest)}</span></button>']
    for d in dms:
        cl = DOMAIN_COLOR.get(d, DEFAULT_COLOR)
        db.append(f'<button class="fb" data-k="dom" data-v="{esc(d)}" style="--fc:{cl}" '
                  f'onclick="nlFilter(\'dom\',\'{esc(d)}\')">{esc(d)} '
                  f'<span class="nl-cnt">{dom_cnt[d]}</span></button>')
    return (f'<div class="fbar"><span class="fbar-lbl">身份类型</span>'
            f'<div class="fbar-btns">{"".join(pb)}</div></div>'
            f'<div class="fbar"><span class="fbar-lbl">预言领域</span>'
            f'<div class="fbar-btns">{"".join(db)}</div></div>'
            f'<div class="fbar-stat" id="fbar-stat"></div>')


def latest_html():
    if not _latest:
        return ""
    tabs, panes = [], []
    for i, (key, label, days) in enumerate(_BUCKETS):
        items = [e for e in _latest if e["age"] <= days]
        act = " on" if i == 1 else ""      # 默认展示「过去一周」
        tabs.append(f'<button class="nl-tab{act}" data-t="{key}" onclick="nlSel(\'{key}\')">'
                    f'{label} <span class="nl-cnt">{len(items)}</span></button>')
        if items:
            body = "".join(_latest_row(e) for e in items)
        else:
            body = ('<div class="nl-empty">该时间跨度内无新收录言论。'
                    '（收录时间 = 本项目抓取入库日，非预言发表日；无记录即为未抓到，不做推测）</div>')
        panes.append(f'<div class="nl-pane{act}" id="nl-{key}">{body}</div>')
    return (f'<div class="nl-tabs">{"".join(tabs)}</div>{_filter_bar()}{"".join(panes)}'
            '<script>'
            'var NLF={pt:"",dom:""};'
            'function nlApply(){'
            'document.querySelectorAll(".fb").forEach(function(b){'
            'b.classList.toggle("on",NLF[b.dataset.k]===b.dataset.v);});'
            'var shown=0,tot=0;'
            'document.querySelectorAll(".nl-pane.on .nl-row").forEach(function(r){'
            'tot++;'
            'var ok=(!NLF.pt||r.dataset.pt===NLF.pt)&&(!NLF.dom||r.dataset.dom===NLF.dom);'
            'r.style.display=ok?"":"none";if(ok){shown++;}});'
            'var s=document.getElementById("fbar-stat");'
            'if(s){s.textContent=(NLF.pt||NLF.dom)?("筛选后显示 "+shown+" / "+tot+" 条"):("共 "+tot+" 条");}'
            '}'
            'function nlFilter(k,v){NLF[k]=(NLF[k]===v?"":v);nlApply();}'
            'function nlSel(k){'
            'document.querySelectorAll(".nl-tab").forEach(function(b){b.classList.toggle("on",b.dataset.t===k);});'
            'document.querySelectorAll(".nl-pane").forEach(function(p){p.classList.toggle("on",p.id==="nl-"+k);});'
            'nlApply();'
            '}'
            'function goPerson(id){'
            'var c=document.getElementById(id);if(!c){return true;}'
            'c.querySelectorAll("details").forEach(function(d){d.open=true;});'
            'c.scrollIntoView({behavior:"smooth",block:"start"});'
            'c.classList.add("card-hi");'
            'setTimeout(function(){c.classList.remove("card-hi");},2600);'
            'return false;'
            '}'
            'document.addEventListener("DOMContentLoaded",nlApply);'
            '</script>')


def sidebar_html():
    """左侧固定导航：概览各板块 + 身份类型分组，滚动时自动高亮当前所在区块。"""
    items = [
        ("sec-top", "📊", "总览指标", "var(--accent)", ""),
        ("sec-radar", "🎯", "领域雷达", "#88c0d0", ""),
        ("sec-latest", "🆕", "最新收录", "#a3be8c", str(len(_latest))),
        ("sec-timeline", "🕰️", "事件时间线", "#b48ead", str(len(_tl_events))),
    ]
    items += [(gid, icon, pt, color, str(n)) for gid, icon, pt, color, n in _nav_groups]
    lis = []
    for sid, icon, label, color, cnt in items:
        badge = f'<span class="nv-c">{cnt}</span>' if cnt else ""
        lis.append(f'<a class="nv-i" href="#{sid}" data-s="{sid}" '
                   f'style="--nvc:{color}"><span class="nv-ic">{icon}</span>'
                   f'<span class="nv-l">{esc(label)}</span>{badge}</a>')
    return f'''<nav class="sidebar" id="sidebar">
  <div class="nv-hd">🔮 导航</div>
  <div class="nv-list">{"".join(lis)}</div>
  <a class="nv-top" href="#sec-top">↑ 回到顶部</a>
</nav>
<button class="nv-toggle" id="nvToggle" onclick="document.body.classList.toggle('nv-open')" title="展开/收起导航">☰</button>'''


def sidebar_js():
    """滚动高亮脚本。必须放在页面末尾输出：侧栏本身在 <body> 开头，
    若脚本跟着侧栏一起输出，此刻后面的 section 尚未解析，
    getElementById 全拿到 null，监听器会静默失效（踩过这个坑）。"""
    return '''<script>
(function(){
  var links = Array.prototype.slice.call(document.querySelectorAll(".nv-i"));
  var secs = links.map(function(a){ return document.getElementById(a.dataset.s); });
  function setActive(i){
    links.forEach(function(a,j){ a.classList.toggle("on", i===j); });
    var cur = links[i];
    if(cur){
      var box = document.querySelector(".nv-list");
      if(box && box.scrollHeight > box.clientHeight){
        var t = cur.offsetTop - box.offsetTop, h = cur.offsetHeight;
        if(t < box.scrollTop) box.scrollTop = t - 8;
        else if(t + h > box.scrollTop + box.clientHeight) box.scrollTop = t + h - box.clientHeight + 8;
      }
    }
  }
  function onScroll(){
    var y = window.scrollY + 140, idx = 0;
    for(var k=0;k<secs.length;k++){ if(secs[k] && secs[k].offsetTop <= y) idx = k; }
    if(window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) idx = secs.length - 1;
    setActive(idx);
  }
  var tick = false;
  window.addEventListener("scroll", function(){
    if(tick) return; tick = true;
    requestAnimationFrame(function(){ onScroll(); tick = false; });
  }, {passive:true});
  links.forEach(function(a){
    a.addEventListener("click", function(e){
      var el = document.getElementById(a.dataset.s);
      if(!el) return;
      e.preventDefault();
      window.scrollTo({top: el.offsetTop - 20, behavior:"smooth"});
      document.body.classList.remove("nv-open");
    });
  });
  onScroll();
})();
</script>'''


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
/* ---- 左侧固定导航 ---- */
.sidebar{{position:fixed;top:0;left:0;width:228px;height:100vh;background:#12131c;
  border-right:1px solid #232433;padding:20px 0 16px;display:flex;flex-direction:column;z-index:50}}
.nv-hd{{font-size:14px;font-weight:700;color:#f2f4fa;padding:0 18px 14px;
  border-bottom:1px solid #232433;margin-bottom:12px;letter-spacing:.3px}}
.nv-list{{flex:1;overflow-y:auto;padding:0 10px;scrollbar-width:thin}}
.nv-list::-webkit-scrollbar{{width:6px}}
.nv-list::-webkit-scrollbar-thumb{{background:#2f3142;border-radius:3px}}
/* 参考图样式(Chao 2026-08-21): 行间留白 + 圆角 hit area + 右对齐数字徽章,
   选中态为整行浅紫圆角块(不再用左侧竖条)。 */
.nv-i{{display:flex;align-items:center;gap:11px;padding:10px 12px;margin-bottom:6px;
  border-radius:10px;text-decoration:none;color:#9aa1b8;font-size:13px;
  transition:background .15s,color .15s}}
.nv-i:hover{{background:#1c1e2b;color:#dfe4f2}}
.nv-i.on{{background:#352c52;color:#ffffff;font-weight:600}}
.nv-ic{{font-size:15px;flex-shrink:0;width:18px;text-align:center}}
.nv-l{{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.nv-c{{font-size:11px;color:#8b93a8;background:#1e2030;padding:2px 8px;border-radius:10px;
  flex-shrink:0;min-width:26px;text-align:center}}
.nv-i.on .nv-c{{background:#3a3157;color:#cbb8ee}}
.nv-top{{margin:10px 18px 0;padding-top:12px;border-top:1px solid #232433;
  font-size:12px;color:#8b93a8;text-decoration:none}}
.nv-top:hover{{color:#88c0d0}}
.nv-toggle{{display:none;position:fixed;top:12px;left:12px;z-index:60;background:#3b4252;
  color:#eceff4;border:1px solid #4c566a;border-radius:8px;width:38px;height:38px;
  font-size:16px;cursor:pointer}}
@media(max-width:1100px){{
  .sidebar{{transform:translateX(-100%);transition:transform .2s}}
  body.nv-open .sidebar{{transform:none}}
  .nv-toggle{{display:block}}
}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.5;padding:24px 24px 24px 252px;max-width:1476px;margin:0 auto}}
@media(max-width:1100px){{ body{{padding:64px 18px 24px}} }}
h1{{font-size:26px;font-weight:700;margin-bottom:4px}}
.sub{{color:var(--muted);font-size:13px;margin-bottom:20px}}
.stats{{display:flex;gap:14px;margin-bottom:22px;flex-wrap:wrap}}
.stat{{background:var(--card);border-radius:10px;padding:12px 18px;min-width:96px}}
.stat .n{{font-size:26px;font-weight:700;color:var(--accent)}}
.stat .l{{font-size:12px;color:var(--muted)}}
.toprow{{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:24px;align-items:flex-start}}
.panel{{background:var(--card);border-radius:12px;padding:18px;flex:1;min-width:300px}}
.panel-hd{{font-size:15px;font-weight:600;margin-bottom:14px}}
/* 🆕 最新收录言论板块 */
.nl-tabs{{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}}
.nl-tab{{background:#333b4d;color:#c3cadb;border:1px solid #4c566a;border-radius:16px;
  padding:6px 15px;font-size:12.5px;cursor:pointer;font-family:inherit;transition:.15s}}
.nl-tab:hover{{border-color:#88c0d0}}
.nl-tab.on{{background:#88c0d022;color:#88c0d0;border-color:#88c0d0;font-weight:600}}
.nl-cnt{{opacity:.7;font-size:11px;margin-left:3px}}
/* 筛选按钮条：身份类型 / 预言领域 */
.fbar{{display:flex;align-items:flex-start;gap:10px;margin:0 0 8px}}
.fbar-lbl{{flex:0 0 56px;font-size:11.5px;color:#8e97a8;padding-top:6px;letter-spacing:.5px}}
.fbar-btns{{display:flex;gap:6px;flex-wrap:wrap;flex:1}}
.fb{{background:#2f3646;color:#aab3c4;border:1px solid #414b60;border-radius:14px;
     padding:4px 10px;font-size:11.5px;cursor:pointer;transition:.15s;--fc:#88c0d0}}
.fb:hover{{border-color:var(--fc);color:#e5e9f0}}
.fb.on{{background:color-mix(in srgb,var(--fc) 14%,transparent);color:var(--fc);
        border-color:var(--fc);font-weight:600}}
.fbar-stat{{font-size:11.5px;color:#8e97a8;margin:2px 0 10px 66px}}
/* 从最新收录跳转过来时短暂高亮该人物卡片 */
.nl-jump{{color:#eceff4;text-decoration:none;border-bottom:1px dashed #6b7688;cursor:pointer}}
.nl-jump:hover{{color:#88c0d0;border-bottom-color:#88c0d0}}
.card-hi{{outline:2px solid #88c0d0;outline-offset:3px;transition:outline .3s}}
.nl-pane{{display:none;max-height:520px;overflow-y:auto;padding-right:4px}}
.nl-pane.on{{display:block}}
.nl-row{{border-left:3px solid #4c566a;background:#2f3646;border-radius:0 6px 6px 0;
  padding:9px 12px;margin-bottom:8px}}
.nl-hd{{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-bottom:5px}}
.nl-ic{{font-size:14px}}
.nl-name{{font-weight:600;font-size:13.5px;color:#eceff4}}
.nl-type{{font-size:11px}}
.nl-dom{{font-size:10.5px;padding:1px 7px;border-radius:9px}}
.nl-reg{{font-size:11px;color:var(--muted);margin-left:auto}}
.nl-body{{font-size:12.5px;line-height:1.6;margin-bottom:6px}}
.nl-txt{{color:#d8dee9;text-decoration:none;border-bottom:1px dotted #5d6a82}}
a.nl-txt:hover{{color:#88c0d0;border-bottom-color:#88c0d0}}
.nl-times{{display:flex;gap:8px;flex-wrap:wrap}}
.nl-t{{font-size:10.5px;color:var(--muted);background:#262c38;padding:2px 7px;border-radius:4px;
  white-space:nowrap;cursor:help}}
.nl-target{{color:#ebcb8b}}
.nl-collect{{color:#a3be8c}}
.nl-empty{{font-size:12px;color:var(--muted);padding:16px;text-align:center;line-height:1.7}}
/* 卡片双时间徽章 */
.ctimes{{display:flex;gap:7px;flex-wrap:wrap;margin:6px 0 2px}}
.ct{{font-size:10.5px;padding:2px 8px;border-radius:4px;background:#262c38;
  color:var(--muted);white-space:nowrap;cursor:help}}
.ct-collect{{color:#a3be8c}}
.ct-target{{color:#ebcb8b}}
.pmeta{{font-size:10px;color:#7b8496;margin-left:4px;white-space:nowrap;cursor:help}}
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
.pv-hit{{color:#a3be8c;font-size:10px;flex-shrink:0;background:rgba(163,190,140,.12);
  border:1px solid rgba(163,190,140,.35);border-radius:3px;padding:0 5px;white-space:nowrap}}
.pv-miss{{color:#bf616a;font-size:10px;flex-shrink:0;background:rgba(191,97,106,.12);
  border:1px solid rgba(191,97,106,.35);border-radius:3px;padding:0 5px;white-space:nowrap}}
.pregion{{font-size:11px;color:var(--muted);background:var(--card2);padding:1px 7px;border-radius:4px}}
.pstatus{{font-size:11px;padding:1px 7px;border-radius:4px;margin-left:auto}}
.st-在世{{background:#a3be8c33;color:#a3be8c}}
.st-已故{{background:#8892a633;color:#8892a6}}
.st-历史复核{{background:#ebcb8b33;color:#ebcb8b}}
.ptype{{font-size:12px;margin-bottom:6px}}
.pbio{{font-size:11.5px;color:var(--muted);background:var(--card2);border-radius:6px;padding:6px 9px;margin-bottom:8px;line-height:1.5}}
/* ---- 人物背景：折叠板块 ---- */
.pbio-wrap{{margin-bottom:8px}}
.pbio-sum{{list-style:none;cursor:pointer;font-size:11.5px;color:var(--muted);
  background:var(--card2);border-radius:6px;padding:6px 9px;line-height:1.5;
  display:flex;align-items:baseline;gap:8px}}
.pbio-sum::-webkit-details-marker{{display:none}}
.pbio-sum:hover{{background:#2b3240}}
.pbio-txt{{flex:1}}
.pbio-more{{flex-shrink:0;font-size:10px;color:var(--accent);border:1px solid var(--accent);
  border-radius:4px;padding:1px 6px;opacity:.75;white-space:nowrap}}
.pbio-wrap[open] .pbio-more{{opacity:1}}
.pbio-wrap[open] .pbio-sum{{border-bottom-left-radius:0;border-bottom-right-radius:0}}
.pbio-full{{font-size:11.5px;color:var(--text);background:#20252f;border-radius:0 0 6px 6px;
  padding:9px 11px;line-height:1.75;border-top:1px solid #333b4a}}
/* ---- 单条言论：第三级详情 ----
   注意：.pred-x 必须写成 details.pred.pred-x 提高特异性。CSS 里 .pred 规则
   定义在本段之后并带 display:flex，同权重下后者胜出，会把 details 变成 flex 容器
   从而破坏原生折叠（实测：关闭状态 pd-body 仍有 301px 高度）。
   双类选择器权重 0-2-0 大于 0-1-0，可靠覆盖。 */
details.pred.pred-x{{display:block;padding:0;background:transparent;border-radius:6px}}
.pred-sum{{list-style:none;cursor:pointer;display:flex;align-items:flex-start;gap:8px;
  font-size:12.5px;background:var(--card2);border-radius:6px;padding:7px 10px}}
.pred-sum::-webkit-details-marker{{display:none}}
.pred-sum:hover{{background:#2b3240}}
.pred-x[open] .pred-sum{{border-bottom-left-radius:0;border-bottom-right-radius:0}}
/* 正文独占整宽：pred-main 吃满剩余空间，元数据换行到正文下方小字带。
   min-width:0 是关键——否则 flex 子项不肯收缩，正文会被挤成窄柱。 */
.pred-main{{flex:1;min-width:0;display:block}}
.ptext{{color:var(--text);text-decoration:none;display:inline;line-height:1.65}}
.pdot{{display:inline-block;width:6px;height:6px;border-radius:50%;
  margin-right:6px;vertical-align:middle;flex-shrink:0}}
.pmetabar{{margin-top:5px;display:flex;flex-wrap:wrap;gap:9px;align-items:center;line-height:1.4}}
.pm{{font-size:10px;color:#7b8496;white-space:nowrap}}
.pm-dom{{font-weight:600}}
.pd-more{{flex-shrink:0;font-size:9.5px;color:var(--muted);border:1px solid #3b4353;
  border-radius:3px;padding:1px 5px;white-space:nowrap;margin-top:1px}}
.pred-x[open] .pd-more{{color:var(--accent);border-color:var(--accent)}}
.pd-body{{background:#20252f;border-radius:0 0 6px 6px;padding:9px 11px;
  border-top:1px solid #333b4a}}
.pd-detail{{font-size:11.5px;color:var(--text);line-height:1.75}}
.pd-thin{{color:var(--muted);font-style:italic}}
.pd-quote{{font-size:11.5px;color:#d8dee9;line-height:1.7;margin-top:7px;
  padding-left:9px;border-left:2px solid var(--accent);font-style:italic}}
.pd-src{{display:inline-block;margin-top:8px;font-size:10.5px;color:var(--accent);text-decoration:none}}
.pd-src:hover{{text-decoration:underline}}
.pd-nosrc{{color:var(--muted);font-style:italic}}
/* ---- 第二级：展开全部言论 ---- */
.pmore{{margin-top:7px}}
.pmore-sum{{list-style:none;cursor:pointer;font-size:11px;color:var(--accent);
  text-align:center;padding:5px 9px;border:1px dashed #3b4353;border-radius:6px;opacity:.8}}
.pmore-sum::-webkit-details-marker{{display:none}}
.pmore-sum:hover{{opacity:1;border-color:var(--accent);background:#242a35}}
.pmore[open] .pmore-sum{{margin-bottom:7px}}
.pmore-list{{margin-top:0}}
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
{sidebar_html()}
<h1 id="sec-top">🔮 Forecast Checker — 预言家看板</h1>
<div class="sub">灵媒 · 预言家 · 出体者 · 预知者 · 模型预测者 内容汇总 · 双维度分组（身份类型 × 预言主题领域）· 更新 {esc(data.get("_last_updated", ""))}</div>
<div class="stats">
  <div class="stat"><div class="n">{total_people}</div><div class="l">收录人物</div></div>
  <div class="stat"><div class="n">{total_preds}</div><div class="l">追溯预言</div></div>
  <div class="stat"><div class="n">{with_pred}</div><div class="l">有预言者</div></div>
  <div class="stat"><div class="n">{len(groups)}</div><div class="l">身份类型</div></div>
  <div class="stat"><div class="n">{covered_domains}</div><div class="l">覆盖领域</div></div>
</div>
<div class="toprow" id="sec-radar">
  <div class="panel"><div class="panel-hd">🎯 预言主题领域雷达</div><div class="radar-wrap">{radar_svg()}</div></div>
  <div class="panel"><div class="panel-hd">📊 各领域预言条数</div>{dbars}</div>
</div>
<div class="panel" style="margin-bottom:24px" id="sec-latest">
  <div class="panel-hd">🆕 最新收录言论 <span style="font-size:11px;color:var(--muted);font-weight:400">（按收录入库时间分档 · 每条标「说于 / 目标 / 收录」三个时间点 · 点击标题切换跨度）</span></div>
  {latest_html()}
</div>
<div class="panel" style="margin-bottom:24px" id="sec-timeline">
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
{sidebar_js()}
</body></html>'''

out_dir = os.path.join(base, "..", "dashboard")
with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(HTML)
print("wrote dashboard/index.html", len(HTML), "chars |", total_people, "人", total_preds, "预言")
