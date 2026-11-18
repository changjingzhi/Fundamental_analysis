# -*- coding: utf-8 -*-
"""波动率与周期长度对比：用真实数据说明「为什么有的票震、有的票稳」。"""
import os
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

TARGETS = [
    ("600033", "福建高速", "1"), ("601006", "大秦铁路", "1"), ("600941", "中国移动", "1"),
    ("600036", "招商银行", "1"), ("600176", "中国巨石", "1"), ("603969", "银龙股份", "1"),
    ("603986", "兆易创新", "1"), ("603629", "利通电子", "1"), ("600356", "恒丰纸业", "1"),
    ("399986", "中证银行", "0"), ("000688", "科创50", "1"),
]


def load(code, mkt):
    sec = f"{mkt}.{code}"
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={sec}&fields1=f1,f2,f3,f4,f5,f6"
           "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
           "&klt=101&fqt=1&beg=20240101&end=20500101")
    d = fetcher._get(url).get("data") or {}
    return [x.split(",") for x in (d.get("klines") or [])]


def stats(rows):
    closes = [float(r[2]) for r in rows]
    rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    last = rets[-250:] if len(rets) > 250 else rets
    vol = statistics.pstdev(last) * (252 ** 0.5) * 100
    # 近 250 日最大回撤
    c = closes[-250:] if len(closes) > 250 else closes
    peak, mdd = c[0], 0.0
    for x in c:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    # 月度涨跌
    months = {}
    for r in rows:
        months[r[0][:7]] = float(r[2])
    ms = sorted(months)
    mret = [months[ms[i]] / months[ms[i - 1]] - 1 for i in range(1, len(ms))]
    # 单边最长连续（同向）天数
    longest, cur = 1, 1
    for i in range(1, len(rets)):
        if (rets[i] > 0) == (rets[i - 1] > 0):
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 1
    return {
        "vol": round(vol, 1), "mdd": round(mdd * 100, 1),
        "max_m": round(max(mret) * 100, 1) if mret else None,
        "min_m": round(min(mret) * 100, 1) if mret else None,
        "longest": longest, "n": len(rets),
    }


print("| 标的 | 近250日年化波动率 | 近250日最大回撤 | 最好单月 | 最差单月 | 最长单边天数 |")
print("|---|---|---|---|---|---|")
out = []
for code, name, mkt in TARGETS:
    try:
        rows = load(code, mkt)
        s = stats(rows)
        out.append((name, s))
        print(f"| {name} | **{s['vol']}%** | {s['mdd']}% | {s['max_m']}% | {s['min_m']}% | {s['longest']} |")
    except Exception as e:  # noqa: BLE001
        print(f"| {name} | 失败 {e} | | | | |")
