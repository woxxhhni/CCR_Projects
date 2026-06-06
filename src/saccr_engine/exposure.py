"""RC, PFE, EAD, and RWA calculations."""

from __future__ import annotations

import math

import pandas as pd

from saccr_engine.config import ALPHA, MULTIPLIER_FLOOR

KEYS = ["Counterparty ID", "Netting Set ID"]


def replacement_cost(value: float, collateral: float) -> float:
    return max(value - collateral, 0.0)


def pfe_multiplier(value: float, collateral: float, addon_aggregate: float) -> float:
    if addon_aggregate <= 0:
        return 1.0
    exponent = (value - collateral) / (2 * (1 - MULTIPLIER_FLOOR) * addon_aggregate)
    return min(1.0, MULTIPLIER_FLOOR + (1 - MULTIPLIER_FLOOR) * math.exp(exponent))


def calculate_replacement_costs(
    enriched_trades: pd.DataFrame, collateral: pd.DataFrame | None = None
) -> pd.DataFrame:
    value = (
        enriched_trades.groupby(KEYS, as_index=False)["MtM"]
        .sum()
        .rename(columns={"MtM": "Net MtM"})
    )

    if collateral is not None and not collateral.empty:
        value = value.merge(collateral[KEYS + ["Collateral Amount"]], on=KEYS, how="left")
    else:
        value["Collateral Amount"] = 0.0

    value["Collateral Amount"] = value["Collateral Amount"].fillna(0.0)
    value["RC"] = value.apply(
        lambda row: replacement_cost(row["Net MtM"], row["Collateral Amount"]), axis=1
    )
    return value


def calculate_exposure(
    netting_set_addon: pd.DataFrame,
    replacement_costs: pd.DataFrame,
    counterparty_reference: pd.DataFrame | None = None,
) -> pd.DataFrame:
    result = replacement_costs.merge(netting_set_addon, on=KEYS, how="left")
    result["AddOn Aggregate"] = result["AddOn Aggregate"].fillna(0.0)
    result["Multiplier"] = result.apply(
        lambda row: pfe_multiplier(
            row["Net MtM"], row["Collateral Amount"], row["AddOn Aggregate"]
        ),
        axis=1,
    )
    result["PFE"] = result["Multiplier"] * result["AddOn Aggregate"]
    result["EAD"] = ALPHA * (result["RC"] + result["PFE"])

    if counterparty_reference is not None and not counterparty_reference.empty:
        result = result.merge(counterparty_reference, on="Counterparty ID", how="left")
    if "Risk Weight" not in result:
        result["Risk Weight"] = 1.0
    result["Risk Weight"] = result["Risk Weight"].fillna(1.0)
    result["RWA"] = result["EAD"] * result["Risk Weight"]
    return result

