#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""04 散户参与度：锚定效应是不是一种散户现象。

三组证据，对应报告第 5.6 节、表 6–7、图 4–7、图 10：
  A. 横截面异质性   —— 效应集中在高换手、小市值股票
  B. 时期 × 换手    —— 2017–2020 的消失只发生在机构主导的低换手组
  C. 时序回归       —— 月度 IC 对市场换手率

用法：
    python scripts/04_retail_participation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.factor import add_signals, build_panel, monthly_turnover   # noqa: E402
from src.stats import ic_series, nw_t                               # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PERIODS = [("2013-2016", "2013-01", "2016-12"),
           ("2017-2020", "2017-01", "2020-12"),
           ("2021-2025", "2021-01", "2025-12")]


def group_ic(sig: pd.DataFrame, fwd: pd.DataFrame, me: pd.DataFrame,
             var: str, nq: int = 3) -> pd.DataFrame:
    """按上月末的某个特征分 nq 组，组内分别计算 IC。"""
    rows: dict[int, dict] = {}
    for ym in sig.index[:-1]:
        if ym not in fwd.index:
            continue
        a, b = sig.loc[ym], fwd.loc[ym]
        g = me[me["ym"] == ym].set_index("code")[var]
        m = a.notna() & b.notna() & g.reindex(a.index).notna()
        if m.sum() < 300:
            continue
        gg = pd.qcut(g.reindex(a.index)[m].rank(method="first"), nq, labels=False)
        for k in range(nq):
            sel = gg[gg == k].index
            if len(sel) < 100:
                continue
            rows.setdefault(k, {})[ym] = a[sel].rank().corr(b[sel].rank())
    return pd.DataFrame({k: pd.Series(v) for k, v in rows.items()})


def main() -> int:
    me, _ = build_panel(start="2013-01")
    tv = monthly_turnover()
    me = me.merge(tv[["code", "ym", "turn", "mvend"]], on=["code", "ym"], how="left") \
           .sort_values(["code", "ym"])
    me["turn_lag"] = me.groupby("code")["turn"].shift(1)
    me["mv_lag"] = me.groupby("code")["mvend"].shift(1)

    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    F1 = P.shift(-1) / P - 1
    sig = add_signals(me)["neu"]
    ic = ic_series(sig, F1)
    print(f"[sample] {len(ic)} months, mean IC {ic.mean():+.4f}\n")

    print("=" * 74)
    print("A. Cross-sectional heterogeneity (terciles, sorted on previous month-end value)")
    print("=" * 74)
    for var, labs in [("turn_lag", ("low turnover", "mid", "high turnover")),
                      ("mv_lag", ("small cap", "mid", "large cap"))]:
        t = group_ic(sig, F1, me, var)
        cells = []
        for k, lab in enumerate(labs):
            if k in t.columns:
                mu, tn = nw_t(t[k])
                cells.append(f"{lab}: {mu:+.4f} (NW t {tn:+.2f})")
        print("  " + "   ".join(cells))

    print("\n" + "=" * 74)
    print("B. Period x turnover tercile")
    print("=" * 74)
    t_turn = group_ic(sig, F1, me, "turn_lag")
    print(f"{'period':12s}{'low':>20s}{'mid':>20s}{'high':>20s}")
    for lab, a0, b0 in PERIODS:
        cells = []
        for k in range(3):
            s = t_turn[k]
            sub = s[(s.index >= pd.Period(a0, "M")) & (s.index <= pd.Period(b0, "M"))]
            mu, tn = nw_t(sub)
            cells.append(f"{mu:+.3f} ({tn:+.1f})")
        print(f"{lab:12s}" + "".join(f"{c:>20s}" for c in cells))

    print("\n" + "=" * 74)
    print("C. Time series: monthly IC on lagged market turnover")
    print("=" * 74)
    mkt_turn = me.groupby("ym")["turn"].median()
    print("  median monthly market turnover by period:")
    for lab, a0, b0 in PERIODS:
        sub = mkt_turn[(mkt_turn.index >= pd.Period(a0, "M")) & (mkt_turn.index <= pd.Period(b0, "M"))]
        print(f"    {lab}: {sub.median()*100:.1f}%")
    x = mkt_turn.shift(1).reindex(ic.index)
    ok = x.notna() & ic.notna()
    X = np.column_stack([np.ones(int(ok.sum())), x[ok].values])
    y = ic[ok].values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    se = np.sqrt((r @ r) / (ok.sum() - 2) * np.linalg.inv(X.T @ X)[1, 1])
    print(f"  IC_t = a + b*turnover :  b = {beta[1]:+.4f}, t = {beta[1]/se:+.2f}, "
          f"1SD impact = {beta[1]*x[ok].std():+.4f}")

    print("\n" + "=" * 74)
    print("High-turnover subsample, orthogonalised vs reversal + momentum")
    print("=" * 74)
    d = me.copy()
    d["q"] = d.groupby("ym")["turn_lag"].rank(pct=True)
    d = d[d["q"] > 2 / 3]
    print(f"{'period':14s}{'raw IC':>9s}{'orth IC':>10s}{'orth t':>9s}{'n':>6s}")
    for lab, a0, b0 in [("full", "2013-01", "2025-12")] + PERIODS:
        rec_raw, rec_orth = {}, {}
        for ym, sd in d.groupby("ym"):
            if ym not in F1.index or not (pd.Period(a0, "M") <= ym <= pd.Period(b0, "M")):
                continue
            sd = sd.dropna(subset=["gV120", "ret_1m", "ret_12_1"])
            f = F1.loc[ym].dropna()
            sd = sd[sd["code"].isin(f.index)]
            if len(sd) < 100:
                continue
            y = f.reindex(sd["code"]).values
            Xg = np.column_stack([np.ones(len(sd)), sd["ret_1m"].values, sd["ret_12_1"].values])
            b, *_ = np.linalg.lstsq(Xg, sd["gV120"].values, rcond=None)
            res = sd["gV120"].values - Xg @ b
            rec_raw[ym] = pd.Series(sd["gV120"].values).rank().corr(pd.Series(y).rank())
            rec_orth[ym] = pd.Series(res).rank().corr(pd.Series(y).rank())
        mr, _ = nw_t(pd.Series(rec_raw))
        mo, to = nw_t(pd.Series(rec_orth))
        print(f"{lab:14s}{mr:+9.4f}{mo:+10.4f}{to:+9.2f}{len(rec_orth):>6d}")
    print("\nnote: the sign flips across sub-periods, i.e. the residual is not a stable factor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
