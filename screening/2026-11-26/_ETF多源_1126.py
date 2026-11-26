# -*- coding: utf-8 -*-
"""2026-11-26 ETF 抓取（多源重试：东财 push2 → 新浪 hq.sinajs.cn）。"""
import json
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

ETFS = [
    ("1.512800", "sh512800", "银行ETF"),
    ("1.512000", "sh512000", "券商ETF"),
    ("1.515220", "sh515220", "煤炭ETF"),
    ("1.512480", "sh512480", "半导体ETF"),
    ("1.512760", "sh512760", "芯片ETF"),
    ("1.512660", "sh512660", "军工ETF"),
    ("0.159928", "sz159928", "消费ETF"),
    ("1.512170", "sh512170", "医疗ETF"),
    ("1.515790", "sh515790", "光伏ETF"),
    ("1.515120", "sh515120", "创新药ETF"),
]


def em(sec, tries=6):
    url = (f"https://push2.eastmoney.com/api/qt/stock/get?secid={sec}"
           f"&invt=2&fltt=2&fields=f43,f48,f58,f60,f170")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read().decode())["data"]
            if d:
                return {"price": d.get("f43"), "pct": d.get("f170"), "amt": d.get("f48")}
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.5 + i)
    return None


def sina(sym, tries=3):
    url = f"https://hq.sinajs.cn/list={sym}"
    h = dict(UA)
    h["Referer"] = "https://finance.sina.com.cn"
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = r.read().decode("gbk", "ignore")
            body = txt.split('"')[1]
            if not body:
                return None
            p = body.split(",")
            # ETF: 名称,今开,昨收,现价,最高,最低,...,成交量(股),成交额(元)
            prev, price, amt = float(p[2]), float(p[3]), float(p[9])
            return {"price": price, "pct": round((price / prev - 1) * 100, 2), "amt": amt,
                    "name": p[0]}
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1.2)
    return None


print(f"{'ETF':10s} {'价格':>8s} {'涨跌%':>8s} {'成交额(亿)':>10s}  源")
for sec, sym, label in ETFS:
    d = em(sec)
    src = "eastmoney"
    if not d:
        d = sina(sym)
        src = "sina"
    if not d:
        print(f"{label:10s} FAIL")
        continue
    amt = d.get("amt")
    amt = f"{amt/1e8:.1f}" if isinstance(amt, (int, float)) else "-"
    print(f"{label:10s} {d.get('price'):>8} {d.get('pct'):>8} {amt:>10s}  {src}")
    time.sleep(0.8)
