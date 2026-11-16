# A 股股票分析工具包（code/）

> 一键抓取东方财富公开行情 + F10 数据，自动生成"八章"基本面与股价走势分析底稿。
> 已在 002701 奥瑞金、002611 东方精工两只股票上端到端验证。

## 目录结构

```
code/
├── a_share_analyzer/          # 可复用 Python 工具包（无第三方依赖硬性要求）
│   ├── main.py                # 入口：python main.py <代码> <名称> [--out 目录]
│   ├── fetcher.py             # 东方财富数据抓取（requests 优先，失败自动退回 PowerShell）
│   ├── analyzer.py            # 技术面 / 历史 / 估值 / 财务计算
│   └── report.py              # Markdown 八章底稿生成
├── skill/
│   └── a-share-stock-analysis/
│       └── SKILL.md           # 技能定义：如何调用工具并把底稿完善成最终报告
└── README.md
```

## 快速使用

```powershell
# 环境变量（PowerShell 控制台建议设置）
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

python D:\股票分析\code\a_share_analyzer\main.py 002701 奥瑞金 --out "D:\股票分析\2026_11_13_奥瑞金"
python D:\股票分析\code\a_share_analyzer\main.py 002611 东方精工 --out "D:\股票分析\2026_11_14_东方精工"
```

输出（每个 `--out` 目录下）：

| 文件 | 内容 |
|---|---|
| `<名称><代码>基本面与股价走势分析_底稿.md` | 八章数据底稿：所有表格自动填充，【待补充】处由分析师/AI 完善 |
| `raw_data.json` | 全部原始抓取数据，供排查或二次分析 |

## 底稿包含什么（八章）

1. **公司概况**——名称/行业/董事长/股本/主营简介
2. **股价与估值快照**——收盘价、市值、PE/PB、**扣非 PE(TTM)**、股息率、52 周区间
3. **基本面分析**——近 6 期财务全景表（营收/归母/扣非+同比、毛利率/ROE/负债率）、单季拆分、主营构成、分红、十大股东、股东户数趋势
4. **股价走势分析**——年度涨跌、月度收盘、均线、量能、近 10 日、公告扫描
5. **对照解读**——估值口径甄别（表观 PE vs 扣非 PE vs 历史分位）、业绩/股价背离框架
6. **投资要点**——积极/风险/综合定位框架
7. **长期持有评估**——年度收盘史、估值赔率、适用性矩阵、跟踪清单框架
8. **免责声明**

### 内置自动诊断

- **一次性收益检测**：最新报告期归母与扣非偏离超 50% 且扣非同比下滑时，输出红色警告（如东方精工 2026 三季报"含约 35.7 亿非经常性收益，表观利润严重失真"）；
- **扣非 PE(TTM)** 自动计算（TTM 扣非净利滚动 + 总市值）；
- **估值分位**：PE/PB 近两年分位 + 2017 年以来年度 PB（最低/均值/最高）+ 不复权价格全历史分位。

## 依赖与环境

- Python 3.8+（本机 Miniconda Python 3.12 验证）；
- `requests`：**优先使用**（正确继承系统代理）。本机代理（127.0.0.1:7897）对 requests 偶发断连，此时自动退回 **PowerShell Invoke-RestMethod**（已验证稳定）；未装 requests 时同样走 PowerShell 兜底（仅 Windows）；
- 接口均为东方财富公开接口（push2/push2his/emweb/datacenter/np-anotice），无需密钥；
- 数据仅供研究参考，不构成投资建议。

## 抓取接口速查（fetcher.py）

| 函数 | 数据 |
|---|---|
| `quote(code)` | 实时行情（f43 最新价、f92 每股净资产、f116 总市值…） |
| `kline(code, fqt, beg)` | 日 K 线（fqt=1 前复权 / 0 不复权） |
| `zyzb(code, type=0/1)` | 主要财务指标（按报告期 / 仅年报） |
| `company / business / bonus / holders` | F10 公司概况 / 主营构成 / 分红 / 股东 |
| `valuation(code)` | 历史 PE/PB 序列（近 500 个交易日） |
| `holdernum(code)` | 历年股东户数 |
| `announcements(code, begin, end)` | 公告列表（含 art_code） |
| `announcement_content(art_code)` | 公告正文（HTML，可用 `strip_html` 清洗） |

## 已知限制

- 市值口径：总市值 = f116（A 股口径）；B 股/两地上市场景需人工核对；
- 公告扫描默认取最近约 15 个月、最多 100 条，关键词过滤重大事件；
- 年度 PB 用"年末收盘 / 该年末 BPS"近似，未经股本变动完全回溯；
- 东方财富 f45/f46（当日高低）与 K 线极值偶尔有 1 分钱级差异，以 K 线为准。
