#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
价格锚因子 v2：
  测试 1 —— 组合构建、换手率与交易成本（月频 vs 季频）
  测试 2 —— 行业 + 市值中性化后的残差是否还活着
  附加   —— 按市场情绪状态分组，检验锚定效应是否随情绪变化

用法：
    python tools/anchor_v2.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .loader import CACHE_PATH, load_info, load_prices
from .anchors import build_features

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SIG = "gV120"


# ---------------------------------------------------------------- 工具函数
def xs_resid(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """横截面回归取残差（X 已含常数项）。"""
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def build_panel(start="2021-01"):
    px = load_prices()
    me, qc = build_features(px)
    me = me[me["ym"] >= pd.Period(start, freq="M")].copy()

    # 行业：用上一年年报的行业代码，避免前视
    info = load_info()
    ind = info.dropna(subset=["EndDate"]).copy()
    ind["iyear"] = ind["EndDate"].dt.year
    ind = ind.sort_values(["Symbol", "iyear"]).groupby(["Symbol", "iyear"], as_index=False).tail(1)
    ind = ind[["Symbol", "iyear", "IndustryCode"]].rename(
        columns={"Symbol": "code", "IndustryCode": "ind"})

    me["iyear"] = me["date"].dt.year - 1          # 用上年行业
    me = me.merge(ind, on=["code", "iyear"], how="left")
    miss = me["ind"].isna().mean()
    print(f"[行业] 匹配率 {1-miss:.1%}（缺失的归入 'UNK'）")
    me["ind"] = me["ind"].fillna("UNK")

    # 市值
    me["logmv"] = np.log(me["float_mv"].clip(lower=1e6))
    # 前月收益与 12-1 动量（正交化用）
    me = me.sort_values(["code", "ym"])
    me["ret_1m"] = me.groupby("code")["close"].pct_change(1)
    me["ret_12_1"] = me.groupby("code")["close"].shift(1) / me.groupby("code")["close"].shift(11) - 1
    return me, qc


def add_signals(me: pd.DataFrame) -> pd.DataFrame:
    """生成三种版本：原始 / 行业市值中性化 / 中性化+对反转动量正交。"""
    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    outs = {k: {} for k in ("raw", "neu", "neu_orth")}
    for ym, s in me.groupby("ym"):
        s = s.dropna(subset=[SIG, "ret_1m", "ret_12_1", "logmv"])
        if len(s) < 300:
            continue
        outs["raw"][ym] = pd.Series(s[SIG].values, index=s["code"])
        # 行业哑变量 + log 市值
        d = pd.get_dummies(s["ind"], drop_first=True, dtype=float)
        X = np.column_stack([np.ones(len(s)), s["logmv"].values, d.values])
        r1 = xs_resid(s[SIG].values, X)
        outs["neu"][ym] = pd.Series(r1, index=s["code"])
        X2 = np.column_stack([X, s["ret_1m"].values, s["ret_12_1"].values])
        r2 = xs_resid(s[SIG].values, X2)
        outs["neu_orth"][ym] = pd.Series(r2, index=s["code"])
    return {k: pd.DataFrame(v).T for k, v in outs.items()}


def ic_stats(S: pd.DataFrame, F: pd.DataFrame, h=1) -> dict:
    idx, ic = [], []
    for ym in S.index[:-h]:
        if ym not in F.index:
            continue
        a, b = S.loc[ym], F.loc[ym]
        m = a.notna() & b.notna()
        if m.sum() < 200:
            continue
        idx.append(ym); ic.append(a[m].rank().corr(b[m].rank()))
    ic = pd.Series(ic, index=pd.PeriodIndex(idx, freq="M"))
    return dict(ic=ic, mean=ic.mean(), t=ic.mean() / ic.std() * np.sqrt(len(ic)), n=len(ic))


# ---------------------------------------------------------------- 组合回测
def backtest(S: pd.DataFrame, R: pd.DataFrame, rebal_every: int, cost_bp: float,
             nq: int = 5) -> dict:
    """做多低信号组、做空高信号组（IC 为负），等权，按 rebal_every 月调仓。"""
    dates = [d for d in S.index if d in R.index]
    gross, turn = [], []
    prev_long, prev_short = set(), set()
    for i, ym in enumerate(dates[:-1]):
        if i % rebal_every != 0:
            continue
        s = S.loc[ym].dropna()
        if len(s) < 300:
            continue
        q = pd.qcut(s.rank(method="first"), nq, labels=False)
        longs = set(q[q == 0].index)      # 低信号 = 深套
        shorts = set(q[q == nq - 1].index)  # 高信号 = 浮盈
        # 持有 rebal_every 个月
        hold = dates[i + 1: i + 1 + rebal_every]
        for h in hold:
            if h not in R.index:
                continue
            r = R.loc[h]
            rl = r.reindex(list(longs)).dropna()
            rs = r.reindex(list(shorts)).dropna()
            if len(rl) < 20 or len(rs) < 20:
                continue
            gross.append(rl.mean() - rs.mean())
        # 换手：与上次调仓的名单差异
        if prev_long:
            tl = 1 - len(longs & prev_long) / max(len(longs), 1)
            ts = 1 - len(shorts & prev_short) / max(len(shorts), 1)
            turn.append((tl + ts) / 2)
        prev_long, prev_short = longs, shorts

    g = pd.Series(gross)
    t = pd.Series(turn)
    avg_turn = t.mean() if len(t) else np.nan
    # 扣费：每次调仓按双边换手计
    per_rebal_cost = cost_bp / 1e4 * avg_turn * 2 if len(t) else 0
    net = g - per_rebal_cost / rebal_every
    return dict(gross=g.mean(), net=net.mean(), sharpe=g.mean() / g.std() * np.sqrt(12),
                net_sharpe=net.mean() / net.std() * np.sqrt(12), turn=avg_turn,
                n=len(g), total_gross=(1 + g).prod(), total_net=(1 + net).prod())


# ---------------------------------------------------------------- 主流程


def monthly_turnover(cache: str | None = None) -> pd.DataFrame:
    """月度换手率 = 当月成交额 / 月末流通市值。"""
    px = pd.read_pickle(cache or CACHE_PATH)
    px = px.copy()
    px["amt"] = px["volume"] * px["close_raw"]
    px["ym"] = px["date"].dt.to_period("M")
    g = px.groupby(["code", "ym"], as_index=False).agg(
        amt=("amt", "sum"), mvend=("float_mv", "last"), pxend=("close_raw", "last"))
    # Dsmvosd 单位为千元，成交额为元，故分母乘 1000
    g["turn"] = g["amt"] / (g["mvend"] * 1000)
    return g[["code", "ym", "turn", "amt", "mvend", "pxend"]]
