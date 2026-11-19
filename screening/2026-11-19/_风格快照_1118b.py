# -*- coding: utf-8 -*-
"""2026-11-18 快照补抓：银行个股 + 行业板块（带延时与容错）。"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

BEG, END = "20261110", "20500101"
DAY = "2026-11-18"


def kline_sec(sec, retries=3):
    fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={sec}"
           f"&fields1=f1,f2,f3,f4,f5,f6&fields2={fields2}&klt=101&fqt=0"
           f"&beg={BEG}&end={END}")
    for i in range(retries):
        try:
            data = fetcher._get(url).get("data")
            return data.get("klines") if data else []
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (i + 1))
    return []


# ---------- 银行个股 ----------
BANKS = [
    ("601398", "工商银行"), ("601288", "农业银行"), ("601939", "建设银行"),
    ("601988", "中国银行"), ("601658", "邮储银行"), ("601328", "交通银行"),
    ("600036", "招商银行"), ("601166", "兴业银行"), ("600000", "浦发银行"),
    ("601818", "光大银行"), ("600016", "民生银行"), ("601009", "南京银行"),
    ("600926", "杭州银行"), ("002142", "宁波银行"), ("601077", "渝农商行"),
    ("600928", "西安银行"),
]
print("三、银行个股 2026-11-18 涨跌（16 家）")
bank_rows = []
for code, name in BANKS:
    sec = ("1." if code.startswith("6") else "0.") + code
    rows = kline_sec(sec)
    rec = None
    for r in rows:
        p = r.split(",")
        if p[0] == DAY:
            rec = p
            break
    if rec:
        bank_rows.append((float(rec[8]), name, rec))
    time.sleep(0.35)
bank_rows.sort(reverse=True)
for pct, name, r in bank_rows:
    print(f"  {name:6s} {pct:+6.2f}%   收 {r[2]}   成交 {float(r[6])/1e8:5.1f}亿")
print(f"  [抓取成功 {len(bank_rows)}/16]")

# ---------- 行业板块 ----------
print()
print("二、东财行业板块 2026-11-18 涨跌")
blocks = []
try:
    clist = fetcher._get(
        "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&fltt=2&invt=2"
        "&fid=f3&fs=m:90+t:2&fields=f12,f14"
    ).get("data", {}).get("diff", [])
    blocks = [(d["f12"], d["f14"]) for d in clist if str(d.get("f12", "")).startswith("BK")]
except Exception as e:  # noqa: BLE001
    print(f"[warn] 板块清单失败: {e}")
print(f"板块数量: {len(blocks)}")

res = []
for i, (bk, name) in enumerate(blocks):
    rows = kline_sec(f"90.{bk}")
    rec = None
    for r in rows:
        p = r.split(",")
        if p[0] == DAY:
            rec = p
            break
    if rec:
        hist = {}
        for r in rows:
            p = r.split(",")
            hist[p[0]] = float(p[8])
        res.append((float(rec[8]), name, float(rec[6]) / 1e8,
                    hist.get("2026-11-16"), hist.get("2026-11-17")))
    time.sleep(0.35)
    if (i + 1) % 20 == 0:
        print(f"  ... {i+1}/{len(blocks)}")

res.sort(reverse=True)
print(f"\n成功 {len(res)}/{len(blocks)}")
print("\n-- 11-18 涨幅前 15 --")
for pct, name, amt, d16, d17 in res[:15]:
    print(f"  {name:10s} {pct:+6.2f}%  成交{amt:6.0f}亿   11-16: {d16:+6.2f}%  11-17: {d17:+6.2f}%")
print("\n-- 11-18 跌幅前 15 --")
for pct, name, amt, d16, d17 in res[-15:]:
    print(f"  {name:10s} {pct:+6.2f}%  成交{amt:6.0f}亿   11-16: {d16:+6.2f}%  11-17: {d17:+6.2f}%")
