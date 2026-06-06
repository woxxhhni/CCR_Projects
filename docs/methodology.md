# SA-CCR Methodology Notes

This project implements a Basel-aligned SA-CCR workflow for interview and learning purposes.

The curated trade portfolio is built from public DTCC CFTC Public Price Dissemination swap transaction records. Those records provide actual reported trade economics, but they do not disclose a bank-specific counterparty book, netting set, collateral agreement, risk weight, trade direction, or mark-to-market. This project therefore separates fields into two categories:

- public SDR fields: product, asset class, notional, currency, effective date, maturity date, underlier, cleared indicator
- synthetic SA-CCR enrichment fields: counterparty, netting set, margin agreement, collateral, risk weight, direction, MtM

## Core Formula

```text
EAD = alpha * (RC + PFE)
alpha = 1.4
PFE = multiplier * AddOn_aggregate

Unmargined RC = max(V - C, 0)
Margined RC = max(V - C, TH + MTA - NICA, 0)
```

Where:

- `V` is the net market value of trades in a netting set.
- `C` is net collateral held at the netting-set level.
- `TH` is the positive threshold before collateral must be exchanged.
- `MTA` is the minimum transfer amount under the margin agreement.
- `NICA` is net independent collateral amount.
- `AddOn_aggregate` is the sum of asset-class add-ons.
- `multiplier` reflects over-collateralisation or negative mark-to-market and has a 5% floor.

For margined netting sets, the final EAD is capped at the EAD of the same netting set calculated on an unmargined basis. The cap calculation reruns the portfolio using unmargined maturity factors and unmargined RC treatment.

## Trade-Level Enrichment

Each trade is enriched with:

- remaining maturity
- maturity bucket
- hedging set
- supervisory factor base
- supervisory factor adjustment for basis and volatility transactions
- supervisory correlation
- supervisory duration
- adjusted notional
- supervisory option volatility
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
- entity-level add-ons are aggregated with a correlation formula
- index and single-name trades use different supervisory correlations and option volatilities

Commodity:

- positions are grouped by commodity hedging set and commodity type
- type-level add-ons are aggregated with a correlation formula
- electricity uses a separate supervisory factor and option volatility bucket

Basis and volatility transactions:

- basis transactions are placed in separate hedging sets and use 50% of the relevant supervisory factor
- volatility transactions are placed in separate hedging sets and use 500% of the relevant supervisory factor
- ordinary vanilla options are not treated as volatility transactions; they affect supervisory delta through put/call, strike, underlying price, exercise date, and supervisory option volatility

## Limitations

This project is designed for transparent learning and discussion. It does not replace jurisdiction-specific regulatory implementation requirements, production data governance, legal enforceability checks, collateral eligibility and haircut engines, complete CSA/VM/IM operations, or formal model validation.
