# -*- coding: utf-8 -*-
"""2026-11-18 A股市场风格快照数据抓取（专用：直接构造 secid，绕过 market_of 误判）。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

BEG, END = "20261105", "20500101"
DAYS = ["2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19"]


def kline_sec(sec, beg=BEG, end=END):
    fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={sec}"
           f"&fields1=f1,f2,f3,f4,f5,f6&fields2={fields2}&klt=101&fqt=0"
           f"&beg={beg}&end={end}")
    data = fetcher._get(url).get("data")
    return data.get("klines") if data else []


def parse(rows):
    out = {}
    for r in rows:
        p = r.split(",")
        out[p[0]] = p
    return out


# ---------- 1. 风格指数 ----------
INDEXES = [
    ("1.000922", "中证红利"),
    ("1.000016", "上证50"),
    ("1.000300", "沪深300"),
    ("1.000001", "上证指数"),
    ("0.399001", "深证成指"),
    ("1.000852", "中证1000"),
    ("0.399006", "创业板指"),
    ("1.000688", "科创50"),
    ("0.399986", "中证银行"),
]

print("=" * 78)
print("一、风格指数（涨跌% / 成交额亿）")
print("=" * 78)
idx = {}
for sec, label in INDEXES:
    rows = parse(kline_sec(sec))
    idx[sec] = rows
    cells = []
    for d in DAYS:
        r = rows.get(d)
        if r:
            cells.append(f"{d[5:]}: {r[8]}% / {float(r[6])/1e8:,.0f}亿")
    print(f"{label:6s} | " + " | ".join(cells))

# ---------- 2. 行业板块（东财行业板块全量，抓 11-18 涨跌） ----------
print()
print("=" * 78)
print("二、东财行业板块 2026-11-18 涨跌（取 code 后逐个拉日线）")
print("=" * 78)
try:
    clist = fetcher._get(
        "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&fltt=2&invt=2"
        "&fid=f3&fs=m:90+t:2&fields=f12,f14"
    ).get("data", {}).get("diff", [])
    blocks = [(d["f12"], d["f14"]) for d in clist if d.get("f12", "").startswith("BK")]
    print(f"行业板块数量: {len(blocks)}")
    res = []
    for bk, name in blocks:
        rows = parse(kline_sec(f"90.{bk}"))
        r = rows.get("2026-11-18")
        if r:
            res.append((float(r[8]), name, float(r[6]) / 1e8, rows.get("2026-11-16"), rows.get("2026-11-17")))
    res.sort(reverse=True)
    print("\n-- 11-18 涨幅前 12 --")
    for pct, name, amt, r16, r17 in res[:12]:
        d16 = f"{float(r16[8]):+.2f}%" if r16 else "-"
        d17 = f"{float(r17[8]):+.2f}%" if r17 else "-"
        print(f"  {name:8s} {pct:+6.2f}%  成交{amt:6.0f}亿  (11-16: {d16}  11-17: {d17})")
    print("\n-- 11-18 跌幅前 12 --")
    for pct, name, amt, r16, r17 in res[-12:]:
        d16 = f"{float(r16[8]):+.2f}%" if r16 else "-"
        d17 = f"{float(r17[8]):+.2f}%" if r17 else "-"
        print(f"  {name:8s} {pct:+6.2f}%  成交{amt:6.0f}亿  (11-16: {d16}  11-17: {d17})")
except Exception as e:  # noqa: BLE001
    print(f"[warn] 板块抓取失败: {e}")

# ---------- 3. 银行个股 11-18 ----------
print()
print("=" * 78)
print("三、银行个股 2026-11-18 涨跌（16 家）")
print("=" * 78)
BANKS = [
    ("601398", "工商银行"), ("601288", "农业银行"), ("601939", "建设银行"),
    ("601988", "中国银行"), ("601658", "邮储银行"), ("601328", "交通银行"),
    ("600036", "招商银行"), ("601166", "兴业银行"), ("600000", "浦发银行"),
    ("601818", "光大银行"), ("600016", "民生银行"), ("601009", "南京银行"),
    ("600926", "杭州银行"), ("002142", "宁波银行"), ("601077", "渝农商行"),
    ("600928", "西安银行"),
]
bank_rows = []
for code, name in BANKS:
    sec = ("1." if code.startswith("6") else "0.") + code
    rows = parse(kline_sec(sec))
    r = rows.get("2026-11-18")
    if r:
        bank_rows.append((float(r[8]), name, r))
bank_rows.sort(reverse=True)
for pct, name, r in bank_rows:
    print(f"  {name:6s} {pct:+6.2f}%   收 {r[2]}   成交 {float(r[6])/1e8:5.1f}亿")

# ---------- 4. 涨停/跌停池（11-18） ----------
print()
print("=" * 78)
print("四、11-18 涨停/跌停家数（东财涨停板行情）")
print("=" * 78)
for label, api in [("涨停", "getTopicZTPool"), ("跌停", "getTopicDTPool")]:
    try:
        url = (f"https://push2ex.eastmoney.com/{api}?ut=7eea3edcaed734bea9cbfc24409ed989"
               f"&dpt=wz.ztzt&Pageindex=0&pagesize=1000&sort=fbt%3Aasc&date=20261118&_=1")
        d = fetcher._get(url).get("data")
        total = d.get("tc") if d else None
        print(f"  {label}家数: {total}")
    except Exception as e:  # noqa: BLE001
        print(f"  {label}抓取失败: {e}")
