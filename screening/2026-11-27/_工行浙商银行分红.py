# -*- coding: utf-8 -*-
"""工商银行(601398) / 浙商银行(601916) 分红历史与最近分红日。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

TARGETS = [("601398", "工商银行"), ("601916", "浙商银行")]
KEEP = ("NOTICE_DATE", "IMPL_PLAN_PROFILE", "ASSIGN_PROGRESS",
        "EQUITY_RECORD_DATE", "EX_DIVIDEND_DATE", "PAY_CASH_DATE", "REPORT_DATE")

for code, name in TARGETS:
    print(f"\n===== {name} {code} =====")
    try:
        bon = fetcher.bonus(code) or {}
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 抓取失败: {e}")
        continue
    rows = bon.get("fhyx") or []
    print(f"分红方案记录 {len(rows)} 条，字段: {list(rows[0].keys()) if rows else '-'}")
    for r in rows[:12]:
        print("-" * 60)
        for k in KEEP:
            if k in r and r[k] not in (None, "", "-"):
                print(f"  {k}: {str(r[k])[:10] if 'DATE' in k else r[k]}")
