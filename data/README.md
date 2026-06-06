# Data Sources

## Curated SA-CCR Sample

`sample_trades.csv` is a curated SA-CCR-ready trade file built from public DTCC CFTC Public Price Dissemination (PPD) swap transaction records for 2025-02-14.

The raw public data contains actual reported swap transaction economics, including:

- asset class
- product identifiers
- effective date
- expiration date
- notional amounts and currencies
- fixed/floating rate fields
- underlier fields
- cleared indicator
- option fields where available

Source:

- DTCC Public Price Dissemination Dashboard: https://pddata.dtcc.com/ppd/cftcdashboard
- DTCC PPD user guide: https://kgc0418-tdw-data-0.s3.amazonaws.com/gtr/static/gtr/docs/RT_PPD_quick_ref_guide.pdf

## Fields Added for SA-CCR Demonstration

Public SDR data does not disclose a bank's internal counterparty, legal netting set, collateral agreement, risk weight, trade direction, or mark-to-market. Those fields are therefore added using deterministic synthetic enrichment so the data can support a complete SA-CCR workflow.

Synthetic fields:

- `Counterparty ID`
- `Netting Set ID`
- `Buy/Sell Indicator`
- `MtM`
- `Margined/ Unmargined`
- `Margin Frequency (Business Days)`
- `counterparty_reference.csv`
- `collateral.csv`

The public trade identifiers and product economics are retained through source columns such as `Source Dissemination Identifier`, `Source UPI FISN`, and `Source Product Name`.

## Raw Files

Raw SDR ZIP files are not committed because they can be large. Recreate them with:

```bash
python scripts/download_dtcc_sdr.py --date 2025-02-14
python scripts/build_saccr_sample_from_sdr.py
```

