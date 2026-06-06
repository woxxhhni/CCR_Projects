"""Data quality checks for trade input files."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = [
    "COB Date",
    "Counterparty ID",
    "Netting Set ID",
    "Ticket Number",
    "Trade Type",
    "Asset Class",
    "Maturity Date",
    "Base Notional",
    "Buy/Sell Indicator",
    "MtM",
]

KNOWN_ASSET_CLASSES = {"Interest Rate", "FX", "Credit", "Equity", "Commodity"}


def validate_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Return a data quality issue table and raise for missing required columns."""
    missing = [column for column in REQUIRED_COLUMNS if column not in trades.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    issues: list[dict[str, object]] = []

    for column in REQUIRED_COLUMNS:
        null_count = int(trades[column].isna().sum())
        if null_count:
            issues.append(
                {
                    "severity": "warning",
                    "check": "missing_values",
                    "column": column,
                    "count": null_count,
                    "message": f"{column} has missing values",
                }
            )

    unknown_assets = sorted(set(trades["Asset Class"].dropna()) - KNOWN_ASSET_CLASSES)
    if unknown_assets:
        issues.append(
            {
                "severity": "error",
                "check": "unknown_asset_class",
                "column": "Asset Class",
                "count": len(unknown_assets),
                "message": ", ".join(unknown_assets),
            }
        )

    maturity = pd.to_datetime(trades["Maturity Date"], errors="coerce")
    cob = pd.to_datetime(trades["COB Date"], errors="coerce")
    expired = int((maturity <= cob).fillna(False).sum())
    if expired:
        issues.append(
            {
                "severity": "warning",
                "check": "expired_maturity",
                "column": "Maturity Date",
                "count": expired,
                "message": "Trades have maturity dates on or before COB date",
            }
        )

    return pd.DataFrame(
        issues,
        columns=["severity", "check", "column", "count", "message"],
    )

