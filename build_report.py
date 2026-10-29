# -*- coding: utf-8 -*-
"""
디자인 고정 + 데이터 주입 리포트 빌더.
- 레이아웃(HTML 뼈대)과 CSS는 이 스크립트/ report_style.css 에 고정.
- 내용은 전부 report_data.json 에서 주입. (헤르메스/gpt-4.1은 이 JSON만 생성하면 됨)
사용: PYTHONUTF8=1 python build_report.py [data.json] [out.pdf]
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SC = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SC, "report_data.json")
OUTPDF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SC, "report_built.pdf")
OUTHTML = os.path.splitext(OUTPDF)[0] + ".html"

d = json.load(open(DATA, encoding="utf-8"))
css = open(os.path.join(SC, "report_style.css"), encoding="utf-8").read()
KV = open(os.path.join(SC, "nousgirl_b64.txt"), encoding="utf-8").read().strip()
M = d["meta"]

# 페이지 물리 순서 (표지 제외). 방법론은 표지로 녹였고, 남은 정량 대시보드는 뒤 결론의 근거라 앞(02)에 둔다.
PAGE_ORDER = ["p2_summary", "p3_method_dash", "p4_strength", "p5_loyalty", "p6_cluster",
              "p7_segment", "p8_ingredient", "p8_risk", "p9_deepdive", "p10_unmet", "p11_bench"]
# 없는 쪽(예: 화해가 없으면 성분 페이지)은 번호에서 건너뛴다. 예전에는 06 다음이 08로 찍혔다(10/25 점검).
_present = [k for k in PAGE_ORDER if k in d and isinstance(d[k], dict)]
for _i, _k in enumerate(_present, 1):
    d[_k]["no"] = f"{_i:02d}"

# ---- 사진 (10/25) ----
# assemble_data 가 data/photos 의 파일 경로를 넣어 준 칸에만 사진을 그린다. 경로가 없거나 파일이 없으면 빈 문자열(칸 자체가 없음).
# PDF 가 무거워지지 않게 가로 maxw px 의 JPEG 로 줄여 HTML 안에 넣는다(HTML 하나로 열리게, 표지 키비주얼과 같은 방식).
import base64
def img_uri(ph, maxw=640):
    path = (ph or {}).get("path")
    if path and not os.path.exists(path) and os.path.exists(os.path.join(SC, path)):
        path = os.path.join(SC, path)   # 키트 안 상대경로(photos/...)도 찾는다
    if not path or not os.path.exists(path):
        return None
    try:
        from PIL import Image
        im = Image.open(path)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGB", im.size, "white"); bg.paste(im, mask=im.split()[-1]); im = bg
        else:
            im = im.convert("RGB")
        if im.width > maxw:
            im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        print("사진 건너뜀:", path, e)
        return None
PHOTO_CSS = """
.cover .pphoto{position:absolute;right:calc(6mm + 75px);top:calc(50% - 165px - 214px);width:180px;z-index:2;text-align:center}
.cover .pphoto img{width:180px;height:180px;object-fit:cover;border-radius:18px;border:2px solid var(--ink);background:#fff;display:block}
.pcap{font-size:9.5px;color:var(--sub);font-weight:600;margin-top:5px;line-height:1.35}
.phead{display:flex;justify-content:space-between;align-items:center;gap:16px}
.phead .pmini{display:flex;align-items:center;gap:10px;text-align:right}
.phead .pmini img{width:58px;height:58px;flex-shrink:0;object-fit:cover;border-radius:10px;border:1px solid var(--line);background:#fff}
.phead .pmini .pcap{margin-top:0}
.vph{margin-top:10px}
.vph img{width:100%;height:118px;object-fit:cover;border-radius:8px;display:block}
.qph{display:flex;gap:12px;align-items:center;margin-top:8px;border-left:4px solid #f0b7c2;padding:0 0 0 15px}
.scent.wph .q{padding-top:6px;padding-bottom:6px}
.qph img{width:44px;height:44px;object-fit:cover;border-radius:8px;flex-shrink:0}
.qph .txt{font-size:12.5px;line-height:1.5;color:#2c2c34;font-weight:500}
.qph .m{font-size:10.5px;color:var(--sub);font-weight:700;margin-top:3px}
"""

def rt(p):
    return (f'<div class="rt"><span class="lead-b"><img src="{KV}"><span>'
            f'<span class="b">{M["brand_a"]}</span> · {M["running_title"]}</span></span>'
            f'<span>{p["no"]} · {p["tab"]}</span></div>')

def foot(right):
    return (f'<div class="foot"><span class="wm">Architected by <b>{M["architect"]}</b> '
            f'· Powered by {M["tool"]}</span><span>{right}</span></div>')

def h2(title, en):
    return f'<h2>{title} <span class="n">{en}</span></h2>'

def lead(t):
    return f'<p class="lead">{t}</p>' if t else ""

def pgsum(o):
    if not o or not o.get("pt"):
        return ""
    return f'<div class="pgsum"><div class="pi">{o["pi"]}</div><div class="pt">{o["pt"]}</div></div>'

def ins(so_what=None, action=None):
    rows = ""
    if so_what:
        rows += f'<div class="l"><span class="k">SO WHAT</span><span class="tx">{so_what}</span></div>'
    if action:
        rows += f'<div class="l ac"><span class="k">ACTION</span><span class="tx">{action}</span></div>'
    return f'<div class="ins">{rows}</div>' if rows else ""

# ---------------- P1 표지 ----------------
def _cover_photo():
    ph = M.get("product_photo"); u = img_uri(ph, 520)
    return f'<div class="pphoto"><img src="{u}"><div class="pcap">{ph["cap"]}</div></div>' if u else ""

def cover():
    c = d["cover"]
    tags = "".join(f'<span class="tag{" r" if t.get("r") else ""}">{t["t"]}</span>' for t in c["tags"])
    title = "<br>".join(c["title_lines"])
    return f'''<div class="page cover">
  <div class="bgwm">{M["brand_a"]}</div>
  <div class="cvtop">
    <div class="brandlock"><img src="{KV}"><span class="wm"><span class="h">{M["brand_a"]}</span><span class="x">✕</span>{M["brand_b"]}</span></div>
  </div>
  <div class="cvmid">
    <div class="txt">
      <span class="k">{c["kicker"]}</span>
      <h1>{title}</h1>
      <div class="sub">{c["subtitle"]}</div>
      <div class="tags">{tags}</div>
      {f'<div class="basis">{c["basis"]}</div>' if c.get("basis") else ""}
    </div>
    <div class="kv"><div class="disc"></div><div class="dot"></div><img class="fig" src="{KV}"></div>
    {_cover_photo()}
  </div>
  <div class="cvbtm">
    <div class="meta">분석 도구 · <b>{M["tool"]}</b><br>데이터 기준일 · <b>{M["date"]}</b></div>
    <div class="credit"><div class="big">Architected by <span>{M["architect"]}</span></div>Powered by {M["brand_a"]}</div>
  </div>
</div>'''

# ---------------- P2 핵심요약 ----------------
def _p2_head(p):
    ph = M.get("product_photo"); u = img_uri(ph, 200)
    if not u:
        return h2(p["h2"], p["en"])
    cap = ph["cap"].replace(" · ", "<br>", 1)
    return f'<div class="phead">{h2(p["h2"], p["en"])}<div class="pmini"><span class="pcap">{cap}</span><img src="{u}"></div></div>'

def p2():
    p = d["p2_summary"]
    sc = "".join(
        f'<div class="s"><div class="v {s.get("cls","")}">{s["v"]}'
        + (f'<span class="u">{s["u"]}</span>' if s.get("u") else "")
        + f'</div><div class="l">{s["l"]}</div></div>'
        for s in p["scores"])
    fs = "".join(
        f'<div class="f"><div class="ic">{f["ic"]}</div><div class="c">'
        f'<div class="t">{f["t"]}</div><div class="d">{f["d"]}</div></div>'
        f'<div class="mn"><div class="big">{f["big"]}</div><div class="cap">{f["cap"]}</div></div></div>'
        for f in p["finds"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {_p2_head(p)}
    {lead(p["lead"])}
    <div class="score">{sc}</div>
    <div class="finds">{fs}</div>
  </section>
  {pgsum(p["pgsum"])}
  {foot(p["foot_right"])}
</div>'''

# ---------------- P3 방법론 + 대시보드 ----------------
def p3():
    p = d["p3_method_dash"]; da = p["dashboard"]
    sigs = da.get("signals", [])
    kwp = "".join(f'<span class="kw pos">{k["k"]}<b>{k["c"]}</b></span>' for k in da.get("kw_pos", []))
    kwn = "".join(f'<span class="kw neg">{k["k"]}<b>{k["c"]}</b></span>' for k in da.get("kw_neg", []))
    kwsec = ""
    if kwp and kwn:
        kwsec = (
            '<div class="kwsec">'
            '<div class="kwcol"><div class="subh"><span class="dot"></span>강점 · 칭찬 키워드</div>'
            f'<div class="kws">{kwp}</div></div>'
            '<div class="kwcol"><div class="subh"><span class="dot n"></span>아쉬움 · 지적 키워드</div>'
            f'<div class="kws">{kwn}</div></div>'
            '</div>')
    sg = "".join(
        f'<div class="sg {s.get("cls","")}"><div class="big">{s["big"]}</div>'
        f'<div class="t">{s["t"]}</div><div class="d">{s["d"]}</div></div>'
        for s in sigs)
    ch = "".join(
        f'<div class="cc {c["cls"]}"><div class="h"><span>{c["name"]}</span><span>{c["tag"]}</span></div>'
        f'<div class="big">{c["big_pre"]}' + (f'<span class="r">{c["big_r"]}</span>' if c["big_r"] else "")
        + f'{c["big"]}<span class="u">{c["u"]}</span></div><div class="sm">{c["sm"]}</div></div>'
        for c in da["channels"])
    bars = "".join(
        f'<div class="bar"><span class="lb">{b["lb"]}</span><span class="tr"><i style="width:{b["w"]}%"></i></span>'
        f'<span class="pc">{b["pc"]}</span></div>'
        for b in da["dist"])
    _maxh = max((t.get("h", 0) for t in da["timeline"]), default=0)
    # 막대 높이를 칸 높이의 %로 주면 위 라벨(최다·평점)이 차지한 만큼 막대가 눌려, 라벨이 하나 더 붙은 최고 막대가
    # 옆 막대보다 낮아 보였다(10/25 점검). 라벨 자리 56px 을 빼고 남은 높이를 px 로 계산해 눌리지 않게 한다.
    _TL_PX = 210 - 56
    cols = "".join(
        f'<div class="col{" peak" if _maxh and t.get("h") == _maxh else ""}">'
        + ('<span class="pk">건수 최다</span>' if _maxh and t.get("h") == _maxh else "")
        + f'<span class="val">{t["val"]}</span><div class="b" style="height:{max(2, float(t["h"]) * _TL_PX / 100):.1f}px;flex-shrink:0"></div></div>'
        for t in da["timeline"])
    tlx = "".join(f'<span>{t["x"]}</span>' for t in da["timeline"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(da["h2"], da["en"])}
    {lead(da["lead"])}
    <div class="chan">{ch}</div>
    {f'<div class="seclabel"><span class="n">1</span>리뷰가 말하는 핵심 신호<span class="sub">{da.get("sec1_sub", "핵심 신호")}</span></div><div class="signals">{sg}</div>' if sg else ""}
    {f'<div class="seclabel"><span class="n">2</span>무엇을 좋아하고, 무엇을 아쉬워하나<span class="sub">{da.get("kw_sub", "화해 키워드 언급 건수")}</span></div>{kwsec}' if kwsec else ""}
    <div class="seclabel"><span class="n">3</span>{da.get("sec3_title", "별점 분포와 표본의 작성 월")}<span class="sub">{da.get("sec3_sub", "")}</span></div>
    <div class="dash">
      <div>
        <div class="subh"><span class="dot"></span>{da["dist_title"]}</div>
        <div class="bars">{bars}</div>
        {f'<div class="chartcap">{da["dist_cap"]}</div>' if da.get("dist_cap") else ""}
      </div>
      <div>
        <div class="subh"><span class="dot"></span>{da["tl_title"]}</div>
        <div class="tl">{cols}</div>
        <div class="tlx">{tlx}</div>
        {f'<div class="chartcap">{da["tl_cap"]}</div>' if da.get("tl_cap") else ""}
      </div>
    </div>
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P4 강점 ----------------
def p4():
    p = d["p4_strength"]
    drv = "".join(
        f'<div class="d{" hero" if dr["hero"] else ""}"><div class="rk">{dr["rk"]}</div>'
        f'<div class="t">{dr["t"]}</div><div class="x">{dr["x"]}</div>'
        + (f'<div style="font-size:10px;color:var(--sub);margin-top:6px;line-height:1.4">{dr["xsrc"]}</div>' if dr.get("xsrc") else "") +
        f'<div class="gauge"><div class="gl"><span>{dr["gl"]}</span><b>{dr["gv"]}</b></div>'
        f'<div class="tr"><i style="width:{dr["gw"]}%"></i></div></div>'
        f'<div class="ev">{dr["ev"]}</div></div>'
        for dr in p["drivers"])
    flow = ""
    for i, fb in enumerate(p["flow"]):
        if i: flow += '<div class="ar">→</div>'
        flow += f'<div class="fb{" goal" if fb["goal"] else ""}"><div class="ft">{fb["ft"]}</div><div class="fd">{fb["fd"]}</div></div>'
    rows = "".join(
        f'<tr><td class="g">{r["g"]}</td><td style="width:160px">{r["mid"]}</td><td>{r["right"]}</td></tr>'
        for r in p["cross_rows"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(p["h2"], p["en"])}
    {lead(p["lead"])}
    <div class="drv">{drv}</div>
    <div class="subh"><span class="dot"></span>{p["flow_title"]}</div>
    {f'<div class="flow">{flow}</div>' if flow else ""}
    {ins(p["so_what"], p["action"])}
    <div class="subh" style="margin-top:22px"><span class="dot"></span>{p["cross_title"]}</div>
    <table class="segtbl" style="font-size:12.5px">{rows}</table>
    <p style="font-size:12px;color:#52525b;line-height:1.6;margin-top:12px;padding-left:2px">{p["closer"]}</p>
    {pgsum(p["pgsum"]) if p.get("pgsum") else ""}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P5 충성도 ----------------
def cmprow(r, mut=False):
    cls = "cmprow mut" if mut else "cmprow"
    delta = f'<span class="updelta">{r["delta"]}</span>' if r.get("delta") else ""
    return (f'<div class="{cls}"><div class="l"><span>{r["l"]}</span><span>{r["pc"]}{delta}</span></div>'
            f'<div class="tr"><i style="width:{r["w"]}%"></i></div></div>')

def cmp_block(blk):
    left = f'<div class="ct">{blk["left_title"]}<span class="tag2">{blk["left_tag"]}</span></div>' + "".join(cmprow(r) for r in blk["left"])
    right = f'<div class="ct">{blk["right_title"]}<span class="tag2">{blk["right_tag"]}</span></div>' + "".join(cmprow(r, True) for r in blk["right"])
    return f'<div class="cmp"><div>{left}</div><div>{right}</div></div>'

def p5():
    p = d["p5_loyalty"]; rp = p["repurchase"]; lo = p["longitudinal"]
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(rp["h2"], rp["en"])}
    {lead(rp["lead"])}
    {cmp_block(rp)}
    {ins(rp["so_what"], rp["action"])}
  </section>
  <section>
    {h2(lo["h2"], lo["en"])}
    {lead(lo["lead"])}
    {cmp_block(lo)}
    {ins(lo["so_what"])}
    {pgsum(lo["pgsum"])}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P6 클러스터 ----------------
def p6():
    p = d["p6_cluster"]
    axes = ""
    for ax in p["axes"]:
        rows = ""
        for r in ax["rows"]:
            rise = f'<span class="rise">{r["rise"]}</span>' if r.get("rise") else ""
            if rise:
                lhtml = f'<span>{r["l"]}</span><span><b>{r["b"]}</b>{rise}</span>'
            else:
                lhtml = f'<span>{r["l"]}</span><b>{r["b"]}</b>'
            rows += f'<div class="krow"><div class="l">{lhtml}</div><div class="tr"><i style="width:{r["w"]}%"></i></div></div>'
        axes += f'<div class="{ax["cls"]}"><div class="ah">{ax["ah"]}</div>{rows}</div>'
    def _vph(v):
        u = img_uri(v.get("photo"), 480)
        return f'<div class="vph"><img src="{u}"><div class="pcap">{v["photo"]["cap"]}</div></div>' if u else ""
    voc = "".join(
        f'<div class="vc {v["cls"]}"><div class="vq">{v["vq"]}</div><div class="vm">{v["vm"]}</div>{_vph(v)}</div>'
        for v in p["voc"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(p["h2"], p["en"])}
    {lead(p["lead"])}
    <div class="axis">{axes}</div>
    <div class="subh"><span class="dot"></span>{p["voc_title"]}</div>
    <div class="axvoc">{voc}</div>
    {ins(p["so_what"])}
    {pgsum(p["pgsum"])}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P7 세그먼트 ----------------
def p7():
    p = d["p7_segment"]; sg = p["segment"]; cr = p["cross"]
    sbars = "".join(
        f'<div class="srow{" hot" if b["hot"] else ""}"><span class="nm">{b["nm"]}</span>'
        f'<span class="tr"><i style="width:{b["w"]}%"></i></span><span class="pc">{b["pc"]}</span></div>'
        for b in sg["bars"])
    stbl = "".join(
        f'<tr><td class="{r["cls"]}">{r["k"]}</td><td>{r["v"]}</td></tr>'
        for r in sg["table"])
    lbox = f'<div class="box"><div class="bt">{cr["left_title"]}</div>' + "".join(f'<div class="it"><span>{i["s"]}</span><b>{i["b"]}</b></div>' for i in cr["left"]) + "</div>"
    rbox = f'<div class="box r"><div class="bt">{cr["right_title"]}</div>' + "".join(f'<div class="it"><span>{i["s"]}</span><b>{i["b"]}</b></div>' for i in cr["right"]) + "</div>"
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(sg["h2"], sg["en"])}
    {lead(sg["lead"])}
    <div class="seg">
      <div class="segcard"><div class="h">{sg["bars_title"]}</div>{sbars}</div>
      <div class="segcard"><div class="h">{sg["table_title"]}</div><table class="segtbl">{stbl}</table></div>
    </div>
  </section>
  <section>
    {h2(cr["h2"], cr["en"])}
    {lead(cr["lead"])}
    <div class="vs">{lbox}{rbox}</div>
    {ins(cr["so_what"], cr["action"])}
    {pgsum(cr["pgsum"])}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P7b 성분 교차검증 (화해 전성분, 2026-09-07) ----------------
def p7i():
    p = d.get("p8_ingredient")
    if not p:
        return ""
    sg = "".join(
        f'<div class="sg {s.get("cls","")}"><div class="big">{s["big"]}</div>'
        f'<div class="t">{s["t"]}</div><div class="d">{s["d"]}</div></div>'
        for s in p["signals"])
    lbox = f'<div class="box r"><div class="bt">{p["vs_left_title"]}</div>' + "".join(f'<div class="it"><span>{i["s"]}</span><b>{i["b"]}</b></div>' for i in p["vs_left"]) + "</div>"
    rbox = f'<div class="box"><div class="bt">{p["vs_right_title"]}</div>' + "".join(f'<div class="it"><span>{i["s"]}</span><b>{i["b"]}</b></div>' for i in p["vs_right"]) + "</div>"
    chips = "".join(f'<span class="warn">{c}</span>' for c in p.get("chips", []))
    chipsec = f'<div class="ingrsec"><div class="subh"><span class="dot n"></span>{p["chips_title"]}</div><div class="ingrlist">{chips}</div></div>' if chips else ""
    tbl = "".join(f'<tr><td class="{r["cls"]}">{r["k"]}</td><td>{r["v"]}</td></tr>' for r in p["table"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(p["h2"], p["en"])}
    {lead(p["lead"])}
    <div class="signals" style="margin-top:0">{sg}</div>
    <div class="seclabel" style="margin-top:20px"><span class="n">1</span>리뷰의 불만과 성분표 신호<span class="sub">아쉬워요 키워드 × 전성분</span></div>
    <div class="vs">{lbox}{rbox}</div>
    {chipsec}
    {ins(p["so_what"], p["action"])}
    <div class="seclabel" style="margin-top:20px"><span class="n">2</span>{p["table_title"]}<span class="sub">포지셔닝 · 랭킹 · 피부타입 비고</span></div>
    <div class="segcard" style="margin-top:10px"><table class="segtbl">{tbl}</table></div>
    {pgsum(p["pgsum"])}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P8 리스크 ----------------
def p8():
    p = d["p8_risk"]
    cards = "".join(
        f'<div class="rc"><span class="grade {c["grade"]}">{c["grade_t"]}</span>'
        f'<div class="rt2">{c["t"]}</div><div class="rd">{c["d"]}</div><div class="sig">{c["sig"]}</div></div>'
        for c in p["cards"])
    mx = p["matrix"]
    r1 = f'<div class="cell axl">{mx["row1_axis"]}</div>' + "".join(f'<div class="cell {c["cls"]}">{c["t"]}</div>' for c in mx["row1"])
    r2 = f'<div class="cell axl">{mx["row2_axis"]}</div>' + "".join(f'<div class="cell {c["cls"]}">{c["t"]}</div>' for c in mx["row2"])
    r3 = '<div class="cell axl"></div>' + "".join(f'<div class="cell hd">{h}</div>' for h in mx["col_heads"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(p["h2"], p["en"])}
    {lead(p["lead"])}
    <div class="rsum">{cards}</div>
    <div class="matrix">
      <div class="mh">{p["matrix_title"]}</div>
      <div class="mgrid">{r1}{r2}{r3}</div>
    </div>
    {ins(p["so_what"])}
    <div class="benchhead" style="margin-top:16px"><div class="bt">{p["benchhead"]}</div></div>
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P9 심층이슈 ----------------
def p9():
    p = d["p9_deepdive"]; dp = p["deep"]; ch = p["churn"]
    quotes = "".join(f'<div class="q"><div class="txt">{q["txt"]}</div><div class="m">{q["m"]}</div></div>' for q in dp["quotes"])
    # 사진: 인용한 리뷰의 사진(photo) 또는 같은 범주의 사진 리뷰 인용(photo_quote). 둘 다 없으면 그리지 않는다.
    _pq = dp.get("photo_quote") or {}
    _pu = img_uri(_pq, 240) if _pq else None
    _dph = img_uri(dp.get("photo"), 240)
    pquote = (f'<div class="qph"><img src="{_pu}"><div><div class="txt">{_pq["txt"]}</div>'
              f'<div class="m">{_pq["m"]}</div></div></div>') if _pu else (
             f'<div class="qph"><img src="{_dph}"><div class="pcap">{dp["photo"]["cap"]}</div></div>' if _dph else "")
    cards = "".join(
        f'<div class="ch"><div class="hd"><span class="no">{c["no"]}</span>{c["hd"]}</div>'
        f'<div class="q">{c["q"]}</div>'
        + (f'<div class="fix">{c["fix"]}</div>' if c.get("fix") else "")
        + (f'<div style="font-size:10.5px;color:var(--sub);margin-top:9px;line-height:1.45">{c["src"]}</div>' if c.get("src") else "")
        + '</div>'
        for c in ch["cards"])
    share = "".join(
        f'<div class="crow"><span class="cl">{s["cl"]}</span><div class="ct"><i style="width:{s["w"]}%;background:{s["color"]}"></i></div>'
        f'<span class="cv">{s["cv"]}</span></div>'
        for s in ch["share"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(dp["h2"], dp["en"])}
    {lead(dp["lead"])}
    <div class="scent{' wph' if pquote else ''}">
      <div class="quotes">{quotes}</div>
      <div class="stat"><div class="n">{dp["stat_n"]}</div><div class="l">{dp["stat_l"]}</div></div>
    </div>
    {pquote}
    {ins(dp["so_what"], dp["action"])}
  </section>
  <section>
    {h2(ch["h2"], ch["en"])}
    {lead(ch["lead"])}
    <div class="churn">{cards}</div>
    <div class="cshare">
      <div class="csh">{ch["share_title"]}<span>{ch["share_sub"]}</span></div>
      {share}
    </div>
    {pgsum(ch["pgsum"])}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P10 언멧 + 액션 ----------------
def p10():
    # 6차: assemble_data 가 이 쪽(빈틈·액션 제언)을 더 내지 않는다. 키가 없으면 그리지 않는다.
    p = d.get("p10_unmet")
    if not p:
        return ""
    um = p["unmet"]; ac = p["actions"]
    items = "".join(
        f'<div class="u"><span class="no">{i["no"]}</span><div class="c"><div class="t">{i["t"]}</div>'
        f'<div class="d">{i["d"]}</div></div><span class="v">{i["v"]}</span></div>'
        for i in um["items"])
    _eff_col = any(r.get("eff") for r in ac["rows"])
    rows = "".join(
        f'<tr><td><span class="pri {r["pri"]}" style="white-space:nowrap">{r["pri_t"]}</span></td>'
        f'<td><b>{r["what"]}</b>' + (f'<br><span class="sm">{r["sm"]}</span>' if r.get("sm") else "") + '</td>'
        f'<td>{r["why"]}</td>' + (f'<td>{r["eff"]}</td>' if _eff_col else "") + '</tr>'
        for r in ac["rows"])
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(um["h2"], um["en"])}
    {lead(um["lead"])}
    <div class="unmet">{items}</div>
    <h2 style="margin-top:22px">{ac["h2"]} <span class="n">{ac["en"]}</span></h2>
    {lead(ac["lead"])}
    <table class="acttbl">
      <thead><tr><th style="width:78px">우선순위</th><th>무엇을</th><th style="width:{180 if _eff_col else 260}px">근거</th>{'<th style="width:96px">기대 효과</th>' if _eff_col else ""}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
    {pgsum(ac["pgsum"])}
  </section>
  {foot(p["foot_right"])}
</div>'''

# ---------------- P11 벤치마크 ----------------
def p11():
    p = d["p11_bench"]
    # 카드 수가 홀수면 2열 그리드 오른쪽 아래가 빈다. 마지막 카드를 두 칸에 걸쳐 놓는다(스타일 시트는 그대로).
    _odd = len(p["cards"]) % 2 == 1
    cards = "".join(
        f'<div class="bc"' + (' style="grid-column:1/-1"' if _odd and i == len(p["cards"]) - 1 else "") + '>'
        f'<div class="bn">{c["bn"]}</div><div class="bh">{c["bh"]}</div>'
        + (f'<div class="bd">{c["bd"]}</div>' if c["bd"] else "")
        # keep-all: 「통일」이 「통/일」로 갈라지지 않게 낱말 단위로만 줄바꿈
        + (f'<div class="apply" style="word-break:keep-all">{c["apply"]}</div>' if c.get("apply") else "") + '</div>'
        for i, c in enumerate(p["cards"]))
    return f'''<div class="page">
  {rt(p)}
  <section>
    {h2(p["h2"], p["en"])}
    {lead(p["lead"])}
    <div class="benchhead"><div class="bt">{p["benchhead"]}</div></div>
    <div class="bench">{cards}</div>
    <div class="close">
      <div class="ct2">{p["close_label"]}</div>
      <div class="cq">{p["close_q"]}</div>
    </div>
  </section>
  {foot(p["foot_right"])}
</div>'''

pages = [pg for pg in [cover(), p2(), p3(), p4(), p5(), p6(), p7(), p7i(), p8(), p9(), p10(), p11()] if pg]
# 7차: 줄 끝 분리 공통 처리. meta.nobreak 의 이름(테마·키워드·범주·배합 목적·고정 용어)을 전 쪽 본문에서 찾아,
# 이름 안의 띄어쓰기·가운뎃점과 바로 뒤 숫자(「 166건」, 「 3」, 「(21%)」, 「 42.1%(전체 37%)」)에서 줄이 갈리지 않게 묶는다.
# 이름이 한 낱말이고 뒤에 숫자도 없으면 묶을 것이 없어 그대로 둔다. 한글 이름이라 태그 속성 안에서는 걸리지 않는다.
import re
_NW_OPEN = '<span style="white-space:nowrap">'
# 묶음은 span 이 아닌 이름 없는 인라인 태그로 감싼다(「.ingrlist span」 같은 칩 스타일이 붙지 않게).
# 글자를 직접 자식으로 둔 flex 상자(h2·.subh·.seclabel·.hd·.cell axl·.kw)에는 넣지 않는다. 넣었더니 묶음이 따로 떨어진
# flex 항목이 되어 앞뒤에 gap 만큼 빈칸이 생겼다(「재구매 리뷰  비교」). display:contents 로 상자를 없애면 빈칸은 사라지지만 줄바꿈을 못 막았다.
_NB_OPEN = '<w-nb style="white-space:nowrap">'
_FLEX_TXT = re.compile(r'<h2\b[^>]*>.*?</h2>|<div class="(?:subh|seclabel|hd|cell axl)"[^>]*>.*?</div>|<span class="kw [^"]*">.*?</b></span>', re.S)
def _glue_names(s, names):
    names = sorted({n for n in names if n}, key=len, reverse=True)
    if not names:
        return s
    _keep = []
    def _hold(m):
        _keep.append(m.group(0))
        return f"\x00{len(_keep) - 1}\x00"
    s = _FLEX_TXT.sub(_hold, s)
    alts = "|".join(r"[ \u00a0]".join(map(re.escape, n.split(" "))) for n in names)
    paren = r"\([^()<>]{1,10}\)"
    num = r"\d[\d,.]*(?:/\d[\d,.]*)?(?:%|건|배|개|종|위|점)?"
    nwnum = re.escape(_NW_OPEN) + r"\d[^<]*</span>"
    # 묶음 앞뒤에 붙은 글자(「2위(」, 「)입니다.」, 띄어쓰기 없이 붙은 굵은 낱말 「<b>유분·무거움</b>(」)까지 같이 묶는다.
    # 묶음 경계에서 새 줄바꿈 자리가 생겼다(「2위 / (쫀득함 744건)」).
    rx = re.compile(rf"(?:(?<=[\s>])|^)(?P<pre>(?:<b>[^\s<>]{{1,12}}</b>)?[^\s<>]{{0,12}}?)(?<![가-힣A-Za-z0-9])(?P<nm>{alts})"
                    rf"(?P<tail>{paren}|[ ](?:{nwnum}|{num}(?:{paren})?))?(?P<post>[^\s<>]{{0,12}})")
    def rep(m):
        nm, tail = m.group("nm"), m.group("tail") or ""
        if not tail and " " not in nm and "\u00b7" not in nm and "\u00a0" not in nm:
            return m.group(0)
        return _NB_OPEN + m.group(0) + "</w-nb>"
    s = rx.sub(rep, s)
    # 이미 묶여 있던 짧은 덩어리(NW: 「4/40건」, 「363건, 71%」)도 앞뒤에 붙은 글자까지 넓힌다(「…71%) / 입니다.」 방지).
    s = re.sub(re.escape(_NW_OPEN) + r"([^<]{1,40})</span>([^\s<>]{1,12})", lambda m: _NW_OPEN + m.group(1) + m.group(2) + "</span>", s)
    s = re.sub(r"(?<=[\s>])([^\s<>]{1,12})" + re.escape(_NW_OPEN) + r"([^<]{1,40})</span>", lambda m: _NW_OPEN + m.group(1) + m.group(2) + "</span>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: _keep[int(m.group(1))], s)
pages = [_glue_names(pg, M.get("nobreak", [])) for pg in pages]
html = ('<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">'
        f'<style>{css}\n.page{{word-break:keep-all;overflow-wrap:break-word}}{PHOTO_CSS}</style></head><body>\n' + "\n".join(pages) + "\n</body></html>")
open(OUTHTML, "w", encoding="utf-8").write(html)
print("HTML:", len(html), "bytes ->", OUTHTML)

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    # 설치된 크롬으로 렌더한다. Playwright 전용 Chromium 은 패키지 갱신(9/21, 1.58) 뒤 설치돼 있지 않아 launch 가 실패했다.
    b = pw.chromium.launch(channel="chrome"); pg = b.new_page()
    pg.goto("file:///" + OUTHTML.replace("\\", "/"))
    try: pg.wait_for_load_state("networkidle", timeout=9000)
    except Exception: pass
    pg.wait_for_timeout(1500)
    pg.pdf(path=OUTPDF, format="A4", print_background=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
    b.close()
print("PDF:", os.path.getsize(OUTPDF), "bytes ->", OUTPDF)
import fitz
doc = fitz.open(OUTPDF)
for i, page in enumerate(doc):
    page.get_pixmap(dpi=105).save(os.path.join(SC, f"bt_p{i+1}.png"))
print("pages:", doc.page_count)
