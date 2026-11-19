# -*- coding: utf-8 -*-
"""11-18 行业板块代理：行业 ETF 日线（板块日线接口被限流）。"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

BEG, END = "20261110", "20500101"

ETFS = [
    ("1.512800", "银行ETF"),
    ("1.512000", "券商ETF"),
    ("1.515220", "煤炭ETF"),
    ("1.512480", "半导体ETF"),
    ("1.512760", "芯片ETF"),
    ("1.512660", "军工ETF"),
    ("0.159928", "消费ETF"),
    ("1.512170", "医疗ETF"),
    ("1.512400", "有色ETF"),
    ("1.515790", "光伏ETF"),
    ("0.159611", "电力ETF"),
    ("1.515210", "钢铁ETF"),
    ("0.159806", "新能源车ETF"),
    ("1.512980", "传媒ETF"),
    ("1.515120", "创新药ETF"),
    ("1.516160", "新能源ETF"),
]


def kline_sec(sec, retries=3):
    fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={sec}"
           f"&fields1=f1,f2,f3,f4,f5,f6&fields2={fields2}&klt=101&fqt=1"
           f"&beg={BEG}&end={END}")
    for i in range(retries):
        try:
            data = fetcher._get(url).get("data")
            return data.get("klines") if data else []
        except Exception:  # noqa: BLE001
            time.sleep(1.2 * (i + 1))
    return []


rows = []
ok = 0
for sec, name in ETFS:
    ks = kline_sec(sec)
    hist = {}
    for r in ks:
        p = r.split(",")
        hist[p[0]] = (float(p[8]), float(p[6]) / 1e8)
    if hist:
        ok += 1
    d16 = hist.get("2026-11-16", (None, None))
    d17 = hist.get("2026-11-17", (None, None))
    d18 = hist.get("2026-11-18", (None, None))
    rows.append((name, d16, d17, d18))
    time.sleep(0.3)

print(f"成功 {ok}/{len(ETFS)}")
print(f"{'ETF':10s} {'11-16':>8s} {'11-17':>8s} {'11-18':>8s}  {'11-18成交(亿)':>12s}")
# 按 11-18 排序
rows.sort(key=lambda x: (x[3][0] if x[3][0] is not None else -99), reverse=True)
for name, d16, d17, d18 in rows:
    f = lambda v: f"{v:+.2f}%" if v is not None else "  -  "  # noqa: E731
    amt = f"{d18[1]:.1f}" if d18[1] is not None else "-"
    print(f"{name:10s} {f(d16[0]):>8s} {f(d17[0]):>8s} {f(d18[0]):>8s}  {amt:>12s}")
