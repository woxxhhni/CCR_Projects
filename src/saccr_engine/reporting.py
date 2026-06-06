"""Reporting helpers for the SA-CCR engine."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def build_counterparty_summary(netting_set_exposure: pd.DataFrame) -> pd.DataFrame:
    columns = ["AddOn Aggregate", "PFE", "RC", "EAD", "RWA"]
    return (
        netting_set_exposure.groupby("Counterparty ID", as_index=False)[columns]
        .sum()
        .sort_values("RWA", ascending=False)
    )


def build_asset_class_summary(asset_class_addon: pd.DataFrame) -> pd.DataFrame:
    return (
        asset_class_addon.groupby("Asset Class", as_index=False)["AddOn Exposure"]
        .sum()
        .sort_values("AddOn Exposure", ascending=False)
    )


def write_reports(results: dict[str, pd.DataFrame], output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for name, frame in results.items():
        frame.to_csv(output_path / f"{name}.csv", index=False)

