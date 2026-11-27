# -*- coding: utf-8 -*-
"""2026-11-27 收盘 ETF 补抓（新浪 hq.sinajs.cn，东财限流时备用）。"""
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

CODES = [
    ("sh512800", "银行ETF"), ("sh512000", "券商ETF"), ("sh515220", "煤炭ETF"),
    ("sh512660", "军工ETF"), ("sz159928", "消费ETF"), ("sh512170", "医疗ETF"),
    ("sh515790", "光伏ETF"), ("sh515120", "创新药ETF"), ("sh512480", "半导体ETF"),
    ("sh512760", "芯片ETF"),
]
url = "https://hq.sinajs.cn/list=" + ",".join(c for c, _ in CODES)
req = urllib.request.Request(url, headers={
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
})
raw = urllib.request.urlopen(req, timeout=20).read().decode("gbk", "ignore")

print(f"{'ETF':10s} {'现价':>8s} {'涨跌%':>8s} {'成交额(亿)':>10s}")
for line in raw.strip().split("\n"):
    if '="' not in line:
        continue
    code = line.split("hq_str_")[1].split("=")[0]
    label = next((n for c, n in CODES if c == code), code)
    body = line.split('="')[1].rstrip('";')
    f = body.split(",")
    if len(f) < 10 or not f[3]:
        print(f"{label:10s} EMPTY")
        continue
    try:
        price, prev = float(f[3]), float(f[2])
        amount = float(f[9])
        pct = (price / prev - 1) * 100 if prev else 0
        print(f"{label:10s} {price:>8.3f} {pct:>+7.2f}% {amount/1e8:>10.1f}")
    except (ValueError, IndexError):
        print(f"{label:10s} PARSE_FAIL {body[:60]}")
