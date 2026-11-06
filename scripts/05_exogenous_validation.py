#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""05 外生验证：用中国结算数据排除「换手率本身来自价格」的内生性质疑。

对应报告第 5.8 节、表 9–10、图 11。

数据（需自行下载，不入库）：
    QX_CSDC       中登主要指标统计表：过户笔数 / 过户总金额 -> 笔均成交金额
    QX_InvestorM  投资者情况统计表：新增自然人投资者等

用法：
    python scripts/05_exogenous_validation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.factor import add_signals, build_panel, monthly_turnover   # noqa: E402
from src.loader import load_csdc, load_investor                     # noqa: E402
from src.stats import ic_series, nw_t                               # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PERIODS = [("2013-2016", "2013-01", "2016-12"),
           ("2017-2020", "2017-01", "2020-12"),
           ("2021-2025", "2021-01", "2025-12")]


def reg(ic: pd.Series, x: pd.Series, label: str, lag: int = 1) -> None:
    xx = x.shift(lag).reindex(ic.index)
    ok = xx.notna() & ic.notna()
    if ok.sum() < 24:
        print(f"  {label:26s} insufficient sample")
        return
    X = np.column_stack([np.ones(int(ok.sum())), xx[ok].values])
    y = ic[ok].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    se = float(np.sqrt((r @ r) / (ok.sum() - 2) * np.linalg.inv(X.T @ X)[1, 1]))
    sd = float(np.std(xx[ok].values))
    print(f"  {label:26s} N={int(ok.sum()):3d}  b={beta[1]:+9.4f}  t={beta[1]/se:+6.2f}  "
          f"1SD={beta[1]*sd:+.4f}")


def main() -> int:
    me, _ = build_panel(start="2013-01")
    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    F1 = P.shift(-1) / P - 1
    ic = ic_series(add_signals(me)["neu"], F1)
    print(f"[sample] {len(ic)} months, mean IC {ic.mean():+.4f}")

    csdc = load_csdc()
    inv = load_investor()
    if csdc.empty and inv.empty:
        print("\n未找到中登数据；跳过外生验证。请下载 QX_CSDC / QX_InvestorM 后重试。")
        return 1
    if not csdc.empty:
        print(f"[csdc] {csdc.index.min()} ~ {csdc.index.max()} ({len(csdc)} months)")
    if not inv.empty:
        print(f"[investor] {inv.index.min()} ~ {inv.index.max()} ({len(inv)} months)")

    print("\n" + "=" * 76)
    print("Exogenous retail-participation proxies vs the anchor effect")
    print("=" * 76)
    if not inv.empty:
        reg(ic, inv["NewPersons"], "new retail investors (10k)")
    if not csdc.empty:
        reg(ic, csdc["per_trade"], "avg trade size (10k CNY)")
        reg(ic, csdc["TransferNumbers"], "transfer count")
    print("  --- price-derived proxies for comparison ---")
    reg(ic, monthly_turnover().groupby("ym")["turn"].median(), "market turnover")

    if not csdc.empty:
        print("\n" + "=" * 76)
        print("Per-period: average trade size vs effect strength")
        print("=" * 76)
        print(f"{'period':12s}{'n':>5s}{'IC':>10s}{'avg trade (10k)':>18s}{'turnover':>11s}")
        mt = monthly_turnover().groupby("ym")["turn"].median()
        for lab, a0, b0 in PERIODS:
            i0, i1 = pd.Period(a0, "M"), pd.Period(b0, "M")
            sub = ic[(ic.index >= i0) & (ic.index <= i1)]
            pt = csdc["per_trade"][(csdc.index >= i0) & (csdc.index <= i1)].median()
            tv = mt[(mt.index >= i0) & (mt.index <= i1)].median()
            print(f"{lab:12s}{len(sub):>5d}{sub.mean():+10.4f}"
                  f"{(f'{pt:.2f}' if pd.notna(pt) else '-'):>18s}{tv*100:>10.1f}%")

        q = csdc["per_trade"].shift(1)
        med = q.median()
        print("\nsplit on average trade size (smaller = more retail):")
        for lab, mask in [("low  (retail-heavy)", q <= med), ("high (institution-heavy)", q > med)]:
            sub = ic[ic.index.isin(q[mask].index)]
            mu, tn = nw_t(sub)
            print(f"  {lab:24s} N={len(sub):3d}  IC={mu:+.4f}  NW t={tn:+.2f}")

    print("\nnote: CSDC data ends 2023-08, so 2024-2025 is not covered.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
