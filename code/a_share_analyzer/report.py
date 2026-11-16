# -*- coding: utf-8 -*-
"""Markdown 报告底稿生成模块。

生成"八章"分析底稿：所有数据表自动填充；标注【待补充】的部分
由使用者（AI/分析师）结合公告正文与行业知识撰写。
"""
from datetime import datetime

CN = "%+.2f%%"


def _fmt_pct(v):
    return CN % float(v) if v is not None else "-"


def _yi(v):
    """元 -> 亿元"""
    return f"{v / 1e8:.2f} 亿" if v is not None else "-"


def _fy(v):
    """float or None -> str"""
    return f"{float(v):.2f}" if v is not None else "-"


def build(data):
    L = []
    A = L.append
    name, code = data["name"], data["code"]
    suffix = "SH" if code.startswith(("6", "9")) else "SZ"
    q = data["quote"]
    fin = data["fin"]
    tech = data["tech"]
    hist = data["hist"]
    vs = data["val"]
    today = datetime.now().strftime("%Y-%m-%d")

    price = q.get("f43")
    A(f"# {name}（{code}.{suffix}）基本面与股价走势分析报告\n")
    A(f"> **报告日期**：{today}（数据截至最新交易日 {tech.get('last_date', '-')} 收盘）\n")
    A("> **数据来源**：东方财富公开行情 / F10 数据、公司公告（本工具自动抓取）\n")
    A("> **声明**：本文仅为基于公开数据的客观梳理，不构成任何投资建议。市场有风险，投资需谨慎。\n")
    A("\n---\n")

    # ---------------- 一、公司概况 ----------------
    A("## 一、公司概况\n")
    A("| 项目 | 内容 |")
    A("|---|---|")
    A(f"| 公司全称 | {data['jbzl'].get('ORG_NAME', '-')} |")
    A(f"| 证券代码 | {code}（{data['jbzl'].get('SECURITY_TYPE', '-')}，{str(data['jbzl'].get('LISTING_DATE') or q.get('f189') or '-')[:10]} 上市） |")
    A(f"| 所属行业 | {data['jbzl'].get('EM2016', '-')} |")
    A(f"| 总部 | {data['jbzl'].get('PROVINCE', '-')} |")
    A(f"| 董事长 / 总经理 | {data['jbzl'].get('CHAIRMAN', '-')} / {data['jbzl'].get('PRESIDENT', '-')} |")
    A(f"| 员工人数 | {data['jbzl'].get('EMP_NUM', '-')} 人 |")
    A(f"| 总股本 | {(q.get('f84') or 0) / 1e8:.2f} 亿股 |")
    A(f"| 主营 | {data['jbzl'].get('ORG_PROFILE', '-')[:200]}…… |")
    A("\n【待补充】公司历史重大事件（并购/出售/暴雷/转型）梳理。\n")
    A("\n---\n")

    # ---------------- 二、股价与估值快照 ----------------
    A("## 二、股价与估值快照\n")
    A("| 指标 | 数值 |")
    A("|---|---|")
    A(f"| 最新收盘价 | **{_fy(price)} 元**（{q.get('f169'):+.2f}，{_fmt_pct(q.get('f170'))}） |")
    A(f"| 当日区间 | {_fy(q.get('f45'))} ~ {_fy(q.get('f46'))} |")
    A(f"| 成交额 / 换手率 | {_yi(q.get('f48'))} / {_fy(q.get('f168'))}% |")
    A(f"| 总市值 / 流通市值 | {_yi(q.get('f116'))} / {_yi(q.get('f117'))} |")
    A(f"| 每股净资产 | {_fy(q.get('f92'))} 元 |")
    A(f"| PE(TTM) | {_fy(data['val'].get('pe'))} 倍（详见『五、对照解读』的口径甄别） |")
    A(f"| 扣非 PE(TTM) | {_fy(data['pe_deduct'])} 倍 |")
    A(f"| 市净率 PB | {_fy(data['val'].get('pb'))} 倍 |")
    A(f"| 近 12 个月派息 | {data['div'].get('per_share', '-')} 元/股 → 股息率 {_fy(data['div'].get('yield'))}% |")
    A(f"| 52 周区间 | {_fy(tech['y52_low']['low'])} ~ {_fy(tech['y52_high']['high'])} 元 |")
    A("\n---\n")

    # ---------------- 三、基本面 ----------------
    A("## 三、基本面分析\n")
    A("### 3.1 财务全景（近 6 个报告期）\n")
    A("| 报告期 | 营收 | 同比 | 归母净利 | 同比 | 扣非净利 | 同比 | 毛利率 | ROE | 负债率 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for r in fin:
        A(f"| {r['period']} | {_yi(r['rev'])} | {_fmt_pct(r['rev_yoy'])} | {_yi(r['np'])} | {_fmt_pct(r['np_yoy'])} | {_yi(r['np_deduct'])} | {_fmt_pct(r['np_deduct_yoy'])} | {_fy(r['gm'])}% | {_fy(r['roe'])}% | {_fy(r['debt'])}% |")
    A("")
    flag = data.get("one_off")
    if flag:
        A(f"> {flag}\n")
    if data.get("biz_rows"):
        A("### 3.2 主营构成（最新报告期，按产品）\n")
        A("| 报告期 | 项目 | 收入 | 占比 |")
        A("|---|---|---|---|")
        for period, item, inc, ratio in data["biz_rows"]:
            A(f"| {period} | {item} | {_yi(inc)} | {_fy(ratio)} |")
        A("")
    qs = data.get("quarter")
    if qs:
        A("### 3.3 最近三个单季拆分\n")
        A("| 季度 | 单季营收 | 单季归母 | 单季扣非 |")
        A("|---|---|---|---|")
        for r in qs:
            A(f"| {r['q']} | {_yi(r['rev'])} | {_yi(r['np'])} | {_yi(r['np_deduct'])} |")
        A("")
    A("【待补充】季度拆分同比、非经常性损益来源（查年报/公告附注）、盈利能力与运营效率解读。\n")
    A("### 3.4 分红与股东回报\n")
    A("| 方案 | 实施进度 | 除权日 |")
    A("|---|---|---|")
    for r in data["fhyx"][:8]:
        A(f"| {r.get('IMPL_PLAN_PROFILE', '-')} | {r.get('ASSIGN_PROGRESS', '-')} | {str(r.get('EX_DIVIDEND_DATE') or '-')[:10]} |")
    A(f"\n近 12 个月实际派现合计 **{data['div'].get('per_share', '-')} 元/股**，对应当前价股息率 **{_fy(data['div'].get('yield'))}%**。\n")
    A("\n【待补充】历年分红连续性、回购/增持/员工持股等股东回报行为。\n")
    A("### 3.5 股东结构\n")
    A("| 股东 | 持股比例 |")
    A("|---|---|")
    for r in data["sdgd"][:10]:
        A(f"| {r.get('HOLDER_NAME', '-')} | {_fy(r.get('HOLD_NUM_RATIO'))}% |")
    A("")
    if data.get("holder_hist"):
        A("股东户数趋势：")
        A("| 日期 | 户数 |")
        A("|---|---|")
        for d, n in data["holder_hist"]:
            A(f"| {d} | {n:,} |")
        A("")
    A("【待补充】实际控制人/家族持股比例合计、机构参与度、散户化程度判断。\n")
    A("\n---\n")

    # ---------------- 四、股价走势 ----------------
    A("## 四、股价走势分析\n")
    A("### 4.1 近年年度涨跌幅（前复权）\n")
    A("| 年份 | 年度涨跌幅 |")
    A("|---|---|")
    for y, r in tech["yearly_ret"]:
        A(f"| {y} | **{_fmt_pct(r)}** |")
    A("")
    A(f"- 年初至今（{tech['ytd']['first_close']} → {tech['last_close']}）：**{_fmt_pct(tech['ytd']['chg'])}**，年内最大回撤 {_fy(tech['ytd'].get('mdd'))}%；")
    A(f"- 近一年涨跌幅：**{_fmt_pct(tech['chg_1y'])}**；")
    A(f"- 52 周高点 {tech['y52_high']['high']}（{tech['y52_high']['date']}），低点 {tech['y52_low']['low']}（{tech['y52_low']['date']}）；")
    hi = tech['y52_high']['high']; lo = tech['y52_low']['low']
    if hi and lo and tech.get('last_close'):
        A(f"- 距 52 周高点回撤 {_fmt_pct((tech['last_close'] / hi - 1) * 100)}，距低点反弹 {_fmt_pct((tech['last_close'] / lo - 1) * 100)}。\n")
    A("### 4.2 当月走势复盘（月度收盘）\n")
    A("| 月份 | 收盘价 |")
    A("|---|---|")
    for m, c in tech["monthly_closes"]:
        A(f"| {m} | {c} |")
    A("")
    A("【待补充】主升/主跌段催化事件（查 4.5 公告扫描：业绩预告、战略合作、并购出售等）。\n")
    A("### 4.3 技术面现状\n")
    A("| 均线 | 数值 |")
    A("|---|---|")
    for n in (5, 10, 20, 30, 60, 120, 250):
        v = tech["ma"].get(n)
        A(f"| MA{n} | {v if v is not None else '-'} |")
    A("")
    A(f"- 现价 {tech['last_close']}；近 20 日涨跌 {_fmt_pct(tech['vol'].get('ret20'))}，近 60 日涨跌 {_fmt_pct(tech['vol'].get('ret60'))}；")
    A(f"- 量能：近 20 日均量 {tech['vol']['v20']:.1f} 万手 / 近 60 日 {tech['vol']['v60']:.1f} 万手，量能比 {tech['vol'].get('ratio')}。\n")
    A("### 4.4 最近 10 个交易日\n")
    A("| 日期 | 开 | 收 | 高 | 低 | 量(万手) |")
    A("|---|---|---|---|---|---|")
    for r in tech["last10"]:
        A(f"| {r['date']} | {r['open']} | {r['close']} | {r['high']} | {r['low']} | {r['vol'] / 1e4:.1f} |")
    A("")
    A("### 4.5 公告扫描（重大事件，按时间倒序）\n")
    A("| 日期 | 标题 |")
    A("|---|---|")
    for d, t, _ in data["ann_scan"][:30]:
        A(f"| {d} | {t} |")
    A("\n【待补充】重要公告正文摘要（`fetcher.announcement_content(art_code)` 可读取全文）。\n")
    A("\n---\n")

    # ---------------- 五、对照解读 ----------------
    A("## 五、基本面与股价的对照解读\n")
    A("### 5.1 估值口径甄别（关键）\n")
    A(f"- 表面 PE(TTM)：**{_fy(vs.get('pe'))} 倍**（近两年分位 {vs.get('pe_pct')}%）；")
    if data.get("pe_deduct"):
        A(f"- **扣非 PE(TTM)：约 {_fy(data['pe_deduct'])} 倍**（TTM 扣非净利 {_yi(data.get('ttm_deduct'))}）；")
    A(f"- PB：{_fy(vs.get('pb'))} 倍（估值序列 {vs.get('start', '-')[:10]}~{vs.get('end', '-')[:10]} 分位 {vs.get('pb_pct')}%）；")
    if data.get("ann_pb"):
        apb = data["ann_pb"]
        A(f"- 年度 PB 参照（2017 年以来）：最低 {apb['min']} / 平均 {apb['avg']} / 最高 {apb['max']}；当前 {apb['cur']}。")
    A(f"- 历史价格位置：不复权全历史（{hist.get('start', '-')[:10]}~{hist.get('end', '-')[:10]}）收盘价分位 **{hist.get('pctile')}%**；历史最高 {hist['all_high']['high']}（{hist['all_high']['date']}），最低 {hist['all_low']['low']}（{hist['all_low']['date']}）。\n")
    A("【待补充】结合扣非口径与历史分位，判断当前估值真实水平（便宜/中性/昂贵）。\n")
    A("### 5.2 业绩 vs 股价背离分析\n")
    A("【待补充】归纳市场定价的核心矛盾与潜在反转观察点。\n")
    A("\n---\n")

    # ---------------- 六、投资要点 ----------------
    A("## 六、投资要点总结\n")
    A("### 积极因素 ✅\n【待补充】\n")
    A("### 风险因素 ⚠️\n【待补充】\n")
    A("### 综合定位\n【待补充】\n")
    A("\n---\n")

    # ---------------- 七、长期持有评估 ----------------
    A("## 七、长期持有可行性评估\n")
    A("### 7.1 历史教训（完整周期）\n")
    A("| 年份 | 年末收盘(不复权) |")
    A("|---|---|")
    for y, d, c in hist["yearly_closes"]:
        A(f"| {y} | {c:.2f} |")
    A("\n【待补充】结合年度财务数据（`fetcher.zyzb(code, type=1)`）标注各年重大事件与教训。\n")
    A("### 7.2 估值与赔率\n")
    A(f"- PB {_fy(vs.get('pb'))} 倍 vs 历史年度区间；价格分位 {hist.get('pctile')}%；扣非 PE 约 {_fy(data.get('pe_deduct'))} 倍；")
    A(f"- 股息率 {_fy(data['div'].get('yield'))}%（是否可持续需结合历年分红）。\n")
    A("### 7.3 适用性矩阵\n")
    A("| 类型 | 是否适合 | 理由 |")
    A("|---|---|---|")
    A("| 股息/现金流型 | 【待判断】 | |")
    A("| 逆向价值型 | 【待判断】 | |")
    A("| 成长复利型 | 【待判断】 | |")
    A("| 事件驱动型 | 【待判断】 | |")
    A("| 无跟踪躺平型 | 【待判断】 | |")
    A("")
    A("### 7.4 长期持有跟踪清单（季度验证）\n")
    A("【待补充】列出 3-5 个可量化的跟踪指标。\n")
    A("### 7.5 一句话总结\n【待补充】\n")
    A("\n---\n")

    # ---------------- 八、免责声明 ----------------
    A("## 八、免责声明\n")
    A(f"本报告基于东方财富公开行情数据与公司公开披露信息自动整理，数据截至最新交易日 {tech.get('last_date', '-')} 收盘。文中分析为客观信息梳理与中性归纳，**不构成任何买卖建议**。投资者应独立判断并自行承担投资风险。\n")
    return "\n".join(L)
