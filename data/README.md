# 数据说明

本仓库**不包含任何原始数据**。CSMAR 与中登数据受许可协议约束，仅授权个人在特定机构内使用，不可再分发。

## 需要自备的文件

| 文件名模式 | 来源 | 关键字段 | 用途 |
|---|---|---|---|
| `TRDNEW_Dalyr*.csv` | CSMAR 个股交易数据库 · 日行情 | `Stkcd` `Trddt` `Trdsta` `Clsprc` `Dnshrtrd` `Dsmvosd` `Adjprcwd` | 价格、成交量、流通市值 |
| `STK_ITEMCHANGE*.csv` | CSMAR 上市状态变更表 | `Symbol` `ChangeDate` `ChangedItem` `ValueAfter` | ST 区间、退市时点 |
| `STK_LISTEDCOINFOANL*.csv` | CSMAR 上市公司基本信息年度表 | `Symbol` `EndDate` `IndustryCode` `LISTINGDATE` | 行业中性化、次新股过滤 |
| `QX_CSDC*.csv` | 中国结算 · 主要指标统计表 | `SgnMonth` `TransferNumbers` `TransferAmounts` | 笔均成交金额（外生散户代理） |
| `QX_InvestorM*.csv` | 中国结算 · 投资者情况统计表 | `SgnMonth` `NewPersons` `FinalAPerons` | 新增自然人投资者 |

## 放置方式

直接丢进 `data/raw/` 即可，**支持任意子目录与分卷命名**（例如 `data/raw/2018-2022-价格/TRDNEW_Dalyr3.csv`），加载器会递归查找。

也可以用环境变量指定外部路径：

```bash
# Windows PowerShell
$env:ANCHOR_DATA_ROOT = "D:\data\csmar_export"
$env:ANCHOR_CACHE     = "D:\data\cache\prices.pkl"

# Linux / macOS
export ANCHOR_DATA_ROOT=/data/csmar_export
export ANCHOR_CACHE=/data/cache/prices.pkl
```

## 两个容易致命的坑

**1. 必须用后复权价（`Adjprcwd`）**

目标锚与现价的比较都在复权空间内完成。若用未复权价，10 送 10 会机械腰斩，凭空造出一个「深度套牢」的假信号——而且这些假信号恰好集中在高送转的成长股上，回测时会显得「非常显著」。

**2. `Dsmvosd`（流通市值）的单位是千元**

成交额 = 成交量 × 未复权价，单位是元。计算换手率时分母必须乘 1000：

```python
turnover = (volume * close_raw).sum() / (float_mv * 1000)
```

算错的话换手率会放大 1000 倍，横截面排序不受影响但时序水平完全失真。

## 样本量参考

完整样本（2010-01 – 2025-12，含退市）：

- 原始日频记录 1,520 万条
- 清洗后 1,329 万条（剔除 192 万条停牌 / 零成交 / 缺失）
- 股票 5,831 只，其中约 279 只已终止上市

保留退市股是有意为之：退市股几乎必然是深度浮亏的极端样本，剔除会系统性低估锚定效应。
