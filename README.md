# CCR Projects

Python projects for counterparty credit risk (CCR), exposure aggregation, and SA-CCR regulatory capital workflows.

This repository is being built as an interview-ready portfolio for risk analyst roles. The first project is a Basel-aligned SA-CCR portfolio capital engine implemented as a normal Python project rather than a notebook.

## Project 1: SA-CCR Portfolio Capital Engine

Location: `src/saccr_engine`

The project reads derivative trade data, enriches each trade with SA-CCR calculation fields, aggregates add-ons by asset class and netting set, and produces counterparty-level EAD/RWA reports.

The sample portfolio contains 320 curated trades built from DTCC CFTC Public Price Dissemination swap transaction records for 2025-02-14. The public SDR records provide real transaction economics such as asset class, product identifiers, effective date, maturity date, notional amount, currency, underlier information, and cleared indicator. Internal bank fields that are not publicly disseminated, such as counterparty, netting set, collateral, risk weight, trade direction, and MtM, are added with deterministic synthetic enrichment for SA-CCR demonstration.

Core workflow:

```text
Trade data
-> data quality checks
-> trade enrichment
-> adjusted notional
-> supervisory delta
-> maturity factor
-> effective notional
-> asset-class add-on aggregation
-> PFE multiplier
-> RC / PFE / EAD / illustrative RWA
-> risk reports
```

## Why This Project Is Useful

This project is designed to match common risk analyst responsibilities:

- counterparty credit risk exposure aggregation
- SA-CCR workflow understanding
- regulatory capital reporting
- trade data cleaning and validation
- portfolio summaries by counterparty, netting set, and asset class
- Python-based risk data processing

## Methodology

The engine follows the core SA-CCR structure:

```text
EAD = alpha * (RC + PFE)
alpha = 1.4
PFE = multiplier * AddOn_aggregate

Unmargined RC = max(V - C, 0)
Margined RC = max(V - C, TH + MTA - NICA, 0)
```

The engine implements:

- supervisory duration for interest rate and credit trades
- unmargined and margined maturity factors
- option-aware supervisory delta using Basel-style supervisory option volatility
- supervisory factors by asset class, rating, and product type
- basis and volatility transaction supervisory-factor adjustments
- IR maturity-bucket aggregation
- FX currency-pair aggregation
- credit, equity, and commodity correlation-style add-on aggregation
- collateral-aware PFE multiplier with 5% floor
- EAD cap for margined netting sets based on the same portfolio calculated on an unmargined basis
- counterparty-level risk weight mapping for illustrative RWA

Primary reference: Basel Committee on Banking Supervision, [The standardised approach for measuring counterparty credit risk exposures](https://www.bis.org/publ/bcbs279.pdf).

## Repository Structure

```text
CCR_Projects/
|-- data/
|   |-- sample_trades.csv
|   |-- collateral.csv
|   |-- README.md
|   `-- counterparty_reference.csv
|-- docs/
|   `-- methodology.md
|-- scripts/
|   |-- build_saccr_sample_from_sdr.py
|   |-- download_dtcc_sdr.py
|   `-- run_saccr.py
|-- src/
|   `-- saccr_engine/
|       |-- addon.py
|       |-- config.py
|       |-- data_checks.py
|       |-- enrichment.py
|       |-- exposure.py
|       |-- pipeline.py
|       `-- reporting.py
|-- tests/
|   `-- test_core_calculations.py
|-- requirements.txt
`-- README.md
```

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the SA-CCR engine:

```bash
python scripts/run_saccr.py
```

Generate the interview-ready portfolio report:

```bash
python scripts/generate_report.py
```

Rebuild the curated sample from DTCC SDR raw files:

```bash
python scripts/download_dtcc_sdr.py --date 2025-02-14
python scripts/build_saccr_sample_from_sdr.py
```

Run tests:

```bash
pytest
```

## Output Files

The run script writes CSV reports to `outputs/`:

- `data_quality_issues.csv`
- `trade_level_enriched.csv`
- `addon_detail.csv`
- `asset_class_addon.csv`
- `netting_set_exposure.csv`
- `unmargined_cap_exposure.csv`
- `counterparty_summary.csv`
- `asset_class_summary.csv`

The report generator writes the final delivery reports to:

- `docs/sa_ccr_portfolio_report.html`
- `docs/sa_ccr_portfolio_report.md`

## Current Assumptions and Limitations

This is an educational and interview portfolio implementation, not a production regulatory capital engine.

Key simplifications:

- the public SDR trade economics are real, but internal counterparty, netting set, collateral, risk weight, trade direction, and MtM fields are synthetically added
- market data conversion is simplified; non-USD notionals are converted with a static FX table for project reproducibility
- equity and commodity adjusted notionals use base notional as a proxy when price/unit data is unavailable
- option delta uses available strike, underlying price, exercise date, and Basel supervisory option volatility buckets
- risk weights are illustrative and supplied through `data/counterparty_reference.csv`
- collateral and margin agreement fields are deterministic synthetic data because public SDR feeds do not disclose bank CSA terms
- legal enforceability, collateral eligibility/haircuts, exact NICA treatment, settlement timing, multi-risk hybrid allocation, and jurisdiction-specific reporting templates are outside the current scope

## Resume-Ready Description

Built a Python-based Basel-aligned SA-CCR portfolio capital calculation engine to aggregate derivative exposures by counterparty, netting set, asset class, and hedging set.

Implemented trade enrichment, supervisory factors, adjusted notional, maturity factors, add-on aggregation, PFE multiplier, margined/unmargined replacement cost, EAD cap logic, and illustrative RWA reporting.

Developed reproducible risk reports to summarize capital drivers by counterparty and asset class using pandas and NumPy.
