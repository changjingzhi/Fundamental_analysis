# -*- coding: utf-8 -*-
"""技术面 / 长期历史 / 估值 / 财务数据计算模块。

输入均为 fetcher 抓取的原始数据，输出结构化 dict，供 report 模块渲染。
"""
import bisect
from datetime import datetime, timedelta

KLINE_COLS = ("date", "open", "close", "high", "low", "vol")


def parse_kline(lines):
    """'2026-11-13,14.50,14.00,...' -> list[dict]"""
    rows = []
    for ln in lines:
        p = ln.split(",")
        if len(p) < 6:
            continue
        rows.append({c: (p[i] if c == "date" else float(p[i]))
                     for i, c in enumerate(KLINE_COLS)})
    return rows


def _d(s):
    return datetime.strptime(s, "%Y-%m-%d")


def _pct(a, b):
    return (a / b - 1) * 100 if b else None


def _round(x, n=2):
    return round(x, n) if x is not None else None


def technical(rows):
    """基于前复权日线计算技术指标。rows: list[dict]"""
    if not rows:
        return {
            "last_date": "-", "last_close": 0.0, "n": 0,
            "ma": {n: None for n in (5, 10, 20, 30, 60, 120, 250)},
            "y52_high": {"high": 0.0, "date": "-"},
            "y52_low": {"low": 0.0, "date": "-"},
            "ytd": {"first_close": 0.0, "chg": None,
                    "high": {"high": 0.0, "date": "-"}, "low": {"low": 0.0, "date": "-"},
                    "mdd": None},
            "chg_1y": None, "monthly_closes": [], "yearly_ret": [],
            "stage": {"h1": None, "q3": None, "oct": None},
            "vol": {"v20": 0.0, "v60": 0.0, "ratio": None, "ret20": None, "ret60": None},
            "last10": [],
        }
    last = rows[-1]
    closes = [r["close"] for r in rows]
    out = {"last_date": last["date"], "last_close": last["close"], "n": len(rows)}

    def ma(n):
        return sum(closes[-n:]) / n if len(closes) >= n else None
    out["ma"] = {n: _round(ma(n), 2) for n in (5, 10, 20,30, 60, 120, 250)}

    ld = _d(last["date"])
    y52 = [r for r in rows if _d(r["date"]) >= ld - timedelta(days=364)]
    out["y52_high"] = max(y52, key=lambda r: r["high"])
    out["y52_low"] = min(y52, key=lambda r: r["low"])

    year = last["date"][:4]
    ytd = [r for r in rows if r["date"].startswith(year)]
    first = ytd[0]
    out["ytd"] = {
        "first_close": first["close"],
        "chg": _round(_pct(last["close"], first["close"])),
        "high": max(ytd, key=lambda r: r["high"]),
        "low": min(ytd, key=lambda r: r["low"]),
    }
    peak, mdd = -1.0, 0.0
    for r in ytd:
        peak = max(peak, r["close"])
        mdd = min(mdd, r["close"] / peak - 1)
    out["ytd"]["mdd"] = _round(mdd * 100)

    prev = [r for r in rows if _d(r["date"]) <= ld - timedelta(days=364)]
    out["chg_1y"] = _round(_pct(last["close"], prev[-1]["close"])) if prev else None

    months = {}
    for r in ytd:
        months[r["date"][:7]] = r["close"]
    out["monthly_closes"] = [(k, v) for k, v in sorted(months.items())]

    # 各年度涨跌幅（前复权）
    yearly = {}
    for r in rows:
        yearly.setdefault(r["date"][:4], []).append(r)
    rets = []
    years = sorted(yearly)
    for i, y in enumerate(years):
        if i == 0:
            continue
        base = yearly[years[i - 1]][-1]["close"]
        rets.append((y, _round(_pct(yearly[y][-1]["close"], base))))
    out["yearly_ret"] = rets[-5:]

    def stage(a, b):
        seg = [r for r in rows if a <= r["date"] <= b]
        return _round(_pct(seg[-1]["close"], seg[0]["close"])) if len(seg) >= 2 else None
    out["stage"] = {
        "h1": stage(year + "-01-01", year + "-06-30"),
        "q3": stage(year + "-07-01", year + "-09-30"),
        "oct": stage(year + "-10-01", last["date"]),
    }

    v20 = sum(r["vol"] for r in rows[-20:]) / 20
    v60 = sum(r["vol"] for r in rows[-60:]) / 60 if len(rows) >= 60 else v20
    out["vol"] = {
        "v20": v20 / 1e4, "v60": v60 / 1e4, "ratio": _round(v20 / v60, 2) if v60 else None,
        "ret20": stage(rows[-21]["date"], last["date"]) if len(rows) >= 21 else None,
        "ret60": stage(rows[-61]["date"], last["date"]) if len(rows) >= 61 else None,
    }
    out["last10"] = rows[-10:]
    return out


def yearly_history(rows):
    """不复权全历史统计。"""
    if not rows:
        return {
            "n": 0, "start": "-", "end": "-",
            "all_high": {"high": 0.0, "date": "-"},
            "all_low": {"low": 0.0, "date": "-"},
            "cur": 0.0, "vs_high": None, "vs_low": None, "pctile": None,
            "close_range": [], "yearly_closes": [],
        }
    closes = sorted(r["close"] for r in rows)
    cur = rows[-1]["close"]
    yearly = {}
    for r in rows:
        yearly.setdefault(r["date"][:4], []).append(r)
    out = {
        "n": len(rows),
        "start": rows[0]["date"], "end": rows[-1]["date"],
        "all_high": max(rows, key=lambda r: r["high"]),
        "all_low": min(rows, key=lambda r: r["low"]),
        "cur": cur,
        "vs_high": _round(_pct(cur, max(r["high"] for r in rows))),
        "vs_low": _round(_pct(cur, min(r["low"] for r in rows))),
        "pctile": _round(bisect.bisect_left(closes, cur) / len(closes) * 100, 0),
        "close_range": [closes[0], closes[len(closes) // 4], closes[len(closes) // 2],
                        closes[3 * len(closes) // 4], closes[-1]],
        "yearly_closes": [(y, v[-1]["date"], v[-1]["close"]) for y, v in sorted(yearly.items())],
    }
    return out


def annual_pb(yearly_closes, annual_zyzb, cur_price, cur_bps):
    """年度 PB：年末收盘 / 该年末 BPS（年报数据）。"""
    bps = {}
    for r in annual_zyzb:
        try:
            bps[str(r["REPORT_YEAR"])] = float(r["BPS"])
        except (KeyError, TypeError, ValueError):
            continue
    rows = []
    for y, d, c in yearly_closes:
        if y in bps:
            rows.append((y, c, bps[y], _round(c / bps[y], 2)))
    rows = [r for r in rows if r[0] >= "2017"]
    pbs = [r[3] for r in rows]
    return {
        "table": rows,
        "min": min(pbs) if pbs else None,
        "avg": _round(sum(pbs) / len(pbs), 2) if pbs else None,
        "max": max(pbs) if pbs else None,
        "cur": _round(cur_price / cur_bps, 2) if cur_bps else None,
    }


def valuation_stats(vrows):
    """估值序列统计。vrows: list[(date, pe, pb)]"""
    if not vrows:
        return {}
    vrows.sort()
    pes = sorted(r[1] for r in vrows)
    pbs = sorted(r[2] for r in vrows)
    def pct(vals, v):
        return _round(bisect.bisect_left(vals, v) / len(vals) * 100, 0)
    return {
        "start": vrows[0][0], "end": vrows[-1][0], "n": len(vrows),
        "pe": vrows[-1][1], "pb": vrows[-1][2],
        "pe_pct": pct(pes, vrows[-1][1]), "pb_pct": pct(pbs, vrows[-1][2]),
        "pe_range": [pes[0], pes[len(pes) // 4], pes[len(pes) // 2],
                     pes[3 * len(pes) // 4], pes[-1]],
        "pb_range": [pbs[0], pbs[len(pbs) // 4], pbs[len(pbs) // 2],
                     pbs[3 * len(pbs) // 4], pbs[-1]],
    }


def financial_summary(qrows):
    """主要财务指标摘要。qrows: zyzb type=0 数据（按报告期倒序）。"""
    def g(r, k):
        return r.get(k)

    rows = []
    for r in qrows[:6]:
        rows.append({
            "period": r.get("REPORT_DATE_NAME", ""),
            "rev": g(r, "TOTALOPERATEREVE"), "rev_yoy": g(r, "TOTALOPERATEREVETZ"),
            "np": g(r, "PARENTNETPROFIT"), "np_yoy": g(r, "PARENTNETPROFITTZ"),
            "np_deduct": g(r, "KCFJCXSYJLR"), "np_deduct_yoy": g(r, "KCFJCXSYJLRTZ"),
            "gm": g(r, "XSMLL"), "roe": g(r, "ROEJQ"), "debt": g(r, "ZCFZL"),
            "eps": g(r, "EPSJB"), "bps": g(r, "BPS"),
            "ocf": g(r, "MGJYXJJE"), "ocf_yoy": g(r, "MGJYXJJETZ"),
            "ld": g(r, "LD"), "sd": g(r, "SD"), "roic": g(r, "ROIC"),
        })
    return rows


def quarter_split(qrows):
    """最近三个单季拆分（Q1/Q2/Q3）。qrows 需覆盖 3 期（如三季报/中报/一季报）。"""
    qrows = sorted(qrows, key=lambda r: str(r.get("REPORT_DATE", "")))[-3:]
    if len(qrows) < 3:
        return None
    def v(r, k):
        return float(r.get(k) or 0)
    a, b, c = qrows  # Q1, Q2(累计), Q3(累计)
    return [
        {"q": "Q1", "rev": v(a, "TOTALOPERATEREVE"), "np": v(a, "PARENTNETPROFIT"),
         "np_deduct": v(a, "KCFJCXSYJLR")},
        {"q": "Q2", "rev": v(b, "TOTALOPERATEREVE") - v(a, "TOTALOPERATEREVE"),
         "np": v(b, "PARENTNETPROFIT") - v(a, "PARENTNETPROFIT"),
         "np_deduct": v(b, "KCFJCXSYJLR") - v(a, "KCFJCXSYJLR")},
        {"q": "Q3", "rev": v(c, "TOTALOPERATEREVE") - v(b, "TOTALOPERATEREVE"),
         "np": v(c, "PARENTNETPROFIT") - v(b, "PARENTNETPROFIT"),
         "np_deduct": v(c, "KCFJCXSYJLR") - v(b, "KCFJCXSYJLR")},
    ]


def ttm_deduct(qrows):
    """TTM 扣非净利 = 最新4期滚动。qrows 需含 三季报/中报/一季报 + 上年年报。"""
    by = {r.get("REPORT_DATE", "")[:10]: r for r in qrows}
    keys = sorted(by)
    if len(keys) < 4:
        return None
    latest, prev3 = keys[-1], keys[-4:]
    tot = sum(float(by[k].get("KCFJCXSYJLR") or 0) for k in prev3)
    # TTM = 本年最新 + 上年年报 - 上年同期
    year = latest[:4]
    same = f"{int(year) - 1}-09-30"
    annual = f"{int(year) - 1}-12-31"
    if same not in by or annual not in by:
        return None
    val = (float(by[latest].get("KCFJCXSYJLR") or 0)
           + float(by[annual].get("KCFJCXSYJLR") or 0)
           - float(by[same].get("KCFJCXSYJLR") or 0))
    return val


def one_off_flag(fin):
    """检测最新报告期是否含大额非经常性收益。"""
    latest = fin[0] if fin else None
    if not latest:
        return ""
    np_, npd = latest.get("np"), latest.get("np_deduct")
    if not np_ or not npd:
        return ""
    gap = abs(float(np_) - float(npd))
    if float(np_) > 0 and gap / abs(float(np_)) > 0.5:
        d_yoy = latest.get("np_deduct_yoy") or 0
        if float(d_yoy) < 0:
            return ("⚠️ 最新报告期归母净利含大额非经常性收益（约 %.1f 亿），"
                    "表观利润严重失真；扣非净利同比 %+.1f%%，扣非口径才是经营真相。"
                    % (gap / 1e8, float(d_yoy)))
        return ("⚠️ 最新报告期归母净利含大额非经常性收益（约 %.1f 亿），"
                "需重点核查收益来源与可持续性。" % (gap / 1e8))
    return ""


def dividends(fhyx, price, days=365):
    """近 N 天实施的现金分红（每股合计 + 股息率）。fhyx: 分红方案列表。"""
    import re
    total, items = 0.0, []
    now = datetime.now()
    for r in fhyx or []:
        if r.get("ASSIGN_PROGRESS") != "实施方案":
            continue
        ex = r.get("EX_DIVIDEND_DATE")
        if not ex:
            continue
        try:
            d = datetime.strptime(ex[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if (now - d).days > days:
            continue
        m = re.search(r"10派([\d.]+)元", r.get("IMPL_PLAN_PROFILE") or "")
        if m:
            per = float(m.group(1)) / 10
            total += per
            items.append((ex[:10], per, r.get("IMPL_PLAN_PROFILE", "")))
    return {"per_share": _round(total, 3), "yield": _round(total / price * 100, 2) if price else None,
            "items": items}


def holder_trend(hn_rows):
    """股东户数趋势。hn_rows: holdernum 数据。"""
    if not hn_rows:
        return []
    out = []
    for r in hn_rows[:12]:
        try:
            out.append((str(r.get("END_DATE"))[:10], int(r.get("HOLDER_NUM") or 0)))
        except (TypeError, ValueError):
            continue
    out.sort()
    return out


def scan_announcements(ann_list, latest_n=40):
    """公告扫描：只保留重大事件类标题，按日期倒序。"""
    kws = ("出售", "并购", "收购", "重组", "回购", "增持", "减持", "质押", "分红",
           "利润分配", "业绩预告", "业绩快报", "异动", "问询", "战略", "合作",
           "投资", "注销", "变更", "股东会", "换届", "处罚", "风险")
    seen = set()
    rows = []
    for a in ann_list or []:
        title = a.get("title") or ""
        if any(k in title for k in kws):
            key = (a.get("notice_date"), title)
            if key in seen:
                continue
            seen.add(key)
            rows.append((str(a.get("notice_date"))[:10], title, a.get("art_code")))
    return rows[:latest_n]
