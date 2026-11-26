# -*- coding: utf-8 -*-
"""2026-11-26 ETF 近 6 日线（新浪 K 线接口）。"""
import json
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ETFS = [
    ("sh512800", "银行ETF"),
    ("sh512000", "券商ETF"),
    ("sh515220", "煤炭ETF"),
    ("sh512480", "半导体ETF"),
    ("sh512760", "芯片ETF"),
    ("sh512660", "军工ETF"),
    ("sz159928", "消费ETF"),
    ("sh512170", "医疗ETF"),
    ("sh515790", "光伏ETF"),
    ("sh515120", "创新药ETF"),
]


def kline(sym, tries=3):
    url = ("https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           f"CN_MarketData.getKLineData?symbol={sym}&scale=240&ma=no&datalen=10")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = r.read().decode("utf-8", "ignore")
            return json.loads(txt)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.2 * (i + 1))
    return []


for sym, label in ETFS:
    ks = kline(sym)
    if not ks:
        print(f"{label:10s} FAIL")
        continue
    parts = []
    for i in range(len(ks) - 6, len(ks)):
        if i <= 0:
            continue
        d = ks[i]["day"][5:]
        c, pc = float(ks[i]["close"]), float(ks[i - 1]["close"])
        amt = float(ks[i].get("volume") or 0) * c / 1e8
        parts.append(f"{d}: {(c/pc-1)*100:+.2f}%/{amt:.1f}亿")
    print(f"{label:10s} | " + " | ".join(parts))
    time.sleep(0.6)
