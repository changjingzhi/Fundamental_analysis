# -*- coding: utf-8 -*-
"""东方财富公开数据抓取模块。

抓取顺序：requests（继承系统代理）→ 失败时退回 PowerShell Invoke-RestMethod
（本机代理对 PowerShell 连接更稳定）。两种方式都不可用时抛出异常。
"""
import json
import subprocess
import sys
import time

try:
    import requests as _requests
    HAVE_REQUESTS = True
except ImportError:  # pragma: no cover
    _requests = None
    HAVE_REQUESTS = False

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Encoding": "identity",
    "Accept": "*/*",
}


def _get_requests(url, timeout):
    r = _requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _get_powershell(url, timeout):
    """PowerShell Invoke-RestMethod 兜底（Windows）。"""
    if sys.platform != "win32":
        raise RuntimeError("requests 失败且当前非 Windows，无法使用 PowerShell 兜底")
    ps = (
        "$ProgressPreference='SilentlyContinue';"
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        "$h=@{'User-Agent'='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'};"
        f"(Invoke-RestMethod -Uri '{url}' -Headers $h -TimeoutSec {timeout})"
        " | ConvertTo-Json -Depth 12 -Compress"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=timeout + 60)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("PowerShell 兜底超时") from e
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode("utf-8", "ignore")[:300])
    return json.loads(out.stdout.decode("utf-8-sig"))


def _get(url, timeout=30, retries=3):
    last = None
    for i in range(retries):
        try:
            if HAVE_REQUESTS:
                return _get_requests(url, timeout)
            break
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1 + i)
    # requests 路径失败（或不可用），走 PowerShell 兜底
    return _get_powershell(url, timeout)


def market_of(code):
    """6/9 开头为上交所(secid 市场号 1)，其余按深交所(0)。"""
    return "1" if code.startswith(("6", "9")) else "0"


def secid(code):
    return f"{market_of(code)}.{code}"


def scode(code):
    return ("SH" if market_of(code) == "1" else "SZ") + code


# ---------------- 行情 ----------------

def quote(code):
    """实时行情快照。"""
    fields = "f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f62,f84,f85,f92,f116,f117,f162,f167,f168,f169,f170,f171,f173,f184,f185,f186,f187,f188,f189,f190"
    url = f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid(code)}&invt=2&fltt=2&fields={fields}"
    return _get(url).get("data")


def kline(code, fqt=1, beg="19900101", end="20500101"):
    """日 K 线。fqt=1 前复权 / 0 不复权。返回原始字符串列表。"""
    fields2 = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid(code)}"
           f"&fields1=f1,f2,f3,f4,f5,f6&fields2={fields2}&klt=101&fqt={fqt}"
           f"&beg={beg}&end={end}")
    data = _get(url).get("data")
    return data.get("klines") if data else []


# ---------------- F10 ----------------

def zyzb(code, typ=0):
    """主要财务指标。typ=0 按报告期(季度+年报) / typ=1 仅年报。"""
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type={typ}&code={scode(code)}"
    return _get(url).get("data") or []


def company(code):
    """公司概况。"""
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax?code={scode(code)}"
    return _get(url)


def business(code):
    """主营构成。"""
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code={scode(code)}"
    return _get(url)


def bonus(code):
    """分红方案与历史。"""
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/BonusFinancing/PageAjax?code={scode(code)}"
    return _get(url)


def holders(code):
    """十大股东 / 股东户数 / 机构持股。"""
    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax?code={scode(code)}"
    return _get(url)


# ---------------- 数据中心 ----------------

def valuation(code, page_size=500):
    """历史 PE/PB 估值序列。"""
    url = (f"https://datacenter.eastmoney.com/securities/api/data/v1/get"
           f"?reportName=RPT_VALUEANALYSIS_DET&columns=ALL"
           f"&filter=(SECURITY_CODE%3D%22{code}%22)"
           f"&pageNumber=1&pageSize={page_size}&sortTypes=-1&sortColumns=TRADE_DATE"
           f"&source=WEB&client=WEB")
    res = _get(url).get("result")
    return res.get("data") if res else []


def holdernum(code, page_size=60):
    """历年股东户数。"""
    url = (f"https://datacenter.eastmoney.com/securities/api/data/v1/get"
           f"?reportName=RPT_HOLDERNUM_DET&columns=SECURITY_CODE,END_DATE,HOLDER_NUM"
           f"&filter=(SECURITY_CODE%3D%22{code}%22)"
           f"&pageNumber=1&pageSize={page_size}&sortTypes=-1&sortColumns=END_DATE"
           f"&source=WEB&client=WEB")
    res = _get(url).get("result")
    return res.get("data") if res else []


# ---------------- 公告 ----------------

def announcements(code, begin=None, end=None, page_size=50, page_index=1):
    """公告列表（含 art_code）。"""
    url = (f"https://np-anotice-stock.eastmoney.com/api/security/ann?sr=-1"
           f"&page_size={page_size}&page_index={page_index}&ann_type=A&client_source=web"
           f"&stock_list={code}&f_node=0&s_node=0")
    if begin:
        url += f"&begin_time={begin}"
    if end:
        url += f"&end_time={end}"
    return _get(url).get("data", {}).get("list") or []


def announcement_content(art_code):
    """公告正文（HTML，含 <p> 标签）。"""
    url = (f"https://np-cnotice-stock.eastmoney.com/api/content/ann"
           f"?art_code={art_code}&client_source=web&page_index=1")
    data = _get(url).get("data") or {}
    return data.get("notice_content") or ""


def strip_html(html):
    """去掉公告正文 HTML 标签。"""
    import re
    text = re.sub(r"<[^>]+>", "", html or "")
    return text.replace("&nbsp;", " ").replace("&amp;", "&")
