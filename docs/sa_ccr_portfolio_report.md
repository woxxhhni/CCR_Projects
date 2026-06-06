# SA-CCR Industry-Style Portfolio Capital Report

Generated on: 2026-06-06

## 1. Executive Summary

This report summarizes a Python-based SA-CCR portfolio capital engine built for counterparty credit risk analysis. The portfolio is a public-safe anonymized sample generated in this GitHub project from bank SA-CCR implementation field conventions and Basel-style product coverage. It preserves realistic product scope, margin fields, netting-set structure, and notional ranges, but does not copy client/project trade rows or original counterparty names.

| Metric                    | Value          |
| ------------------------- | -------------- |
| Trade count               | 298            |
| Counterparties            | 12             |
| Netting sets              | 95             |
| Base notional             | $54.96bn       |
| Margined trades           | 204            |
| Unmargined trades         | 94             |
| Total EAD                 | $656.70mm      |
| Total RWA                 | $381.78mm      |
| Margined EAD caps applied | 0 netting sets |
| EAD reduction from cap    | $0.00          |
| Data quality issues       | 0              |

## 2. Product Coverage

| Asset Class   | Product                | Trades | Base Notional | Margined | Unmargined |
| ------------- | ---------------------- | ------ | ------------- | -------- | ---------- |
| Commodity     | Commodity Option       | 12     | $368.10mm     | 8        | 4          |
| Commodity     | Electricity Swap       | 6      | $140.90mm     | 5        | 1          |
| Commodity     | Oil Forward            | 10     | $141.50mm     | 8        | 2          |
| Commodity     | Precious Metal Forward | 14     | $594.20mm     | 10       | 4          |
| Commodity     | Precious Metal Swap    | 10     | $369.60mm     | 7        | 3          |
| Credit        | Credit Index CDS       | 12     | $1.44bn       | 8        | 4          |
| Credit        | Credit Single Name CDS | 10     | $462.10mm     | 5        | 5          |
| Credit        | Credit TRS             | 12     | $751.40mm     | 6        | 6          |
| Equity        | Equity Index Option    | 10     | $429.20mm     | 6        | 4          |
| Equity        | Equity TRS             | 14     | $426.00mm     | 10       | 4          |
| FX            | FX Forward             | 32     | $1.78bn       | 20       | 12         |
| FX            | FX Option              | 28     | $1.69bn       | 15       | 13         |
| FX            | FX Swap                | 24     | $1.96bn       | 18       | 6          |
| Interest Rate | Cap/Floor              | 14     | $3.30bn       | 9        | 5          |
| Interest Rate | Cross Currency Swap    | 16     | $4.61bn       | 11       | 5          |
| Interest Rate | Interest Rate FRA      | 16     | $2.41bn       | 11       | 5          |
| Interest Rate | Interest Rate Swap     | 34     | $25.75bn      | 25       | 9          |
| Interest Rate | OIS                    | 14     | $6.58bn       | 13       | 1          |
| Interest Rate | Swaption               | 10     | $1.78bn       | 9        | 1          |

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
| AddOn Aggregate         | $568.04mm |
| PFE                     | $354.86mm |
| RC                      | $114.21mm |
| EAD                     | $656.70mm |
| RWA                     | $381.78mm |
| EAD before margined cap | $656.70mm |
| EAD reduction from cap  | $0.00     |

### Add-On by Asset Class

| Asset Class   | AddOn Exposure | Share of AddOn |
| ------------- | -------------- | -------------- |
| Interest Rate | $278.14mm      | 49.0%          |
| Commodity     | $122.60mm      | 21.6%          |
| Equity        | $76.21mm       | 13.4%          |
| FX            | $67.47mm       | 11.9%          |
| Credit        | $23.62mm       | 4.2%           |

### Counterparty Summary

| Counterparty            | Type            | Rating | AddOn    | PFE      | RC       | EAD      | RWA      |
| ----------------------- | --------------- | ------ | -------- | -------- | -------- | -------- | -------- |
| IND_CORPORATE_002       | Corporate       | BB     | $48.30mm | $17.45mm | $31.83mm | $69.00mm | $69.00mm |
| IND_HEDGE_FUND_001      | Fund            | BB     | $59.20mm | $40.32mm | $2.10mm  | $59.38mm | $59.38mm |
| IND_INSURER_001         | Insurance       | A      | $73.48mm | $54.30mm | $10.57mm | $90.83mm | $45.42mm |
| IND_BANK_002            | Bank            | BBB    | $49.62mm | $24.54mm | $32.34mm | $79.63mm | $39.81mm |
| IND_CLEARING_MEMBER_001 | Clearing Member | A      | $60.40mm | $41.18mm | $3.37mm  | $62.36mm | $31.18mm |
| IND_PENSION_001         | Pension         | A      | $50.32mm | $34.46mm | $6.58mm  | $57.45mm | $28.72mm |
| IND_REGIONAL_BANK_001   | Bank            | BBB    | $45.06mm | $31.90mm | $5.12mm  | $51.82mm | $25.91mm |
| IND_CORPORATE_001       | Corporate       | BBB    | $20.20mm | $14.41mm | $1.50mm  | $22.28mm | $22.28mm |
| IND_ASSET_MANAGER_001   | Asset Manager   | A      | $38.90mm | $27.00mm | $1.57mm  | $40.00mm | $20.00mm |
| IND_SOVEREIGN_001       | Sovereign       | AA     | $60.41mm | $34.11mm | $18.03mm | $72.99mm | $14.60mm |
| IND_BANK_001            | Bank            | A      | $39.00mm | $19.45mm | $950.25k | $28.57mm | $14.28mm |
| IND_BROKER_001          | Broker Dealer   | BBB    | $23.14mm | $15.74mm | $259.80k | $22.40mm | $11.20mm |

### Largest Netting Sets by EAD

| Counterparty            | Netting Set | Margin | AddOn    | PFE      | RC       | EAD      | RWA      | Cap Applied |
| ----------------------- | ----------- | ------ | -------- | -------- | -------- | -------- | -------- | ----------- |
| IND_HEDGE_FUND_001      | 3012        | U      | $36.24mm | $36.24mm | $512.74k | $51.45mm | $51.45mm | No          |
| IND_INSURER_001         | 3048        | U      | $31.78mm | $31.78mm | $4.81mm  | $51.23mm | $25.62mm | No          |
| IND_BANK_002            | 3049        | M      | $19.32mm | $5.37mm  | $28.29mm | $47.12mm | $23.56mm | No          |
| IND_CORPORATE_002       | 3074        | M      | $26.54mm | $1.33mm  | $24.92mm | $36.76mm | $36.76mm | No          |
| IND_ASSET_MANAGER_001   | 3205        | U      | $23.96mm | $22.58mm | $0.00    | $31.62mm | $15.81mm | No          |
| IND_PENSION_001         | 3060        | U      | $19.76mm | $19.31mm | $0.00    | $27.04mm | $13.52mm | No          |
| IND_CLEARING_MEMBER_001 | 3161        | U      | $15.31mm | $15.31mm | $490.02k | $22.11mm | $11.06mm | No          |
| IND_REGIONAL_BANK_001   | 3054        | U      | $15.28mm | $15.28mm | $462.79k | $22.04mm | $11.02mm | No          |
| IND_INSURER_001         | 3390        | U      | $10.49mm | $10.49mm | $3.24mm  | $19.21mm | $9.61mm  | No          |
| IND_SOVEREIGN_001       | 3065        | U      | $11.29mm | $11.29mm | $1.52mm  | $17.94mm | $3.59mm  | No          |

## 5. References

- Basel Committee on Banking Supervision, [The standardised approach for measuring counterparty credit risk exposures](https://www.bis.org/publ/bcbs279.pdf).
- BIS Basel Framework, [CRE52 - Standardised approach to counterparty credit risk](https://www.bis.org/basel_framework/chapter/CRE/52.htm).

## 6. Reproducibility

```bash
python scripts/build_industry_style_sample.py
python scripts/run_saccr.py
python scripts/generate_report.py
pytest
```
