"""Trade-level enrichment for SA-CCR style calculations."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from saccr_engine.config import (
    BUSINESS_DAYS_PER_YEAR,
    COMMODITY_FACTOR_KEYS,
    COMMODITY_GROUPS,
    CORRELATIONS,
    CREDIT_SUPERVISORY_FACTORS,
    MATURITY_BUCKETS,
    OPTION_SUPERVISORY_VOLATILITY,
    SUPERVISORY_DURATION_RATE,
    SUPERVISORY_FACTORS,
)


def enrich_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Add calculation fields needed by the SA-CCR engine."""
    df = trades.copy()
    date_columns = ["COB Date", "Maturity Date", "Start Date", "End Date", "Contractual Exercise Date"]
    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    df["Maturity Days"] = (df["Maturity Date"] - df["COB Date"]).dt.days
    df = df[df["Maturity Days"] > 0].copy()
    df["Remaining Maturity Years"] = df["Maturity Days"] / 365.0
    df["Maturity Bucket"] = np.select(
        [
            df["Remaining Maturity Years"] < 1,
            df["Remaining Maturity Years"].between(1, 5, inclusive="both"),
            df["Remaining Maturity Years"] > 5,
        ],
        MATURITY_BUCKETS,
        default=">5Y",
    )

    df["Commodity Group"] = df.apply(assign_commodity_group, axis=1)
    df["Commodity Type"] = df["Sub Class"].fillna("Unknown")
    df["Hedging Set"] = df.apply(assign_hedging_set, axis=1)
    df["Supervisory Factor"] = df.apply(assign_supervisory_factor, axis=1)
    df["Correlation"] = df.apply(assign_correlation, axis=1)
    df["Supervisory Duration"] = df.apply(supervisory_duration, axis=1)
    df["Adjusted Notional"] = df.apply(adjusted_notional, axis=1)
    df["Delta"] = df.apply(supervisory_delta, axis=1)
    df["Maturity Factor"] = df.apply(maturity_factor, axis=1)
    df["Effective Notional"] = (
        df["Adjusted Notional"] * df["Delta"] * df["Maturity Factor"]
    )
    return df


def as_number(value: Any, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clean_text(value: Any, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def assign_commodity_group(row: pd.Series) -> str:
    if row["Asset Class"] != "Commodity":
        return ""
    subclass = clean_text(row.get("Sub Class"), "Other")
    return COMMODITY_GROUPS.get(subclass, "Other")


def assign_hedging_set(row: pd.Series) -> str:
    asset_class = row["Asset Class"]
    suffix = ""
    indicator = clean_text(row.get("Basis/Volatility Indicator"))
    if indicator in {"Basis", "Volatility"}:
        suffix = f"_{indicator}"

    if asset_class == "Interest Rate":
        return f"{clean_text(row.get('Base Currency'), 'UNKNOWN')}{suffix}"
    if asset_class == "FX":
        currencies = [
            clean_text(row.get("Trade Leg 1 Currency")),
            clean_text(row.get("Trade Leg 2 Currency")),
        ]
        currencies = sorted(currency for currency in currencies if currency)
        pair = "/".join(currencies) if len(currencies) == 2 else "UNKNOWN"
        return f"{pair}{suffix}"
    if asset_class in {"Credit", "Equity"}:
        entity = clean_text(row.get("Underlying Entity Name"), "UNKNOWN")
        return f"{entity}{suffix}"
    if asset_class == "Commodity":
        return f"{assign_commodity_group(row)}{suffix}"
    return "UNKNOWN"


def assign_supervisory_factor(row: pd.Series) -> float:
    asset_class = row["Asset Class"]
    if asset_class == "Interest Rate":
        return SUPERVISORY_FACTORS["Interest Rate"]
    if asset_class == "FX":
        return SUPERVISORY_FACTORS["FX"]
    if asset_class == "Credit":
        rating = clean_text(row.get("Underlying Entity Rating"), "BBB").upper()
        return CREDIT_SUPERVISORY_FACTORS.get(rating, CREDIT_SUPERVISORY_FACTORS["BBB"])
    if asset_class == "Equity":
        entity_type = clean_text(row.get("Underlying Entity Type")).lower()
        key = "Equity Index" if entity_type == "index" else "Equity Single Name"
        return SUPERVISORY_FACTORS[key]
    if asset_class == "Commodity":
        subclass = clean_text(row.get("Sub Class"), "Other")
        factor_key = COMMODITY_FACTOR_KEYS.get(subclass, "Commodity Other")
        return SUPERVISORY_FACTORS[factor_key]
    return 0.0


def assign_correlation(row: pd.Series) -> float:
    asset_class = row["Asset Class"]
    entity_type = clean_text(row.get("Underlying Entity Type")).lower()
    if asset_class == "Credit":
        return CORRELATIONS["Credit Index"] if entity_type == "index" else CORRELATIONS["Credit Single Name"]
    if asset_class == "Equity":
        return CORRELATIONS["Equity Index"] if entity_type == "index" else CORRELATIONS["Equity Single Name"]
    if asset_class == "Commodity":
        return CORRELATIONS["Commodity"]
    return np.nan


def supervisory_duration(row: pd.Series) -> float:
    asset_class = row["Asset Class"]
    if asset_class not in {"Interest Rate", "Credit"}:
        return 1.0

    cob = row["COB Date"]
    start = row.get("Start Date")
    end = row.get("End Date")
    if pd.isna(end):
        end = row.get("Maturity Date")
    if pd.isna(start):
        start = cob

    floor_years = 10.0 / BUSINESS_DAYS_PER_YEAR
    s_years = max(((start - cob).days if not pd.isna(start) else 0) / 365.0, 0.0)
    e_years = max(((end - cob).days if not pd.isna(end) else 0) / 365.0, floor_years)
    if e_years <= s_years:
        e_years = s_years + floor_years

    rate = SUPERVISORY_DURATION_RATE
    return (math.exp(-rate * s_years) - math.exp(-rate * e_years)) / rate


def adjusted_notional(row: pd.Series) -> float:
    base_notional = abs(as_number(row.get("Base Notional")))
    asset_class = row["Asset Class"]
    if asset_class in {"Interest Rate", "Credit"}:
        return base_notional * as_number(row.get("Supervisory Duration"), 1.0)
    if asset_class == "FX":
        if base_notional > 0:
            return base_notional
        notionals = [
            abs(as_number(row.get("Leg 1 Notional"))),
            abs(as_number(row.get("Leg 2 Notional"))),
            base_notional,
        ]
        return max(notionals)
    return base_notional


def maturity_factor(row: pd.Series) -> float:
    margin_flag = clean_text(row.get("Margined/ Unmargined")).upper()
    remaining_years = max(as_number(row.get("Remaining Maturity Years")), 10.0 / BUSINESS_DAYS_PER_YEAR)
    if margin_flag == "M":
        mpor_days = as_number(row.get("Margin Frequency (Business Days)"), 10.0)
        ccp_flag = clean_text(row.get("CCP")).upper()
        floor_days = 5.0 if ccp_flag == "Y" else 10.0
        mpor_days = max(mpor_days, floor_days)
        return 1.5 * math.sqrt(mpor_days / BUSINESS_DAYS_PER_YEAR)
    return math.sqrt(min(remaining_years, 1.0))


def supervisory_delta(row: pd.Series) -> float:
    direction = 1.0 if clean_text(row.get("Buy/Sell Indicator")).upper() == "B" else -1.0
    put_call = clean_text(row.get("Put/Call Indicator")).upper()
    if put_call not in {"C", "P"}:
        return direction

    price = as_number(row.get("Underlying Price (Pi)"), np.nan)
    strike = as_number(row.get("Strike Price (Ki)"), np.nan)
    if not np.isfinite(price) or not np.isfinite(strike) or price <= 0 or strike <= 0:
        return direction

    exercise_date = row.get("Contractual Exercise Date")
    cob = row.get("COB Date")
    if pd.isna(exercise_date) or pd.isna(cob):
        time_to_exercise = max(as_number(row.get("Remaining Maturity Years")), 1.0 / 365.0)
    else:
        time_to_exercise = max((exercise_date - cob).days / 365.0, 1.0 / 365.0)

    sigma = OPTION_SUPERVISORY_VOLATILITY.get(row["Asset Class"], 1.0)
    d1 = (math.log(price / strike) + 0.5 * sigma * sigma * time_to_exercise) / (
        sigma * math.sqrt(time_to_exercise)
    )
    if put_call == "C":
        return direction * normal_cdf(d1)
    return -direction * normal_cdf(-d1)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
