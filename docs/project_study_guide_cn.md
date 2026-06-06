# SA-CCR 项目中文学习手册

这份手册的目标不是替代代码注释，而是帮助你真正理解这个项目，并能在面试中清楚解释：

- 这个项目在解决什么问题
- 每个模块负责哪一段计算
- SA-CCR 的核心公式如何落到代码
- Excel 对账表如何证明 Python 引擎结果可信
- 哪些地方是 demo 级实现，哪些地方和真实生产监管系统还有差距

建议你按下面这个顺序学习：

```text
1. 先看业务全链路
2. 再看输入数据字段
3. 再看 trade-level 逐笔计算
4. 再看 AddOn 聚合
5. 再看 RC / PFE / EAD
6. 最后用 Excel 对账表反向验证代码
```

---

## 1. 项目一句话说明

这个项目是一个基于 Python 的 Basel-aligned SA-CCR demo engine。它读取一组公开安全的 synthetic derivative portfolio，对每笔交易做 SA-CCR enrichment，然后按 counterparty、netting set、asset class、hedging set 聚合，最终输出 RC、PFE、EAD 和 illustrative RWA，并生成 HTML 报告和 Excel 对账表。

面试中可以这样说：

> I built a Python-based Basel-aligned SA-CCR exposure engine. It covers trade enrichment, adjusted notional, supervisory delta, maturity factor, asset-class add-on aggregation, RC/PFE/EAD calculation, margined EAD cap logic, and reviewer-facing HTML/Excel reconciliation outputs across interest rate, FX, credit, equity, and commodity derivatives.

中文理解：

> 我做了一个 SA-CCR 暴露计算 demo，不是只算单笔交易，而是从交易数据、抵押品、counterparty reference 开始，跑完整个 portfolio capital workflow，并用 Excel 对账表复核 Python 计算链路。

---

## 2. 项目结构地图

```text
CCR_Projects/
|-- data/
|   |-- sample_trades.csv
|   |-- collateral.csv
|   |-- counterparty_reference.csv
|   `-- README.md
|-- docs/
|   |-- SA_CCR_Excel_Reconciliation_Workbook.xlsx
|   |-- methodology.md
|   |-- project_study_guide_cn.html
|   |-- regulatory_alignment.md
|   |-- sa_ccr_portfolio_report.html
|   |-- sa_ccr_portfolio_report.md
|   `-- project_study_guide_cn.md
|-- outputs/
|   |-- trade_level_enriched.csv
|   |-- addon_detail.csv
|   |-- asset_class_addon.csv
|   |-- netting_set_exposure.csv
|   |-- unmargined_cap_exposure.csv
|   |-- counterparty_summary.csv
|   |-- asset_class_summary.csv
|   `-- data_quality_issues.csv
|-- scripts/
|   |-- build_industry_style_sample.py
|   |-- run_saccr.py
|   `-- generate_report.py
|-- src/saccr_engine/
|   |-- config.py
|   |-- data_checks.py
|   |-- enrichment.py
|   |-- addon.py
|   |-- exposure.py
|   |-- pipeline.py
|   `-- reporting.py
`-- tests/
    `-- test_core_calculations.py
```

最核心的阅读顺序：

```text
pipeline.py
-> data_checks.py
-> enrichment.py
-> addon.py
-> exposure.py
-> reporting.py
```

如果你只看一个文件来理解全流程，先看 `src/saccr_engine/pipeline.py`。

---

## 3. 项目运行链路

项目的主流程是：

```bash
python scripts/build_industry_style_sample.py
python scripts/run_saccr.py
python scripts/generate_report.py
pytest
```

每一步含义：

| 命令 | 作用 | 输出 |
| --- | --- | --- |
| `build_industry_style_sample.py` | 生成 synthetic portfolio | `data/sample_trades.csv`, `data/collateral.csv`, `data/counterparty_reference.csv` |
| `run_saccr.py` | 运行 SA-CCR engine | `outputs/*.csv` |
| `generate_report.py` | 生成展示报告 | `docs/sa_ccr_portfolio_report.html`, `docs/sa_ccr_portfolio_report.md` |
| `pytest` | 跑核心单元测试 | 验证关键公式和 pipeline 能运行 |

你要理解的是：这个项目不是 notebook，而是一个正常 Python 项目，脚本只是入口，真正的业务逻辑在 `src/saccr_engine/`。

---

## 4. 输入数据怎么理解

### 4.1 `data/sample_trades.csv`

这是交易级输入表。它包含 298 笔 synthetic trades，覆盖 5 个 SA-CCR asset classes 和 19 类产品：

| Asset Class | Product examples |
| --- | --- |
| Interest Rate | IRS, Cross Currency Swap, FRA, OIS, Swaption, Cap/Floor |
| FX | FX Forward, FX Swap, FX Option |
| Credit | Single-name CDS, Index CDS, Credit TRS |
| Equity | Equity TRS, Equity Index Option |
| Commodity | Oil Forward, Electricity Swap, Precious Metal Swap, Commodity Option |

重点字段：

| 字段 | 含义 |
| --- | --- |
| `COB Date` | 估值日期 |
| `Counterparty ID` | 交易对手 |
| `Netting Set ID` | 净额组 |
| `Ticket Number` | 交易编号 |
| `Trade Type` | 产品类型 |
| `Asset Class` | SA-CCR 资产类别 |
| `Maturity Date` | 到期日 |
| `Base Notional` | USD-equivalent demo notional |
| `Buy/Sell Indicator` | 方向，用于 delta 正负号 |
| `MtM` | 当前市场价值 |
| `Margined/ Unmargined` | 是否有保证金协议 |
| `CCP` | 是否集中清算 |
| `Margin Frequency (Business Days)` | 保证金周期，用于 MPOR/maturity factor |
| `Put/Call Indicator`, `Strike Price (Ki)`, `Underlying Price (Pi)` | option delta 需要的字段 |

### 4.2 `data/collateral.csv`

这是 netting-set level 的 CSA/抵押品字段。

重点字段：

| 字段 | 含义 |
| --- | --- |
| `Collateral Amount` | 抵押品金额 C |
| `Threshold Amount` | threshold, TH |
| `Minimum Transfer Amount` | MTA |
| `Net Independent Collateral Amount` | NICA |

这些字段用于 margined RC：

```text
RC = max(V - C, TH + MTA - NICA, 0)
```

### 4.3 `data/counterparty_reference.csv`

这是 counterparty 层参考信息。当前主要用于 illustrative RWA：

```text
RWA = EAD * Risk Weight
```

注意：这里的 risk weight 是 demo reference，不是完整信用风险资本引擎。

---

## 5. `pipeline.py`：全流程编排

`pipeline.py` 是项目的总控。

核心函数：

```python
run_pipeline(trades_path, counterparty_reference_path, collateral_path)
```

它做的事情：

```text
1. 读取 trade CSV
2. 做数据质量检查
3. trade-level enrichment
4. 读取 collateral 和 counterparty reference
5. 计算 AddOn
6. 计算 RC
7. 计算 PFE / EAD / RWA
8. 重新跑 unmargined 版本，用于 margined EAD cap
9. 输出 counterparty summary 和 asset class summary
```

关键代码逻辑：

```text
validate_trades(trades)
enrich_trades(trades)
calculate_addons(enriched)
calculate_replacement_costs(enriched, collateral)
calculate_exposure(netting_set_addon, replacement_costs, counterparty_reference)
apply_margined_ead_cap(...)
build_counterparty_summary(...)
build_asset_class_summary(...)
```

你可以把 `pipeline.py` 理解成工厂流水线。它自己不写复杂公式，而是把每个模块的结果串起来。

面试表达：

> The pipeline separates concerns. Data validation, trade enrichment, add-on aggregation, exposure calculation, and report generation are implemented in separate modules, while `pipeline.py` orchestrates the end-to-end workflow and returns all intermediate outputs for reconciliation.

---

## 6. `config.py`：参数表

`config.py` 存放 SA-CCR 参数和 demo 配置。

核心参数：

```python
ALPHA = 1.4
MULTIPLIER_FLOOR = 0.05
BUSINESS_DAYS_PER_YEAR = 250.0
SUPERVISORY_DURATION_RATE = 0.05
```

Supervisory factors 示例：

| Asset / Product | Supervisory Factor |
| --- | --- |
| Interest Rate | 0.005 |
| FX | 0.04 |
| Equity Single Name | 0.32 |
| Equity Index | 0.20 |
| Commodity Electricity | 0.40 |
| Commodity Oil/Gas | 0.18 |

Credit 根据 rating 取 supervisory factor，例如：

| Rating | Factor |
| --- | --- |
| AAA/AA | 0.0038 |
| A | 0.0042 |
| BBB | 0.0054 |
| BB | 0.0106 |
| B | 0.0160 |
| CCC | 0.0600 |

Correlation 示例：

| 类型 | Correlation |
| --- | --- |
| Credit Single Name | 0.50 |
| Credit Index | 0.80 |
| Equity Single Name | 0.50 |
| Equity Index | 0.80 |
| Commodity | 0.40 |

学习重点：

- `config.py` 不负责计算，只负责参数。
- 面试时你可以说这些是 Basel-style demo parameters。
- 不要说这是完整生产参数库，因为真实银行会有更复杂的 product taxonomy、rating mapping、jurisdiction overrides 和 parameter governance。

---

## 7. `data_checks.py`：数据质量检查

这个模块做最基础的数据质量检查。

必需字段：

```text
COB Date
Counterparty ID
Netting Set ID
Ticket Number
Trade Type
Asset Class
Maturity Date
Base Notional
Buy/Sell Indicator
MtM
```

检查内容：

| 检查 | 作用 |
| --- | --- |
| required columns | 如果缺少核心字段，直接报错 |
| missing values | 记录 warning |
| unknown asset class | 记录 error |
| expired maturity | 记录 warning |

输出：

```text
outputs/data_quality_issues.csv
```

学习重点：

这个模块不是完整数据治理系统。真实生产系统还需要 source lineage、字段级校验、legal netting agreement 校验、CSA 数据完整性、collateral eligibility、market data quality 等。

面试表达：

> I included a lightweight data-quality layer to check required fields, known asset classes, missing values, and expired maturities. It is not a full production data governance framework, but it makes the demo workflow reproducible and auditable.

---

## 8. `enrichment.py`：逐笔交易计算

这是最重要的模块之一。它把原始交易变成 SA-CCR 计算需要的 enriched trade table。

输出文件：

```text
outputs/trade_level_enriched.csv
```

核心入口：

```python
enrich_trades(trades, force_unmargined=False)
```

每笔交易会新增这些字段：

```text
Maturity Days
Remaining Maturity Years
Maturity Bucket
Commodity Group
Commodity Type
Hedging Set
SA-CCR Margin Treatment
Supervisory Factor Base
Supervisory Factor Adjustment
Supervisory Factor
Correlation
Supervisory Duration
Adjusted Notional
Supervisory Option Volatility
Delta
Maturity Factor
Effective Notional
```

### 8.1 Remaining maturity 和 maturity bucket

```text
Maturity Days = Maturity Date - COB Date
Remaining Maturity Years = Maturity Days / 365
```

Interest Rate 的 maturity bucket：

```text
<1Y
1Y-5Y
>5Y
```

这三个 bucket 后面用于 IR add-on aggregation。

### 8.2 Hedging set

不同 asset class 的 hedging set 不一样：

| Asset Class | Hedging Set |
| --- | --- |
| Interest Rate | currency，例如 USD、EUR、CNY |
| FX | currency pair，例如 EUR/USD |
| Credit | underlying entity |
| Equity | underlying entity |
| Commodity | commodity group，例如 Energy、Metals |

Basis / volatility trades 会加后缀：

```text
USD_Basis
EUR_Volatility
```

### 8.3 Supervisory factor

```text
Supervisory Factor = Supervisory Factor Base * Supervisory Factor Adjustment
```

Adjustment：

| 类型 | Multiplier |
| --- | --- |
| 普通交易 | 1.0 |
| Basis transaction | 0.5 |
| Volatility transaction | 5.0 |

注意：普通 option 不等于 volatility transaction。普通 option 的影响主要体现在 supervisory delta。

### 8.4 Supervisory duration

Interest Rate 和 Credit 需要 supervisory duration。

公式思想：

```text
SD = (exp(-0.05 * S) - exp(-0.05 * E)) / 0.05
```

其中：

- `S` 是 start date 到 COB 的年数，最小为 0
- `E` 是 end/maturity date 到 COB 的年数
- 最短期限有 10 business days floor

其他 asset class 的 supervisory duration 当前设为 1。

### 8.5 Adjusted notional

逻辑：

| Asset Class | Adjusted Notional |
| --- | --- |
| Interest Rate | `Base Notional * Supervisory Duration` |
| Credit | `Base Notional * Supervisory Duration` |
| FX | 使用 base notional；如果缺失则取两条 leg notional 较大值 |
| Equity | 当前用 base notional proxy |
| Commodity | 当前用 base notional proxy |

真实监管生产系统里，equity/commodity adjusted notional 理想上应从价格和数量计算；这个项目为了 demo 可复现，用 base notional proxy。

### 8.6 Supervisory delta

非 option：

```text
Buy  -> +1
Sell -> -1
```

Option：

```text
Call delta = direction * N(d1)
Put delta  = -direction * N(-d1)
```

其中：

```text
d1 = [ln(P / K) + 0.5 * sigma^2 * T] / [sigma * sqrt(T)]
```

字段含义：

| 符号 | 字段 |
| --- | --- |
| P | `Underlying Price (Pi)` |
| K | `Strike Price (Ki)` |
| sigma | `Supervisory Option Volatility` |
| T | exercise date 到 COB 的年数 |

### 8.7 Maturity factor

Unmargined：

```text
MF = sqrt(min(M, 1))
```

其中 `M` 是 remaining maturity years，并有 10 business days floor。

Margined：

```text
MF = 1.5 * sqrt(MPOR / 250)
```

MPOR floor：

| 情况 | Floor |
| --- | --- |
| CCP cleared | 5 business days |
| Non-CCP | 10 business days |

### 8.8 Effective notional

这是 trade-level enrichment 的最终核心字段：

```text
Effective Notional = Adjusted Notional * Delta * Maturity Factor
```

后面所有 AddOn 聚合基本都从 `Effective Notional` 开始。

你必须能讲清楚这一句：

> Trade-level enrichment converts raw economics into SA-CCR calculation fields. The key output is effective notional, which combines adjusted notional, supervisory delta, and maturity factor.

---

## 9. `addon.py`：AddOn 聚合

这个模块负责把逐笔交易的 effective notional 聚合成 asset-class add-on。

输出文件：

```text
outputs/addon_detail.csv
outputs/asset_class_addon.csv
```

入口：

```python
calculate_addons(enriched_trades)
```

返回三个表：

| 表 | 含义 |
| --- | --- |
| `addon_detail` | 每个 asset class / hedging set 的明细 AddOn |
| `asset_class_addon` | netting set + asset class 层 AddOn |
| `netting_set_addon` | netting set 层合计 AddOn |

### 9.1 Interest Rate AddOn

IR 的 aggregation 比较特殊。先按：

```text
Counterparty ID
Netting Set ID
Asset Class
Hedging Set
Maturity Bucket
```

汇总 effective notional。

三个 maturity bucket：

```text
D1 = <1Y
D2 = 1Y-5Y
D3 = >5Y
```

聚合公式：

```text
Aggregated Effective Notional
= sqrt(D1^2 + D2^2 + D3^2 + 1.4*D1*D2 + 1.4*D2*D3 + 0.6*D1*D3)
```

然后：

```text
IR AddOn = Aggregated Effective Notional * 0.005
```

这个公式体现不同 maturity bucket 之间的部分抵消。

### 9.2 FX AddOn

FX 按 currency pair hedging set 聚合：

```text
Aggregated Effective Notional = abs(sum(Effective Notional))
FX AddOn = Aggregated Effective Notional * 0.04
```

同一 currency pair 内多空可以抵消。

### 9.3 Credit / Equity AddOn

Credit 和 Equity 先按 entity 聚合，再用 correlation formula。

Entity level：

```text
Entity AddOn = Effective Notional * Supervisory Factor
Systematic Component = Correlation * Entity AddOn
Idiosyncratic Component = (1 - Correlation^2) * Entity AddOn^2
```

Netting set + asset class 层：

```text
AddOn = sqrt(Systematic_Total^2 + Idiosyncratic_Total)
```

Index correlation 通常高于 single-name，因此 index trades 的 diversification treatment 不同。

### 9.4 Commodity AddOn

Commodity 逻辑和 credit/equity 类似，但是先按 commodity type 聚合。

```text
Type AddOn = Effective Notional * Supervisory Factor
Systematic Component = Correlation * Type AddOn
Idiosyncratic Component = (1 - Correlation^2) * Type AddOn^2
Commodity AddOn = sqrt(Systematic_Total^2 + Idiosyncratic_Total)
```

Commodity 当前 correlation 使用 0.40。

### 9.5 Netting set AddOn

最后，把同一个 netting set 下所有 asset class add-on 相加：

```text
AddOn Aggregate = sum(asset class AddOn)
```

这个 `AddOn Aggregate` 会进入 PFE 计算。

面试表达：

> Add-on aggregation is asset-class specific. Interest rate trades use maturity-bucket aggregation, FX aggregates by currency pair, credit and equity use entity-level correlation aggregation, and commodity uses type/group correlation aggregation. The final netting-set AddOn is the sum of asset-class add-ons.

---

## 10. `exposure.py`：RC / PFE / EAD / RWA

这个模块把 AddOn 转成 exposure。

输出文件：

```text
outputs/netting_set_exposure.csv
outputs/unmargined_cap_exposure.csv
```

### 10.1 Replacement Cost

Unmargined：

```text
RC = max(V - C, 0)
```

Margined：

```text
RC = max(V - C, TH + MTA - NICA, 0)
```

符号含义：

| 符号 | 含义 |
| --- | --- |
| V | netting set 内所有 trade 的 net MtM |
| C | collateral amount |
| TH | threshold |
| MTA | minimum transfer amount |
| NICA | net independent collateral amount |

代码位置：

```python
replacement_cost(...)
calculate_replacement_costs(...)
```

### 10.2 PFE multiplier

公式：

```text
multiplier = min(1, floor + (1 - floor) * exp((V - C) / [2 * (1 - floor) * AddOn]))
floor = 0.05
```

直觉：

- 如果 `V - C` 很高，multiplier 接近 1
- 如果交易组合负 MtM 或 over-collateralized，multiplier 会下降
- 但 multiplier 不会低于 5% floor

代码位置：

```python
pfe_multiplier(value, collateral, addon_aggregate)
```

### 10.3 PFE

```text
PFE = multiplier * AddOn Aggregate
```

### 10.4 EAD

```text
EAD = alpha * (RC + PFE)
alpha = 1.4
```

这是 SA-CCR 最核心的总公式。

### 10.5 Margined EAD cap

项目对 margined netting set 做了 EAD cap：

```text
Margined EAD <= same netting set calculated on unmargined basis
```

实现方式：

```text
1. 正常跑一次 margined / unmargined 混合 portfolio
2. 强制所有 trades 按 unmargined 再跑一次
3. 如果某个 margined netting set 的 EAD 超过 unmargined EAD，则 cap 到 unmargined EAD
```

代码位置：

```python
apply_margined_ead_cap(...)
```

输出字段：

```text
Unmargined EAD Cap
EAD Before Cap
EAD Cap Applied
```

### 10.6 RWA

```text
RWA = EAD * Risk Weight
```

注意：项目里的 RWA 是 illustrative RWA，不是完整信用风险资本引擎。

面试表达：

> The exposure module calculates replacement cost, the PFE multiplier, PFE, EAD, and illustrative RWA at the netting-set level. For margined netting sets, it also applies the Basel-style EAD cap by comparing the margined EAD with the same portfolio calculated on an unmargined basis.

---

## 11. `reporting.py` 和输出文件

`reporting.py` 做两件事：

```text
1. counterparty-level summary
2. asset-class-level summary
3. write all result DataFrames to outputs/*.csv
```

核心输出：

| 文件 | 用途 |
| --- | --- |
| `trade_level_enriched.csv` | 逐笔交易 enriched 字段 |
| `addon_detail.csv` | AddOn 聚合明细 |
| `asset_class_addon.csv` | 每个 netting set + asset class 的 AddOn |
| `netting_set_exposure.csv` | RC/PFE/EAD/RWA 核心结果 |
| `unmargined_cap_exposure.csv` | EAD cap 对照结果 |
| `counterparty_summary.csv` | counterparty 层汇总 |
| `asset_class_summary.csv` | asset class 层汇总 |
| `data_quality_issues.csv` | 数据质量检查输出 |

你可以这样理解：

```text
outputs/*.csv 是模型结果表
docs/*.html 是展示报告
docs/*.xlsx 是对账审计表
```

---

## 12. HTML 报告怎么读

文件：

```text
docs/sa_ccr_portfolio_report.html
```

它适合给面试官快速看项目成果。

重点看：

| 区域 | 你要能解释什么 |
| --- | --- |
| Product Coverage | 覆盖哪些 asset class 和 product type |
| Portfolio Overview | trade count、netting sets、counterparties |
| Calculation Methodology | SA-CCR 公式和流程 |
| Exposure Results | AddOn、PFE、RC、EAD、RWA |
| Top Counterparties / Netting Sets | 风险集中在哪里 |
| Limitations | 哪些地方不是生产级 |

这个报告是“业务展示层”，不是计算引擎本体。

---

## 13. Excel 对账表怎么用来学习

文件：

```text
docs/SA_CCR_Excel_Reconciliation_Workbook.xlsx
```

这是你理解项目最有价值的材料之一，因为它把 Python 的计算链路用 Excel 公式复刻了一遍。

重点 sheet：

| Sheet | 用途 |
| --- | --- |
| `Summary` | 总览：trade count、counterparty count、AddOn、PFE、RC、EAD |
| `Checks` | Excel vs Python 的 pass/fail 控制表 |
| `Inputs_Trades` | 原始交易输入 |
| `Inputs_Collateral` | collateral 输入 |
| `Inputs_Counterparties` | counterparty/risk weight 输入 |
| `Trade_Calc` | 逐笔交易公式复刻 |
| `AddOn_Calc` | AddOn 公式复刻 |
| `Asset_Class_AddOn` | asset class 层对账 |
| `Netting_Set_Calc` | RC/PFE/EAD/RWA 对账 |
| `Counterparty_Calc` | counterparty 层对账 |
| `Python_*` | Python 输出作为 target |

建议学习路径：

```text
1. 先打开 Summary，看总结果
2. 再看 Checks，确认所有层级 OK
3. 再到 Trade_Calc 选一笔交易，看每列公式
4. 再到 AddOn_Calc，看 effective notional 怎么被聚合
5. 再到 Netting_Set_Calc，看 RC、multiplier、PFE、EAD
6. 最后到 Python_* sheet，看 Excel 结果如何和 Python 输出对齐
```

当前对账结果：

| Check Area | 状态 |
| --- | --- |
| Trade effective notional | OK |
| AddOn detail | OK |
| Asset class add-on | OK |
| Netting-set EAD | OK |
| Counterparty EAD | OK |
| Total EAD | OK |

尾差大约在 floating point precision 级别，不影响对账结论。

面试表达：

> I built an Excel reconciliation workbook as an independent reviewer-facing audit layer. It recreates the main SA-CCR calculations using Excel formulas and reconciles them against the Python engine outputs at trade, add-on, netting-set, and counterparty levels.

---

## 14. 测试怎么理解

文件：

```text
tests/test_core_calculations.py
```

测试覆盖：

| 测试 | 验证内容 |
| --- | --- |
| `test_replacement_cost_is_floored_at_zero` | RC 不能小于 0 |
| `test_margined_replacement_cost_uses_threshold_mta_and_nica` | margined RC 使用 TH/MTA/NICA |
| `test_pfe_multiplier_is_between_floor_and_one` | multiplier 在 5% floor 和 1 之间 |
| `test_normal_cdf_midpoint` | option delta 用到的 normal CDF |
| `test_basis_transaction_reduces_supervisory_factor` | basis transaction factor adjustment |
| `test_pipeline_runs_on_sample_data` | 整个 pipeline 能跑通并输出核心字段 |

面试时不要夸大测试覆盖。可以这样说：

> The tests cover the most important formula-level behavior and a full pipeline smoke test. For production, I would expand tests with more regulatory examples, boundary cases, product-specific golden cases, and independent model validation packs.

---

## 15. 当前最终结果怎么记

当前项目跑出的 portfolio summary 大致是：

| 指标 | 数值 |
| --- | ---: |
| Trades | 298 |
| Counterparties | 12 |
| Netting Sets | 95 |
| Total AddOn | 568.0mm |
| Total PFE | 354.9mm |
| Total RC | 114.2mm |
| Total EAD | 656.7mm |

Asset class AddOn 大小排序：

```text
Interest Rate
Commodity
Equity
FX
Credit
```

你不需要死背所有数字，但要知道：

- Interest Rate AddOn 最大，因为 portfolio 里 IR notionals 和 maturity structure 较大
- Commodity / Equity 的 supervisory factor 较高，所以也贡献较多 AddOn
- Credit AddOn 相对较小，与样本 notional、rating factor 和产品分布有关

---

## 16. 和真实生产监管系统的差距

这个项目适合说成：

```text
Basel-aligned educational / interview portfolio engine
```

不要说成：

```text
Fully production-compliant regulatory capital engine
```

主要差距：

| 领域 | 当前项目 | 真实生产系统还需要 |
| --- | --- | --- |
| 数据 | synthetic portfolio | source system lineage、trade capture、market data feed、daily controls |
| Legal netting | 用 `Netting Set ID` 表示 | legal enforceability、jurisdiction review、netting agreement validation |
| Collateral | 简化 CSA 字段 | VM/IM、collateral eligibility、haircuts、settlement timing、dispute logic |
| Product taxonomy | 19 类 demo 产品 | 完整产品库、hybrid trades、exotic mapping |
| Market data | static / simplified | FX rates、curves、underlying prices、calibration controls |
| RWA | illustrative risk weight | 完整信用风险资本规则、CRM、rating/PD/LGD、jurisdiction templates |
| CVA/CCP | 不在范围内 | CVA capital、default fund exposure、CCP-specific rules |
| Governance | README + tests + Excel reconciliation | model validation、audit trail、change control、sign-off |

面试表达：

> I would describe it as Basel-aligned for the core SA-CCR default-risk exposure workflow, but not as a full regulatory capital production engine. The remaining gaps are mainly around legal enforceability, collateral eligibility and haircuts, full product taxonomy, production data governance, CVA/CCP capital, and jurisdiction-specific reporting.

---

## 17. 推荐学习方法：三遍法

### 第一遍：看流程

目标：知道每个文件做什么。

你只需要回答：

```text
输入是什么？
经过哪些模块？
输出是什么？
```

建议看：

```text
README.md
src/saccr_engine/pipeline.py
docs/sa_ccr_portfolio_report.html
```

### 第二遍：看公式

目标：理解 SA-CCR 核心计算。

建议顺序：

```text
enrichment.py
addon.py
exposure.py
docs/SA_CCR_Excel_Reconciliation_Workbook.xlsx
```

你要能手写：

```text
Effective Notional = Adjusted Notional * Delta * Maturity Factor
PFE = multiplier * AddOn Aggregate
EAD = 1.4 * (RC + PFE)
```

### 第三遍：看面试表达

目标：把代码语言转成业务语言。

你要能讲：

```text
为什么需要 trade enrichment？
为什么 AddOn 要按 asset class 聚合？
为什么 RC 和 PFE 都需要？
为什么 margined netting set 要有 EAD cap？
为什么做 Excel reconciliation？
这个 demo 和 production system 的差距是什么？
```

---

## 18. 面试常见问题和回答模板

### Q1: 你这个项目主要做什么？

回答：

> This project implements a Basel-aligned SA-CCR portfolio exposure workflow in Python. It starts from synthetic trade, collateral, and counterparty reference data, enriches trades with SA-CCR fields, aggregates add-ons by asset class and netting set, calculates RC, PFE, EAD, and illustrative RWA, and produces both an HTML report and an Excel reconciliation workbook.

### Q2: 为什么不用 notebook？

回答：

> I wanted this to look like a normal maintainable Python project rather than a one-off notebook. The code is split into modules for configuration, data checks, enrichment, add-on aggregation, exposure calculation, pipeline orchestration, and reporting. This makes the workflow easier to test, review, and extend.

### Q3: SA-CCR 的核心公式是什么？

回答：

```text
EAD = alpha * (RC + PFE)
alpha = 1.4
PFE = multiplier * AddOn Aggregate
```

补充：

> RC captures current exposure based on net MtM and collateral, while PFE captures potential future exposure based on supervisory add-ons and the multiplier.

### Q4: 逐笔交易最关键的计算是什么？

回答：

```text
Effective Notional = Adjusted Notional * Supervisory Delta * Maturity Factor
```

补充：

> Adjusted notional reflects asset-class-specific notional treatment, supervisory delta captures direction and option moneyness, and maturity factor reflects remaining maturity or MPOR treatment.

### Q5: AddOn 怎么算？

回答：

> AddOn aggregation is asset-class specific. Interest rate trades are aggregated by currency and maturity bucket, FX trades by currency pair, credit and equity trades by underlying entity using correlation aggregation, and commodities by commodity group/type using correlation aggregation. The final netting-set AddOn is the sum of asset-class add-ons.

### Q6: Margined 和 unmargined RC 有什么区别？

回答：

```text
Unmargined RC = max(V - C, 0)
Margined RC = max(V - C, TH + MTA - NICA, 0)
```

补充：

> Margined RC reflects CSA terms such as threshold, minimum transfer amount, and independent collateral.

### Q7: PFE multiplier 为什么不是永远等于 1？

回答：

> The multiplier reduces PFE when the netting set is over-collateralized or has negative net market value, but it is floored at 5%. This prevents PFE from being reduced to zero while still recognizing some risk reduction from collateralization.

### Q8: Excel 对账表的作用是什么？

回答：

> The Excel workbook is an independent transparency layer. It recreates the main Python calculations in Excel formulas and reconciles trade-level effective notional, add-on detail, netting-set EAD, and counterparty EAD against the Python outputs. This makes the model easier for reviewers and interviewers to inspect.

### Q9: 这个项目和真实监管系统有什么差距？

回答：

> It is Basel-aligned for the core SA-CCR exposure workflow, but it is not a production regulatory capital engine. It simplifies legal netting enforceability, collateral eligibility and haircuts, product taxonomy, market data sourcing, risk-weight calculation, CVA/CCP capital, and formal model governance.

### Q10: 你为什么用 synthetic data？

回答：

> Public transaction feeds usually do not contain all SA-CCR-required fields, such as legal netting sets, CSA terms, collateral balances, MtM, internal counterparty mapping, and regulatory risk weights. Synthetic data allows the project to be public-safe, reproducible, and broad enough to demonstrate all five SA-CCR asset classes.

---

## 19. 自测清单

你可以用下面的问题检查自己是否真的理解了项目。

基础层：

- 这个项目的三个输入 CSV 分别是什么？
- `pipeline.py` 的调用顺序是什么？
- `outputs/` 里的每个 CSV 大概代表什么？
- HTML 报告和 Excel 对账表分别服务什么目的？

公式层：

- `Effective Notional` 怎么算？
- IR supervisory duration 为什么只对 Interest Rate / Credit 使用？
- option delta 需要哪些字段？
- margined maturity factor 和 unmargined maturity factor 有什么区别？
- IR AddOn 为什么要分 `<1Y`, `1Y-5Y`, `>5Y`？
- FX 为什么按 currency pair 聚合？
- Credit/Equity 为什么要用 correlation aggregation？
- PFE multiplier 的 floor 是多少？
- EAD cap 为什么要重跑 unmargined exposure？

面试层：

- 你如何用 60 秒介绍这个项目？
- 如果面试官问“这是不是完整监管系统”，你怎么回答？
- 如果面试官问“你怎么证明结果对”，你怎么讲 Excel reconciliation？
- 如果面试官问“下一步怎么改进”，你能说出 3 个方向吗？

---

## 20. 下一步可以怎么加深

如果你想继续把这个项目讲得更扎实，可以按下面顺序练习：

1. 从 `sample_trades.csv` 选一笔 Interest Rate Swap，在 Excel `Trade_Calc` 中手动追一遍 effective notional。
2. 从 `Netting_Set_Calc` 选一个 netting set，手算 RC、multiplier、PFE、EAD。
3. 找一个 `EAD Cap Applied = True` 的 netting set，解释为什么 capped。
4. 选一个 top counterparty，从 `Counterparty_Calc` 追到 `Netting_Set_Calc`，再追到 `AddOn_Calc`。
5. 准备一个 3 分钟英文项目介绍。

可以用这个英文结构：

```text
1. Business objective
2. Input data and product coverage
3. SA-CCR calculation workflow
4. Python implementation structure
5. Excel reconciliation and validation
6. Limitations and production gaps
```

---

## 21. 你应该重点记住的 8 句话

1. 这个项目是 Basel-aligned SA-CCR core exposure workflow demo，不是完整生产监管系统。
2. 核心公式是 `EAD = 1.4 * (RC + PFE)`。
3. `PFE = multiplier * AddOn Aggregate`。
4. 逐笔交易最核心字段是 `Effective Notional = Adjusted Notional * Delta * Maturity Factor`。
5. AddOn aggregation 是 asset-class specific 的。
6. RC 是当前暴露，PFE 是潜在未来暴露。
7. Margined netting set 使用 CSA 字段计算 RC，并应用 unmargined EAD cap。
8. Excel reconciliation workbook 用公式复刻 Python 结果，是 reviewer-facing audit layer。
