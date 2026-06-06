# SA-CCR Regulatory Alignment Review

This note reviews the project against the Basel SA-CCR mechanics. The conclusion is:

> The project is Basel-aligned for the core SA-CCR exposure workflow, but it should not be described as a fully production-compliant regulatory capital engine.

It is suitable as an interview portfolio project showing product classification, data enrichment, netting-set aggregation, RC/PFE/EAD/RWA reporting, and awareness of remaining regulatory implementation gaps.

## Primary Regulatory References

- Basel Committee on Banking Supervision, [The standardised approach for measuring counterparty credit risk exposures](https://www.bis.org/publ/bcbs279.pdf)
- BIS Basel Framework, [CRE52 - Standardised approach to counterparty credit risk](https://www.bis.org/basel_framework/chapter/CRE/52.htm)
- China State Council / NFRA, [Commercial Bank Capital Management Measures](https://www.gov.cn/zhengce/202311/content_6913410.htm)

## Alignment Matrix

| Regulatory topic | Project status | What the project implements | Remaining gap |
| --- | --- | --- | --- |
| Scope of SA-CCR | Partially aligned | Applies the workflow to derivative trades across interest rate, FX, credit, equity, and commodity asset classes. | Does not cover securities financing transactions, long-settlement treatment, or jurisdiction-specific scope filters. |
| Netting-set level EAD | Aligned for demo | Calculates EAD separately by `Counterparty ID` and `Netting Set ID`. | Legal enforceability of netting agreements is represented as data, not validated through legal opinions or jurisdiction checks. |
| EAD formula | Aligned | Uses `EAD = alpha * (RC + PFE)` with `alpha = 1.4`. | None for the core formula. |
| Unmargined replacement cost | Aligned for demo | Uses `RC = max(V - C, 0)`. | Collateral haircuts and exact eligible collateral treatment are simplified. |
| Margined replacement cost | Mostly aligned | Uses `RC = max(V - C, TH + MTA - NICA, 0)`. | NICA, independent amount, posted/received collateral, one-way margining, and collateral haircut treatment are simplified. |
| Margined EAD cap | Implemented | Calculates the same netting set on an unmargined basis and caps margined EAD when applicable. | Multiple margin agreements covering multiple netting sets are not fully modeled. |
| PFE multiplier | Aligned | Uses multiplier formula with a 5% floor. | Collateral treatment feeding the multiplier is simplified through netting-set collateral fields. |
| Maturity factor | Mostly aligned | Supports unmargined maturity factor and margined MPOR treatment with CCP/non-CCP floors. | Does not fully implement all MPOR escalators such as dispute history, illiquid collateral, very large netting sets, or operational margin call exceptions. |
| Supervisory duration | Aligned for demo | Applies supervisory duration for interest rate and credit trades. | Day-count and start/end date treatment are simplified to project-level date conventions. |
| Supervisory factors and correlations | Mostly aligned | Implements Basel-style supervisory factors, credit ratings, equity/credit correlations, commodity correlations, and option volatilities. | Rating mapping and product subclass mapping are simplified; jurisdiction-specific parameter overrides are not modeled. |
| Basis and volatility transactions | Partially aligned | Supports separate basis/volatility hedging-set labels and factor adjustments of 0.5x and 5x. | Detection depends on input labels; full risk-factor-pair basis identification is not implemented. |
| Supervisory delta | Mostly aligned | Implements linear trade delta and option delta using strike, underlying price, exercise date, and supervisory volatility. | Does not cover every edge case, such as negative-rate shifted option treatment, complex exotic payoff mapping, or supervisory delta for every structured product. |
| Adjusted notional | Partially aligned | Uses supervisory duration for interest rate/credit, converted notional for FX, and base notional for equity/commodity. | Equity and commodity adjusted notional should ideally be calculated from price and units when available; current treatment uses base notional as a proxy. |
| Asset-class add-on aggregation | Mostly aligned | Implements IR maturity-bucket aggregation, FX currency-pair aggregation, credit/equity entity correlation, and commodity group/type aggregation. | Hybrid/multi-risk trades, detailed commodity basis definitions, and complete product taxonomy are simplified. |
| RWA calculation | Illustrative only | Applies counterparty risk weights from a reference table to produce illustrative RWA. | Production RWA requires a full credit risk capital engine, counterparty class, eligible CRM, ratings/PD/LGD treatment, and jurisdiction-specific reporting rules. |
| CVA and CCP capital | Not in scope | The project focuses on counterparty default EAD/RWA workflow. | CVA capital, central counterparty default fund exposures, and CCP-specific rules require separate modules. |
| Governance and validation | Portfolio-level demo | Provides reproducible scripts, tests, output CSVs, and report generation. | Production compliance requires model validation, reconciliation, audit controls, change control, source-system lineage, and regulatory sign-off. |

## Product Coverage In The Default Dataset

The public-safe industry-style dataset covers 298 trades across 19 product types:

- FX: FX Forward, FX Swap, FX Option
- Interest Rate: Interest Rate Swap, Cross Currency Swap, FRA, OIS, Swaption, Cap/Floor
- Commodity: Precious Metal Forward, Precious Metal Swap, Commodity Option, Oil Forward, Electricity Swap
- Credit: Credit TRS, Credit Single Name CDS, Credit Index CDS
- Equity: Equity TRS, Equity Index Option

This gives broad interview coverage while avoiding publication of client/project rows from local Excel files or confidential bank materials.

## Recommended Wording For Resume Or Interview

Use:

> Built a Basel-aligned Python SA-CCR exposure engine covering trade enrichment, adjusted notional, supervisory delta, maturity factor, asset-class add-on aggregation, RC/PFE/EAD, margined EAD cap, and report generation across interest rate, FX, credit, equity, and commodity derivatives.

Avoid:

> Fully regulatory-compliant SA-CCR production engine.

The second statement would overclaim because the project does not include legal netting enforceability, production collateral haircut rules, full CSA operations, CVA/CCP capital, jurisdiction-specific reporting templates, or formal model validation.
