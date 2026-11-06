#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""02 主结果：行业市值中性化、对反转动量正交化、组合回测与交易成本。

对应报告第 5.1–5.4 节与表 2–4。

用法：
    python scripts/02_main_results.py [--start 2013-01]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.factor import add_signals, backtest, build_panel          # noqa: E402
from src.stats import ic_series, nw_t                               # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2013-01", help="信号起始月（前面留给锚的预热期）")
    args = ap.parse_args()

    me, qc = build_panel(start=args.start)
    print(f"[sample] {me['ym'].nunique()} months, {me['ym'].min()} ~ {me['ym'].max()}, "
          f"avg cross-section {me.groupby('ym').size().mean():.0f}")
    print(f"[qc] extreme daily returns: {qc['异常日收益(|r|>25%)笔数']:,} / {qc['总日观测']:,}\n")

    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    F1 = P.shift(-1) / P - 1
    sigs = add_signals(me)

    print("=" * 78)
    print("Table 3  Raw / industry+size neutralised / orthogonalised vs reversal+momentum")
    print("=" * 78)
    print(f"{'version':30s}{'IC':>9s}{'IC t':>8s}{'NW t':>8s}{'months':>8s}")
    for name, lab in [("raw", "raw"), ("neu", "industry + size neutralised"),
                      ("neu_orth", "neutralised + orthogonalised")]:
        ic = ic_series(sigs[name], F1)
        mu, nwt = nw_t(ic)
        print(f"{lab:30s}{ic.mean():+9.4f}"
              f"{ic.mean()/ic.std()*np.sqrt(len(ic)):+8.2f}{nwt:+8.2f}{len(ic):>8d}")

    print("\n" + "=" * 78)
    print("Quintile mean next-month return (%)  Q1 = deepest below anchor, Q5 = largest gain")
    print("=" * 78)
    for name, lab in [("raw", "raw"), ("neu", "neutralised"), ("neu_orth", "neutralised+orth")]:
        rows = []
        for ym in sigs[name].index[:-1]:
            if ym not in F1.index:
                continue
            a, b = sigs[name].loc[ym], F1.loc[ym]
            m = a.notna() & b.notna()
            if m.sum() < 300:
                continue
            q = pd.qcut(a[m].rank(method="first"), 5, labels=False)
            rows.append(b[m].groupby(q).mean())
        qm = pd.DataFrame(rows).mean()
        print(f"{lab:30s}" + "  ".join(f"Q{i+1}:{qm.get(i, np.nan)*100:+.2f}" for i in range(5))
              + f"   Q5-Q1:{(qm.get(4, np.nan)-qm.get(0, np.nan))*100:+.2f}%")

    print("\n" + "=" * 78)
    print("Table 4  Long Q1 / short Q5, equal weight, with transaction costs")
    print("=" * 78)
    R = P.pct_change().shift(-1)
    print(f"{'version':22s}{'rebal':>7s}{'gross/m':>10s}{'Sharpe':>8s}"
          f"{'turnover':>9s}{'net30':>8s}{'net50':>8s}{'netSR50':>9s}")
    for name, lab in [("neu", "neutralised"), ("neu_orth", "neutralised+orth")]:
        for reb, rlab in [(1, "monthly"), (3, "quarterly")]:
            r30 = backtest(sigs[name], R, reb, 30)
            r50 = backtest(sigs[name], R, reb, 50)
            print(f"{lab:22s}{rlab:>7s}{r30['gross']*100:+9.2f}%{r30['sharpe']:+8.2f}"
                  f"{r30['turn']*100:8.0f}%{r30['net']*100:+7.2f}%{r50['net']*100:+7.2f}%"
                  f"{r50['net_sharpe']:+9.2f}")

    print("\nnote: backtest window is limited by the neutralised panel; "
          "see reports/report_zh.pdf for the exact sample.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
