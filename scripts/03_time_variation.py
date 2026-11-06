#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""03 时变特征：锚定效应是「单调衰减」还是「消失又复现」。

对应报告第 5.5 节、表 5、图 1–3。

用法：
    python scripts/03_time_variation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.factor import add_signals, build_panel           # noqa: E402
from src.stats import ic_series, monthly_slope, nw_t, ols_trend   # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PERIODS = [("2013-2016", "2013-01", "2016-12"),
           ("2017-2020", "2017-01", "2020-12"),
           ("2021-2025", "2021-01", "2025-12")]


def main() -> int:
    me, _ = build_panel(start="2013-01")
    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    F1 = P.shift(-1) / P - 1
    sig = add_signals(me)["neu"]

    ic = ic_series(sig, F1)
    slope = monthly_slope(sig, F1)
    print(f"[sample] {len(ic)} months, mean IC {ic.mean():+.4f}\n")

    print("=" * 72)
    print("Yearly IC and cross-sectional slope")
    print("=" * 72)
    print(f"{'year':8s}{'n':>5s}{'mean IC':>11s}{'t':>8s}{'slope/1SD':>12s}{'t':>8s}")
    for y, g in ic.groupby(ic.index.year):
        s = slope.reindex(g.index)
        print(f"{y:<8d}{len(g):>5d}{g.mean():+11.4f}"
              f"{g.mean()/g.std()*len(g)**0.5:+8.2f}"
              f"{s.mean()*100:+11.2f}%{s.mean()/s.std()*len(s)**0.5:+8.2f}")

    print("\n" + "=" * 72)
    print("Sub-period comparison (the U-shape)")
    print("=" * 72)
    print(f"{'period':12s}{'n':>5s}{'IC':>10s}{'NW t':>8s}{'slope':>10s}{'NW t':>8s}")
    for lab, a, b in PERIODS:
        g = ic[(ic.index >= pd.Period(a, "M")) & (ic.index <= pd.Period(b, "M"))]
        s = slope.reindex(g.index)
        mi, ti = nw_t(g)
        ms, ts = nw_t(s)
        print(f"{lab:12s}{len(g):>5d}{mi:+10.4f}{ti:+8.2f}{ms*100:+9.2f}%{ts:+8.2f}")

    tr = ols_trend(ic)
    print(f"\ntrend test  IC_t = a + b*t :  b = {tr['slope']:+.6f}/month "
          f"({tr['slope']*12:+.4f}/year), t = {tr['t']:+.2f}")
    print("  b < 0 would mean the effect decays over time (investors learn);")
    print("  the estimate is insignificant, which rejects the learning story.")

    print("\n36-month rolling mean IC")
    roll = ic.rolling(36).mean().dropna()
    for ym in roll.index[::12]:
        print(f"  {ym} : {roll.loc[ym]:+.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
