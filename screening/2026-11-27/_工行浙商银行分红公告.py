# -*- coding: utf-8 -*-
"""工商银行(601398) / 浙商银行(601916) 近期公告扫描：是否已有新分红计划。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "code", "a_share_analyzer"))
import fetcher  # noqa: E402

TARGETS = [("601398", "工商银行"), ("601916", "浙商银行")]
KWS = ("分红", "派息", "利润分配", "股息", "权益分派")

for code, name in TARGETS:
    print(f"\n===== {name} {code} =====")
    try:
        anns = fetcher.announcements(code, "2026-08-01", "2027-12-31", 100) or []
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 抓取失败: {e}")
        continue
    print(f"2026-08-01 以来公告 {len(anns)} 条，最近 8 条标题：")
    for a in anns[:8]:
        print(f"  {a.get('notice_date', '')[:10]}  {a.get('title', '')[:60]}")
    hits = [a for a in anns if any(k in (a.get("title") or "") for k in KWS)]
    print(f"\n命中分红关键词 {len(hits)} 条：")
    for a in hits:
        print(f"  {a.get('notice_date', '')[:10]}  {a.get('title', '')}")
