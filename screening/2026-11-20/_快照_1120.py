# -*- coding: utf-8 -*-
"""2026-11-20 市场快照：指数与板块代理 ETF（实时，收盘后即完整数据）。"""
import os
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

print(f"抓取时间: {datetime.now():%Y-%m-%d %H:%M:%S}")

QF = "f43,f46,f47,f48,f58,f60,f169,f170"


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
