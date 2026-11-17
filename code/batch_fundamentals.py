# -*- coding: utf-8 -*-
"""股票池基本面速览（批量）。

用法:
    python batch_fundamentals.py <股票清单文件> --out <输出目录>

清单文件：每行第 1 列为带市场前缀的代码（如 sh.603127）或纯 6 位代码，
          第 2 列（可选）为名称；以 # 开头的行为注释。

对每只股票抓取：行情/行业 + 最新季报主要指标 + 近 3 年年报 ROE + 5 年 PE/PB 分位，
输出 <输出目录>/池基本面速览.md 与 .csv。
"""
import argparse
import csv
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "a_share_analyzer"))

import fetcher  # noqa: E402

QUOTE_FIELDS = "f43,f57,f58,f116,f117,f127,f162,f167,f168,f173,f92"


def parse_codes(path):
    out = []
    with open(path, encoding="utf-8-sig") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = ln.replace("\t", " ").split()
            raw = parts[0]
            code = raw.split(".")[-1]
            if not code.isdigit() or len(code) != 6:
                continue
            name = parts[1] if len(parts) > 1 else ""
            out.append((code, name))
    return out


def _f(x, n=2):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return round(v, n)


def _pct(vals, v):
    if v is None or not vals:
        return None
    vals = sorted(vals)
    import bisect
    return round(bisect.bisect_left(vals, v) / len(vals) * 100, 0)


def fetch_one(code, name):
    row = {"code": code, "name": name}
    try:
        q = fetcher._get(
            "https://push2.eastmoney.com/api/qt/stock/get"
            f"?secid={fetcher.secid(code)}&invt=2&fltt=2&fields={QUOTE_FIELDS}"
        ).get("data") or {}
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {code} 行情失败: {e}")
        q = {}
    row["name"] = row["name"] or q.get("f58") or "-"
    row["industry"] = q.get("f127") or "-"
    row["price"] = _f(q.get("f43"))
    row["mcap"] = round(q["f116"] / 1e8, 1) if q.get("f116") else None
    row["bps"] = _f(q.get("f92"), 3)

    # 最新季报 + 近三年年报
    try:
        zy_q = fetcher.zyzb(code, 0) or []
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {code} 季报失败: {e}")
        zy_q = []
    try:
        zy_a = fetcher.zyzb(code, 1) or []
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {code} 年报失败: {e}")
        zy_a = []

    if zy_q:
        r = zy_q[0]
        row["period"] = r.get("REPORT_DATE_NAME") or str(r.get("REPORT_DATE"))[:10]
        row["rev"] = round((r.get("TOTALOPERATEREVE") or 0) / 1e8, 2)
        row["rev_yoy"] = _f(r.get("TOTALOPERATEREVETZ"), 1)
        row["np"] = round((r.get("PARENTNETPROFIT") or 0) / 1e8, 2)
        row["np_yoy"] = _f(r.get("PARENTNETPROFITTZ"), 1)
        row["npd"] = round((r.get("KCFJCXSYJLR") or 0) / 1e8, 2)
        row["npd_yoy"] = _f(r.get("KCFJCXSYJLRTZ"), 1)
        row["gm"] = _f(r.get("XSMLL"), 1)
        row["roe"] = _f(r.get("ROEJQ"), 2)
        row["debt"] = _f(r.get("ZCFZL"), 1)
        row["ocfps"] = _f(r.get("MGJYXJJE"), 2)

    # TTM 扣非（最新季报 + 上年年报 - 上年同期）
    try:
        by = {str(x.get("REPORT_DATE"))[:10]: x for x in zy_q}
        keys = sorted(by)
        if keys:
            latest = keys[-1]
            y = int(latest[:4])
            same, ann = f"{y - 1}-{latest[5:]}", f"{y - 1}-12-31"
            if same in by and ann in by:
                ttm = (float(by[latest].get("KCFJCXSYJLR") or 0)
                       + float(by[ann].get("KCFJCXSYJLR") or 0)
                       - float(by[same].get("KCFJCXSYJLR") or 0))
                row["ttm_npd"] = round(ttm / 1e8, 2)
                if ttm > 0 and row.get("mcap"):
                    row["pe_deduct"] = round(row["mcap"] / (ttm / 1e8), 1)
    except Exception:  # noqa: BLE001
        pass

    # 近三年年报 ROE / 增速
    if zy_a:
        hist = []
        for r in zy_a[:4]:
            hist.append((str(r.get("REPORT_DATE"))[:4],
                         _f(r.get("ROEJQ"), 1),
                         _f(r.get("TOTALOPERATEREVETZ"), 1),
                         _f(r.get("PARENTNETPROFITTZ"), 1)))
        row["roe_hist"] = hist

    # 估值序列（5 年）
    try:
        val = fetcher.valuation(code, page_size=1300) or []
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {code} 估值失败: {e}")
        val = []
    pes, pbs = [], []
    for d in val:
        try:
            pe, pb = float(d.get("PE_TTM") or 0), float(d.get("PB_MRQ") or 0)
        except (TypeError, ValueError):
            continue
        if pe > 0:
            pes.append(pe)
        if pb > 0:
            pbs.append(pb)
    if val:
        row["val_date"] = str(val[0].get("TRADE_DATE"))[:10]
        row["pe"] = _f(val[0].get("PE_TTM"), 2)
        row["pb"] = _f(val[0].get("PB_MRQ"), 2)
        row["pe_pct"] = _pct(pes, row["pe"])
        row["pb_pct"] = _pct(pbs, row["pb"])
        row["pe_min"] = _f(min(pes), 1) if pes else None
        row["pe_max"] = _f(max(pes), 1) if pes else None
        row["pb_min"] = _f(min(pbs), 2) if pbs else None
        row["pb_max"] = _f(max(pbs), 2) if pbs else None
    return row


HEAD = [
    ("code", "代码"), ("name", "名称"), ("industry", "行业"), ("price", "现价"),
    ("mcap", "总市值(亿)"), ("pe", "PE(TTM)"), ("pb", "PB"), ("pe_deduct", "扣非PE"),
    ("pe_pct", "PE分位%"), ("pb_pct", "PB分位%"), ("roe", "ROE(加权)"),
    ("rev_yoy", "营收YoY%"), ("np_yoy", "归母YoY%"), ("npd_yoy", "扣非YoY%"),
    ("gm", "毛利率%"), ("debt", "负债率%"), ("period", "最新报告期"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool", help="股票清单文件")
    ap.add_argument("--out", default=".", help="输出目录")
    args = ap.parse_args()

    codes = parse_codes(args.pool)
    print(f"共 {len(codes)} 只待抓取")
    rows = []
    for i, (code, name) in enumerate(codes, 1):
        t0 = time.time()
        r = fetch_one(code, name)
        rows.append(r)
        print(f"[{i}/{len(codes)}] {code} {r['name']} {r.get('industry')} "
              f"PE {r.get('pe')} PB {r.get('pb')} ROE {r.get('roe')} ({time.time()-t0:.1f}s)")

    os.makedirs(args.out, exist_ok=True)
    md = os.path.join(args.out, "池基本面速览.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(h for _, h in HEAD) + " |\n")
        f.write("|" + "---|" * len(HEAD) + "\n")
        for r in rows:
            f.write("| " + " | ".join(
                "-" if r.get(k) is None else str(r.get(k)) for k, _ in HEAD) + " |\n")
        f.write("\n\n## 近三年年报 ROE / 营收增速 / 净利增速\n\n")
        for r in rows:
            f.write(f"- **{r['name']}({r['code']})**：" + " ｜ ".join(
                f"{y}: ROE {roe}% / 营收 {rev:+}% / 净利 {np:+}%"
                for y, roe, rev, np in (r.get("roe_hist") or []) if y) + "\n")
    csv_path = os.path.join(args.out, "池基本面速览.csv")
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k, _ in HEAD] + ["roe_hist", "ttm_npd", "val_date"],
                           extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\n输出: {md}\n输出: {csv_path}")


if __name__ == "__main__":
    main()
