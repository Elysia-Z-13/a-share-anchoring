#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""统计工具：Newey-West t 值、横截面回归斜率。"""
from __future__ import annotations

import numpy as np
import pandas as pd


def nw_t(x: pd.Series, lags: int = 6) -> tuple[float, float]:
    """月度序列的均值与其 Newey-West t 值（Bartlett 核，滞后 lags 期）。

    月度 IC 序列通常存在自相关，普通 t 值会高估显著性，因此本文所有
    时序结论均以 NW t 为准。
    """
    v = pd.Series(x).dropna().values
    n = len(v)
    if n < 3:
        return np.nan, np.nan
    mu = v.mean()
    d = v - mu
    var = np.dot(d, d) / n
    for L in range(1, min(lags, n - 1) + 1):
        gl = np.dot(d[L:], d[:-L]) / n
        var += 2 * (1 - L / (lags + 1)) * gl
    se = np.sqrt(max(var, 1e-12) / n)
    return float(mu), float(mu / se)


def monthly_slope(sig: pd.DataFrame, fwd: pd.DataFrame) -> pd.Series:
    """每月横截面回归：未来收益 ~ 标准化信号，返回斜率（每 1 个标准差对应的收益）。"""
    out = {}
    for ym in sig.index[:-1]:
        if ym not in fwd.index:
            continue
        a, b = sig.loc[ym], fwd.loc[ym]
        m = a.notna() & b.notna()
        if m.sum() < 300:
            continue
        x = a[m].values
        x = (x - x.mean()) / x.std()
        y = b[m].values
        out[ym] = float(np.dot(x, y - y.mean()) / (len(x) - 1))
    return pd.Series(out).sort_index()


def ols_trend(series: pd.Series) -> dict:
    """对时间趋势做 OLS：y = a + b·t，返回 b 与 t 值。"""
    y = series.dropna().values
    t = np.arange(len(y), dtype=float)
    X = np.column_stack([np.ones(len(t)), t])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    se = float(np.sqrt((resid @ resid) / (len(y) - 2) * np.linalg.inv(X.T @ X)[1, 1]))
    return {"slope": float(beta[1]), "t": float(beta[1] / se), "n": int(len(y))}


def ic_series(sig: pd.DataFrame, fwd: pd.DataFrame, h: int = 1, min_n: int = 300) -> pd.Series:
    """逐月计算信号与未来 h 期收益的横截面 Rank IC。"""
    out = {}
    for ym in sig.index[:-h]:
        if ym not in fwd.index:
            continue
        a, b = sig.loc[ym], fwd.loc[ym]
        m = a.notna() & b.notna()
        if m.sum() < min_n:
            continue
        out[ym] = a[m].rank().corr(b[m].rank())
    return pd.Series(out).sort_index()
