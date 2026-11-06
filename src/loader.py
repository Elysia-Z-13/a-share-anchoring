#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CSMAR 数据加载与清洗。

数据来源（需自行向 CSMAR 申请，不入库）：
    TRDNEW_Dalyr      个股日行情：Stkcd / Trddt / Trdsta / Clsprc / Dnshrtrd /
                      Dsmvosd（流通市值，单位千元）/ Adjprcwd（后复权收盘价）
    STK_ITEMCHANGE    上市状态变更：Symbol / ChangeDate / ChangedItem / ValueAfter
    STK_LISTEDCOINFOANL 上市公司基本信息年度表：Symbol / EndDate / IndustryCode

清洗规则
--------
1. Trdsta == 1（正常交易）
2. Dnshrtrd > 0（剔除节假日、停牌等零成交行）
3. Adjprcwd > 0 且非缺失

输出列：code / date / close（后复权）/ close_raw / volume / float_mv
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 数据根目录：可用环境变量覆盖，默认 data/raw
DATA_ROOT = os.environ.get("ANCHOR_DATA_ROOT", "data/raw")
CACHE_PATH = os.environ.get("ANCHOR_CACHE", "data/cache/prices.pkl")

COLS = ["Stkcd", "Trddt", "Trdsta", "Clsprc", "Dnshrtrd", "Dsmvosd", "Adjprcwd"]


def _find(pattern: str, root: str | None = None) -> list[str]:
    """在数据根目录下递归查找文件，不依赖子文件夹命名。"""
    base = root or DATA_ROOT
    files = sorted(glob.glob(f"{base}/**/{pattern}", recursive=True))
    return files


def load_prices(root: str | None = None, cache: str | None = None,
                max_date: str | None = None) -> pd.DataFrame:
    """加载并清洗日行情，结果缓存为 pickle 供反复实验使用。"""
    cache_path = Path(cache or CACHE_PATH)
    if cache_path.exists():
        print(f"[cache] {cache_path}")
        return pd.read_pickle(cache_path)

    files = _find("TRDNEW_Dalyr*.csv", root)
    if not files:
        raise SystemExit(
            f"未找到日行情文件。请把 CSMAR 的 TRDNEW_Dalyr*.csv 放到 "
            f"{root or DATA_ROOT}/ 下（支持任意子目录），或用 ANCHOR_DATA_ROOT 指定路径。"
        )
    print(f"[load] {len(files)} 个日行情文件")

    # 逐文件读入并立即过滤，避免 concat 时内存峰值过高
    parts, n_raw = [], 0
    for f in files:
        d = pd.read_csv(f, usecols=COLS, dtype={"Stkcd": str}, encoding="utf-8-sig")
        n_raw += len(d)
        d = d[(d["Trdsta"] == 1) & (d["Dnshrtrd"] > 0)
              & d["Adjprcwd"].notna() & (d["Adjprcwd"] > 0)]
        d["Stkcd"] = d["Stkcd"].str.zfill(6).astype("int32")
        parts.append(d[["Stkcd", "Trddt", "Clsprc", "Dnshrtrd", "Dsmvosd", "Adjprcwd"]])
    px = pd.concat(parts, ignore_index=True)
    del parts
    print(f"  {n_raw:,} 行 → 清洗后 {len(px):,} 行（剔除 {n_raw - len(px):,}）")

    px = px.rename(columns={"Stkcd": "code", "Trddt": "date", "Clsprc": "close_raw",
                            "Dnshrtrd": "volume", "Dsmvosd": "float_mv", "Adjprcwd": "close"})
    px["date"] = pd.to_datetime(px["date"], errors="coerce")

    if max_date:
        px = px[px["date"] <= pd.Timestamp(max_date)]
        print(f"  truncated at {max_date}: {len(px):,} rows")

    out = (px[["code", "date", "close", "close_raw", "volume", "float_mv"]]
           .sort_values(["code", "date"]).reset_index(drop=True))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_pickle(cache_path)
    print(f"[cache] wrote {cache_path}")
    return out


def load_status(root: str | None = None) -> pd.DataFrame:
    """上市状态变更表，用于构造 ST 区间与退市日。合并多个年份分卷。"""
    files = _find("STK_ITEMCHANGE*.csv", root)
    if not files:
        print("[warn] 未找到上市状态变更表，ST 过滤将被跳过")
        return pd.DataFrame()
    parts = []
    for f in files:
        d = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        d.columns = [c.strip() for c in d.columns]
        parts.append(d)
    d = pd.concat(parts, ignore_index=True).drop_duplicates()
    d["Symbol"] = pd.to_numeric(d["Symbol"].astype(str).str.zfill(6), errors="coerce").astype("int32")
    for c in ("DeclareDate", "ChangeDate"):
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce")
    return d


def load_info(root: str | None = None) -> pd.DataFrame:
    """上市公司基本信息年度表，用于行业中性化与次新股过滤。"""
    files = _find("STK_LISTEDCOINFOANL*.csv", root)
    if not files:
        print("[warn] 未找到上市公司基本信息表，行业中性化将退化为仅市值中性化")
        return pd.DataFrame()
    d = pd.concat([pd.read_csv(f, dtype={"Symbol": str}, encoding="utf-8-sig")
                   for f in files], ignore_index=True).drop_duplicates()
    d.columns = [c.strip() for c in d.columns]
    d["Symbol"] = pd.to_numeric(d["Symbol"].astype(str).str.zfill(6), errors="coerce").astype("int32")
    if "EndDate" in d.columns:
        d["EndDate"] = pd.to_datetime(d["EndDate"], errors="coerce")
    if "LISTINGDATE" in d.columns:
        d["LISTINGDATE"] = pd.to_datetime(d["LISTINGDATE"], errors="coerce")
    return d


def load_csdc(root: str | None = None) -> pd.DataFrame:
    """中国结算主要指标（外生散户参与度代理）。

    QX_CSDC：SgnMonth / 过户笔数 TransferNumbers（万笔）/ 过户总金额 TransferAmounts（亿元）
             → 笔均成交金额 = TransferAmounts / TransferNumbers，单位万元/笔
    """
    files = _find("QX_CSDC*.csv", root)
    if not files:
        return pd.DataFrame()
    d = pd.read_csv(files[0], encoding="utf-8-sig")
    d.columns = [c.strip() for c in d.columns]
    d["ym"] = pd.PeriodIndex(pd.to_datetime(d["SgnMonth"], format="%Y-%m"), freq="M")
    d["per_trade"] = d["TransferAmounts"] / d["TransferNumbers"]
    return d.set_index("ym")


def load_investor(root: str | None = None) -> pd.DataFrame:
    """中国结算投资者情况表（自然人口径）。"""
    files = _find("QX_InvestorM*.csv", root)
    if not files:
        return pd.DataFrame()
    d = pd.read_csv(files[0], encoding="utf-8-sig")
    d.columns = [c.strip() for c in d.columns]
    d["ym"] = pd.PeriodIndex(pd.to_datetime(d["SgnMonth"], format="%Y-%m"), freq="M")
    return d.set_index("ym")


if __name__ == "__main__":
    px = load_prices()
    print(f"\n{px['code'].nunique():,} 只股票  {px['date'].min().date()} ~ {px['date'].max().date()}")
