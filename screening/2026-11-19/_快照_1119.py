# -*- coding: utf-8 -*-
"""2026-11-19 市场快照：指数与板块代理 ETF（实时 + 日线）。"""
import os
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

print(f"抓取时间: {datetime.now():%Y-%m-%d %H:%M:%S}")

# ---------- 实时快照 ----------
QF = "f43,f46,f47,f48,f58,f60,f169,f170"  # 现价/今开/成交量/成交额/名称/昨收/涨跌额/涨跌幅


def q(sec):
    url = (f"https://push2.eastmoney.com/api/qt/stock/get?secid={sec}"
           f"&invt=2&fltt=2&fields={QF}")
    try:
        return fetcher._get(url).get("data") or {}
    except Exception as e:  # noqa: BLE001
        return {"err": str(e)[:80]}


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
print("\n== 指数实时 ==")
print(f"{'指数':8s} {'现价':>10s} {'涨跌%':>8s} {'成交额(亿)':>10s}")
for sec, label in INDEXES:
    d = q(sec)
    if d.get("err"):
        print(f"{label:8s} FAIL {d['err']}")
    else:
        amt = d.get("f48")
        amt = f"{amt/1e8:,.0f}" if isinstance(amt, (int, float)) else "-"
        print(f"{label:8s} {d.get('f43'):>10} {d.get('f170'):>8}% {amt:>10s}")
    time.sleep(0.3)

ETFS = [
    ("1.512800", "银行ETF"),
    ("1.512000", "券商ETF"),
    ("1.515220", "煤炭ETF"),
    ("1.512480", "半导体ETF"),
    ("1.512760", "芯片ETF"),
    ("1.512660", "军工ETF"),
    ("0.159928", "消费ETF"),
    ("1.512170", "医疗ETF"),
    ("1.515790", "光伏ETF"),
    ("1.515120", "创新药ETF"),
]
print("\n== 板块代理 ETF 实时 ==")
print(f"{'ETF':10s} {'现价':>8s} {'涨跌%':>8s} {'成交额(亿)':>10s}")
for sec, label in ETFS:
    d = q(sec)
    if d.get("err"):
        print(f"{label:10s} FAIL")
    else:
        amt = d.get("f48")
        amt = f"{amt/1e8:.1f}" if isinstance(amt, (int, float)) else "-"
        print(f"{label:10s} {d.get('f43'):>8} {d.get('f170'):>8}% {amt:>10s}")
    time.sleep(0.3)

# ---------- 日线（确认 11-19 是否为完整交易日数据） ----------
print("\n== 指数日线近 3 日 ==")


def kline_sec(sec, beg="20261110", end="20500101"):
    fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={sec}"
           f"&fields1=f1,f2,f3,f4,f5,f6&fields2={fields2}&klt=101&fqt=0"
           f"&beg={beg}&end={end}")
    try:
        data = fetcher._get(url).get("data")
        return data.get("klines") if data else []
    except Exception:  # noqa: BLE001
        return []


for sec, label in INDEXES[:6]:
    ks = kline_sec(sec)
    tail = ks[-3:] if ks else []
    parts = []
    for r in tail:
        p = r.split(",")
        parts.append(f"{p[0][5:]}: {p[8]}% / {float(p[6])/1e8:,.0f}亿")
    print(f"{label:8s} | " + " | ".join(parts))
    time.sleep(0.3)
