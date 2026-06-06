# SA-CCR Methodology Notes

This project implements a simplified SA-CCR workflow for interview and learning purposes.

The curated trade portfolio is built from public DTCC CFTC Public Price Dissemination swap transaction records. Those records provide actual reported trade economics, but they do not disclose a bank-specific counterparty book, netting set, collateral agreement, risk weight, trade direction, or mark-to-market. This project therefore separates fields into two categories:

- public SDR fields: product, asset class, notional, currency, effective date, maturity date, underlier, cleared indicator
- synthetic SA-CCR enrichment fields: counterparty, netting set, collateral, risk weight, direction, MtM

## Core Formula

```text
EAD = alpha * (RC + PFE)
alpha = 1.4
PFE = multiplier * AddOn_aggregate
RC = max(V - C, 0)
```

Where:

- `V` is the net market value of trades in a netting set.
- `C` is net collateral held at the netting-set level.
- `AddOn_aggregate` is the sum of asset-class add-ons.
- `multiplier` reflects over-collateralisation or negative mark-to-market and has a 5% floor.

## Trade-Level Enrichment

Each trade is enriched with:

- remaining maturity
- maturity bucket
- hedging set
- supervisory factor
- supervisory correlation
- supervisory duration
- adjusted notional
- supervisory delta
- maturity factor
- effective notional

## Asset Class Treatment

Interest rate:

- hedging set is based on currency
- effective notionals are aggregated by maturity bucket
- maturity bucket aggregation applies partial offset between buckets

FX:

- hedging set is based on currency pair
- long/short positions offset within the same currency pair

Credit and equity:

- positions referencing the same entity offset first
- entity-level add-ons are aggregated with a simplified correlation formula

Commodity:

- positions are grouped by commodity hedging set and commodity type
- type-level add-ons are aggregated with a simplified correlation formula

## Limitations

This project is designed for transparent learning and discussion. It does not replace jurisdiction-specific regulatory implementation requirements, production data governance, market data conversion, full margin agreement treatment, or formal model validation.
