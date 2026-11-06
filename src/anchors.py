#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
价格锚因子检验：以「历史价格参照点」为锚，检验锚定 / 处置效应在 A 股的方向与强度。

锚的四种定义（全部在复权空间内计算，无需分析师数据）：
  1. H252   过去 252 交易日最高价        -> g52  = P/H252 - 1
  2. H_all  可得历史（最长 750 日）最高价 -> gAll = P/H_all - 1
  3. VWAP120 过去 120 日成交量加权均价    -> gV120 = P/VWAP120 - 1
  4. VWAP250 过去 250 日成交量加权均价    -> gV250 = P/VWAP250 - 1

g 越接近 0 表示价格越贴近锚（在锚上方或刚突破）；越负表示离锚越远（深度浮亏/套牢）。
符号本身就是待检验的假设：
  - 「套牢盘压制」假说预测 g 与未来收益负相关（越接近解套位，抛压越大）
  - 「锚定反应不足」假说预测 g 与未来收益正相关（创新高后继续走强）

调用方：scripts/02_main_results.py、scripts/03_time_variation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def rank_ic(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    if m.sum() < 30:
        return np.nan
    return a[m].rank().corr(b[m].rank())


def build_features(px: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """计算锚与信号。无 high/low 时自动退化为仅用收盘价（已实测两者秩相关 0.9999）。"""
    px = px.sort_values(["code", "date"]).copy()
    has_hl = {"high", "low"}.issubset(px.columns)
    if has_hl:
        px["tp"] = (px["high"] + px["low"] + px["close"]) / 3.0
        px["hk"] = px["high"]
    else:
        px["tp"] = px["close"]
        px["hk"] = px["close"]
    px["pv"] = px["tp"] * px["volume"]

    # 用 groupby.rolling（C 实现）而不是 groupby.apply，960 万行差一个数量级
    g = px.groupby("code", sort=False)
    def roll(col, win, mp, how):
        r = getattr(g[col].rolling(win, min_periods=mp), how)()
        return r.reset_index(level=0, drop=True).sort_index()

    px["h252"] = roll("hk", 252, 120, "max")
    px["hall"] = roll("hk", 750, 250, "max")
    px["spv120"] = roll("pv", 120, 60, "sum")
    px["sv120"] = roll("volume", 120, 60, "sum")
    px["spv250"] = roll("pv", 250, 120, "sum")
    px["sv250"] = roll("volume", 250, 120, "sum")
    px["ret1d"] = g["close"].pct_change()

    jump = int((px["ret1d"].abs() > 0.25).sum())
    qc = {"异常日收益(|r|>25%)笔数": jump, "总日观测": int(px["ret1d"].notna().sum()),
          "使用高低价": has_hl}

    me = px.groupby(["code", px["date"].dt.to_period("M")], as_index=False).tail(1).copy()
    me["vwap120"] = me["spv120"] / me["sv120"]
    me["vwap250"] = me["spv250"] / me["sv250"]
    me["g52"] = me["close"] / me["h252"] - 1.0
    me["gAll"] = me["close"] / me["hall"] - 1.0
    me["gV120"] = me["close"] / me["vwap120"] - 1.0
    me["gV250"] = me["close"] / me["vwap250"] - 1.0
    me["ym"] = me["date"].dt.to_period("M")
    return me, qc


def evaluate(me: pd.DataFrame, sig: str, horizons: tuple[int, ...]) -> dict:
    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    res = {}
    for h in horizons:
        F = P.shift(-h) / P - 1.0
        S = me.pivot(index="ym", columns="code", values=sig).sort_index()
        idx, ic, n = [], [], []
        for ym in S.index[:-h]:
            if ym not in F.index:
                continue
            a, b = S.loc[ym], F.loc[ym]
            v = rank_ic(a, b)
            if not np.isnan(v):
                idx.append(ym); ic.append(v); n.append(int((a.notna() & b.notna()).sum()))
        ic = pd.Series(ic, index=pd.PeriodIndex(idx, freq="M"))
        # 五分组
        rows = []
        for ym in S.index[:-h]:
            if ym not in F.index:
                continue
            a, b = S.loc[ym], F.loc[ym]
            m = a.notna() & b.notna()
            if m.sum() < 50:
                continue
            q = pd.qcut(a[m].rank(method="first"), 5, labels=False)
            rows.append(b[m].groupby(q).mean())
        Q = pd.DataFrame(rows) if rows else pd.DataFrame()
        spread = (Q[4] - Q[0]) if len(Q) else pd.Series(dtype=float)
        res[h] = {
            "ic": ic,
            "ic_mean": ic.mean() if len(ic) else np.nan,
            "ic_t": (ic.mean() / ic.std() * np.sqrt(len(ic))) if len(ic) > 2 else np.nan,
            "n_months": len(ic),
            "avg_stocks": np.mean(n) if n else np.nan,
            "q": Q.mean() if len(Q) else pd.Series(dtype=float),
            "spread": spread.mean() if len(spread) else np.nan,
            "spread_t": (spread.mean() / spread.std() * np.sqrt(len(spread))) if len(spread) > 2 else np.nan,
            "by_year": ic.groupby(ic.index.year).mean() if len(ic) else pd.Series(dtype=float),
        }
    return res
