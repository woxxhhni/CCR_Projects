"""Asset-class add-on aggregation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from saccr_engine.config import MATURITY_BUCKETS, SUPERVISORY_FACTORS

KEYS = ["Counterparty ID", "Netting Set ID"]


def calculate_addons(enriched_trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate asset-class and aggregate add-ons.

    Returns:
        asset_class_addon, netting_set_addon, addon_detail
    """
    detail_frames = [
        _interest_rate_addons(enriched_trades),
        _fx_addons(enriched_trades),
        _credit_or_equity_addons(enriched_trades, "Credit"),
        _credit_or_equity_addons(enriched_trades, "Equity"),
        _commodity_addons(enriched_trades),
    ]
    addon_detail = pd.concat(detail_frames, ignore_index=True)
    if addon_detail.empty:
        columns = KEYS + ["Asset Class", "AddOn Exposure"]
        return pd.DataFrame(columns=columns), pd.DataFrame(columns=KEYS + ["AddOn Aggregate"]), addon_detail

    asset_class_addon = (
        addon_detail.groupby(KEYS + ["Asset Class"], as_index=False)["AddOn Exposure"].sum()
    )
    netting_set_addon = (
        asset_class_addon.groupby(KEYS, as_index=False)["AddOn Exposure"]
        .sum()
        .rename(columns={"AddOn Exposure": "AddOn Aggregate"})
    )
    return asset_class_addon, netting_set_addon, addon_detail


def _interest_rate_addons(df: pd.DataFrame) -> pd.DataFrame:
    ir = df[df["Asset Class"] == "Interest Rate"].copy()
    if ir.empty:
        return _empty_detail()

    grouped = (
        ir.groupby(KEYS + ["Asset Class", "Hedging Set", "Maturity Bucket"], as_index=False)[
            "Effective Notional"
        ].sum()
    )
    pivot = grouped.pivot_table(
        index=KEYS + ["Asset Class", "Hedging Set"],
        columns="Maturity Bucket",
        values="Effective Notional",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()

    for bucket in MATURITY_BUCKETS:
        if bucket not in pivot:
            pivot[bucket] = 0.0

    d1 = pivot["<1Y"]
    d2 = pivot["1Y-5Y"]
    d3 = pivot[">5Y"]
    expression = d1**2 + d2**2 + d3**2 + 1.4 * d1 * d2 + 1.4 * d2 * d3 + 0.6 * d1 * d3
    pivot["Aggregated Effective Notional"] = np.sqrt(np.maximum(expression, 0.0))
    pivot["AddOn Exposure"] = (
        pivot["Aggregated Effective Notional"] * SUPERVISORY_FACTORS["Interest Rate"]
    )
    pivot["Aggregation Level"] = "IR currency and maturity bucket"
    return pivot[
        KEYS
        + [
            "Asset Class",
            "Hedging Set",
            "Aggregation Level",
            "Aggregated Effective Notional",
            "AddOn Exposure",
        ]
    ]


def _fx_addons(df: pd.DataFrame) -> pd.DataFrame:
    fx = df[df["Asset Class"] == "FX"].copy()
    if fx.empty:
        return _empty_detail()

    result = (
        fx.groupby(KEYS + ["Asset Class", "Hedging Set"], as_index=False)["Effective Notional"].sum()
    )
    result["Aggregated Effective Notional"] = result["Effective Notional"].abs()
    result["AddOn Exposure"] = result["Aggregated Effective Notional"] * SUPERVISORY_FACTORS["FX"]
    result["Aggregation Level"] = "FX currency pair"
    return result[
        KEYS
        + [
            "Asset Class",
            "Hedging Set",
            "Aggregation Level",
            "Aggregated Effective Notional",
            "AddOn Exposure",
        ]
    ]


def _credit_or_equity_addons(df: pd.DataFrame, asset_class: str) -> pd.DataFrame:
    subset = df[df["Asset Class"] == asset_class].copy()
    if subset.empty:
        return _empty_detail()

    entity = (
        subset.groupby(KEYS + ["Asset Class", "Hedging Set"], as_index=False)
        .agg(
            Effective_Notional=("Effective Notional", "sum"),
            Supervisory_Factor=("Supervisory Factor", "first"),
            Correlation=("Correlation", "first"),
        )
    )
    entity["Entity AddOn"] = entity["Effective_Notional"] * entity["Supervisory_Factor"]
    entity["Systematic Component"] = entity["Correlation"] * entity["Entity AddOn"]
    entity["Idiosyncratic Component"] = (1 - entity["Correlation"] ** 2) * entity["Entity AddOn"] ** 2

    result = (
        entity.groupby(KEYS + ["Asset Class"], as_index=False)
        .agg(
            Systematic_Total=("Systematic Component", "sum"),
            Idiosyncratic_Total=("Idiosyncratic Component", "sum"),
        )
    )
    result["AddOn Exposure"] = np.sqrt(
        np.maximum(result["Systematic_Total"] ** 2 + result["Idiosyncratic_Total"], 0.0)
    )
    result["Hedging Set"] = asset_class
    result["Aggregation Level"] = f"{asset_class} entity correlation"
    result["Aggregated Effective Notional"] = np.nan
    return result[
        KEYS
        + [
            "Asset Class",
            "Hedging Set",
            "Aggregation Level",
            "Aggregated Effective Notional",
            "AddOn Exposure",
        ]
    ]


def _commodity_addons(df: pd.DataFrame) -> pd.DataFrame:
    subset = df[df["Asset Class"] == "Commodity"].copy()
    if subset.empty:
        return _empty_detail()

    commodity_type = (
        subset.groupby(KEYS + ["Asset Class", "Hedging Set", "Commodity Type"], as_index=False)
        .agg(
            Effective_Notional=("Effective Notional", "sum"),
            Supervisory_Factor=("Supervisory Factor", "first"),
            Correlation=("Correlation", "first"),
        )
    )
    commodity_type["Type AddOn"] = (
        commodity_type["Effective_Notional"] * commodity_type["Supervisory_Factor"]
    )
    commodity_type["Systematic Component"] = (
        commodity_type["Correlation"] * commodity_type["Type AddOn"]
    )
    commodity_type["Idiosyncratic Component"] = (
        (1 - commodity_type["Correlation"] ** 2) * commodity_type["Type AddOn"] ** 2
    )

    result = (
        commodity_type.groupby(KEYS + ["Asset Class", "Hedging Set"], as_index=False)
        .agg(
            Systematic_Total=("Systematic Component", "sum"),
            Idiosyncratic_Total=("Idiosyncratic Component", "sum"),
        )
    )
    result["AddOn Exposure"] = np.sqrt(
        np.maximum(result["Systematic_Total"] ** 2 + result["Idiosyncratic_Total"], 0.0)
    )
    result["Aggregation Level"] = "Commodity group/type correlation"
    result["Aggregated Effective Notional"] = np.nan
    return result[
        KEYS
        + [
            "Asset Class",
            "Hedging Set",
            "Aggregation Level",
            "Aggregated Effective Notional",
            "AddOn Exposure",
        ]
    ]


def _empty_detail() -> pd.DataFrame:
    return pd.DataFrame(
        columns=KEYS
        + [
            "Asset Class",
            "Hedging Set",
            "Aggregation Level",
            "Aggregated Effective Notional",
            "AddOn Exposure",
        ]
    )

