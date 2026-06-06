# SA-CCR Portfolio Capital Report

Generated on: 2026-06-06

## 1. Executive Summary

This report summarizes a Python-based SA-CCR portfolio capital engine built for counterparty credit risk analysis. The portfolio uses public DTCC CFTC swap dissemination records for trade economics and deterministic synthetic fields for internal bank data that public SDR files do not disclose.

| Metric                    | Value          |
| ------------------------- | -------------- |
| Trade count               | 320            |
| Counterparties            | 8              |
| Netting sets              | 63             |
| Base notional             | $15.68bn       |
| Margined trades           | 251            |
| Unmargined trades         | 69             |
| Total EAD                 | $87.38mm       |
| Total RWA                 | $53.15mm       |
| Margined EAD caps applied | 6 netting sets |
| EAD reduction from cap    | $29.97mm       |
| Data quality issues       | 0              |

## 2. Product Coverage

| Asset Class   | Product                   | Trades | Base Notional | Margined | Unmargined |
| ------------- | ------------------------- | ------ | ------------- | -------- | ---------- |
| Commodity     | Commodity Agricultural    | 14     | $10.53mm      | 9        | 5          |
| Commodity     | Commodity Energy          | 14     | $8.52mm       | 12       | 2          |
| Commodity     | Commodity Metals          | 14     | $55.02mm      | 11       | 3          |
| Commodity     | Commodity Option          | 14     | $97.90mm      | 6        | 8          |
| Commodity     | Commodity Other           | 14     | $138.87mm     | 10       | 4          |
| Credit        | Credit Index CDS          | 41     | $1.46bn       | 39       | 2          |
| Credit        | Credit Other              | 5      | $580.50mm     | 5        | 0          |
| Credit        | Credit Single Name CDS    | 4      | $316.47mm     | 4        | 0          |
| Equity        | Equity Single Stock TRS   | 50     | $4.79mm       | 31       | 19         |
| FX            | FX Forward/NDF            | 24     | $41.75mm      | 16       | 8          |
| FX            | FX Option                 | 24     | $938.65mm     | 18       | 6          |
| FX            | FX Swap                   | 22     | $225.42mm     | 13       | 9          |
| Interest Rate | Interest Rate FRA         | 27     | $6.35bn       | 26       | 1          |
| Interest Rate | Interest Rate Fixed-Float | 27     | $2.21bn       | 26       | 1          |
| Interest Rate | Interest Rate OIS         | 26     | $3.24bn       | 25       | 1          |

## 3. Calculation Methodology

```text
EAD = alpha * (RC + PFE)
alpha = 1.4
PFE = multiplier * AddOn_aggregate

Unmargined RC = max(V - C, 0)
Margined RC = max(V - C, TH + MTA - NICA, 0)
```

The engine enriches trades with hedging sets, supervisory factors, supervisory duration, option delta, maturity factor, effective notional, add-on aggregation, PFE multiplier, RC, EAD, RWA, and margined EAD cap logic.

## 4. Final Results

| Measure                 | Amount    |
| ----------------------- | --------- |
| AddOn Aggregate         | $62.79mm  |
| PFE                     | $27.14mm  |
| RC                      | $56.68mm  |
| EAD                     | $87.38mm  |
| RWA                     | $53.15mm  |
| EAD before margined cap | $117.35mm |
| EAD reduction from cap  | $29.97mm  |

### Add-On by Asset Class

| Asset Class   | AddOn Exposure | Share of AddOn |
| ------------- | -------------- | -------------- |
| Commodity     | $19.56mm       | 31.1%          |
| Interest Rate | $19.02mm       | 30.3%          |
| FX            | $16.68mm       | 26.6%          |
| Credit        | $6.60mm        | 10.5%          |
| Equity        | $932.78k       | 1.5%           |

### Counterparty Summary

| Counterparty       | Type                  | Rating | AddOn    | PFE      | RC       | EAD      | RWA      |
| ------------------ | --------------------- | ------ | -------- | -------- | -------- | -------- | -------- |
| CP_CORPORATE_A     | Corporate             | BBB    | $7.49mm  | $1.71mm  | $20.03mm | $23.78mm | $23.78mm |
| CP_HEDGE_FUND_A    | Fund                  | BB     | $8.68mm  | $5.37mm  | $5.38k   | $7.53mm  | $7.53mm  |
| CP_PENSION_A       | Pension               | A      | $15.19mm | $8.45mm  | $785.86k | $12.93mm | $6.46mm  |
| CP_SOVEREIGN_A     | Sovereign             | AA     | $4.79mm  | $325.68k | $26.75mm | $20.65mm | $4.13mm  |
| CP_BANK_B          | Bank                  | BBB    | $6.03mm  | $3.64mm  | $1.08mm  | $6.61mm  | $3.30mm  |
| CP_ASSET_MANAGER_A | Financial Institution | BBB    | $6.81mm  | $3.48mm  | $1.17mm  | $6.51mm  | $3.26mm  |
| CP_INSURER_A       | Insurance             | A      | $4.88mm  | $2.38mm  | $3.57mm  | $5.22mm  | $2.61mm  |
| CP_BANK_A          | Bank                  | A      | $8.92mm  | $1.78mm  | $3.29mm  | $4.15mm  | $2.08mm  |

### Largest Netting Sets by EAD

| Counterparty       | Netting Set | Margin | AddOn   | PFE      | RC       | EAD      | RWA      | Cap Applied |
| ------------------ | ----------- | ------ | ------- | -------- | -------- | -------- | -------- | ----------- |
| CP_CORPORATE_A     | 1069        | M      | $2.99mm | $149.58k | $20.03mm | $22.79mm | $22.79mm | Yes         |
| CP_SOVEREIGN_A     | 1037        | M      | $3.41mm | $170.38k | $26.71mm | $20.38mm | $4.08mm  | Yes         |
| CP_PENSION_A       | 1029        | U      | $6.15mm | $5.99mm  | $0.00    | $8.39mm  | $4.19mm  | No          |
| CP_HEDGE_FUND_A    | 1028        | U      | $3.99mm | $3.86mm  | $0.00    | $5.41mm  | $5.41mm  | No          |
| CP_ASSET_MANAGER_A | 1021        | U      | $2.85mm | $2.85mm  | $778.71k | $5.07mm  | $2.54mm  | No          |
| CP_BANK_B          | 1015        | U      | $2.51mm | $2.51mm  | $99.84k  | $3.66mm  | $1.83mm  | No          |
| CP_PENSION_A       | 1096        | M      | $2.63mm | $1.02mm  | $291.72k | $1.83mm  | $915.21k | No          |
| CP_INSURER_A       | 1087        | M      | $1.98mm | $1.02mm  | $43.55k  | $1.49mm  | $746.89k | No          |
| CP_INSURER_A       | 1092        | U      | $1.02mm | $1.02mm  | $28.91k  | $1.47mm  | $737.02k | No          |
| CP_BANK_A          | 1079        | M      | $2.40mm | $346.67k | $698.77k | $1.46mm  | $731.81k | No          |

## 5. References

- Basel Committee on Banking Supervision, [The standardised approach for measuring counterparty credit risk exposures](https://www.bis.org/publ/bcbs279.pdf).
- BIS Basel Framework, [CRE52 - Standardised approach to counterparty credit risk](https://www.bis.org/basel_framework/chapter/CRE/52.htm).
- DTCC, [Public Price Dissemination Dashboard](https://pddata.dtcc.com/ppd/info-center).
