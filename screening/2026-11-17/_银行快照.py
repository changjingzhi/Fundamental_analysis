# -*- coding: utf-8 -*-
"""银行板块 2026-11-17 快照：指数位置、个股估值、利率变量。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

FIELDS = "f43,f58,f60,f170,f162,f167,f116,f92,f173"


def q(sec, fields=FIELDS):
    url = (f"https://push2.eastmoney.com/api/qt/stock/get?secid={sec}"
           f"&invt=2&fltt=2&fields={fields}")
    return fetcher._get(url).get("data") or {}


BANKS = [
    ("1.601398", "工商银行"), ("1.601288", "农业银行"), ("1.601939", "建设银行"),
    ("1.601988", "中国银行"), ("1.601658", "邮储银行"), ("1.601328", "交通银行"),
    ("1.600036", "招商银行"), ("1.601166", "兴业银行"), ("1.600000", "浦发银行"),
    ("1.601818", "光大银行"), ("1.600016", "民生银行"), ("1.601009", "南京银行"),
    ("1.600926", "杭州银行"), ("1.002142", "宁波银行"), ("1.601077", "渝农商行"),
    ("1.600928", "西安银行"),
]

print("== 银行个股（2026-11-17）==")
print("名称\t价格\t涨跌%\tPB\tPE动\t市值(亿)")
pbs = []
for sec, n in BANKS:
    d = q(sec)
    pb = d.get("f167")
    if isinstance(pb, (int, float)):
        pbs.append(pb)
    mc = round((d.get("f116") or 0) / 1e8)
    print(f"{n}\t{d.get('f43')}\t{d.get('f170')}%\t{pb}\t{d.get('f162')}\t{mc}")
print(f"等权平均 PB = {sum(pbs)/len(pbs):.3f}（{len(pbs)} 家样本）")

print("\n== 利率与风格指数 ==")
for sec, label in [("100.CN10Y", "中国10Y国债(候选1)"), ("100.CGB10Y", "候选2"),
                   ("90.BK0475", "银行Ⅱ板块"), ("1.000922", "中证红利"),
                   ("1.000300", "沪深300"), ("1.000688", "科创50")]:
    d = q(sec, "f43,f58,f170")
    print(f"{label}\t{d}")

print("\n== 中证银行指数位置 ==")
rows = [x.split(",") for x in fetcher.kline("399986", 0, "20260101", "20500101")]
c = [float(r[2]) for r in rows]
print(f"起始 {rows[0][0]} 收 {rows[0][2]} → 最新 {rows[-1][0]} 收 {rows[-1][2]}")
print(f"2026 YTD {c[-1]/c[0]-1:+.2%}")
print(f"距 2025-07-10 高点 8497.84：{c[-1]/8497.84-1:+.2%}")
for n in (5, 20, 60, 120):
    if len(c) > n:
        print(f"近 {n} 日：{c[-1]/c[-1-n]-1:+.2%}")
# 近 3 日成交额
print("近 5 日成交额(亿)：")
for r in rows[-5:]:
    print(f"  {r[0]}  收 {r[2]}  涨跌 {r[8]}%  成交额 {float(r[6])/1e8:.0f} 亿")
