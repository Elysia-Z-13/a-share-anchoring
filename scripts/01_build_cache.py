#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""01 建立行情缓存：读取 CSMAR 原始 CSV，清洗后缓存为 pickle。

只需跑一次；后续脚本会自动复用缓存。

用法：
    set ANCHOR_DATA_ROOT=data/raw      (Windows)  /  export ... (Linux/macOS)
    python scripts/01_build_cache.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.loader import CACHE_PATH, DATA_ROOT, load_info, load_prices, load_status  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    print(f"data root : {DATA_ROOT}")
    print(f"cache path: {CACHE_PATH}\n")

    px = load_prices()
    print(f"\n{px['code'].nunique():,} stocks  {px['date'].min().date()} ~ {px['date'].max().date()}")
    print(f"rows: {len(px):,}")

    st = load_status()
    if not st.empty:
        sub = st[st["ChangedItem"] == "上市状态"]
        print(f"\nstatus changes: {len(st):,} (listing-status {len(sub):,})")
        print("  ValueAfter:", dict(sub["ValueAfter"].value_counts().head(6)))

    info = load_info()
    if not info.empty:
        print(f"company info: {len(info):,} rows, {info['Symbol'].nunique():,} stocks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
