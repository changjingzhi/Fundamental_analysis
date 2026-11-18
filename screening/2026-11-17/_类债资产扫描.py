# -*- coding: utf-8 -*-
"""A 股「类债配置品」扫描 → 生成 markdown 报告。

筛法：
  1. 取公用事业/交运/通信/出版类行业板块的成分股
  2. 硬条件：总市值 > 80 亿、PE(动) 0~25、PB < 3
  3. 逐只核实：近 12 个月股息率、ROE(加权)、资产负债率、每股经营现金流/每股收益
  4. 打分为「类债成色」：股息率、现金含量、杠杆、ROE 稳定性
"""
import argparse
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402
import analyzer  # noqa: E402

# 目标行业板块（名称关键字）
TARGET_BOARDS = ("高速公路", "铁路公路", "港口", "航运港口", "机场",
                 "火力发电", "水力发电", "燃气", "水务", "电信运营商", "出版")

FIELDS = "f12,f14,f2,f3,f9,f23,f20,f100,f8"


def board_list():
    out = []
    for pn in range(1, 7):
        url = ("https://push2.eastmoney.com/api/qt/clist/get"
               f"?pn={pn}&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f12,f14")
        d = fetcher._get(url).get("data") or {}
        rows = d.get("diff") or []
        out += rows
        if len(rows) < 100:
            break
    return out


def board_stocks(bk, pz=100):
    url = ("https://push2.eastmoney.com/api/qt/clist/get"
           f"?pn=1&pz={pz}&po=1&np=1&fltt=2&invt=2&fid=f20&fs=b:{bk}&fields={FIELDS}")
    d = fetcher._get(url).get("data") or {}
    return d.get("diff") or []


def f(v, unit="", nd=2):
    return f"{v:.{nd}f}{unit}" if isinstance(v, (int, float)) else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=os.path.join(_HERE, "类债资产扫描.md"))
    args = ap.parse_args()

    boards = board_list()
    picked = [(b["f12"], b["f14"]) for b in boards
              if any(k in (b.get("f14") or "") for k in TARGET_BOARDS)]
    print("目标板块：", picked)

    seen, pool = {}, []
    for bk, name in picked:
        for r in board_stocks(bk):
            code = r.get("f12")
            if not code or code in seen:
                continue
            try:
                mc = float(r.get("f20")) / 1e8
                pe = float(r.get("f9"))
                pb = float(r.get("f23"))
            except (TypeError, ValueError):
                continue
            nm = r.get("f14") or ""
            if "ST" in nm or "退" in nm or mc < 80 or not (0 < pe < 25) or not (0 < pb < 3):
                continue
            if code.startswith(("2", "9")):      # 剔除 B 股
                continue
            seen[code] = True
            pool.append({"code": code, "name": nm, "price": r.get("f2"), "pe": pe,
                         "pb": pb, "mcap": round(mc), "ind": r.get("f100") or name,
                         "pct": r.get("f3"), "turn": r.get("f8")})
    pool.sort(key=lambda x: -x["mcap"])
    print(f"池子 {len(pool)} 只，逐只核实…")

    for c in pool:
        try:
            bon = fetcher.bonus(c["code"]) or {}
            div = analyzer.dividends(bon.get("fhyx"), c["price"] or 0)
            zy = fetcher.zyzb(c["code"], 0)
            r = zy[0] if zy else {}
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {c['name']} {e}")
            div, r = {}, {}
        c["div_yield"] = div.get("yield")
        c["div_ps"] = div.get("per_share")
        c["roe"] = r.get("ROEJQ")
        c["debt"] = r.get("ZCFZL")
        c["ocfps"] = r.get("MGJYXJJE")
        c["period"] = r.get("REPORT_DATE_NAME") or "-"
        c["eps_ttm"] = round(c["price"] / c["pe"], 3) if c.get("price") and c["pe"] else None
        c["ocf_ratio"] = (round(c["ocfps"] / c["eps_ttm"], 2)
                          if isinstance(c.get("ocfps"), (int, float)) and c.get("eps_ttm") else None)

    # 类债成色分级
    def kind(c):
        ind = c.get("ind") or ""
        nm = c.get("name") or ""
        if "航运" in ind and "港" not in nm:
            return "伪类债（周期航运）"
        if any(k in ind for k in ("高速公路", "铁路", "港口", "水务", "水力发电",
                                  "出版", "电信运营商", "大众出版", "教育出版",
                                  "通信服务", "通信")) or "港" in nm:
            return "真类债（特许经营）"
        if any(k in ind for k in ("火力发电", "燃气", "机场", "热力", "电力")):
            return "准类债（公用但周期）"
        return "其他"

    def grade(c):
        y, o, d, roe = c.get("div_yield"), c.get("ocf_ratio"), c.get("debt"), c.get("roe")
        if not all(isinstance(x, (int, float)) for x in (y, o, d, roe)):
            return "数据不全"
        score = 0
        score += 3 if y >= 4 else 2 if y >= 3 else 1 if y >= 2 else 0
        score += 2 if o >= 1.5 else 1 if o >= 1.0 else 0
        score += 2 if d <= 50 else 1 if d <= 70 else 0
        score += 2 if 6 <= roe <= 16 else 1 if roe > 0 else 0
        star = ("★★★★★" if score >= 8 else "★★★★" if score >= 7 else
                "★★★" if score >= 5 else "★★" if score >= 3 else "★")
        # 硬门槛：现金含量不足或杠杆过高，不允许上四星
        if o < 0.8 or d > 70:
            star = star if star in ("★", "★★") else "★★"
        # 准类债星级上限：火电/燃气存在周期波动
        if kind(c) == "准类债（公用但周期）" and star == "★★★★★":
            star = "★★★★"
        return star

    for c in pool:
        c["grade"] = grade(c)
        c["kind"] = kind(c)

    good = [c for c in pool if c["grade"] in ("★★★★★", "★★★★")]
    good.sort(key=lambda x: -(x.get("div_yield") or 0))

    def rows_of(kd, stars=("★★★★★", "★★★★")):
        return sorted([c for c in pool if c["kind"] == kd and c["grade"] in stars],
                      key=lambda x: -(x.get("div_yield") or 0))

    grp = Counter(c["ind"] for c in pool)

    L = []
    A = L.append
    A("# A 股「类债配置品」扫描 —— 谁是真债券替代，谁是伪高股息")
    A("")
    A("> 扫描日期：**2026-11-17**（收盘后数据）")
    A("> 数据来源：东方财富行情/行业板块接口 + F10 分红融资接口 + 季报指标接口")
    A("> 复现脚本：`_类债资产扫描.py`；财务口径：**2026 三季报加权 ROE、每股经营现金流（未年化）**")
    A("> 股息率 = 近 12 个月已实施现金分红 ÷ 当前股价")
    A("> 本文只做事实梳理，不构成投资建议。")
    A("")
    A("---")
    A("")
    A("## 一、什么叫「类债配置品」：五个条件")
    A("")
    A("| # | 条件 | 判据 | 为什么 |")
    A("|---|---|---|---|")
    A("| 1 | **收入可预测** | 特许经营/政府定价/刚需 | 债券的核心是现金流确定性 |")
    A("| 2 | **现金含量高** | 每股经营现金流 ÷ EPS > 1.2 | 折旧大、几乎无再投资，赚的是现金 |")
    A("| 3 | **杠杆可控且在下降** | 资产负债率 < 50%，趋势向下 | 债券的对手方风险 |")
    A("| 4 | **股息率有溢价** | ≥ 3%，且高于 10Y 国债 | 否则不如直接买国债 |")
    A("| 5 | **ROE 稳定但不高** | 6%~16% | 高了说明有成长（不该按债定价），低了说明资产在损耗 |")
    A("")
    A("> ⚠️ 与「高股息股」的区别：高股息可能是周期顶部的一次性派息（如煤炭、航运），")
    A("> **类债品的股息必须来自稳定的特许经营现金流**。")
    A("")
    A("---")
    A("")
    A("## 二、扫描范围与池子")
    A("")
    A("| 项 | 内容 |")
    A("|---|---|")
    A(f"| 覆盖行业板块 | {', '.join(n for _, n in picked)} |")
    A(f"| 硬条件 | 总市值 > 80 亿、PE(动) 0~25、PB < 3、非 ST |")
    A(f"| 入围池子 | **{len(pool)} 只** |")
    A("")
    A("按行业分布：")
    A("")
    A("| 行业 | 只数 |")
    A("|---|---|")
    for k, v in grp.most_common():
        A(f"| {k} | {v} |")
    A("")
    A("---")
    A("")
    A(f"## 三、真类债（特许经营）：★★★★ 以上 {len(rows_of('真类债（特许经营）'))} 只")
    A("")
    A("| 名称 | 代码 | 行业 | 股息率 | PB | PE | ROE(加权) | 负债率 | OCF/EPS | 成色 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for c in rows_of("真类债（特许经营）"):
        A(f"| **{c['name']}** | {c['code']} | {c['ind']} | **{f(c['div_yield'], '%')}** "
          f"| {c['pb']:.2f} | {c['pe']:.2f} | {f(c['roe'], '%')} "
          f"| {f(c['debt'], '%', 1)} | {f(c['ocf_ratio'], '×')} | {c['grade']} |")
    A("")
    A("## 四、准类债（公用事业但受成本/价格管制）：★★★★ 以上 %d 只" % len(rows_of("准类债（公用但周期）")))
    A("")
    A("| 名称 | 代码 | 行业 | 股息率 | PB | PE | ROE(加权) | 负债率 | OCF/EPS | 成色 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for c in rows_of("准类债（公用但周期）"):
        A(f"| {c['name']} | {c['code']} | {c['ind']} | {f(c['div_yield'], '%')} "
          f"| {c['pb']:.2f} | {c['pe']:.2f} | {f(c['roe'], '%')} "
          f"| {f(c['debt'], '%', 1)} | {f(c['ocf_ratio'], '×')} | {c['grade']} |")
    A("")
    A("> **准类债的共同弱点**：燃料成本（火电）与顺价机制（燃气）会把利润拉回均值。")
    A("> 尤其是**火电股当前 ROE 处于周期高位**（大唐发电 15.7%、华能国际 9.3%），")
    A("> 高股息与高 ROE 同时出现时，恰恰意味着均值回归的风险在累积。")
    A("")
    A("## 五、伪类债（周期航运的高股息）：★☆ 一律需警惕")
    A("")
    A("| 名称 | 代码 | 行业 | 股息率 | PB | PE | ROE(加权) | 负债率 | OCF/EPS | 成色 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted([x for x in pool if x["kind"] == "伪类债（周期航运）"],
                    key=lambda x: -(x.get("div_yield") or 0)):
        A(f"| {c['name']} | {c['code']} | {c['ind']} | {f(c['div_yield'], '%')} "
          f"| {c['pb']:.2f} | {c['pe']:.2f} | {f(c['roe'], '%')} "
          f"| {f(c['debt'], '%', 1)} | {f(c['ocf_ratio'], '×')} | {c['grade']} |")
    A("")
    A("> 航运股的股息率是「运价周期的高点分红」，运价一跌分红跟着消失 —— 与煤炭、钢铁同属「伪类债」。")
    A("")
    A("---")
    A("")
    A(f"## 六、全部 {len(pool)} 只池子明细（按市值降序）")
    A("")
    A("| # | 代码 | 名称 | 类型 | 行业 | 现价 | PB | PE(动) | 市值(亿) | 股息率 | ROE(加权) | 负债率 | OCF/EPS | 成色 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(pool, 1):
        A(f"| {i} | {c['code']} | {c['name']} | {c['kind']} | {c['ind']} | {c['price']} | {c['pb']:.2f} "
          f"| {c['pe']:.2f} | {c['mcap']} | {f(c['div_yield'], '%')} | {f(c['roe'], '%')} "
          f"| {f(c['debt'], '%', 1)} | {f(c['ocf_ratio'], '×')} | {c['grade']} |")
    A("")
    A("---")
    A("")
    A("## 七、怎么读这张表（三类必须区分）")
    A("")
    A("| 类型 | 特征 | 处理方式 |")
    A("|---|---|---|")
    A("| **真类债**（特许经营 + 现金流稳） | 高速公路、港口、水电、水务、出版 | 股息率 3.5% 以上分批配置，本质是「含通胀条款的永续债」 |")
    A("| **准类债**（有周期但波动小） | 火电、燃气、通信运营商 | 需跟踪燃料成本/顺价机制/资本开支周期 |")
    A("| **伪类债**（周期顶部高股息） | 煤炭、航运、部分钢铁 | 股息率会随盈利崩塌，是「周期股的低 PE 陷阱」 |")
    A("")
    A("---")
    A("")
    A("## 八、已知局限")
    A("")
    A("- 股息率只统计**近 12 个月已实施**的现金分红，未考虑未来分红政策变化")
    A("- ROE 与每股经营现金流为 **2026 三季报累计值**，未年化")
    A("- **未纳入 10 年期国债收益率**做溢价比较（数据缺口，见 `../../INDEX.md` 第六节）")
    A("- 高速公路/水电的**特许经营到期日**未纳入评分，而这是资产久期的核心变量")
    A("- 未剔除「一次性大额分红」导致的股息率虚高")

    with open(args.md, "w", encoding="utf-8") as fp:
        fp.write("\n".join(L) + "\n")
    print(f"已生成：{args.md}")
    print(f"池子 {len(pool)} 只，★★★★ 以上 {len(good)} 只")
    for c in good[:12]:
        print(f"  {c['name']}({c['code']}) 股息率 {c['div_yield']}% PB {c['pb']} "
              f"ROE {c['roe']} 负债率 {c['debt']} OCF/EPS {c['ocf_ratio']} {c['grade']}")


if __name__ == "__main__":
    main()
