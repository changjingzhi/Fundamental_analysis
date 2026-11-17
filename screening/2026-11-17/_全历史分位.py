# -*- coding: utf-8 -*-
"""全历史 PE/PB 分位检验：验证「估值处于历史最底部」这一说法。

对清单内每只股票分页拉取 RPT_VALUEANALYSIS_DET 全历史估值序列，
计算当前 PE(TTM)/PB(MRQ) 在上市以来全样本中的分位，并给出历史最低值及其日期。
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

CODES = [
    ("603969", "银龙股份"), ("603986", "兆易创新"), ("603588", "高能时代"),
    ("603045", "福达合金"), ("601138", "工业富联"), ("600176", "中国巨石"),
    ("603629", "利通电子"), ("600601", "方正科技"), ("605277", "新亚电子"),
    ("603127", "昭衍新药"), ("601890", "亚星锚链"), ("601218", "吉鑫科技"),
    ("603506", "南都物业"), ("600768", "富邦新材"), ("603507", "振江股份"),
    ("605138", "盛泰集团"),
]


def pages(code, size=500, maxp=20):
    out = []
    for p in range(1, maxp + 1):
        url = ("https://datacenter.eastmoney.com/securities/api/data/v1/get"
               "?reportName=RPT_VALUEANALYSIS_DET&columns=ALL"
               f"&filter=(SECURITY_CODE%3D%22{code}%22)"
               f"&pageNumber={p}&pageSize={size}&sortTypes=-1&sortColumns=TRADE_DATE"
               "&source=WEB&client=WEB")
        res = fetcher._get(url).get("result") or {}
        d = res.get("data") or []
        out += d
        if len(d) < size:
            break
    return out


def pct(vals, v):
    import bisect
    if not vals or v is None:
        return None
    return round(bisect.bisect_left(vals, v) / len(vals) * 100, 1)


def main():
    print("| 名称 | 样本区间 | 交易日 | PE(TTM) | PE全历史分位 | PE历史最低(日期) "
          "| PB | PB全历史分位 | PB历史最低(日期) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for code, name in CODES:
        try:
            rows = pages(code)
        except Exception as e:  # noqa: BLE001
            print(f"| {name} | 抓取失败: {e} | | | | | | | |")
            continue
        pe, pb, dates = [], [], []
        for r in rows:
            try:
                p = float(r.get("PE_TTM"))
                b = float(r.get("PB_MRQ"))
            except (TypeError, ValueError):
                continue
            d = str(r.get("TRADE_DATE"))[:10]
            if p > 0:
                pe.append((p, d))
            if b > 0:
                pb.append((b, d))
            dates.append(d)
        if not pe or not pb:
            print(f"| {name} | 无数据 | | | | | | | |")
            continue
        cur = rows[0]
        cur_pe, cur_pb = float(cur.get("PE_TTM") or 0), float(cur.get("PB_MRQ") or 0)
        pe_v = sorted(x[0] for x in pe)
        pb_v = sorted(x[0] for x in pb)
        pe_min = min(pe)
        pb_min = min(pb)
        print(f"| {name} | {min(dates)}~{max(dates)} | {len(dates)} "
              f"| {cur_pe:.2f} | **{pct(pe_v, cur_pe)}%** "
              f"| {pe_min[0]:.2f}（{pe_min[1]}） "
              f"| {cur_pb:.2f} | **{pct(pb_v, cur_pb)}%** "
              f"| {pb_min[0]:.2f}（{pb_min[1]}） |")


if __name__ == "__main__":
    main()
