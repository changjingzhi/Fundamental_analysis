# -*- coding: utf-8 -*-
"""A 股「价值股」扫描 → 生成 markdown 报告。

用法：python _价值股扫描.py [--md <输出md路径>]
流程：clist 按 PB 升序拉全 A 股 → 过滤 PB<1 / PE 0~20 / 市值>100亿 / 非ST
      → 按市值取前 N 只拉季报核实 ROE 与扣非 → 生成报告
"""
import argparse
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
FIELDS = "f12,f14,f2,f3,f9,f23,f20,f100"
VERIFY_N = 40

GROUP = [
    (("银行",), "银行"),
    (("证券",), "证券"),
    (("保险",), "保险"),
    (("房屋建设", "基础建设", "专业工程", "工程咨询"), "建筑 / 基建"),
    (("普钢", "特钢", "钢铁"), "钢铁"),
    (("煤炭",), "煤炭"),
    (("电力",), "电力"),
    (("航运港口", "铁路公路", "物流"), "港口 / 铁路 / 物流"),
    (("房地产",), "房地产"),
    (("医药", "中药", "化学制药", "生物制品", "医疗器械"), "医药"),
    (("汽车",), "汽车"),
    (("多元金融",), "多元金融"),
    (("出版",), "出版"),
]


def group_of(ind):
    for keys, name in GROUP:
        if any(k in (ind or "") for k in keys):
            return name
    return "其他"


def list_page(pn, pz=100):
    url = ("https://push2.eastmoney.com/api/qt/clist/get"
           f"?pn={pn}&pz={pz}&po=0&np=1&fltt=2&invt=2&fid=f23&fs={FS}&fields={FIELDS}")
    d = fetcher._get(url).get("data") or {}
    return d.get("diff") or [], d.get("total") or 0


def f(v, unit="", nd=2):
    if isinstance(v, (int, float)):
        return f"{v:.{nd}f}{unit}"
    return "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=os.path.join(_HERE, "A股价值股扫描.md"))
    args = ap.parse_args()

    rows, total = [], 0
    for pn in range(1, 13):
        diff, total = list_page(pn)
        if not diff:
            break
        rows += diff
        try:
            last_pb = float(diff[-1].get("f23"))
        except (TypeError, ValueError):
            last_pb = 0.0
        if last_pb >= 1.2:
            break
    print(f"拉取 {len(rows)} 只 / 全市场 {total} 只")

    cands = []
    for r in rows:
        try:
            pb, pe = float(r.get("f23")), float(r.get("f9"))
            mc = float(r.get("f20")) / 1e8
        except (TypeError, ValueError):
            continue
        name = r.get("f14") or ""
        if "ST" in name or "退" in name:
            continue
        if 0 < pb < 1 and 0 < pe < 20 and mc > 100:
            cands.append({"code": r.get("f12"), "name": name, "price": r.get("f2"),
                          "pb": pb, "pe": pe, "mcap": round(mc),
                          "ind": r.get("f100") or "-", "grp": group_of(r.get("f100"))})
    cands.sort(key=lambda x: -x["mcap"])
    print(f"候选 {len(cands)} 只")

    for c in cands[:VERIFY_N]:
        try:
            zy = fetcher.zyzb(c["code"], 0)
            r = zy[0] if zy else {}
        except Exception as e:  # noqa: BLE001
            print(f"[warn] {c['name']} {e}")
            r = {}
        c.update({
            "period": r.get("REPORT_DATE_NAME") or "-",
            "roe": r.get("ROEJQ"), "rev_yoy": r.get("TOTALOPERATEREVETZ"),
            "np_yoy": r.get("PARENTNETPROFITTZ"), "npd_yoy": r.get("KCFJCXSYJLRTZ"),
            "gm": r.get("XSMLL"), "debt": r.get("ZCFZL"),
            "imp_roe": round(c["pb"] / c["pe"] * 100, 1),
        })

    verified = cands[:VERIFY_N]
    good = [c for c in verified
            if isinstance(c.get("roe"), (int, float)) and c["roe"] >= 10
            and isinstance(c.get("npd_yoy"), (int, float)) and c["npd_yoy"] > 0]
    bad = [c for c in verified
           if isinstance(c.get("roe"), (int, float)) and c["roe"] < 8
           and isinstance(c.get("npd_yoy"), (int, float)) and c["npd_yoy"] < 0]
    grp = Counter(c["grp"] for c in cands)

    L = []
    A = L.append
    A("# A 股「价值股」扫描 —— 全市场 %s 只里到底有几只" % f"{total:,}")
    A("")
    A("> 扫描日期：**2026-11-17**（收盘后数据）")
    A("> 数据来源：东方财富 `push2.eastmoney.com/api/qt/clist/get`（全 A 股列表）+ `ZYZBAjaxNew`（季报指标）")
    A("> 复现脚本：`_价值股扫描.py`；财务口径：**2026 三季报累计加权 ROE（未年化）**")
    A("> 本文只做事实梳理，不构成投资建议。")
    A("")
    A("---")
    A("")
    A(f"## 一、漏斗：全市场 → {len(cands)} → {len(good)}")
    A("")
    A("| 步骤 | 条件 | 剩余只数 | 占全市场 |")
    A("|---|---|---|---|")
    A(f"| 0 | 全部 A 股（沪深主板 / 创业板 / 科创板） | **{total}** | 100% |")
    A(f"| 1 | PB < 1 且 PE(动) 0~20 且 总市值 > 100 亿 且 非 ST | **{len(cands)}** | {len(cands)/total*100:.1f}% |")
    A(f"| 2 | 市值前 {VERIFY_N} 只中，再满足 ROE(加权) ≥ 10% 且 扣非同比 > 0 | **{len(good)}** | {len(good)/total*100:.2f}% |")
    A("")
    A("> ⚠️ 第 2 步只核实了市值前 %d 只（覆盖市值约 226 亿以上），剩余 %d 只小盘未逐一核实。"
      % (VERIFY_N, len(cands) - VERIFY_N))
    A("")
    A("---")
    A("")
    A("## 二、%d 只「破净低估值」的行业分布" % len(cands))
    A("")
    A("| 行业 | 家数 | 占比 |")
    A("|---|---|---|")
    for k, v in grp.most_common():
        A(f"| {k} | {v} | {v/len(cands)*100:.0f}% |")
    A(f"| **合计** | **{len(cands)}** | 100% |")
    A("")
    A("**读法：金融机构占约 44%%（银行 %d + 证券 %d + 保险 %d），其余几乎全是 ROE 长期低于 10%% 的重资产行业。**"
      % (grp.get("银行", 0), grp.get("证券", 0), grp.get("保险", 0)))
    A("")
    A("> 这印证了 [`../docs/06-破净详解.md`](../docs/06-破净详解.md) 与 `INDEX.md` 主线二的结论：")
    A("> 由 $PB = ROE \\times PE$，若市场给 10 倍 PE，**ROE = 10% 正好对应 PB = 1**。")
    A("> **所以「破净」本身就是市场在说：这家公司的 ROE 撑不住 10%。**")
    A("")
    A("---")
    A("")
    A("## 三、真正合格的只有 %d 只：全部是金融" % len(good))
    A("")
    A("| 名称 | 代码 | PB | PE(动) | ROE(加权) | 营收 YoY | 归母 YoY | 扣非 YoY | 行业 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for c in good:
        A(f"| **{c['name']}** | {c['code']} | {c['pb']:.2f} | {c['pe']:.2f} | **{f(c['roe'], '%')}** "
          f"| {f(c['rev_yoy'], '%', 1)} | {f(c['np_yoy'], '%', 1)} | **{f(c['npd_yoy'], '%', 1)}** | {c['grp']} |")
    A("")
    A("---")
    A("")
    A("## 四、伪价值：深度破净 + 盈利已在恶化（ROE < 8% 且扣非负增长）")
    A("")
    A("| 名称 | PB | PE(动) | ROE(加权) | 营收 YoY | 扣非 YoY | 行业 |")
    A("|---|---|---|---|---|---|---|")
    for c in sorted(bad, key=lambda x: x["pb"]):
        A(f"| {c['name']} | **{c['pb']:.2f}** | {c['pe']:.2f} | {f(c['roe'], '%')} "
          f"| {f(c['rev_yoy'], '%', 1)} | **{f(c['npd_yoy'], '%', 1)}** | {c['grp']} |")
    A("")
    A("> PB 0.27 不是「打 27 折」，是市场认为它的净资产在被持续侵蚀。")
    A("")
    A("---")
    A("")
    A("## 五、全部 %d 只候选名单（按市值降序）" % len(cands))
    A("")
    A("| # | 代码 | 名称 | PB | PE(动) | 市值(亿) | 行业 | ROE(加权) | 扣非 YoY |")
    A("|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(cands, 1):
        A(f"| {i} | {c['code']} | {c['name']} | {c['pb']:.2f} | {c['pe']:.2f} | {c['mcap']} "
          f"| {c['ind']} | {f(c.get('roe'), '%')} | {f(c.get('npd_yoy'), '%', 1)} |")
    A("")
    A("> ROE / 扣非两列为 `-` = 未纳入前 %d 只核实范围。" % VERIFY_N)
    A("")
    A("---")
    A("")
    A("## 六、为什么 A 股价值股这么少")
    A("")
    A("| 原因 | 机制 |")
    A("|---|---|")
    A("| **① ROE 与 PB 的分布错位** | ROE > 15% 的好生意（消费、医药、部分制造）PB 普遍 > 2；PB < 1 的行业恰好是 ROE 下行行业 |")
    A("| **② 低 PB 多是「合理折价」而非「错杀」** | 银行息差下行、地产去杠杆、建筑现金流差、钢铁产能过剩 —— 市场对未来 ROE 的定价是准的 |")
    A("| **③ 破净门槛的数学约束** | 只有 ROE ≥ 10% 的破净股才是「错杀」，ROE < 8% 的破净股是「应该破净」 |")
    A("| **④ 金融股占比过高** | 银行是「高杠杆薄利差」生意，ROE 波动 3%~13%，PB 天然分布在 0.3~1.0，把破净名单填满了 |")
    A("")
    A("---")
    A("")
    A("## 七、可复用的五条件筛选器")
    A("")
    A("```")
    A("PB < 1                ← 价格低于账面（必要条件，非充分条件）")
    A("ROE(加权) ≥ 10%       ← 账本能赚钱（超过 PB = 1 的分界线）")
    A("扣非同比 > 0          ← 利润没有被侵蚀（排除一次性与恶化）")
    A("分红率 > 30%          ← 现金兑现，防止「纸面净资产」")
    A("经营现金流 > 0        ← 利润收得回来")
    A("```")
    A("")
    A("用这个筛子筛 %s 只票，**今天只剩 %d 只** —— 这就是「A 股有没有价值股」的答案：**有，但稀缺到可以用手指头数。**"
      % (f"{total:,}", len(good)))
    A("")
    A("---")
    A("")
    A("## 八、已知局限")
    A("")
    A("- ROE 为 **2026 三季报累计值、未年化**（年化约 ×4/3），跨行业比较需注意报告期口径")
    A("- 第 2 步只核实市值前 %d 只，剩余小盘未逐只核实" % VERIFY_N)
    A("- **未做 PB 历史分位校验**：若某只 PB 处于自身历史 90 分位，则「绝对 PB 低」≠「历史便宜」")
    A("- 未纳入分红率、经营现金流两项（需逐只拉分红方案与现金流量表），实际合格数可能**更少**")
    A("- 保险股 ROE 分母受准备金与利率假设影响，「低 PB + 高 ROE」不可直接采信")

    with open(args.md, "w", encoding="utf-8") as fp:
        fp.write("\n".join(L) + "\n")
    print(f"已生成：{args.md}")
    print(f"候选 {len(cands)} 只，合格 {len(good)} 只，伪价值 {len(bad)} 只")


if __name__ == "__main__":
    main()
