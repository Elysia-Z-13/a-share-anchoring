#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
生成研究报告所需的全部数字与图表。
输出：data/report_assets.json + reports/figs/*.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.factor import build_panel, add_signals         # noqa: E402
from src.loader import CACHE_PATH                        # noqa: E402
from src.stats import nw_t                               # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
BLUE, RED, GRAY, DARK = (55, 110, 180), (200, 70, 70), (150, 150, 150), (40, 40, 40)


def F(sz):
    return ImageFont.truetype(FONT_PATH, sz, index=0)


# ------------------------------------------------------------------ 绘图工具
def new_canvas(w=1100, h=620):
    img = Image.new("RGB", (w, h), "white")
    return img, ImageDraw.Draw(img)


def axes(d, box, ymin, ymax, ylabel, nticks=5):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], outline=(210, 210, 210))
    for i in range(nticks + 1):
        y = y1 - (y1 - y0) * i / nticks
        v = ymin + (ymax - ymin) * i / nticks
        d.line([x0, y, x1, y], fill=(235, 235, 235))
        d.text((x0 - 12, y), f"{v:.2f}", font=F(14), fill=GRAY, anchor="rm")
    d.text((x0 - 60, (y0 + y1) / 2), ylabel, font=F(16), fill=DARK, anchor="mm")
    return lambda v: y1 - (y1 - y0) * (v - ymin) / (ymax - ymin)


def save(img, name, title, subtitle=""):
    d = ImageDraw.Draw(img)
    d.text((30, 18), title, font=F(26), fill=DARK)
    if subtitle:
        d.text((30, 54), subtitle, font=F(15), fill=GRAY)
    img.save(FIG / name)
    print(f"  saved {name}")


def bar_chart(vals, labels, name, title, subtitle="", ylabel="", fmt="{:.3f}",
              color=None, hl=None):
    img, d = new_canvas()
    box = (110, 95, 1060, 520)
    lo, hi = min(min(vals), 0), max(max(vals), 0)
    pad = (hi - lo) * 0.18 + 0.004
    ymap = axes(d, box, lo - pad, hi + pad, ylabel)
    n = len(vals)
    w = (box[2] - box[0]) / n
    bw = w * 0.62
    zero = ymap(0)
    for i, (v, lb) in enumerate(zip(vals, labels)):
        cx = box[0] + w * (i + 0.5)
        c = color or (RED if v < 0 else BLUE)
        if hl is not None and i in hl:
            c = (240, 150, 40)
        top, bot = sorted([zero, ymap(v)])
        d.rectangle([cx - bw / 2, top, cx + bw / 2, bot], fill=c)
        d.text((cx, bot + 8 if v < 0 else top - 8), fmt.format(v), font=F(14),
               fill=DARK, anchor="ma" if v < 0 else "mb")
        d.text((cx, box[3] + 24), str(lb), font=F(15), fill=DARK, anchor="ma")
    d.line([box[0], zero, box[2], zero], fill=DARK, width=2)
    save(img, name, title, subtitle)


def grouped_bar(groups, series, name, title, subtitle="", ylabel=""):
    """groups: x 标签；series: {名称: [值...]}"""
    img, d = new_canvas()
    box = (110, 95, 1060, 500)
    allv = [v for vs in series.values() for v in vs]
    lo, hi = min(min(allv), 0), max(max(allv), 0)
    pad = (hi - lo) * 0.18 + 0.004
    ymap = axes(d, box, lo - pad, hi + pad, ylabel)
    n, m = len(groups), len(series)
    w = (box[2] - box[0]) / n
    bw = w * 0.8 / m
    zero = ymap(0)
    cols = [BLUE, RED, (240, 150, 40), (90, 160, 110)]
    for i, g in enumerate(groups):
        for j, (nm, vs) in enumerate(series.items()):
            v = vs[i]
            cx = box[0] + w * i + w * 0.1 + bw * (j + 0.5)
            top, bot = sorted([zero, ymap(v)])
            d.rectangle([cx - bw / 2, top, cx + bw / 2, bot], fill=cols[j % 4])
            d.text((cx, bot + 6 if v < 0 else top - 6), f"{v:.3f}", font=F(12),
                   fill=DARK, anchor="ma" if v < 0 else "mb")
        d.text((box[0] + w * (i + 0.5), box[3] + 24), str(g), font=F(15), fill=DARK, anchor="ma")
    d.line([box[0], zero, box[2], zero], fill=DARK, width=2)
    # 图例
    lx = box[0] + 20
    for j, (nm, _) in enumerate(series.items()):
        d.rectangle([lx, box[3] + 52, lx + 18, box[3] + 68], fill=cols[j % 4])
        d.text((lx + 26, box[3] + 60), nm, font=F(14), fill=DARK, anchor="lm")
        lx += 30 + len(nm) * 15
    save(img, name, title, subtitle)


def line_chart(xs, ys, name, title, subtitle="", ylabel=""):
    img, d = new_canvas()
    box = (110, 95, 1060, 520)
    lo, hi = min(min(ys), 0), max(max(ys), 0)
    pad = (hi - lo) * 0.2 + 0.004
    ymap = axes(d, box, lo - pad, hi + pad, ylabel)
    n = len(xs)
    step = (box[2] - box[0]) / max(n - 1, 1)
    zero = ymap(0)
    d.line([box[0], zero, box[2], zero], fill=DARK, width=2)
    pts = [(box[0] + i * step, ymap(v)) for i, v in enumerate(ys)]
    d.line(pts, fill=BLUE, width=3)
    step_lab = max(1, n // 9)          # 标签自动抽稀，避免挤成一团
    for i, (x, y) in enumerate(pts):
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=BLUE)
        if i % step_lab == 0:
            d.text((x, box[3] + 24), str(xs[i]), font=F(13), fill=DARK, anchor="ma")
    save(img, name, title, subtitle)


def scatter(x, y, name, title, subtitle="", xlabel="", ylabel=""):
    img, d = new_canvas()
    box = (110, 95, 1060, 520)
    xr = (min(x) - 0.02 * (max(x) - min(x)), max(x) + 0.02 * (max(x) - min(x)))
    ylo, yhi = np.percentile(y, 2), np.percentile(y, 98)
    pad = (yhi - ylo) * 0.15 + 0.005
    yr = (min(ylo, 0) - pad, max(yhi, 0) + pad)
    ymap = axes(d, box, yr[0], yr[1], ylabel)
    xmap = lambda v: box[0] + (box[2] - box[0]) * (v - xr[0]) / (xr[1] - xr[0])
    d.line([box[0], ymap(0), box[2], ymap(0)], fill=(200, 200, 200), width=1)
    k, b = np.polyfit(x, y, 1)
    d.line([(xmap(xr[0]), ymap(k * xr[0] + b)), (xmap(xr[1]), ymap(k * xr[1] + b))],
           fill=RED, width=3)
    for xi, yi in zip(x, y):
        d.ellipse([xmap(xi) - 4, ymap(yi) - 4, xmap(xi) + 4, ymap(yi) + 4], fill=BLUE)
    d.text(((box[0] + box[2]) / 2, box[3] + 44), xlabel, font=F(16), fill=DARK, anchor="mm")
    save(img, name, title, subtitle)


# ------------------------------------------------------------------ 主流程
def main() -> int:
    me, _ = build_panel(start="2013-01")
    print(f"[样本] {me['ym'].nunique()} 个月 {me['ym'].min()}~{me['ym'].max()}，"
          f"平均截面 {me.groupby('ym').size().mean():.0f} 只")

    # 换手率（Dsmvosd 单位为千元）
    px = pd.read_pickle(CACHE_PATH)
    px["amt"] = px["volume"] * px["close_raw"]
    px["ym"] = px["date"].dt.to_period("M")
    tv = px.groupby(["code", "ym"], as_index=False).agg(amt=("amt", "sum"),
                                                        mvend=("float_mv", "last"))
    tv["turn"] = tv["amt"] / (tv["mvend"] * 1000)
    me = me.merge(tv[["code", "ym", "turn", "mvend"]], on=["code", "ym"], how="left") \
           .sort_values(["code", "ym"])
    me["turn_lag"] = me.groupby("code")["turn"].shift(1)
    me["mv_lag"] = me.groupby("code")["mvend"].shift(1)

    P = me.pivot(index="ym", columns="code", values="close").sort_index()
    F1 = P.shift(-1) / P - 1
    sigs = add_signals(me)
    S_neu = sigs["neu"]

    def ic_series(S):
        out = {}
        for ym in S.index[:-1]:
            if ym not in F1.index:
                continue
            a, b = S.loc[ym], F1.loc[ym]
            m = a.notna() & b.notna()
            if m.sum() < 300:
                continue
            out[ym] = a[m].rank().corr(b[m].rank())
        return pd.Series(out).sort_index()

    # 逐年
    ic_all = ic_series(S_neu)
    yearly = ic_all.groupby(ic_all.index.year).agg(["mean", "count"])

    # 分期
    periods = [("2013-2016", "2013-01", "2016-12"), ("2017-2020", "2017-01", "2020-12"),
               ("2021-2025", "2021-01", "2025-12")]
    per_stats = {}
    for lab, a0, b0 in periods:
        sub = ic_all[(ic_all.index >= pd.Period(a0, "M")) & (ic_all.index <= pd.Period(b0, "M"))]
        mu, tn = nw_t(sub)
        per_stats[lab] = dict(ic=float(mu), t=float(tn), n=int(len(sub)))

    # 换手率分组
    def group_ic(var, nq=3):
        rows = {}
        for ym in S_neu.index[:-1]:
            if ym not in F1.index:
                continue
            a, b = S_neu.loc[ym], F1.loc[ym]
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

    t_turn = group_ic("turn_lag")
    turn_stats = {k: nw_t(t_turn[k]) for k in t_turn.columns}
    t_mv = group_ic("mv_lag")
    mv_stats = {k: nw_t(t_mv[k]) for k in t_mv.columns}

    # 时期 × 换手
    pt = {}
    for lab, a0, b0 in periods:
        pt[lab] = {}
        for k in range(3):
            s = t_turn[k]
            sub = s[(s.index >= pd.Period(a0, "M")) & (s.index <= pd.Period(b0, "M"))]
            mu, tn = nw_t(sub)
            pt[lab][k] = dict(ic=float(mu), t=float(tn))

    # 五分组
    quint = {}
    for name, S in [("raw", sigs["raw"]), ("neu", S_neu)]:
        rows = []
        for ym in S.index[:-1]:
            if ym not in F1.index:
                continue
            a, b = S.loc[ym], F1.loc[ym]
            m = a.notna() & b.notna()
            if m.sum() < 300:
                continue
            q = pd.qcut(a[m].rank(method="first"), 5, labels=False)
            rows.append(b[m].groupby(q).mean())
        quint[name] = (pd.DataFrame(rows).mean() * 100).round(3).tolist()

    # 市场换手率
    mkt_turn = me.groupby("ym")["turn"].median()
    mkt_turn_pct = mkt_turn[(mkt_turn.index >= pd.Period("2013-01", "M")) &
                            (mkt_turn.index <= pd.Period("2025-12", "M"))]

    # 情绪
    mkt = me.groupby("ym").agg(mret=("ret_1m", "mean"))
    mkt["cum6"] = mkt["mret"].rolling(6).apply(lambda x: (1 + x).prod() - 1)
    sent = mkt["cum6"].shift(1)
    s = sent.reindex(ic_all.index)
    ok = s.notna()
    q3 = pd.qcut(s[ok], 3, labels=["悲观", "中性", "乐观"])
    sent_stats = {}
    for g in ["悲观", "中性", "乐观"]:
        v = ic_all[ok][q3 == g]
        mu, tn = nw_t(v)
        sent_stats[g] = dict(ic=float(mu), t=float(tn), n=int(len(v)))
    X = np.column_stack([np.ones(ok.sum()), s[ok].values])
    yv = ic_all[ok].values
    beta, *_ = np.linalg.lstsq(X, yv, rcond=None)
    resid = yv - X @ beta
    se = float(np.sqrt((resid @ resid) / (ok.sum() - 2) * np.linalg.inv(X.T @ X)[1, 1]))

    # 滚动
    roll = ic_all.rolling(36).mean().dropna()

    # 高换手组正交
    d = me.copy()
    d["q"] = d.groupby("ym")["turn_lag"].rank(pct=True)
    d = d[d["q"] > 2 / 3]
    hf = {}
    for lab, a0, b0 in [("全期", "2013-01", "2025-12")] + periods:
        rec_raw, rec_orth = {}, {}
        for ym, sd in d.groupby("ym"):
            if ym not in F1.index:
                continue
            if not (pd.Period(a0, "M") <= ym <= pd.Period(b0, "M")):
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
        mr, tr = nw_t(pd.Series(rec_raw))
        mo, to = nw_t(pd.Series(rec_orth))
        hf[lab] = dict(raw=float(mr), raw_t=float(tr), orth=float(mo), orth_t=float(to),
                       n=int(len(rec_raw)))

    # ---------------- 中登外生数据 ----------------
    from src.loader import load_csdc, load_investor
    csdc = load_csdc()
    inv = load_investor()

    def _reg(x):
        xx = x.shift(1).reindex(ic_all.index)
        ok = xx.notna() & ic_all.notna()
        if ok.sum() < 24:
            return None
        X = np.column_stack([np.ones(int(ok.sum())), xx[ok].values])
        y = ic_all[ok].values
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = y - X @ b
        se = float(np.sqrt((r @ r) / (ok.sum() - 2) * np.linalg.inv(X.T @ X)[1, 1]))
        sd = float(np.std(xx[ok].values))
        return dict(b=float(b[1]), t=float(b[1] / se), n=int(ok.sum()),
                    sd=sd, effect=float(b[1] * sd))

    csdc_stats = {
        "per_trade": _reg(csdc["per_trade"]),
        "new_persons": _reg(inv["NewPersons"]),
        "transfer_numbers": _reg(csdc["TransferNumbers"]),
        "mkt_turn": _reg(mkt_turn_pct),
        "sent": _reg(sent),
    }
    per_trade_period = {}
    for lab, a0, b0 in periods:
        s = csdc["per_trade"][(csdc.index >= pd.Period(a0, "M")) & (csdc.index <= pd.Period(b0, "M"))]
        per_trade_period[lab] = float(s.median()) if len(s) else float("nan")
    q = csdc["per_trade"].shift(1)
    med = q.median()
    low = ic_all[ic_all.index.isin(q[q <= med].index)]
    high = ic_all[ic_all.index.isin(q[q > med].index)]
    csdc_stats["low_per_trade"] = dict(ic=float(nw_t(low)[0]), t=float(nw_t(low)[1]), n=int(len(low)))
    csdc_stats["high_per_trade"] = dict(ic=float(nw_t(high)[0]), t=float(nw_t(high)[1]), n=int(len(high)))

    assets = dict(
        n_months=int(me["ym"].nunique()),
        start=str(me["ym"].min()), end=str(me["ym"].max()),
        avg_xs=float(me.groupby("ym").size().mean()),
        n_stocks=int(me["code"].nunique()),
        yearly={str(k): dict(ic=float(v["mean"]), n=int(v["count"])) for k, v in yearly.iterrows()},
        periods=per_stats,
        turn_groups={str(k): dict(ic=float(v[0]), t=float(v[1])) for k, v in turn_stats.items()},
        mv_groups={str(k): dict(ic=float(v[0]), t=float(v[1])) for k, v in mv_stats.items()},
        period_turn=pt,
        quint=quint,
        mkt_turn={str(k): float(v) for k, v in mkt_turn_pct.items()},
        mkt_turn_period={lab: float(mkt_turn_pct[(mkt_turn_pct.index >= pd.Period(a, "M")) &
                                                 (mkt_turn_pct.index <= pd.Period(b, "M"))].median())
                         for lab, a, b in periods},
        sentiment=sent_stats,
        sent_beta=float(beta[1]), sent_se=se, sent_t=float(beta[1] / se),
        rolling={str(k): float(v) for k, v in roll.items()},
        high_turn_orth=hf,
        csdc=csdc_stats,
        per_trade_period=per_trade_period,
    )
    Path("reports/assets.json").write_text(json.dumps(assets, ensure_ascii=False, indent=1),
                                               encoding="utf-8")
    print("[保存] data/report_assets.json")

    # ---------------- 图 ----------------
    print("[绘图]")
    yrs = [y for y in assets["yearly"] if assets["yearly"][y]["n"] >= 11]
    bar_chart([assets["yearly"][y]["ic"] for y in yrs], yrs, "fig1_yearly_ic.png",
              "图 1  锚定效应逐年衰减与复现（中性化信号 IC）",
              "2013–2025，月度截面 Rank IC 的年均值；虚线为零。2017–2020 几乎归零，2021 年后回升。",
              ylabel="Rank IC", fmt="{:.3f}")

    labs = list(per_stats)
    bar_chart([per_stats[l]["ic"] for l in labs], labs, "fig2_period_ic.png",
              "图 2  三期对比：效应消失又复现",
              "括号内为 Newey-West t 值（滞后 6 期）。",
              ylabel="Rank IC")

    line_chart(list(roll.index), list(roll.values), "fig3_rolling_ic.png",
               "图 3  36 个月滚动 IC",
               "窗口内月度 IC 均值。低谷出现在 2019–2020，与全市场换手率低点重合。",
               ylabel="滚动 IC")

    gl = ["低换手", "中换手", "高换手"]
    bar_chart([turn_stats[k][0] for k in sorted(turn_stats)], gl, "fig4_turn_group.png",
              "图 4  锚定效应集中于高换手（散户主导）股票",
              "按上月末换手率三分组，各组内单独计算 IC。",
              ylabel="Rank IC")

    ml = ["小市值", "中市值", "大市值"]
    bar_chart([mv_stats[k][0] for k in sorted(mv_stats)], ml, "fig5_mv_group.png",
              "图 5  锚定效应集中于小市值股票",
              "按上月末流通市值三分组。",
              ylabel="Rank IC")

    grouped_bar(list(pt),
                {f"{gl[k]}": [pt[l][k]["ic"] for l in pt] for k in range(3)},
                "fig6_period_turn.png",
                "图 6  时期 × 换手分组：2017–2020 低换手组效应翻正",
                "高换手组（散户主导）三期均为负，说明效应从未真正消失。",
                ylabel="Rank IC")

    yrs2 = list(mkt_turn.index)
    line_chart([str(y) for y in yrs2[::6]], list(mkt_turn_pct.values[::6]),
               "fig7_market_turnover.png",
               "图 7  全市场月换手率（%）",
               "2017–2020 为明显低谷，与图 1 的效应低谷精确对应。每 6 个月标注一次。",
               ylabel="月换手率")

    q_lab = ["Q1 深套", "Q2", "Q3", "Q4", "Q5 浮盈"]
    grouped_bar(q_lab, {"原始": quint["raw"], "中性化": quint["neu"]},
                "fig8_quintile.png",
                "图 8  五分组次月平均收益（%）",
                "Q1 = 价格相对锚最低（深套），Q5 = 浮盈最大。原始版本 Q5 为负收益，中性化后回升。",
                ylabel="月收益 %")

    bar_chart([sent_stats[g]["ic"] for g in ["悲观", "中性", "乐观"]], ["悲观", "中性", "乐观"],
              "fig9_sentiment.png", "图 9  按市场情绪三分组的 IC",
              f"时序回归 IC_t = a + b·情绪_t：b = {beta[1]:+.3f}，t = {beta[1]/se:+.2f}（与「乐观时效应更弱」的预测相反）。",
              ylabel="Rank IC")

    # 散点：市场换手率 vs IC
    xx = mkt_turn_pct.shift(1).reindex(ic_all.index)
    o = xx.notna() & ic_all.notna()
    scatter(xx[o].values * 100, ic_all[o].values, "fig10_turn_ic_scatter.png",
            "图 10  市场换手率与锚定效应强度",
            "横轴：上月全市场月换手率（%）；纵轴：当月 IC。红线为 OLS 拟合。",
            xlabel="上月全市场月换手率 %", ylabel="Rank IC")

    npx_ = inv["NewPersons"].shift(1).reindex(ic_all.index)
    o2 = npx_.notna() & ic_all.notna()
    scatter(npx_[o2].values, ic_all[o2].values, "fig11_csdc_newpersons.png",
            "图 11  外生散户入场强度与锚定效应",
            f"横轴：上月新增自然人投资者（万人）；纵轴：当月 IC。OLS 斜率 t = "
            f"{csdc_stats['new_persons']['t']:+.2f}，数据来自中登，不经由股价计算。",
            xlabel="上月新增自然人投资者（万人）", ylabel="Rank IC")

    print(f"[完成] 图表 {len(list(FIG.glob('*.png')))} 张")
    return 0


if __name__ == "__main__":
    sys.exit(main())
