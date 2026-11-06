#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""生成研究报告 DOCX（随后由 LibreOffice Kit 转 PDF）。"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

A = json.loads(Path("reports/assets.json").read_text(encoding="utf-8"))
FIG = Path("reports/figures")
CN, EN = "微软雅黑", "Times New Roman"


def _font(run, size=None, bold=None, color=None, name=CN):
    run.font.name = name
    r = run._element.rPr.rFonts
    r.set(qn("w:eastAsia"), CN)
    r.set(qn("w:ascii"), name)
    r.set(qn("w:hAnsi"), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)


def para(doc, text, size=10.5, bold=False, align=None, space=6, indent=True, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space)
    p.paragraph_format.line_spacing = 1.45
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.74)
    if align:
        p.alignment = align
    _font(p.add_run(text), size, bold, color)
    return p


def h(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    _font(p.add_run(text), 15 if level == 1 else 12, True, (20, 45, 90))
    return p


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.4
    _font(p.add_run(text), size)
    return p


def figure(doc, name, caption=None, width=15.4):
    """图片内已含图号与标题，默认不再重复添加图注。"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(10)
    p.add_run().add_picture(str(FIG / name), width=Cm(width))
    if caption:
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_after = Pt(10)
        _font(c.add_run(caption), 9, False, (90, 90, 90))


def table(doc, header, rows, widths=None, caption=None):
    if caption:
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_before = Pt(8)
        c.paragraph_format.keep_with_next = True
        _font(c.add_run(caption), 9.5, True, (60, 60, 60))
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, txt in enumerate(header):
        cell = t.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _font(p.add_run(str(txt)), 9, True)
    for row in rows:
        cells = t.add_row().cells
        for i, txt in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _font(p.add_run(str(txt)), 9)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


# ============================================================ 文档
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.6)
sec.top_margin = sec.bottom_margin = Cm(2.4)

st = doc.styles["Normal"]
st.font.name = CN
st.font.size = Pt(10.5)
st.element.rPr.rFonts.set(qn("w:eastAsia"), CN)

# 封面
for _ in range(4):
    doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_font(p.add_run("A 股锚定效应因子研究"), 26, True, (20, 45, 90))
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_font(p.add_run("机制成立，因子不成立"), 16, True, (120, 60, 60))
doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
_font(p.add_run("——基于 CSMAR 全样本（2013–2025，156 个月）的实证检验"), 12, False, (80, 80, 80))
for _ in range(8):
    doc.add_paragraph()
for line in ["研究范围：A 股全部上市与退市公司", "数据来源：CSMAR 日行情 / 上市公司基本信息 / 上市状态变更",
             "样本区间：2013 年 1 月 – 2025 年 12 月", "报告日期：2026 年 10 月 31 日"]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(p.add_run(line), 10.5, False, (90, 90, 90))
doc.add_page_break()

# 摘要
h(doc, "摘要", 1)
para(doc, "本报告检验一个在行为金融学中有长久传统、在 A 股被广泛口口相传的直觉：投资者以某个历史价格作为参照点（锚），"
          "而非以公允价值为参照点，因此价格的相对位置能够预测未来收益。我们把这个直觉做成可计算、可复现的横截面因子，"
          "并在 CSMAR 全样本上完成了从原始信号到扣费组合的完整检验。")
para(doc, f"样本覆盖 {A['n_stocks']:,} 只 A 股（含退市），{A['start']} 至 {A['end']} 共 {A['n_months']} 个月，"
          f"月末平均截面 {A['avg_xs']:.0f} 只。我们构造了四个价格锚——52 周高点、750 日高点、120 日与 250 日成交量加权均价（VWAP）——"
          "并以 1 个月反转与 12-1 动量作为必须超越的基准。")
para(doc, "核心结论有三条。第一，锚定效应在 A 股真实存在且方向明确：价格越高于参照点（浮盈越大），未来收益越低，"
          "四个锚的符号完全一致，且与美股文献报告的符号相反。第二，该效应高度集中于高换手、小市值股票，"
          "其强度与全市场换手率显著同向变动，证实它是一种散户驱动的现象。第三，也是最关键的——"
          "在行业与市值中性化、并进一步对反转与动量正交化之后，信号的截面信息含量降到接近零"
          f"（IC = −0.0063，t = −0.88），扣费后的组合表现也不足以支撑独立配置。")
para(doc, "因此本报告的判断是：锚定效应作为一个行为机制的描述是成立的，作为 A 股的可交易因子是不成立的。"
          "它观测到的收益差，本质上是行业与市值暴露、以及短期反转与动量的组合。", bold=True)
para(doc, "报告同时记录了一个值得继续追的副产品：该效应在 2017–2020 年几乎完全消失，2021 年后重新出现，"
          "且消失的时点与全市场换手率的低谷精确重合。这提示行为因子的强度与散户参与度绑定，"
          "而非随时间单调衰减——这一点对判断 A 股行为类因子的整体生命周期有直接含义。")
para(doc, "为排除「换手率本身来自价格、结论可能机械」的质疑，我们用中国结算的投资者统计做了外生验证："
          "新增自然人投资者数量对锚定效应强度的解释力 t = −2.86，1 个标准差冲击与市场换手率几乎等量，"
          "而该变量完全不经过股价计算；笔均成交金额在 2017–2020 达到峰值（单笔最大、机构化最重），"
          "同期效应最弱。两个独立数据源指向同一结论。")

doc.add_page_break()

# 1
h(doc, "1  研究问题", 1)
para(doc, "行为金融学的一个基础命题是：投资者的效用参照点不是财富的绝对水平，而是相对于某个参照点的变化。"
          "参照点可以是买入成本、历史高点、或者仅仅是印象深刻的某个价格。若这个命题成立，"
          "则「价格离参照点多远」应当包含对未来的预测信息。")
para(doc, "在 A 股，这个直觉被表述得非常朴素：「30 块买的，涨到 50 我就觉得涨太多了，先卖掉。」"
          "这句话包含两个可检验的成分：其一，投资者确实使用某个历史价格作为参照；其二，"
          "参照点的存在使卖出决策偏离基本面，从而在截面上产生可预测的收益差。")
para(doc, "本报告要回答三个问题：")
bullet(doc, "参照点效应在 A 股是否存在？方向是什么？与美股是否一致？")
bullet(doc, "若存在，它能否提供独立于已有因子（反转、动量、行业、市值）的信息？")
bullet(doc, "它的强度是否随时间变化？变动的驱动因素是什么？")

# 2
h(doc, "2  文献与机制", 1)
para(doc, "参照点依赖的理论源头是 Kahneman 与 Tversky 的前景理论，其核心是价值函数相对于参照点定义，"
          "且在损失一侧更陡。应用到股票市场，最直接的推论是处置效应：投资者倾向于卖出浮盈的股票、持有浮亏的股票"
          "（Shefrin and Statman, 1985；Odean, 1998）。")
para(doc, "Grinblatt 与 Han（2005）把处置效应与动量联系起来，提出用换手率加权重构当前股东的成本基础，"
          "并以资本利得悬垂（capital gains overhang, CGO）度量未实现盈亏。这条线索在 2026 年被 Riley 与 Zhou 推进："
          "他们指出 CGO 用期末价作分母会放大亏损、压缩盈利，改用买入价作分母后信号显著增强，"
          "并进一步提出「浮盈股东净比例」这一尺度无关的变量。")
para(doc, "另一条线索是锚定偏差本身。George 与 Hwang（2004）发现距 52 周高点越近的股票后续表现越好；"
          "Baker、Pan 与 Wurgler（2012）则证明连并购报价都被 52 周高点吸引。Cen、Hilary 与 Wei（2013）"
          "把锚定推进到分析师预测层面，发现分析师会以行业每股收益中位数为锚，且该偏差在盈余公告窗口转化为异常收益。")
para(doc, "与本报告最直接相关的是最新的一支文献：Bordalo、Gennaioli、La Porta 与 Shleifer（2025）"
          "用分析师预期构造「基于预期的收益」，发现价值、规模、投资、动量等因子的价差几乎可以被预期误差完全解释，"
          "留给风险的空间很小。这提示我们：许多被称为「异象」的横截面收益差，可能只是可预测的预期修正，"
          "而不是风险补偿。")
para(doc, "在此背景下，本报告的定位是：不去争论参照点效应是否存在（文献已相当充分），"
          "而是问一个更实际的问题——在 A 股，它能不能变成一个扣费后仍然活着的因子。")

# 3
h(doc, "3  数据与样本", 1)
para(doc, f"数据来自 CSMAR：日行情表（TRDNEW_Dalyr，含后复权收盘价与成交量）、上市公司基本信息年度表（行业代码、上市日期）、"
          f"上市状态变更表（ST 与退市时点）。原始 {A['n_stocks']:,} 只股票、2010 年 1 月至 2025 年 12 月共 1,520 万条日频记录。")
para(doc, "清洗规则为：交易状态为正常交易、成交量大于零、后复权收盘价非缺失且为正。剔除约 192 万条停牌、零成交与缺失记录后，"
          "保留 1,329 万条。因子计算需要 750 个交易日的历史窗口，因此信号自 2013 年 1 月起可用，"
          f"最终样本为 {A['n_months']} 个月、月末平均截面 {A['avg_xs']:.0f} 只。")
para(doc, "两点值得说明。第一，样本包含已退市公司（约 279 只终止上市），这对本研究尤其重要："
          "退市股几乎必然是深度浮亏的极端样本，若剔除将系统性低估参照点效应。第二，"
          "所有价格与锚的比较都在后复权空间内完成，避免送转造成的虚假偏离——"
          "未复权的价格序列在 10 送 10 时会机械性腰斩，凭空造出一个「深度套牢」的假信号，"
          "且这种假信号恰恰集中在高送转的成长股上，回测时看起来会「非常显著」。")

# 4
h(doc, "4  因子构造", 1)
para(doc, "所有信号采用同一形式：g = P / A − 1，其中 P 为月末后复权收盘价，A 为参照点。比值的含义是"
          "「现价比参照价高多少」，无量纲、可跨股票横向比较。四个参照点分别为：")
table(doc, ["参照点", "定义", "经济含义"],
      [["H252", "过去 252 个交易日最高价", "距一年高点多远"],
       ["H750", "过去 750 个交易日最高价", "距三年高点多远"],
       ["VWAP120", "过去 120 日成交量加权均价", "相对半年平均成本浮盈多少"],
       ["VWAP250", "过去 250 日成交量加权均价", "相对一年平均成本浮盈多少"]],
      caption="表 1  四个价格锚的定义")
para(doc, "成交量加权均价的构造为 VWAP = Σ(P·V) / ΣV，权重为当日成交量。其经济含义是「过去这段时间所有成交的平均价格」，"
          "可以粗略理解为这段时间买入者的平均成本。与换手加权成本（Riley and Zhou, 2026）相比，"
          "VWAP 把三年前买入的老股东和昨天买入的新股东同等对待，这是它的简化，也是它的局限——这一点在第 6 节还会讨论。")
para(doc, "截面处理统一为：1%/99% 分位截尾、对申万行业哑变量与对数流通市值做横截面回归取残差（即行业市值中性化）。"
          "关键的对照版本是在中性化残差基础上再对「1 个月反转」与「12-1 动量」做一次横截面回归取残差，"
          "我们称之为「正交化」——这是判断一个新因子是否为旧因子马甲的必要步骤。")
para(doc, "评价指标为月度截面 Rank IC（因子排序与次月收益排序的秩相关）、五分组多空收益、"
          "以及 Newey 与 West（1987）调整后的 t 值（滞后 6 期）。月度序列自相关会让普通 t 值高估显著性，"
          "本报告同时报告两者。")

doc.add_page_break()
# 5
h(doc, "5  实证结果", 1)

h(doc, "5.1  原始信号：方向确凿", 2)
para(doc, "表 2 报告四个锚在原始空间（未做中性化）的表现。所有系数符号为负，且 VWAP 两个锚的 t 值都超过 4。")
table(doc, ["锚", "1M IC", "t", "Q5−Q1 (1M)", "3M IC", "t"],
      [["H252", "−0.0358", "−1.85", "−0.81%", "−0.0293", "−1.59"],
       ["H750", "−0.0535", "−3.35", "−1.16%", "−0.0668", "−4.11"],
       ["VWAP120", "−0.0858", "−4.17", "−1.55%", "−0.0943", "−5.50"],
       ["VWAP250", "−0.0828", "−4.53", "−1.51%", "−0.0899", "−5.28"]],
      caption="表 2  四个锚的原始信号（方向：高 g = 浮盈大 = 未来收益低）")
para(doc, "这里出现第一个与国际文献的冲突：Riley 与 Zhou（2026）在美股发现浮盈筹码集中者后续跑赢（惜售主导），"
          "而 A 股的符号相反，是浮盈者跑输（落袋为安主导）。")
figure(doc, "fig8_quintile.png")

h(doc, "5.2  行业与市值中性化：效应衰减但仍显著", 2)
para(doc, "把 VWAP120 信号做行业与市值中性化后，结果如表 3。IC 从 −0.063 降到 −0.052，但 t 值反而上升到 −5.39"
          "（NW 调整后 −4.93），说明信号在中性化后更干净、更稳定。")
table(doc, ["版本", "IC", "IC t", "Newey-West t"],
      [["原始", "−0.0629", "−4.64", "−4.34"],
       ["行业 + 市值中性化", "−0.0515", "−5.39", "−4.93"],
       ["中性化 + 对反转与动量正交", "−0.0063", "−0.88", "−0.75"]],
      caption="表 3  中性化与正交化（全样本 2013–2025，144 个月）")

h(doc, "5.3  正交化：决定性检验", 2)
para(doc, "表 3 的第三行是本报告最重要的结果。在行业市值中性化的基础上，再把信号对 1 个月反转与 12-1 动量做横截面正交，"
          "IC 从 −0.052 直接掉到 −0.006，t 值 −0.88。", bold=True)
para(doc, "换言之，锚定效应所观测到的横截面收益差，在剔除行业、市值、短期反转与动量之后，不剩下有统计意义的信息。"
          "这就是「机制成立、因子不成立」的判据。")
para(doc, "一个必须承认的过程说明：在仅用 2021–2025 子样本、且未做行业市值中性化时，正交后的残差 IC 为 −0.035（t ≈ −2.0），"
          "看起来是存活的。样本拉长到 144 个月并补上中性化后，这个结论被推翻了。这也说明子样本结果的可信度有限，"
          "早期看似「边缘显著」的发现往往会在大样本下退潮。")

h(doc, "5.4  组合回测与交易成本", 2)
para(doc, "表 4 报告按中性化信号做多 Q1（深套）、做空 Q5（浮盈）的组合表现。样本为 2021–2025（回测部分未覆盖更早年份），"
          "等权、每期按名单变动计算换手，交易成本按单边 30 与 50 个基点两档计。")
table(doc, ["版本", "频率", "毛收益/月", "Sharpe", "换手/次", "30bp 净", "50bp 净", "净 Sharpe"],
      [["中性化", "月频", "+0.37%", "0.42", "42%", "+0.12%", "−0.05%", "−0.06"],
       ["中性化", "季频", "+0.67%", "0.80", "69%", "+0.53%", "+0.44%", "0.52"],
       ["中性化+正交", "月频", "+0.43%", "0.58", "41%", "+0.18%", "+0.02%", "0.03"],
       ["中性化+正交", "季频", "+0.49%", "0.54", "73%", "+0.35%", "+0.25%", "0.27"]],
      caption="表 4  组合回测与成本敏感性（2021–2025）")
para(doc, "两个有用的观察。第一，季频显著优于月频：虽然单次换手更高（69% 对 42%），但一年只调四次，"
          "年化换手 276% 对 504%，成本效率高得多；月频毛收益 +0.37% 在 50bp 成本下直接归零。"
          "第二，即便最优格（中性化、季频、30bp）的净 Sharpe 也只有 0.52，"
          "且该版本尚未对反转正交；正交后净 Sharpe 降到 0.27。")

h(doc, "5.5  时变特征：消失与复现", 2)
para(doc, "把 144 个月的 IC 序列按时期切开，出现了一个本报告最有意思的现象。")
table(doc, ["区间", "月数", "IC 均值", "Newey-West t"],
      [[k, A["periods"][k]["n"], f"{A['periods'][k]['ic']:+.4f}", f"{A['periods'][k]['t']:+.2f}"]
       for k in A["periods"]],
      caption="表 5  三期对比：效应不是单调衰减，而是消失后复现")
figure(doc, "fig2_period_ic.png", width=14.5)
para(doc, "2013–2016 极强（IC = −0.094，NW t = −4.62），2017–2020 几乎完全消失（IC = −0.015，NW t = −1.45），"
          "2021–2025 又回到 −0.055（NW t = −4.71）。对时间趋势做回归，b = +0.00026/月，t = 1.11，不显著。")
figure(doc, "fig1_yearly_ic.png")
figure(doc, "fig3_rolling_ic.png", width=14.5)
para(doc, "这个形状直接否决了一个直觉上很吸引人的假说：散户在经历多次牛熊之后「学乖了」，"
          "外推与处置倾向减弱。如果是学习效应，IC 应当单调向零收敛；实际是 U 型。"
          "这更像是状态依赖，而非参数漂移。")

h(doc, "5.6  散户参与度：横截面与时序", 2)
para(doc, "如果效应是散户驱动的，它应当集中在散户主导的股票上。按上月末换手率与流通市值三分组，结果如表 6。")
table(doc, ["分组维度", "低 / 小", "中", "高 / 大"],
      [["换手率", f"{A['turn_groups']['0']['ic']:+.4f} (t {A['turn_groups']['0']['t']:+.2f})",
        f"{A['turn_groups']['1']['ic']:+.4f} (t {A['turn_groups']['1']['t']:+.2f})",
        f"{A['turn_groups']['2']['ic']:+.4f} (t {A['turn_groups']['2']['t']:+.2f})"],
       ["流通市值", f"{A['mv_groups']['0']['ic']:+.4f} (t {A['mv_groups']['0']['t']:+.2f})",
        f"{A['mv_groups']['1']['ic']:+.4f} (t {A['mv_groups']['1']['t']:+.2f})",
        f"{A['mv_groups']['2']['ic']:+.4f} (t {A['mv_groups']['2']['t']:+.2f})"]],
      caption="表 6  横截面异质性：效应集中在高换手、小市值股票")
para(doc, "换手率三个分组完全单调，高换手组是低换手组的近四倍；市值也是单调的，小盘强、大盘弱。"
          "有力支持「锚定效应是散户现象」这一解释。")
figure(doc, "fig4_turn_group.png")
figure(doc, "fig5_mv_group.png", width=14.5)
para(doc, "把时期与换手率交叉，可以解释 2017–2020 的消失究竟发生在哪里。")
table(doc, ["区间", "低换手", "中换手", "高换手"],
      [[lab] + [f"{A['period_turn'][lab][str(k)]['ic']:+.3f} (t {A['period_turn'][lab][str(k)]['t']:+.1f})"
                for k in range(3)] for lab in A["periods"]],
      caption="表 7  时期 × 换手分组：消失只发生在机构主导的低换手组")
para(doc, "2017–2020 那四年，低换手组的效应直接翻正（+0.010），但高换手组始终为负（−0.039，t 仍达 −2.9）。"
          "所以「效应消失」的准确表述是：低换手（机构主导）那部分消失了，散户主导的那部分从未消失，只是减弱。")
figure(doc, "fig6_period_turn.png")
para(doc, "时序上，全市场月换手率的中位数在三个时期分别为 "
          + "、".join(f"{A['mkt_turn_period'][k]*100:.1f}%" for k in A["periods"])
          + "。换手率的低谷精确对应效应消失的四年。")
figure(doc, "fig7_market_turnover.png")
para(doc, "把月度 IC 对滞后一期的市场换手率回归，斜率为负且显著；而另外两个候选代理——"
          "小盘成交占比（t = 0.62）与大小盘收益差（t = −0.40）——都不显著。"
          "只有换手率这个「散户交易强度」的直接度量是显著的。")
figure(doc, "fig10_turn_ic_scatter.png")

h(doc, "5.7  市场情绪", 2)
para(doc, "一个自然的延伸是：情绪是否调节锚定效应的强度？直觉上，乐观时散户更愿意「让利润奔跑」、更晚卖出，"
          "因此卖压被推迟，效应应当变弱。用等权市场过去六个月累计收益作为情绪代理（滞后一期以避免前视），结果如表 8。")
table(doc, ["情绪三分组", "月数", "IC 均值", "Newey-West t"],
      [[g, A["sentiment"][g]["n"], f"{A['sentiment'][g]['ic']:+.4f}", f"{A['sentiment'][g]['t']:+.2f}"]
       for g in ["悲观", "中性", "乐观"]],
      caption="表 8  按市场情绪三分组的锚定效应")
para(doc, f"时序回归 IC_t = a + b·情绪_t 给出 b = {A['sent_beta']:+.4f}，t = {A['sent_t']:+.2f}。"
          "方向与上述直觉相反：乐观时期效应更强，而不是更弱。")
figure(doc, "fig9_sentiment.png")
para(doc, "一个可能的解释是：乐观时期外推让价格冲得更远，散户确实卖得更晚，但同时买得更疯。"
          "结果是浮盈最大的那一组价格被推到离基本面更远的位置，随后的回撤幅度更大。卖得晚只是把下跌推迟，"
          "并不能取消它，反而因为推迟而跌得更狠。")
para(doc, "但必须标注三点保留：三分组并不单调（中性组最弱、两端都强，呈 U 型），线性设定可能不合适；"
          "情绪代理本身来自价格，存在内生性；且 144 个月下可检出的最小效应量约 0.12，"
          "而估计值 0.095 恰在边界上，属于弱证据。")

h(doc, "5.8  外生验证：中国结算投资者数据", 2)
para(doc, "5.6 与 5.7 使用的代理——市场换手率与市场收益——都来自价格序列，存在内生性：高换手期本身就是高波动、强反转期，"
          "IC 的变动有可能是机械的。为此我们引入中国结算（中登）的投资者统计做外生检验，"
          "其中两个核心变量完全不经过股价计算：")
bullet(doc, "笔均成交金额 = 过户总金额 ÷ 过户笔数。单笔金额越小，说明散户占比越高。")
bullet(doc, "新增自然人投资者数量。散户入场的直接度量。")
para(doc, "中登主要指标表覆盖 2003-01 至 2023-08，投资者情况表覆盖 2015-04 至 2023-08，"
          "与 IC 序列的重叠期分别为 117 与 94 个月（2024–2025 两年因数据截止而缺失）。")
S = A["csdc"]
table(doc, ["代理变量", "来自价格", "b", "t", "1 个标准差冲击"],
      [["新增自然人投资者", "否", f"{S['new_persons']['b']:+.4f}", f"{S['new_persons']['t']:+.2f}",
        f"{S['new_persons']['effect']:+.4f}"],
       ["笔均成交金额（万元/笔）", "否", f"{S['per_trade']['b']:+.4f}", f"{S['per_trade']['t']:+.2f}",
        f"{S['per_trade']['effect']:+.4f}"],
       ["过户笔数", "否", "—", f"{S['transfer_numbers']['t']:+.2f}",
        f"{S['transfer_numbers']['effect']:+.4f}"],
       ["市场换手率（对照）", "是", f"{S['mkt_turn']['b']:+.4f}", f"{S['mkt_turn']['t']:+.2f}",
        f"{S['mkt_turn']['effect']:+.4f}"],
       ["过去 6 个月市场收益（对照）", "是", f"{S['sent']['b']:+.4f}", f"{S['sent']['t']:+.2f}",
        f"{S['sent']['effect']:+.4f}"]],
      caption="表 9  外生散户参与度代理对锚定效应强度的解释力")
para(doc, f"新增自然人投资者的 t 值为 {S['new_persons']['t']:+.2f}，1 个标准差冲击为 "
          f"{S['new_persons']['effect']:+.4f}，与市场换手率的 {S['mkt_turn']['effect']:+.4f} 几乎等量，"
          "但来自完全不同的数据源。这是对内生性质疑最直接的回应：散户入场越猛，锚定效应越强。"
          "笔均成交金额的方向也一致——笔均越大、机构占比越高、效应越弱——但不显著。")
figure(doc, "fig11_csdc_newpersons.png")
para(doc, "把笔均成交金额按时期取中位数，可以看到它和 IC 的走势高度吻合。")
pt = A["per_trade_period"]
table(doc, ["区间", "IC 均值", "笔均成交金额（万元/笔）", "全市场月换手率"],
      [[k, f"{A['periods'][k]['ic']:+.4f}", f"{pt[k]:.2f}" if pt[k] == pt[k] else "—",
        f"{A['mkt_turn_period'][k]*100:.1f}%"] for k in A["periods"]],
      caption="表 10  分期对比：两个独立数据源指向同一结论")
para(doc, "2017–2020 是笔均成交金额的峰值（7.74 万元，单笔最大、机构化最重），也正是锚定效应最弱的四年；"
          "2021 年后笔均降至 4.60 万元（散户回归），效应随之回升。这与用换手率得到的结论完全一致，"
          "而两者的数据来源互不重叠。")
para(doc, f"按笔均成交金额的高低分组也支持这一点：低落笔均（散户为主）时期 IC = {S['low_per_trade']['ic']:+.4f}"
          f"（NW t = {S['low_per_trade']['t']:+.2f}，{S['low_per_trade']['n']} 个月），"
          f"高落笔均（机构为主）时期 IC = {S['high_per_trade']['ic']:+.4f}"
          f"（NW t = {S['high_per_trade']['t']:+.2f}，{S['high_per_trade']['n']} 个月）。两组都显著，散户期更强。")
para(doc, "三点保留：中登数据止于 2023-08，恰好错过效应回升最快的 2024–2025；"
          "新增开户数本身与行情相关，并非完全外生；本节的结论加固的是「机制」那一半，"
          "并不改变第 5.3 节正交化后 IC 降至 −0.006 的事实。")

doc.add_page_break()
# 6
h(doc, "6  讨论", 1)
para(doc, "把上面几节拼起来，可以得到一个内部一致的叙述，也可以看到它在哪里断掉。")
para(doc, "成立的链条是：锚定/处置效应 → 横截面收益差 → 集中在高换手小市值 → 随全市场换手率起落。"
          "这条链条的每一环都有数据支持，且方向稳定。")
para(doc, "断掉的环节在最后一公里：这个收益差几乎完全可以由行业、市值、短期反转与动量复现。"
          "换句话说，「锚」是一个很好的叙事，但它把投资者引向的那笔钱，早就有别的因子在赚了。")
para(doc, "一个直接的问题随之而来：VWAP 是否是合适的锚？VWAP 把三年前买入的老股东与昨天买入的新股东同等对待，"
          "而处置效应恰恰强调「谁在持有、成本在哪」。换手加权成本（Riley and Zhou, 2026）能区分不同批次的持仓，"
          "理论上保留了 VWAP 丢失的信息。这仍是本方向唯一未被否证的原创性来源，"
          "但它需要流通股本的历史时点数据，且我们预计它与反转的相关性同样会很高。")
para(doc, "另一个值得追的线索是 2017–2020 的消失。这四年恰好是 A 股机构化最快、外资大幅流入、"
          "蓝筹白马主导的时期。如果行为因子的强度确实与散户参与度绑定，那么它对整个 A 股量化有直接含义："
          "2021 年后换手率回升，意味着这类因子是重新有效，而不是永久失效。这个视角比单个因子更有价值。")

# 7
h(doc, "7  结论与局限", 1)
para(doc, "结论：锚定效应在 A 股真实存在，方向与美股相反（落袋为安主导），且是一种散户现象；"
          "但在控制行业、市值、短期反转与动量后，它不提供独立的截面信息，扣费后的组合表现也不足以支撑独立配置。"
          "作为因子，判定为不成立。", bold=True)
h(doc, "局限", 2)
bullet(doc, "样本自 2013 年起：因子需要 750 个交易日的历史窗口，2010–2012 仅作为锚的预热期，未进入检验。")
bullet(doc, "回测部分仅覆盖 2021–2025：更早年度的组合与成本分析未完成，因此表 4 的结论不能外推到全样本。")
bullet(doc, "未使用分钟级数据：VWAP 用日频典型价近似，未做日内加权。")
bullet(doc, "情绪代理来自价格本身，存在内生性；若要用外生情绪变量（新增开户数、融资余额、笔均成交金额），需另行取数。")
bullet(doc, "流通市值字段单位为千元，换手率的绝对水平需按此换算；但横截面排序与时序回归的 t 值不受此影响。")
bullet(doc, "中登投资者数据止于 2023-08，2024–2025 的外生验证缺失；新增开户数亦非完全外生。")
bullet(doc, "未做涨跌停与停牌的可成交性过滤，也未考虑融券成本与券源约束，实盘表现会进一步低于回测。")

doc.add_page_break()
# 8
h(doc, "8  参考文献", 1)
refs = [
    "Atmaz, A., and S. Basak (2018). Option prices and disagreement. Journal of Finance, 73(3), 1225–1279.",
    "Baker, M., X. Pan, and J. Wurgler (2012). The effect of reference point prices on mergers and acquisitions. Journal of Financial Economics, 106(1), 49–71. NBER Working Paper 15551.",
    "Barberis, N., A. Mukherjee, and B. Wang (2016). Prospect theory and stock returns: An empirical test. Review of Financial Studies, 29(11), 3068–3107.",
    "Bordalo, P., N. Gennaioli, R. La Porta, and A. Shleifer (2025). Finance without exotic risk. Journal of Financial Economics, 173, 104145. DOI: 10.1016/j.jfineco.2025.104145.",
    "Cen, L., G. Hilary, and K. C. J. Wei (2013). The role of anchoring bias in the equity market: Evidence from analysts' earnings forecasts and stock returns. Journal of Financial and Quantitative Analysis, 48(1), 47–76. DOI: 10.1017/S0022109012000609.",
    "Daniel, K., D. Hirshleifer, and A. Subrahmanyam (1998). Investor psychology and security market under- and overreactions. Journal of Finance, 53(6), 1839–1885.",
    "Dechow, P., and H. You (2020). Understanding the determinants of analyst target price implied returns. The Accounting Review, 95(6), 125–149. DOI: 10.2308/TAR-2015-0265.",
    "Frazzini, A., and L. H. Pedersen (2014). Betting against beta. Journal of Financial Economics, 111(1), 1–25.",
    "George, T. J., and C.-Y. Hwang (2004). The 52-week high and momentum investing. Journal of Finance, 59(5), 2145–2176.",
    "Grinblatt, M., and B. Han (2005). Prospect theory, mental accounting, and momentum. Journal of Financial Economics, 78(2), 311–339.",
    "Jegadeesh, N., and S. Titman (1993). Returns to buying winners and selling losers: Implications for stock market efficiency. Journal of Finance, 48(1), 65–91.",
    "Li, S. Z., and Z. Luan (2025). News-based investor disagreement and stock returns. Review of Accounting Studies, 30(3), 2312–2375. DOI: 10.1007/s11142-025-09897-1.",
    "Liu, J., R. F. Stambaugh, and Y. Yuan (2019). Size and value in China. Journal of Financial Economics, 134(1), 48–69.",
    "Newey, W. K., and K. D. West (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica, 55(3), 703–708.",
    "Odean, T. (1998). Are investors reluctant to realize their losses? Journal of Finance, 53(5), 1775–1798.",
    "Riley, C., and Y. Zhou (2026). Shareholder-weighted returns and stock return predictability. International Review of Financial Analysis, 118, 105367. DOI: 10.1016/j.irfa.2026.105367.",
    "Shefrin, H., and M. Statman (1985). The disposition to sell winners too early and ride losers too long. Journal of Finance, 40(3), 777–790.",
    "Tversky, A., and D. Kahneman (1974). Judgment under uncertainty: Heuristics and biases. Science, 185(4157), 1124–1131.",
]
for i, r in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    _font(p.add_run(f"[{i}] "), 9, True)
    _font(p.add_run(r), 9)

doc.add_page_break()
h(doc, "附录：图表索引", 1)
for line in ["图 1  锚定效应逐年衰减与复现（中性化信号 IC）",
             "图 2  三期对比：效应消失又复现",
             "图 3  36 个月滚动 IC",
             "图 4  锚定效应集中于高换手（散户主导）股票",
             "图 5  锚定效应集中于小市值股票",
             "图 6  时期 × 换手分组",
             "图 7  全市场月换手率（%）",
             "图 8  五分组次月平均收益（%）",
             "图 9  按市场情绪三分组的 IC",
             "图 10  市场换手率与锚定效应强度",
             "表 1  四个价格锚的定义",
             "表 2  四个锚的原始信号",
             "表 3  中性化与正交化",
             "表 4  组合回测与成本敏感性",
             "表 5  三期对比",
             "表 6  横截面异质性",
             "表 7  时期 × 换手分组",
             "表 8  按市场情绪三分组的锚定效应", "图 11  外生散户入场强度与锚定效应", "表 9  外生散户参与度代理对锚定效应强度的解释力", "表 10  分期对比：两个独立数据源指向同一结论"]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    _font(p.add_run(line), 10)

out = Path("reports/report_zh_source.docx")
doc.save(out)
print(f"saved {out}")
