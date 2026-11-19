# -*- coding: utf-8 -*-
"""测试东财板块日线接口可达性。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

tests = [
    ("无额外头", "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=90.BK0475"
     "&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
     "&klt=101&fqt=1&beg=20261110&end=20500101"),
    ("push2 非 his", "https://push2.eastmoney.com/api/qt/stock/kline/get?secid=90.BK0475"
     "&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
     "&klt=101&fqt=1&beg=20261110&end=20500101"),
    ("板块行情快照", "https://push2.eastmoney.com/api/qt/stock/get?secid=90.BK0475&invt=2&fltt=2"
     "&fields=f43,f58,f170"),
]
for label, url in tests:
    try:
        d = fetcher._get(url)
        print(f"[OK] {label}: {str(d)[:220]}")
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {label}: {e}")
