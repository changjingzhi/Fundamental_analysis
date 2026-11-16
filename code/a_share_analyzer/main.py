# -*- coding: utf-8 -*-
"""A 股基本面 + 股价走势分析底稿生成工具

用法:
    python main.py 002701 奥瑞金
    python main.py 002611 东方精工 --out "D:\\股票分析\\2026_11_14_东方精工" --kline-beg 20110101

输出:
    <输出目录>/<名称><代码>基本面与股价走势分析_底稿.md   八章数据底稿
    <输出目录>/raw_data.json                          原始抓取数据（供排查/二次分析）
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetcher
import analyzer
import report


def _safe(name, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] {name} 抓取失败: {e}")
        return None


def run(code, name, out, kline_beg):
    print(f"== 开始分析 {name}({code}) ==")

    q = _safe("实时行情", fetcher.quote, code) or {}
    price = q.get("f43")

    k_adj = analyzer.parse_kline(_safe("前复权日线", fetcher.kline, code, 1, "20100101") or [])
    k_full = analyzer.parse_kline(_safe("不复权全历史日线", fetcher.kline, code, 0, kline_beg) or [])
    zy_q = _safe("季度财务指标", fetcher.zyzb, code, 0) or []
    zy_a = _safe("年度财务指标", fetcher.zyzb, code, 1) or []
    comp = _safe("公司概况", fetcher.company, code) or {}
    biz = _safe("主营构成", fetcher.business, code) or {}
    bon = _safe("分红数据", fetcher.bonus, code) or {}
    hol = _safe("股东数据", fetcher.holders, code) or {}
    hnum = _safe("股东户数历史", fetcher.holdernum, code) or []
    val = _safe("估值序列", fetcher.valuation, code) or []
    ann = _safe("公告列表", fetcher.announcements, code, "2025-08-01", "2050-01-01", 100) or []

    # ---------------- 计算 ----------------
    tech = analyzer.technical(k_adj)
    hist = analyzer.yearly_history(k_full)
    vrows = []
    for d in val:
        try:
            pe, pb = float(d.get("PE_TTM") or 0), float(d.get("PB_MRQ") or 0)
            if pe > 0 and pb > 0:
                vrows.append((d["TRADE_DATE"][:10], pe, pb))
        except (TypeError, ValueError, KeyError):
            continue
    vs = analyzer.valuation_stats(vrows)

    fin = analyzer.financial_summary(zy_q)
    quarter = analyzer.quarter_split(zy_q)
    ttm = analyzer.ttm_deduct(zy_q)
    mcap = q.get("f116")
    cur_bps = (zy_q[0].get("BPS") if zy_q and zy_q[0].get("BPS") is not None
               else (q.get("f92")))
    ann_pb = analyzer.annual_pb(hist["yearly_closes"], zy_a, price or 0, float(cur_bps or 0) or None)
    div = analyzer.dividends(bon.get("fhyx"), price or 0)
    holder_hist = analyzer.holder_trend(hnum)
    ann_scan = analyzer.scan_announcements(ann)
    one_off = analyzer.one_off_flag(fin)
    pe_deduct = round(float(mcap) / ttm, 1) if mcap and ttm else None

    # 主营构成（最新两个报告期、按产品）
    biz_rows = []
    try:
        seen = set()
        for r in biz.get("zygcfx") or []:
            if r.get("MAINOP_TYPE") != 1:
                continue
            period = str(r.get("REPORT_DATE") or "")[:10]
            if period in seen:
                continue
            seen.add(period)
            biz_rows.append((period, r.get("ITEM_NAME"), r.get("MAIN_BUSINESS_INCOME"),
                             r.get("MBI_RATIO")))
            if len(seen) >= 2:
                break
    except Exception:
        pass

    data = {
        "code": code, "name": name, "quote": q, "jbzl": (comp.get("jbzl") or [{}])[0],
        "tech": tech, "hist": hist, "val": vs, "fin": fin, "quarter": quarter,
        "ttm_deduct": ttm, "pe_deduct": pe_deduct, "ann_pb": ann_pb, "div": div,
        "holder_hist": holder_hist, "ann_scan": ann_scan, "one_off": one_off,
        "sdgd": hol.get("sdgd") or [], "fhyx": bon.get("fhyx") or [],
        "biz_rows": biz_rows,
    }

    # ---------------- 输出 ----------------
    os.makedirs(out, exist_ok=True)
    md_path = os.path.join(out, f"{name}{code}基本面与股价走势分析_底稿.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report.build(data))
    raw_path = os.path.join(out, "raw_data.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # ---------------- 控制台摘要 ----------------
    print(f"== 完成。底稿: {md_path}")
    print(f"收盘价 {price} | 总市值 {mcap/1e8 if mcap else '-':.1f} 亿 | PB {vs.get('pb')} | "
          f"PE(TTM) {vs.get('pe')} | 扣非PE {pe_deduct} | 股息率 {div.get('yield')}%")
    print(f"52周: {tech['y52_low']['low']}~{tech['y52_high']['high']} | "
          f"年初至今 {tech['ytd']['chg']}% | 近一年 {tech['chg_1y']}%")
    if fin:
        r = fin[0]
        print(f"最新报告期 {r['period']}: 营收 {r['rev']/1e8:.2f} 亿({r['rev_yoy']:+.1f}%) | "
              f"归母 {r['np']/1e8:.2f} 亿({r['np_yoy']:+.1f}%) | "
              f"扣非 {r['np_deduct']/1e8:.2f} 亿({r['np_deduct_yoy']:+.1f}%)")
    if one_off:
        print(">>> " + one_off)
    return md_path


def main():
    ap = argparse.ArgumentParser(description="A股基本面+股价走势分析底稿生成器")
    ap.add_argument("code", help="股票代码，如 002701")
    ap.add_argument("name", help="股票名称，如 奥瑞金")
    ap.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    ap.add_argument("--kline-beg", default="19900101",
                    help="不复权K线起始日（默认 19900101）")
    args = ap.parse_args()
    run(args.code, args.name, args.out, args.kline_beg)


if __name__ == "__main__":
    main()
