"""RC, PFE, EAD, and RWA calculations."""

from __future__ import annotations

import math

import pandas as pd

from saccr_engine.config import ALPHA, MULTIPLIER_FLOOR

KEYS = ["Counterparty ID", "Netting Set ID"]
COLLATERAL_COLUMNS = [
    "Collateral Amount",
    "Threshold Amount",
    "Minimum Transfer Amount",
    "Net Independent Collateral Amount",
]


def replacement_cost(
    value: float,
    collateral: float,
    margin_flag: str = "U",
    threshold: float = 0.0,
    minimum_transfer_amount: float = 0.0,
    nica: float = 0.0,
) -> float:
    if str(margin_flag).strip().upper() == "M":
        margin_call_exposure = threshold + minimum_transfer_amount - nica
        return max(value - collateral, margin_call_exposure, 0.0)
    return max(value - collateral, 0.0)


def pfe_multiplier(value: float, collateral: float, addon_aggregate: float) -> float:
    if addon_aggregate <= 0:
        return 1.0
    exponent = (value - collateral) / (2 * (1 - MULTIPLIER_FLOOR) * addon_aggregate)
    return min(1.0, MULTIPLIER_FLOOR + (1 - MULTIPLIER_FLOOR) * math.exp(exponent))


def calculate_replacement_costs(
    enriched_trades: pd.DataFrame,
    collateral: pd.DataFrame | None = None,
    force_unmargined: bool = False,
) -> pd.DataFrame:
    value = (
        enriched_trades.groupby(KEYS, as_index=False)["MtM"]
        .sum()
        .rename(columns={"MtM": "Net MtM"})
    )
    margin_source = (
        "SA-CCR Margin Treatment"
        if "SA-CCR Margin Treatment" in enriched_trades.columns
        else "Margined/ Unmargined"
    )
    margin = (
        enriched_trades.groupby(KEYS)[margin_source]
        .agg(lambda values: "M" if (values.astype(str).str.upper() == "M").any() else "U")
        .reset_index()
        .rename(columns={margin_source: "Margin Agreement"})
    )
    value = value.merge(margin, on=KEYS, how="left")

    if collateral is not None and not collateral.empty:
        available_columns = [column for column in COLLATERAL_COLUMNS if column in collateral.columns]
        extra_columns = ["Margin Agreement ID"] if "Margin Agreement ID" in collateral.columns else []
        value = value.merge(collateral[KEYS + available_columns + extra_columns], on=KEYS, how="left")

    for column in COLLATERAL_COLUMNS:
        if column not in value.columns:
            value[column] = 0.0
        value[column] = value[column].fillna(0.0)

    if "Margin Agreement ID" not in value.columns:
        value["Margin Agreement ID"] = ""
    value["Margin Agreement ID"] = value["Margin Agreement ID"].fillna("")

    if force_unmargined:
        value["Margin Agreement"] = "U"
        value["Collateral Amount"] = value["Net Independent Collateral Amount"]

    value["Margin Agreement"] = value["Margin Agreement"].fillna("U")
    value["RC"] = value.apply(
        lambda row: replacement_cost(
            value=row["Net MtM"],
            collateral=row["Collateral Amount"],
            margin_flag=row["Margin Agreement"],
            threshold=row["Threshold Amount"],
            minimum_transfer_amount=row["Minimum Transfer Amount"],
            nica=row["Net Independent Collateral Amount"],
        ),
        axis=1,
    )
    value["RC Formula"] = value["Margin Agreement"].map(
        {
            "M": "max(V-C, TH+MTA-NICA, 0)",
            "U": "max(V-C, 0)",
        }
    ).fillna("max(V-C, 0)")
    if force_unmargined:
        value["RC Formula"] = "unmargined cap basis: max(V-NICA, 0)"
    return value


def apply_margined_ead_cap(
    exposure: pd.DataFrame,
    unmargined_exposure: pd.DataFrame,
) -> pd.DataFrame:
    result = exposure.merge(
        unmargined_exposure[KEYS + ["EAD"]].rename(columns={"EAD": "Unmargined EAD Cap"}),
        on=KEYS,
        how="left",
    )
    result["EAD Before Cap"] = result["EAD"]
    margin_flag = result["Margin Agreement"].fillna("U").astype(str).str.upper()
    cap_available = result["Unmargined EAD Cap"].notna()
    result["EAD Cap Applied"] = (
        (margin_flag == "M")
        & cap_available
        & (result["EAD"] > result["Unmargined EAD Cap"])
    )
    result.loc[result["EAD Cap Applied"], "EAD"] = result.loc[
        result["EAD Cap Applied"], "Unmargined EAD Cap"
    ]
    if "Risk Weight" not in result:
        result["Risk Weight"] = 1.0
    result["RWA Before Cap"] = result["EAD Before Cap"] * result["Risk Weight"]
    result["RWA"] = result["EAD"] * result["Risk Weight"]
    return result


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
